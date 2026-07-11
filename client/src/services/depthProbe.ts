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
}

export interface DepthProbeResult {
  ready: boolean;
  width?: number;
  height?: number;
  /** "absolute"면 LiDAR 실측(미터 단위 신뢰 가능), "relative"면 시차 기반 상대값. */
  accuracy?: "absolute" | "relative";
  filtered?: boolean;
  samples: DepthSample[];
}

interface DepthProbeBridgeModule {
  startProbe(): Promise<{ running: boolean }>;
  stopProbe(): Promise<{ running: boolean }>;
  probe(points: { x: number; y: number }[]): Promise<DepthProbeResult>;
}

function getModule(): DepthProbeBridgeModule | null {
  if (Platform.OS !== "ios") return null;
  return (NativeModules.DepthProbeBridge as DepthProbeBridgeModule) ?? null;
}

/** 프로브 세션 시작. LiDAR 미탑재/카메라 점유 등 실패 시 에러 메시지 반환. */
export async function startDepthProbe(): Promise<{ ok: boolean; error?: string }> {
  const mod = getModule();
  if (!mod) return { ok: false, error: "미지원 플랫폼 또는 구버전 네이티브 빌드" };
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
