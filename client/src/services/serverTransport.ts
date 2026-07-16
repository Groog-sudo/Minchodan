/**
 * 서버 접속 수송 모드 (WiFi 평상시 / USB 개발 / Tailscale 외부망).
 * 선택값은 앱 재시작 후에도 유지한다.
 */

import * as FileSystem from "expo-file-system/legacy";

import {
  DEFAULT_SERVER_TRANSPORT,
  NETWORK_MODE,
  NGROK_DOMAIN,
  SERVER_PORT,
  TAILSCALE_HOST,
  USB_HOST,
  WIFI_HOST,
  buildWsUrl,
  getWsUrlCandidates,
  type ServerTransport,
} from "../config";

const STORAGE_FILE = `${FileSystem.documentDirectory ?? ""}server_transport.txt`;

export function transportLabel(transport: ServerTransport): string {
  if (NETWORK_MODE === "tailscale") return `Tailscale(${TAILSCALE_HOST}:${SERVER_PORT})`;
  if (NETWORK_MODE === "ngrok") return `ngrok(${NGROK_DOMAIN})`;
  return transport === "usb" ? `USB(${USB_HOST})` : `WiFi(${WIFI_HOST})`;
}

export function transportButtonText(transport: ServerTransport): string {
  if (NETWORK_MODE === "tailscale") return "연결: Tailscale";
  if (NETWORK_MODE === "ngrok") return "연결: ngrok";
  return transport === "wifi" ? "연결: WiFi" : "연결: USB";
}

export function transportAccessibilityLabel(transport: ServerTransport): string {
  if (NETWORK_MODE === "tailscale") {
    return "Tailscale 외부망 연결 중. WiFi USB 토글은 Tailscale 모드에서 주소를 바꾸지 않습니다.";
  }
  if (NETWORK_MODE === "ngrok") {
    return "ngrok 외부망 연결 중. WiFi USB 토글은 ngrok 모드에서 주소를 바꾸지 않습니다.";
  }
  return transport === "wifi"
    ? "WiFi 연결 중. USB 개발 모드로 전환"
    : "USB 연결 중. WiFi 평상시 모드로 전환";
}

export async function loadServerTransport(): Promise<ServerTransport> {
  try {
    const info = await FileSystem.getInfoAsync(STORAGE_FILE);
    if (!info.exists) return DEFAULT_SERVER_TRANSPORT;
    const raw = (await FileSystem.readAsStringAsync(STORAGE_FILE)).trim();
    if (raw === "usb" || raw === "wifi") return raw;
  } catch {
    // 최초 실행·권한 이슈 시 기본값
  }
  return DEFAULT_SERVER_TRANSPORT;
}

export async function saveServerTransport(transport: ServerTransport): Promise<void> {
  try {
    await FileSystem.writeAsStringAsync(STORAGE_FILE, transport);
  } catch (err) {
    console.warn("[ServerTransport] 저장 실패:", err);
  }
}

export function wsUrlFor(transport: ServerTransport): string {
  return buildWsUrl(transport);
}

/** WiFi 실패 시 Tailscale 폴백을 포함한 WS 후보 목록. */
export function wsUrlCandidatesFor(transport: ServerTransport): string[] {
  return getWsUrlCandidates(transport);
}
