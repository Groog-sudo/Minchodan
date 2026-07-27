/**
 * Android 프레임 캡처 구현.
 *
 * Android도 이제 iOS와 동일한 이름("reflexFrameCapture")의 네이티브 Frame
 * Processor 플러그인을 사용해 반사 스트림을 메모리 경로로 받을 수 있다.
 * 다만 문서상 과도기 이력이 남아 있고, 플러그인 미등록/런타임 실패 시에는
 * takePhoto() 기반 폴백 경로가 여전히 필요하다.
 *
 * 공용 captureViaTakePhoto(frameCaptureProvider.ts)를 쓰지 않고 Android 전용 캡처
 * 로직을 이 파일에 독립적으로 둔다 - iOS와 동일하게 photo.orientation 메타데이터를
 * 신뢰해 크롭 좌표를 계산했더니 Android 실기기에서 비트맵 회전 불일치로 크롭 좌표가
 * 이미지 경계를 벗어나는 크래시가 실측 확인됐다(dg2 브랜치 실기기 테스트, 2026-07-10).
 * 대신 Image.getSize()로 실제 픽셀 해상도를 직접 얻어 크롭 좌표를 계산하고, 경계
 * 가드까지 적용한다. 크롭 자체를 생략하면(화면 프리뷰와 다른 종횡비로 늘려버리면)
 * bbox가 화면과 어긋나게 그려지므로 크롭은 유지하되 좌표 산출 방식만 바꾼다.
 *
 * Android 실기기에서 new File(uri).bytes()가 rejected 에러로 실패하는 사례가 있어,
 * FileSystem.readAsStringAsync + 수동 base64 디코딩으로 우회한다.
 */

import { useCallback, useRef } from "react";
import { Image } from "react-native";
import { decodeBase64JpegToHwc } from "./realFrameProvider";
import {
  type Camera,
  type PhotoFile,
  type Frame,
  type FrameProcessorPlugin,
  useFrameProcessor,
  VisionCameraProxy,
} from "react-native-vision-camera";
import { useRunOnJS } from "react-native-worklets-core";
import * as FileSystem from "expo-file-system/legacy";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import type { StreamType } from "../types/detection";
import type {
  FrameCaptureController,
  FrameCaptureProviderParams,
  FrameData,
} from "./frameCaptureProvider";
import { audioEngine } from "./audioEngine";

const reflexFrameProcessorPlugin: FrameProcessorPlugin | undefined =
  VisionCameraProxy.initFrameProcessorPlugin("reflexFrameCapture", {});

/** 캡처 파이프라인 전체가 이 시간을 넘기면 강제 취소한다(무한 대기 방지). */
const CAPTURE_TIMEOUT_MS = 3000;
let didLogPluginStatus = false;
let didLogTakePhotoFallback = false;
let didLogStreamFrame = false;

/** 순수 JS 기반 Base64 -> Uint8Array 디코더 (Hermes 환경 최적화). */
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
    const b0 = lookup[base64.charCodeAt(i)];
    const b1 = lookup[base64.charCodeAt(i + 1)];
    const b2 = lookup[base64.charCodeAt(i + 2)];
    const b3 = lookup[base64.charCodeAt(i + 3)];

    bytes[p++] = (b0 << 2) | (b1 >> 4);
    if (p < bufferLength) bytes[p++] = ((b1 & 15) << 4) | (b2 >> 2);
    if (p < bufferLength) bytes[p++] = ((b2 & 3) << 6) | (b3 & 63);
  }
  return bytes;
}

/** 이미지 파일의 실제 픽셀 가로/세로 해상도를 비동기로 얻는다(orientation 메타데이터 대신). */
function getImageSize(uri: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    Image.getSize(uri, (width, height) => resolve({ width, height }), reject);
  });
}

function withTimeout<T>(promise: Promise<T>, ms: number, errorMessage: string): Promise<T> {
  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error(errorMessage)), ms),
  );
  return Promise.race([promise, timeout]);
}

