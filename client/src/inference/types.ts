export interface DetectionResult {
  model: "segmentation" | "object_detection";
  className: string;
  confidence: number;
  bbox: { x: number; y: number; w: number; h: number };
}

export type InferenceFrame = Float32Array;

export interface DualDetectionResult {
  seg: DetectionResult[];
  det: DetectionResult[];
}
