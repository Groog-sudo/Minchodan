/**
 * 프레임 공급 추상화.
 * TFLite 온디바이스 추론 입력 텐서(640x640x3 NHWC, 값 범위 0~1 정규화)를 공급한다.
 *
 * 모델 입력 shape: [1, 640, 640, 3] float32 (HWC RGB)
 *  -> 총 길이 3*640*640 = 1,228,800
 *  -> 메모리 레이아웃: R0, G0, B0, R1, G1, B1, ...
 *  -> 값 범위: 0~1 (/255 정규화, Ultralytics 표준)
 *
 * 프레임 소스:
 *  - Mock(MOCK_CAMERA=true): MockFrameProvider가 번들 샘플을 공급 (시뮬레이터)
 *  - Real(MOCK_CAMERA=false): useCamera가 takePhoto 결과를 decodeBase64JpegToHwc 로 변환 (실기기)
 *    -> Real은 카메라 훅이 프레임을 생산하므로 Provider 인스썬스 없이 디코더 유틸만 사용.
 */

import { MOCK_CAMERA } from "../config/mock";
import { decodeBase64JpegToHwc } from "./realFrameProvider";
import type { MockFrameProvider } from "./mockFrameProvider";

export const FRAME_SIZE = 640;
export const FRAME_TENSOR_LENGTH = FRAME_SIZE * FRAME_SIZE * 3;

export interface FrameProvider {
  /** 640x640x3 NHWC 정규화 float32 프레임을 반환한다. */
  getFrame(): Promise<Float32Array>;
  /** preview용 소스. Mock 전용. */
  getPreviewSource?(): number | string | null;
  dispose?(): void;
}

export { decodeBase64JpegToHwc };

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
