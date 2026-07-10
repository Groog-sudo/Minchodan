import { useCallback, useMemo, useRef } from "react";
import {
  type Frame,
  type FrameProcessorPlugin,
  type PhotoFile,
  useFrameProcessor,
  VisionCameraProxy,
} from "react-native-vision-camera";
import { useRunOnJS } from "react-native-worklets-core";
import * as FileSystem from "expo-file-system/legacy";
import { File } from "expo-file-system";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import type { FrameCaptureProvider, FrameData } from "./frameCapture";
import type { StreamType } from "../types/detection";
import { MOCK_CAMERA } from "../config/mock";
import { audioEngine } from "./audioEngine";

// 플러그인 인스턴스는 네이티브 리소스(CIContext)가 과도하게 매번 생성되는 것을 방지하기 위해 1회만 초기화
const reflexFrameProcessorPlugin: FrameProcessorPlugin | undefined =
  !MOCK_CAMERA
    ? VisionCameraProxy.initFrameProcessorPlugin("reflexFrameCapture", {})
    : undefined;

function base64ToUint8(b64: string): Uint8Array {
  const bin = globalThis.atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
    bytes[i] = bin.charCodeAt(i) & 0xff;
  }
  return bytes;
}

export function useFrameCaptureProvider(
  cameraRef: React.RefObject<any>,
  intervalSharedValue: any,
  lastCaptureTsShared: any
): FrameCaptureProvider {
  const onFrameRef = useRef<((frame: FrameData) => void) | null>(null);
  const isCapturingRealFrame = useRef(false);

  // 1. 단발 촬영 폴백 경로 (capturePhoto)
  const capturePhoto = useCallback(
    async (stream: StreamType): Promise<FrameData | null> => {
      if (!cameraRef.current) {
        console.warn(`[Camera/Real-iOS] ${stream} 캡처 실패: cameraRef 없음`);
        return null;
      }
      if (isCapturingRealFrame.current) {
        return null;
      }
      isCapturingRealFrame.current = true;
      try {
        const photo: PhotoFile = await cameraRef.current.takePhoto({
          flash: "off",
          enableShutterSound: false,
        });
        const path = photo.path.startsWith("file://")
          ? photo.path
          : `file://${photo.path}`;

        const isRotated90 =
          photo.orientation === "landscape-left" ||
          photo.orientation === "landscape-right";
        const correctedWidth = isRotated90 ? photo.height : photo.width;
        const correctedHeight = isRotated90 ? photo.width : photo.height;
        const cropSize = Math.min(correctedWidth, correctedHeight);
        const originX = Math.floor((correctedWidth - cropSize) / 2);
        const originY = Math.floor((correctedHeight - cropSize) / 2);

        const manipResult = await manipulateAsync(
          path,
          [
            { crop: { originX, originY, width: cropSize, height: cropSize } },
            { resize: { width: 640, height: 640 } },
          ],
          { compress: 0.5, format: SaveFormat.JPEG, base64: true }
        );

        const base64 = manipResult.base64 ?? "";
        const float32 = new Float32Array(0);
        const jpegBytes = await new File(manipResult.uri).bytes();

        if (!audioEngine.isGuidePlaying) {
          console.log(`[Camera/Real-iOS] ${stream} 단발 프레임 완료: bytes=${jpegBytes.length}`);
        }

        void FileSystem.deleteAsync(path, { idempotent: true }).catch(() => {});
        void FileSystem.deleteAsync(manipResult.uri, { idempotent: true }).catch(() => {});

        return { float32, stream, base64, jpegBytes };
      } catch (err) {
        console.error(`[Camera/Real-iOS] ${stream} 단발 캡처 오류:`, err);
        return null;
      } finally {
        isCapturingRealFrame.current = false;
      }
    },
    [cameraRef]
  );

  // 2. 스트림 프레임 수신 처리 (worklet -> JS)
  const streamFrameCounterRef = useRef(0);
  const handleStreamFrameBase64 = useRunOnJS(
    (base64: string, intervalMs: number) => {
      if (!onFrameRef.current || !base64) return;
      streamFrameCounterRef.current++;

      const jpegBytes = base64ToUint8(base64);
      const frame: FrameData = {
        float32: new Float32Array(0),
        stream: "reflex",
        base64,
        jpegBytes,
      };

      if (!audioEngine.isGuidePlaying) {
        console.log(
          `[Camera/Stream-iOS] reflex 프레임 수신: bytes=${jpegBytes.length} base64len=${base64.length}`
        );
      }

      onFrameRef.current(frame);

      // 인지/반사 비율에 따라 인지 채널로도 흐름을 분류
      // iOS useCamera.ts 의 startCapture 에서 전달해주던 reflexFps/cognitiveFps 비례 ratio 처리를 여기로 위임하거나
      // 혹은 useCamera.ts 에서 supportsStream 시 streamFrameCounter를 사용해 이관할 수도 있으나,
      // 캡처 공급 측에서 frameCounter를 기준으로 프레임을 분할 처리합니다. (기존 iOS useCamera.ts 와 정합)
      // reflexFps(10) / cognitiveFps(2) = 5
      const ratio = 5; // 고정 비율 또는 useCamera 측에서 조정 가능
      if (streamFrameCounterRef.current % ratio === 0) {
        onFrameRef.current({ ...frame, stream: "cognitive" });
      }
    },
    []
  );

  // 3. 네이티브 프레임 프로세서 바인딩 (worklet)
  const frameProcessor = useFrameProcessor(
    (frame: Frame) => {
      "worklet";
      if (reflexFrameProcessorPlugin == null) return;
      const now = Date.now();
      if (now - lastCaptureTsShared.value < intervalSharedValue.value) return;
      lastCaptureTsShared.value = now;

      const result = reflexFrameProcessorPlugin.call(frame);
      if (typeof result === "string" && result.length > 0) {
        handleStreamFrameBase64(result, intervalSharedValue.value);
      }
    },
    [handleStreamFrameBase64]
  );

  const startStream = useCallback(
    (onFrame: (frame: FrameData) => void, intervalMs: number): boolean => {
      onFrameRef.current = onFrame;
      streamFrameCounterRef.current = 0;
      console.log("[Camera/Stream-iOS] iOS FrameProcessor 스트림을 시작합니다.");
      return true;
    },
    []
  );

  const stop = useCallback(() => {
    onFrameRef.current = null;
    console.log("[Camera/Stream-iOS] iOS 스트림을 중지합니다.");
  }, []);

  return useMemo(() => ({
    startStream,
    capturePhoto,
    supportsStream: true,
    stop,
    // useCamera.ts에서 Camera 컴포넌트에 이 프로퍼티를 전달해 바인딩할 수 있도록 노출
    frameProcessor,
  }), [startStream, capturePhoto, stop, frameProcessor]) as any;
}
