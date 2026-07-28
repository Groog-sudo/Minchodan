export interface DetectionResult {
  model: "segmentation" | "object_detection";
  className: string;
  confidence: number;
  bbox: { x: number; y: number; w: number; h: number };
  distanceMeters?: number | null;
  distanceSource?: "lidar" | "heuristic" | "none";
  depthSampleCount?: number;
  depthAccuracy?: "absolute" | "relative";
}

export type InferenceFrame = Float32Array;

// docs/design/indoor_fp_mitigation_design.md §4 - 씬 분류 결과.
// iOS: VNClassifyImageRequest / Android: ML Kit Image Labeling (SceneClassifyBridgeModule).
export interface SceneClassification {
  isLikelyIndoor: boolean;
  confidence: number;
  topLabels: { identifier: string; confidence: number }[];
}

/**
 * 네이티브 추론 브릿지가 보고하는 구간별 지연(ms).
 * iOS CoreMLInferenceBridge / Android TFLiteInferenceBridge 모두 동일 키를 쓴다.
 */
export interface InferenceBenchmark {
  det_ms?: number;
  seg_ms?: number;
  prep_ms?: number;
  scene_ms?: number;
  total_ms?: number;
}

export interface DualDetectionResult {
  seg: DetectionResult[];
  det: DetectionResult[];
  scene?: SceneClassification;
  /**
   * 2026-07-28: 타입에 없어 디텍터가 반환하지 않았고, CameraView.runDetectionResult가
   * 항상 undefined를 받아 `reportInferenceLatency(0)`을 호출했다. 동적 FPS 조절의
   * 과부하 보호(추론이 캡처 간격을 못 따라가면 간격을 늘림)가 무력화된 상태였다.
   */
  benchmark?: InferenceBenchmark;
}
