/**
 * 프레임 공급 추상화.
 * TFLite 온디바이스 추론 입력 텐서(640x640x3 CHW, 정규화 0~1)를 공급한다.
 *
 * 모델 입력 shape: [1, 3, 640, 640] float32 (CHW RGB)
 *  -> 총 길이 3*640*640 = 1,228,800
 *  -> 메모리 레이아웃: R[0..H*W), G[H*W..2*H*W), B[2*H*W..3*H*W)
 *
 * 프레임 소스:
 *  - Mock(MOCK_CAMERA=true): MockFrameProvider가 번들 샘플을 공급 (시뮬레이터)
 *  - Real(MOCK_CAMERA=false): useCamera가 takePhoto 결과를 decodeBase64JpegToChw 로 변환 (실기기)
 *    -> Real은 카메라 훅이 프레임을 생산하므로 Provider 인스턴스 없이 디코더 유틸만 사용.
 */

import { MOCK_CAMERA } from "../config/mock";
import { decodeBase64JpegToChw } from "./realFrameProvider";
import type { MockFrameProvider } from "./mockFrameProvider";

export const FRAME_SIZE = 640;
export const FRAME_TENSOR_LENGTH = FRAME_SIZE * FRAME_SIZE * 3;

export interface FrameProvider {
  /** 640x640x3 CHW 정규화 float32 프레임을 반환한다. */
  getFrame(): Promise<Float32Array>;
  /** preview용 소스. Mock 전용. */
  getPreviewSource?(): number | string | null;
  dispose?(): void;
}

export { decodeBase64JpegToChw };

let _instance: FrameProvider | null = null;

/**
 * Mock 모드일 때만 MockFrameProvider 인스턴스를 반환.
 * Real 모드는 null (카메라 훅이 직접 디코딩).
 */
export function getFrameProvider(): FrameProvider | null {
  if (!MOCK_CAMERA) return null;
  if (_instance) return _instance;
  const { createMockFrameProvider } = require("./mockFrameProvider") as {
    createMockFrameProvider: () => MockFrameProvider;
  };
  _instance = createMockFrameProvider();
  return _instance;
}
