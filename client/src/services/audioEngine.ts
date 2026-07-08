import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import { Asset } from "expo-asset";
import * as FileSystem from "expo-file-system/legacy";

/**
 * 시각장애인 긴급 회피용 입체 비프음 오디오 엔진.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 * iOS 기기의 볼륨 및 소음 보호 차단(Hearing Protection)을 우회하기 위해,
 * 플레이어 Stream을 루프로 상시 기동해 둔 채 오직 볼륨 프로퍼티(Gain) 스위칭만으로 경보를 핑퐁 렌더링합니다.
 */
class AudioEngine {
  private player: AudioPlayer | null = null;
  private beepTimer: ReturnType<typeof setInterval> | null = null;
  private stopTimeout: ReturnType<typeof setTimeout> | null = null;
  private currentBeepInterval: number = -1;
  private currentPanning: number = 0.0;
  private sessionInitialized = false;
  private guidePlayer: AudioPlayer | null = null;
  private guideFileUri: string | null = null;
  /**
   * 가이드 음성 재생 중 여부. 재생 구간 동안 반사 경로의 프레임당 콘솔 로그(디버그용)를
   * 억제하는 데 사용한다 - Metro 개발 모드에서 로그가 JS 브릿지로 실시간 전송되며
   * 오디오 콜백 스케줄링과 경합해 음성이 끊기는 문제가 실측 확인됨(2026-07-08).
   * 탐지/햅틱/비프 로직 자체는 계속 동작하며 콘솔 출력만 억제한다.
   */
  public isGuidePlaying = false;

  // 로컬 번들 800Hz 비프 에셋 (reflex_audio_specification.md 준수, 오프라인 안정)
  private readonly BEEP_SRC: number = require("../../assets/sounds/beep.wav");

  /**
   * iOS 오디오 세션 초기화. 반사 루프 플레이어와 인지 가이드 일회성 플레이어가
   * 동시에 활성화되는 상황이 있어, mixWithOthers를 명시적으로 설정해 두 플레이어가
   * 서로의 재생을 끊거나 덕킹(ducking)하지 않도록 한다.
   */
  private async ensureSession(): Promise<void> {
    if (this.sessionInitialized) return;
    this.sessionInitialized = true;
    try {
      await setAudioModeAsync({
        playsInSilentMode: true,
        interruptionMode: "mixWithOthers",
        shouldPlayInBackground: false,
        allowsRecording: false,
      });
      console.log("[AudioEngine] 오디오 세션 설정 완료 (mixWithOthers)");
    } catch (err) {
      console.error("[AudioEngine] 오디오 세션 설정 실패:", err);
    }
  }

