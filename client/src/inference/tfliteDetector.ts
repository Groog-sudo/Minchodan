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

const COCO_CLASS_NAMES = [
  "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
  "truck", "boat", "traffic light", "fire hydrant", "stop sign",
  "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
  "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
  "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
  "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
  "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana",
  "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
  "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table",
  "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
  "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock",
  "vase", "scissors", "teddy bear", "hair drier", "toothbrush",
];

const CONF_THRESHOLD = 0.25;

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

      const results: DetectionResult[] = [];
      for (let i = 0; i < numBoxes; i++) {
        const off = i * attrsPerBox;
        const x1 = Math.min(out[off], out[off + 2]);
        const y1 = Math.min(out[off + 1], out[off + 3]);
        const x2 = Math.max(out[off], out[off + 2]);
        const y2 = Math.max(out[off + 1], out[off + 3]);
        const score = out[off + 4];
        const cls = Math.round(Math.abs(out[off + 5]));

        if (score < CONF_THRESHOLD || cls >= numClasses) continue;
        const w = x2 - x1;
        const h = y2 - y1;
        if (w <= 1 || h <= 1) continue;

        results.push({
          model: label,
          className: names[cls] ?? `cls_${cls}`,
          confidence: score,
          bbox: { x: x1, y: y1, w, h },
        });
      }
      return results.sort((a, b) => b.confidence - a.confidence);
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
        6,
        COCO_CLASS_NAMES.length,
        COCO_CLASS_NAMES,
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
