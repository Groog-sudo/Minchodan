import { useCallback, useEffect, useRef, useState } from "react";
import { loadTensorflowModel, type TensorflowModel } from "react-native-fast-tflite";

import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";

// segbest.tflite 세그멘테이션 모델 규격 클래스 (4개)
const CLASS_NAMES = [
  "sidewalk_normal",
  "caution",
  "roadway",
  "braille_normal"
];

// 보행자에게 주의/위험을 알릴 클래스 목록
const HIGH_RISK_CLASSES = new Set(["caution", "roadway"]);

export interface OnDeviceDetectionResult {
  className: string;
  confidence: number;
  bbox: { x: number; y: number; w: number; h: number };
}

/**
 * 온디바이스 YOLO26n 세그멘테이션 TFLite 모델 실시간 추론 훅.
 * 네이티브 NPU/GPU를 활용해 서버 연결 없이 단말 내에서 즉시 노면 상태 및 위험을 탐지합니다.
 */
export function useOnDeviceDetection() {
  const modelRef = useRef<TensorflowModel | null>(null);
  const [isModelLoaded, setIsModelLoaded] = useState(false);

  // 1. 컴포넌트 마운트 시 세그멘테이션 TFLite 모델 탑재
  useEffect(() => {
    async function initModel() {
      try {
        console.log("[OnDevice] YOLO26n Segmentation TFLite 모델 로딩 시작...");
        // assets에서 빌드 시 포함된 tflite 모델 로드
        const model = await loadTensorflowModel(
          require("../../assets/models/yolo26n/segmentation.tflite")
        );
        modelRef.current = model;
        setIsModelLoaded(true);
        console.log("[OnDevice] YOLO26n Segmentation TFLite 모델 로드 성공!");
      } catch (err) {
        console.error("[OnDevice] TFLite 모델 로딩 실패:", err);
      }
    }
    initModel();

    return () => {
      if (modelRef.current) {
        modelRef.current.dispose();
        modelRef.current = null;
      }
    };
  }, []);

  /**
   * 단일 이미지 픽셀 어레이 버퍼(Float32Array, 640x640x3)를 받아 YOLO26n 추론 수행
   * @param rgbBuffer Float32Array 형식의 정규화된(0~1) 픽셀 버퍼
   */
  const detectFrame = useCallback(async (rgbBuffer: Float32Array): Promise<OnDeviceDetectionResult[]> => {
    if (!modelRef.current) {
      console.warn("[OnDevice] 추론 실패: 모델이 아직 로드되지 않았습니다.");
      return [];
    }

    try {
      // TFLite 동적 컴파일 연산 기동 (출력 텐서: [(1, 300, 38), (1, 32, 160, 160)])
      const output = await modelRef.current.run([rgbBuffer]);

      // 첫 번째 출력 텐서 (300개 박스 검출 정보) 파싱
      const outputData = output[0] as Float32Array;
      const numClasses = 4;
      const numBoxes = 300;
      const attrsPerBox = 38; // 4 (bbox) + 4 (classes) + 32 (masks)

      const detections: OnDeviceDetectionResult[] = [];
      const confidenceThreshold = 0.35;
      const proximityThresholdY = 640 * 0.85; // 하단 15% 진입 임계치 (y=544)

      for (let i = 0; i < numBoxes; i++) {
        const offset = i * attrsPerBox;
        const xc = outputData[offset + 0];
        const yc = outputData[offset + 1];
        const w = outputData[offset + 2];
        const h = outputData[offset + 3];

        // 4개 클래스 중 최대 확률값 및 인덱스 탐색
        let maxClassConf = 0;
        let maxClassId = -1;
        for (let c = 0; c < numClasses; c++) {
          const conf = outputData[offset + 4 + c];
          if (conf > maxClassConf) {
            maxClassConf = conf;
            maxClassId = c;
          }
        }

        // 신뢰도가 임계치를 초과할 때만 객체로 확정
        if (maxClassConf > confidenceThreshold && maxClassId !== -1) {
          const className = CLASS_NAMES[maxClassId];
          const x = xc - w / 2;
          const y = yc - h / 2;

          detections.push({
            className,
            confidence: maxClassConf,
            bbox: { x, y, w, h }
          });
        }
      }

      // 점수 기준 상위 필터링
      const sortedDetections = detections
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, 10);

      // 로컬 반사 게이트(Reflex Gate) 연산 가동 (caution / roadway 대상)
      let highestRiskDetection: OnDeviceDetectionResult | null = null;
      for (const det of sortedDetections) {
        if (HIGH_RISK_CLASSES.has(det.className)) {
          // 객체의 최하단 경계(y + h)가 프레임 하단 15% 임계치 아래로 내려왔는지 점검
          const bottomY = det.bbox.y + det.bbox.h;
          if (bottomY >= proximityThresholdY) {
            highestRiskDetection = det;
            break;
          }
        }
      }

      if (highestRiskDetection) {
        // 로컬 햅틱/비프음 즉각 피드백 발동 (서버 네트워크 지연 0ms)
        const bbox = highestRiskDetection.bbox;
        const centerX = bbox.x + bbox.w / 2;

        // 1. Panning 산출: -1.0(좌) ~ 1.0(우)
        const panning = (centerX / 640) * 2 - 1.0;

        // 2. Distance 산출 및 주기 매핑
        const bottomY = bbox.y + bbox.h;
        const ratio = (bottomY - proximityThresholdY) / (640 - proximityThresholdY);
        const distance = 1.5 - (Math.max(0, Math.min(1.0, ratio)) * 1.1);

        let beepInterval = 250;
        let hapticPattern = "double";

        if (distance <= 0.5) {
          beepInterval = 0;
          hapticPattern = "continuous";
        } else if (distance <= 1.0) {
          beepInterval = 100;
          hapticPattern = "continuous";
        }

        console.log(`[OnDevice Reflex] 객체 감지: ${highestRiskDetection.className}, 거리: ${distance.toFixed(2)}m, 방향: ${panning.toFixed(2)}`);
        audioEngine.playBeep(panning, beepInterval);
        hapticEngine.trigger(hapticPattern);
      } else {
        // 위험 요소가 없으면 비프음 정지
        audioEngine.stopBeep();
        hapticEngine.stopContinuous();
      }

      return sortedDetections;
    } catch (err) {
      console.error("[OnDevice] 추론 실패:", err);
      return [];
    }
  }, []);

  return { isModelLoaded, detectFrame };
}
