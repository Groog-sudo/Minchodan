/**
 * Minchodan 클라이언트 환경 설정.
 * Android 에뮬레이터: 10.0.2.2 (호스트 머신 localhost 매핑)
 * 실기기: 서버 LAN IP로 변경 필요
 */

// 외부 포트 터널링 (localtunnel 사용 - browser warning 우회)
// export const WS_URL = "wss://sweet-ideas-happen.loca.lt/ws/detect";
export const WS_URL = "ws://192.168.0.136:8000/ws/detect";


// USB 직접 연결 - adb reverse tcp:8000 tcp:8000 설정 후 사용 (현재 활성)
// export const WS_URL = "ws://localhost:8000/ws/detect";
export const DEVICE_ID = "dev-001";
export const TOKEN = "token-abc-001";
export const REFLEX_FPS = 4;
export const COGNITIVE_FPS = 2;
export const HEARTBEAT_INTERVAL = 5000;
export const MAX_RECONNECT = 3;
export const RECONNECT_DELAY = 1000;
