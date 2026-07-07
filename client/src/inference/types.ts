export interface DetectionResult {
  model: "segmentation" | "object_detection";
  className: string;
  confidence: number;
  bbox: { x: number; y: number; w: number; h: number };
}

export type InferenceFrame = Float32Array;

// docs/design/indoor_fp_mitigation_design.md §4.3 - VNClassifyImageRequest 씬 분류 결과 (iOS 전용).
export interface SceneClassification {
  isLikelyIndoor: boolean;
  confidence: number;
  topLabels: { identifier: string; confidence: number }[];
}

export interface DualDetectionResult {
  seg: DetectionResult[];
  det: DetectionResult[];
  scene?: SceneClassification;
}
