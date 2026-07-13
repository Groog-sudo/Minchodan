import { useCallback, useEffect, useState } from "react";
import type { AppUserRow, MemberRegisterPayload } from "../types/monitor";
import { resolveApiBaseUrl } from "../config/network";

// 발표/면접 포인트:
// - useDetectionLogs.ts와 동일한 서버 페이지네이션 패턴(offset/limit + X-Total-Count 헤더).
const API_BASE_URL: string =
  resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

const MEMBERS_ENDPOINT = `${API_BASE_URL}/api/v1/admin/members`;

export function useMembers(token: string | null, page: number, pageSize: number) {
  const [rows, setRows] = useState<AppUserRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const offset = page * pageSize;
      const response = await fetch(
        `${MEMBERS_ENDPOINT}?limit=${pageSize}&offset=${offset}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) {
        throw new Error(`회원 목록 조회 실패 (HTTP ${response.status})`);
      }
      const data: AppUserRow[] = await response.json();
      setRows(data);
      const totalHeader = response.headers.get("X-Total-Count");
      if (totalHeader) setTotalCount(Number(totalHeader));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "회원 목록 조회 중 오류");
    } finally {
      setLoading(false);
    }
  }, [token, page, pageSize]);

  const registerMember = useCallback(
    async (payload: MemberRegisterPayload): Promise<{ ok: boolean; message: string }> => {
      if (!token) return { ok: false, message: "로그인이 필요합니다." };
      try {
        const response = await fetch(MEMBERS_ENDPOINT, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          const message =
            (detail && typeof detail.detail === "string" && detail.detail) ||
            `등록 실패 (HTTP ${response.status})`;
          return { ok: false, message };
        }
        await refresh();
        return { ok: true, message: "등록되었습니다." };
      } catch (err) {
        return {
          ok: false,
          message: err instanceof Error ? err.message : "등록 중 오류가 발생했습니다.",
        };
      }
    },
    [token, refresh],
  );

  useEffect(() => {
    if (!token) return;
    void refresh();
  }, [token, refresh]);

  return { rows, totalCount, error, loading, refresh, registerMember };
}
