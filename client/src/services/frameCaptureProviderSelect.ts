/**
 * 프레임 캡처 제공자 - 플랫폼 무관 기본 구현.
 *
 * Metro 번들러는 빌드 시 항상 frameCaptureProviderSelect.ios.ts 또는 .android.ts를
 * 우선 선택하므로 실제 앱에서는 이 파일이 사용되지 않는다. 다만 tsc(정적 타입체크)는
 * RN의 플랫폼 확장자 분기를 인식하지 못해 이 바코드(확장자 없는) 파일을 필요로 한다
 * (client/src/inference/localDetectorSelect.ts와 동일한 이유).
 *
 * 안전한 기본값으로 takePhoto() 기반 구현(Android 과도기 구현과 동일)을 사용한다.
 */

import { useRef } from "react";

import type { StreamType } from "../types/detection";
import {
  captureViaTakePhoto,
  readJpegBytesDefault,
  type FrameCaptureController,
  type FrameCaptureProviderParams,
  type FrameData,
} from "./frameCaptureProvider";

export function useFrameCaptureProvider(
  params: FrameCaptureProviderParams,
): FrameCaptureController {
  const { cameraRef } = params;
  const isCapturingRef = useRef(false);

  const capturePhoto = (stream: StreamType): Promise<FrameData | null> =>
    captureViaTakePhoto(cameraRef, isCapturingRef, stream, readJpegBytesDefault);

  return {
    supportsStream: false,
    frameProcessor: undefined,
    capturePhoto,
  };
}
