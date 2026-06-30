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
        } else if (data.type === "heartbeat") {
          ws.send(
            JSON.stringify({ type: "heartbeat_ack", ts: Date.now() }),
          );
        }
      } catch (err) {
        console.error("[WS] 메시지 파싱 오류:", err);
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      clearHeartbeat();

      if (reconnectCount.current < MAX_RECONNECT) {
        reconnectCount.current += 1;
        reconnectTimer.current = setTimeout(() => connect(), RECONNECT_DELAY);
      } else {
        setStatus("fallback");
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
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearHeartbeat]);

  return { status, send, lastMessage };
}
