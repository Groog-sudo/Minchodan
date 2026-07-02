import * as Haptics from "expo-haptics";

/**
 * 시각장애인 긴급 회피용 햅틱(진동) 피드백 서비스.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 */
class HapticEngine {
  private continuousTimer: ReturnType<typeof setInterval> | null = null;

  /**
   * 지정된 패턴으로 진동 피드백을 트리거합니다.
   * @param pattern 'short' | 'double' | 'continuous'
   */
  public async trigger(pattern: string): Promise<void> {
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
