import { useCallback, useMemo, useRef } from "react";
import type { FrameCaptureProvider, FrameData } from "./frameCapture";
import type { StreamType } from "../types/detection";
import { getFrameProvider } from "./frameProvider";

export function useFrameCaptureProvider(
  cameraRef: React.RefObject<any>,
  intervalSharedValue: any,
  lastCaptureTsShared: any
): FrameCaptureProvider {
  const onFrameRef = useRef<((frame: FrameData) => void) | null>(null);

  const capturePhoto = useCallback(
    async (stream: StreamType): Promise<FrameData | null> => {
      const provider = getFrameProvider();
      if (!provider) return null;
      try {
        const float32 = await provider.getFrame();
        return { float32, stream, base64: null, jpegBytes: null };
      } catch (err) {
        console.error(`[Camera/Mock] ${stream} 프레임 오류:`, err);
        return null;
      }
    },
    []
  );

  const startStream = useCallback(
    (onFrame: (frame: FrameData) => void, intervalMs: number): boolean => {
      onFrameRef.current = onFrame;
      console.log("[Camera/Mock] 스트림 모드가 지원되지 않아 타이머 폴백 모드로 동작합니다.");
      return false;
    },
    []
  );

  const stop = useCallback(() => {
    onFrameRef.current = null;
  }, []);

  return useMemo(() => ({
    startStream,
    capturePhoto,
    supportsStream: false,
    stop,
  }), [startStream, capturePhoto, stop]);
}
