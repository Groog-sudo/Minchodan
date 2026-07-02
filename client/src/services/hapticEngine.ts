import * as Haptics from "expo-haptics";

import { MOCK_HAPTIC } from "../config/mock";

export type HapticMockHandler = (pattern: string) => void;

/**
 * 시각장애인 긴급 회피용 햅틱(진동) 피드백 서비스.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 *
 * MOCK_HAPTIC=true(시뮬레이터)에서는 진동 대신 콘솔 로그 + 등록된 시각 핸들러 호출.
 */
class HapticEngine {
  private continuousTimer: ReturnType<typeof setInterval> | null = null;
  private mockHandler: HapticMockHandler | null = null;

  /** Mock 모드 시각 피드백 핸들러 등록 (CameraView 오버레이). */
  public setMockHandler(handler: HapticMockHandler | null): void {
    this.mockHandler = handler;
  }

  /**
   * 지정된 패턴으로 진동 피드백을 트리거합니다.
   * @param pattern 'short' | 'double' | 'continuous'
   */
  public async trigger(pattern: string): Promise<void> {
    if (MOCK_HAPTIC) {
      console.log(`[Mock Haptics] 진동 패턴: ${pattern}`);
      this.mockHandler?.(pattern);
      return;
    }

    this.stopContinuous();

    try {
      switch (pattern) {
        case "short":
          await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          break;
        case "double":
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
          break;
        case "continuous":
          // 지속 햅틱은 300ms 간격으로 강한 진동을 연속해서 발생시킵니다.
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
          this.continuousTimer = setInterval(() => {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
          }, 300);
          break;
        default:
          await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      }
    } catch (err) {
      console.error("[HapticEngine] 진동 피드백 실패:", err);
    }
  }

  /**
   * 지속 진동 타이머를 중지합니다.
   */
  public stopContinuous(): void {
    if (this.continuousTimer) {
      clearInterval(this.continuousTimer);
      this.continuousTimer = null;
    }
  }
}

export const hapticEngine = new HapticEngine();
