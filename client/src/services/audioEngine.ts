import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import { Asset } from "expo-asset";
import * as FileSystem from "expo-file-system/legacy";
import * as Speech from "expo-speech";

/**
 * 시각장애인 긴급 회피용 입체 비프음 오디오 엔진.
 * docs/reflex_audio_specification.md 규격을 준수합니다.
 * iOS 기기의 볼륨 및 소음 보호 차단(Hearing Protection)을 우회하기 위해,
 * 플레이어 Stream을 루프로 상시 기동해 둔 채 오직 볼륨 프로퍼티(Gain) 스위칭만으로 경보를 핑퐁 렌더링합니다.
 */
// 패닝 버킷: DebugTriggerPanel.tsx의 PAN_PRESETS와 동일한 5단계.
// expo-audio는 실시간 pan API가 없어(2026-07-09 확인), 좌우 채널 게인을 미리 구운
// 스테레오 WAV 5종(client/assets/sounds/beep_pan/)을 버킷별로 전환 재생하는 방식으로
// 입체음향을 구현한다(docs/design/reflex_audio_specification.md §4 후속 과제 해소).
const PAN_BUCKETS: readonly number[] = [-1.0, -0.5, 0.0, 0.5, 1.0];

function nearestPanBucket(panning: number): number {
  return PAN_BUCKETS.reduce((closest, candidate) =>
    Math.abs(candidate - panning) < Math.abs(closest - panning) ? candidate : closest,
  );
}

class AudioEngine {
  private panPlayers: Map<number, AudioPlayer> = new Map();
  private activeBucket: number = 0.0;
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

  // 버킷별 800Hz 비프 스테레오 에셋 (원본 assets/sounds/beep.wav에서 좌우 게인만 다르게
  // 프리렌더링, reflex_audio_specification.md 준수, 오프라인 안정).
  private readonly BEEP_PAN_SRC: Record<string, number> = {
    "-1.0": require("../../assets/sounds/beep_pan/beep_pan_neg1.0.wav"),
    "-0.5": require("../../assets/sounds/beep_pan/beep_pan_neg0.5.wav"),
    "0.0": require("../../assets/sounds/beep_pan/beep_pan_0.0.wav"),
    "0.5": require("../../assets/sounds/beep_pan/beep_pan_0.5.wav"),
    "1.0": require("../../assets/sounds/beep_pan/beep_pan_1.0.wav"),
  };

  // 반사 경로 사전합성 음성 클립(고정, LLM/실시간 TTS 미경유). 서버 reflex_alert의
  // clip 필드(예: "reflex_clips/high_front.wav") basename으로 매칭한다.
  private readonly REFLEX_CLIP_SOURCES: Record<string, number> = {
    "high_front.wav": require("../../assets/sounds/reflex_clips/high_front.wav"),
    "high_front-left.wav": require("../../assets/sounds/reflex_clips/high_front-left.wav"),
    "high_front-right.wav": require("../../assets/sounds/reflex_clips/high_front-right.wav"),
    "surface_caution.wav": require("../../assets/sounds/reflex_clips/surface_caution.wav"),
    "head_level_warning.wav": require("../../assets/sounds/reflex_clips/head_level_warning.wav"),
  };
  private readonly reflexClipUriCache = new Map<string, string>();

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

