import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";

/**
 * 시각장애인 긴급 회피용 입체 비프음 오디오 엔진.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 */
class AudioEngine {
  private player: AudioPlayer | null = null;
  private beepTimer: ReturnType<typeof setInterval> | null = null;
  private currentBeepInterval: number = -1;
  private currentPanning: number = 0.0;
  private sessionInitialized = false;

  // 로컬 번들 800Hz 비프 에셋 (reflex_audio_specification.md 준수, 오프라인 안정)
  private readonly BEEP_SRC: number = require("../../assets/sounds/beep.wav");

  /** iOS 오디오 세션 초기화 - 무음 모드에서도 소리 재생 활성화. */
  private async ensureSession(): Promise<void> {
    if (this.sessionInitialized) return;
    this.sessionInitialized = true; // 진입 즉시 락을 걸어 중복 충돌을 방지
    try {
      await setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true,    // 무음 스위치 무시 (시각장애인 보조 필수)
        shouldPlayInBackground: false,
        interruptionMode: "duckOthers",
      });
      console.log("[AudioEngine] 오디오 세션 활성화 완료");
    } catch (err) {
      console.warn("[AudioEngine] 오디오 세션 초기화 실패 (재생 바이패스):", err);
    }
  }

  /** 사운드 플레이어 지연 초기화 (최초 1회 런타임에 안전하게 생성). */
  private ensurePlayer(): void {
    if (this.player) return;
    try {
      this.player = createAudioPlayer(this.BEEP_SRC);
      this.player.volume = 1.0;
      console.log("[AudioEngine] 오디오 플레이어 지연 적재 완료");
    } catch (err) {
      console.error("[AudioEngine] 오디오 플레이어 생성 실패:", err);
    }
  }

  /**
   * 입체 비프음 재생 및 가속을 기동합니다.
   * @param panning 좌우 밸런스 값 (-1.0 ~ 1.0)
   * @param intervalMs 비프음 주기 (ms, 0은 연속 경고음)
   */
  public async playBeep(panning: number, intervalMs: number): Promise<void> {
    // 1. 이미 동일한 주기로 울리고 있다면 무시
    if (this.currentBeepInterval === intervalMs) {
      return;
    }

    this.stopBeepTimer();
    this.currentBeepInterval = intervalMs;
    this.currentPanning = panning;

    // 2. iOS 오디오 세션 및 플레이어 보장 (네이티브 모듈 로딩 완료 후 안전하게 런타임 확보)
    await this.ensureSession();
    this.ensurePlayer();

    try {
      if (!this.player) {
        console.warn("[AudioEngine] 플레이어 없음");
        return;
      }

      this.player.volume = 1.0;

      // 3. 주기별 재생 스케줄링
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
   * 전체 반사음 재생을 정지하고 일시정지 상태로 인스턴스를 유지합니다.
   * (인스턴스 파괴 및 재생성으로 인한 비동기 로딩 딜레이 방지)
   */
  public async stopBeep(): Promise<void> {
    this.stopBeepTimer();
    this.currentBeepInterval = -1;
    this.currentPanning = 0.0;

    try {
      if (this.player) {
        this.player.pause();
        // 메모리에 플레이어 인스턴스를 유지(release/null 처리 생략하여 레이스 방지)
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
