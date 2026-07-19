/** 브라우저 탭을 닫으면 제거되는 콘솔 관리자 JWT sessionStorage 키 */
export const ADMIN_TOKEN_KEY = "admin_token";

const AUTH_EXPIRED_EVENT = "minchodan:admin-auth-expired";

/**
 * JWT payload의 exp만 클라이언트에서 읽어 만료 여부를 판정한다.
 * 서명 검증은 서버가 수행하며, 여기서는 만료된 토큰으로 API를 반복 호출하는
 * 401 스팸을 막기 위한 선제 가드다.
 */
export function isAdminTokenExpired(token: string): boolean {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return true;
    const payloadJson = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(payloadJson) as { exp?: number };
    if (typeof payload.exp !== "number") return true;
    // 30초 여유: 경계 만료로 인한 레이스 완화
    return payload.exp * 1000 <= Date.now() + 30_000;
  } catch {
    return true;
  }
}

export function readAdminToken(): string | null {
  const token = sessionStorage.getItem(ADMIN_TOKEN_KEY);
  if (!token) return null;
  if (isAdminTokenExpired(token)) {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    return null;
  }
  return token;
}

/** 만료/무효 토큰을 제거하고 App이 로그인 화면으로 돌아가게 알린다. */
export function forceAdminRelogin(reason = "token_invalid"): void {
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  window.dispatchEvent(
    new CustomEvent(AUTH_EXPIRED_EVENT, { detail: { reason } }),
  );
}

export function subscribeAdminAuthExpired(
  handler: (reason: string) => void,
): () => void {
  const listener = (event: Event) => {
    const detail = (event as CustomEvent<{ reason?: string }>).detail;
    handler(detail?.reason ?? "token_invalid");
  };
  window.addEventListener(AUTH_EXPIRED_EVENT, listener);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, listener);
}
