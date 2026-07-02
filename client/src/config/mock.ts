/**
 * Mock 모드 토글 설정.
 * iOS 시뮬레이터(카메라/햅틱 하드웨어 없음)에서 개발하기 위한 우회 계층 on/off.
 *
 * 자동 판단이 불가하므로(expo-constants 미설치) 명시 플래그 사용.
 *  - 시뮬레이터 개발: true (Mock Frame Injector + 시각 햅틱)
 *  - 실기기 테스트   : false (실제 카메라 + 실제 진동)
 *
 * 실기기 도착 시 아래 두 값을 false로 변경하면 즉시 실제 모드로 전환된다.
 */

export const MOCK_CAMERA: boolean = true;
export const MOCK_HAPTIC: boolean = true;
