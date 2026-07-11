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
        // 자체가 녹음되고 있었다. 시작 신호음은 녹음 중 재생 자체를 하지 않는다
        // (진입점 안내는 이미 있는 haptic 피드백이 담당). 종료 신호음은
        // recorder.stop() 완료 이후에만 재생되므로 이 문제가 없다.
        await recorder.prepareToRecordAsync();
        recorder.record();
        recordStartTsRef.current = Date.now();
        console.log(
          `[STT] 녹음 시작: guidePlaying=${audioEngine.isGuidePlaying}, ts=${recordStartTsRef.current}`,
        );
        statusRef.current = "recording";
        setStatus("recording");
      } catch (err) {
        console.error("[STT] 녹음 시작 실패:", err);
        statusRef.current = "idle";
        setStatus("idle");
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
      // iOS LINEARPCM 44.1kHz mono 16bit만 base64 길이로 캡처 시간을 역산할 수 있다.
      // Android MPEG-4/AAC는 압축률이 달라 같은 공식을 적용하면 정상 녹음도 잘린 파일로
      // 오판하므로, Android는 서버 디코더/VAD 검증에 맡긴다.
      const holdMs =
        recordStartTsRef.current > 0 ? Date.now() - recordStartTsRef.current : 0;
      if (Platform.OS === "ios") {
        const capturedSec = Math.max(0, (audioB64.length * 0.75 - 44) / (44100 * 2));
        console.log(
          `[STT] 녹음 완료(iOS PCM): hold=${(holdMs / 1000).toFixed(2)}s, captured=${capturedSec.toFixed(2)}s`,
        );
        if (holdMs >= 800 && capturedSec < (holdMs / 1000) * 0.5) {
          console.warn(
            `[STT] 캡처 결함 감지(세션 인터럽션 의심): hold=${(holdMs / 1000).toFixed(2)}s, ` +
              `captured=${capturedSec.toFixed(2)}s - 서버 전송 생략, 재시도 안내`,
          );
          onError?.(
            "capture_truncated",
            `hold=${(holdMs / 1000).toFixed(2)}s captured=${capturedSec.toFixed(2)}s`,
          );
          audioEngine.speakFallback("다시 말씀해 주세요");
          return;
        }
      } else {
        console.log(`[STT] 녹음 완료(${Platform.OS} 압축 오디오): hold=${(holdMs / 1000).toFixed(2)}s`);
      }
      onAudioReady(audioB64);
    } catch (err) {
      console.error("[STT] 녹음 종료/전송 실패:", err);
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
