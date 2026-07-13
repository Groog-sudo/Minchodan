/**
 * STT 음성 명령 캡처 훅.
 * 마이크로 녹음한 오디오를 base64로 인코딩해 서버에 전달할 준비만 한다.
 * "서버: GPU 서버에서 모든 추론 수행" 원칙에 따라 단말은 오디오 캡처만 담당하고
 * 실제 음성 인식(faster-whisper)은 서버(server/api/ws_router.py의 stt_audio 핸들러)가
 * 수행한다 - 단말 내 SFSpeechRecognizer 등 온디바이스 STT는 사용하지 않는다.
 */

import { useCallback, useRef, useState } from "react";
import {
  AudioQuality,
  getRecordingPermissionsAsync,
  IOSOutputFormat,
  requestRecordingPermissionsAsync,
  useAudioRecorder,
  type RecordingOptions,
} from "expo-audio";
import * as FileSystem from "expo-file-system/legacy";
import { Platform } from "react-native";

import { audioEngine } from "../services/audioEngine";
import { getSessionInfo, setVoiceProcessing } from "../services/audioSessionBridge";

// 2026-07-11 AEC 검증(Mitos 로드맵 우선순위 4): AEC(voiceChat 세션) 활성이 확인된
// 경우에 한해 녹음 시작 신호음을 복원한다. 실기기 검증에서 신호음이 다시 전사에
// 섞이는 회귀가 확인되면 이 플래그만 false로 되돌린다(AEC 전환 자체는 유지).
const STT_START_CUE_WITH_AEC = true;

