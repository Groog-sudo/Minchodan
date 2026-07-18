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
import { setVoiceProcessing } from "../services/audioSessionBridge";

// 시작 신호음은 AEC/세션 전환과 겹치면 지연·먹통을 키우므로 기본 비활성.
// (필요 시 true로 되돌리되, record() 직후 세션 재적용은 하지 않는다.)
const STT_START_CUE_WITH_AEC = false;

// 16kHz PCM: Whisper 입력에 가깝고, 44.1kHz 대비 전송/인코딩 부담이 작다.
const STT_RECORDING_OPTIONS: RecordingOptions = {
  extension: Platform.OS === "ios" ? ".wav" : ".m4a",
  sampleRate: 16000,
  numberOfChannels: 1,
  bitRate: 64000,
  ios: {
    outputFormat: IOSOutputFormat.LINEARPCM,
    audioQuality: AudioQuality.HIGH,
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
    bitsPerSecond: 64000,
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
  // prepare await 전 idle 상태에서 중첩 start가 들어오면 AEC 폭주 → 동기 락.
  const startInFlightRef = useRef(false);
  const recordStartTsRef = useRef<number>(0);
  const pendingStartRef = useRef<Promise<void> | null>(null);
  const preparedRef = useRef(false);

  const ensurePermission = useCallback(async (): Promise<boolean> => {
    const current = await getRecordingPermissionsAsync();
    if (current.granted) return true;
    const result = await requestRecordingPermissionsAsync();
    return result.granted;
  }, []);

  const warmPrepare = useCallback(async (): Promise<void> => {
    if (preparedRef.current) return;
    try {
      await recorder.prepareToRecordAsync();
      preparedRef.current = true;
      console.log("[STT] recorder warm-prepare 완료");
    } catch (err) {
      console.warn("[STT] warm-prepare 실패(무시):", err);
    }
  }, [recorder]);

  const startRecording = useCallback(async (): Promise<void> => {
    if (startInFlightRef.current || statusRef.current !== "idle") return;
    startInFlightRef.current = true;
    const run = (async () => {
      const granted = await ensurePermission();
      if (!granted) {
        console.warn("[STT] 마이크 권한 거부됨");
        onError?.("permission_denied");
        return;
      }
      try {
        const aecInfo = await setVoiceProcessing(true);
        if (aecInfo) {
          console.log(
            `[STT][AEC] 세션 전환: mode=${aecInfo.mode}, aec=${aecInfo.voiceProcessingActive}, route=${aecInfo.outputRoute}`,
          );
        }
        if (!startInFlightRef.current) {
          void setVoiceProcessing(false);
          return;
        }
        if (!preparedRef.current) {
          await recorder.prepareToRecordAsync();
          preparedRef.current = true;
        }
        if (!startInFlightRef.current) {
          void setVoiceProcessing(false);
          return;
        }
        recorder.record();
        recordStartTsRef.current = Date.now();
        console.log(
          `[STT] 녹음 시작: guidePlaying=${audioEngine.isGuidePlaying}, ts=${recordStartTsRef.current}`,
        );
        statusRef.current = "recording";
        setStatus("recording");
        if (STT_START_CUE_WITH_AEC) {
          void audioEngine.playSttStartCue();
        }
      } catch (err) {
        console.error("[STT] 녹음 시작 실패:", err);
        preparedRef.current = false;
        statusRef.current = "idle";
        setStatus("idle");
        void setVoiceProcessing(false);
        onError?.("start_failed", err instanceof Error ? err.message : String(err));
      }
    })();
    pendingStartRef.current = run;
    await run;
    pendingStartRef.current = null;
    if (statusRef.current === "idle") {
      startInFlightRef.current = false;
    }
  }, [recorder, ensurePermission, onError]);

  const stopRecordingAndSend = useCallback(async (): Promise<void> => {
    if (statusRef.current === "idle" && startInFlightRef.current) {
      startInFlightRef.current = false;
      if (pendingStartRef.current) {
        await pendingStartRef.current;
      }
      void setVoiceProcessing(false);
      return;
    }
    if (pendingStartRef.current) {
      await pendingStartRef.current;
    }
    if (statusRef.current !== "recording") {
      startInFlightRef.current = false;
      return;
    }
    statusRef.current = "sending";
    setStatus("sending");
    try {
      await recorder.stop();
      preparedRef.current = false;
      await setVoiceProcessing(false);
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
      const holdMs =
        recordStartTsRef.current > 0 ? Date.now() - recordStartTsRef.current : 0;
      if (Platform.OS === "ios") {
        const capturedSec = Math.max(0, (audioB64.length * 0.75 - 44) / (16000 * 2));
        console.log(
          `[STT] 녹음 완료(iOS PCM 16k): hold=${(holdMs / 1000).toFixed(2)}s, captured=${capturedSec.toFixed(2)}s, b64_len=${audioB64.length}`,
        );
      } else {
        console.log(
          `[STT] 녹음 완료(${Platform.OS}): hold=${(holdMs / 1000).toFixed(2)}s, b64_len=${audioB64.length}`,
        );
      }
      onAudioReady(audioB64);
      // 다음 누름을 빠르게 하기 위해 백그라운드 warm-prepare
      void warmPrepare();
    } catch (err) {
      console.error("[STT] 녹음 종료/전송 실패:", err);
      preparedRef.current = false;
      void setVoiceProcessing(false);
      onError?.("start_failed", err instanceof Error ? err.message : String(err));
    } finally {
      recordStartTsRef.current = 0;
      startInFlightRef.current = false;
      statusRef.current = "idle";
      setStatus("idle");
    }
  }, [recorder, onAudioReady, onError, warmPrepare]);

  const requestPermissionEarly = useCallback(async (): Promise<void> => {
    const granted = await ensurePermission();
    if (granted) {
      void warmPrepare();
    }
  }, [ensurePermission, warmPrepare]);

  return { status, startRecording, stopRecordingAndSend, requestPermissionEarly };
}
