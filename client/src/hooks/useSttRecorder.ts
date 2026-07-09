/**
 * STT 음성 명령 캡처 훅.
 * 마이크로 녹음한 오디오를 base64로 인코딩해 서버에 전달할 준비만 한다.
 * "서버: GPU 서버에서 모든 추론 수행" 원칙에 따라 단말은 오디오 캡처만 담당하고
 * 실제 음성 인식(faster-whisper)은 서버(server/api/ws_router.py의 stt_audio 핸들러)가
 * 수행한다 - 단말 내 SFSpeechRecognizer 등 온디바이스 STT는 사용하지 않는다.
 */

import { useCallback, useRef, useState } from "react";
import {
  getRecordingPermissionsAsync,
  RecordingPresets,
  requestRecordingPermissionsAsync,
  useAudioRecorder,
} from "expo-audio";
import * as FileSystem from "expo-file-system/legacy";

export type SttCaptureStatus = "idle" | "recording" | "sending";

export interface UseSttRecorderReturn {
  status: SttCaptureStatus;
  startRecording: () => Promise<void>;
  stopRecordingAndSend: () => Promise<void>;
}

/** @param onAudioReady 녹음 완료 후 base64 오디오 데이터를 전달받는 콜백 (WS 전송은 호출측 책임) */
export function useSttRecorder(onAudioReady: (audioB64: string) => void): UseSttRecorderReturn {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [status, setStatus] = useState<SttCaptureStatus>("idle");
  const statusRef = useRef<SttCaptureStatus>("idle");

  const ensurePermission = useCallback(async (): Promise<boolean> => {
    const current = await getRecordingPermissionsAsync();
    if (current.granted) return true;
    const result = await requestRecordingPermissionsAsync();
    return result.granted;
  }, []);

  const startRecording = useCallback(async (): Promise<void> => {
    if (statusRef.current !== "idle") return;
    const granted = await ensurePermission();
    if (!granted) {
      console.warn("[STT] 마이크 권한 거부됨");
      return;
    }
    try {
      await recorder.prepareToRecordAsync();
      recorder.record();
      statusRef.current = "recording";
      setStatus("recording");
    } catch (err) {
      console.error("[STT] 녹음 시작 실패:", err);
      statusRef.current = "idle";
      setStatus("idle");
    }
  }, [recorder, ensurePermission]);

  const stopRecordingAndSend = useCallback(async (): Promise<void> => {
    if (statusRef.current !== "recording") return;
    statusRef.current = "sending";
    setStatus("sending");
    try {
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) {
        console.warn("[STT] 녹음 파일 URI 없음");
        return;
      }
      const audioB64 = await FileSystem.readAsStringAsync(uri, {
        encoding: FileSystem.EncodingType.Base64,
      });
      onAudioReady(audioB64);
    } catch (err) {
      console.error("[STT] 녹음 종료/전송 실패:", err);
    } finally {
      statusRef.current = "idle";
      setStatus("idle");
    }
  }, [recorder, onAudioReady]);

  return { status, startRecording, stopRecordingAndSend };
}
