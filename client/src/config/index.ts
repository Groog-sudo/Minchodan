/**
 * Minchodan 클라이언트 환경 설정.
 * Android 에뮬레이터: 10.0.2.2 (호스트 머신 localhost 매핑)
 * 실기기(같은 Wi-Fi): NETWORK_MODE="lan" + 서버 LAN IP로 변경 필요
 * 실기기(LTE/핫스팟, 외부망): NETWORK_MODE="ngrok" (docs/ops/wireless_test_guide.md 참조)
 * (docs/mobile/ios_android_bifurcation_contract.md §7.3: 두 상수를 항상 함께 보존한다.)
 */

const NETWORK_MODE = "ngrok" as "lan" | "ngrok";

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
// 2026-07-11 재연결 정책 변경(Mitos 로드맵 우선순위 2): 재연결은 포기하지 않고
// 지수 백오프로 무한 반복한다. MAX_RECONNECT는 "중단 횟수"가 아니라 이 횟수만큼
// 연속 실패하면 폴백 모드(온디바이스 경보 전용)로 전환 + 음성 고지하는 문턱값이다.
export const MAX_RECONNECT = 3;
export const RECONNECT_DELAY = 1000;
export const RECONNECT_DELAY_MAX = 30000;
