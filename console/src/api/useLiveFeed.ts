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

export interface ConsoleGuideAudioEvent {
  event_id: string;
  device_id: string;
  audio_codec: string;
  duration_ms: number;
  guidance_text: string;
  source?: string;
  ts: number;
  // 수신 시각(프론트 기준). 재생 UI에서 지연 시각화에 사용.
  received_at: number;
  // 오디오 Blob URL. 컴포넌트에서 <audio src> 또는 new Audio().play()로 재생.
  // null이면 합성 실패/미수신. 컴포넌트는 null일 때 텍스트만 표시.
  audio_url: string | null;
}

export interface ConsoleReflexAlertEvent {
  event_id: string;
  alert_id: string;
  device_id: string;
  direction?: string;
  risk_level?: string;
  // 단말 번들 클립 파일명(예: "high_front.wav"). 콘솔 public/reflex_clips/에
  // 동일 파일명으로 정적 복사해 두었으므로 그대로 URL로 매핑해 재생한다.
  clip?: string;
  haptic?: any;
  panning?: any;
  distance?: any;
  beep_interval_ms?: number;
  haptic_pattern?: { intensity?: string; duration_ms?: number; pattern?: string };
  track_id?: number;
  class_name?: string;
  hit_count?: number;
  distance_band?: string;
  alert_source?: string;
  event_state?: string;
  estimated_distance_m?: number;
  policy_version?: string;
  ts: number;
  received_at: number;
}

export function useLiveFeed() {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [latestDetections, setLatestDetections] = useState<any[]>([]);
  const [latencyEvents, setLatencyEvents] = useState<LiveLatencyEvent[]>([]);
  const [guidanceLogEvents, setGuidanceLogEvents] = useState<DetectionGuidanceLogRow[]>([]);
  const [lastGps, setLastGps] = useState<{ lat: number; lon: number; heading: number } | null>(
    null,
  );
  // 2026-07-19: 서버가 단말과 동일한 guide 오디오(WAV)를 콘솔로도 미러링한다.
  // 서버는 console_guide_audio JSON을 먼저 보내고, 직후 원본 WAV 바이너리를 이어 보낸다.
  // 단말 useWebSocket.ts의 pendingGuideEventIdRef와 동일한 상태 머신 패턴.
  const [guideAudioEvent, setGuideAudioEvent] = useState<ConsoleGuideAudioEvent | null>(null);
  // 2026-07-19: 반사 알림(비프+햅틱) 콘솔 미러링. 단말이 듣는 비프음을 콘솔에서도
  // 동일/유사하게 재생하고, 햅틱은 청각 재현 불가하므로 시각 펄스로 표현한다.
  const [reflexAlertEvent, setReflexAlertEvent] = useState<ConsoleReflexAlertEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const prevUrlRef = useRef<string | null>(null);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingBlobRef = useRef<Blob | null>(null);
  const rafRef = useRef<number | null>(null);
  // 직전 console_guide_audio JSON 메타데이터. 다음 ArrayBuffer(오디오)와 짝짓는다.
  const pendingGuideAudioRef = useRef<Omit<ConsoleGuideAudioEvent, "audio_url" | "received_at"> | null>(null);
  // 오디오 Blob URL 정리용. 컴포넌트가 해제되거나 새 이벤트가 오면 이전 URL을 revoke한다.
  const prevAudioUrlRef = useRef<string | null>(null);

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
          // 직전에 console_guide_audio JSON을 받은 적이 있으면 이 바이너리는
          // 단말과 동일한 guide 오디오(WAV)다. image/jpeg로 강제 해석하지 않고
          // 오디오 Blob으로 래핑해 컴포넌트에 넘긴다(2026-07-19).
          if (pendingGuideAudioRef.current) {
            const meta = pendingGuideAudioRef.current;
            pendingGuideAudioRef.current = null;
            const audioBlob = new Blob([event.data], { type: `audio/${meta.audio_codec || "wav"}` });
            const audioUrl = URL.createObjectURL(audioBlob);
            if (prevAudioUrlRef.current) {
              URL.revokeObjectURL(prevAudioUrlRef.current);
            }
            prevAudioUrlRef.current = audioUrl;
            setGuideAudioEvent({
              ...meta,
              received_at: Date.now(),
              audio_url: audioUrl,
            });
            return;
          }
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
          } else if (data.type === "console_guide_audio") {
            // 직후 도착할 ArrayBuffer(WAV)와 짝을 이룰 메타를 보관한다.
            // 바이너리가 오지 않거나 순서가 어긋나면 타임아웃으로 폐기한다.
            pendingGuideAudioRef.current = {
              event_id: data.event_id,
              device_id: data.device_id,
              audio_codec: data.audio_codec ?? "wav",
              duration_ms: data.duration_ms ?? 0,
              guidance_text: data.guidance_text ?? "",
              source: data.source,
              ts: data.ts ?? Date.now(),
            };
            // 가드레일: 5초 내 바이너리가 오지 않으면 상태 폐기(정체 방지).
            setTimeout(() => {
              if (pendingGuideAudioRef.current && pendingGuideAudioRef.current.event_id === data.event_id) {
                pendingGuideAudioRef.current = null;
              }
            }, 5000);
          } else if (data.type === "reflex_alert") {
            // 2026-07-19: 단말이 받는 반사 알림을 콘솔에도 미러링.
            // 비프음은 clip 필드 파일명으로 console/public/reflex_clips/에서 재생,
            // 햅틱은 청각 재현이 불가하므로 컴포넌트에서 시각 펄스로 표현한다.
            setReflexAlertEvent({
              event_id: data.event_id,
              alert_id: data.alert_id,
              device_id: data.device_id,
              direction: data.direction,
              risk_level: data.risk_level,
              clip: data.clip,
              haptic: data.haptic,
              panning: data.panning,
              distance: data.distance,
              beep_interval_ms: data.beep_interval_ms,
              haptic_pattern: data.haptic_pattern,
              track_id: data.track_id,
              class_name: data.class_name,
              hit_count: data.hit_count,
              distance_band: data.distance_band,
              alert_source: data.alert_source,
              event_state: data.event_state,
              estimated_distance_m: data.estimated_distance_m,
              policy_version: data.policy_version,
              ts: data.ts ?? Date.now(),
              received_at: Date.now(),
            });
          } else if (data.type === "reflex_clear") {
            setReflexAlertEvent(null);
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
      if (prevAudioUrlRef.current) {
        URL.revokeObjectURL(prevAudioUrlRef.current);
        prevAudioUrlRef.current = null;
      }
      pendingGuideAudioRef.current = null;
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
    guideAudioEvent,
    reflexAlertEvent,
  };
}
