import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import { Asset } from "expo-asset";
import * as FileSystem from "expo-file-system/legacy";
import { File, Paths } from "expo-file-system";
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

// 반사 비프-인지 가이드 음량 우선순위 정책 (2026-07-09 추가).
// CameraView.tsx 4단계(0/200/600/1200ms)와 server/detection/gates/reflex_gate.py
// 4단계(0/100/250/500ms) 양쪽 모두, 이 문턱값 이하가 "초접근/근접"(1~2단계)에 해당한다.
const HIGH_DANGER_INTERVAL_MS = 250;
// 가이드 재생 중 저위험(3~4단계) 비프의 덕킹 볼륨. 0으로 완전히 죽이지 않고
// 존재감만 남겨, 방향성 안내 자체는 계속 인지할 수 있게 한다.
const DUCKED_BEEP_VOLUME = 0.25;

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
  // [2026-07-09 추가] iOS Hearing Protection은 재생 "시작" 시점마다 볼륨 제한을
  // 부여한다(위 클래스 주석 참조 - panPlayers가 상시 루프로 이 문제를 우회하는 이유와
  // 동일). 가이드 음성은 매번 createAudioPlayer()로 새 플레이어를 만들어 무음에서
  // 시작하는 "재생 시작" 이벤트를 반복 발생시켰고, 실기기에서 "시간이 지날수록
  // 목소리가 점점 작아진다"는 현상으로 이어졌다(누적 노출 기반 동적 제한 추정).
  // panPlayers와 동일한 패턴으로, 무음 placeholder를 상시 재생 중인 단일 플레이어를
  // 유지하고 실제 안내 음성은 player.replace()로 소스만 교체한다(재생 상태 자체는
  // 끊기지 않음 - AVPlayer의 rate는 replaceCurrentItem으로 재설정되지 않는다).
  private guideWarmPlayer: AudioPlayer | null = null;
  /**
   * 가이드 음성 재생 중 여부. 재생 구간 동안 반사 경로의 프레임당 콘솔 로그(디버그용)를
   * 억제하는 데 사용한다 - Metro 개발 모드에서 로그가 JS 브릿지로 실시간 전송되며
   * 오디오 콜백 스케줄링과 경합해 음성이 끊기는 문제가 실측 확인됨(2026-07-08).
   * 탐지/햅틱/비프 로직 자체는 계속 동작하며 콘솔 출력만 억제한다.
   */
  public isGuidePlaying = false;
  /** [TEMP DEBUG 2026-07-09] speakFallback 중복 호출 진단용 순번 카운터. */
  private _speakCallSeq = 0;

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

  // 가이드 음성 상시 재생 플레이어의 유휴 상태 소스 (1초 무음, 44.1kHz 모노).
  private readonly SILENCE_SRC: number = require("../../assets/sounds/silence.wav");

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
   * 가이드 음성 상시 재생 플레이어를 지연 초기화한다. panPlayers와 동일한 이유로
   * loop=true 무음 소스를 volume=0.0으로 미리 상시 기동해두고, playGuideAudioBytes()는
   * 이 플레이어의 소스만 player.replace()로 교체한다(재생 "시작" 이벤트를 만들지 않음).
   */
  private async ensureGuideWarmPlayer(): Promise<AudioPlayer | null> {
    if (this.guideWarmPlayer) return this.guideWarmPlayer;
    try {
      const asset = Asset.fromModule(this.SILENCE_SRC);
      if (!asset.localUri) {
        await asset.downloadAsync();
      }
      const sourceUri = asset.localUri || asset.uri;
      if (!sourceUri) {
        throw new Error("가이드 무음 placeholder 에셋 URI 생성 실패");
      }

      const player = createAudioPlayer(sourceUri);
      player.loop = true;
      player.volume = 0.0;
      player.play();
      this.guideWarmPlayer = player;
      console.log("[AudioEngine] 가이드 상시 재생 플레이어 기동 완료 (Hearing Protection 우회)");
      return player;
    } catch (err) {
      console.error("[AudioEngine] 가이드 상시 재생 플레이어 생성 실패:", err);
      return null;
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

    // 인지 가이드 음성과의 볼륨 우선순위 정책 (2026-07-09 추가):
    // 실기기 청취 검증에서 가이드 자체는 끊기지 않지만(자연 종료까지 재생 완료 확인),
    // 반사 비프가 풀볼륨으로 계속 겹쳐 울려 가이드 음성이 끊기는 것처럼 들리는 문제를
    // 확인했다. HIGH_DANGER_INTERVAL_MS 이하(초접근/근접, 실제 충돌 임박)는 안전이
    // 최우선이므로 가이드를 명시적으로 선점(stopGuideAudio)하고 풀볼륨 유지한다.
    // 그보다 여유 있는 단계(중/원거리)는 가이드 음성이 재생 중이면 비프를 덕킹해
    // 안내 문장이 들리도록 한다.
    const isHighDanger = intervalMs <= HIGH_DANGER_INTERVAL_MS; // 0(연속음)도 여기 포함됨
    const wasGuidePlaying = this.isGuidePlaying;
    if (isHighDanger) {
      if (wasGuidePlaying) this.stopGuideAudio();
    }
    const peakVolume = !isHighDanger && this.isGuidePlaying ? DUCKED_BEEP_VOLUME : 1.0;
    // [TEMP DEBUG 2026-07-09] 덕킹/선점 정책 실동작 확인용 - 재현 확인 후 제거
    if (wasGuidePlaying) {
      console.log(`[AudioEngine][DEBUG] 비프-가이드 우선순위 판정: intervalMs=${intervalMs}, isHighDanger=${isHighDanger}, action=${isHighDanger ? "가이드 선점(stopGuideAudio)" : `비프 덕킹(volume=${DUCKED_BEEP_VOLUME})`}`);
    }

    try {
      const player = this.panPlayers.get(bucket);
      if (!player) {
        console.warn(`[AudioEngine] 버킷 플레이어 없음: ${bucket}`);
        return;
      }

      // 6. 주기별 볼륨 변조(Modulation) 스케줄링
      if (intervalMs === 0) {
        // 정지 단계: 볼륨을 항시 peakVolume으로 고정하여 연속 경보음 출력
        player.volume = peakVolume;
      } else {
        // 점멸 단계: intervalMs 주기로 볼륨 스위칭 (peakVolume -> 0.0)
        player.volume = peakVolume; // 진입 순간 즉시 소리 켬
        setTimeout(() => {
          if (this.currentBeepInterval === intervalMs && this.activeBucket === bucket) {
            player.volume = 0.0; // 120ms 동안만 삐- 소리 내고 묵음
          }
        }, 120);

        this.beepTimer = setInterval(() => {
          if (this.activeBucket === bucket) {
            // 매 펄스마다 가이드 재생 상태가 바뀌었을 수 있어 그때그때 볼륨을 재계산한다.
            const pulseVolume = !isHighDanger && this.isGuidePlaying ? DUCKED_BEEP_VOLUME : 1.0;
            player.volume = pulseVolume; // 삐-
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

    // [TEMP DEBUG 2026-07-09] 짤림 원인 진단용 - 재현 확인 후 제거
    const callTs = Date.now();
    console.log(`[AudioEngine][DEBUG] playGuideAudio 호출 ts=${callTs}, wasPlaying=${this.isGuidePlaying}, b64len=${base64Wav.length}`);

    // 선점(Preemption): 재생 중인 이전 안내 음성이 있으면 즉시 중단하고 정리한다.
    // (tts-voice-streamer 스킬 설계: 인지 경로는 최신 안내가 이전 안내를 선점)
    this.stopGuideAudio();
    await this.ensureSession();
    this.isGuidePlaying = true;

    // [2026-07-09 실측 수정] cacheDirectory는 iOS가 저장공간 부족 시 앱 실행 중에도
    // 시스템이 임의로 파일을 정리할 수 있는 영역이다(Paths.cache 공식 문서: "a place
    // to store files that can be deleted by the system when the device runs low on
    // storage"). AVAudioPlayer가 파일을 재생하는 도중 캐시가 정리되면 JS 콜백은 정상
    // 완료(didJustFinish)로 보고하지만 실제 오디오 데이터 일부가 유실돼 문장 중간
    // 음절이 사라지는 것처럼 들리는 현상이 실기기에서 확인됐다. 앱이 명시적으로
    // 삭제하기 전까지 시스템이 건드리지 않는 documentDirectory로 옮긴다.
    const fileUri = `${FileSystem.documentDirectory}guide-${Date.now()}.wav`;
    try {
      await FileSystem.writeAsStringAsync(fileUri, base64Wav, {
        encoding: FileSystem.EncodingType.Base64,
      });

      const guidePlayer = createAudioPlayer(fileUri);
      this.guidePlayer = guidePlayer;
      this.guideFileUri = fileUri;
      guidePlayer.volume = 1.0;
      // [TEMP DEBUG]
      console.log(`[AudioEngine][DEBUG] 재생 시작 ts=${callTs}, duration=${guidePlayer.duration}s`);

      guidePlayer.addListener("playbackStatusUpdate", (status) => {
        // [TEMP DEBUG] currentTime/duration으로 실제 끝까지 재생됐는지 확인
        if (status.didJustFinish && this.guidePlayer === guidePlayer) {
          console.log(`[AudioEngine][DEBUG] 자연 종료(didJustFinish) ts=${callTs}, currentTime=${status.currentTime}, duration=${status.duration}`);
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
   * 인지 경로 서버 TTS 결과(WAV raw bytes)를 1회 재생합니다.
   * [2026-07-09 도입] playGuideAudio()의 base64 문자열 경로 대신, WS 바이너리
   * 프레임으로 받은 원본 바이트를 신형 File API(File.write, 동기, base64 미경유)로
   * 직접 기록한다. 실기기에서 문장 중간 음절이 산발적으로 사라지는 현상의 원인
   * 후보(base64 인코딩/디코딩 및 RN 구 브릿지의 대용량 문자열 처리)를 제거하기
   * 위함. 진단 결과에 따라 playGuideAudio()를 완전히 대체하거나 폐기될 수 있다.
   */
  public async playGuideAudioBytes(wavBytes: Uint8Array): Promise<void> {
    if (!wavBytes || wavBytes.length === 0) return;

    const callTs = Date.now();
    console.log(`[AudioEngine][DEBUG] playGuideAudioBytes 호출 ts=${callTs}, wasPlaying=${this.isGuidePlaying}, bytes=${wavBytes.length}`);

    // 선점(Preemption): speakFallback()(단말 TTS)이 재생 중이었다면 중단한다.
    // 웜 플레이어 자체는 stopGuideAudio()를 거치지 않고 아래 replace()가 직접
    // 선점하므로(재생 "시작" 이벤트 없이 소스만 교체), 여기서는 Speech만 정리한다.
    Speech.stop();
    await this.ensureSession();

    // [2026-07-09 실측 수정] Paths.cache 대신 Paths.document 사용 - 사유는
    // playGuideAudio()의 동일 수정 주석 참조(재생 도중 시스템의 캐시 정리로
    // 인한 산발적 음절 유실 방지).
    const file = new File(Paths.document, `guide-bytes-${Date.now()}.wav`);
    const prevFileUri = this.guideFileUri;
    try {
      file.create();
      file.write(wavBytes);

      // [2026-07-09 추가] 매번 createAudioPlayer()로 새 플레이어를 만들지 않고,
      // 상시 재생 중인 단일 웜 플레이어의 소스만 교체한다(클래스 주석 참조 -
      // Hearing Protection이 재생 "시작" 이벤트마다 볼륨을 제한해 시간이 지날수록
      // 목소리가 작아지는 현상 우회). replace()는 AVPlayer의 rate(재생 상태)를
      // 건드리지 않으므로 이미 재생 중이던 플레이어는 새 소스로 이어서 재생된다.
      const guidePlayer = await this.ensureGuideWarmPlayer();
      if (!guidePlayer) {
        throw new Error("가이드 상시 재생 플레이어를 사용할 수 없습니다.");
      }
      this.guidePlayer = guidePlayer;
      this.guideFileUri = file.uri;
      this.isGuidePlaying = true;

      guidePlayer.loop = false;
      guidePlayer.replace({ uri: file.uri });
      guidePlayer.volume = 1.0;
      guidePlayer.play();
      console.log(`[AudioEngine][DEBUG] (bytes) 재생 시작 ts=${callTs}, duration=${guidePlayer.duration}s`);

      guidePlayer.addListener("playbackStatusUpdate", (status) => {
        if (status.didJustFinish && this.guidePlayer === guidePlayer) {
          console.log(`[AudioEngine][DEBUG] (bytes) 자연 종료(didJustFinish) ts=${callTs}, currentTime=${status.currentTime}, duration=${status.duration}`);
          this.stopGuideAudio();
        }
      });

      // 이전 임시 파일은 새 소스로 교체가 끝난 뒤 정리한다(재생 중이던 파일을
      // 미리 지우면 안 됨).
      if (prevFileUri) {
        FileSystem.deleteAsync(prevFileUri, { idempotent: true }).catch(() => {});
      }
    } catch (err) {
      console.error("[AudioEngine] 가이드 음성(bytes) 재생 실패:", err);
      this.isGuidePlaying = false;
      try {
        file.delete();
      } catch {
        // 파일이 생성되지 않은 상태일 수 있음 - 무시
      }
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

    // [TEMP DEBUG 2026-07-09] 문장 중간 절단(예: "우측으로 [짤림]아 가세요") 원인 진단용.
    // 동일/중복 guide 메시지가 겹쳐 도착해 speakFallback이 중복 호출되는지 확인한다.
    const callId = ++this._speakCallSeq;
    const callTs = Date.now();
    console.log(`[AudioEngine][DEBUG] speakFallback 호출 id=${callId} ts=${callTs} wasPlaying=${this.isGuidePlaying} text="${text}"`);

    this.stopGuideAudio();
    this.isGuidePlaying = true;
    Speech.speak(text, {
      language: "ko-KR",
      // [TEMP DEBUG 2026-07-09] 기본 속도(1.0)에서 "우측으로"->"돌아가세요" 단어 경계
      // 사이가 부자연스럽게 들려("짤림"으로 체감) 속도를 낮춰 자연스러워지는지 검증한다.
      rate: 0.85,
      onStart: () => {
        console.log(`[AudioEngine][DEBUG] speakFallback onStart id=${callId} ts=${Date.now()}`);
      },
      onBoundary: (event: any) => {
        const idx = event?.charIndex ?? -1;
        const len = event?.charLength ?? 0;
        const chunk = idx >= 0 ? text.slice(idx, idx + len) : "?";
        console.log(`[AudioEngine][DEBUG] speakFallback onBoundary id=${callId} ts=${Date.now()} charIndex=${idx} charLength=${len} chunk="${chunk}"`);
      },
      onDone: () => {
        console.log(`[AudioEngine][DEBUG] speakFallback onDone id=${callId} ts=${Date.now()}`);
        this.isGuidePlaying = false;
      },
      onStopped: () => {
        console.log(`[AudioEngine][DEBUG] speakFallback onStopped id=${callId} ts=${Date.now()}`);
        this.isGuidePlaying = false;
      },
      onError: (err) => {
        console.error(`[AudioEngine] 단말 TTS 폴백 실패 id=${callId}:`, err);
        this.isGuidePlaying = false;
      },
    });
  }

  /** 재생 중인 안내 음성을 즉시 중단하고 플레이어/임시 파일을 정리한다. */
  public stopGuideAudio(): void {
    Speech.stop();

    const prevPlayer = this.guidePlayer;
    const prevFileUri = this.guideFileUri;
    // [TEMP DEBUG 2026-07-09] 짤림 원인 진단용 - 재현 확인 후 제거
    if (prevPlayer) {
      try {
        console.log(`[AudioEngine][DEBUG] stopGuideAudio 호출 - currentTime=${prevPlayer.currentTime}s / duration=${prevPlayer.duration}s (${prevPlayer.currentTime < prevPlayer.duration - 0.3 ? "조기 중단 의심!" : "정상 종료 근처"})`);
      } catch {
        console.log("[AudioEngine][DEBUG] stopGuideAudio 호출 - player 상태 조회 실패");
      }
    }
    this.guidePlayer = null;
    this.guideFileUri = null;
    this.isGuidePlaying = false;

    if (prevPlayer) {
      if (prevPlayer === this.guideWarmPlayer) {
        // [2026-07-09 추가] 상시 재생 플레이어는 절대 remove()하지 않는다 - Hearing
        // Protection 우회를 위해 재생 상태 자체를 계속 유지해야 한다(panPlayers와
        // 동일 원칙). 볼륨만 0으로 낮춰 무음화한다.
        try {
          prevPlayer.volume = 0.0;
        } catch (err) {
          console.error("[AudioEngine] 가이드 플레이어 음소거 실패:", err);
        }
      } else {
        // 레거시 playGuideAudio()(base64, 현재 미사용) 경로가 만든 일회성 플레이어.
        try {
          prevPlayer.remove();
        } catch (err) {
          console.error("[AudioEngine] 가이드 플레이어 정리 실패:", err);
        }
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
      // reflex_alert는 항상 reflex_gate/surface_gate/head_level_gate가 실제 위험을
      // 판정했을 때만 발생하므로(§ playBeep의 isHighDanger 정책과 동일한 근거),
      // 인지 가이드가 재생 중이면 선점한다(2026-07-09 추가).
      if (this.isGuidePlaying) this.stopGuideAudio();
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