  /**
   * 버킷별(5방향) 스테레오 플레이어를 지연 초기화한다. iOS Hearing Protection
   * 볼륨 제한 우회를 위해 5개 전부를 loop=true + volume=0.0으로 미리 상시 기동해두고,
   * playBeep()은 그중 방향이 일치하는 플레이어의 볼륨만 스위칭한다.
   */
  private async ensurePanPlayers(): Promise<void> {
    if (this.panPlayers.size > 0) return;
    try {
      for (const bucket of PAN_BUCKETS) {
        const src = this.BEEP_PAN_SRC[bucket.toFixed(1)];
        const asset = Asset.fromModule(src);
        if (!asset.localUri) {
          await asset.downloadAsync();
        }
        const sourceUri = asset.localUri || asset.uri;
        if (!sourceUri) {
          throw new Error(`로컬 오디오 에셋 URI 생성 실패 (bucket=${bucket})`);
        }

        const player = createAudioPlayer(sourceUri);
        player.loop = true;
        player.volume = 0.0;
        player.play();
        this.panPlayers.set(bucket, player);
      }
      console.log("[AudioEngine] 패닝 버킷 5종 백그라운드 루프 스트림 기동 완료");
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

    const bucket = nearestPanBucket(panning);

    // 2. 동일 주기 + 동일 방향 버킷이면 무시 (방향이 바뀌면 버킷 전환이 필요하므로 통과시킨다)
    if (this.currentBeepInterval === intervalMs && bucket === this.activeBucket) {
      return;
    }

    // 3. 동기적으로 기존 타이머를 즉시 지워 중복 스케줄링 방어
    this.stopBeepTimer();

    // 4. iOS 오디오 세션 및 버킷 플레이어 보장
    await this.ensureSession();
    await this.ensurePanPlayers();

    // 5. 방향(버킷)이 바뀌었다면 이전 버킷 플레이어를 즉시 묵음 처리한다.
    if (bucket !== this.activeBucket) {
      const prevPlayer = this.panPlayers.get(this.activeBucket);
      if (prevPlayer) prevPlayer.volume = 0.0;
    }

    this.currentBeepInterval = intervalMs;
    this.currentPanning = panning;
    this.activeBucket = bucket;

    try {
      const player = this.panPlayers.get(bucket);
      if (!player) {
        console.warn(`[AudioEngine] 버킷 플레이어 없음: ${bucket}`);
        return;
      }

      // 6. 주기별 볼륨 변조(Modulation) 스케줄링
      if (intervalMs === 0) {
        // 정지 단계: 볼륨을 항시 1.0으로 고정하여 연속 경보음 출력
        player.volume = 1.0;
      } else {
        // 점멸 단계: intervalMs 주기로 볼륨 스위칭 (1.0 -> 0.0)
        player.volume = 1.0; // 진입 순간 즉시 소리 켬
        setTimeout(() => {
          if (this.currentBeepInterval === intervalMs && this.activeBucket === bucket) {
            player.volume = 0.0; // 120ms 동안만 삐- 소리 내고 묵음
          }
        }, 120);

        this.beepTimer = setInterval(() => {
          if (this.activeBucket === bucket) {
            player.volume = 1.0; // 삐-
            setTimeout(() => {
              if (this.currentBeepInterval === intervalMs && this.activeBucket === bucket) {
                player.volume = 0.0; // 120ms 뒤 묵음
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
      // AVPlayer를 끄지 않고 볼륨만 0.0으로 주입하여 물리 차단 방어 (현재 활성 버킷만)
      const player = this.panPlayers.get(this.activeBucket);
      if (player) {
        player.volume = 0.0;
      }
    } catch (err) {
      console.error("[AudioEngine] 즉시 정지 오류:", err);
    }
  }

  /**
   * 인지 경로 서버 TTS 결과(WAV base64)를 1회 재생합니다.
   * 반사 경로의 상시 루프 플레이어(panPlayers)와는 별개의 일회성 플레이어를 사용한다.
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

  /**
   * 서버 TTS 실패/타임아웃(3초) 시 단말 내장 TTS로 안내 문장을 대신 발화한다.
   * (docs/design/reflex_audio_specification.md와 무관 - 인지 경로 전용 폴백.
   * 서버는 여전히 오디오를 생성하지 못했을 뿐 안내 문장 자체는 만들었으므로,
   * 무음 대신 단말이 직접 말해 안내가 사라지는 체감을 없앤다.)
   */
  public speakFallback(text: string): void {
    if (!text || !text.trim()) return;

    this.stopGuideAudio();
    this.isGuidePlaying = true;
    Speech.speak(text, {
      language: "ko-KR",
      onDone: () => {
        this.isGuidePlaying = false;
      },
      onStopped: () => {
        this.isGuidePlaying = false;
      },
      onError: (err) => {
        console.error("[AudioEngine] 단말 TTS 폴백 실패:", err);
        this.isGuidePlaying = false;
      },
    });
  }

  /** 재생 중인 안내 음성을 즉시 중단하고 플레이어/임시 파일을 정리한다. */
  public stopGuideAudio(): void {
    Speech.stop();

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

  /** 반사 클립 basename에 대응하는 로컬 번들 자산 URI를 1회만 리졸브하고 캐시한다. */
  private async resolveReflexClipUri(basename: string): Promise<string | null> {
    const cached = this.reflexClipUriCache.get(basename);
    if (cached) return cached;

    const src = this.REFLEX_CLIP_SOURCES[basename];
    if (!src) return null;

    const asset = Asset.fromModule(src);
    if (!asset.localUri) {
      await asset.downloadAsync();
    }
    const uri = asset.localUri || asset.uri;
    if (uri) this.reflexClipUriCache.set(basename, uri);
    return uri ?? null;
  }

  /**
   * 반사 경로 사전합성 음성 클립을 1회 재생한다(비프/햅틱과 별개 채널, 병행 재생).
   * clipPath는 서버 reflex_alert 페이로드의 clip 필드(예: "reflex_clips/high_front.wav").
   */
  public async playReflexClip(clipPath: string): Promise<void> {
    const basename = clipPath.split("/").pop() ?? "";
    const uri = await this.resolveReflexClipUri(basename);
    if (!uri) {
      console.warn(`[AudioEngine] 알 수 없는 반사 클립: ${clipPath}`);
      return;
    }

    try {
      await this.ensureSession();
      const clipPlayer = createAudioPlayer(uri);
      clipPlayer.volume = 1.0;
      clipPlayer.addListener("playbackStatusUpdate", (status) => {
        if (status.didJustFinish) {
          clipPlayer.remove();
        }
      });
      clipPlayer.play();
    } catch (err) {
      console.error("[AudioEngine] 반사 클립 재생 실패:", err);
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
