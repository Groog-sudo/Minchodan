import { useEffect, useState, useRef } from "react";
import type { DetectionGuidanceLogRow, LiveLatencyEvent } from "../types/monitor";
import { resolveApiBaseUrl } from "../config/network";

const API_BASE_URL =
  resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
const WS_LIVE_FEED_URL = API_BASE_URL.replace(/^http/, "ws") + "/ws/console/live-feed";
const MAX_LIVE_LATENCY_EVENTS = 30;
const MAX_LIVE_LOG_ROWS = 50;

export function useLiveFeed() {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [latestDetections, setLatestDetections] = useState<any[]>([]);
  const [latencyEvents, setLatencyEvents] = useState<LiveLatencyEvent[]>([]);
  const [guidanceLogEvents, setGuidanceLogEvents] = useState<DetectionGuidanceLogRow[]>([]);
  const [lastGps, setLastGps] = useState<{ lat: number; lon: number; heading: number } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const prevUrlRef = useRef<string | null>(null);
  const clearTimerRef = useRef<any | null>(null);
  const reconnectTimerRef = useRef<any | null>(null);

  useEffect(() => {
    let active = true;
    let wsInstance: WebSocket | null = null;

    function connect() {
      if (!active) return;

      const ws = new WebSocket(WS_LIVE_FEED_URL);
      wsRef.current = ws;
      wsInstance = ws;

      ws.binaryType = "blob";

      ws.onopen = () => {
        if (wsRef.current !== ws) return;
        if (!active) {
          ws.close();
          return;
        }
        setConnected(true);
      };

      ws.onmessage = (event) => {
        if (wsRef.current !== ws) return;
        if (!active) return;
        // 💡 이 디버그 로그 1줄 추가
        console.log("[WS LIVE FEED 수신]:", typeof event.data, event.data);

        // if (event.data instanceof Blob) {
        //   const newUrl = URL.createObjectURL(event.data);
        //   setImageUrl(newUrl);

        //   // Revoke the previous object URL to prevent memory leaks
        //   if (prevUrlRef.current) {
        //     URL.revokeObjectURL(prevUrlRef.current);
        //   }
        //   prevUrlRef.current = newUrl;
        let blobData: Blob | null = null;
        if (event.data instanceof Blob) {
          blobData = event.data;
        } else if (event.data instanceof ArrayBuffer) {
          blobData = new Blob([event.data], { type: "image/jpeg" });
        }

        if (blobData) {
          const newUrl = URL.createObjectURL(blobData);
          setImageUrl(newUrl);

          if (prevUrlRef.current) {
            URL.revokeObjectURL(prevUrlRef.current);
          }
          prevUrlRef.current = newUrl;


          // Reset clear timer
          if (clearTimerRef.current) {
            clearTimeout(clearTimerRef.current);
          }
          // Clear detections if no new frame in 2 seconds
          clearTimerRef.current = setTimeout(() => {
            if (active) {
              setLatestDetections([]);
            }
          }, 2000);

        } else if (typeof event.data === "string") {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "server_detection") {
              setLatestDetections(data.detections || []);
            } else if (data.type === "latency_event") {
              setLatencyEvents((prev) =>
                [data as LiveLatencyEvent, ...prev].slice(0, MAX_LIVE_LATENCY_EVENTS),
              );
            } else if (data.type === "guidance_log_event" && data.row) {
              setGuidanceLogEvents((prev) =>
                [data.row as DetectionGuidanceLogRow, ...prev].slice(0, MAX_LIVE_LOG_ROWS),
              );
            } else if (data.type === "realtime_gps" && data.lat != null && data.lon != null) {
              // 앱에서 서버로 전달된 실기기 GPS 좌표를 콘솔에서 수신해 지도 iframe에 주입한다.
              setLastGps({ lat: data.lat, lon: data.lon, heading: data.heading ?? 0 });
            }
          } catch (e) {
            console.error("Failed to parse websocket message", e);
          }
        }
      };

      ws.onclose = () => {
        if (wsRef.current !== ws) return;
        if (active) {
          wsRef.current = null;
          wsInstance = null;
          setConnected(false);
          setLatestDetections([]);
          // latencyEvents는 재연결 후에도 최근 이력으로 유지한다 (bbox 오버레이와 달리
          // "현재 프레임" 개념이 없어 끊겼다고 비울 이유가 없다).
          // Reconnect in 3 seconds
          reconnectTimerRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        if (wsRef.current !== ws) return;
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
        }
      };
    }

    connect();

    return () => {
      active = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsInstance) {
        // 카메라 렌더링을 위한 디버깅 코드
        // console.log("[WS CLOSE 디버그] clean-up에 의해 소켓이 닫힙니다.");
        wsInstance.close();
      }
      if (prevUrlRef.current) {
        URL.revokeObjectURL(prevUrlRef.current);
      }
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current);
      }
    };
  }, []);

  return { imageUrl, latestDetections, connected, latencyEvents, guidanceLogEvents, lastGps };
}
