import { DualDetectionResult } from "./types";

export interface LocalDetector {
  readonly isLoaded: boolean;
  readonly segLoaded: boolean;
  readonly detLoaded: boolean;
  readonly detShapeLog: string;
  /**
   * 입력 계약: true면 Float32Array 정규화 텐서(TFLite)를 요구하고,
   * false면 base64 JPEG만 사용(CoreML)한다.
   *
   * 💡 [면접 대비 주석] 이 플래그로 상류 캡처 계층이 불필요한 JS JPEG 디코딩과
   * ~4.7MiB Float32Array 할당을 건너뛴다 (2026-07-17, P0).
   * CoreML 정상 모드는 base64만 네이티브에 넘기는데도 이전에는 매 프레임마다
   * float32 변환을 수행해 JS 스레드를 포화시켰다 - 단말 버튼 반응 지연의 직접 원인.
   */
  readonly requiresFloat32: boolean;

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
