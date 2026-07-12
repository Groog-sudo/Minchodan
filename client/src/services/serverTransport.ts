/**
 * 서버 접속 수송 모드 (WiFi 평상시 / USB 개발).
 * 선택값은 앱 재시작 후에도 유지한다.
 */

import * as FileSystem from "expo-file-system/legacy";

import {
  DEFAULT_SERVER_TRANSPORT,
  USB_HOST,
  WIFI_HOST,
  buildWsUrl,
  type ServerTransport,
} from "../config";

const STORAGE_FILE = `${FileSystem.documentDirectory ?? ""}server_transport.txt`;

export function transportLabel(transport: ServerTransport): string {
  return transport === "usb" ? `USB(${USB_HOST})` : `WiFi(${WIFI_HOST})`;
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
