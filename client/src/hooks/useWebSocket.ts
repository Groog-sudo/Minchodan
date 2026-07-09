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
}

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
          if (data.transport !== "binary" && data.guidance_text) {
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

      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearHeartbeat]);

  return { status, send, sendBinary, lastMessage };
}
