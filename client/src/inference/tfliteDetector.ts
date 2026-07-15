import { Platform, NativeModules } from "react-native";
import {
  loadTensorflowModel,
  type TensorflowModel,
  type TensorflowModelDelegate,
} from "react-native-fast-tflite";
import { LocalDetector } from "./localDetector";
import { DualDetectionResult, DetectionResult, SceneClassification } from "./types";
import { audioEngine } from "../services/audioEngine";

const { SceneClassifyBridgeModule } = NativeModules;

const ACCELERATION_DELEGATES: TensorflowModelDelegate[] = Platform.select({
  ios: ["core-ml"],
  // android: NNAPI 호환성 문제 우회 - CPU 모드로 강제해 탐지 미작동 원인 조사 (2026-07-14)
  android: [],
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

const CONF_THRESHOLD = 0.35; // 오탐 방지를 위해 서버와 동일하게 0.35로 상향
const IOU_THRESHOLD = 0.45; // 중복 박스 제거(NMS) 기준

function calculateIoU(box1: { x: number, y: number, w: number, h: number }, box2: { x: number, y: number, w: number, h: number }) {
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
    if (!model || !this.isLoaded) return [];
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
        if (off + 5 >= out.length) break;

        // ultralytics nms=True export 출력 포맷은 [x1, y1, x2, y2, confidence, classId]
        // 코너 좌표(픽셀 단위)이다. xc/yc/w/h 중심좌표가 아니므로 min/max로 정규화해서 계산한다.
        const x1 = Math.min(out[off], out[off + 2]);
        const y1 = Math.min(out[off + 1], out[off + 3]);
        const x2 = Math.max(out[off], out[off + 2]);
        const y2 = Math.max(out[off + 1], out[off + 3]);
        const w = x2 - x1;
        const h = y2 - y1;
        const xc = x1 + w / 2;
        const yc = y1 + h / 2;
        const maxScore = out[off + 4];
        const clsId = Math.round(Math.abs(out[off + 5]));

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

    // 입력 shape 검증 로그: 640x640x3 = 1,228,800 이어야 모델 입력 스펙과 정합
    const expectedLen = 640 * 640 * 3;
    if (frame.length !== expectedLen) {
      console.warn(`[TFLiteDetector] 입력 shape 불일치: 실제=${frame.length}, 기대=${expectedLen}`);
    } else {
      console.log(`[TFLiteDetector] 입력 shape OK: ${frame.length}`);
    }


    const segFrame = frame.slice(0);
    const [seg, det, scene] = await Promise.all([
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
      this.classifySceneAndroid(base64),
    ]);

    return { seg, det, scene };
  }

  /**
   * Android: ML Kit Image Labeling 네이티브 브릿지로 iOS scene.isLikelyIndoor 동등 신호 산출.
   * 모듈/base64 없으면 undefined → CameraView는 허용적(실외) 폴백.
   */
  private async classifySceneAndroid(
    base64: string | null,
  ): Promise<SceneClassification | undefined> {
    if (Platform.OS !== "android" || !base64 || !SceneClassifyBridgeModule?.classifyScene) {
      return undefined;
    }
    try {
      const scene = await SceneClassifyBridgeModule.classifyScene(base64) as SceneClassification;
      if (scene?.topLabels?.length && !audioEngine.isGuidePlaying) {
        const labels = scene.topLabels
          .map((l) => `${l.identifier}(${l.confidence.toFixed(2)})`)
          .join(", ");
        console.log(`[SceneClassify][Android] indoor=${scene.isLikelyIndoor} ${labels}`);
      }
      return scene;
    } catch (err) {
      console.warn("[TFLiteDetector] SceneClassify 실패, 씬 게이트 스킵:", err);
      return undefined;
    }
  }

  dispose() {
    this.isLoaded = false;
    if (this.segModel) {
      try {
        this.segModel.dispose();
      } catch { }
      this.segModel = null;
    }
    if (this.detModel) {
      try {
        this.detModel.dispose();
      } catch { }
      this.detModel = null;
    }
  }
}
