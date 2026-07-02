import { useCallback, useEffect, useRef, useState } from "react";
import {
  loadTensorflowModel,
  type TensorflowModel,
} from "react-native-fast-tflite";

import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";

// segmentation.tflite (segbest.pt 변환) 노면 클래스 (4종)
const SEG_CLASS_NAMES = [
  "sidewalk_normal",
  "caution",
  "roadway",
  "braille_normal",
];

// object_detection.tflite (COCO 80종) 중 보행 회피 의미 보유 클래스만 명시.
// 인덱스는 COCO 표준 순서.
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

// 노면 위험(주의/차도) 클래스 인덱스 (segmentation)
const SEG_HAZARD = new Set<number>([1, 2]); // caution, roadway

// 보행 충돌 위험 COCO 클래스 인덱스 (person, bicycle, car, motorcycle, bus, truck, skateboard)
const DET_HAZARD = new Set<number>([0, 1, 2, 3, 5, 7, 36]);

const FRAME_SIZE = 640;
const NUM_BOXES = 300; // Ultralytics NMS 출력 max_det
const CONF_THRESHOLD = 0.35;
const PROXIMITY_Y = FRAME_SIZE * 0.85; // 하단 15% 진입 임계치

export interface OnDeviceDetectionResult {
  model: "segmentation" | "object_detection";
  className: string;
  confidence: number;
  bbox: { x: number; y: number; w: number; h: number };
}

/**
 * 온디바이스 듀얼 비전 추론 훅.
 * segmentation.tflite + object_detection.tflite 두 모델을 동시에 로드하여
 * 단일 프레임(CHW float32)에 대해 추론하고 결과를 머지한다.
 * 위험 클래스가 하단 근접 영역에 진입하면 Reflex Gate를 발동해 비프음/햅틱을 즉시 가동.
 */
export function useOnDeviceDetection() {
  const segModelRef = useRef<TensorflowModel | null>(null);
  const detModelRef = useRef<TensorflowModel | null>(null);
  const [segLoaded, setSegLoaded] = useState(false);
  const [detLoaded, setDetLoaded] = useState(false);
  const isModelsLoaded = segLoaded && detLoaded;

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        console.log("[OnDevice] segmentation.tflite 로딩...");
        const seg = await loadTensorflowModel(
          require("../../assets/models/yolo26n/segmentation.tflite"),
          []
        );
        if (cancelled) return;
        segModelRef.current = seg;
        setSegLoaded(true);
        console.log("[OnDevice] segmentation 로드 완료");
      } catch (err) {
        console.error("[OnDevice] segmentation 로드 실패:", err);
      }
      try {
        console.log("[OnDevice] object_detection.tflite 로딩...");
        const det = await loadTensorflowModel(
          require("../../assets/models/yolo26n/object_detection.tflite"),
          []
        );
        if (cancelled) return;
        detModelRef.current = det;
        setDetLoaded(true);
        console.log("[OnDevice] object_detection 로드 완료");
      } catch (err) {
        console.error("[OnDevice] object_detection 로드 실패:", err);
      }
    }
    init();

    return () => {
      cancelled = true;
      if (segModelRef.current) {
        try {
          segModelRef.current.dispose();
        } catch {
          // dispose 미지원 가능, 무시
        }
        segModelRef.current = null;
      }
      if (detModelRef.current) {
        try {
          detModelRef.current.dispose();
        } catch {
          // noop
        }
        detModelRef.current = null;
      }
    };
  }, []);

  const runModel = useCallback(
    async (
      model: TensorflowModel | null,
      attrsPerBox: number,
      numClasses: number,
      names: readonly string[],
      label: OnDeviceDetectionResult["model"],
      frame: Float32Array,
    ): Promise<OnDeviceDetectionResult[]> => {
      if (!model) return [];
      try {
        const outputs = await model.run([frame.buffer as ArrayBuffer]);
        const out = new Float32Array(outputs[0]);
        const results: OnDeviceDetectionResult[] = [];
        for (let i = 0; i < NUM_BOXES; i++) {
          const off = i * attrsPerBox;
          const x1 = out[off];
          const y1 = out[off + 1];
          const x2 = out[off + 2];
          const y2 = out[off + 3];
          const score = out[off + 4];
          const cls = Math.round(out[off + 5]);
          if (score < CONF_THRESHOLD || cls < 0 || cls >= numClasses) {
            continue;
          }
          results.push({
            model: label,
            className: names[cls] ?? `cls_${cls}`,
            confidence: score,
            bbox: { x: x1, y: y1, w: x2 - x1, h: y2 - y1 },
          });
        }
        return results.sort((a, b) => b.confidence - a.confidence).slice(0, 10);
      } catch (err) {
        console.error(`[OnDevice] ${label} 추론 오류:`, err);
        return [];
      }
    },
    [],
  );

  /**
   * 단일 프레임(CHW float32)에 대해 두 모델 추론 후 머지 + Reflex Gate 발동.
   */
  const detectFrame = useCallback(
    async (
      frame: Float32Array,
    ): Promise<{ seg: OnDeviceDetectionResult[]; det: OnDeviceDetectionResult[] }> => {
      const seg = await runModel(
        segModelRef.current,
        38,
        SEG_CLASS_NAMES.length,
        SEG_CLASS_NAMES,
        "segmentation",
        frame,
      );
      const det = await runModel(
        detModelRef.current,
        6,
        COCO_CLASS_NAMES.length,
        COCO_CLASS_NAMES,
        "object_detection",
        frame,
      );

      // 위험 클래스 + 하단 근접 박스 중 최상위 1개 선정
      let highest: OnDeviceDetectionResult | null = null;
      const all = [...seg, ...det];
      for (const d of all) {
        const isSegHazard =
          d.model === "segmentation" &&
          SEG_HAZARD.has(SEG_CLASS_NAMES.indexOf(d.className));
        const isDetHazard =
          d.model === "object_detection" &&
          DET_HAZARD.has(COCO_CLASS_NAMES.indexOf(d.className));
        if (!isSegHazard && !isDetHazard) continue;
        const bottomY = d.bbox.y + d.bbox.h;
        if (bottomY >= PROXIMITY_Y) {
          highest = d;
          break;
        }
      }

      if (highest) {
        const b = highest.bbox;
        const centerX = b.x + b.w / 2;
        const panning = Math.max(-1, Math.min(1, (centerX / FRAME_SIZE) * 2 - 1));
        const bottomY = b.y + b.h;
        const ratio = Math.max(
          0,
          Math.min(1, (bottomY - PROXIMITY_Y) / (FRAME_SIZE - PROXIMITY_Y)),
        );
        const distance = 1.5 - ratio * 1.1;

        let beepInterval = 250;
        let hapticPattern = "double";
        if (distance <= 0.5) {
          beepInterval = 0;
          hapticPattern = "continuous";
        } else if (distance <= 1.0) {
          beepInterval = 100;
          hapticPattern = "continuous";
        }

        console.log(
          `[OnDevice Reflex] ${highest.model}/${highest.className} 거리=${distance.toFixed(2)}m 패닝=${panning.toFixed(2)}`,
        );
        audioEngine.playBeep(panning, beepInterval);
        hapticEngine.trigger(hapticPattern);
      } else {
        audioEngine.stopBeep();
        hapticEngine.stopContinuous();
      }

      return { seg, det };
    },
    [runModel],
  );

  return { isModelsLoaded, segLoaded, detLoaded, detectFrame };
}
