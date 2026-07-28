import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import { Asset } from "expo-asset";
import * as FileSystem from "expo-file-system/legacy";
import { File, Paths } from "expo-file-system";
import { Platform } from "react-native";
import * as Speech from "expo-speech";

import { GUIDE_PRIORITY, type GuidePriority } from "./guidePriority";

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

// 반사 비프-인지 가이드 음량 우선순위 정책 (2026-07-09 추가, 2026-07-19 정정).
// useWebSocket 긴급 채널(interval<=100, beep-only)과 맞춘다. 이전 250ms는 Mid
// 단계(250ms) 비프까지 가이드를 선점해 탐지 시작 직후 안내가 끊기던 원인이었다.
const HIGH_DANGER_INTERVAL_MS = 100;
// 가이드 재생 중 저위험(3~4단계) 비프의 덕킹 볼륨. 0으로 완전히 죽이지 않고
// 존재감만 남겨, 방향성 안내 자체는 계속 인지할 수 있게 한다.
/** 가이드/클립 재생 중 Near 연속 비프 볼륨. 0.25는 말 안내를 덮어 실측에서 비프만 들림. */
const DUCKED_BEEP_VOLUME = 0.08;

/**
 * expo-speech 폴백 발화의 음절 경계 로그 스위치 (2026-07-28).
 * 발화 1회에 수십 건이 Metro 브릿지로 나가, 하필 프레임·추론 처리량이 떨어지는
 * 오디오 구간의 계측을 왜곡하고 부하를 더한다. 발음/타이밍 디버깅 시에만 켠다.
 */
const SPEAK_BOUNDARY_DEBUG = false;

// 반사 클립 안전 회수 시간(ms). didJustFinish가 오지 않는 경우의 백스톱.
const REFLEX_CLIP_REAP_MIN_MS = 1500;
const REFLEX_CLIP_REAP_MAX_MS = 5000;
/**
 * Near/인지 음성 안내 대기열 상한.
 * 2026-07-21: Near 완주 후 Medium 1회를 위해 2슬롯(동시 near pending + med pending).
 * 동일 우선순위는 최신만, 종료 시 OTHER만 폐기하고 FRONT_MED는 유지.
 */
const GUIDE_PENDING_MAX = 2;
/**
 * setSttActive(true) 이후 응답 콜백이 끝내 오지 않을 경우의 안전 상한(ms).
 * useWebSocket.ts의 STT_INTERACTION_TIMEOUT_MS와 동일 값을 쓴다 - 두 백스톱이
 * 겹쳐도 무해하다(둘 다 setSttActive(false) 호출뿐이라 idempotent).
 */
const STT_SAFETY_TIMEOUT_MS = 20000;

