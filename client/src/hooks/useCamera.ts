/**
 * 이중 캡처 타이머 훅.
 * 후면 카메라에서 반사(10fps)/인지(2fps) 스트림을 분리 캡처.
 * react-native-vision-camera v4 API 사용 (takePhoto + expo-file-system base64).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  type CameraDevice,
  type PhotoFile,
  useCameraDevice,
  useCameraPermission,
} from "react-native-vision-camera";
import * as FileSystem from "expo-file-system/legacy";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import type { StreamType } from "../types/detection";

export interface UseCameraReturn {
  cameraRef: React.RefObject<Camera | null>;
  device: CameraDevice | undefined;
  hasPermission: boolean;
  isCapturing: boolean;
  startCapture: (
    onFrame: (base64: string, stream: StreamType) => void,
  ) => void;
  stopCapture: () => void;
}

export function useCamera(
  reflexFps: number = REFLEX_FPS,
  cognitiveFps: number = COGNITIVE_FPS,
): UseCameraReturn {
  const { hasPermission, requestPermission } = useCameraPermission();
  const backDevice = useCameraDevice("back");
  const frontDevice = useCameraDevice("front");
  const device = backDevice || frontDevice;
  const cameraRef = useRef<Camera | null>(null);
  const reflexTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cognitiveTimerRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  const onFrameRef = useRef<
    ((base64: string, stream: StreamType) => void) | null
  >(null);
  const [isCapturing, setIsCapturing] = useState(false);

  useEffect(() => {
    if (!hasPermission) {
      requestPermission();
    }
  }, [hasPermission, requestPermission]);

  const captureFrame = useCallback(
    async (stream: StreamType): Promise<string | null> => {
      if (!cameraRef.current) return null;
      try {
        const photo: PhotoFile = await cameraRef.current.takePhoto({
          flash: "off",
          enableShutterSound: false,
        });

        const path = photo.path.startsWith("file://")
          ? photo.path
          : `file://${photo.path}`;
        const base64 = await FileSystem.readAsStringAsync(path, {
          encoding: FileSystem.EncodingType.Base64,
        });

        return base64;
      } catch (err) {
        console.error(`[Camera] ${stream} 캡처 오류:`, err);
        return null;
      }
    },
    [],
  );

  const startCapture = useCallback(
    (onFrame: (base64: string, stream: StreamType) => void) => {
      if (isCapturing) return;
      onFrameRef.current = onFrame;
      setIsCapturing(true);

      const reflexInterval = Math.floor(1000 / reflexFps);
      const cognitiveInterval = Math.floor(1000 / cognitiveFps);

      reflexTimerRef.current = setInterval(async () => {
        const frame = await captureFrame("reflex");
        if (frame && onFrameRef.current) {
          onFrameRef.current(frame, "reflex");
        }
      }, reflexInterval);

      cognitiveTimerRef.current = setInterval(async () => {
        const frame = await captureFrame("cognitive");
        if (frame && onFrameRef.current) {
          onFrameRef.current(frame, "cognitive");
        }
      }, cognitiveInterval);

      console.log(
        `[Camera] 이중 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps`,
      );
    },
    [reflexFps, cognitiveFps, isCapturing, captureFrame],
  );

  const stopCapture = useCallback(() => {
    if (reflexTimerRef.current) {
      clearInterval(reflexTimerRef.current);
      reflexTimerRef.current = null;
    }
    if (cognitiveTimerRef.current) {
      clearInterval(cognitiveTimerRef.current);
      cognitiveTimerRef.current = null;
    }
    onFrameRef.current = null;
    setIsCapturing(false);
    console.log("[Camera] 루프 중지");
  }, []);

  useEffect(() => {
    return () => stopCapture();
  }, [stopCapture]);

  return {
    cameraRef,
    device,
    hasPermission,
    isCapturing,
    startCapture,
    stopCapture,
  };
}
