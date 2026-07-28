import { NativeModules } from "react-native";
import { LocalDetector } from "./localDetector";
import { TFLiteDetector } from "./tfliteDetector";
import { DualDetectionResult, SceneClassification } from "./types";
import { audioEngine } from "../services/audioEngine";

const { TFLiteInferenceBridge, SceneClassifyBridgeModule } = NativeModules;

/**
 * iOS CoreMLDetector(localDetectorSelect.ios.ts)의 Android 대응.
 *
 * 2026-07-28 신설. 기존 Android 경로는 JS TFLiteDetector를 직접 썼고, 그 입력 계약이
 * requiresFloat32=true라서 프레임마다 JS에서 JPEG 디코드 + 640x640x3 Float32Array
 * 생성을 수행했다. Xiaomi 12 실측에서 이 한 번이 JS 스레드를 약 900ms 점유해
 * 캡처·WS 송신·콘솔 Live Feed가 전부 약 1.05fps에 묶였다(목표 8fps=125ms).
 *
 * 네이티브 TFLiteInferenceBridge(Kotlin)가 base64를 직접 디코드·추론하므로
 * requiresFloat32=false가 되고 JS 전처리 비용이 0이 된다. iOS와 동일한 구조다.
 * 네이티브 모듈이 없거나(구버전 APK) 로드에 실패하면 기존 JS TFLiteDetector로
 * 자동 폴백해 동작 자체는 유지한다.
 */
class NativeTFLiteDetector implements LocalDetector {
  isLoaded = false;
  segLoaded = false;
  detLoaded = false;
  detShapeLog = "";

  private fallback: TFLiteDetector | null = null;
  /** detectFrameCached가 NO_FRAME 외 사유로 실패하면 이후 base64 경로로 고정한다. */
  private cachedPathUnavailable = false;

  /** 네이티브 경로에서는 JS float32 전처리가 불필요. 폴백 시에만 true로 되돌아간다. */
  get requiresFloat32(): boolean {
    return this.fallback !== null;
  }

  async load(): Promise<boolean> {
    if (!TFLiteInferenceBridge?.loadModels) {
      console.warn(
        "[NativeTFLiteDetector] TFLiteInferenceBridge 네이티브 모듈 미발견, JS TFLite 폴백",
      );
      return await this.loadFallback();
    }

    try {
      console.log("[NativeTFLiteDetector] 네이티브 TFLite 모델 적재 시도...");
      const result = await TFLiteInferenceBridge.loadModels();
      const detOk = !!result?.det;
      const segOk = !!result?.seg;

      if (!detOk) {
        console.warn("[NativeTFLiteDetector] det 인터프리터 생성 실패, JS TFLite 폴백");
        return await this.loadFallback();
      }

      this.isLoaded = true;
      this.detLoaded = true;
      this.segLoaded = segOk;
      this.detShapeLog = result?.engine ?? "TFLite Native";
      console.log(
        `[NativeTFLiteDetector] det=native / seg=${segOk ? "native" : "미로드"} (${this.detShapeLog})`,
      );
      return true;
    } catch (e) {
      console.error("[NativeTFLiteDetector] 네이티브 로드 에러, JS TFLite 폴백:", e);
      return await this.loadFallback();
    }
  }

  private async loadFallback(): Promise<boolean> {
    this.fallback = new TFLiteDetector();
    const ok = await this.fallback.load();
    this.isLoaded = this.fallback.isLoaded;
    this.segLoaded = this.fallback.segLoaded;
    this.detLoaded = this.fallback.detLoaded;
    this.detShapeLog = `${this.fallback.detShapeLog} (JS Fallback)`;
    return ok;
  }

