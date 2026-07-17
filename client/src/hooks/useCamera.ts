/**
 * 이중 캡처 타이머 훅.
 * 반사(reflex 10fps)/인지(cognitive 2fps) 스트림을 분리 캡처하여
 * 온디바이스 TFLite 추론용 Float32Array 텐서를 공급한다.
 *
 * 동작 모드:
 *  - MOCK_CAMERA=true : MockFrameProvider가 번들 샘플 → float32 (시뮬레이터)
 *  - MOCK_CAMERA=false: 실기기. 캡처 하드웨어 접근은 플랫폼별로 분리된
 *    useFrameCaptureProvider(services/frameCaptureProviderSelect.ios.ts /
 *    .android.ts)가 담당하고, 이 훅은 타이머·동적 FPS·Mock 분기 등 플랫폼
 *    무관 오케스트레이션만 수행한다
 *    (docs/mobile/ios_android_bifurcation_contract.md §4 참조).
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
  useFrameProcessor,
} from "react-native-vision-camera";
import { useSharedValue } from "react-native-worklets-core";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import { MOCK_CAMERA } from "../config/mock";
import type { StreamType } from "../types/detection";
import {
  decodeBase64JpegToHwc,
  getFrameProvider,
} from "../services/frameProvider";
import {
  base64ToUint8,
  useFrameCaptureProvider,
  type FrameData,
} from "../services/frameCaptureProvider";

export type { FrameData };

// 동적 FPS 조절 파라미터 (온디바이스 추론 지연 기준)
// - 지연이 현재 간격의 90%를 넘으면(따라잡지 못함) 간격을 늘려 fps를 낮춘다.
// - 지연이 현재 간격의 50% 미만으로 안정되면 기본 간격까지 서서히 되돌린다.
const OVERLOAD_LATENCY_RATIO = 0.9;
const RECOVERY_LATENCY_RATIO = 0.5;
const INTERVAL_INCREASE_STEP_MS = 50;
const INTERVAL_DECREASE_STEP_MS = 20;
// 최저 5fps: 1fps까지 떨어지면 콘솔 Live Feed가 끊겨 보인다.
// 온디바이스 추론 과부하는 detectingRef 게이트로 계속 완화한다.
const MAX_REFLEX_INTERVAL_MS = 200;

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
  /** true면 <Camera>가 photo 대신 frameProcessor(연속 스트림)로 구동돼야 한다. */
  useStreamCapture: boolean;
  /** useStreamCapture가 true일 때만 값이 있다. <Camera frameProcessor={...}>에 그대로 전달한다. */
  frameProcessor: ReturnType<typeof useFrameProcessor> | undefined;
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
  const cognitiveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onFrameRef = useRef<((frame: FrameData) => void) | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [permissionRequested, setPermissionRequested] = useState(false);

  // 동적 FPS 상태: baseIntervalRef는 설정된 기본값(가장 빠른 허용치),
  // currentIntervalRef는 추론 지연 피드백에 따라 조절되는 실제 반사 루프 간격
  const baseIntervalRef = useRef(Math.floor(1000 / reflexFps));
  const currentIntervalRef = useRef(baseIntervalRef.current);
  const [currentReflexFps, setCurrentReflexFps] = useState(reflexFps);

  // 프레임 프로세서(worklet) 경로용 SharedValue. worklet(별도 JS 컨텍스트)과 메인
  // JS 스레드 간 상태 공유는 SharedValue로만 안전하다(일반 useRef는 worklet에서
  // 최신값을 보장하지 못함). currentIntervalRef가 갱신될 때마다 함께 갱신한다.
  const intervalSharedValue = useSharedValue(currentIntervalRef.current);
  const lastCaptureTsShared = useSharedValue(0);

  const reportInferenceLatency = useCallback((latencyMs: number) => {
    if (!Number.isFinite(latencyMs) || latencyMs < 0) return;
    const base = baseIntervalRef.current;
    const cur = currentIntervalRef.current;
    let next = cur;

    if (latencyMs > cur * OVERLOAD_LATENCY_RATIO) {
      // 추론이 캡처 간격을 따라가지 못함 - fps를 낮춰 부하 경감 (SIGKILL 재발 방지)
      next = Math.min(MAX_REFLEX_INTERVAL_MS, cur + INTERVAL_INCREASE_STEP_MS);
    } else if (latencyMs < cur * RECOVERY_LATENCY_RATIO && cur > base) {
      // 여유가 충분하면 기본 fps까지 서서히 복구
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
        return { float32, stream, base64: null, jpegBytes: null };
      } catch (err) {
        console.error(`[Camera/Mock] ${stream} 프레임 오류:`, err);
        return null;
      }
    },
    [],
  );

  // ---- 스트림 캡처 콜백 (플랫폼 구현이 base64 결과를 밀어 넣는 진입점) ----
  const streamFrameCounterRef = useRef(0);

  const handleStreamFrameBase64 = useCallback((base64: string) => {
    if (!onFrameRef.current || !base64) return;
    streamFrameCounterRef.current++;

    const jpegBytes = base64ToUint8(base64);
    const frame: FrameData = {
      float32: decodeBase64JpegToHwc(base64),
      stream: "reflex",
      base64,
      jpegBytes,
    };

    onFrameRef.current(frame);

    const ratio = Math.max(1, Math.floor(reflexFps / cognitiveFps));
    if (streamFrameCounterRef.current % ratio === 0) {
      onFrameRef.current({ ...frame, stream: "cognitive" });
    }
  }, [reflexFps, cognitiveFps]);

  // 플랫폼별 캡처 구현 (iOS/Android 모두 frameProcessor 가능, 실패 시 takePhoto 폴백).
  // Metro가 frameCaptureProviderSelect.ios.ts 또는 .android.ts를 자동 바인딩한다.
  const captureProvider = useFrameCaptureProvider({
    cameraRef,
    intervalSharedValue,
    lastCaptureTsShared,
    onStreamFrameBase64: handleStreamFrameBase64,
  });

  const captureFrame = isMockMode ? captureMockFrame : captureProvider.capturePhoto;
  // Frame Processor(연속 스트림) 우선. 플러그인 미등록 시에만 takePhoto 폴백.
  // takePhoto 강제(useStreamCapture=false)는 AVCapturePhotoOutput 경로로
  // AVFoundation -11803 "Cannot Record"/오디오 세션 충돌을 유발한다(2026-07-17 실측).
  // Expo Go 등 supportsStream=false 환경에서는 자동으로 takePhoto 폴백된다.
  const useStreamCapture = !isMockMode && captureProvider.supportsStream;

  // ---- 캡처 루프 (capturePhoto 경로 전용, 스트림 경로는 <Camera frameProcessor>가 구동) ----

  const startCapture = useCallback(
    (onFrame: (frame: FrameData) => void) => {
      if (isCapturing) return;
      onFrameRef.current = onFrame;
      setIsCapturing(true);

      baseIntervalRef.current = Math.floor(1000 / reflexFps);
      currentIntervalRef.current = baseIntervalRef.current;
      intervalSharedValue.value = currentIntervalRef.current;
      setCurrentReflexFps(reflexFps);
      streamFrameCounterRef.current = 0;

      if (useStreamCapture) {
        // 스트림 경로: <Camera frameProcessor={frameProcessor}>가 이미 프레임을
        // 지속적으로 공급 중이므로(isCapturing=true가 됨과 동시에 onFrameRef가 유효해져
        // handleStreamFrameBase64가 실제로 dispatch를 시작), 여기서는 별도 타이머가 필요 없다.
        console.log(
          `[Camera] Stream 캡처 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps (동적 조절 활성, supportsStream=${captureProvider.supportsStream})`,
        );
        return;
      }

      const frameCounter = { current: 0 };

      // setInterval 대신 재귀 setTimeout을 사용: 매 tick마다 currentIntervalRef의
      // 최신값을 다시 읽어와야 reportInferenceLatency()의 동적 fps 조절이 반영된다.
      const tick = async () => {
        frameCounter.current++;

        // 단일 프레임 캡처 (하드웨어 호출 1회로 통일)
        const frame = await captureFrame("reflex");
        if (frame && onFrameRef.current) {
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
        }

        // stopCapture()가 이미 호출되어 null이 됐다면 재예약하지 않는다.
        if (reflexTimerRef.current !== null) {
          reflexTimerRef.current = setTimeout(tick, currentIntervalRef.current);
        }
      };

      reflexTimerRef.current = setTimeout(tick, currentIntervalRef.current);

      console.log(
        `[Camera] ${isMockMode ? "Mock" : "Real"} 통합 단일 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps (동적 조절 활성, supportsStream=${captureProvider.supportsStream})`,
      );
    },
    [
      reflexFps,
      cognitiveFps,
      isCapturing,
      isMockMode,
      captureFrame,
      useStreamCapture,
      intervalSharedValue,
    ],
  );

  const stopCapture = useCallback(() => {
    if (reflexTimerRef.current) {
      clearTimeout(reflexTimerRef.current);
      reflexTimerRef.current = null;
    }
    if (cognitiveTimerRef.current) {
      clearInterval(cognitiveTimerRef.current);
      cognitiveTimerRef.current = null;
    }
    onFrameRef.current = null;
    streamFrameCounterRef.current = 0;
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
    currentReflexFps,
    startCapture,
    stopCapture,
    requestCameraPermission,
    reportInferenceLatency,
    useStreamCapture,
    frameProcessor: useStreamCapture
      ? (captureProvider.frameProcessor as ReturnType<typeof useFrameProcessor>)
      : undefined,
  };
}
