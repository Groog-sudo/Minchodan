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
          // audio_mp3_b64(수백 KB base64 문자열)를 setLastMessage로 상태에 태우면
          // JSON.parse -> setState -> 리렌더 -> effect 체인을 다시 관통하며 JS 스레드가
          // 오디오 콜백 스케줄링과 경합해 재생이 끊기는 문제가 있었다(2026-07-09).
          if (data.audio_mp3_b64) {
            void audioEngine.playGuideAudio(data.audio_mp3_b64);
          } else if (data.guidance_text) {
            // 서버 TTS 실패/타임아웃(realtime_tts.py 3초 가드레일)으로 오디오가 빈 경우
            // 단말 내장 TTS로 대신 발화해 무음 구간을 없앤다.
            audioEngine.speakFallback(data.guidance_text);
          }
          const { audio_mp3_b64: _audio_mp3_b64, ...guideWithoutAudio } = data;
          setLastMessage(guideWithoutAudio as WSMessage);
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
