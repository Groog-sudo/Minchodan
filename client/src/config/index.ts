/**
 * Minchodan 클라이언트 환경 설정.
 * Android 에뮬레이터: 10.0.2.2 (호스트 머신 localhost 매핑)
 * 실기기: 서버 LAN IP로 변경 필요
 */

const LAN_IP = "192.168.0.209";

export const WS_URL = `ws://${LAN_IP}:8000/ws/detect`;
export const DEVICE_ID = "dev-001";
export const TOKEN = "token-abc-001";
export const REFLEX_FPS = 10;
export const COGNITIVE_FPS = 2;
export const HEARTBEAT_INTERVAL = 5000;
export const MAX_RECONNECT = 3;
export const RECONNECT_DELAY = 1000;
