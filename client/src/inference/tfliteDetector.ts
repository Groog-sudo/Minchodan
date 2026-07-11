import { Platform } from "react-native";
import {
  loadTensorflowModel,
  type TensorflowModel,
  type TensorflowModelDelegate,
} from "react-native-fast-tflite";
import { LocalDetector } from "./localDetector";
import { DualDetectionResult, DetectionResult } from "./types";

const ACCELERATION_DELEGATES: TensorflowModelDelegate[] = Platform.select({
  ios: ["core-ml"],
  android: ["nnapi"],
  default: [],
}) ?? [];

const SEG_CLASS_NAMES = [
  "sidewalk_normal",
  "caution",
  "roadway",
  "braille_normal",
];

const AIHUB_CLASS_NAMES = [
  "barricade", "bench", "bicycle", "bollard", "bus", "car", "carrier", "cat",
  "chair", "dog", "fire_hydrant", "kiosk", "motorcycle", "movable_signage",
  "parking_meter", "person", "pole", "potted_plant", "power_controller",
  "scooter", "stop", "stroller", "table", "traffic_light", "traffic_light_controller",
  "traffic_sign", "tree_trunk", "truck", "wheelchair"
];

const CONF_THRESHOLD = 0.50; // 오탐 방지를 위해 0.25에서 0.50으로 상향
const IOU_THRESHOLD = 0.45; // 중복 박스 제거(NMS) 기준

function calculateIoU(box1: {x:number, y:number, w:number, h:number}, box2: {x:number, y:number, w:number, h:number}) {
  const x1 = Math.max(box1.x, box2.x);
  const y1 = Math.max(box1.y, box2.y);
  const x2 = Math.min(box1.x + box1.w, box2.x + box2.w);
  const y2 = Math.min(box1.y + box1.h, box2.y + box2.h);
  const intersection = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
  const area1 = box1.w * box1.h;
  const area2 = box2.w * box2.h;
  return intersection / (area1 + area2 - intersection);
}

function nonMaxSuppression(boxes: DetectionResult[], iouThreshold: number): DetectionResult[] {
  const sorted = [...boxes].sort((a, b) => b.confidence - a.confidence);
  const keep: DetectionResult[] = [];
  for (const box of sorted) {
    let shouldKeep = true;
    for (const keptBox of keep) {
      if (box.className === keptBox.className && calculateIoU(box.bbox, keptBox.bbox) > iouThreshold) {
        shouldKeep = false;
        break;
      }
    }
    if (shouldKeep) keep.push(box);
  }
  return keep;
}

export class TFLiteDetector implements LocalDetector {
  isLoaded = false;
  segLoaded = false;
  detLoaded = false;
  detShapeLog = "";

  private segModel: TensorflowModel | null = null;
  private detModel: TensorflowModel | null = null;

  private async loadModelWithFallback(source: number, label: string): Promise<TensorflowModel> {
    try {
      return await loadTensorflowModel(source, ACCELERATION_DELEGATES);
    } catch (err) {
      console.warn(`[TFLiteDetector] ${label} delegate 로드 실패, CPU 폴백:`, err);
      return await loadTensorflowModel(source, []);
    }
  }

  async load(): Promise<boolean> {
    try {
      console.log("[TFLiteDetector] segmentation.tflite 로딩...");
      this.segModel = await this.loadModelWithFallback(
        require("../../assets/models/yolo26n/segmentation.tflite"),
        "segmentation"
      );
      this.segLoaded = true;

      console.log("[TFLiteDetector] object_detection.tflite 로딩...");
      this.detModel = await this.loadModelWithFallback(
        require("../../assets/models/yolo26n/object_detection.tflite"),
        "object_detection"
      );
      this.detLoaded = true;

      const outShape = this.detModel.outputs?.[0]?.shape;
      this.detShapeLog = outShape ? `[${outShape.join(",")}]` : "(알 수 없음)";
      this.isLoaded = true;

      console.log("[TFLiteDetector] 듀얼 TFLite 모델 로드 성공");
      return true;
    } catch (e) {
      console.error("[TFLiteDetector] 모델 로드 실패:", e);
      return false;
    }
  }