  async detect(frame: Float32Array, base64: string | null): Promise<DualDetectionResult> {
    if (this.fallback) {
      return await this.fallback.detect(frame, base64);
    }
    if (!this.isLoaded) return { seg: [], det: [] };
    if (!base64) {
      console.warn("[NativeTFLiteDetector] 네이티브 경로는 base64 입력이 필요합니다.");
      return { seg: [], det: [] };
    }

    try {
      // 씬 분류(ML Kit)는 별도 네이티브 모듈이므로 추론과 병렬로 돌린다.
      const [bridgeResult, scene] = await Promise.all([
        this.runNativeDetect(base64),
        this.classifyScene(base64),
      ]);

      if (bridgeResult?.benchmark && !audioEngine.isGuidePlaying) {
        const b = bridgeResult.benchmark;
        console.log(
          // 2026-07-28: det_run(GPU delegate 실행) / det_decode(JVM dense head + NMS) 분리.
          // 기존 prep/det/seg/total 토큰 순서는 핸드오프 §측정 명령의 grep 패턴이 의존하므로
          // 그대로 두고 뒤에 덧붙인다.
          `[TFLiteNativeBench] prep=${b.prep_ms?.toFixed(2)}ms det=${b.det_ms?.toFixed(2)}ms seg=${b.seg_ms?.toFixed(2)}ms total=${b.total_ms?.toFixed(2)}ms det_run=${b.det_run_ms?.toFixed(2)}ms det_decode=${b.det_decode_ms?.toFixed(2)}ms seg_run=${b.seg_run_ms?.toFixed(2)}ms seg_decode=${b.seg_decode_ms?.toFixed(2)}ms`,
        );
      }

      return {
        det: bridgeResult?.det ?? [],
        seg: bridgeResult?.seg ?? [],
        scene,
        // 2026-07-28: 누락 시 CameraView가 reportInferenceLatency(0)을 호출해
        // 동적 FPS 과부하 보호가 무력화된다.
        benchmark: bridgeResult?.benchmark,
      };
    } catch (e) {
      console.error("[NativeTFLiteDetector] 추론 중 에러:", e);
      return { seg: [], det: [] };
    }
  }

  /**
   * 2026-07-28: base64를 다시 넘기지 않고 네이티브 프레임 캐시(ReflexFrameCache)를 직접
   * 소비하는 detectFrameCached를 우선 사용한다. 프레임 프로세서가 이미 만들어 둔
   * 640x640 픽셀을 그대로 쓰므로 Base64.decode + BitmapFactory.decode + getPixels 왕복이
   * 사라진다. 캐시가 비어 있으면(NO_FRAME) 기존 base64 경로로 한 번 폴백한다.
   */
  private async runNativeDetect(base64: string): Promise<any> {
    if (TFLiteInferenceBridge?.detectFrameCached && !this.cachedPathUnavailable) {
      try {
        return await TFLiteInferenceBridge.detectFrameCached();
      } catch (err: any) {
        if (err?.code !== "NO_FRAME") {
          console.warn(
            "[NativeTFLiteDetector] detectFrameCached 실패, base64 경로로 폴백:",
            err?.message ?? err,
          );
          this.cachedPathUnavailable = true;
        }
      }
    }
    return await TFLiteInferenceBridge.detectFrame(base64);
  }

  /** iOS bridgeResult.scene 대응. 실패 시 undefined → CameraView는 허용적(실외) 폴백. */
  private async classifyScene(base64: string): Promise<SceneClassification | undefined> {
    if (!SceneClassifyBridgeModule?.classifyScene) return undefined;
    try {
      const scene = (await SceneClassifyBridgeModule.classifyScene(
        base64,
      )) as SceneClassification;
      if (scene?.topLabels?.length && !audioEngine.isGuidePlaying) {
        const labels = scene.topLabels
          .map((l) => `${l.identifier}(${l.confidence.toFixed(2)})`)
          .join(", ");
        console.log(`[SceneClassify][Android] indoor=${scene.isLikelyIndoor} ${labels}`);
      }
      return scene;
    } catch (err) {
      console.warn("[NativeTFLiteDetector] SceneClassify 실패, 씬 게이트 스킵:", err);
      return undefined;
    }
  }

  dispose(): void {
    this.isLoaded = false;
    if (this.fallback) {
      this.fallback.dispose();
      this.fallback = null;
    }
  }
}

export function createLocalDetector(): LocalDetector {
  return new NativeTFLiteDetector();
}
