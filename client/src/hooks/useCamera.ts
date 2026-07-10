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
import { Image } from "react-native";
import {
  Camera,
  type CameraDevice,
  type PhotoFile,
  useCameraDevice,
  useCameraDevices,
  useCameraPermission,
} from "react-native-vision-camera";
import * as FileSystem from "expo-file-system/legacy";
import { File } from "expo-file-system";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import { COGNITIVE_FPS, REFLEX_FPS } from "../config";
import { MOCK_CAMERA } from "../config/mock";
import type { StreamType } from "../types/detection";
import {
  decodeBase64JpegToChw,
  FRAME_TENSOR_LENGTH,
  getFrameProvider,
} from "../services/frameProvider";
import { audioEngine } from "../services/audioEngine";

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
      setCurrentReflexFps(Math.round(1000 / next));
      console.log(
        `[Camera] 동적 FPS 조절: 반사 간격 ${cur}ms -> ${next}ms (추론 지연=${latencyMs.toFixed(1)}ms)`,
      );
    }
  }, []);

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
        // 이미지 파일의 실제 픽셀 가로/세로 크기를 런타임에 직접 획득하여 orientation 오차 원천 방지
        const imgSize = await getImageSize(path);
        const correctedWidth = imgSize.width;
        const correctedHeight = imgSize.height;
        const cropSize = Math.min(correctedWidth, correctedHeight);
        let originX = Math.floor((correctedWidth - cropSize) / 2);
        let originY = Math.floor((correctedHeight - cropSize) / 2);

        // 음수 좌표 방지 가드
        if (originX < 0) originX = 0;
        if (originY < 0) originY = 0;

        // 가로 경계 가드 (x + width <= bitmap.width)
        if (originX + cropSize > correctedWidth) {
          originX = Math.max(0, correctedWidth - cropSize);
        }
        // 세로 경계 가드 (y + height <= bitmap.height)
        if (originY + cropSize > correctedHeight) {
          originY = Math.max(0, correctedHeight - cropSize);
        }

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

        // 안드로이드 실기기에서 new File(path).bytes()의 readAsStringAsync rejected 에러 우회를 위해
        // FileSystem.readAsStringAsync를 통해 직접 base64 문자열을 읽은 후 수동 바이트 디코딩 처리 적용
        const rawBase64 = await FileSystem.readAsStringAsync(manipResult.uri, {
          encoding: FileSystem.EncodingType.Base64,
        });
        const jpegBytes = base64ToUint8Array(rawBase64);

        if (!audioEngine.isGuidePlaying) {
          console.log(`[Camera/Real] ${stream} 프레임 압축완료: 원본경로=${path} -> base64len(CoreML용)=${base64.length} float32len=${float32.length}`);
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


  const captureFrame = isMockMode ? captureMockFrame : captureRealFrame;

  // ---- 캡처 루프 ----

  const startCapture = useCallback(
    (onFrame: (frame: FrameData) => void) => {
      if (isCapturing) return;
      onFrameRef.current = onFrame;
      setIsCapturing(true);

      baseIntervalRef.current = Math.floor(1000 / reflexFps);
      currentIntervalRef.current = baseIntervalRef.current;
      setCurrentReflexFps(reflexFps);
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
    [reflexFps, cognitiveFps, isCapturing, isMockMode, captureFrame],
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
  };
}

// FRAME_TENSOR_LENGTH re-export (사용처 참고용)
export { FRAME_TENSOR_LENGTH };

// 이미지의 실제 가로/세로 해상도를 비동기로 획득하는 헬퍼 함수
function getImageSize(uri: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    Image.getSize(
      uri,
      (width, height) => resolve({ width, height }),
      (err) => reject(err)
    );
  });
}

// 순수 JS 기반의 초고속 Base64 to Uint8Array 디코더 (Hermes 환경 최적화)
function base64ToUint8Array(base64: string): Uint8Array {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const lookup = new Uint8Array(256);
  for (let i = 0; i < chars.length; i++) {
    lookup[chars.charCodeAt(i)] = i;
  }
  
  let bufferLength = base64.length * 0.75;
  if (base64[base64.length - 1] === "=") {
    bufferLength--;
    if (base64[base64.length - 2] === "=") {
      bufferLength--;
    }
  }
  
  const bytes = new Uint8Array(bufferLength);
  let p = 0;
  for (let i = 0; i < base64.length; i += 4) {
    const base64x = lookup[base64.charCodeAt(i)];
    const base64y = lookup[base64.charCodeAt(i + 1)];
    const base64z = lookup[base64.charCodeAt(i + 2)];
    const base64w = lookup[base64.charCodeAt(i + 3)];
    
    bytes[p++] = (base64x << 2) | (base64y >> 4);
    if (p < bufferLength) {
      bytes[p++] = ((base64y & 15) << 4) | (base64z >> 2);
    }
    if (p < bufferLength) {
      bytes[p++] = ((base64z & 3) << 6) | (base64w & 63);
    }
  }
  return bytes;
}