  private async runModel(
    model: TensorflowModel | null,
    attrsPerBox: number,
    numClasses: number,
    names: readonly string[],
    label: "segmentation" | "object_detection",
    buffer: ArrayBuffer
  ): Promise<DetectionResult[]> {
    if (!model) return [];
    try {
      const outputs = await model.run([buffer]);
      let out: Float32Array = new Float32Array(0);
      for (let oi = 0; oi < outputs.length; oi++) {
        const cand = new Float32Array(outputs[oi]);
        if (cand.length % attrsPerBox === 0 && cand.length >= attrsPerBox) {
          out = cand;
          break;
        }
      }
      if (out.length === 0 && outputs.length > 0) {
        out = new Float32Array(outputs[0]);
      }
      const numBoxes = Math.floor(out.length / attrsPerBox);
      const shape = model.outputs?.[0]?.shape || [];
      const isTransposed = shape.length >= 3 && shape[1] === attrsPerBox; // e.g. [1, 33, 8400]

      const results: DetectionResult[] = [];
      for (let i = 0; i < numBoxes; i++) {
        let xc, yc, w, h, maxScore = 0, clsId = -1;

        if (label === "object_detection" && attrsPerBox >= 33) {
          // Yolo 26N Format
          if (isTransposed) {
            // Memory layout: [1, attrsPerBox, numBoxes] -> out[attr * numBoxes + i]
            xc = out[0 * numBoxes + i];
            yc = out[1 * numBoxes + i];
            w  = out[2 * numBoxes + i];
            h  = out[3 * numBoxes + i];
            for (let c = 0; c < numClasses; c++) {
              const score = out[(4 + c) * numBoxes + i];
              if (score > maxScore) {
                maxScore = score;
                clsId = c;
              }
            }
          } else {
            // Memory layout: [1, numBoxes, attrsPerBox] -> out[i * attrsPerBox + attr]
            const off = i * attrsPerBox;
            xc = out[off];
            yc = out[off + 1];
            w  = out[off + 2];
            h  = out[off + 3];
            for (let c = 0; c < numClasses; c++) {
              const score = out[off + 4 + c];
              if (score > maxScore) {
                maxScore = score;
                clsId = c;
              }
            }
          }
        } else {
          // Legacy/Fallback Format
          const off = i * attrsPerBox;
          const x1 = Math.min(out[off], out[off + 2]);
          const y1 = Math.min(out[off + 1], out[off + 3]);
          const x2 = Math.max(out[off], out[off + 2]);
          const y2 = Math.max(out[off + 1], out[off + 3]);
          w = x2 - x1;
          h = y2 - y1;
          xc = x1 + w / 2;
          yc = y1 + h / 2;
          maxScore = out[off + 4];
          clsId = Math.round(Math.abs(out[off + 5]));
        }

        if (maxScore < CONF_THRESHOLD || clsId >= numClasses) continue;
        if (w <= 1 || h <= 1) continue;

        results.push({
          model: label,
          className: names[clsId] ?? `cls_${clsId}`,
          confidence: maxScore,
          bbox: { x: xc - w / 2, y: yc - h / 2, w, h },
        });
      }
      return nonMaxSuppression(results, IOU_THRESHOLD);
    } catch (err) {
      console.error(`[TFLiteDetector] ${label} 추론 에러:`, err);
      return [];
    }
  }

  async detect(frame: Float32Array, base64: string | null): Promise<DualDetectionResult> {
    if (!this.isLoaded) return { seg: [], det: [] };

    const segFrame = frame.slice(0);
    const [seg, det] = await Promise.all([
      this.runModel(
        this.segModel,
        38,
        SEG_CLASS_NAMES.length,
        SEG_CLASS_NAMES,
        "segmentation",
        segFrame.buffer as ArrayBuffer
      ),
      this.runModel(
        this.detModel,
        6, // YOLO 26N NMS-enabled format (4 coords + score + classId = 6)
        AIHUB_CLASS_NAMES.length,
        AIHUB_CLASS_NAMES,
        "object_detection",
        frame.buffer as ArrayBuffer
      ),
    ]);

    return { seg, det };
  }

  dispose() {
    this.isLoaded = false;
    if (this.segModel) {
      try {
        this.segModel.dispose();
      } catch {}
      this.segModel = null;
    }
    if (this.detModel) {
      try {
        this.detModel.dispose();
      } catch {}
      this.detModel = null;
    }
  }
}
