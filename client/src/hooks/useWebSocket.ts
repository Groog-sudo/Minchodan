/**
 * WebSocket 연결 생명주기 관리 훅.
 * 연결 수립, hello/welcome 핸드셰이크, 하트비트, 재연결, 정리를 담당.
 * API 명세서 v0.2.0 기준 heartbeat/heartbeat_ack 프로토콜 사용.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "react-native";

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

    ws.onmessage = (event: WebSocketMessageEvent) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        setLastMessage(data);

        if (data.type === "welcome") {
          setStatus("connected");
          console.log(`[WS] 연결 성공, 세션 ID: ${data.session_id}`);
        } else if (data.type === "heartbeat") {
          ws.send(
            JSON.stringify({ type: "heartbeat_ack", ts: Date.now() }),
          );
        } else if (data.type === "reflex_alert") {
          // 입체 비프음 및 햅틱 연동 실행 (docs/reflex_audio_specification.md 준수)
          const panning = typeof data.panning === "number" ? data.panning : 0.0;
          const beepInterval = typeof data.beep_interval_ms === "number" ? data.beep_interval_ms : 250;
          const hapticPattern = typeof data.haptic_pattern === "string" ? data.haptic_pattern : "double";

          console.log(`[WS] 반사 알림 수신: id=${data.alert_id}, panning=${panning}, interval=${beepInterval}ms, pattern=${hapticPattern}`);
          audioEngine.playBeep(panning, beepInterval);
          hapticEngine.trigger(hapticPattern);
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

    ws.onerror = (error: Event) => {
      console.error("[WS] 오류:", error);
    };
  }, [deviceId, token, clearHeartbeat]);



  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
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

  return { status, send, lastMessage };
}
