/**
 * WebSocket 연결 생명주기 관리 훅.
 * 연결 수립, hello/welcome 핸드셰이크, 하트비트, 재연결, 정리를 담당.
 * API 명세서 v0.2.0 기준 heartbeat/heartbeat_ack 프로토콜 사용.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";

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
  getWsUrlCandidates,
} from "../config";
// 서버 heartbeat 미수신 타임아웃. 서버가 5초마다 heartbeat를 보내므로(HeartbeatManager
// interval=5), 15초(3회분) 이상 안 오면 연결이 죽은 것으로 판단해 능동 종료한다.
// 너무 짧으면 서버 busy 시 오탐, 너무 길면 half-open 감지 지연. 3회분은 네트워크 지터 여유.
const SERVER_HEARTBEAT_TIMEOUT_MS = 15000;
import { audioEngine } from "../services/audioEngine";
import {
  GUIDE_PRIORITY,
  resolveGuidePriority,
  type GuidePriority,
} from "../services/guidePriority";
import { hapticEngine } from "../services/hapticEngine";
import { placePhoneCall } from "../services/phoneDialBridge";
import type { WSMessage, WSStatus } from "../types/detection";
import { normalizeTextForSpeech } from "../utils/speechText";

/**
 * 현재 전달된 primary URL을 1순위로 두고, config 후보(LAN/Tailscale)를 합친다.
 * 학원 WiFi 기기격리로 LAN이 실패해도 Tailscale로 넘어가게 한다.
 */
function expandWsUrlCandidates(primaryBase: string): string[] {
  const base = primaryBase.replace(/\?.*$/, "").replace(/\/$/, "");
  const merged = [base];
  for (const url of getWsUrlCandidates()) {
    const normalized = url.replace(/\?.*$/, "").replace(/\/$/, "");
    if (!merged.includes(normalized)) {
      merged.push(normalized);
    }
  }
  return merged;
}

export interface NavRouteData {
  appKey: string;
  waypoints: { lat: number; lon: number }[];
}

export interface UseWebSocketReturn {
  status: WSStatus;
  send: (data: object) => void;
  /** JPEG raw byte 프레임을 바이너리 WS 프레임으로 전송한다 (base64 미경유). */
  sendBinary: (data: Uint8Array) => void;
  /**
   * ACK 기반 in-flight 제한을 적용해 detection 메타(JSON) + binary JPEG를 한 쌍으로 전송한다
   * (2026-07-17, P0). MAX_IN_FLIGHT_FRAMES 초과 시 메타·binary 모두 같이 드롭하고 false를
   * 반환한다(서버 pending_binary_meta 매칭 오류 방지). ACK 수신 시 in-flight에서 해제된다.
   */
  sendDetectionFrame: (
    meta: { type: string; payload: { event_id?: string; frame_id?: number; [k: string]: unknown } },
    jpegBytes: Uint8Array,
  ) => boolean;
  /** 현재 ACK를 기다리는 in-flight 프레임 수. 디버그/지표용. */
  inFlightFrameCount: number;
  lastMessage: WSMessage | null;
  /** 지도 패널용 경로. lastMessage는 초당 수십 건의 ack/탐지 메시지에 덮여
   * 저빈도 이벤트가 React 배칭으로 유실될 수 있어(guide 오디오와 동일한 이유)
   * nav_route는 전용 상태로 직접 보존한다. null = 경로 미설정/해제. */
  navRoute: NavRouteData | null;
  /** network_probe RTT 최신값(ms). EXPO_PUBLIC_NETWORK_BENCHMARK=true일 때 갱신된다. */
  networkRttMs: number | null;
  /** network_probe RTT 최근 30개 평균(ms). */
  networkRttAvgMs: number | null;
  /** 서버로부터 메시지를 마지막으로 수신한 시각(Date.now()). WS half-open 감지와
   * CameraView의 서버 생존 판정에 사용. 0 = 아직 수신 없음(초기 연결 전). */
  lastServerMessageTs: number;
}

// STT 응답이 오지 않는 예외 상황(네트워크 끊김 등)에서 인지 경로가 무한정 뮤트된 채
// 남지 않도록 하는 안전 상한(서버 STT+LLM+TTS 실측 지연이 최대 15s대인 것을 감안).
const STT_INTERACTION_TIMEOUT_MS = 20000;

