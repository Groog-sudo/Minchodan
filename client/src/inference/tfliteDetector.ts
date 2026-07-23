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
  // det TFLite를 nms=False([1,33,8400])로 재export해 NON_MAX_SUPPRESSION_V4를 제거함(2026-07-24).
  // android-gpu 우선, 로드 실패 시 loadModelWithFallback이 CPU([])로 폴백.
  android: ["android-gpu"],
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

const CONF_THRESHOLD = 0.35; // seg 기본 임계값
const DET_CONF_THRESHOLD = 0.50; // det 오탐 완화 (기존 NMS-enabled 경로와 동일)
const IOU_THRESHOLD = 0.45; // JS NMS IoU 임계값
const DENSE_NUM_ANCHORS = 8400; // YOLO26n raw head anchors

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
  // TFLite는 항상 정규화 Float32Array 텐서를 입력으로 요구한다.
  readonly requiresFloat32 = true;

  private static detRawLogged = false;
  private static segRawLogged = false;

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

      console.log(`[TFLiteDetector DEBUG] segmentation inputs: ${JSON.stringify(this.segModel.inputs)}, outputs: ${JSON.stringify(this.segModel.outputs)}`);
      console.log(`[TFLiteDetector DEBUG] object_detection inputs: ${JSON.stringify(this.detModel.inputs)}, outputs: ${JSON.stringify(this.detModel.outputs)}`);

      console.log("[TFLiteDetector] 듀얼 TFLite 모델 로드 성공");
      return true;
    } catch (e) {
      console.error("[TFLiteDetector] 모델 로드 실패:", e);
      return false;
    }
  }

  /**
   * channels-first raw head 디코드: [1, 4+nc(+32 mask), 8400]
   * det(nms=False): [1,33,8400] / seg: [1,40,8400]
   * 반환 null이면 legacy NMS-enabled([1,300,6]) 경로로 넘긴다.
   */
  private decodeChannelsFirst(
    out: Float32Array,
    numClasses: number,
    names: readonly string[],
    label: "segmentation" | "object_detection",
  ): DetectionResult[] | null {
    const boxAttrs = 4 + numClasses;
    const withMaskAttrs = boxAttrs + 32;
    if (
      out.length !== boxAttrs * DENSE_NUM_ANCHORS &&
      out.length !== withMaskAttrs * DENSE_NUM_ANCHORS
    ) {
      return null;
    }

    const confThreshold =
      label === "object_detection" ? DET_CONF_THRESHOLD : CONF_THRESHOLD;
    const results: DetectionResult[] = [];
    for (let i = 0; i < DENSE_NUM_ANCHORS; i++) {
      let bestClassId = -1;
      let bestScore = -1;
      for (let c = 0; c < numClasses; c++) {
        const score = out[(4 + c) * DENSE_NUM_ANCHORS + i];
        if (score > bestScore) {
          bestScore = score;
          bestClassId = c;
        }
      }
      if (bestScore < confThreshold || bestClassId < 0) continue;
      const cx = out[0 * DENSE_NUM_ANCHORS + i] * 640;
      const cy = out[1 * DENSE_NUM_ANCHORS + i] * 640;
      const w = out[2 * DENSE_NUM_ANCHORS + i] * 640;
      const h = out[3 * DENSE_NUM_ANCHORS + i] * 640;
      if (w <= 1 || h <= 1) continue;
      results.push({
        model: label,
        className: names[bestClassId] ?? `cls_${bestClassId}`,
        confidence: bestScore,
        bbox: { x: cx - w / 2, y: cy - h / 2, w, h },
      });
    }
    return nonMaxSuppression(results, IOU_THRESHOLD);
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
      const denseLen = (4 + numClasses) * DENSE_NUM_ANCHORS;
      const denseMaskLen = denseLen + 32 * DENSE_NUM_ANCHORS;
      for (let oi = 0; oi < outputs.length; oi++) {
        const cand = new Float32Array(outputs[oi]);
        if (cand.length === denseLen || cand.length === denseMaskLen) {
          out = cand;
          break;
        }
        if (cand.length % attrsPerBox === 0 && cand.length >= attrsPerBox) {
          out = cand;
          break;
        }
      }
      if (out.length === 0 && outputs.length > 0) {
        out = new Float32Array(outputs[0]);
      }

      if (
        (label === "object_detection" && !TFLiteDetector.detRawLogged) ||
        (label === "segmentation" && !TFLiteDetector.segRawLogged)
      ) {
        if (label === "object_detection") TFLiteDetector.detRawLogged = true;
        else TFLiteDetector.segRawLogged = true;
        console.log(
          `[TFLiteDetector DEBUG] ${label} raw output length=${out.length} ` +
            `(dense=${denseLen}, legacyAttrs=${attrsPerBox})`,
        );
      }

      const denseDecoded = this.decodeChannelsFirst(out, numClasses, names, label);
      if (denseDecoded !== null) {
        return denseDecoded;
      }

      // legacy: ultralytics nms=True export [1,300,6] = [x1,y1,x2,y2,score,classId] 픽셀 코너
      const numBoxes = Math.floor(out.length / attrsPerBox);
      const results: DetectionResult[] = [];

      for (let i = 0; i < numBoxes; i++) {
        const off = i * attrsPerBox;
        if (off + 5 >= out.length) break;

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

        const currentConfThreshold =
          label === "object_detection" ? DET_CONF_THRESHOLD : CONF_THRESHOLD;
        if (maxScore < currentConfThreshold || clsId >= numClasses) continue;
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
        6, // legacy nms=True [1,300,6] 폴백용 (현행 자산은 dense 33ch)
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
