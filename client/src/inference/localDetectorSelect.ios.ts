import { NativeModules } from "react-native";
import { LocalDetector } from "./localDetector";
import { TFLiteDetector } from "./tfliteDetector";
import { DualDetectionResult } from "./types";

const { CoreMLInferenceBridge } = NativeModules;

class CoreMLDetector implements LocalDetector {
  isLoaded = false;
  segLoaded = false;
  detLoaded = false;
  detShapeLog = "CoreML ANE Engine";

  // TFLite는 seg 전용 폴백으로 사용 (segmentation.mlmodelc 번들 전까지)
  private segFallback: TFLiteDetector | null = null;
  // CoreML 완전 로드 실패 시 det+seg 모두 TFLite로 폴백
  private fullFallback: TFLiteDetector | null = null;
  private isFullFallbackMode = false;

  async load(): Promise<boolean> {
    if (!CoreMLInferenceBridge) {
      console.warn("[CoreMLDetector] CoreMLInferenceBridge Native Module 미발견, TFLite 폴백 모드로 기동");
      this.isFullFallbackMode = true;
      this.fullFallback = new TFLiteDetector();
      const success = await this.fullFallback.load();
      this.syncStatusFrom(this.fullFallback, " (Fallback TFLite)");
      return success;
    }

    try {
      console.log("[CoreMLDetector] CoreML 모델 ANE 적재 시도...");
      const success = await CoreMLInferenceBridge.loadModels();
      if (success) {
        this.isLoaded = true;
        this.detLoaded = true;
        this.detShapeLog = "CoreML ANE Engine";

        // segmentation.mlmodelc가 번들에 없으면 seg 전용 TFLite 로드
        // (CoreMLInferenceBridge.loadModels 내부에서 seg 누락 시에도 resolve(true) 반환)
        console.log("[CoreMLDetector] seg 전용 TFLite 폴백 적재 (segmentation.mlmodelc 미번들)");
        this.segFallback = new TFLiteDetector();
        const segOk = await this.segFallback.load();
        // seg 모델만 로드되면 충분 (det는 CoreML 경로 사용)
        this.segLoaded = segOk && this.segFallback.segLoaded;
        console.log("[CoreMLDetector] det=CoreML ANE / seg=TFLite 하이브리드 기동 완료");
        return true;
      }
    } catch (e) {
      console.error("[CoreMLDetector] CoreML 로드 에러, TFLite 자동 폴백 실행:", e);
    }

    // CoreML 로드 실패 시 det+seg 모두 TFLite로 폴백
    this.isFullFallbackMode = true;
    this.fullFallback = new TFLiteDetector();
    const success = await this.fullFallback.load();
    this.syncStatusFrom(this.fullFallback, " (Fallback TFLite)");
    return success;
  }

  private syncStatusFrom(detector: TFLiteDetector, suffix: string): void {
    this.isLoaded = detector.isLoaded;
    this.segLoaded = detector.segLoaded;
    this.detLoaded = detector.detLoaded;
    this.detShapeLog = detector.detShapeLog + suffix;
  }

  async detect(frame: Float32Array, base64: string | null): Promise<DualDetectionResult> {
    if (!this.isLoaded) return { seg: [], det: [] };

    // 완전 폴백 모드: det+seg 모두 TFLite
    if (this.isFullFallbackMode && this.fullFallback) {
      return await this.fullFallback.detect(frame, base64);
    }

    // 하이브리드 모드: det=CoreML / seg=TFLite 병렬 수행
    try {
      // seg는 TFLite (frame buffer 사용)
      const segPromise = this.segFallback
        ? this.segFallback.detect(frame, base64)
        : Promise.resolve({ seg: [], det: [] } as DualDetectionResult);

      // det는 CoreML (base64 사용)
      let detResults: { seg: any[]; det: any[] } = { seg: [], det: [] };
      if (base64) {
        const coremlResult = await CoreMLInferenceBridge.detectFrame(base64);
        detResults = coremlResult as DualDetectionResult;
      } else {
        console.warn("[CoreMLDetector] CoreML은 base64 이미지 입력을 필요로 합니다.");
      }

      const segResults = await segPromise;
      return {
        det: detResults.det,
        seg: segResults.seg,
      };
    } catch (e) {
      console.error("[CoreMLDetector] 추론 중 에러 발생:", e);
      return { seg: [], det: [] };
    }
  }

  dispose() {
    this.isLoaded = false;
    if (this.segFallback) {
      this.segFallback.dispose();
      this.segFallback = null;
    }
    if (this.fullFallback) {
      this.fullFallback.dispose();
      this.fullFallback = null;
    }
  }
}

export function createLocalDetector(): LocalDetector {
  return new CoreMLDetector();
}
