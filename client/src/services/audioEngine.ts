import { Audio } from "expo-av";

/**
 * 시각장애인 긴급 회피용 입체 비프음 오디오 엔진.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 */
class AudioEngine {
  private soundInstance: Audio.Sound | null = null;
  private beepTimer: ReturnType<typeof setInterval> | null = null;
  private currentBeepInterval: number = -1;
  private currentPanning: number = 0.0;

  // 공개된 짧은 비프음 리소스를 디폴트로 참조 (로컬 파일 준비 시 핫스왑 가능)
  private readonly DEFAULT_BEEP_URL = "https://www.soundjay.com/buttons/sounds/button-37a.mp3";

  /**
   * 입체 비프음 재생 및 가속을 기동합니다.
   * @param panning 좌우 밸런스 값 (-1.0 ~ 1.0)
   * @param intervalMs 비프음 주기 (ms, 0은 연속 경고음)
   */
  public async playBeep(panning: number, intervalMs: number): Promise<void> {
    // 1. 이미 동일한 주기와 Panning으로 울리고 있다면 무시
    if (this.currentBeepInterval === intervalMs && Math.abs(this.currentPanning - panning) < 0.1) {
      return;
    }

    this.stopBeepTimer();
    this.currentBeepInterval = intervalMs;
    this.currentPanning = panning;

    try {
      // 2. 사운드 인스턴스 초기 로드 및 속성 갱신
      if (!this.soundInstance) {
        const { sound } = await Audio.Sound.createAsync(
          { uri: this.DEFAULT_BEEP_URL },
          { shouldPlay: false }
        );
        this.soundInstance = sound;
      }

      // 스테레오 Panning(좌우 치향) 적용 및 볼륨 극대화
      await this.soundInstance.setVolumeAsync(1.0);
      await this.soundInstance.setPanAsync(panning);

      // 3. 주기별 재생 스케줄링
      if (intervalMs === 0) {
        // 정지 단계: 끊김 없는 연속 반복음 설정
        await this.soundInstance.setIsLoopingAsync(true);
        await this.soundInstance.playAsync();
      } else {
        // 그 외 단계: intervalMs 주기로 점멸 재생
        await this.soundInstance.setIsLoopingAsync(false);
        this.beepTimer = setInterval(async () => {
          if (this.soundInstance) {
            await this.soundInstance.replayAsync();
          }
        }, intervalMs);
      }
    } catch (err) {
      console.error("[AudioEngine] 비프음 재생 실패:", err);
    }
  }

  /**
   * 비프음 점멸 타이머를 정지합니다.
   */
  private stopBeepTimer(): void {
    if (this.beepTimer) {
      clearInterval(this.beepTimer);
      this.beepTimer = null;
    }
  }

  /**
   * 전체 반사음 재생을 정지하고 리소스를 반환합니다.
   */
  public async stopBeep(): Promise<void> {
    this.stopBeepTimer();
    this.currentBeepInterval = -1;
    this.currentPanning = 0.0;

    try {
      if (this.soundInstance) {
        await this.soundInstance.stopAsync();
        await this.soundInstance.unloadAsync();
        this.soundInstance = null;
      }
    } catch (err) {
      console.error("[AudioEngine] 정지 오류:", err);
    }
  }

  /**
   * 선점(Preemption) 규칙에 따라 작동 중인 모든 음성을 강제 캔슬합니다.
   */
  public async stopAllActiveAudio(): Promise<void> {
    await this.stopBeep();
  }
}

export const audioEngine = new AudioEngine();
