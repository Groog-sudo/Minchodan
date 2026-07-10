/**
 * WebSocket 연결 생명주기 관리 훅.
 * 연결 수립, hello/welcome 핸드셰이크, 하트비트, 재연결, 정리를 담당.
 * API 명세서 v0.2.0 기준 heartbeat/heartbeat_ack 프로토콜 사용.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import {
  DEVICE_ID,
  HEARTBEAT_INTERVAL,
  MAX_RECONNECT,
  RECONNECT_DELAY,
  TOKEN,
  WS_URL,
} from "../config";
import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";
import type { WSMessage, WSStatus } from "../types/detection";

export interface UseWebSocketReturn {
  status: WSStatus;
  send: (data: object) => void;
  /** JPEG raw byte 프레임을 바이너리 WS 프레임으로 전송한다 (base64 미경유). */
  sendBinary: (data: Uint8Array) => void;
  lastMessage: WSMessage | null;
  /** STT 질문 상호작용(녹음~응답 수신) 구간 동안 인지 경로 가이드 음성을 뮤트한다.
   * 반사 경로(reflex_alert)는 안전 비협상 원칙에 따라 절대 뮤트하지 않는다.
   * timeoutMs를 넘기면 해당 시간 뒤 자동 해제(기본은 STT_INTERACTION_TIMEOUT_MS 안전 상한). */
  setSttInteractionActive: (active: boolean, timeoutMs?: number) => void;
}

// STT 응답이 오지 않는 예외 상황(네트워크 끊김 등)에서 인지 경로가 무한정 뮤트된 채
// 남지 않도록 하는 안전 상한(서버 STT+LLM+TTS 실측 지연이 최대 15s대인 것을 감안).
const STT_INTERACTION_TIMEOUT_MS = 20000;

export function useWebSocket(
  deviceId: string = DEVICE_ID,
  token: string = TOKEN,
): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  // STT 상호작용 중 인지 경로 뮤트 상태. ref로 관리해 onmessage 클로저 안에서도
  // 항상 최신 값을 읽는다(state였다면 connect()가 재실행되지 않는 한 stale closure).
  const sttInteractionActiveRef = useRef(false);
  const sttInteractionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${WS_URL}?device_id=${deviceId}`;
    console.log(`[WS] 연결 시도 주소: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    // guide 오디오(WAV)를 서버가 바이너리 프레임으로 보내므로(2026-07-09 도입),
    // 수신 시 Blob이 아닌 ArrayBuffer로 받아 동기적으로 다루기 쉽게 한다.
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => {
      reconnectCount.current = 0;
      ws.send(
        JSON.stringify({ type: "hello", device_id: deviceId, token }),
      );

      clearHeartbeat();
      heartbeatTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "heartbeat", ts: Date.now() }));
        }
      }, HEARTBEAT_INTERVAL);
    };

    ws.onmessage = (event: any) => {
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
          console.log(`[WS] 연결 성공, 세션 ID: ${data.session_id}`);
        } else if (data.type === "heartbeat") {
          ws.send(
            JSON.stringify({ type: "heartbeat_ack", ts: Date.now() }),
          );
        } else if (data.type === "reflex_alert") {
          setLastMessage(data);
          // 입체 비프음 및 햅틱 연동 실행 (docs/reflex_audio_specification.md 준수)
          const panning = typeof data.panning === "number" ? data.panning : 0.0;
          const beepInterval = typeof data.beep_interval_ms === "number" ? data.beep_interval_ms : 250;
          const hapticPattern = typeof data.haptic_pattern === "string" ? data.haptic_pattern : "double";

          if (!audioEngine.isGuidePlaying) {
            console.log(`[WS] 반사 알림 수신: id=${data.alert_id}, panning=${panning}, interval=${beepInterval}ms, pattern=${hapticPattern}`);
          }
          audioEngine.playBeep(panning, beepInterval);
          hapticEngine.trigger(hapticPattern);
          if (data.clip) {
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
        } else {
          setLastMessage(data);
        }
      } catch (err) {
        console.error("[WS] 메시지 파싱 오류:", err);
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      clearHeartbeat();
      console.log("[WS] 연결 종료");

      // 오디오 및 진동 피드백 즉각 종료
      audioEngine.stopBeep();
      hapticEngine.stopContinuous();

      if (reconnectCount.current < MAX_RECONNECT) {
        reconnectCount.current += 1;
        reconnectTimer.current = setTimeout(() => connect(), RECONNECT_DELAY);
      } else {
        setStatus("fallback");
        console.warn(`[WS] 재연결 시도(${MAX_RECONNECT}회) 실패로 중단.`);
      }
    };

    ws.onerror = (error: any) => {
      console.error("[WS] 오류:", error);
    };
  }, [deviceId, token, clearHeartbeat]);



  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const sendBinary = useCallback((data: Uint8Array) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // RN WebSocket은 ArrayBufferView(Uint8Array)를 바이너리 프레임으로 직접 전송한다.
      // base64 인코딩을 경유하지 않아 33% 페이로드 증가와 JS 인코딩/서버 디코딩 오버헤드를 제거한다.
      wsRef.current.send(data);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearHeartbeat();
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
  }, [connect, clearHeartbeat]);

  return { status, send, sendBinary, lastMessage, setSttInteractionActive };
}