type PendingGuideItem =
  | {
      kind: "bytes";
      wavBytes: Uint8Array;
      priority: GuidePriority;
      onComplete?: () => void;
    }
  | {
      kind: "fallback";
      text: string;
      priority: GuidePriority;
      onComplete?: () => void;
    };

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
  // 💡 [면접 대비 주석] 웜 플레이어 리스너 누수 차단 (2026-07-28).
  // guideWarmPlayer는 Hearing Protection 우회를 위해 무음 루프로 "상시 재생"되는 단일
  // 인스턴스를 재사용한다. 그런데 playGuideAudioBytesNow()가 재생할 때마다 이 플레이어에
  // addListener("playbackStatusUpdate")를 새로 걸면서 해제는 하지 않아, 가이드를 N번
  // 재생하면 상태 업데이트마다 N개 클로저가 실행됐다. 상시 재생이라 가이드가 없을 때도
  // 업데이트가 계속 발생하므로 비용이 누적된다.
  // Xiaomi 12 실측(2026-07-28): 오디오 재생 구간에서 handleFrame이 5초당 45 -> 18회,
  // 추론 디스패치 21 -> 1회로 붕괴. logcat ExpoAudio 세션 이벤트 30초에 1701회.
  // 새 리스너를 걸기 전에 직전 구독을 반드시 해제한다.
  private guideStatusSubscription: { remove: () => void } | null = null;
  // 💡 [면접 대비 주석] 반사 클립 플레이어 누수 차단 (2026-07-28).
  // 기존에는 createAudioPlayer()로 만든 클립 플레이어를 지역 변수로만 들고,
  // didJustFinish 콜백에서만 remove()했다. 참조를 보관하지 않으므로 클립이 완주하지
  // 못하면(가이드 선점, 앱 백그라운드 전환, 오디오 세션 인터럽션) 네이티브 플레이어와
  // 리스너를 정리할 경로가 아예 없었다. 반사 클립은 Near 경보마다 재생되어 실사용
  // 빈도가 높아 장시간 보행에서 누적된다.
  // 참조를 보관해 새 클립 재생 전에 직전 플레이어를 정리하고, didJustFinish가 오지
  // 않는 경우를 대비해 안전 타이머로도 회수한다.
  private reflexClipPlayer: AudioPlayer | null = null;
  private reflexClipSubscription: { remove: () => void } | null = null;
  private reflexClipReapTimer: ReturnType<typeof setTimeout> | null = null;
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
  /**
   * 음성 안내 우선순위 조정자 상태 (2026-07-19 4단).
   * 0=idle, 1=기타, 2=12시 MED, 3=12시 NEAR, 4=STT(길찾아줘/물어볼게).
   * 반사 비프/클립은 별도 채널이되, STT 활성 중에는 억제한다.
   */
  private activeGuidePriority: 0 | GuidePriority = 0;
  /**
   * STT 상호작용(녹음~응답 종료) 활성 여부.
   * 활성 중에는 위험 안내(NEAR 포함)·비프·반사 클립을 막아 질문/길찾기를 방해하지 않는다.
   */
  private sttActive = false;
  /**
   * 2026-07-21: Near enter 반사 클립 재생 중이면 비프를 DUCKED_BEEP_VOLUME으로 낮춘다.
   * 말이 비프에 가려지지 않게 하기 위함. 클립 종료 또는 안전 타임아웃으로 해제.
   */
  private reflexClipDucking = false;
  private reflexClipDuckTimer: ReturnType<typeof setTimeout> | null = null;
  /** 클립 didJustFinish 미도착 대비 덕킹 최대 유지(ms). */
  private static readonly REFLEX_CLIP_DUCK_MAX_MS = 3500;
  /**
   * 2026-07-20: setSttActive(true) 호출 지점(CameraView.tsx 녹음 시작, useWebSocket.ts
   * 응답 수신)과 무관하게 일괄 적용되는 안전 상한 타이머. 이전에는 useWebSocket.ts의
   * STT_INTERACTION_TIMEOUT_MS 백스톱이 "응답 수신 이후" 구간에만 걸려 있어, 녹음
   * 시작 직후 네트워크 유실 등으로 응답 자체가 끝내 오지 않으면 STT 억제 상태가
   * 영구히 풀리지 않아 햅틱·비프·인지 안내가 전부 조용히 억제되는 결함이 있었다
   * (외부망 실기기 필드 테스트에서 재현: STT 활성화 14회 대비 비활성화 9회로
   * 마지막 활성화가 해제되지 않은 채 로그가 종료됨).
   */
  private sttSafetyTimer: ReturnType<typeof setTimeout> | null = null;
  /**
   * 재생 중 쌓인 Near/인지 음성 대기열(최대 GUIDE_PENDING_MAX, 우선순위 혼합 가능).
   * 재생 종료 시 최고 우선순위 1건만 꺼내 재생하고 나머지는 폐기한다.
   */
  private pendingGuides: PendingGuideItem[] = [];
  /** 선점/중단 시 이전 재생 콜백이 drain 하지 않도록 무효화하는 세대 번호. */
  private guideEpoch = 0;
  /** [TEMP DEBUG 2026-07-09] speakFallback 중복 호출 진단용 순번 카운터. */
  private _speakCallSeq = 0;
  /**
   * 단말 내장 TTS(ko) 중 가장 자연스러운 음성 identifier.
   * undefined=미조회, null=조회 실패/후보 없음, string=선택됨.
   * Android 기본 SAPI/로컬 TTS는 기계음이 강해 Google Neural 계열을 우선한다.
   */
  private preferredKoVoiceId: string | null | undefined = undefined;

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

  // STT 녹음 종료 신호음(더블 비프). 진입점은 haptic이 담당한다 - 녹음이 활성 상태인
  // 동안 스피커로 소리를 내면 마이크가 그대로 다시 주워듣는 음향 블리드가 물리적으로
  // 발생함을 실기기 파형 분석으로 확인했다(2026-07-11). 종료 신호음은 recorder.stop()
  // 완료 이후에만 재생되므로 이 문제가 없다.
  private readonly STT_END_CUE_SRC: number = require("../../assets/sounds/stt_end.wav");
  private sttEndCueUri: string | null = null;
  // STT 녹음 시작 신호음(단일 상승 비프, 종료 더블 비프와 구분). 2026-07-11 음향
  // 블리드 때문에 제거했던 시작 신호음을 AEC(voiceChat 세션) 활성이 확인된 경우에
  // 한해 복원한다 - AEC가 스피커 출력을 마이크 입력에서 상쇄하므로 녹음 오염이
  // 없다는 가설의 검증 대상(useSttRecorder가 세션 모드 확인 후에만 호출).
  private readonly STT_START_CUE_SRC: number = require("../../assets/sounds/stt_start.wav");
  private sttStartCueUri: string | null = null;
  // guideWarmPlayer와 동일한 이유(재생 "시작" 이벤트를 만들지 않기 위해)로 무음
  // placeholder를 상시 재생해두고 소스만 교체하는 상시 플레이어를 사용한다.
  private sttCueWarmPlayer: AudioPlayer | null = null;

  /**
   * iOS 오디오 세션 초기화. 반사 루프 플레이어와 인지 가이드 일회성 플레이어가
   * 동시에 활성화되는 상황이 있어, mixWithOthers를 명시적으로 설정해 두 플레이어가
   * 서로의 재생을 끊거나 덕킹(ducking)하지 않도록 한다.
   * 2026-07-10 정정: allowsRecording을 false로 고정해두면 expo-audio의
   * useAudioRecorder().record()가 항상 RecordingDisabledException으로 실패한다
   * (STT 녹음이 서버에 단 한 번도 도달하지 못한 근본 원인, 실기기 실측 확인).
   * shouldRouteThroughEarpiece 기본값이 false라 true로 바꿔도 스피커 출력은 유지된다.
   */
  private async ensureSession(): Promise<void> {
    if (this.sessionInitialized) return;
    this.sessionInitialized = true;
    try {
      await setAudioModeAsync({
        playsInSilentMode: true,
        interruptionMode: "mixWithOthers",
        shouldPlayInBackground: false,
        allowsRecording: true,
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
    // 2026-07-20: STT 중에도 Near 반사 비프는 유지한다(질문 음성은 인지 guide만
    // STT 우선). 이전에는 sttActive면 비프를 막아 길찾기 대화 중 Near가 조용히 죽었다.

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

    // 2026-07-21: Near 비프 update가 후속 행동 안내(post_reflex guide)를 끊지 않게 한다.
    // 긴급 비프는 덕킹만 하고, STT가 아닌 가이드 음성은 유지한다(선점 stop 제거).
    const isHighDanger = intervalMs <= HIGH_DANGER_INTERVAL_MS;
    const wasGuidePlaying = this.isGuidePlaying;
    const activePri = this.activeGuidePriority;
    const peakVolume = this.resolveBeepPeakVolume(isHighDanger);
    if (wasGuidePlaying || this.reflexClipDucking) {
      console.log(
        `[AudioEngine][DEBUG] 비프-가이드 덕킹: intervalMs=${intervalMs}, isHighDanger=${isHighDanger}, activePri=${activePri}, peak=${peakVolume}, clipDuck=${this.reflexClipDucking}`,
      );
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
            // 매 펄스마다 가이드/클립 재생 상태가 바뀌었을 수 있어 볼륨을 재계산한다.
            const pulseVolume = this.resolveBeepPeakVolume(isHighDanger);
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
   * 비프 피크 볼륨. 반사 클립 덕킹 또는 가이드 재생 중이면 DUCKED_BEEP_VOLUME.
   */
  private resolveBeepPeakVolume(isHighDanger: boolean): number {
    if (this.reflexClipDucking) {
      return DUCKED_BEEP_VOLUME;
    }
    // 2026-07-21: Near 비프 중에도 post_reflex/인지 안내가 들리도록 가이드 재생 시 항상 덕킹.
    if (this.isGuidePlaying) {
      return DUCKED_BEEP_VOLUME;
    }
    void isHighDanger;
    return 1.0;
  }

  private beginReflexClipDucking(): void {
    this.setBeepDucked(true);
    if (this.reflexClipDuckTimer) {
      clearTimeout(this.reflexClipDuckTimer);
      this.reflexClipDuckTimer = null;
    }
    this.reflexClipDuckTimer = setTimeout(() => {
      this.endReflexClipDucking();
    }, AudioEngine.REFLEX_CLIP_DUCK_MAX_MS);
  }

  private endReflexClipDucking(): void {
    if (this.reflexClipDuckTimer) {
      clearTimeout(this.reflexClipDuckTimer);
      this.reflexClipDuckTimer = null;
    }
    // 가이드 음성이 아직 재생 중이면 덕킹 유지(가이드 종료 시 unduck).
    if (this.isGuidePlaying) return;
    this.setBeepDucked(false);
  }

  /** 가이드/클립 재생 중 Near 연속 비프를 즉시 낮춘다(재생 시작 시점 볼륨 고정 문제 해소). */
  private setBeepDucked(ducked: boolean): void {
    this.reflexClipDucking = ducked;
    const player = this.panPlayers.get(this.activeBucket);
    if (!player || this.currentBeepInterval < 0) return;
    if (this.currentBeepInterval === 0) {
      player.volume = ducked ? DUCKED_BEEP_VOLUME : this.resolveBeepPeakVolume(true);
    }
  }

  /** 가이드 음성 시작 시 호출 - 연속 Near 비프가 안내를 덮지 않게 한다. */
  private duckBeepForGuideSpeech(): void {
    this.setBeepDucked(true);
  }

  private unduckBeepAfterGuideSpeech(): void {
    if (this.reflexClipDuckTimer) return; // 클립 덕킹 타이머가 관리 중
    this.setBeepDucked(false);
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
   * 현재 재생 중인 가이드 우선순위. 0=없음.
   */
  public getActiveGuidePriority(): 0 | GuidePriority {
    return this.activeGuidePriority;
  }

  /**
   * maxPriority 이하만 중단. STT arm 시 Near 음성까지 선점(질문 방해 방지).
   */
  public stopGuideAudioIfPriorityAtMost(maxPriority: GuidePriority): boolean {
    if (!this.isGuidePlaying) return false;
    if (this.activeGuidePriority > maxPriority) {
      console.log(
        `[AudioEngine] stopGuideAudio 생략: activePriority=${this.activeGuidePriority} > max=${maxPriority}`,
      );
      return false;
    }
    this.stopGuideAudio();
    return true;
  }

  /** STT(길찾아줘/물어볼게) 상호작용 중 여부. 비프/햅틱 게이트용. */
  public isSttActive(): boolean {
    return this.sttActive;
  }

  /**
   * STT 상호작용 구간 활성화/비활성화.
   * 활성 시 STT 미만 위험/일반 안내는 canStartGuide에서 드롭한다.
   * 2026-07-20: Near 반사 비프/햅틱은 끄지 않는다(필드 테스트 - 길찾기 중 Near 침묵 방지).
   * 반사 음성 클립(playReflexClip)만 STT 중 억제해 질문 답변과 말이 겹치지 않게 한다.
   *
   * 호출 지점(CameraView.tsx 녹음 시작, useWebSocket.ts 응답 수신 전후)과 무관하게
   * STT_SAFETY_TIMEOUT_MS 안전 상한을 여기서 일괄 건다(2026-07-20). 이전에는 녹음
   * 시작 직후 setSttActive(true)에는 백스톱이 없어, 응답이 끝내 오지 않으면(외부망
   * 유실 등) 억제 상태가 영구히 풀리지 않아 햅틱·비프·안내가 조용히 죽는 결함이 있었다.
   */
  public setSttActive(active: boolean): void {
    this.sttActive = active;
    if (this.sttSafetyTimer) {
      clearTimeout(this.sttSafetyTimer);
      this.sttSafetyTimer = null;
    }
    if (active) {
      // Near 비프는 유지. 대기 중인 인지/기타 안내만 폐기(질문 방해 방지).
      this.discardPendingGuidesBelow(GUIDE_PRIORITY.STT);
      this.sttSafetyTimer = setTimeout(() => {
        console.log("[AudioEngine] STT 안전 상한 타이머 - 상태 강제 해제");
        this.setSttActive(false);
      }, STT_SAFETY_TIMEOUT_MS);
    }
    // 재생 중인 STT 답변 우선순위를 여기서 지우면 초단시간 폐기 직후 위험 안내가 끼어든다.
    if (!active && !this.isGuidePlaying) {
      this.activeGuidePriority = 0;
    }
    console.log(`[AudioEngine] STT 상호작용 ${active ? "활성화" : "비활성화"}`);
  }

  /**
   * 가이드 음성 재생 우선순위 판정.
   * STT 활성 중에는 STT 미만 인지/일반 안내만 드롭한다(질문 방해 금지).
   * Near 반사 비프·햅틱은 playBeep/haptic 경로에서 STT와 병행(2026-07-20).
   * 재생 중인 항목보다 낮은 우선순위도 더 이상 즉시 드롭하지 않고 대기열 적재
   * 후보로 넘긴다 - 큐가 우선순위 혼합을 담아야 위험도 기반 폐기(evictLowestPriority)가
   * 의미를 가진다. 상위/동일/하위 판정은 enqueueGuide가 담당한다.
   */
  private canStartGuide(priority: GuidePriority): boolean {
    if (this.sttActive && priority < GUIDE_PRIORITY.STT) {
      console.log(
        `[AudioEngine] STT 상호작용 중 - 위험/일반 안내 드롭(priority=${priority} < STT=${GUIDE_PRIORITY.STT})`,
      );
      return false;
    }
    return true;
  }

  private setGuidePriority(priority: GuidePriority): void {
    this.activeGuidePriority = priority;
  }

  /** 대기열에서 minPriority 미만 항목을 폐기한다. */
  private discardPendingGuidesBelow(minPriority: GuidePriority): void {
    if (this.pendingGuides.length === 0) return;
    const kept: PendingGuideItem[] = [];
    let dropped = 0;
    for (const item of this.pendingGuides) {
      if (item.priority >= minPriority) {
        kept.push(item);
      } else {
        dropped += 1;
        item.onComplete?.();
      }
    }
    this.pendingGuides = kept;
    if (dropped > 0) {
      console.log(
        `[AudioEngine] 대기열 ${dropped}건 폐기(minPriority=${minPriority}), 잔여=${kept.length}`,
      );
    }
  }

  /** 대기열 전체 폐기. */
  private clearPendingGuides(): void {
    if (this.pendingGuides.length === 0) return;
    const dropped = this.pendingGuides.splice(0);
    for (const item of dropped) {
      item.onComplete?.();
    }
    console.log(`[AudioEngine] 대기열 전체 폐기: ${dropped.length}건`);
  }

  /**
   * 대기열이 상한(GUIDE_PENDING_MAX)을 넘으면 가장 낮은 우선순위 항목부터 폐기한다.
   * 우선순위가 같으면 먼저 들어온(오래된) 쪽을 버려 최근 상황 정보를 우선 보존한다.
   */
  private evictLowestPriorityPendingGuide(): PendingGuideItem | undefined {
    if (this.pendingGuides.length === 0) return undefined;
    let dropIndex = 0;
    for (let i = 1; i < this.pendingGuides.length; i++) {
      if (this.pendingGuides[i].priority < this.pendingGuides[dropIndex].priority) {
        dropIndex = i;
      }
    }
    const [dropped] = this.pendingGuides.splice(dropIndex, 1);
    return dropped;
  }

  /**
   * Near/인지 음성을 대기열에 넣거나 즉시 재생한다.
   * - 재생 중 + 상위 우선순위(STT 등): 선점 즉시 재생
   * - 재생 중 + 동일/하위: 선점 금지(완주). 동일 우선은 최신으로 교체, 다른 밴드는 유지
   *   (Near 재생 중 Medium 1건 보존 → Near 완주 후 Medium 재생)
   * - 재생 중 + OTHER: 즉시 drop
   * - 유휴: 즉시 재생
   */
  private enqueueGuide(item: PendingGuideItem): void {
    if (!this.canStartGuide(item.priority)) {
      item.onComplete?.();
      return;
    }

    if (this.isGuidePlaying) {
      if (item.priority > this.activeGuidePriority) {
        this.discardPendingGuidesBelow(item.priority);
        void this.playGuideImmediate(item);
        return;
      }
      if (item.priority <= GUIDE_PRIORITY.OTHER) {
        console.log(
          `[AudioEngine] 재생 중 OTHER 안내 즉시 폐기 kind=${item.kind} priority=${item.priority}`,
        );
        item.onComplete?.();
        return;
      }
      // 동일 우선순위만 최신으로 교체. FRONT_NEAR 재생 중 FRONT_MED는 별도 슬롯 유지.
      const kept: PendingGuideItem[] = [];
      let replaced = 0;
      for (const old of this.pendingGuides) {
        if (old.priority === item.priority) {
          old.onComplete?.();
          replaced += 1;
        } else {
          kept.push(old);
        }
      }
      kept.push(item);
      this.pendingGuides = kept;
      while (this.pendingGuides.length > GUIDE_PENDING_MAX) {
        const dropped = this.evictLowestPriorityPendingGuide();
        if (dropped) {
          console.log(
            `[AudioEngine] 대기열 초과(${GUIDE_PENDING_MAX}) - 안내 폐기 kind=${dropped.kind} priority=${dropped.priority}`,
          );
          dropped.onComplete?.();
        }
      }
      console.log(
        `[AudioEngine] 가이드 완주 대기 activePri=${this.activeGuidePriority} ` +
          `queued=${item.kind}/pri=${item.priority} samePriReplaced=${replaced} ` +
          `pending=${this.pendingGuides.length}`,
      );
      return;
    }

    void this.playGuideImmediate(item);
  }

  /**
   * 자연 종료 후 대기열에서 최고 우선순위 1건만 재생한다.
   * OTHER만 폐기하고 FRONT_MED 등은 남겨, Near 완주 후 Medium 1회가 이어지게 한다.
   */
  private drainHighestPriorityPendingGuide(): void {
    if (this.pendingGuides.length === 0) return;
    let bestIndex = this.pendingGuides.length - 1;
    for (let i = this.pendingGuides.length - 2; i >= 0; i--) {
      if (this.pendingGuides[i].priority > this.pendingGuides[bestIndex].priority) {
        bestIndex = i;
      }
    }
    const [best] = this.pendingGuides.splice(bestIndex, 1);
    const leftover = this.pendingGuides.splice(0);
    const kept: PendingGuideItem[] = [];
    let discarded = 0;
    for (const item of leftover) {
      if (item.priority <= GUIDE_PRIORITY.OTHER) {
        item.onComplete?.();
        discarded += 1;
      } else {
        kept.push(item);
      }
    }
    this.pendingGuides = kept;
    if (discarded > 0 || kept.length > 0) {
      console.log(
        `[AudioEngine] 대기 재생 kind=${best.kind} pri=${best.priority} ` +
          `kept=${kept.length} discardedOther=${discarded}`,
      );
    } else {
      console.log(
        `[AudioEngine] 대기 최고 우선순위 재생 kind=${best.kind} priority=${best.priority}`,
      );
    }
    void this.playGuideImmediate(best);
  }

  private notifyGuideFinished(epoch: number, onComplete?: () => void): void {
    if (epoch !== this.guideEpoch) return;
    this.isGuidePlaying = false;
    this.clearGuidePriority();
    this.unduckBeepAfterGuideSpeech();
    onComplete?.();
    this.drainHighestPriorityPendingGuide();
  }

  private async playGuideImmediate(item: PendingGuideItem): Promise<void> {
    if (item.kind === "bytes") {
      await this.playGuideAudioBytesNow(item.wavBytes, item.priority, item.onComplete);
      return;
    }
    this.speakFallbackNow(item.text, item.priority, item.onComplete);
  }

  private clearGuidePriority(): void {
    this.activeGuidePriority = 0;
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
   *
   * 재생 중이면 대기열(최대 6)에 적재하고, 종료 시 최신 1건만 재생한다.
   */
  public async playGuideAudioBytes(
    wavBytes: Uint8Array,
    priority: GuidePriority = GUIDE_PRIORITY.OTHER,
    onComplete?: () => void,
  ): Promise<void> {
    if (!wavBytes || wavBytes.length === 0) {
      onComplete?.();
      return;
    }
    this.enqueueGuide({ kind: "bytes", wavBytes, priority, onComplete });
  }

  private async playGuideAudioBytesNow(
    wavBytes: Uint8Array,
    priority: GuidePriority,
    onComplete?: () => void,
  ): Promise<void> {
    const callTs = Date.now();
    const epoch = ++this.guideEpoch;
    console.log(
      `[AudioEngine][DEBUG] playGuideAudioBytesNow ts=${callTs}, bytes=${wavBytes.length}, priority=${priority}, epoch=${epoch}`,
    );

    // 선점: 단말 TTS가 재생 중이면 중단. 웜 플레이어는 replace()로 소스만 교체.
    Speech.stop();
    await this.ensureSession();
    this.duckBeepForGuideSpeech();

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
      if (epoch !== this.guideEpoch) {
        onComplete?.();
        try {
          file.delete();
        } catch {
          // ignore
        }
        return;
      }
      this.guidePlayer = guidePlayer;
      this.guideFileUri = file.uri;
      this.isGuidePlaying = true;
      this.setGuidePriority(priority);

      guidePlayer.loop = false;
      guidePlayer.replace({ uri: file.uri });
      guidePlayer.volume = 1.0;
      guidePlayer.play();
      console.log(`[AudioEngine][DEBUG] (bytes) 재생 시작 ts=${callTs}, duration=${guidePlayer.duration}s`);

      // 웜 플레이어는 재사용되므로 직전 구독을 반드시 해제한 뒤 새로 건다(위 필드 주석).
      this.guideStatusSubscription?.remove();
      this.guideStatusSubscription = guidePlayer.addListener("playbackStatusUpdate", (status) => {
        if (status.didJustFinish && this.guidePlayer === guidePlayer) {
          console.log(
            `[AudioEngine][DEBUG] (bytes) 자연 종료(didJustFinish) ts=${callTs}, currentTime=${status.currentTime}, duration=${status.duration}`,
          );
          // 웜 플레이어는 remove 하지 않고 음소거만(Hearing Protection 우회 유지).
          try {
            guidePlayer.volume = 0.0;
          } catch {
            // ignore
          }
          if (this.guideFileUri === file.uri) {
            this.guideFileUri = null;
            FileSystem.deleteAsync(file.uri, { idempotent: true }).catch(() => {});
          }
          this.notifyGuideFinished(epoch, onComplete);
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
      this.clearGuidePriority();
      this.unduckBeepAfterGuideSpeech();
      try {
        file.delete();
      } catch {
        // 파일이 생성되지 않은 상태일 수 있음 - 무시
      }
      if (epoch === this.guideEpoch) {
        onComplete?.();
        this.drainHighestPriorityPendingGuide();
      } else {
        onComplete?.();
      }
    }
  }

  /** 단말 ko TTS 후보 점수(높을수록 자연·선호). */
  private scoreKoVoice(voice: Speech.Voice): number {
    const id = `${voice.identifier ?? ""} ${voice.name ?? ""}`.toLowerCase();
    let score = 0;
    if ((voice.language ?? "").toLowerCase().startsWith("ko")) score += 100;
    if (id.includes("neural") || id.includes("wavenet") || id.includes("natural")) score += 50;
    if (id.includes("google")) score += 40;
    if (id.includes("premium") || id.includes("enhanced") || id.includes("quality")) score += 30;
    if (id.includes("female") || id.includes("woman") || id.includes("여자")) score += 10;
    // 2026-07-13 실기기 발견(초반 인사말이 남성 기계음 "Eddy"로 재생됨): iOS의
    // com.apple.eloquence.* 계열(Eddy/Reed/Rocko/Sandy 등)은 90년대풍 합성음 특화
    // 보이스로 반드시 강하게 배제해야 한다. 기존 "compact" 패널티는 Android Google
    // TTS 저품질 로컬 엔진을 겨냥한 규칙이었으나, iOS 기본 여성 음성(Yuna)의 식별자가
    // 정확히 "com.apple.ttsbundle.Yuna-compact" 형태라 이 규칙에 걸려 Eddy보다 낮은
    // 점수를 받는 역효과가 있었다(Eloquence 계열은 "compact"를 포함하지 않아 무감점).
    // "compact" 패널티는 실제로 문제였던 Android에만 적용한다.
    if (id.includes("eloquence")) score -= 80;
    if (Platform.OS === "android" && (id.includes("robot") || id.includes("compact") || id.includes("local"))) {
      score -= 30;
    } else if (id.includes("robot") || id.includes("local")) {
      score -= 30;
    }
    return score;
  }

  /** 설치된 ko 음성 중 가장 덜 기계적인 identifier를 1회 캐시한다. */
  private async ensurePreferredKoVoice(): Promise<string | undefined> {
    if (this.preferredKoVoiceId !== undefined) {
      return this.preferredKoVoiceId ?? undefined;
    }
    try {
      const voices = await Speech.getAvailableVoicesAsync();
      const koVoices = voices.filter((v) =>
        (v.language ?? "").toLowerCase().startsWith("ko"),
      );
      if (koVoices.length === 0) {
        this.preferredKoVoiceId = null;
        return undefined;
      }
      koVoices.sort((a, b) => this.scoreKoVoice(b) - this.scoreKoVoice(a));
      this.preferredKoVoiceId = koVoices[0]?.identifier ?? null;
      console.log(
        `[AudioEngine] 단말 ko TTS 선택: name=${koVoices[0]?.name} id=${this.preferredKoVoiceId}`,
      );
    } catch (e) {
      console.warn("[AudioEngine] 단말 TTS 음성 목록 조회 실패:", e);
      this.preferredKoVoiceId = null;
    }
    return this.preferredKoVoiceId ?? undefined;
  }

  /**
   * 서버 TTS 실패/타임아웃 시 단말 내장 TTS로 안내 문장을 대신 발화한다.
   * (docs/design/reflex_audio_specification.md와 무관 - 인지 경로 전용 폴백.
   * 서버는 여전히 오디오를 생성하지 못했을 뿐 안내 문장 자체는 만들었으므로,
   * 무음 대신 단말이 직접 말해 안내가 사라지는 체감을 없앤다.)
   *
   * 온보딩·SMS 읽어주기 등도 이 경로를 쓰므로, Android 기본 기계음 완화를 위해
   * Google Neural 계열 ko 음성을 우선 선택한다(미설치 시 OS 기본).
   *
   * 재생 중이면 대기열(최대 6)에 적재하고, 종료 시 최신 1건만 재생한다.
   */
  public speakFallback(
    text: string,
    priority: GuidePriority = GUIDE_PRIORITY.OTHER,
    onComplete?: () => void,
  ): void {
    if (!text || !text.trim()) {
      onComplete?.();
      return;
    }
    this.enqueueGuide({ kind: "fallback", text, priority, onComplete });
  }

  private speakFallbackNow(
    text: string,
    priority: GuidePriority,
    onComplete?: () => void,
  ): void {
    const callId = ++this._speakCallSeq;
    const callTs = Date.now();
    console.log(
      `[AudioEngine][DEBUG] speakFallbackNow id=${callId} ts=${callTs} text="${text}" priority=${priority}`,
    );

    void (async () => {
      const voice = await this.ensurePreferredKoVoice();

      // 이전 재생만 중단. 대기열은 유지(선점 시 enqueue가 이미 정리함).
      // stopGuideAudio가 guideEpoch를 올려 이전 Speech/bytes 콜백을 무효화한다.
      this.stopGuideAudio({ clearPending: false });
      const playEpoch = this.guideEpoch;

      this.isGuidePlaying = true;
      this.setGuidePriority(priority);
      this.duckBeepForGuideSpeech();
      Speech.speak(text, {
        language: "ko-KR",
        voice,
        pitch: 0.95,
        rate: 0.85,
        onStart: () => {
          console.log(`[AudioEngine][DEBUG] speakFallback onStart id=${callId} ts=${Date.now()}`);
        },
        onBoundary: (event: any) => {
          // 2026-07-28: 음절 경계마다 console.log를 내보내면 발화 1회에 수십 건이
          // Metro 브릿지로 나간다. 하필 이 구간이 프레임·추론 처리량이 떨어지는
          // 구간이라 계측을 왜곡하고 부하를 더한다. 기본 비활성, 필요 시 상수만 켠다.
          if (!SPEAK_BOUNDARY_DEBUG) return;
          const idx = event?.charIndex ?? -1;
          const len = event?.charLength ?? 0;
          const chunk = idx >= 0 ? text.slice(idx, idx + len) : "?";
          console.log(
            `[AudioEngine][DEBUG] speakFallback onBoundary id=${callId} ts=${Date.now()} charIndex=${idx} charLength=${len} chunk="${chunk}"`,
          );
        },
        onDone: () => {
          console.log(`[AudioEngine][DEBUG] speakFallback onDone id=${callId} ts=${Date.now()}`);
          this.notifyGuideFinished(playEpoch, onComplete);
        },
        onStopped: () => {
          console.log(`[AudioEngine][DEBUG] speakFallback onStopped id=${callId} ts=${Date.now()}`);
          // 선점/중단(epoch 불일치): onComplete·drain 모두 생략.
          // 자연 종료는 onDone에서 처리한다.
          if (playEpoch !== this.guideEpoch) return;
          this.isGuidePlaying = false;
          this.clearGuidePriority();
          this.unduckBeepAfterGuideSpeech();
          onComplete?.();
        },
        onError: (err) => {
          console.error(`[AudioEngine] 단말 TTS 폴백 실패 id=${callId}:`, err);
          this.notifyGuideFinished(playEpoch, onComplete);
        },
      });
    })();
  }

  /**
   * 재생 중인 안내 음성을 즉시 중단하고 플레이어/임시 파일을 정리한다.
   * @param clearPending true(기본)면 대기열도 폐기. 내부 선점 재생 시에는 false.
   */
  public stopGuideAudio(options?: { clearPending?: boolean }): void {
    const clearPending = options?.clearPending !== false;
    this.guideEpoch += 1;
    Speech.stop();

    if (clearPending) {
      this.clearPendingGuides();
    }

    const prevPlayer = this.guidePlayer;
    const prevFileUri = this.guideFileUri;
    // [TEMP DEBUG 2026-07-09] 짤림 원인 진단용 - 재현 확인 후 제거
    if (prevPlayer) {
      try {
        console.log(
          `[AudioEngine][DEBUG] stopGuideAudio 호출 - currentTime=${prevPlayer.currentTime}s / duration=${prevPlayer.duration}s (${prevPlayer.currentTime < prevPlayer.duration - 0.3 ? "조기 중단 의심!" : "정상 종료 근처"})`,
        );
      } catch {
        console.log("[AudioEngine][DEBUG] stopGuideAudio 호출 - player 상태 조회 실패");
      }
    }
    this.guidePlayer = null;
    this.guideFileUri = null;
    this.isGuidePlaying = false;
    this.clearGuidePriority();

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
   * 반사 경로 사전합성 음성 클립을 1회 재생한다(비프/햅틱과 별개 채널).
   * clipPath는 서버 reflex_alert 페이로드의 clip 필드(예: "reflex_clips/high_front.wav").
   *
   * 호출측(useWebSocket) 정책 (2026-07-21):
   * - Mid/Low(beep_interval_ms>100): 매 반사마다 클립.
   * - Near 긴급(<=100) update: 클립 없음(비프+햅틱만).
   * - Near episode enter: 클립 1회(다음 행동 단서). 재생 중 비프는 덕킹.
   */
  public async playReflexClip(clipPath: string): Promise<void> {
    if (this.sttActive) {
      console.log("[AudioEngine] STT 상호작용 중 - 반사 음성 클립 억제");
      return;
    }

    const basename = clipPath.split("/").pop() ?? "";
    const uri = await this.resolveReflexClipUri(basename);
    if (!uri) {
      console.warn(`[AudioEngine] 알 수 없는 반사 클립: ${clipPath}`);
      return;
    }

    try {
      await this.ensureSession();
      // 2026-07-21: 인지/Near 말 안내 재생 중에는 반사 클립이 안내를 끊지 않는다.
      // (실측: enter 클립이 FRONT_NEAR guide를 0초대에 stop → "안 들림").
      // 비프·햅틱은 useWebSocket에서 그대로 유지. STT만 상위 선점.
      if (this.isGuidePlaying && this.activeGuidePriority >= GUIDE_PRIORITY.FRONT_MED) {
        console.log(
          `[AudioEngine] 가이드 재생 중(pri=${this.activeGuidePriority}) - 반사 클립 생략(완주 우선)`,
        );
        return;
      }
      if (
        this.isGuidePlaying &&
        this.activeGuidePriority > 0 &&
        this.activeGuidePriority < GUIDE_PRIORITY.FRONT_MED
      ) {
        // OTHER 온보딩 등만 반사 클립이 선점 가능
        this.stopGuideAudio();
      }
      this.beginReflexClipDucking();
      // 직전 클립이 남아 있으면(완주 실패) 먼저 회수한다.
      this.disposeReflexClipPlayer();
      const clipPlayer = createAudioPlayer(uri);
      this.reflexClipPlayer = clipPlayer;
      clipPlayer.volume = 1.0;
      this.reflexClipSubscription = clipPlayer.addListener("playbackStatusUpdate", (status) => {
        if (status.didJustFinish) {
          this.disposeReflexClipPlayer();
          this.endReflexClipDucking();
        }
      });
      clipPlayer.play();
      // didJustFinish 미도착 대비 안전 회수. 클립은 짧은 사전합성 WAV이므로
      // duration을 못 읽어도 상한(REFLEX_CLIP_REAP_MAX_MS)으로 충분하다.
      const durationMs = Number.isFinite(clipPlayer.duration)
        ? Math.round(clipPlayer.duration * 1000)
        : 0;
      const reapAfter = Math.min(
        REFLEX_CLIP_REAP_MAX_MS,
        Math.max(REFLEX_CLIP_REAP_MIN_MS, durationMs + 500),
      );
      this.reflexClipReapTimer = setTimeout(() => {
        this.reflexClipReapTimer = null;
        if (this.reflexClipPlayer === clipPlayer) {
          this.disposeReflexClipPlayer();
          this.endReflexClipDucking();
        }
      }, reapAfter);
    } catch (err) {
      this.endReflexClipDucking();
      console.error("[AudioEngine] 반사 클립 재생 실패:", err);
    }
  }

  /** 반사 클립 플레이어와 그 리스너·안전 타이머를 회수한다(중복 호출 안전). */
  private disposeReflexClipPlayer(): void {
    if (this.reflexClipReapTimer) {
      clearTimeout(this.reflexClipReapTimer);
      this.reflexClipReapTimer = null;
    }
    this.reflexClipSubscription?.remove();
    this.reflexClipSubscription = null;
    const player = this.reflexClipPlayer;
    this.reflexClipPlayer = null;
    if (player) {
      try {
        player.remove();
      } catch (err) {
        console.error("[AudioEngine] 반사 클립 플레이어 정리 실패:", err);
      }
    }
  }

  /** STT 종료 신호음 로컬 번들 자산 URI를 1회만 리졸브하고 캐시한다. */
  private async resolveSttEndCueUri(): Promise<string | null> {
    if (this.sttEndCueUri) return this.sttEndCueUri;

    const asset = Asset.fromModule(this.STT_END_CUE_SRC);
    if (!asset.localUri) {
      await asset.downloadAsync();
    }
    const uri = asset.localUri || asset.uri;
    if (!uri) return null;
    this.sttEndCueUri = uri;
    return uri;
  }

  /** STT 신호음 상시 재생 플레이어를 지연 초기화한다(무음 placeholder, volume=0.0 루프). */
  private async ensureSttCueWarmPlayer(): Promise<AudioPlayer | null> {
    if (this.sttCueWarmPlayer) return this.sttCueWarmPlayer;
    try {
      const asset = Asset.fromModule(this.SILENCE_SRC);
      if (!asset.localUri) {
        await asset.downloadAsync();
      }
      const sourceUri = asset.localUri || asset.uri;
      if (!sourceUri) {
        throw new Error("STT 신호음 무음 placeholder 에셋 URI 생성 실패");
      }

      const player = createAudioPlayer(sourceUri);
      player.loop = true;
      player.volume = 0.0;
      player.play();
      this.sttCueWarmPlayer = player;
      return player;
    } catch (err) {
      console.error("[AudioEngine] STT 신호음 상시 재생 플레이어 생성 실패:", err);
      return null;
    }
  }

  /** STT 시작 신호음 로컬 번들 자산 URI를 1회만 리졸브하고 캐시한다. */
  private async resolveSttStartCueUri(): Promise<string | null> {
    if (this.sttStartCueUri) return this.sttStartCueUri;

    const asset = Asset.fromModule(this.STT_START_CUE_SRC);
    if (!asset.localUri) {
      await asset.downloadAsync();
    }
    const uri = asset.localUri || asset.uri;
    if (!uri) return null;
    this.sttStartCueUri = uri;
    return uri;
  }

  /**
   * STT 녹음 시작 신호음(단일 상승 비프). 반드시 AEC(voiceChat 세션) 활성이 확인된
   * 뒤에만 호출할 것 - AEC 없이 녹음 중 재생하면 신호음이 마이크에 그대로 녹음되어
   * "입력 없음" 회귀가 재발한다(2026-07-11 파형 분석으로 확인된 음향 블리드).
   */
  public async playSttStartCue(): Promise<void> {
    const uri = await this.resolveSttStartCueUri();
    if (!uri) {
      console.warn("[AudioEngine] STT 시작 신호음 에셋 없음");
      return;
    }
    try {
      await this.ensureSession();
      const player = await this.ensureSttCueWarmPlayer();
      if (!player) return;
      player.loop = false;
      player.replace({ uri });
      player.volume = 1.0;
      player.play();
    } catch (err) {
      console.error("[AudioEngine] STT 시작 신호음 재생 실패:", err);
    }
  }

  /** STT 녹음이 실제로 종료되는 순간 재생하는 더블 비프 신호음(종료점 안내). */
  public async playSttEndCue(): Promise<void> {
    const uri = await this.resolveSttEndCueUri();
    if (!uri) {
      console.warn("[AudioEngine] STT 종료 신호음 에셋 없음");
      return;
    }
    try {
      await this.ensureSession();
      const player = await this.ensureSttCueWarmPlayer();
      if (!player) return;
      player.loop = false;
      player.replace({ uri });
      player.volume = 1.0;
      player.play();
    } catch (err) {
      console.error("[AudioEngine] STT 종료 신호음 재생 실패:", err);
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
