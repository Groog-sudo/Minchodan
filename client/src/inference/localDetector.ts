import { DualDetectionResult } from "./types";

export interface LocalDetector {
  readonly isLoaded: boolean;
  readonly segLoaded: boolean;
  readonly detLoaded: boolean;
  readonly detShapeLog: string;

  /**
   * 모델 로드 함수.
   * @returns 로드 성공 여부
   */
  load(): Promise<boolean>;

  /**
   * 단일 프레임 추론.
   * @param frame Float32Array 정규화 텐서 데이터 (TFLite용)
   * @param base64 base64 jpeg 이미지 문자열 (CoreML용)
   */
  detect(frame: Float32Array, base64: string | null): Promise<DualDetectionResult>;

  /**
   * 리소스 해제
   */
  dispose(): void;
}

/**
 * 플랫폼별 팩토리 진입점.
 * Metro 번들러가 localDetector.ios.ts 또는 localDetector.android.ts를 자동 컴파일하여 바인딩합니다.
 */
export { createLocalDetector } from "./localDetectorSelect";
