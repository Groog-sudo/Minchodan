import * as Haptics from "expo-haptics";

import { MOCK_HAPTIC } from "../config/mock";
import { audioEngine } from "./audioEngine";

export type HapticMockHandler = (pattern: string) => void;

/**
 * 시각장애인 긴급 회피용 햅틱(진동) 피드백 서비스.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 *
 * MOCK_HAPTIC=true(시뮬레이터)에서는 진동 대신 콘솔 로그 + 등록된 시각 핸들러 호출.
 */
/** continuous 패턴 최대 지속(ms). 이후 자동 stopContinuous (로드맵 Option A). */
const CONTINUOUS_MAX_MS = 5000;
/**
 * continuous 패턴 최소 보장 지속(ms). reflex_clear가 respectMinimum=true로 stopContinuous를
 * 호출할 때만 적용된다(2026-07-20, 실기기 필드 테스트: Near 반사 episode가 ~300ms 안팎으로
 * 짧게 끝나는 경우가 흔해 즉시 정지하면 시작 알림 진동 1회 외엔 거의 못 느끼는 문제 확인).
 */
const CONTINUOUS_MIN_MS = 500;

class HapticEngine {
  private continuousTimer: ReturnType<typeof setInterval> | null = null;
  private continuousCapTimer: ReturnType<typeof setTimeout> | null = null;
  private continuousStartedAt: number | null = null;
  private pendingStopTimer: ReturnType<typeof setTimeout> | null = null;
  private mockHandler: HapticMockHandler | null = null;

  /** Mock 모드 시각 피드백 핸들러 등록 (CameraView 오버레이). */
  public setMockHandler(handler: HapticMockHandler | null): void {
    this.mockHandler = handler;
  }

  /**
   * 지정된 패턴으로 진동 피드백을 트리거합니다.
   * @param pattern 'short' | 'double' | 'continuous'
   * @param opts.allowDuringStt STT(길찾아줘/물어볼게) 중에도 허용(녹음 시작 큐 등)
   */
  public async trigger(
    pattern: string,
    opts?: { allowDuringStt?: boolean },
  ): Promise<void> {
    // 1순위 STT 구간: Near 위험 햅틱 억제. STT 자체 큐만 allowDuringStt로 통과.
    if (!opts?.allowDuringStt && audioEngine.isSttActive()) {
      console.log(`[HapticEngine] STT 상호작용 중 - 위험 햅틱 억제: ${pattern}`);
      return;
    }

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
          // CONTINUOUS_MAX_MS 후 자동 종료해 피로·배터리 고갈을 막는다.
          this.continuousStartedAt = Date.now();
          await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
          this.continuousTimer = setInterval(() => {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
          }, 300);
          this.continuousCapTimer = setTimeout(() => {
            this.stopContinuous();
          }, CONTINUOUS_MAX_MS);
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
   * @param opts.respectMinimum true면 CONTINUOUS_MIN_MS를 채울 때까지 실제 정지를 유예한다.
   *   reflex_clear처럼 "이미 시작된 진동을 최소한은 느끼게 하고 싶은" 자동 해제 경로에서만 켠다.
   *   STT 억제·화면 전환 등 즉시 멈춰야 하는 경로는 기본값(즉시 정지)을 그대로 쓴다.
   */
  public stopContinuous(opts?: { respectMinimum?: boolean }): void {
    if (this.pendingStopTimer) {
      clearTimeout(this.pendingStopTimer);
      this.pendingStopTimer = null;
    }
    if (opts?.respectMinimum && this.continuousTimer && this.continuousStartedAt !== null) {
      const remaining = CONTINUOUS_MIN_MS - (Date.now() - this.continuousStartedAt);
      if (remaining > 0) {
        this.pendingStopTimer = setTimeout(() => this.stopContinuousNow(), remaining);
        return;
      }
    }
    this.stopContinuousNow();
  }

  private stopContinuousNow(): void {
    if (this.continuousTimer) {
      clearInterval(this.continuousTimer);
      this.continuousTimer = null;
    }
    if (this.continuousCapTimer) {
      clearTimeout(this.continuousCapTimer);
      this.continuousCapTimer = null;
    }
    this.continuousStartedAt = null;
  }
}

export const hapticEngine = new HapticEngine();
