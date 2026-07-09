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
  type Frame,
  type FrameProcessorPlugin,
  type PhotoFile,
  useCameraDevice,
  useCameraDevices,
  useCameraPermission,
  useFrameProcessor,
  VisionCameraProxy,
} from "react-native-vision-camera";
import { useRunOnJS, useSharedValue } from "react-native-worklets-core";
import * as FileSystem from "expo-file-system/legacy";
import { File } from "expo-file-system";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import { MOCK_CAMERA } from "../config/mock";
import { CAPTURE_ENGINE } from "../config/capture";
import type { StreamType } from "../types/detection";
import {
  decodeBase64JpegToChw,
  FRAME_TENSOR_LENGTH,
  getFrameProvider,
} from "../services/frameProvider";
import { audioEngine } from "../services/audioEngine";

// [2026-07-09 도입] client/ios/ReflexFrameProcessorPlugin.swift 등록명과 반드시 일치해야 한다.
// 플러그인 인스턴스는 네이티브 리소스(CIContext)를 갖고 있어 모듈 스코프에서 1회만 생성한다
// (컴포넌트 리렌더마다 재생성하면 매번 새 네이티브 인스턴스가 만들어짐).
const reflexFrameProcessorPlugin: FrameProcessorPlugin | undefined =
  CAPTURE_ENGINE === "frameProcessor" && !MOCK_CAMERA
    ? VisionCameraProxy.initFrameProcessorPlugin("reflexFrameCapture", {})
    : undefined;

/** base64 문자열을 Uint8Array로 변환한다 (services/realFrameProvider.ts의 동일 패턴). */
function base64ToUint8(b64: string): Uint8Array {
  const bin = globalThis.atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i) & 0xff;
  return bytes;
}

export interface FrameData {
  float32: Float32Array;
  stream: StreamType;
  // CoreML 네이티브 브릿지 호출용 (RN 브릿지는 JSON 직렬화 가능 타입만 인자로 받으므로 base64 유지 필요)
  base64: string | null;
  // 서버 WS 전송용 raw JPEG 바이트 (base64 미경유, 바이너리 프레임으로 직접 전송)
  jpegBytes: Uint8Array | null;
}

