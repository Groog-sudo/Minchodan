/**
 * Android 프레임 캡처 구현 (과도기).
 *
 * Android는 아직 iOS의 ReflexFrameProcessorPlugin.swift에 대응하는 네이티브 Frame
 * Processor 플러그인이 없다 (docs/mobile/ios_android_bifurcation_contract.md §4.5).
 * 그 전까지는 takePhoto() 기반 단발 촬영 루프(supportsStream=false)로 동작한다.
 *
 * Android 실기기에서 new File(uri).bytes()가 rejected 에러로 실패하는 사례가 있어,
 * FileSystem.readAsStringAsync + 수동 base64 디코딩으로 우회한다.
 *
 * 후속 작업: Kotlin으로 "reflexFrameCapture" 이름의 Frame Processor 플러그인을
 * 작성해 등록하면, 이 파일의 supportsStream을 true로 전환하고 frameCaptureProviderSelect.ios.ts와
 * 동일한 구조(useFrameProcessor + VisionCameraProxy)로 교체한다.
 */

import { useRef } from "react";
import * as FileSystem from "expo-file-system/legacy";

import type { StreamType } from "../types/detection";
import {
  captureViaTakePhoto,
  type FrameCaptureController,
  type FrameCaptureProviderParams,
  type FrameData,
} from "./frameCaptureProvider";

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

async function readJpegBytesAndroid(uri: string): Promise<Uint8Array> {
  const rawBase64 = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  return base64ToUint8Array(rawBase64);
}

export function useFrameCaptureProvider(
  params: FrameCaptureProviderParams,
): FrameCaptureController {
  const { cameraRef } = params;
  const isCapturingRef = useRef(false);

  const capturePhoto = (stream: StreamType): Promise<FrameData | null> =>
    captureViaTakePhoto(cameraRef, isCapturingRef, stream, readJpegBytesAndroid);

  return {
    supportsStream: false,
    frameProcessor: undefined,
    capturePhoto,
  };
}
