/**
 * WebSocket 연결 생명주기 관리 훅.
 * 연결 수립, hello/welcome 핸드셰이크, 하트비트, 재연결, 정리를 담당.
 * API 명세서 v0.2.0 기준 heartbeat/heartbeat_ack 프로토콜 사용.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { AppState, Linking } from "react-native";

import {
  DEVICE_ID,
  HEARTBEAT_INTERVAL,
  MAX_RECONNECT,
  NETWORK_BENCHMARK_ENABLED,
  NETWORK_BENCHMARK_INTERVAL_MS,
  NETWORK_BENCHMARK_PAYLOAD_BYTES,
  RECONNECT_DELAY,
  RECONNECT_DELAY_MAX,
  TOKEN,
  WS_URL,
} from "../config";
import { findPhoneContact, savePhoneContact } from "../services/contactsBridge";
import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";
import type { WSMessage, WSStatus } from "../types/detection";

export interface NavRouteData {
  appKey: string;
  waypoints: { lat: number; lon: number }[];
}

export interface UseWebSocketReturn {
  status: WSStatus;
  send: (data: object) => void;
  /** JPEG raw byte 프레임을 바이너리 WS 프레임으로 전송한다 (base64 미경유). */
  sendBinary: (data: Uint8Array) => void;
  lastMessage: WSMessage | null;
  /** 지도 패널용 경로. lastMessage는 초당 수십 건의 ack/탐지 메시지에 덮여
   * 저빈도 이벤트가 React 배칭으로 유실될 수 있어(guide 오디오와 동일한 이유)
   * nav_route는 전용 상태로 직접 보존한다. null = 경로 미설정/해제. */
  navRoute: NavRouteData | null;
  /** STT 질문 상호작용(녹음~응답 수신) 구간 동안 인지 경로 가이드 음성을 뮤트한다.
   * 반사 경로(reflex_alert)는 안전 비협상 원칙에 따라 절대 뮤트하지 않는다.
   * timeoutMs를 넘기면 해당 시간 뒤 자동 해제(기본은 STT_INTERACTION_TIMEOUT_MS 안전 상한). */
  setSttInteractionActive: (active: boolean, timeoutMs?: number) => void;
  /** network_probe RTT 최신값(ms). EXPO_PUBLIC_NETWORK_BENCHMARK=true일 때 갱신된다. */
  networkRttMs: number | null;
  /** network_probe RTT 최근 30개 평균(ms). */
  networkRttAvgMs: number | null;
}

// STT 응답이 오지 않는 예외 상황(네트워크 끊김 등)에서 인지 경로가 무한정 뮤트된 채
// 남지 않도록 하는 안전 상한(서버 STT+LLM+TTS 실측 지연이 최대 15s대인 것을 감안).
const STT_INTERACTION_TIMEOUT_MS = 20000;

