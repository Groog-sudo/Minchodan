/**
 * iOS 프레임 캡처 구현.
 * client/ios/ReflexFrameProcessorPlugin.swift(등록명 "reflexFrameCapture")를 통해
 * AVCaptureVideoDataOutput 기반 연속 스트림으로 반사 프레임을 획득한다.
 * (2026-07-09 도입 - takePhoto() 반복 호출이 AVAudioSessionInterruption을 유발해
 * TTS가 끊기는 문제를 우회하기 위해 전환. 상세: docs/changelogs/kb.md)
 */

import { useRef } from "react";
import {
  type Frame,
  type FrameProcessorPlugin,
  useFrameProcessor,
  VisionCameraProxy,
} from "react-native-vision-camera";
import { useRunOnJS } from "react-native-worklets-core";

import type { StreamType } from "../types/detection";
import {
  captureViaTakePhoto,
  readJpegBytesDefault,
  type FrameCaptureController,
  type FrameCaptureProviderParams,
  type FrameData,
} from "./frameCaptureProvider";

// 모듈 스코프에서 1회만 생성한다 - 네이티브 리소스(CIContext)를 갖고 있어 컴포넌트
// 리렌더마다 재생성하면 매번 새 네이티브 인스턴스가 생긴다. 등록명은
// ReflexFrameProcessorPlugin.swift와 반드시 일치해야 한다.
const reflexFrameProcessorPlugin: FrameProcessorPlugin | undefined =
  VisionCameraProxy.initFrameProcessorPlugin("reflexFrameCapture", {});

export function useFrameCaptureProvider(
  params: FrameCaptureProviderParams,
): FrameCaptureController {
  const { cameraRef, intervalSharedValue, lastCaptureTsShared, onStreamFrameBase64 } = params;
  const isCapturingRef = useRef(false);

  const onFrameBase64 = useRunOnJS(
    (base64: string) => onStreamFrameBase64(base64),
    [onStreamFrameBase64],
  );

  // 카메라 전체 fps(예: 30fps)로 호출되므로, 반사 fps 간격(intervalSharedValue)으로
  // throttle해야 추론이 못 따라가는 것을 막는다(동적 fps 조절과 동일한 목적).
  const frameProcessor = useFrameProcessor(
    (frame: Frame) => {
      "worklet";
      if (reflexFrameProcessorPlugin == null) return;
      const now = Date.now();
      if (now - lastCaptureTsShared.value < intervalSharedValue.value) return;
      lastCaptureTsShared.value = now;

      const result = reflexFrameProcessorPlugin.call(frame);
      if (typeof result === "string" && result.length > 0) {
        onFrameBase64(result);
      }
    },
    [onFrameBase64],
  );

  const capturePhoto = (stream: StreamType): Promise<FrameData | null> =>
    // 2026-07-12: iOS 실기기에서 확인된 180도 방향 반전 보정 적용 (frameCaptureProvider.ts 주석 참조)
    captureViaTakePhoto(cameraRef, isCapturingRef, stream, readJpegBytesDefault, true);

  return {
    // 네이티브 플러그인이 등록되지 않은 경우(개발 빌드 미동기화 등) takePhoto로 자동 폴백.
    supportsStream: reflexFrameProcessorPlugin != null,
    frameProcessor,
    capturePhoto,
  };
}
