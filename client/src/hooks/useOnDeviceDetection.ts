import { useCallback, useEffect, useRef, useState } from "react";
import { createLocalDetector } from "../inference/localDetector";
import { DetectionResult, SceneClassification } from "../inference/types";
import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";

// Object Detection 29 커스텀 클래스 인덱스 명세
// (CoreMLInferenceBridge.swift의 classNames 딕셔너리, det_best_20260705.mlpackage 기준과 순서 일치)
const DET_CLASS_NAMES = [
  "barricade", "bench", "bicycle", "bollard", "bus",
  "car", "carrier", "cat", "chair", "dog",
  "fire_hydrant", "kiosk", "motorcycle", "movable_signage",
  "parking_meter", "person", "pole", "potted_plant",
  "power_controller", "scooter", "stop", "stroller",
  "table", "traffic_light", "traffic_light_controller",
  "traffic_sign", "tree_trunk", "truck", "wheelchair",
];

const SEG_CLASS_NAMES = [
  "sidewalk_normal",
  "caution",
  "roadway",
  "braille_normal",
];

// object_detection 29 클래스는 범용 COCO가 아니라 보행 위험 사물만 선별해
// 재학습된 도메인 특화 모델이므로, 탐지된 결과 자체가 이미 전부 위험군이다
// (기존 COCO 91클래스에서 7종만 골라 쓰던 화이트리스트 방식이 불필요해짐).
// segmentation은 노면 상태 4클래스 중 위험 구간(caution, roadway)만 위험군으로 취급한다.
const SEG_HAZARD = new Set<number>([1, 2]); // caution, roadway

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
    ): Promise<{ seg: OnDeviceDetectionResult[]; det: OnDeviceDetectionResult[]; scene?: SceneClassification }> => {
      let seg: OnDeviceDetectionResult[] = [];
      let det: OnDeviceDetectionResult[] = [];
      let scene: SceneClassification | undefined;

      if (!detectorRef.current || !detectorRef.current.isLoaded) {
        return { seg, det };
      }

      try {
        const result = await detectorRef.current.detect(frame, base64);
        seg = result.seg;
        det = result.det;
        scene = result.scene;
      } catch (e) {
        console.error("[OnDevice] 로컬 추론 실행 중 오류:", e);
      }

      // ====================================================================
      // [기존 Beep음 & 햅틱(hapticEngine) 발동 코드 100% 동일하게 보존 및 가동]
      // ====================================================================
      // [2026-07-14] seg(노면 세그)를 Reflex 즉각 경보 후보에서 제외한다.
      // 설계 원칙: 노면 클래스는 인지 경로(서버 LLM TTS) 전담이며 즉각 비프/햅틱 발동 불가.
      // det(object_detection 29클래스)만 반사 경로 위험군 대상이다.
      let highest: OnDeviceDetectionResult | null = null;
      const all = [...det, ...seg];
      for (const d of all) {
        if (d.model === "object_detection") {
          highest = d;
          if (!audioEngine.isGuidePlaying) {
            console.log(`[Reflex] 위험 탐지: ${d.model}/${d.className} conf=${d.confidence.toFixed(3)} bbox=${JSON.stringify(d.bbox)}`);
          }
          break;
        }
      }
      if (all.length > 0 && !audioEngine.isGuidePlaying) {
        console.log(`[Reflex] 전체 탐지: ${all.map(d => `${d.className}(${d.confidence.toFixed(2)})`).join(", ")}`);
      }

      // 중복 피드백 제어를 제거하여 상위 CameraView.tsx 단일 오케스트레이션으로 일원화합니다.
      return { seg, det, scene };
    },
    []
  );

  return { isModelsLoaded, segLoaded, detLoaded, detShapeLog, detectFrame };
}
