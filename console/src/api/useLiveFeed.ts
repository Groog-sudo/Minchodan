import { useEffect, useState, useRef } from "react";
import type { DetectionGuidanceLogRow, LiveLatencyEvent } from "../types/monitor";
import { resolveApiBaseUrl } from "../config/network";

const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
// Vite(/ws) 프록시를 우선 사용하고, 없으면 FastAPI 직접 연결로 폴백한다.
const WS_LIVE_FEED_URL =
  import.meta.env.VITE_WS_LIVE_FEED_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/console/live-feed`
    : API_BASE_URL.replace(/^http/, "ws") + "/ws/console/live-feed");

const MAX_LIVE_LATENCY_EVENTS = 30;
const MAX_LIVE_LOG_ROWS = 50;
const RECONNECT_MS = 1500;

export function useLiveFeed() {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [latestDetections, setLatestDetections] = useState<any[]>([]);
  const [latencyEvents, setLatencyEvents] = useState<LiveLatencyEvent[]>([]);
  const [guidanceLogEvents, setGuidanceLogEvents] = useState<DetectionGuidanceLogRow[]>([]);
  const [lastGps, setLastGps] = useState<{ lat: number; lon: number; heading: number } | null>(
    null,
  );

  const wsRef = useRef<WebSocket | null>(null);
  const prevUrlRef = useRef<string | null>(null);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingBlobRef = useRef<Blob | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    let disposed = false;
    let generation = 0;

    const revokePrevUrl = () => {
      if (prevUrlRef.current) {
        URL.revokeObjectURL(prevUrlRef.current);
        prevUrlRef.current = null;
      }
    };

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const clearIdleTimer = () => {
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current);
        clearTimerRef.current = null;
      }
    };

    const connect = () => {
      if (disposed) return;
      clearReconnectTimer();
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      pendingBlobRef.current = null;

      // 이전 소켓이 남아 있으면 세대만 올려 무효화한 뒤 닫는다.
      const prev = wsRef.current;
      if (prev) {
        wsRef.current = null;
        try {
          prev.onopen = null;
          prev.onmessage = null;
          prev.onerror = null;
          prev.onclose = null;
          prev.close();
        } catch {
          // ignore
        }
      }

      const myGen = ++generation;
      const ws = new WebSocket(WS_LIVE_FEED_URL);
      ws.binaryType = "blob";
      wsRef.current = ws;

      ws.onopen = () => {
        if (disposed || myGen !== generation || wsRef.current !== ws) {
          try {
            ws.close();
          } catch {
            // ignore
          }
          return;
        }
        setConnected(true);
      };

      ws.onmessage = (event) => {
        if (disposed || myGen !== generation || wsRef.current !== ws) return;

        let blobData: Blob | null = null;
        if (event.data instanceof Blob) {
          blobData = event.data;
        } else if (event.data instanceof ArrayBuffer) {
          blobData = new Blob([event.data], { type: "image/jpeg" });
        }

        if (blobData) {
          // 최신 프레임만 다음 페인트에 반영 (밀린 blob 드롭 → 끊김 완화)
          pendingBlobRef.current = blobData;
          if (rafRef.current == null) {
            rafRef.current = requestAnimationFrame(() => {
              rafRef.current = null;
              const latest = pendingBlobRef.current;
              pendingBlobRef.current = null;
              if (!latest || disposed || myGen !== generation || wsRef.current !== ws) return;

              const newUrl = URL.createObjectURL(latest);
              setImageUrl(newUrl);
              if (prevUrlRef.current) {
                URL.revokeObjectURL(prevUrlRef.current);
              }
              prevUrlRef.current = newUrl;

              clearIdleTimer();
              clearTimerRef.current = setTimeout(() => {
                if (!disposed && myGen === generation) {
                  setLatestDetections([]);
                }
              }, 2000);
            });
          }
          return;
        }

        if (typeof event.data !== "string") return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === "server_detection") {
            setLatestDetections(data.detections || []);
          } else if (data.type === "latency_event") {
            setLatencyEvents((prevEvents) =>
              [data as LiveLatencyEvent, ...prevEvents].slice(0, MAX_LIVE_LATENCY_EVENTS),
            );
          } else if (data.type === "guidance_log_event" && data.row) {
            setGuidanceLogEvents((prevRows) =>
              [data.row as DetectionGuidanceLogRow, ...prevRows].slice(0, MAX_LIVE_LOG_ROWS),
            );
          } else if (data.type === "realtime_gps" && data.lat != null && data.lon != null) {
            setLastGps({
              lat: data.lat,
              lon: data.lon,
              heading: data.heading ?? 0,
            });
          }
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };

      ws.onclose = () => {
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
        if (disposed || myGen !== generation) return;

        setConnected(false);
        setLatestDetections([]);
        clearReconnectTimer();
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_MS);
      };

      ws.onerror = () => {
        if (disposed || myGen !== generation || wsRef.current !== ws) return;
        // onclose에서 재연결한다.
        try {
          ws.close();
        } catch {
          // ignore
        }
      };
    };

    connect();

    return () => {
      disposed = true;
      generation += 1;
      clearReconnectTimer();
      clearIdleTimer();
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      pendingBlobRef.current = null;

      const ws = wsRef.current;
      wsRef.current = null;
      if (ws) {
        try {
          ws.onopen = null;
          ws.onmessage = null;
          ws.onerror = null;
          ws.onclose = null;
          ws.close();
        } catch {
          // ignore
        }
      }
      revokePrevUrl();
      setConnected(false);
    };
  }, []);

  return {
    imageUrl,
    latestDetections,
    connected,
    latencyEvents,
    guidanceLogEvents,
    lastGps,
  };
}