// 💡 [면접 대비 주석] ACK 기반 in-flight 프레임 제한 (2026-07-17, P0).
// 서버가 ACK를 반환하기 전에 단말이 무제한 프레임을 밀어 넣으면, WS 송신 버퍼·서버
// 수신 큐·콘솔 relay 경로에 과거 프레임이 누적돼 버퍼링이 발생한다. ACK를 받은 프레임만
// 다음 프레임으로 교체하는 최소 역압력(backpressure). 2는 "현재 전송중 + 여유 1" 의미로,
// 단일 RTT 지연 동안 다음 프레임을 멈추지 않기 위한 여유분이다.
const MAX_IN_FLIGHT_FRAMES = 2;

// 2026-07-18: 핸드셰이크(welcome)까지 못 가고 끊긴 후보를 재시도 순환에서 잠시 제외하는
// 쿨다운(ms). RECONNECT_DELAY_MAX보다 넉넉히 길게 잡아, 짧은 백오프 구간 동안은 계속
// 건너뛰고 망 상태가 바뀔 시간을 준 뒤에만 다시 시도한다.
const CANDIDATE_COOLDOWN_MS = 45000;

// 미응답 network_probe 보관 상한(ms). probe 주기(기본 1s)와 RTT 여유를 감안한 값.
const NETWORK_PROBE_TTL_MS = 10000;
// Near 클립 1회 재생 이력을 보관할 최대 track 수. reflex_clear 유실 시 무한 증가 차단.
const NEAR_CLIP_TRACK_LIMIT = 256;

