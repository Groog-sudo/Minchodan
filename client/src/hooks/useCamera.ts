/**
 * 이중 캡처 타이머 훅.
 * 반사(reflex 10fps)/인지(cognitive 2fps) 스트림을 분리 캡처하여
 * 온디바이스 TFLite 추론용 Float32Array 텐서를 공급한다.
 *
 * 동작 모드:
 *  - MOCK_CAMERA=true : MockFrameProvider가 번들 샘플 → float32 (시뮬레이터)
 *  - MOCK_CAMERA=false: react-native-vision-camera takePhoto → base64 → decode → float32 (실기기)
 *
 * 실기기에서는 서버 WS 전송용 raw JPEG 바이트(jpegBytes)와 CoreML 네이티브 브릿지 호출용
 * base64 문자열을 함께 전달한다 (서버 전송은 jpegBytes를 바이너리 프레임으로 직접 사용).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  type CameraDevice,
  useCameraDevice,
  useCameraDevices,
  useCameraPermission,
} from "react-native-vision-camera";
import { useSharedValue } from "react-native-worklets-core";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import { MOCK_CAMERA } from "../config/mock";
import type { StreamType } from "../types/detection";
import { FRAME_TENSOR_LENGTH } from "../services/frameProvider";
import { useFrameCaptureProvider, type FrameData } from "../services/frameCapture";

export { FrameData };

// 동적 FPS 조절 파라미터 (온디바이스 추론 지연 기준)
const OVERLOAD_LATENCY_RATIO = 0.9;
const RECOVERY_LATENCY_RATIO = 0.5;
const INTERVAL_INCREASE_STEP_MS = 50;
const INTERVAL_DECREASE_STEP_MS = 20;
const MAX_REFLEX_INTERVAL_MS = 1000; // 최저 1fps 보장

export interface UseCameraReturn {
  cameraRef: React.RefObject<Camera | null>;
  device: CameraDevice | undefined;
  hasPermission: boolean;
  permissionStatus: string;
  isCapturing: boolean;
  isMockMode: boolean;
  currentReflexFps: number;
  startCapture: (onFrame: (frame: FrameData) => void) => void;
  stopCapture: () => void;
  requestCameraPermission: () => Promise<boolean>;
  /** 온디바이스 추론 지연(ms)을 보고하여 반사 캡처 fps를 동적으로 조절한다. */
  reportInferenceLatency: (latencyMs: number) => void;
  /** iOS Stream 지원에 필요한 내부 frameProcessor 속성 (iOS 전용, supportsStream이 true일 때 유효) */
  frameProcessor?: any;
  /** iOS용 stream 가동 상태 스위치 */
  useStreamCapture: boolean;
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
  
  const reflexTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onFrameRef = useRef<((frame: FrameData) => void) | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [permissionRequested, setPermissionRequested] = useState(false);

  // 동적 FPS 및 간격 관리
  const baseIntervalRef = useRef(Math.floor(1000 / reflexFps));
  const currentIntervalRef = useRef(baseIntervalRef.current);
  const [currentReflexFps, setCurrentReflexFps] = useState(reflexFps);

  // iOS Native Frame Processor 연동용 공유 변수
  const intervalSharedValue = useSharedValue(currentIntervalRef.current);
  const lastCaptureTsShared = useSharedValue(0);

  // 플랫폼별/환경별 프레임 캡처 제공자 획득
  const provider = useFrameCaptureProvider(
    cameraRef,
    intervalSharedValue,
    lastCaptureTsShared
  );

  const reportInferenceLatency = useCallback((latencyMs: number) => {
    if (!Number.isFinite(latencyMs) || latencyMs < 0) return;
    const base = baseIntervalRef.current;
    const cur = currentIntervalRef.current;
    let next = cur;

    if (latencyMs > cur * OVERLOAD_LATENCY_RATIO) {
      next = Math.min(MAX_REFLEX_INTERVAL_MS, cur + INTERVAL_INCREASE_STEP_MS);
    } else if (latencyMs < cur * RECOVERY_LATENCY_RATIO && cur > base) {
      next = Math.max(base, cur - INTERVAL_DECREASE_STEP_MS);
    }

    if (next !== cur) {
      currentIntervalRef.current = next;
      intervalSharedValue.value = next;
      setCurrentReflexFps(Math.round(1000 / next));
      console.log(
        `[Camera] 동적 FPS 조절: 반사 간격 ${cur}ms -> ${next}ms (추론 지연=${latencyMs.toFixed(1)}ms)`,
      );
    }
  }, [intervalSharedValue]);

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
  }, [isMockMode, hasPermission, permissionRequested, requestCameraPermission]);

  // ---- 캡처 루프 제어 ----

  const startCapture = useCallback(
    (onFrame: (frame: FrameData) => void) => {
      if (isCapturing) return;
      onFrameRef.current = onFrame;
      setIsCapturing(true);

      baseIntervalRef.current = Math.floor(1000 / reflexFps);
      currentIntervalRef.current = baseIntervalRef.current;
      intervalSharedValue.value = currentIntervalRef.current;
      setCurrentReflexFps(reflexFps);

      // 1. 스트림 방식 지원 시 (iOS 네이티브 경로)
      if (provider.supportsStream) {
        provider.startStream(onFrame, currentIntervalRef.current);
        console.log(
          `[Camera] Stream 캡처 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps (동적 조절 활성)`,
        );
        return;
      }

      // 2. 단발 캡처 방식 지원 시 (Android 실기기 및 Mock 타이머 폴백 경로)
      const frameCounter = { current: 0 };
      const tick = async () => {
        frameCounter.current++;

        const frame = await provider.capturePhoto("reflex");
        if (frame && onFrameRef.current) {
          onFrameRef.current(frame);

          const ratio = Math.max(1, Math.floor(reflexFps / cognitiveFps));
          if (frameCounter.current % ratio === 0) {
            onFrameRef.current({
              ...frame,
              stream: "cognitive",
            });
          }
        }

        if (reflexTimerRef.current !== null) {
          reflexTimerRef.current = setTimeout(tick, currentIntervalRef.current);
        }
      };

      reflexTimerRef.current = setTimeout(tick, currentIntervalRef.current);
      console.log(
        `[Camera] ${isMockMode ? "Mock" : "Real"} 타이머 단일 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps`,
      );
    },
    [reflexFps, cognitiveFps, isCapturing, isMockMode, provider, intervalSharedValue],
  );

  const stopCapture = useCallback(() => {
    if (reflexTimerRef.current) {
      clearTimeout(reflexTimerRef.current);
      reflexTimerRef.current = null;
    }
    provider.stop();
    onFrameRef.current = null;
    setIsCapturing(false);
    console.log("[Camera] 루프 중지");
  }, [provider]);

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
    currentReflexFps,
    startCapture,
    stopCapture,
    requestCameraPermission,
    reportInferenceLatency,
    frameProcessor: (provider as any).frameProcessor,
    useStreamCapture: provider.supportsStream,
  };
}

export { FRAME_TENSOR_LENGTH };