async function captureViaTakePhotoAndroid(
  cameraRef: React.RefObject<Camera | null>,
  isCapturingRef: { current: boolean },
  stream: StreamType,
): Promise<FrameData | null> {
  if (!cameraRef.current) {
    console.warn(`[Camera/Real-Android] ${stream} 캡처 실패: cameraRef 없음`);
    return null;
  }
  if (isCapturingRef.current) {
    return null;
  }
  isCapturingRef.current = true;

  try {
    return await withTimeout(
      (async () => {
        const photo: PhotoFile = await cameraRef.current!.takePhoto({
          flash: "off",
          enableShutterSound: false,
        });
        const path = photo.path.startsWith("file://")
          ? photo.path
          : `file://${photo.path}`;

        // photo.orientation 메타데이터를 신뢰하지 않고 실제 픽셀 크기를 직접 얻는다 -
        // Android 실기기에서 orientation 기반 크롭 좌표가 이미지 경계를 벗어나
        // 크래시가 발생한 것을 실측 확인했다.
        const { width, height } = await getImageSize(path);
        const cropSize = Math.min(width, height);
        let originX = Math.floor((width - cropSize) / 2);
        let originY = Math.floor((height - cropSize) / 2);

        // 음수/경계 초과 좌표 방지 가드
        if (originX < 0) originX = 0;
        if (originY < 0) originY = 0;
        if (originX + cropSize > width) originX = Math.max(0, width - cropSize);
        if (originY + cropSize > height) originY = Math.max(0, height - cropSize);

        // Frame Processor와 동일: Android 실측 180도 추가 보정(콘솔 상하 반전 해소).
        const manipResult = await manipulateAsync(
          path,
          [
            { crop: { originX, originY, width: cropSize, height: cropSize } },
            { resize: { width: 640, height: 640 } },
            { rotate: 180 },
          ],
          { compress: 0.7, format: SaveFormat.JPEG, base64: true },
        );

        const base64 = manipResult.base64 ?? "";
        const float32 = decodeBase64JpegToHwc(base64);

        // Android 실기기에서 new File(uri).bytes()가 rejected 에러로 실패하는 사례가
        // 있어 FileSystem.readAsStringAsync + 수동 디코딩으로 우회한다.
        const rawBase64 = await FileSystem.readAsStringAsync(manipResult.uri, {
          encoding: FileSystem.EncodingType.Base64,
        });
        const jpegBytes = base64ToUint8Array(rawBase64);

        if (!audioEngine.isGuidePlaying) {
          console.log(
            `[Camera/Real-Android] ${stream} 프레임 완료: bytes=${jpegBytes.length} base64len=${base64.length}`,
          );
        }

        void FileSystem.deleteAsync(path, { idempotent: true }).catch(() => { });
        void FileSystem.deleteAsync(manipResult.uri, { idempotent: true }).catch(() => { });

        return { float32, stream, base64, jpegBytes };
      })(),
      CAPTURE_TIMEOUT_MS,
      `[Camera/Real-Android] 캡처 처리 시간 초과(${CAPTURE_TIMEOUT_MS}ms)`,
    );
  } catch (err) {
    console.error(`[Camera/Real-Android] ${stream} 캡처 오류:`, err);
    return null;
  } finally {
    isCapturingRef.current = false;
  }
}

export function useFrameCaptureProvider(
  params: FrameCaptureProviderParams,
): FrameCaptureController {
  const { cameraRef, intervalSharedValue, lastCaptureTsShared, onStreamFrameBase64 } = params;
  const isCapturingRef = useRef(false);
  const supportsStream = reflexFrameProcessorPlugin != null;

  if (!didLogPluginStatus) {
    console.log(
      `[Camera/Android] reflexFrameCapture plugin ${supportsStream ? "등록됨" : "미등록"} - ${supportsStream ? "frameProcessor" : "takePhoto 폴백"} 경로 사용`,
    );
    didLogPluginStatus = true;
  }

  const onFrameBase64 = useRunOnJS(
    (base64: string) => {
      if (!didLogStreamFrame) {
        didLogStreamFrame = true;
        console.log("[Camera/Android] frameProcessor 반사 스트림 첫 프레임 수신");
      }
      onStreamFrameBase64(base64);
    },
    [onStreamFrameBase64],
  );

  const frameProcessor = useFrameProcessor(
    (frame: Frame) => {
      "worklet";
      if (reflexFrameProcessorPlugin == null) return;
      const now = Date.now();
      if (now - lastCaptureTsShared.value < intervalSharedValue.value) return;
      lastCaptureTsShared.value = now;

      // worklet 컨텍스트에서는 모듈 스코프 let 변수에 대입할 수 없다
      // (Hermes: invalid assignment left-hand side). 로그는 JS 스레드 콜백에서만.
      const result = reflexFrameProcessorPlugin.call(frame);
      if (typeof result === "string" && result.length > 0) {
        onFrameBase64(result);
      }
    },
    [onFrameBase64],
  );

  const capturePhoto = useCallback(
    (stream: StreamType): Promise<FrameData | null> => {
      if (!didLogTakePhotoFallback) {
        didLogTakePhotoFallback = true;
        console.warn(
          "[Camera/Android] takePhoto 폴백 경로 진입 - 플러그인 미등록 또는 스트림 미사용 상태",
        );
      }
      return captureViaTakePhotoAndroid(cameraRef, isCapturingRef, stream);
    },
    [cameraRef],
  );

  return {
    supportsStream,
    frameProcessor,
    capturePhoto,
  };
}
