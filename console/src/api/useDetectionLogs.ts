import { useCallback, useEffect, useState } from "react";
import type { DetectionGuidanceLogRow } from "../types/monitor";
import { forceAdminRelogin } from "./adminAuth";
import { resolveApiBaseUrl } from "../config/network";

// 발표/면접 포인트:
// - detection_guidance_logs 사후 이력 조회 훅입니다. 실시간 SSE(useMonitorStream)와
//   달리 REST GET 폴링으로 충분한 영역이라 EventSource를 쓰지 않습니다.
// - 서버 주소는 VITE_API_BASE_URL 환경 변수 하나로 재정의합니다 (기본 localhost:8000).
// - 2026-07-12: 전체 건수(수천 건 가능)를 클라이언트가 한 번에 다 받아 슬라이싱하던
//   방식에서, page/pageSize로 서버에 offset 쿼리를 보내는 진짜 서버 페이지네이션으로
//   전환했다(하단 "N건" 표시가 실제 로드된 50건만 반영해 DB 전체 건수와 안 맞는다는
//   피드백). 전체 건수는 X-Total-Count 응답 헤더로 받는다.
const API_BASE_URL: string =
  resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

const LOGS_ENDPOINT = `${API_BASE_URL}/api/v1/admin/detection-logs`;
const DEFAULT_POLL_MS = 30000;

/** 이벤트 프레임을 Authorization 헤더로 조회해 브라우저 전용 Blob URL로 반환합니다. */
export function useAuthorizedEventFrameUrl(
  eventId: string,
  token: string,
): string | null {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let createdUrl: string | null = null;

    void (async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/admin/event-frames/${encodeURIComponent(eventId)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        },
      );
      if (response.status === 401 || response.status === 403) {
        forceAdminRelogin(`event_frame_${response.status}`);
        return;
      }
      if (!response.ok) return;
      createdUrl = URL.createObjectURL(await response.blob());
      setObjectUrl(createdUrl);
    })().catch(() => {
      if (!controller.signal.aborted) setObjectUrl(null);
    });

    return () => {
      controller.abort();
      if (createdUrl) URL.revokeObjectURL(createdUrl);
      setObjectUrl(null);
    };
  }, [eventId, token]);

  return objectUrl;
}

export function useDetectionLogs(
  token: string | null,
  page: number,
  pageSize: number,
  streamFilter: "all" | "reflex" | "cognitive" = "all",
  pollMs = DEFAULT_POLL_MS,
) {
  const [rows, setRows] = useState<DetectionGuidanceLogRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const offset = page * pageSize;
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(offset),
      });
      if (streamFilter !== "all") {
        params.set("stream_type", streamFilter);
      }
      const response = await fetch(
        `${LOGS_ENDPOINT}?${params.toString()}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (response.status === 401) {
        forceAdminRelogin("detection_logs_401");
        return;
      }
      if (!response.ok) {
        throw new Error(`로그 조회 실패 (HTTP ${response.status})`);
      }
      const data: DetectionGuidanceLogRow[] = await response.json();
      setRows(data);
      const totalHeader = response.headers.get("X-Total-Count");
      if (totalHeader) setTotalCount(Number(totalHeader));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그 조회 중 오류");
    } finally {
      setLoading(false);
    }
  }, [token, page, pageSize, streamFilter]);

  const updateLogFalsePositive = useCallback(
    async (logId: number, falsePositive: boolean | null) => {
      if (!token) return;
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/v1/admin/detection-logs/${logId}/false-positive`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ false_positive: falsePositive }),
          },
        );
        if (response.status === 401) {
          forceAdminRelogin("false_positive_401");
          return;
        }
        if (!response.ok) {
          throw new Error(`오탐 판정 업데이트 실패 (HTTP ${response.status})`);
        }
        const updated: DetectionGuidanceLogRow = await response.json();
        setRows((prev) =>
          prev.map((row) => (row.log_id === logId ? updated : row)),
        );
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "오탐 업데이트 중 오류",
        );
      }
    },
    [token],
  );

  useEffect(() => {
    if (!token) return;
    void refresh();
    const timer = setInterval(() => void refresh(), pollMs);
    return () => clearInterval(timer);
  }, [token, refresh, pollMs]);

  return { rows, totalCount, error, loading, refresh, updateLogFalsePositive };
}