// [TEMP DEBUG 2026-07-11] "입력이 없어" 재현 진단용: recorder.record()~stop()이
// JS에서는 2.6~3.6초로 측정되는데도 실제 인코딩된 .m4a(AAC) 파일에는 0.2~0.7초
// 분량만 담기는 현상을 실기기 실측(afinfo)으로 확인했다. AAC 하드웨어 인코더
// 세션 자체의 문제인지 격리하기 위해 Linear PCM(무압축)으로 임시 전환한다.
const STT_RECORDING_OPTIONS: RecordingOptions = {
  extension: Platform.OS === "ios" ? ".wav" : ".m4a",
  sampleRate: 44100,
  numberOfChannels: 1,
  bitRate: 128000,
  ios: {
    outputFormat: IOSOutputFormat.LINEARPCM,
    audioQuality: AudioQuality.MAX,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  android: {
    outputFormat: "mpeg4",
    audioEncoder: "aac",
  },
  web: {
    mimeType: "audio/webm",
    bitsPerSecond: 128000,
  },
};

export type SttCaptureStatus = "idle" | "recording" | "sending";

export interface UseSttRecorderReturn {
  status: SttCaptureStatus;
  startRecording: () => Promise<void>;
  stopRecordingAndSend: () => Promise<void>;
  requestPermissionEarly: () => Promise<void>;
}

/**
 * @param onAudioReady 녹음 완료 후 base64 오디오 데이터를 전달받는 콜백 (WS 전송은 호출측 책임)
 * @param onError Release 빌드에서는 console 출력이 보이지 않아, 녹음 시작/권한 실패를
 *   호출측(햅틱 등 물리 신호)이 구분할 수 있도록 별도로 알려준다. (2026-07-10 추가)
 */
export function useSttRecorder(
  onAudioReady: (audioB64: string) => void,
  onError?: (
    reason: "permission_denied" | "start_failed" | "capture_truncated",
    detail?: string,
  ) => void,
): UseSttRecorderReturn {
  const recorder = useAudioRecorder(STT_RECORDING_OPTIONS);
  const [status, setStatus] = useState<SttCaptureStatus>("idle");
  const statusRef = useRef<SttCaptureStatus>("idle");
  // 2026-07-11: press-and-hold 시간 대비 실제 캡처된 오디오 길이를 대조해
  // 오디오 세션 인터럽션으로 인한 캡처 결함(수 초 홀드에 0.1~0.7초 무음 파일)을
  // 서버 왕복 전에 단말에서 감지하기 위한 기준 시각.
  const recordStartTsRef = useRef<number>(0);
  // 2026-07-10: press-and-hold를 짧게(탭에 가깝게) 하면 recorder.record()가 실제로
  // 끝나기 전에 onPressOut이 먼저 도착해 stopRecordingAndSend가 "recording이 아님"으로
  // 조용히 무시되는 경쟁 상태를 실기기에서 확인했다 - 진행 중인 시작 작업을 참조해두고
  // 정지 시 먼저 그 완료를 기다린다.
  const pendingStartRef = useRef<Promise<void> | null>(null);

  const ensurePermission = useCallback(async (): Promise<boolean> => {
    const current = await getRecordingPermissionsAsync();
    if (current.granted) return true;
    const result = await requestRecordingPermissionsAsync();
    return result.granted;
  }, []);

  const startRecording = useCallback(async (): Promise<void> => {
    if (statusRef.current !== "idle") return;
    const run = (async () => {
      const granted = await ensurePermission();
      if (!granted) {
        console.warn("[STT] 마이크 권한 거부됨");
        onError?.("permission_denied");
        return;
      }
      try {
        // 2026-07-11 실기기 실측(afinfo + 파형 진폭 분석): 녹음이 활성 상태인 동안
        // 스피커로 어떤 소리든 재생하면(TTS든, 웜 플레이어로 튼 신호음이든) 마이크가
        // 그 소리를 그대로 다시 주워듣는 음향 블리드가 물리적으로 발생한다(하드웨어
        // 에코 제거 없이는 회피 불가). 실제로 "입력 없음" 응답이 반복된 녹음 파일들을
        // 0.05초 단위로 파형 분석한 결과, 신호음이 재생되는 100~250ms 구간에만 짧게
        // 진폭이 있고 그 뒤로는 끝까지 무음이었다 - 사용자의 발화가 아니라 신호음
        // 자체가 녹음되고 있었다.
        // 2026-07-11 AEC 대책: 녹음 구간에서 세션을 voiceChat 모드로 전환하면 iOS가
        // VoiceProcessingIO의 AEC를 켜 스피커 출력을 마이크 입력에서 상쇄한다.
        // 시작 신호음은 아래에서 AEC 활성이 "확인된" 경우에만 복원 재생한다.
        // 전환은 prepare 전에 수행한다(녹음 시작 후 세션 변경은 캡처 절단 위험).
        const aecInfo = await setVoiceProcessing(true);
        if (aecInfo) {
          console.log(
            `[STT][AEC] 세션 전환: mode=${aecInfo.mode}, aec=${aecInfo.voiceProcessingActive}, route=${aecInfo.outputRoute}`,
          );
        }
        await recorder.prepareToRecordAsync();
        recorder.record();
        recordStartTsRef.current = Date.now();
        console.log(
          `[STT] 녹음 시작: guidePlaying=${audioEngine.isGuidePlaying}, ts=${recordStartTsRef.current}`,
        );
        statusRef.current = "recording";
        setStatus("recording");

        // 검증 계측: expo-audio recorder가 record() 시점에 세션 모드를 덮는지 확인.
        // voiceChat이 유지된 경우에만 시작 신호음을 재생한다(AEC 상쇄 전제).
        const postInfo = await getSessionInfo();
        const aecActive = postInfo?.voiceProcessingActive === true;
        if (postInfo) {
          console.log(
            `[STT][AEC] record() 후 세션: mode=${postInfo.mode}, aec=${aecActive}`,
          );
        }
        if (postInfo && !aecActive) {
          console.warn(
            "[STT][AEC] record() 후 voiceChat 모드가 풀림(expo-audio 세션 재설정 추정) - 시작 신호음 생략",
          );
        }
        if (STT_START_CUE_WITH_AEC && aecActive && statusRef.current === "recording") {
          void audioEngine.playSttStartCue();
        }
      } catch (err) {
        console.error("[STT] 녹음 시작 실패:", err);
        statusRef.current = "idle";
        setStatus("idle");
        // 녹음 시작 실패 시 voiceChat 세션이 남지 않도록 복구한다(실패해도 무해).
        void setVoiceProcessing(false);
        onError?.("start_failed", err instanceof Error ? err.message : String(err));
      }
    })();
    pendingStartRef.current = run;
    await run;
    pendingStartRef.current = null;
  }, [recorder, ensurePermission, onError]);

  const stopRecordingAndSend = useCallback(async (): Promise<void> => {
    if (pendingStartRef.current) {
      await pendingStartRef.current;
    }
    if (statusRef.current !== "recording") return;
    statusRef.current = "sending";
    setStatus("sending");
    try {
      await recorder.stop();
      // 녹음이 끝났으므로 voiceChat(AEC) 세션을 원래 설정으로 복구한다. voiceChat
      // 유지 시 재생 음질/음량이 저하되므로 종료 신호음 재생 전에 복구한다.
      await setVoiceProcessing(false);
      // 녹음이 완전히 끝난 뒤라 마이크와 무관하다 - 종료 신호음(더블 비프)을 재생한다.
      void audioEngine.playSttEndCue();
      const uri = recorder.uri;
      if (!uri) {
        console.warn("[STT] 녹음 파일 URI 없음");
        onError?.("start_failed", "녹음 파일 URI 없음");
        return;
      }
      const audioB64 = await FileSystem.readAsStringAsync(uri, {
        encoding: FileSystem.EncodingType.Base64,
      });
      // holdMs 계측: 로그/디버그용으로만 사용한다.
      // capture_truncated 가드 제거(2026-07-13): 서버 Whisper vad_filter=True가 무음/짧은
      // 오디오를 걸러주므로 클라이언트에서 이중 차단은 불필요하다. 이 가드가 "길댕아"처럼
      // 짧은 웨이크워드를 서버 전송 전에 차단하는 원인이었음을 실측으로 확인.
      const holdMs =
        recordStartTsRef.current > 0 ? Date.now() - recordStartTsRef.current : 0;
      if (Platform.OS === "ios") {
        const capturedSec = Math.max(0, (audioB64.length * 0.75 - 44) / (44100 * 2));
        console.log(
          `[STT] 녹음 완료(iOS PCM): hold=${(holdMs / 1000).toFixed(2)}s, captured=${capturedSec.toFixed(2)}s, b64_len=${audioB64.length}`,
        );
      } else {
        console.log(
          `[STT] 녹음 완료(${Platform.OS}): hold=${(holdMs / 1000).toFixed(2)}s, b64_len=${audioB64.length}`,
        );
      }
      onAudioReady(audioB64);
    } catch (err) {
      console.error("[STT] 녹음 종료/전송 실패:", err);
      // stop() 실패 경로에서도 voiceChat 세션이 남지 않도록 복구한다.
      void setVoiceProcessing(false);
      onError?.("start_failed", err instanceof Error ? err.message : String(err));
    } finally {
      recordStartTsRef.current = 0;
      statusRef.current = "idle";
      setStatus("idle");
    }
  }, [recorder, onAudioReady, onError]);

  // 2026-07-10: 네이티브 권한 다이얼로그가 뜨는 동안 진행 중이던 press-and-hold 터치가
  // 시스템에 의해 취소되어(onPressOut 미발화) 첫 시도가 항상 무음으로 끝나는 문제를
  // 실기기에서 확인했다 - 제스처 도중이 아니라 화면 진입 시 미리 권한을 확보해둔다.
  const requestPermissionEarly = useCallback(async (): Promise<void> => {
    await ensurePermission();
  }, [ensurePermission]);

  return { status, startRecording, stopRecordingAndSend, requestPermissionEarly };
}