  /** 사운드 플레이어 지연 초기화 (최초 1회 런타임에 안전하게 로컬 URI로 생성). */
  private async ensurePlayer(): Promise<void> {
    if (this.player) return;
    try {
      const asset = Asset.fromModule(this.BEEP_SRC);
      if (!asset.localUri) {
        await asset.downloadAsync();
      }
      const sourceUri = asset.localUri || asset.uri;
      if (!sourceUri) {
        throw new Error("로컬 오디오 에셋 URI 생성 실패");
      }

      console.log("[AudioEngine] 오디오 에셋 다운로드 완료 URI:", sourceUri);
      this.player = createAudioPlayer(sourceUri);
      this.player.loop = true; // 음성 스트림 단절 방지를 위해 항시 루프 재생 모드 적용
      this.player.volume = 0.0; // 최초 생성 시 묵음 처리
      this.player.play(); // 즉시 백그라운드 재생 스트림 개시
      console.log("[AudioEngine] 백그라운드 루프 스트림 기동 완료");
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
    // 1. 널뛰기 방지 정지 대기열이 돌고 있다면, 새로운 재생 요청 유입 시 즉시 취소하여 재생 흐름 유지
    if (this.stopTimeout !== null) {
      clearTimeout(this.stopTimeout);
      this.stopTimeout = null;
    }

    // 2. 이미 동일한 주기로 울리고 있다면 무시
    if (this.currentBeepInterval === intervalMs) {
      return;
    }

    // 3. 동기적으로 기존 타이머를 즉시 지워 중복 스케줄링 방어
    this.stopBeepTimer();
    this.currentBeepInterval = intervalMs;
    this.currentPanning = panning;

    // 4. iOS 오디오 세션 및 플레이어 보장
    await this.ensureSession();
    await this.ensurePlayer();

    try {
      if (!this.player) {
        console.warn("[AudioEngine] 플레이어 없음");
        return;
      }

      // 5. 주기별 볼륨 변조(Modulation) 스케줄링
      if (intervalMs === 0) {
        // 정지 단계: 볼륨을 항시 1.0으로 고정하여 연속 경보음 출력
        this.player.volume = 1.0;
      } else {
        // 점멸 단계: intervalMs 주기로 볼륨 스위칭 (1.0 -> 0.0)
        this.player.volume = 1.0; // 진입 순간 즉시 소리 켬
        setTimeout(() => {
          if (this.player && this.currentBeepInterval === intervalMs) {
            this.player.volume = 0.0; // 120ms 동안만 삐- 소리 내고 묵음
          }
        }, 120);

        this.beepTimer = setInterval(() => {
          if (this.player) {
            this.player.volume = 1.0; // 삐-
            setTimeout(() => {
              if (this.player && this.currentBeepInterval === intervalMs) {
                this.player.volume = 0.0; // 120ms 뒤 묵음
              }
            }, 120);
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
    if (this.beepTimer !== null) {
      clearInterval(this.beepTimer);
      this.beepTimer = null;
    }
  }

  /**
   * 널뛰기 방어 쿨다운을 적용하여 비프음을 안전하게 정지합니다.
   */
  public async stopBeep(): Promise<void> {
    if (this.stopTimeout !== null) {
      return;
    }

    this.stopTimeout = setTimeout(() => {
      this.stopBeepImmediately();
      this.stopTimeout = null;
    }, 600);
  }

  /** 지연 쿨다운 없이 즉시 오디오 스레드를 정지시킵니다 (네이티브 제어 대신 볼륨만 0.0으로 주입). */
  private stopBeepImmediately(): void {
    this.stopBeepTimer();
    this.currentBeepInterval = -1;
    this.currentPanning = 0.0;

    try {
      if (this.player) {
        // AVPlayer를 끄지 않고 볼륨만 0.0으로 주입하여 물리 차단 방어
        this.player.volume = 0.0;
      }
    } catch (err) {
      console.error("[AudioEngine] 즉시 정지 오류:", err);
    }
  }

  /**
   * 인지 경로 서버 TTS 결과(WAV base64)를 1회 재생합니다.
   * 반사 경로의 상시 루프 플레이어(this.player)와는 별개의 일회성 플레이어를 사용한다.
   */
  public async playGuideAudio(base64Wav: string): Promise<void> {
    if (!base64Wav) return;

    // 선점(Preemption): 재생 중인 이전 안내 음성이 있으면 즉시 중단하고 정리한다.
    // (tts-voice-streamer 스킬 설계: 인지 경로는 최신 안내가 이전 안내를 선점)
    this.stopGuideAudio();
    await this.ensureSession();
    this.isGuidePlaying = true;

    const fileUri = `${FileSystem.cacheDirectory}guide-${Date.now()}.wav`;
    try {
      await FileSystem.writeAsStringAsync(fileUri, base64Wav, {
        encoding: FileSystem.EncodingType.Base64,
      });

      const guidePlayer = createAudioPlayer(fileUri);
      this.guidePlayer = guidePlayer;
      this.guideFileUri = fileUri;
      guidePlayer.volume = 1.0;

      guidePlayer.addListener("playbackStatusUpdate", (status) => {
        if (status.didJustFinish && this.guidePlayer === guidePlayer) {
          this.stopGuideAudio();
        }
      });

      guidePlayer.play();
    } catch (err) {
      console.error("[AudioEngine] 가이드 음성 재생 실패:", err);
      this.isGuidePlaying = false;
      FileSystem.deleteAsync(fileUri, { idempotent: true }).catch(() => {});
    }
  }

  /** 재생 중인 안내 음성을 즉시 중단하고 플레이어/임시 파일을 정리한다. */
  public stopGuideAudio(): void {
    const prevPlayer = this.guidePlayer;
    const prevFileUri = this.guideFileUri;
    this.guidePlayer = null;
    this.guideFileUri = null;
    this.isGuidePlaying = false;

    if (prevPlayer) {
      try {
        prevPlayer.remove();
      } catch (err) {
        console.error("[AudioEngine] 가이드 플레이어 정리 실패:", err);
      }
    }
    if (prevFileUri) {
      FileSystem.deleteAsync(prevFileUri, { idempotent: true }).catch(() => {});
    }
  }

  /**
   * 선점(Preemption) 규칙에 따라 작동 중인 모든 음성을 강제 캔슬합니다.
   */
  public async stopAllActiveAudio(): Promise<void> {
    if (this.stopTimeout !== null) {
      clearTimeout(this.stopTimeout);
      this.stopTimeout = null;
    }
    this.stopBeepImmediately();
  }
}

export const audioEngine = new AudioEngine();
