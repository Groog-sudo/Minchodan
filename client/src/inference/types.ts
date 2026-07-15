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

export interface DualDetectionResult {
  seg: DetectionResult[];
  det: DetectionResult[];
  scene?: SceneClassification;
}
