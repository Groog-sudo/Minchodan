import { NativeModules } from "react-native";
import { LocalDetector } from "./localDetector";
import { TFLiteDetector } from "./tfliteDetector";
import { DualDetectionResult } from "./types";
import { audioEngine } from "../services/audioEngine";

const { CoreMLInferenceBridge } = NativeModules;

class CoreMLDetector implements LocalDetector {
  isLoaded = false;
  segLoaded = false;
  detLoaded = false;
  detShapeLog = "CoreML CPU Engine";

  // TFLite는 seg 전용 폴백으로 사용 (segmentation.mlmodelc 번들 전까지)
  private segFallback: TFLiteDetector | null = null;
  // CoreML 완전 로드 실패 시 det+seg 모두 TFLite로 폴백
  private fullFallback: TFLiteDetector | null = null;
  private isFullFallbackMode = false;

  /**
   * 입력 계약: CoreML 정상 모드(det+seg 모두 CoreML)는 base64만 사용하므로 false.
   * 단, seg 전용 TFLite 폴백 또는 완전 TFLite 폴백이 활성화되면 float32가 필요(true).
   * load() 결과에 따라 동적으로 결정된다.
   */
  get requiresFloat32(): boolean {
    return this.isFullFallbackMode || this.segFallback !== null;
  }

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
      console.log("[CoreMLDetector] CoreML 모델 적재 시도...");
      const result = await CoreMLInferenceBridge.loadModels();

      // 결과가 Dictionary 형태 { det: boolean, seg: boolean } 로 리턴되거나, 구버전에서는 boolean일 수 있음
      const isDetLoaded = typeof result === "object" ? !!result.det : !!result;
      const isSegLoaded = typeof result === "object" ? !!result.seg : false;

      if (isDetLoaded) {
        this.isLoaded = true;
        this.detLoaded = true;
        this.detShapeLog = "CoreML CPU Engine";

        if (isSegLoaded) {
          this.segLoaded = true;
          this.segFallback = null;
          // 2026-07-07 실기기 재검증 결과 GPU(computeUnits=.cpuAndGPU)에서 크래시가
          // 재현되어 네이티브(CoreMLInferenceBridge.swift)가 CPU 전용으로 동작 중이므로,
          // 실제로는 ANE/GPU 가속이 아닌 CPU 추론임을 로그에 정확히 반영한다.
          console.log("[CoreMLDetector] det=CoreML(CPU) / seg=CoreML(CPU) 기동 완료");
        } else {
          // segmentation.mlmodelc가 번들에 없으면 seg 전용 TFLite 로드
          console.log("[CoreMLDetector] seg 전용 TFLite 폴백 적재 (segmentation.mlmodelc 미번들)");
          this.segFallback = new TFLiteDetector();
          const segOk = await this.segFallback.load();
          // seg 모델만 로드되면 충분 (det는 CoreML 경로 사용)
          this.segLoaded = segOk && this.segFallback.segLoaded;
          console.log("[CoreMLDetector] det=CoreML(CPU) / seg=TFLite 하이브리드 기동 완료");
        }
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

    // 하이브리드 모드 또는 풀 CoreML 모드
    try {
      // seg가 TFLiteFallback 모드일 경우에만 TFLite 추론 실행
      const segPromise = this.segFallback
        ? this.segFallback.detect(frame, base64)
        : Promise.resolve({ seg: [], det: [] } as DualDetectionResult);

      // det 및 CoreML 세그멘테이션 (base64 사용)
      let coremlResults: DualDetectionResult = { seg: [], det: [] };
      if (base64) {
        const bridgeResult = await CoreMLInferenceBridge.detectFrame(base64);
        // 벤치마크 로그 출력 (Swift 네이티브 측정값)
        if (bridgeResult.benchmark && !audioEngine.isGuidePlaying) {
          const b = bridgeResult.benchmark;
          console.log(`[CoreMLBenchmark] det=${b.det_ms?.toFixed(2)}ms seg=${b.seg_ms?.toFixed(2)}ms scene=${b.scene_ms?.toFixed(2)}ms total=${b.total_ms?.toFixed(2)}ms`);
        }
        // 2026-07-13 추가: 온디바이스 보도 이탈 판정(단일 프레임, CoreMLInferenceBridge.swift
        // computeSidewalkDeparture) 로그. 아직 어떤 알림/햅틱에도 연결하지 않은 관측 전용 값 -
        // 실기기에서 세그멘테이션 경계 근처 단일 기준점이 얼마나 자주 뒤집히는지(노이즈)
        // 확인하기 위한 것이다. 검증 후 서버처럼 히스테리시스를 얹어 실제 기능으로 승격할지 결정한다.
        if (bridgeResult.surfaceDeparture !== undefined && !audioEngine.isGuidePlaying) {
          console.log(`[SurfaceDeparture][OnDevice] isDeparting=${bridgeResult.surfaceDeparture}`);
        }
        // docs/design/indoor_fp_mitigation_design.md §4.4: isLikelyIndoor 게이트 판정에
        // 더해, top-5 identifier는 계속 로그로 남겨 향후 키워드 집합 보강에 활용한다.
        // (가이드 음성 재생 중에는 JS 브릿지 로그 전송이 오디오 콜백과 경합해 억제한다)
        if (bridgeResult.scene?.topLabels?.length && !audioEngine.isGuidePlaying) {
          const labels = bridgeResult.scene.topLabels
            .map((l: { identifier: string; confidence: number }) => `${l.identifier}(${l.confidence.toFixed(2)})`)
            .join(", ");
          console.log(`[SceneClassify] ${labels}`);
        }
        coremlResults = bridgeResult as DualDetectionResult;
      } else {
        console.warn("[CoreMLDetector] CoreML은 base64 이미지 입력을 필요로 합니다.");
      }

      // 2026-07-28: benchmark를 함께 넘긴다. 누락 시 CameraView.runDetectionResult가
      // reportInferenceLatency(0)을 호출해 동적 FPS 과부하 보호가 무력화된다(Android 동일).
      if (this.segFallback) {
        const segResults = await segPromise;
        return {
          det: coremlResults.det,
          seg: segResults.seg,
          scene: coremlResults.scene,
          benchmark: coremlResults.benchmark,
        };
      } else {
        // 완전 CoreML 가속 모드
        return {
          det: coremlResults.det,
          seg: coremlResults.seg || [],
          scene: coremlResults.scene,
          benchmark: coremlResults.benchmark,
        };
      }
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
