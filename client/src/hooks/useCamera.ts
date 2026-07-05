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
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

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
  const isCapturingRealFrame = useRef(false);
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
      if (isCapturingRealFrame.current) {
        // 이미 캡처가 진행 중이면 중복 방지를 위해 즉시 무시 (drop)
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

        // expo-image-manipulator 기기 네이티브 GPU 가속 리사이징/압축 기동
        const manipResult = await manipulateAsync(
          path,
          [{ resize: { width: 640, height: 640 } }],
          { compress: 0.5, format: SaveFormat.JPEG, base64: true },
        );

        const base64 = manipResult.base64 ?? "";
        const float32 = decodeBase64JpegToChw(base64);

        console.log(`[Camera/Real] ${stream} 프레임 압축완료: 원본경로=${path} -> 압축 base64len=${base64.length} float32len=${float32.length}`);

        // 디바이스 임시 스토리지 고갈 방지를 위해 촬영된 원본 및 리사이징 임시 파일 청소
        void FileSystem.deleteAsync(path, { idempotent: true }).catch(() => {});
        void FileSystem.deleteAsync(manipResult.uri, { idempotent: true }).catch(() => {});

        return { float32, stream, base64 };
      } catch (err) {
        console.error(`[Camera/Real] ${stream} 캡처 오류:`, err);
        return null;
      } finally {
        isCapturingRealFrame.current = false;
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
      const frameCounter = { current: 0 };

      reflexTimerRef.current = setInterval(async () => {
        frameCounter.current++;

        // 단일 프레임 캡처 (하드웨어 호출 1회로 통일)
        const frame = await captureFrame("reflex");
        if (!frame || !onFrameRef.current) return;

        // 반사 경로로 즉시 전달
        onFrameRef.current(frame);

        // 매 N번째 프레임마다 동일 프레임을 인지 경로로 전달 (중복 캡처 제거)
        const ratio = Math.max(1, Math.floor(reflexFps / cognitiveFps));
        if (frameCounter.current % ratio === 0) {
          onFrameRef.current({
            ...frame,
            stream: "cognitive",
          });
        }
      }, reflexInterval);

      console.log(
        `[Camera] ${isMockMode ? "Mock" : "Real"} 통합 단일 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps`,
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
