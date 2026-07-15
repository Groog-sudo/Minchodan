/**
 * LiDAR 실거리 프로브 래퍼 (2026-07-11 프로토타입, Mitos 로드맵 §2 거리 휴리스틱 대체 검증).
 * iOS 전용(builtInLiDARDepthCamera, iPhone 12 Pro 이상 Pro 계열). Android·비Pro 기기·
 * 구버전 네이티브 빌드에서는 null을 반환해 호출측이 기능을 숨기게 한다.
 *
 * 프로토타입 제약: 네이티브 프로브가 자체 캡처 세션으로 후면 카메라를 점유하므로
 * vision-camera와 동시 사용 불가. CameraView가 거리 측정 모드에서 카메라를 내리고
 * (isActive=false) 프로브를 켜는 배타 전환으로 사용한다.
 */

import { NativeModules, Platform } from "react-native";

export interface DepthSample {
  x: number;
  y: number;
  /** 실거리(m). 해당 지점의 유효 심도 샘플이 없으면 null. */
  meters: number | null;
  /** 보정 전 카메라 광축(z축) 기준 원본 depth(m). */
  axialMeters?: number | null;
  /** 해당 지점 주변에서 실제로 사용된 유효 depth 픽셀 수. */
  sampleCount?: number;
}

export interface DepthProbeResult {
  ready: boolean;
  width?: number;
  height?: number;
  /** "absolute"면 LiDAR 실측(미터 단위 신뢰 가능), "relative"면 시차 기반 상대값. */
  accuracy?: "absolute" | "relative";
  quality?: "high" | "low";
  filtered?: boolean;
  /** cameraCalibrationData 기반 렌즈·광선 거리 보정 적용 여부. */
  calibrated?: boolean;
  /** 같은 AVCapture 세션에서 depth와 동기화해 만든 1:1 계측 프리뷰. */
  previewUri?: string;
  previewWidth?: number;
  previewHeight?: number;
  synchronizedAt?: number;
  samples: DepthSample[];
}

export interface DepthBoxDistance {
  index: number;
  meters: number | null;
  sampleCount: number;
}

export interface DepthBoxDistanceResult {
  ready: boolean;
  width?: number;
  height?: number;
  accuracy?: "absolute" | "relative";
  quality?: "high" | "low";
  filtered?: boolean;
  calibrated?: boolean;
  distances: DepthBoxDistance[];
}

interface DepthProbeBridgeModule {
  startProbe(): Promise<{ running: boolean }>;
  stopProbe(): Promise<{ running: boolean }>;
  probe(points: { x: number; y: number }[]): Promise<DepthProbeResult>;
  probeBoxes?(boxes: { x: number; y: number; w: number; h: number }[]): Promise<DepthBoxDistanceResult>;
}

function getModule(): DepthProbeBridgeModule | null {
  if (Platform.OS !== "ios") return null;
  return (NativeModules.DepthProbeBridge as DepthProbeBridgeModule) ?? null;
}

/** Android·비 LiDAR iPhone에서는 false. UI에서 거리측정 버튼을 숨길 때 사용. */
export function isDepthProbeSupported(): boolean {
  return getModule() != null;
}

/** 프로브 세션 시작. LiDAR 미탑재/카메라 점유 등 실패 시 에러 메시지 반환. */
export async function startDepthProbe(): Promise<{ ok: boolean; error?: string }> {
  const mod = getModule();
  if (!mod) {
    if (Platform.OS === "android") {
      return {
        ok: false,
        error: "거리측정(LiDAR)은 iPhone Pro 전용입니다. Android에서는 사용할 수 없습니다.",
      };
    }
    return { ok: false, error: "미지원 플랫폼 또는 구버전 네이티브 빌드(iOS LiDAR 필요)" };
  }
  try {
    const result = await mod.startProbe();
    return { ok: result.running };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export async function stopDepthProbe(): Promise<void> {
  const mod = getModule();
  if (!mod) return;
  try {
    await mod.stopProbe();
  } catch (err) {
    console.warn("[DepthProbe] 중지 실패:", err);
  }
}

/** 정규화 좌표(portrait 기준 0~1) 목록의 실거리를 샘플링한다. */
export async function probeDepth(
  points: { x: number; y: number }[],
): Promise<DepthProbeResult | null> {
  const mod = getModule();
  if (!mod) return null;
  try {
    return await mod.probe(points);
  } catch (err) {
    console.warn("[DepthProbe] 샘플링 실패:", err);
    return null;
  }
}

/** 640x640 bbox 목록의 중앙 50% 영역에서 LiDAR 거리(25퍼센타일)를 샘플링한다. */
async function probeDepthBoxes(
  boxes: { x: number; y: number; w: number; h: number }[],
): Promise<DepthBoxDistanceResult | null> {
  const mod = getModule();
  if (!mod?.probeBoxes) return null;
  try {
    return await mod.probeBoxes(boxes);
  } catch (err) {
    console.warn("[DepthProbe] bbox 샘플링 실패:", err);
    return null;
  }
}