export function useWebSocket(
  deviceId: string = DEVICE_ID,
  token: string = TOKEN,
  /** WiFi/USB 토글에 따라 CameraView가 넘긴다. 기본은 config.WS_URL(WiFi). */
  wsBaseUrl: string = WS_URL,
  /**
   * 2026-07-21 P0: detection ack의 server_busy / suggest_reflex_interval_ms 백프레셔.
   * 연결 재생성 없이 최신 콜백을 쓰기 위해 내부 ref로 보관한다.
   */
  onServerLoad?: (info: { busy: boolean; suggestIntervalMs?: number }) => void,
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const onServerLoadRef = useRef(onServerLoad);
  useEffect(() => {
    onServerLoadRef.current = onServerLoad;
  }, [onServerLoad]);
  const reconnectCount = useRef(0);
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const networkProbeTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  // 💡 [면접 대비 주석] 서버 heartbeat 수신 시각 추적 (2026-07-28).
  // 서버는 5초마다 heartbeat를 보낸다(HeartbeatManager interval=5). 단말은 그에 대해
  // heartbeat_ack를 반환하지만, 역방향(서버 -> 단말) 타임아웃이 없었다. WS가 half-open으로
  // 죽으면(TCP는 살아있으나 WS 메시지 불통) onclose가 발화하지 않아 status가 "connected"로
  // 고정되고, CameraView가 온디바이스 반사 경보를 억제한 채 서버 응답을 무한 대기했다.
  // 서버 heartbeat가 15초(3회분) 이상 안 오면 능동적으로 ws.close()하여 onclose를 강제한다.
  const lastServerHeartbeatTsRef = useRef(0);
  // 서버로부터 받은 모든 메시지(heartbeat, ack, reflex_alert, guide, server_detection 등)의
  // 최신 수신 시각. CameraView가 "서버 생존" 판정을 lastFrameSent 의존에서 이 값 기반으로
  // 단순화할 수 있도록 노출한다. WS가 죽으면 어떤 메시지도 안 오므로 이 값이 멈추고,
  // 일정 시간 경과 시 타임아웃으로 판정한다.
  const [lastServerMessageTs, setLastServerMessageTs] = useState(0);
  const pendingNetworkProbes = useRef<Map<string, number>>(new Map());
  // ACK 기반 in-flight 프레임 추적 (2026-07-17, P0).
  // key: `${event_id}:${frame_id}`, value: 송신 시각(Date.now()).
  // 서버 ACK가 frame_id를 반환하므로 이를 키로 사용한다.
  const pendingFrames = useRef<Map<string, number>>(new Map());
  const networkRttSamples = useRef<number[]>([]);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [navRoute, setNavRoute] = useState<NavRouteData | null>(null);
  const [networkRttMs, setNetworkRttMs] = useState<number | null>(null);
  const [networkRttAvgMs, setNetworkRttAvgMs] = useState<number | null>(null);
  const appStateRef = useRef(AppState.currentState);

  // T3-C (2026-07-18): STT 응답 종료 콜백 누락 시 강제 해제하기 위한 안전 상한 타이머.
  // audioEngine.setSttActive(false)는 원칙적으로 STT 응답 오디오의 onDone/onStopped
  // 콜백에서 호출되지만, iOS 백그라운드 전환 등으로 콜백이 도착하지 않을 경우를
  // 대비해 최대 STT_INTERACTION_TIMEOUT_MS 후에는 강제 해제한다.
  const sttSafetyReleaseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 폴백 모드 진입 음성 고지를 단절 1회당 한 번만 내보내기 위한 플래그.
  // true인 동안 재연결이 성공하면 복구 고지를 내보내고 다시 false로 돌린다.
  const fallbackAnnouncedRef = useRef(false);
  // WiFi 실패 시 Tailscale 등 다음 후보 URL로 순환한다.
  // 성공한 후보 우선순위는 welcome에서 승격하며, wsBaseUrl이 바뀔 때만 목록을 재생성한다.
  const wsUrlCandidatesRef = useRef<string[]>(expandWsUrlCandidates(wsBaseUrl));
  const wsUrlIndexRef = useRef(0);
  // 2026-07-18: 후보가 welcome까지 못 가고(핸드셰이크 전) 끊기면 "연결 실패"로 보고
  // 이 시각까지 재시도 순환에서 제외한다. 도달 불가능한 후보(예: Tailscale 미설정망)를
  // 매 재연결마다 블라인드하게 다시 시도해 10초씩 낭비하던 문제를 해소한다(실기기 실측).
  const candidateCooldownUntilRef = useRef<Map<string, number>>(new Map());
  const lastWsBaseUrlRef = useRef(wsBaseUrl);
  // T3-C (2026-07-18): 직전 guide JSON 메시지의 event_id를 임시 저장해, 이어 도착하는
  // 바이너리 WAV 프레임이 STT 응답("stt-")인지 인지 안내("event-")인지 구분한다.
  const pendingGuideEventIdRef = useRef<string | null>(null);
  // 2026-07-19: 바이너리 WAV에 넘길 해석된 우선순위(JSON guide에서 계산).
  const pendingGuidePriorityRef = useRef<GuidePriority>(GUIDE_PRIORITY.OTHER);
  // 2026-07-21: Near track당 클립 1회.
  const nearClipPlayedTracksRef = useRef<Set<string>>(new Set());
  // transport=binary인데 WAV가 안 오면 단말 TTS로 폴백(무음 방지).
  const guideBinaryFallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 폴백 TTS가 이미 재생을 맡은 event_id. 해당 이벤트의 늦은 WAV는 중복 재생하지 않는다.
  const fallbackOwnedGuideEventsRef = useRef<Set<string>>(new Set());
  const GUIDE_BINARY_FALLBACK_MS = 1200;
  // onclose/AppState 타이머가 항상 최신 connect를 호출하도록 한다.
  const connectRef = useRef<() => void>(() => {});

  /**
   * T3-C (2026-07-18): STT 상호작용 안전 상한 타이머를 설정한다.
   * CameraView.tsx에서 STT 녹음 시작 시 직접 audioEngine.setSttActive(true)를 호출하며,
   * 이 훅에서는 STT 응답 수신 후 최대 timeoutMs까지의 백스톱만 관리한다.
   */
  const scheduleSttSafetyRelease = useCallback(
    (timeoutMs: number = STT_INTERACTION_TIMEOUT_MS) => {
      if (sttSafetyReleaseTimerRef.current) {
        clearTimeout(sttSafetyReleaseTimerRef.current);
        sttSafetyReleaseTimerRef.current = null;
      }
      sttSafetyReleaseTimerRef.current = setTimeout(() => {
        console.log("[WS] STT 안전 상한 타이머 - audioEngine STT 상태 강제 해제");
        audioEngine.setSttActive(false);
        sttSafetyReleaseTimerRef.current = null;
      }, timeoutMs);
    },
    [],
  );

  const clearSttSafetyRelease = useCallback(() => {
    if (sttSafetyReleaseTimerRef.current) {
      clearTimeout(sttSafetyReleaseTimerRef.current);
      sttSafetyReleaseTimerRef.current = null;
    }
  }, []);

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
    const nowTs = Date.now();
    // 💡 [면접 대비 주석] 미응답 probe TTL 스윕 (2026-07-28).
    // 이 Map은 ack에서만 delete되고 그 밖에는 clearNetworkProbe()(연결 교체·정리)에서만
    // 비워졌다. 재연결 루프가 있던 동안에는 초당 1.6회 연결이 재수립되며 자동으로
    // 비워져 문제가 드러나지 않았으나, 루프를 고쳐 연결이 몇 시간 유지되기 시작하자
    // ack가 유실된 probe가 초당 1개씩 무한 누적되는 경로가 됐다.
    // probe 주기(기본 1s)와 RTT를 감안해 TTL을 넘긴 항목은 버린다.
    for (const [id, sentAt] of pendingNetworkProbes.current) {
      if (nowTs - sentAt > NETWORK_PROBE_TTL_MS) {
        pendingNetworkProbes.current.delete(id);
      }
    }
    pendingNetworkProbes.current.set(probeId, nowTs);
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
    if (!deviceId || !token) {
      console.warn("[WS] 단말 식별자 또는 인증 토큰이 없어 연결을 중단합니다.");
      setStatus("fallback");
      return;
    }
    const currentState = wsRef.current?.readyState;
    if (currentState === WebSocket.OPEN || currentState === WebSocket.CONNECTING) return;

    // wsBaseUrl(수송 토글)이 바뀐 경우에만 후보를 재생성한다.
    // 매 재연결마다 재생성하면 welcome에서 승격한 Tailscale 우선순위가 사라진다.
    if (lastWsBaseUrlRef.current !== wsBaseUrl) {
      lastWsBaseUrlRef.current = wsBaseUrl;
      wsUrlCandidatesRef.current = expandWsUrlCandidates(wsBaseUrl);
      wsUrlIndexRef.current = 0;
    }
    const candidates = wsUrlCandidatesRef.current;
    // 2026-07-18: 쿨다운 중인(최근 핸드셰이크 실패) 후보는 건너뛰고, 남은 후보들 안에서만
    // 순환한다. 전부 쿨다운 중이면(모두 최근 실패) 어쩔 수 없이 원래 순환으로 되돌아간다 -
    // 재시도를 완전히 멈추지 않기 위한 안전장치.
    const now = Date.now();
    const availableIndices = candidates
      .map((_, i) => i)
      .filter((i) => {
        const until = candidateCooldownUntilRef.current.get(candidates[i]);
        return until === undefined || until <= now;
      });
    const pool = availableIndices.length > 0 ? availableIndices : candidates.map((_, i) => i);
    if (pool.length > 1) {
      wsUrlIndexRef.current = pool[reconnectCount.current % pool.length];
    } else {
      wsUrlIndexRef.current = pool[0] ?? 0;
    }
    const selectedBase = candidates[wsUrlIndexRef.current] ?? wsBaseUrl;
    const wsUrl = `${selectedBase}?device_id=${deviceId}`;
    console.log(
      `[WS] 연결 시도 주소: ${wsUrl}` +
        (candidates.length > 1
          ? ` (후보 ${wsUrlIndexRef.current + 1}/${candidates.length})`
          : ""),
    );
    const ws = new WebSocket(wsUrl);
    // 이 후보로 welcome(핸드셰이크 성공)까지 도달했는지 추적한다. onclose에서 false면
    // "이 후보가 연결 자체에 실패했다"로 보고 쿨다운을 건다(예: Tailscale 미도달망).
    let receivedWelcome = false;
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
      // 최초 수신 시각을 연결 시점으로 초기화(초기값 0이면 첫 프레임 전 타임아웃 오탐).
      lastServerHeartbeatTsRef.current = Date.now();
      heartbeatTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          // 단말 -> 서버 heartbeat_ack 유도용 heartbeat 송신 유지(서버 타임아웃 방지).
          ws.send(JSON.stringify({ type: "heartbeat", ts: Date.now() }));
        }
        // 서버 -> 단말 heartbeat 수신 감지: half-open(서버가 보내지만 단말에 안 도착)
        // 또는 서버 다운 시 lastServerHeartbeatTsRef가 갱신되지 않는다. 15초(서버 5초
        // 간격의 3회분) 이상 미수신 시 능동 종료하여 onclose를 강제 발화시킨다.
        const sinceLastHeartbeat = Date.now() - lastServerHeartbeatTsRef.current;
        if (sinceLastHeartbeat > SERVER_HEARTBEAT_TIMEOUT_MS) {
          console.warn(
            `[WS] 서버 heartbeat 타임아웃(${sinceLastHeartbeat}ms) - 능동 종료 후 재연결`,
          );
          try {
            ws.close();
          } catch {
            // close 예외는 onclose 경쟁/이미 닫힌 소켓. 무시하고 onclose 경로에 맡김.
          }
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
      // T3-C (2026-07-18): audioEngine 우선순위 조정자에 STT/인지 구분을 전달한다.
      const playIncomingGuideBytes = (buf: ArrayBuffer) => {
        if (guideBinaryFallbackTimerRef.current) {
          clearTimeout(guideBinaryFallbackTimerRef.current);
          guideBinaryFallbackTimerRef.current = null;
        }
        const pendingEventId = pendingGuideEventIdRef.current;
        const isStt = String(pendingEventId ?? "").startsWith("stt-");
        const priority = pendingGuidePriorityRef.current;
        pendingGuideEventIdRef.current = null;
        if (pendingEventId && fallbackOwnedGuideEventsRef.current.delete(pendingEventId)) {
          console.warn(
            `[WS] 폴백 재생 중 늦은 guide binary 폐기: event_id=${pendingEventId}, bytes=${buf.byteLength}`,
          );
          return;
        }
        console.log(
          `[Cognitive] guide 오디오 바이너리 수신: bytes=${buf.byteLength}, isStt=${isStt}, priority=${priority}`,
        );
        void audioEngine.playGuideAudioBytes(new Uint8Array(buf), priority, () => {
          if (isStt) {
            audioEngine.setSttActive(false);
            clearSttSafetyRelease();
          }
        });
      };

      if (event.data instanceof ArrayBuffer) {
        playIncomingGuideBytes(event.data);
        return;
      }
      // 일부 RN/폴리필은 Blob으로 올 수 있다 - ArrayBuffer로 변환 후 동일 경로.
      if (typeof Blob !== "undefined" && event.data instanceof Blob) {
        void (event.data as Blob).arrayBuffer().then((buf) => {
          if (wsRef.current !== ws) return;
          playIncomingGuideBytes(buf);
        });
        return;
      }

      try {
        const data: WSMessage = JSON.parse(event.data);

        // 서버 생존 신호: 모든 JSON 메시지 수신 시 갱신. WS가 죽으면 어떤 메시지도
        // 안 오므로 CameraView가 이 값을 기반으로 타임아웃을 판정할 수 있다.
        // (heartbeat 분기에서도 별도 갱신하지만, 여기서 모든 타입을 통합 처리한다.)
        setLastServerMessageTs(Date.now());

        if (data.type === "welcome") {
          receivedWelcome = true;
          setLastMessage(data);
          // 연결됨은 auth_ok에서만 표기한다. welcome 직후 auth 전이면 UI가
          // 연결됨↔연결중으로 깜빡이고, TFLite 로드로 hello가 늦으면 인증 타임아웃과
          // 겹쳐 상태가 더 흔들린다(2026-07-24 Android 실측).
          setStatus((prev) => (prev === "fallback" ? prev : "connecting"));
          // 성공한 후보를 다음 재연결의 1순위로 고정한다.
          const working = wsUrlCandidatesRef.current[wsUrlIndexRef.current];
          if (working) {
            candidateCooldownUntilRef.current.delete(working);
          }
          if (working && wsUrlIndexRef.current > 0) {
            wsUrlCandidatesRef.current = [
              working,
              ...wsUrlCandidatesRef.current.filter((url) => url !== working),
            ];
            wsUrlIndexRef.current = 0;
          }
          console.log(`[WS] welcome 수신, 인증 대기: session=${data.session_id}`);
        } else if (data.type === "auth_ok") {
          setStatus("connected");
          reconnectCount.current = 0;
          console.log(`[WS] 연결 성공(auth_ok), device_id=${data.device_id ?? deviceId}`);
          // 폴백 모드 고지 이후의 복구는 사용자에게 반드시 알린다. 사용자는 화면을
          // 볼 수 없으므로 음성 고지가 유일한 상태 전달 수단이다(Mitos 로드맵).
          if (fallbackAnnouncedRef.current) {
            fallbackAnnouncedRef.current = false;
            audioEngine.speakFallback("서버 연결이 복구되었습니다. 상세 안내를 다시 시작합니다.");
          }
        } else if (data.type === "heartbeat") {
          // 서버 생존 신호: half-open 감지용 수신 시각 갱신.
          lastServerHeartbeatTsRef.current = Date.now();
          setLastServerMessageTs(Date.now());
          ws.send(
            JSON.stringify({ type: "heartbeat_ack", ts: Date.now() }),
          );
        } else if (data.type === "network_probe_ack") {
          recordNetworkProbeAck(data.probe_id);
        } else if (data.type === "ack") {
          // 서버가 ACK를 반환하면 해당 프레임을 in-flight 추적에서 해제한다 (2026-07-17, P0).
          // 이 해제로 다음 프레임 송신이 허용된다(canSendFrame 게이트 통과).
          const ackKey = `${data.event_id ?? ""}:${data.frame_id ?? ""}`;
          pendingFrames.current.delete(ackKey);
          setInFlightFrameCount(pendingFrames.current.size);
          // skipped_decode=true 는 YOLO/큐만 드롭한 것. 콘솔 Live Feed용 송신은
          // 유지해야 하므로 busy 백프레셔를 적용하지 않는다(2026-07-24).
          if (data.server_busy === true && data.skipped_decode !== true) {
            const suggest =
              typeof data.suggest_reflex_interval_ms === "number"
                ? data.suggest_reflex_interval_ms
                : undefined;
            onServerLoadRef.current?.({ busy: true, suggestIntervalMs: suggest });
          }
        } else if (data.type === "reflex_alert") {
          setLastMessage(data);
          // 채널 분기 (2026-07-21):
          // - Mid/Low: 매 반사 클립.
          // - Near 긴급: track당 클립 1회(event_state=enter 또는 해당 track 첫 알림).
          //   서버 enter 누락·억제 후 update만 와도 행동 단서가 나가게 한다.
          const panning = typeof data.panning === "number" ? data.panning : 0.0;
          const beepInterval = typeof data.beep_interval_ms === "number" ? data.beep_interval_ms : 250;
          const hapticPattern = typeof data.haptic_pattern === "string" ? data.haptic_pattern : "double";
          const isUrgent = beepInterval <= 100;
          const trackKey = String(data.track_id ?? data.alert_id ?? "unknown");
          const isNearEnter = data.event_state === "enter";
          const trackNeedsClip = !nearClipPlayedTracksRef.current.has(trackKey);
          const playEnterClip =
            isUrgent && Boolean(data.clip) && (isNearEnter || trackNeedsClip);
          const playMidClip = Boolean(data.clip) && !isUrgent;
          const channel = playEnterClip
            ? "enter-clip+beep"
            : playMidClip
              ? "voice+beep"
              : "beep-only";

          if (!audioEngine.isGuidePlaying) {
            console.log(
              `[LocalReflex][WS] 서버 반사 알림: id=${data.alert_id}, panning=${panning}, interval=${beepInterval}ms, pattern=${hapticPattern}, channel=${channel}, event_state=${data.event_state ?? "-"}, track=${trackKey}`,
            );
          }
          audioEngine.playBeep(panning, beepInterval);
          hapticEngine.trigger(hapticPattern, { allowDuringStt: true });
          if (playEnterClip || playMidClip) {
            if (playEnterClip) {
              // 2026-07-28: reflex_clear가 유실되면 이 Set이 무한히 커진다(track마다 1개).
              // 메모리 자체는 작지만 재사용된 track_id의 클립이 잘못 억제될 수 있어
              // 상한을 두고 가장 오래된 항목부터 버린다(Set은 삽입 순서를 유지한다).
              nearClipPlayedTracksRef.current.add(trackKey);
              while (nearClipPlayedTracksRef.current.size > NEAR_CLIP_TRACK_LIMIT) {
                const oldest = nearClipPlayedTracksRef.current.values().next().value;
                if (oldest === undefined) break;
                nearClipPlayedTracksRef.current.delete(oldest);
              }
            }
            void audioEngine.playReflexClip(data.clip as string);
          }
        } else if (data.type === "reflex_clear") {
          setLastMessage(data);
          console.log(
            `[LocalReflex][WS] 서버 반사 해제: alert_id=${data.alert_id}, track_id=${data.track_id ?? "-"}, reason=${data.reason ?? "-"}`,
          );
          const clearKey = String(data.track_id ?? data.alert_id ?? "");
          if (clearKey) {
            nearClipPlayedTracksRef.current.delete(clearKey);
          } else {
            nearClipPlayedTracksRef.current.clear();
          }
          audioEngine.stopBeep();
          hapticEngine.stopContinuous({ respectMinimum: true });
        } else if (data.type === "guide") {
          // 인지 경로 가이드 음성은 onmessage에서 직접 재생한다(React 상태를 경유하지 않음).
          // [2026-07-09 변경] 서버가 guide 오디오를 더 이상 audio_mp3_b64(base64 문자열)로
          // JSON에 싣지 않고, 이 메시지 직후 바이너리 프레임으로 원본 WAV 바이트를 보낸다
          // (transport:"binary"). 실제 재생은 위 ArrayBuffer 분기에서 이어서 처리한다.
          // transport가 "binary"가 아니면(서버 TTS 실패) 즉시 단말 TTS로 폴백한다.
          console.log(
            `[Cognitive] guide 수신: text="${data.guidance_text}", ` +
              `dir=${data.clock_direction ?? "-"}, dist=${data.distance_class ?? "-"}, obj=${data.object_ko ?? "-"}, ` +
              `transport=${data.transport}`,
          );

          // 2026-07-19: STT(길찾아줘/물어볼게) > Near > 12시 MED > 기타.
          // STT 구간에는 Near 비프/햅틱/위험 음성도 억제한다.
          const isStt = String(data.event_id ?? "").startsWith("stt-");
          pendingGuideEventIdRef.current = data.event_id ?? null;
          const priority = resolveGuidePriority({
            isStt,
            clockDirection: data.clock_direction,
            distanceClass: data.distance_class,
          });
          pendingGuidePriorityRef.current = priority;
          console.log(
            `[Cognitive] guide priority=${priority} (isStt=${isStt}, dir=${data.clock_direction ?? "-"}, dist=${data.distance_class ?? "-"})`,
          );

          if (isStt) {
            // STT 응답 수신: 인지 안내만 STT 우선. Near 비프/햅틱은 유지(2026-07-20).
            audioEngine.setSttActive(true);
            const guideText = data.guidance_text ?? "";
            const serverDurationMs =
              typeof data.duration_ms === "number" && data.duration_ms > 0 ? data.duration_ms : 0;
            const textEstimateMs = Math.max(guideText.length * 180, 2000);
            const estimatedMs = Math.max(serverDurationMs, textEstimateMs);
            scheduleSttSafetyRelease(estimatedMs + 1200);
          }

          if (data.transport !== "binary" && data.guidance_text) {
            console.log("[WS] -> speakFallback(단말 TTS) 경로 진입");
            audioEngine.speakFallback(
              normalizeTextForSpeech(data.guidance_text),
              priority,
              () => {
                if (isStt) {
                  audioEngine.setSttActive(false);
                  clearSttSafetyRelease();
                }
              },
            );
          } else if (data.transport === "binary" && data.guidance_text) {
            // 서버는 guide JSON 직후 WAV를 보내지만, 유실·지연 시 무음이 된다.
            // 1.2s 내 바이너리가 없으면 단말 TTS로 동일 문구를 재생한다.
            if (guideBinaryFallbackTimerRef.current) {
              clearTimeout(guideBinaryFallbackTimerRef.current);
            }
            const fallbackText = data.guidance_text;
            const fallbackSpeechText = normalizeTextForSpeech(fallbackText);
            const fallbackPriority = priority;
            const fallbackIsStt = isStt;
            const fallbackEventId = data.event_id ?? "";
            guideBinaryFallbackTimerRef.current = setTimeout(() => {
              guideBinaryFallbackTimerRef.current = null;
              if (fallbackEventId) {
                fallbackOwnedGuideEventsRef.current.add(fallbackEventId);
              }
              console.warn(
                `[WS] guide binary 미도착(${GUIDE_BINARY_FALLBACK_MS}ms) - speakFallback: "${fallbackText}"`,
              );
              audioEngine.speakFallback(fallbackSpeechText, fallbackPriority, () => {
                if (fallbackIsStt) {
                  audioEngine.setSttActive(false);
                  clearSttSafetyRelease();
                }
              });
            }, GUIDE_BINARY_FALLBACK_MS);
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
        } else if (data.type === "dial_action") {
          const phoneNumber = String(data.phone_number ?? "").replace(/\D/g, "");
          const contactName = data.contact_name ?? "";
          const delayMs =
            typeof data.delay_ms === "number" && data.delay_ms > 0
              ? data.delay_ms
              : 1500;
          console.log(
            `[WS] dial_action 수신: contact=${contactName}, phone=${phoneNumber}, delayMs=${delayMs}`,
          );
          if (phoneNumber) {
            setTimeout(() => {
              void placePhoneCall(phoneNumber, contactName).catch((error: unknown) => {
                console.warn(`[WS] dial_action 실패: ${String(error)}`);
              });
            }, delayMs);
          }
          setLastMessage(data);
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
      if (guideBinaryFallbackTimerRef.current) {
        clearTimeout(guideBinaryFallbackTimerRef.current);
        guideBinaryFallbackTimerRef.current = null;
      }
      pendingGuideEventIdRef.current = null;
      fallbackOwnedGuideEventsRef.current.clear();
      const closeCode = typeof event?.code === "number" ? event.code : -1;
      const closeReason = typeof event?.reason === "string" ? event.reason : "";
      console.log(`[WS] 연결 종료 code=${closeCode} reason=${closeReason}`);

      // 2026-07-18: welcome을 못 받고 끊겼다 = 이 후보가 연결 자체에 실패했다.
      // 다음 재연결 순환에서 쿨다운이 끝날 때까지 건너뛴다(Tailscale 등 도달 불가 후보를
      // 매번 10초씩 재시도해 LAN 폴백을 지연시키던 문제 해소, 실기기 실측).
      if (!receivedWelcome) {
        const failedBase = wsUrlCandidatesRef.current[wsUrlIndexRef.current];
        if (failedBase) {
          candidateCooldownUntilRef.current.set(failedBase, Date.now() + CANDIDATE_COOLDOWN_MS);
          console.log(`[WS] 후보 쿨다운 설정: ${failedBase} (${CANDIDATE_COOLDOWN_MS}ms)`);
        }
      }

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
      reconnectTimer.current = setTimeout(() => connectRef.current(), backoffMs);
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
      console.warn("[WS] 오류 (재연결 시도 중):", error);
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

  // 💡 [면접 대비 주석] ACK 기반 in-flight 프레임 제한 (2026-07-17, P0).
  // 느린 서버/망에서 단말이 ACK 없이 프레임을 무한정 밀어 넣으면 송신 버퍼·서버 큐·
  // 콘솔 relay에 과거 프레임이 누적된다. ACK를 받은 프레임만 in-flight 슬롯에서 해제해
  // 다음 프레임을 허용한다(역압력). 초과 시 메타와 binary를 "한 쌍으로 같이" 드롭한다 -
  // 서버 pending_binary_meta가 단일 슬롯이므로, 메타만 또는 binary만 드롭하면 짝이 어긋나
  // 다음 프레임이 잘못 매칭되는 버그를 방지한다.
  const [inFlightFrameCount, setInFlightFrameCount] = useState(0);

  const sendDetectionFrame = useCallback(
    (
      meta: { type: string; payload: { event_id?: string; frame_id?: number; [k: string]: unknown } },
      jpegBytes: Uint8Array,
    ): boolean => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return false;

      // 오래된 stale 슬롯 정리(ACK 유실/네트워크 끊김 후 잔류 방지). 2초 이상 된 항목은 제거.
      const now = Date.now();
      for (const [key, ts] of pendingFrames.current) {
        if (now - ts > 2000) pendingFrames.current.delete(key);
      }

      if (pendingFrames.current.size >= MAX_IN_FLIGHT_FRAMES) {
        // in-flight 상한 초과: 메타 + binary를 한 쌍으로 같이 드롭(서버 매칭 오류 방지).
        return false;
      }

      const event_id = meta.payload.event_id ?? "";
      const frame_id = meta.payload.frame_id ?? 0;
      const key = `${event_id}:${frame_id}`;
      pendingFrames.current.set(key, now);
      setInFlightFrameCount(pendingFrames.current.size);

      // 메타 JSON 먼저, 직후 binary JPEG (서버 pending_binary_meta 매칭 순서).
      try {
        ws.send(JSON.stringify(meta));
      } catch (error) {
        pendingFrames.current.delete(key);
        setInFlightFrameCount(pendingFrames.current.size);
        console.warn("[WS] detection 메타 전송 스킵(소켓 상태 변경):", error);
        return false;
      }
      try {
        ws.send(jpegBytes);
      } catch (error) {
        console.warn("[WS] detection binary 전송 스킵(소켓 상태 변경):", error);
      }
      return true;
    },
    [],
  );

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    // 수송 모드(WiFi/USB) 또는 wsBaseUrl 변경 시에만 소켓을 교체한다.
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
    lastWsBaseUrlRef.current = "";
    connectRef.current();
    return () => {
      clearHeartbeat();
      clearNetworkProbe();
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }

      // 오디오 및 진동 피드백 완전 종료
      audioEngine.stopBeep();
      hapticEngine.stopContinuous();

      if (sttSafetyReleaseTimerRef.current) {
        clearTimeout(sttSafetyReleaseTimerRef.current);
        sttSafetyReleaseTimerRef.current = null;
      }

      if (guideBinaryFallbackTimerRef.current) {
        clearTimeout(guideBinaryFallbackTimerRef.current);
        guideBinaryFallbackTimerRef.current = null;
      }
      pendingGuideEventIdRef.current = null;
      fallbackOwnedGuideEventsRef.current.clear();

      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- connect는 ref로 최신 유지, URL 변경만 재연결
  }, [wsBaseUrl, clearHeartbeat, clearNetworkProbe]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      const previousState = appStateRef.current;
      appStateRef.current = nextState;

      // inactive(알림/TTS/제어센터 등 짧은 인터럽트)에서는 소켓을 유지한다.
      // Android에서 온보딩 TTS·오디오 세션 전환이 inactive로 잡혀 WS를 끊고
      // 연결됨↔연결중이 깜빡이던 실측(2026-07-24). background일 때만 정리.
      if (nextState === "background") {
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

      if (nextState === "active" && previousState === "background") {
        reconnectCount.current = 0;
        fallbackAnnouncedRef.current = false;
        connectRef.current();
      }
    });

    return () => subscription.remove();
  }, [clearHeartbeat, clearNetworkProbe]);

  return {
    status,
    send,
    sendBinary,
    sendDetectionFrame,
    inFlightFrameCount,
    lastMessage,
    navRoute,
    networkRttMs,
    networkRttAvgMs,
    lastServerMessageTs,
  };
}
