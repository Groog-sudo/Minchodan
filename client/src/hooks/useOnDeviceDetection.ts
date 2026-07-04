import { useCallback, useEffect, useRef, useState } from "react";
import { createLocalDetector } from "../inference/localDetector";
import { DetectionResult } from "../inference/types";
import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";

// 보행 충돌 위험 COCO 클래스 인덱스 명세 (기존 TFLite 명세와 정합)
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

const SEG_CLASS_NAMES = [
  "sidewalk_normal",
  "caution",
  "roadway",
  "braille_normal",
];

// 위험 주의/차도/장애물 클래스 인덱스 (기존 로직 보존)
const SEG_HAZARD = new Set<number>([1, 2]); // caution, roadway
const DET_HAZARD = new Set<number>([0, 1, 2, 3, 5, 7, 36]); // person, bicycle, car, motorcycle, bus, truck, skateboard

const FRAME_SIZE = 640;
const PROXIMITY_Y = FRAME_SIZE * 0.85; // 하단 15% 진입 임계치

export type OnDeviceDetectionResult = DetectionResult;

/**
 * 온디바이스 듀얼 비전 추론 훅 (CoreML 및 ANE 가속 대응 리팩토링 버전).
 * 기존 햅틱 및 비프음 오케스트레이션 로직을 완전 보존하며,
 * OS별 최적화된 로컬 추론 엔진(CoreML / TFLite)을 선택적으로 실행합니다.
 */
export function useOnDeviceDetection() {
  const [segLoaded, setSegLoaded] = useState(false);
  const [detLoaded, setDetLoaded] = useState(false);
  const [detShapeLog, setDetShapeLog] = useState<string>("CoreML Mode");
  const detectorRef = useRef<any>(null);
  const isModelsLoaded = segLoaded && detLoaded;

  useEffect(() => {
    // 플랫폼별 최적화된 Detector 인스턴스 획득 (iOS=CoreML 우선, Android=TFLite)
    const detector = createLocalDetector();
    detectorRef.current = detector;

    async function init() {
      console.log("[OnDevice] 로컬 추론 엔진 기동 시도...");
      const success = await detector.load();
      if (success) {
        setSegLoaded(detector.segLoaded);
        setDetLoaded(detector.detLoaded);
        setDetShapeLog(detector.detShapeLog);
      } else {
        console.warn("[OnDevice] 로컬 추론 엔진 로드 실패");
      }
    }
    init();

    return () => {
      if (detectorRef.current) {
        detectorRef.current.dispose();
        detectorRef.current = null;
      }
    };
  }, []);

  /**
   * 단일 프레임 추론 후 위험 판정 및 물리 햅틱/비프음 즉각 제어 (Reflex Gate)
   */
  const detectFrame = useCallback(
    async (
      frame: Float32Array,
      base64: string | null = null
    ): Promise<{ seg: OnDeviceDetectionResult[]; det: OnDeviceDetectionResult[] }> => {
      let seg: OnDeviceDetectionResult[] = [];
      let det: OnDeviceDetectionResult[] = [];

      if (!detectorRef.current || !detectorRef.current.isLoaded) {
        return { seg, det };
      }

      try {
        const result = await detectorRef.current.detect(frame, base64);
        seg = result.seg;
        det = result.det;
      } catch (e) {
        console.error("[OnDevice] 로컬 추론 실행 중 오류:", e);
      }

      // ====================================================================
      // [기존 Beep음 & 햅틱(hapticEngine) 발동 코드 100% 동일하게 보존 및 가동]
      // ====================================================================
      let highest: OnDeviceDetectionResult | null = null;
      const all = [...det, ...seg]; // det 우선순위 적용
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
          Math.min(1, (bottomY - PROXIMITY_Y) / (FRAME_SIZE - PROXIMITY_Y))
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
          `[OnDevice Reflex] ${highest.model}/${highest.className} 거리=${distance.toFixed(2)}m 패닝=${panning.toFixed(2)}`
        );
        audioEngine.playBeep(panning, beepInterval);
        hapticEngine.trigger(hapticPattern);
      } else {
        audioEngine.stopBeep();
        hapticEngine.stopContinuous();
      }

      return { seg, det };
    },
    []
  );

  return { isModelsLoaded, segLoaded, detLoaded, detShapeLog, detectFrame };
}
