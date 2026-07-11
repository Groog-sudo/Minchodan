import { useCallback, useEffect, useState } from "react";
import type { DetectionGuidanceLogRow } from "../types/monitor";

// 발표/면접 포인트:
// - detection_guidance_logs 사후 이력 조회 훅입니다. 실시간 SSE(useMonitorStream)와
//   달리 REST GET 폴링으로 충분한 영역이라 EventSource를 쓰지 않습니다.
// - 서버 주소는 VITE_API_BASE_URL 환경 변수 하나로 재정의합니다 (기본 localhost:8000).
const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const LOGS_ENDPOINT = `${API_BASE_URL}/api/v1/admin/detection-logs`;
const DEFAULT_POLL_MS = 30000;

/**
 * 이벤트 프레임 이미지 URL을 만듭니다.
 * <img> 태그는 Authorization 헤더를 붙일 수 없어 SSE와 동일하게
 * 쿼리 토큰(?token=...)으로 인증합니다.
 */
export function eventFrameUrl(eventId: string, token: string): string {
  return `${API_BASE_URL}/api/v1/admin/event-frames/${encodeURIComponent(
    eventId,
  )}?${new URLSearchParams({ token }).toString()}`;
}

export function useDetectionLogs(token: string | null, pollMs = DEFAULT_POLL_MS) {
  const [rows, setRows] = useState<DetectionGuidanceLogRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await fetch(`${LOGS_ENDPOINT}?limit=50`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(`로그 조회 실패 (HTTP ${response.status})`);
      }
      const data: DetectionGuidanceLogRow[] = await response.json();
      setRows(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그 조회 중 오류");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;
    void refresh();
    const timer = setInterval(() => void refresh(), pollMs);
    return () => clearInterval(timer);
  }, [token, refresh, pollMs]);

  return { rows, error, loading, refresh };
}
