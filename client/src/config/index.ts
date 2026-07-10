/**
 * Minchodan 클라이언트 환경 설정.
 * Android 에뮬레이터: 10.0.2.2 (호스트 머신 localhost 매핑)
 * 실기기(같은 Wi-Fi): NETWORK_MODE="lan" + 서버 LAN IP로 변경 필요
 * 실기기(LTE/핫스팟, 외부망): NETWORK_MODE="ngrok" (docs/ops/wireless_test_guide.md 참조)
 * (docs/mobile/ios_android_bifurcation_contract.md §7.3: 두 상수를 항상 함께 보존한다.)
 */

const NETWORK_MODE: "lan" | "ngrok" = "lan";

const LAN_IP = "192.168.0.209";
const NGROK_DOMAIN = "partake-primer-surround.ngrok-free.dev";

export const WS_URL =
  NETWORK_MODE === "lan"
    ? `ws://${LAN_IP}:8000/ws/detect`
    : `wss://${NGROK_DOMAIN}/ws/detect`;
export const DEVICE_ID = "dev-001";
export const TOKEN = "token-abc-001";
export const REFLEX_FPS = 4;
export const COGNITIVE_FPS = 2;
export const HEARTBEAT_INTERVAL = 5000;
export const MAX_RECONNECT = 3;
export const RECONNECT_DELAY = 1000;
