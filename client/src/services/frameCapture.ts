import type { StreamType } from "../types/detection";

export interface FrameData {
  float32: Float32Array;
  stream: StreamType;
  // CoreML 네이티브 브릿지 호출용 (RN 브릿지는 JSON 직렬화 가능 타입만 인자로 받으므로 base64 유지 필요)
  base64: string | null;
  // 서버 WS 전송용 raw JPEG 바이트 (base64 미경유, 바이너리 프레임으로 직접 전송)
  jpegBytes: Uint8Array | null;
}

export interface FrameCaptureProvider {
  /**
   * 연속 스트림 캡처 시작 (프레임 프로세서 기반, 플랫폼 네이티브가 프레임을 밀어 넣는 방식).
   * supportsStream이 true인 플랫폼에서만 실제로 동작합니다.
   */
  startStream(onFrame: (frame: FrameData) => void, intervalMs: number): boolean;

  /**
   * 단발 촬영 기반 캡처 (레거시/폴백 경로).
   * supportsStream이 false인 플랫폼의 기본 캡처 경로입니다.
   */
  capturePhoto(stream: StreamType): Promise<FrameData | null>;

  /** 스트림 캡처 지원 여부 (상위 훅이 타이머 루프를 돌릴지 결정하는 데 사용) */
  readonly supportsStream: boolean;

  /** 캡처 리소스 해제 및 중지 */
  stop(): void;
}

export { useFrameCaptureProvider } from "./frameCaptureSelect";
