import { useCallback, useMemo, useRef } from "react";
import { type PhotoFile } from "react-native-vision-camera";
import * as FileSystem from "expo-file-system/legacy";
import { manipulateAsync, SaveFormat } from "expo-image-manipulator";

import type { FrameCaptureProvider, FrameData } from "./frameCapture";
import type { StreamType } from "../types/detection";
import { audioEngine } from "./audioEngine";

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

// 헬퍼: 비동기 작업에 타임아웃을 거는 래퍼 함수
function withTimeout<T>(promise: Promise<T>, ms: number, errorMessage: string): Promise<T> {
  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error(errorMessage)), ms)
  );
  return Promise.race([promise, timeout]);
}

export function useFrameCaptureProvider(
  cameraRef: React.RefObject<any>,
  intervalSharedValue: any,
  lastCaptureTsShared: any
): FrameCaptureProvider {
  const onFrameRef = useRef<((frame: FrameData) => void) | null>(null);
  const isCapturingRealFrame = useRef(false);

  // Android 단발 촬영 및 수동 디코드 기반의 프레임 캡처 구현
  const capturePhoto = useCallback(
    async (stream: StreamType): Promise<FrameData | null> => {
      if (!cameraRef.current) {
        console.warn(`[Camera/Real-Android] ${stream} 캡처 실패: cameraRef 없음`);
        return null;
      }
      if (isCapturingRealFrame.current) {
        return null;
      }
      isCapturingRealFrame.current = true;

      try {
        // 비비동기 대기 방지를 위해 전체 캡처 가공 흐름에 3초 강제 타임아웃 적용
        return await withTimeout(
          (async () => {
            const photo: PhotoFile = await cameraRef.current.takePhoto({
              flash: "off",
              enableShutterSound: false,
            });
            const path = photo.path.startsWith("file://")
              ? photo.path
              : `file://${photo.path}`;

            // 이미지 크롭을 제외하고 다이렉트 리사이징 및 압축 수행 (비트맵 회전 불일치 크래시 100% 원천 예방)
            const manipResult = await manipulateAsync(
              path,
              [
                { resize: { width: 640, height: 640 } },
              ],
              { compress: 0.5, format: SaveFormat.JPEG, base64: true }
            );

            const base64 = manipResult.base64 ?? "";
            const float32 = new Float32Array(0);

            // FileSystem.readAsStringAsync 우회 읽기 적용 후 수동 Uint8Array 디코드
            const rawBase64 = await FileSystem.readAsStringAsync(manipResult.uri, {
              encoding: FileSystem.EncodingType.Base64,
            });
            const jpegBytes = base64ToUint8Array(rawBase64);

            if (!audioEngine.isGuidePlaying) {
              console.log(
                `[Camera/Real-Android] ${stream} 프레임 완료: bytes=${jpegBytes.length} base64len=${base64.length}`
              );
            }

            // 임시 파일 청소
            void FileSystem.deleteAsync(path, { idempotent: true }).catch(() => {});
            void FileSystem.deleteAsync(manipResult.uri, { idempotent: true }).catch(() => {});

            return { float32, stream, base64, jpegBytes };
          })(),
          3000,
          `[Camera/Real-Android] 캡처 처리 시간 초과(3000ms)`
        );
      } catch (err) {
        console.error(`[Camera/Real-Android] ${stream} 캡처 오류:`, err);
        return null;
      } finally {
        isCapturingRealFrame.current = false;
      }
    },
    [cameraRef]
  );

  const startStream = useCallback(
    (onFrame: (frame: FrameData) => void, intervalMs: number): boolean => {
      onFrameRef.current = onFrame;
      console.log("[Camera/Real-Android] Android 스트림 미지원 - 단발 캡처 루프로 동작합니다.");
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