export function useWebSocket(
  deviceId: string = DEVICE_ID,
  token: string = TOKEN,
  /** WiFi/USB 토글에 따라 CameraView가 넘긴다. 기본은 config.WS_URL(WiFi). */
  wsBaseUrl: string = WS_URL,
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const networkProbeTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const pendingNetworkProbes = useRef<Map<string, number>>(new Map());
  const networkRttSamples = useRef<number[]>([]);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [navRoute, setNavRoute] = useState<NavRouteData | null>(null);
  const [networkRttMs, setNetworkRttMs] = useState<number | null>(null);
  const [networkRttAvgMs, setNetworkRttAvgMs] = useState<number | null>(null);
  const appStateRef = useRef(AppState.currentState);

  // STT 상호작용 중 인지 경로 뮤트 상태. ref로 관리해 onmessage 클로저 안에서도
  // 항상 최신 값을 읽는다(state였다면 connect()가 재실행되지 않는 한 stale closure).
  const sttInteractionActiveRef = useRef(false);
  const sttInteractionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 폴백 모드 진입 음성 고지를 단절 1회당 한 번만 내보내기 위한 플래그.
  // true인 동안 재연결이 성공하면 복구 고지를 내보내고 다시 false로 돌린다.
  const fallbackAnnouncedRef = useRef(false);
  // 직전에 수신한 "guide" JSON 메시지가 인지(카메라) 출처인지 기록해, 뒤이어 오는
  // 바이너리 오디오 프레임(ArrayBuffer)도 같은 기준으로 뮤트할지 판단한다.
  const pendingGuideIsCognitiveRef = useRef(false);

  const setSttInteractionActive = useCallback(
    (active: boolean, timeoutMs: number = STT_INTERACTION_TIMEOUT_MS) => {
      sttInteractionActiveRef.current = active;
      if (sttInteractionTimeoutRef.current) {
        clearTimeout(sttInteractionTimeoutRef.current);
        sttInteractionTimeoutRef.current = null;
      }
      if (active) {
        sttInteractionTimeoutRef.current = setTimeout(() => {
          sttInteractionActiveRef.current = false;
          sttInteractionTimeoutRef.current = null;
        }, timeoutMs);
      }
    },
    [],
  );

  const clearHeartbeat = useCallback(() => {
    if (heartbeatTimer.current) {
      clearInterval(heartbeatTimer.current);
      heartbeatTimer.current = null;
    }
  }, []);

  const clearNetworkProbe = useCallback(() => {
    if (networkProbeTimer.current) {
      clearInterval(networkProbeTimer.current);
      networkProbeTimer.current = null;
    }
    pendingNetworkProbes.current.clear();
  }, []);

  const sendNetworkProbe = useCallback((ws: WebSocket) => {
    if (!NETWORK_BENCHMARK_ENABLED || ws.readyState !== WebSocket.OPEN) return;
    const probeId = `ios-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    pendingNetworkProbes.current.set(probeId, Date.now());
    ws.send(
      JSON.stringify({
        type: "network_probe",
        probe_id: probeId,
        client_label: "ios-app",
        client_sent_ts: Date.now(),
        payload: "x".repeat(Math.max(0, NETWORK_BENCHMARK_PAYLOAD_BYTES)),
      }),
    );
  }, []);

  const recordNetworkProbeAck = useCallback((probeId: string | undefined) => {
    if (!probeId) return;
    const sentAt = pendingNetworkProbes.current.get(probeId);
    if (sentAt === undefined) return;
    pendingNetworkProbes.current.delete(probeId);
    const rttMs = Date.now() - sentAt;
    const samples = [...networkRttSamples.current, rttMs].slice(-30);
    networkRttSamples.current = samples;
    const avgMs = samples.reduce((sum, value) => sum + value, 0) / samples.length;
    setNetworkRttMs(rttMs);
    setNetworkRttAvgMs(Math.round(avgMs));
    console.log(`[NetworkBench] probe=${probeId}, rtt=${rttMs}ms, avg30=${Math.round(avgMs)}ms`);
  }, []);

  const connect = useCallback(() => {
    const currentState = wsRef.current?.readyState;
    if (currentState === WebSocket.OPEN || currentState === WebSocket.CONNECTING) return;

    const wsUrl = `${wsBaseUrl}?device_id=${deviceId}`;
    console.log(`[WS] 연결 시도 주소: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    // guide 오디오(WAV)를 서버가 바이너리 프레임으로 보내므로(2026-07-09 도입),
    // 수신 시 Blob이 아닌 ArrayBuffer로 받아 동기적으로 다루기 쉽게 한다.
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;
    // 폴백 모드 중의 백그라운드 재시도가 상태를 "connecting"으로 덮으면 온디바이스
    // 경보/BBox 표시(CameraView의 fallback 판정)가 시도할 때마다 꺼졌다 켜진다.
    // 폴백은 실제 재연결 성공(welcome)까지 유지한다.
    setStatus((prev) => (prev === "fallback" ? prev : "connecting"));

    ws.onopen = () => {
      if (wsRef.current !== ws) return;
      // 주의: 재연결 카운터는 여기(TCP 연결)가 아니라 welcome(핸드셰이크 성공)에서
      // 리셋한다. 인증 실패 등으로 "연결 직후 끊김"이 반복되는 경우에도 백오프가
      // 계속 자라고 폴백 고지가 정상 동작해야 하기 때문이다.
      ws.send(
        JSON.stringify({ type: "hello", device_id: deviceId, token }),
      );

      clearHeartbeat();
      heartbeatTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "heartbeat", ts: Date.now() }));
        }
      }, HEARTBEAT_INTERVAL);

      clearNetworkProbe();
      if (NETWORK_BENCHMARK_ENABLED) {
        sendNetworkProbe(ws);
        networkProbeTimer.current = setInterval(() => {
          sendNetworkProbe(ws);
        }, NETWORK_BENCHMARK_INTERVAL_MS);
      }
    };

    ws.onmessage = (event: any) => {
      if (wsRef.current !== ws) return;
      // guide 오디오 바이너리 프레임: 직전 "guide" JSON 메시지(transport:"binary")에
      // 이어 도착하는 원본 WAV 바이트다. base64 인코딩을 완전히 우회한다(2026-07-09).
      if (event.data instanceof ArrayBuffer) {
        if (pendingGuideIsCognitiveRef.current && sttInteractionActiveRef.current) {
          console.log(`[WS] STT 상호작용 중 - 인지 경로 오디오 뮤트(bytes=${event.data.byteLength})`);
          return;
        }
        console.log(`[WS] guide 오디오 바이너리 수신: bytes=${event.data.byteLength}`);
        void audioEngine.playGuideAudioBytes(new Uint8Array(event.data));
        return;
      }

      try {
        const data: WSMessage = JSON.parse(event.data);

        if (data.type === "welcome") {
          setLastMessage(data);
          setStatus("connected");
          reconnectCount.current = 0;
          console.log(`[WS] 연결 성공, 세션 ID: ${data.session_id}`);
          // 폴백 모드 고지 이후의 복구는 사용자에게 반드시 알린다. 사용자는 화면을
          // 볼 수 없으므로 음성 고지가 유일한 상태 전달 수단이다(Mitos 로드맵).
          if (fallbackAnnouncedRef.current) {
            fallbackAnnouncedRef.current = false;
            audioEngine.speakFallback("서버 연결이 복구되었습니다. 상세 안내를 다시 시작합니다.");
          }
        } else if (data.type === "heartbeat") {
          ws.send(
            JSON.stringify({ type: "heartbeat_ack", ts: Date.now() }),
          );
        } else if (data.type === "network_probe_ack") {
          recordNetworkProbeAck(data.probe_id);
        } else if (data.type === "reflex_alert") {
          setLastMessage(data);
          // 입체 비프음 및 햅틱 연동 실행 (docs/reflex_audio_specification.md 준수)
          // 채널 분기 (접근성 UX, 2026-07-13):
          // - 긴급(Critical/High, interval<=100): 핑퐁 비프만. 음성 클립은 반응을 방해하고
          //   기계음 피로를 키우므로 재생하지 않는다.
          // - 여유(Mid/Low, interval>100): 방향 음성 클립(+비프). 상세 안내는 인지 guide TTS.
          const panning = typeof data.panning === "number" ? data.panning : 0.0;
          const beepInterval = typeof data.beep_interval_ms === "number" ? data.beep_interval_ms : 250;
          const hapticPattern = typeof data.haptic_pattern === "string" ? data.haptic_pattern : "double";
          const isUrgentBeepOnly = beepInterval <= 100;

          if (!audioEngine.isGuidePlaying) {
            console.log(
              `[WS] 반사 알림 수신: id=${data.alert_id}, panning=${panning}, interval=${beepInterval}ms, pattern=${hapticPattern}, channel=${isUrgentBeepOnly ? "beep-only" : "voice+beep"}`,
            );
          }
          audioEngine.playBeep(panning, beepInterval);
          hapticEngine.trigger(hapticPattern);
          if (data.clip && !isUrgentBeepOnly) {
            void audioEngine.playReflexClip(data.clip);
          }
        } else if (data.type === "guide") {
          // 인지 경로 가이드 음성은 onmessage에서 직접 재생한다(React 상태를 경유하지 않음).
          // [2026-07-09 변경] 서버가 guide 오디오를 더 이상 audio_mp3_b64(base64 문자열)로
          // JSON에 싣지 않고, 이 메시지 직후 바이너리 프레임으로 원본 WAV 바이트를 보낸다
          // (transport:"binary"). 실제 재생은 위 ArrayBuffer 분기에서 이어서 처리한다.
          // transport가 "binary"가 아니면(서버 TTS 실패) 즉시 단말 TTS로 폴백한다.
          console.log(`[WS] guide 수신: text="${data.guidance_text}", transport=${data.transport}`);

          // event_id가 "stt-"로 시작하면 STT 질문/네비게이션 응답(항상 재생),
          // 그 외(카메라 event-*)는 인지 경로 - STT 상호작용 중이면 뮤트 대상이다.
          const isStt = String(data.event_id ?? "").startsWith("stt-");
          pendingGuideIsCognitiveRef.current = !isStt;
          if (isStt) {
            // 2026-07-10 실기기 실측: 응답 텍스트가 "도착한 순간" 바로 뮤트를 풀면,
            // 실제 오디오 재생은 그 뒤로도 몇 초 더 이어지는데 그 사이 인지 경로
            // 메시지가 끼어들어 답변이 중간에 끊기는 문제가 있었다("직진하면 차량을
            // 건너주세요"가 답변을 끊음). 응답 재생이 끝날 것으로 추정되는 시점까지
            // 뮤트를 유지한다 - duration_ms(바이너리 WAV 실측 길이)가 있으면 그 값을,
            // 없으면(speakFallback 폴백) 텍스트 길이로 대략 추정한다.
            // 2026-07-10 추가 실측: 서버가 보낸 duration_ms가 긴 문장(TTS 청크 분할
            // 추정)에서 실제 재생 길이보다 훨씬 짧게 나오는 경우가 확인됐다(13초 분량
            // 오디오인데 duration_ms 기준 홀드가 1.3초 만에 풀려 끊김 재현). 서버 값을
            // 그대로 신뢰하지 않고 텍스트 길이 추정치와 큰 값을 사용한다(방어적 하한).
            const guideText = data.guidance_text ?? "";
            const serverDurationMs =
              typeof data.duration_ms === "number" && data.duration_ms > 0 ? data.duration_ms : 0;
            const textEstimateMs = Math.max(guideText.length * 180, 2000);
            const estimatedMs = Math.max(serverDurationMs, textEstimateMs);
            setSttInteractionActive(true, estimatedMs + 1200);
          }

          if (!isStt && sttInteractionActiveRef.current) {
            console.log("[WS] STT 상호작용 중 - 인지 경로 가이드 텍스트 뮤트");
          } else if (data.transport !== "binary" && data.guidance_text) {
            console.log("[WS] -> speakFallback(단말 TTS) 경로 진입");
            audioEngine.speakFallback(data.guidance_text);
          }
          setLastMessage(data as WSMessage);
        } else if (data.type === "nav_route") {
          // 지도 경로: lastMessage 경유 시 고빈도 ack/탐지 메시지에 덮여 유실되므로
          // 전용 상태로 직접 반영한다.
          const wps = data.waypoints ?? [];
          console.log(`[WS] nav_route 수신: waypoints=${wps.length}`);
          setNavRoute(
            wps.length > 0
              ? { appKey: data.app_key ?? "", waypoints: wps }
              : null,
          );
        } else if (data.type === "contact_save") {
          // [TH HARDCODE 아님 - 단말 영속화]
          // 서버가 파싱한 이름/번호를 Android 주소록에 기록한다.
          // 💡 [면접 대비] 서버 RAM만으로는 폰 연락처 앱에 안 보인다.
          //    contact_save → savePhoneContact → ContactsContract INSERT.
          const contactName = data.contact_name ?? "";
          const phoneNumber = data.phone_number ?? "";
          console.log(
            `[WS] contact_save 수신: contact=${contactName}, phone=${phoneNumber}`,
          );
          if (contactName && phoneNumber) {
            void savePhoneContact(contactName, phoneNumber).then((ok) => {
              if (!ok) {
                audioEngine.speakFallback(
                  "주소록 저장에 실패했습니다. 연락처 권한을 확인해 주세요.",
                );
              }
            });
          }
        } else if (data.type === "dial_action") {
          // [TH HARDCODE 아님] 긴급전화/연락처 전화걸기: 서버는 번호(또는 이름만)
          // 전달하고, 실제 다이얼은 OS Linking "tel:"에 위임한다.
          // 💡 [면접 대비] phone 비고 + device_lookup → 단말 주소록 재조회.
          //    (서버 재시작으로 ContactStore RAM이 비어도 전화 가능)
          // Linking은 다이얼러 실행까지만 보장, 통화 연결 여부는 확인하지 않는다.
          const contactName = data.contact_name ?? "";
          let phoneNumber = data.phone_number ?? "";
          console.log(
            `[WS] dial_action 수신: contact=${contactName}, phone=${phoneNumber}, lookup=${data.device_lookup}`,
          );
          void (async () => {
            if (!phoneNumber && data.device_lookup && contactName) {
              phoneNumber = (await findPhoneContact(contactName)) ?? "";
            }
            if (phoneNumber) {
              Linking.openURL(`tel:${phoneNumber}`).catch((err) =>
                console.error("[WS] 전화 걸기 실패:", err),
              );
            } else {
              audioEngine.speakFallback(
                "저장된 번호를 찾을 수 없습니다. 먼저 번호를 저장해 주세요.",
              );
            }
          })();
        } else {
          setLastMessage(data);
        }
      } catch (err) {
        console.error("[WS] 메시지 파싱 오류:", err);
      }
    };

    ws.onclose = (event: any) => {
      // 이전 소켓의 종료 콜백이 새 소켓의 재연결 상태를 덮어쓰지 않게 한다.
      if (wsRef.current !== ws) {
        console.log("[WS] 구 소켓 종료 이벤트 무시");
        return;
      }
      wsRef.current = null;
      // 폴백 모드는 재연결 성공까지 유지한다(위 connecting 주석과 동일한 이유).
      setStatus((prev) => (prev === "fallback" ? prev : "disconnected"));
      clearHeartbeat();
      clearNetworkProbe();
      const closeCode = typeof event?.code === "number" ? event.code : -1;
      const closeReason = typeof event?.reason === "string" ? event.reason : "";
      console.log(`[WS] 연결 종료 code=${closeCode} reason=${closeReason}`);

      // 오디오 및 진동 피드백 즉각 종료
      audioEngine.stopBeep();
      hapticEngine.stopContinuous();

      // 2026-07-11 정책 변경(Mitos 로드맵 우선순위 2): 재연결을 포기하지 않는다.
      // 지수 백오프(1s -> 2s -> 4s ... 최대 RECONNECT_DELAY_MAX)로 무한 재시도하고,
      // MAX_RECONNECT회 연속 실패 시점에 폴백 모드로 전환하며 음성으로 고지한다.
      // 폴백 모드에서도 온디바이스 탐지/반사 경보는 계속 동작하므로(CameraView),
      // 사용자에게는 "기본 경보만 제공"임을 알리는 것이 핵심이다.
      reconnectCount.current += 1;
      const backoffMs = Math.min(
        RECONNECT_DELAY * 2 ** (reconnectCount.current - 1),
        RECONNECT_DELAY_MAX,
      );
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      reconnectTimer.current = setTimeout(() => connect(), backoffMs);
      console.log(
        `[WS] 재연결 예약: ${reconnectCount.current}회차, ${backoffMs}ms 후`,
      );

      if (reconnectCount.current >= MAX_RECONNECT) {
        setStatus("fallback");
        if (!fallbackAnnouncedRef.current) {
          fallbackAnnouncedRef.current = true;
          audioEngine.speakFallback(
            "서버 연결이 끊겨 기본 경보 모드로 전환합니다. 연결은 계속 시도합니다.",
          );
          console.warn(
            `[WS] 연속 ${reconnectCount.current}회 실패 - 폴백 모드 전환 및 음성 고지(재시도는 계속).`,
          );
        }
      }
    };

    ws.onerror = (error: any) => {
      if (wsRef.current !== ws) {
        console.log("[WS] 구 소켓 오류 이벤트 무시");
        return;
      }
      console.error("[WS] 오류:", error);
    };
  }, [
    deviceId,
    token,
    wsBaseUrl,
    clearHeartbeat,
    clearNetworkProbe,
    sendNetworkProbe,
    recordNetworkProbeAck,
  ]);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const sendBinary = useCallback((data: Uint8Array) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    // RN WebSocket은 ArrayBufferView(Uint8Array)를 바이너리 프레임으로 직접 전송한다.
    // 다만 readyState 검사 직후 onclose가 끼어들 수 있어(send 레이스), 예외를 흡수한다.
    try {
      ws.send(data);
    } catch (error) {
      console.warn("[WS] 바이너리 전송 스킵(소켓 상태 변경):", error);
    }
  }, []);

  useEffect(() => {
    // 수송 모드(WiFi/USB) 변경 시 기존 소켓을 끊고 새 주소로 붙는다.
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    clearHeartbeat();
    clearNetworkProbe();
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
    reconnectCount.current = 0;
    fallbackAnnouncedRef.current = false;
    connect();
    return () => {
      clearHeartbeat();
      clearNetworkProbe();
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }

      // 오디오 및 진동 피드백 완전 종료
      audioEngine.stopBeep();
      hapticEngine.stopContinuous();

      if (sttInteractionTimeoutRef.current) {
        clearTimeout(sttInteractionTimeoutRef.current);
        sttInteractionTimeoutRef.current = null;
      }

      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearHeartbeat, clearNetworkProbe]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      const previousState = appStateRef.current;
      appStateRef.current = nextState;

      if (nextState !== "active") {
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
        clearHeartbeat();
        clearNetworkProbe();
        if (wsRef.current) {
          wsRef.current.onclose = null;
          wsRef.current.close();
          wsRef.current = null;
        }
        return;
      }

      if (previousState !== "active") {
        reconnectCount.current = 0;
        fallbackAnnouncedRef.current = false;
        connect();
      }
    });

    return () => subscription.remove();
  }, [connect, clearHeartbeat, clearNetworkProbe]);

  return {
    status,
    send,
    sendBinary,
    lastMessage,
    navRoute,
    setSttInteractionActive,
    networkRttMs,
    networkRttAvgMs,
  };
}
