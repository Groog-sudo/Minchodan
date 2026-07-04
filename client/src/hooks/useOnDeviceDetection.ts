import { useCallback, useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import {
  loadTensorflowModel,
  type TensorflowModel,
  type TensorflowModelDelegate,
} from "react-native-fast-tflite";

import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";

// 플랫폼별 하드웨어 가속 delegate: iOS=CoreML(ANE), Android=NNAPI(NPU/GPU)
// 크로스플랫폼 공유 코드 유지하면서 양쪽 최적화 동시 적용.
// CoreML은 Podfile의 $EnableCoreMLDelegate=true 필요, 미설정 시 자동 CPU 폴백.
// 주: 재변환된 LiteRT 모델에서 CoreML 호환성 검증 전까지 CPU 기본 동작.
const ACCELERATION_DELEGATES: TensorflowModelDelegate[] = Platform.select({
  ios: [],        // TODO: CoreML 호환성 검증 후 ["core-ml"]로 활성화
  android: ["nnapi"],
  default: [],
}) ?? [];

/**
 * 모델 로드: 가속 delegate 시도 후 실패 시 CPU([])로 자동 폴백.
 * delegate가 빌드에 포함되지 않은 환경(CoreML 미활성 등)에서도 동작 보장.
 */
async function loadModelWithFallback(
  source: number,
  label: string,
): Promise<TensorflowModel> {
  try {
    return await loadTensorflowModel(source, ACCELERATION_DELEGATES);
  } catch (err) {
    console.warn(`[OnDevice] ${label} delegate 로드 실패, CPU 폴백:`, err);
    return await loadTensorflowModel(source, []);
  }
}

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
const CONF_THRESHOLD = 0.25; // 신뢰도 임계치 (NMS 출력은 이미 0~1 정규화 confidence)
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
  const [detShapeLog, setDetShapeLog] = useState<string>("");
  const isModelsLoaded = segLoaded && detLoaded;

  useEffect(() => {
    let cancelled = false;

    // 이중 로드 방지 가드레일: 이미 로드되어 있으면 재로드 차단
    if (segModelRef.current && detModelRef.current) {
      console.log("[OnDevice] 모델 이미 로드됨, 상태 복원");
      setSegLoaded(true);
      setDetLoaded(true);
      return;
    }

    async function init() {
      try {
        console.log("[OnDevice] segmentation.tflite 로딩...");
        const seg = await loadModelWithFallback(
          require("../../assets/models/yolo26n/segmentation.tflite"),
          "segmentation",
        );
        if (cancelled) return;
        segModelRef.current = seg;
        setSegLoaded(true);
        console.log("[OnDevice] segmentation 로드 완료 inputs:", JSON.stringify(seg.inputs), "outputs:", JSON.stringify(seg.outputs));
      } catch (err) {
        console.error("[OnDevice] segmentation 로드 실패:", err);
      }
      try {
        console.log("[OnDevice] object_detection.tflite 로딩...");
        const det = await loadModelWithFallback(
          require("../../assets/models/yolo26n/object_detection.tflite"),
          "object_detection",
        );
        if (cancelled) return;
        detModelRef.current = det;
        // object_detection outputs shape 추출 (디버그 오버레이 표시용)
        const outShape = det.outputs?.[0]?.shape;
        const shapeStr = outShape ? `[${outShape.join(",")}]` : "(알 수 없음)";
        setDetShapeLog(shapeStr);
        console.log("[OnDevice] object_detection 로드 완료 outputs shape:", shapeStr);
        setDetLoaded(true);
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

  /**
   * NMS 내장 포맷 디코더.
   * 두 모델 모두 Ultralytics NMS export: [1, max_det, attrsPerBox]
   *   - object_detection: [1, 300, 6]  → [x1, y1, x2, y2, score, cls]
   *   - segmentation:     [1, 300, 38] → [x1, y1, x2, y2, score, cls, mask*32]
   * 좌표는 0~1 정규화 (640x640 기준).
   */
  const runModel = useCallback(
    async (
      model: TensorflowModel | null,
      attrsPerBox: number,
      numClasses: number,
      names: readonly string[],
      label: OnDeviceDetectionResult["model"],
      buffer: ArrayBuffer,
    ): Promise<OnDeviceDetectionResult[]> => {
      if (!model) return [];
      try {
        const outputs = await model.run([buffer]);
        // 출력 텐서가 여러 개일 수 있음(segmentation: NMS[1,300,38] + mask[1,32,160,160]).
        // attrsPerBox(38 또는 6)로 나누어 떨어지는(NMS 결과) 텐서를 선택.
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

        const results: OnDeviceDetectionResult[] = [];
        let maxScore = 0;
        for (let i = 0; i < numBoxes; i++) {
          const off = i * attrsPerBox;
          // 좌표 정규화: NMS 출력이 x2<x1, y2<y1 로 뒤집힐 수 있어 min/max 보정
          const x1 = Math.min(out[off], out[off + 2]);
          const y1 = Math.min(out[off + 1], out[off + 3]);
          const x2 = Math.max(out[off], out[off + 2]);
          const y2 = Math.max(out[off + 1], out[off + 3]);
          const score = out[off + 4]; // NMS 출력: 이미 0~1 confidence
          const cls = Math.round(Math.abs(out[off + 5]));

          if (score > maxScore) maxScore = score;
          if (score < CONF_THRESHOLD || cls >= numClasses) continue;
          // 음수/영역 박스 필터 (w 또는 h가 0 이하인 가짜 박스 제거)
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
        const top = results.slice(0, 5).map((r) => `${r.className}:${r.confidence.toFixed(2)}`).join(", ");
        console.log(`[OnDevice] ${label} 결과: ${results.length}개 탐지 (maxScore=${maxScore.toFixed(3)}) ${top}`);
        return results.sort((a, b) => b.confidence - a.confidence);
      } catch (err: any) {
        console.error(`[OnDevice] ${label} 추론 오류: message=${err?.message}, stack=${err?.stack}`);
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
      // seg, det를 독립 try-catch로 분리: 한쪽 실패해도 다른쪽 실행 보장
      let seg: OnDeviceDetectionResult[] = [];
      let det: OnDeviceDetectionResult[] = [];

      // TypedArray 레벨에서 복제하여 Nitro C++ 브릿지의 메모리 포인터 획득 신뢰성 보장
      const segFrame = frame.slice(0);

      try {
        seg = await runModel(
          segModelRef.current,
          38,
          SEG_CLASS_NAMES.length,
          SEG_CLASS_NAMES,
          "segmentation",
          segFrame.buffer as ArrayBuffer,
        );
      } catch (e) {
        console.error("[OnDevice] seg 추론 오류:", e);
      }
      try {
        det = await runModel(
          detModelRef.current,
          6,
          COCO_CLASS_NAMES.length,
          COCO_CLASS_NAMES,
          "object_detection",
          frame.buffer as ArrayBuffer,
        );
      } catch (e) {
        console.error("[OnDevice] det 추론 오류:", e);
      }

      // 위험 클래스 탐지 시 즉시 Reflex Gate 발동 (근접 필터 없음 - 디버그 모드)
      let highest: OnDeviceDetectionResult | null = null;
      const all = [...det, ...seg]; // det 우선
      for (const d of all) {
        const isDetHazard =
          d.model === "object_detection" &&
          DET_HAZARD.has(COCO_CLASS_NAMES.indexOf(d.className));
        const isSegHazard =
          d.model === "segmentation" &&
          SEG_HAZARD.has(SEG_CLASS_NAMES.indexOf(d.className));
        if (isDetHazard || isSegHazard) {
          highest = d;
          console.log(`[Reflex] 위험 탐지: ${d.model}/${d.className} conf=${d.confidence.toFixed(3)} bbox=${JSON.stringify(d.bbox)}`);
          break;
        }
      }
      if (all.length > 0) {
        console.log(`[Reflex] 전체 탐지: ${all.map(d => `${d.className}(${d.confidence.toFixed(2)})`).join(", ")}`);
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

  return { isModelsLoaded, segLoaded, detLoaded, detShapeLog, detectFrame };
}
