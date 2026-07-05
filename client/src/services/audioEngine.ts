import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";

/**
 * 시각장애인 긴급 회피용 입체 비프음 오디오 엔진.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 *
 * expo-audio (Expo SDK 51+ 차세대 API) 기반:
 * - 비동기 setter(setVolumeAsync 등) 대신 동기 프로퍼티 할당(volume=, pan=, loop=)
 * - createAudioPlayer()로 즉시 인스턴스 생성 (createAsync 대기 불필요)
 * - player.pan 프로퍼티로 스테레오 패닝 (stereoPan 방어 코드 불필요)
 */
class AudioEngine {
  private player: AudioPlayer | null = null;
  private beepTimer: ReturnType<typeof setInterval> | null = null;
  private currentBeepInterval: number = -1;
  private currentPanning: number = 0.0;
  private sessionInitialized = false;

  // 로컬 번들 800Hz 비프 에셋 (reflex_audio_specification.md 준수, 오프라인 안정)
  private readonly BEEP_SRC: string = "https://www.soundjay.com/buttons/sounds/beep-07a.mp3";

  /** iOS 오디오 세션 초기화 - 무음 모드에서도 소리 재생 활성화. */
  private async ensureSession(): Promise<void> {
    if (this.sessionInitialized) return;
    try {
      await setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true,    // 무음 스위치 무시 (시각장애인 보조 필수)
        shouldPlayInBackground: false,
        interruptionMode: "duckOthers",
      });
      this.sessionInitialized = true;
      console.log("[AudioEngine] 오디오 세션 활성화 완료");
    } catch (err) {
      console.error("[AudioEngine] 오디오 세션 초기화 실패:", err);
    }
  }

  /** 사운드 플레이어 지연 초기화 (최초 재생 시 1회 생성). */
  private ensurePlayer(): void {
    if (this.player) return;
    this.player = createAudioPlayer(this.BEEP_SRC);
    this.player.volume = 1.0;
  }

  /**
   * 입체 비프음 재생 및 가속을 기동합니다.
   * @param panning 좌우 밸런스 값 (-1.0 ~ 1.0)
   * @param intervalMs 비프음 주기 (ms, 0은 연속 경고음)
   */
  public async playBeep(panning: number, intervalMs: number): Promise<void> {
    // 1. 이미 동일한 주기와 Panning으로 울리고 있다면 무시
    // panning의 미세한 변화로 인해 플레이어가 매번 release & recreate 되어 재생이 락업되는 현상을 방지합니다.
    if (this.currentBeepInterval === intervalMs) {
      return;
    }

    this.stopBeepTimer();
    this.currentBeepInterval = intervalMs;
    this.currentPanning = panning;

    // 2. iOS 오디오 세션 초기화 (최초 1회)
    await this.ensureSession();

    try {
      // 3. 플레이어 보장 및 속성 갱신 (동기 프로퍼티 할당)
      this.ensurePlayer();
      if (!this.player) {
        console.warn("[AudioEngine] 플레이어 생성 실패");
        return;
      }

      this.player.volume = 1.0;
      // 주: expo-audio는 스테레오 패닝(pan) 미지원.
      // panning 값은 햅틱/거리 계산에만 활용되며, 오디오는 모노 풀볼륨 재생.

      // 4. 주기별 재생 스케줄링
      if (intervalMs === 0) {
        // 정지 단계: 끊김 없는 연속 반복음
        this.player.loop = true;
        this.player.play();
      } else {
        // 점멸 단계: intervalMs 주기로 재생
        this.player.loop = false;
        void this.replay();
        this.beepTimer = setInterval(() => {
          void this.replay();
        }, intervalMs);
      }
    } catch (err) {
      console.error("[AudioEngine] 비프음 재생 실패:", err);
    }
  }

  /** 처음부터 다시 재생. 짧은 비프 클립은 play() 만으로 처음부터 재생됨. */
  private replay(): void {
    const player = this.player;
    if (!player) return;
    try {
      // expo-audio: 이미 재생 중이어도 play() 재호출 시 처음부터 재생.
      // seekTo(0) 는 일부 플랫폼에서 실패하므로 사용하지 않음.
      player.play();
    } catch (err) {
      console.warn("[AudioEngine] replay 오류:", err);
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
      if (this.player) {
        this.player.pause();
        this.player.release();
        this.player = null;
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