// 동적 FPS 조절 파라미터 (온디바이스 추론 지연 기준)
// - 지연이 현재 간격의 90%를 넘으면(따라잡지 못함) 간격을 늘려 fps를 낮춘다.
// - 지연이 현재 간격의 50% 미만으로 안정되면 기본 간격까지 서서히 되돌린다.
const OVERLOAD_LATENCY_RATIO = 0.9;
const RECOVERY_LATENCY_RATIO = 0.5;
const INTERVAL_INCREASE_STEP_MS = 50;
const INTERVAL_DECREASE_STEP_MS = 20;
const MAX_REFLEX_INTERVAL_MS = 1000; // 최저 1fps 보장 (반사 경로 완전 정지 방지)

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
  /** true면 <Camera>가 photo 대신 frameProcessor(연속 스트림)로 구동돼야 한다(2026-07-09 도입). */
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
  const isCapturingRealFrame = useRef(false);
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

  // takePhoto() 기반 캡처 (구 경로, CAPTURE_ENGINE='takePhoto' 롤백용으로 보존).
  // AVCapturePhotoOutput.capturePhoto()가 촬영마다 AVAudioSessionInterruption을 유발해
  // 동시 재생 중인 TTS 안내 음성이 끊기는 결함이 실기기에서 확인됐다(2026-07-09,
  // client/src/config/capture.ts 주석 참조). 기본 경로는 captureRealFrameStream(프레임
  // 프로세서)이며, 문제가 재현되면 CAPTURE_ENGINE만 바꿔 이 경로로 즉시 원복할 수 있다.
  const captureRealFramePhoto = useCallback(
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

        // 카메라 미리보기(<Camera resizeMode="cover"> 기본값)는 종횡비를 유지한 채
        // 화면에 꽉 차도록 중앙 크롭하여 보여준다. 반면 resize({width,height})를
        // 둘 다 지정하면 종횡비를 무시하고 강제로 눌러 늘리므로(stretch), 모델이 보는
        // 이미지와 화면 미리보기의 기하 구조가 달라져 bbox가 화면과 어긋나게 그려진다.
        // 미리보기와 동일하게 중앙 정사각형 크롭 후 리사이즈해야 bbox 좌표가 정합한다.
        //
        // photo.width/height는 EXIF PixelXDimension/Dimension(센서 원본, 항상 landscape
        // 배치) 기준이라 회전 반영 전 값이다. expo-image-manipulator는 크롭보다 먼저
        // ImageFixOrientationTransformer로 EXIF 회전을 이미지에 반영하므로, 세로로 촬영해
        // 90/270도 보정이 필요한 경우(orientation === landscape-left/right) 크롭 좌표계에서는
        // 가로/세로 축이 서로 뒤바뀐다. 이를 보정하지 않으면 크롭 영역이 이미지 경계를 벗어난다.
        const isRotated90 =
          photo.orientation === "landscape-left" ||
          photo.orientation === "landscape-right";
        const correctedWidth = isRotated90 ? photo.height : photo.width;
        const correctedHeight = isRotated90 ? photo.width : photo.height;
        const cropSize = Math.min(correctedWidth, correctedHeight);
        const originX = Math.floor((correctedWidth - cropSize) / 2);
        const originY = Math.floor((correctedHeight - cropSize) / 2);

        // expo-image-manipulator 기기 네이티브 GPU 가속 크롭/리사이징/압축 기동
        const manipResult = await manipulateAsync(
          path,
          [
            { crop: { originX, originY, width: cropSize, height: cropSize } },
            { resize: { width: 640, height: 640 } },
          ],
          { compress: 0.5, format: SaveFormat.JPEG, base64: true },
        );

        const base64 = manipResult.base64 ?? "";
        // 실기기 실행 시 JS CPU 100% 점유로 인한 iOS Watchdog SIGKILL (code 9) 차단을 위해 온디바이스 디코딩 루프 생략
        // (실기기에서는 서버로 raw JPEG 바이트만 전송하여 GPU 추론 서버에서 디코딩 및 검출을 전담 처리함)
        const float32 = new Float32Array(0);

        // 서버 WS 전송용 raw JPEG 바이트 (base64 미경유). CoreML 네이티브 브릿지 호출은
        // RN 구 브릿지가 JSON 직렬화 가능 타입만 인자로 받을 수 있어 base64 문자열이 불가피하지만,
        // 서버로의 WS 전송은 이 바이트를 그대로 바이너리 프레임으로 보내 33% 오버헤드를 제거한다.
        const jpegBytes = await new File(manipResult.uri).bytes();

        if (!audioEngine.isGuidePlaying) {
          console.log(`[Camera/Real] ${stream} 프레임 압축완료: 원본경로=${path} -> JPEG bytes=${jpegBytes.length} base64len(CoreML용)=${base64.length} float32len=${float32.length}`);
        }

        // 디바이스 임시 스토리지 고갈 방지를 위해 촬영된 원본 및 리사이징 임시 파일 청소
        void FileSystem.deleteAsync(path, { idempotent: true }).catch(() => {});
        void FileSystem.deleteAsync(manipResult.uri, { idempotent: true }).catch(() => {});

        return { float32, stream, base64, jpegBytes };
      } catch (err) {
        console.error(`[Camera/Real] ${stream} 캡처 오류:`, err);
        return null;
      } finally {
        isCapturingRealFrame.current = false;
      }
    },
    [],
  );


  const captureFrame = isMockMode ? captureMockFrame : captureRealFramePhoto;
  const useStreamCapture =
    !isMockMode && CAPTURE_ENGINE === "frameProcessor";

  // ---- 프레임 프로세서 캡처 (신 경로, 기본값) ----
  const streamFrameCounterRef = useRef(0);

  // worklet에서 runOnJS로 넘어온 base64를 FrameData로 조립해 반사/인지 경로에 전달한다.
  // captureRealFramePhoto와 동일한 반사+N번째 인지 재전달 규칙을 유지한다(재캡처 없음).
  const handleStreamFrameBase64 = useRunOnJS((base64: string) => {
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
        `[Camera/Stream] reflex 프레임 수신: JPEG bytes=${jpegBytes.length} base64len=${base64.length}`,
      );
    }

    onFrameRef.current(frame);

    const ratio = Math.max(1, Math.floor(reflexFps / cognitiveFps));
    if (streamFrameCounterRef.current % ratio === 0) {
      onFrameRef.current({ ...frame, stream: "cognitive" });
    }
  }, [reflexFps, cognitiveFps]);

  // 카메라 전체 fps(예: 30fps)로 호출되므로, 반사 fps 간격(intervalSharedValue)으로
  // throttle해야 CoreML 추론이 못 따라가는 것을 막는다(동적 fps 조절과 동일한 목적).
  const frameProcessor = useFrameProcessor(
    (frame: Frame) => {
      "worklet";
      if (reflexFrameProcessorPlugin == null) return;
      const now = Date.now();
      if (now - lastCaptureTsShared.value < intervalSharedValue.value) return;
      lastCaptureTsShared.value = now;

      const result = reflexFrameProcessorPlugin.call(frame);
      if (typeof result === "string" && result.length > 0) {
        handleStreamFrameBase64(result);
      }
    },
    [handleStreamFrameBase64],
  );

  // ---- 캡처 루프 (takePhoto 경로 전용, frameProcessor 경로는 <Camera frameProcessor>가 구동) ----

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
        // 프레임 프로세서 경로: <Camera frameProcessor={frameProcessor}>가 이미 프레임을
        // 지속적으로 공급 중이므로(isCapturing=true가 됨과 동시에 onFrameRef가 유효해져
        // handleStreamFrameBase64가 실제로 dispatch를 시작), 여기서는 별도 타이머가 필요 없다.
        console.log(
          `[Camera] Stream(FrameProcessor) 캡처 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps (동적 조절 활성)`,
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
        `[Camera] ${isMockMode ? "Mock" : "Real"} 통합 단일 루프 시작: 반사 ${reflexFps}fps / 인지 ${cognitiveFps}fps (동적 조절 활성)`,
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
    frameProcessor: useStreamCapture ? frameProcessor : undefined,
  };
}

// FRAME_TENSOR_LENGTH re-export (사용처 참고용)
export { FRAME_TENSOR_LENGTH };
