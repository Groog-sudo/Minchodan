/**
 * ADPF 발열 헤드룸 조회 브릿지 (2026-07-29, 핸드오프 §5.8).
 *
 * Android: ThermalBridgeModule(PowerManager.getThermalHeadroom / getCurrentThermalStatus).
 * iOS: 대응 브릿지 없음(ANE 경로는 §5.8과 같은 스로틀링이 실측되지 않았다). null을 돌려
 *      호출부가 발열 제어를 통째로 비활성화하게 한다.
 */

import { NativeModules, Platform } from "react-native";

interface ThermalBridgeNativeModule {
  getThermalState(forecastSeconds: number): Promise<{
    headroom: number | null;
    status: number | null;
    reason?: string;
  }>;
}

export interface ThermalState {
  /** 1.0이 스로틀링 임계. null이면 이 단말에서 조회 불가. */
  headroom: number | null;
  /** PowerManager.THERMAL_STATUS_*. §5.8 실측상 신뢰도가 낮아 진단용으로만 쓴다. */
  status: number | null;
  reason?: string;
}

function getModule(): ThermalBridgeNativeModule | null {
  if (Platform.OS !== "android") return null;
  return (NativeModules.ThermalBridgeModule as ThermalBridgeNativeModule) ?? null;
}

/** 브릿지 자체가 없는 환경(iOS, 구버전 앱)에서는 폴링을 걸 필요조차 없다. */
export function isThermalMonitoringSupported(): boolean {
  return getModule() !== null;
}

/**
 * @param forecastSeconds 예보 구간(초). 기본 10초 뒤를 본다 - 플랫폼이 헤드룸 갱신을
 *   최소 10초 간격으로 제한하므로 폴링 주기와 맞춘다.
 */
export async function readThermalState(
  forecastSeconds: number = 10,
): Promise<ThermalState | null> {
  const mod = getModule();
  if (!mod?.getThermalState) return null;
  try {
    const state = await mod.getThermalState(forecastSeconds);
    if (!state) return null;
    const headroom =
      typeof state.headroom === "number" && Number.isFinite(state.headroom)
        ? state.headroom
        : null;
    const status = typeof state.status === "number" ? state.status : null;
    return { headroom, status, reason: state.reason };
  } catch (err) {
    console.warn("[Thermal] 헤드룸 조회 실패:", err);
    return null;
  }
}
