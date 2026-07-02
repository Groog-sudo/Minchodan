/**
 * 이중 캡처 타이머 훅.
 * 반사(reflex 10fps)/인지(cognitive 2fps) 스트림을 분리 캡처하여
 * 온디바이스 TFLite 추론용 Float32Array 텐서를 공급한다.
 *
 * 동작 모드:
 *  - MOCK_CAMERA=true : MockFrameProvider가 번들 샘플 → float32 (시뮬레이터)
 *  - MOCK_CAMERA=false: react-native-vision-camera takePhoto → base64 → decode → float32 (실기기)
 *
 * 실기기에서는 base64도 함께 전달하여 서버 전송 경로를 유지할 수 있다.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  type CameraDevice,
  type PhotoFile,
  useCameraDevice,
  useCameraDevices,
  useCameraPermission,
} from "react-native-vision-camera";
import * as FileSystem from "expo-file-system/legacy";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import { MOCK_CAMERA } from "../config/mock";
import type { StreamType } from "../types/detection";
import {
  decodeBase64JpegToChw,
  FRAME_TENSOR_LENGTH,
  getFrameProvider,
} from "../services/frameProvider";

export interface FrameData {
  float32: Float32Array;
  stream: StreamType;
  base64: string | null;
}

export interface UseCameraReturn {
  cameraRef: React.RefObject<Camera | null>;
  device: CameraDevice | undefined;
  hasPermission: boolean;
  permissionStatus: string;
  isCapturing: boolean;
  isMockMode: boolean;
  startCapture: (onFrame: (frame: FrameData) => void) => void;
  stopCapture: () => void;
  requestCameraPermission: () => Promise<boolean>;
}

export function useCamera(
  reflexFps: number = REFLEX_FPS,
  cognitiveFps: number = COGNITIVE_FPS,
): UseCameraReturn {
  const isMockMode = MOCK_CAMERA;
  const { hasPermission, requestPermission } = useCameraPermission();
  const backDevice = useCameraDevice("back");
  const allDevices = useCameraDevices();
  const device = backDevice || allDevices[0];
  const cameraRef = useRef<Camera | null>(null);
  const reflexTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cognitiveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onFrameRef = useRef<((frame: FrameData) => void) | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [permissionRequested, setPermissionRequested] = useState(false);

  const effectivePermission = isMockMode ? true : hasPermission;

  const requestCameraPermission = useCallback(async (): Promise<boolean> => {
    if (isMockMode) return true;
    console.log("[Camera] 권한 요청 시작");
    const granted = await requestPermission();
    console.log("[Camera] 권한 요청 결과:", granted);
    setPermissionRequested(true);
    return granted;
  }, [isMockMode, requestPermission]);

  useEffect(() => {
    if (isMockMode) return;
    if (!hasPermission && !permissionRequested) {
      console.log("[Camera] 권한 없음, 자동 요청");
      requestCameraPermission();
    }
    console.log(
      "[Camera] 상태 - hasPermission:",
      hasPermission,
      "device:",
      device?.id ?? "undefined",
    );
  }, [
    isMockMode,
    hasPermission,
    permissionRequested,
    device,
    requestCameraPermission,
  ]);

  // ---- 프레임 획득 ----

  const captureMockFrame = useCallback(
    async (stream: StreamType): Promise<FrameData | null> => {
      const provider = getFrameProvider();
      if (!provider) return null;
      try {
        const float32 = await provider.getFrame();
        return { float32, stream, base64: null };
      } catch (err) {
        console.error(`[Camera/Mock] ${stream} 프레임 오류:`, err);
        return null;
      }
    },
    [],
  );

  const captureRealFrame = useCallback(
    async (stream: StreamType): Promise<FrameData | null> => {
      if (!cameraRef.current) {
        console.warn(`[Camera/Real] ${stream} 캡처 실패: cameraRef 없음`);
        return null;
      }
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
        const float32 = decodeBase64JpegToChw(base64);
        return { float32, stream, base64 };
      } catch (err) {
        console.error(`[Camera/Real] ${stream} 캡처 오류:`, err);
        return null;
      }
    },
    [],
  );

  const captureFrame = isMockMode ? captureMockFrame : captureRealFrame;

  // ---- 캡처 루프 ----

  const startCapture = useCallback(
    (onFrame: (frame: FrameData) => void) => {
      if (isCapturing) return;
      onFrameRef.current = onFrame;
      setIsCapturing(true);

      const reflexInterval = Math.floor(1000 / reflexFps);
      const cognitiveInterval = Math.floor(1000 / cognitiveFps);

      const emit = async (stream: StreamType) => {
        const frame = await captureFrame(stream);
        if (frame && onFrameRef.current) onFrameRef.current(frame);
      };

      reflexTimerRef.current = setInterval(() => {
        void emit("reflex");
      }, reflexInterval);
      cognitiveTimerRef.current = setInterval(() => {
        void emit("cognitive");
      }, cognitiveInterval);

      console.log(
        `[Camera] ${isMockMode ? "Mock" : "Real"} 이중 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps`,
      );
    },
    [reflexFps, cognitiveFps, isCapturing, isMockMode, captureFrame],
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
    hasPermission: effectivePermission,
    permissionStatus: isMockMode
      ? "mock"
      : hasPermission
        ? "granted"
        : permissionRequested
          ? "denied"
          : "not-requested",
    isCapturing,
    isMockMode,
    startCapture,
    stopCapture,
    requestCameraPermission,
  };
}

// FRAME_TENSOR_LENGTH re-export (사용처 참고용)
export { FRAME_TENSOR_LENGTH };
