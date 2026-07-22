/**
 * Minchodan 클라이언트 환경 설정.
 *
 * 실기기 접속은 NETWORK_MODE와 앱 안 "WiFi / USB" 토글로 전환한다 (serverTransport).
 * - wifi(평상시): 노트북 핫스팟 게이트웨이 또는 같은 LAN의 PC IP
 * - usb(개발): adb reverse 후 127.0.0.1 (기능 추가/수정 시)
 * - tailscale: iOS/Android 실기기가 외부망에서 Tailscale VPN으로 서버에 직접 접속
 *
 * (docs/mobile/ios_android_bifurcation_contract.md §7.3)
 */

export type ServerTransport = "wifi" | "usb";
export type NetworkMode = "lan" | "tailscale";

export const NETWORK_MODE = (process.env.EXPO_PUBLIC_NETWORK_MODE ?? "tailscale") as NetworkMode;
export const SERVER_PORT = process.env.EXPO_PUBLIC_SERVER_PORT ?? "8000";
export const WS_SCHEME = process.env.EXPO_PUBLIC_WS_SCHEME === "ws" ? "ws" : "wss";

/** 평상시: PC 모바일 핫스팟(공기계→노트북). Windows 기본 게이트웨이. */
export const WIFI_HOST =
  process.env.EXPO_PUBLIC_WIFI_HOST ??
  process.env.EXPO_PUBLIC_LAN_IP ??
  "";

/** 개발: USB + `adb reverse tcp:8000 tcp:8000` 일 때. */
export const USB_HOST = process.env.EXPO_PUBLIC_USB_HOST ?? "127.0.0.1";

export const TAILSCALE_HOST =
  process.env.EXPO_PUBLIC_TAILSCALE_HOST ??
  "";

/** 앱 기동 기본값: 평상시는 WiFi. USB는 토글로 전환. */
export const DEFAULT_SERVER_TRANSPORT: ServerTransport =
  (process.env.EXPO_PUBLIC_DEFAULT_TRANSPORT as ServerTransport | undefined) ?? "wifi";

export function buildWsUrl(transport: ServerTransport = DEFAULT_SERVER_TRANSPORT): string {
  if (NETWORK_MODE === "tailscale") {
    if (!TAILSCALE_HOST) throw new Error("EXPO_PUBLIC_TAILSCALE_HOST가 필요합니다.");
    return `${WS_SCHEME}://${TAILSCALE_HOST}:${SERVER_PORT}/ws/detect`;
  }
  const host = transport === "usb" ? USB_HOST : WIFI_HOST;
  if (!host) throw new Error("클라이언트 서버 호스트 환경 변수가 필요합니다.");
  const scheme = transport === "usb" && host === "127.0.0.1" ? "ws" : WS_SCHEME;
  return `${scheme}://${host}:${SERVER_PORT}/ws/detect`;
}

/**
 * WS 접속 후보 목록.
 * 학원 WiFi 기기격리 등으로 LAN이 실패할 때 Tailscale 호스트로 폴백한다.
 * NETWORK_MODE=tailscale이면 해당 경로만 반환한다.
 */
export function getWsUrlCandidates(
  transport: ServerTransport = DEFAULT_SERVER_TRANSPORT,
): string[] {
  if (NETWORK_MODE === "tailscale") {
    return [buildWsUrl(transport)];
  }

  const primary = buildWsUrl(transport);
  const candidates = [primary];
  const tailscaleUrl = `${WS_SCHEME}://${TAILSCALE_HOST}:${SERVER_PORT}/ws/detect`;
  if (
    TAILSCALE_HOST &&
    TAILSCALE_HOST !== "127.0.0.1" &&
    !candidates.includes(tailscaleUrl)
  ) {
    candidates.push(tailscaleUrl);
  }
  return candidates;
}

/** 하위 호환: 기본 수송(WiFi) 기준 URL. 런타임은 buildWsUrl + 토글 사용. */
export const WS_URL = buildWsUrl(DEFAULT_SERVER_TRANSPORT);

export const DEVICE_ID = process.env.EXPO_PUBLIC_DEVICE_ID ?? "";
export const TOKEN = process.env.EXPO_PUBLIC_DEVICE_TOKEN ?? "";
export const REFLEX_FPS = 8;
export const COGNITIVE_FPS = 2;
export const HEARTBEAT_INTERVAL = 5000;
export const MAX_RECONNECT = 3;
export const RECONNECT_DELAY = 1000;
export const RECONNECT_DELAY_MAX = 30000;
export const NETWORK_BENCHMARK_ENABLED =
  process.env.EXPO_PUBLIC_NETWORK_BENCHMARK === "true";
export const NETWORK_BENCHMARK_INTERVAL_MS = Number(
  process.env.EXPO_PUBLIC_NETWORK_BENCHMARK_INTERVAL_MS ?? "1000",
);
export const NETWORK_BENCHMARK_PAYLOAD_BYTES = Number(
  process.env.EXPO_PUBLIC_NETWORK_BENCHMARK_PAYLOAD_BYTES ?? "256",
);
