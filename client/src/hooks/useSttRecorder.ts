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
import { audioEngine } from "../services/audioEngine";

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
  onError?: (reason: "permission_denied" | "start_failed", detail?: string) => void,
): UseSttRecorderReturn {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [status, setStatus] = useState<SttCaptureStatus>("idle");
  const statusRef = useRef<SttCaptureStatus>("idle");
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
        await recorder.prepareToRecordAsync();
        recorder.record();
        statusRef.current = "recording";
        setStatus("recording");
        // 시각장애인 사용자에게 실제 녹음 시작 순간을 신호음으로 알림(진입점 안내).
        void audioEngine.playSttStartCue();
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
      // 실제 녹음이 종료된 직후 신호음으로 알림(종료점 안내). 시작음(단일 고음)과
      // 구분되는 더블 비프 패턴을 사용해 시각장애인 사용자가 두 시점을 혼동하지 않게 한다.
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
      onAudioReady(audioB64);
    } catch (err) {
      console.error("[STT] 녹음 종료/전송 실패:", err);
      onError?.("start_failed", err instanceof Error ? err.message : String(err));
    } finally {
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
