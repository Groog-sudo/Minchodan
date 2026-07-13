/**
 * iOS AVAudioSession 모드 전환 래퍼 (2026-07-11, Mitos 로드맵 우선순위 4: AEC 검증).
 * STT 녹음 구간에서 세션 모드를 voiceChat으로 전환하면 iOS VoiceProcessingIO의
 * AEC(에코 캔슬레이션)가 켜져, 녹음 중 스피커 출력(반사 비프, 신호음)이 마이크
 * 입력에서 상쇄된다. Android는 네이티브 구현 전이므로 no-op(null 반환)이다.
 */

import { NativeModules, Platform } from "react-native";

export interface AudioSessionInfo {
  category: string;
  mode: string;
  /** mode === voiceChat 여부. true면 iOS가 AEC(VoiceProcessingIO)를 활성화한 상태. */
  voiceProcessingActive: boolean;
  outputRoute: string;
}

interface AudioSessionBridgeModule {
  setVoiceProcessing(enabled: boolean): Promise<AudioSessionInfo>;
  getSessionInfo(): Promise<AudioSessionInfo>;
}

function getModule(): AudioSessionBridgeModule | null {
  if (Platform.OS === "ios") {
    return (NativeModules.AudioSessionBridge as AudioSessionBridgeModule) ?? null;
  }
  if (Platform.OS === "android") {
    return (NativeModules.AudioSessionBridgeModule as AudioSessionBridgeModule) ?? null;
  }
  return null;
}

/** voiceChat(AEC) 모드 전환. 실패/미지원 시 null 반환(호출측은 기존 동작 유지). */
export async function setVoiceProcessing(
  enabled: boolean,
): Promise<AudioSessionInfo | null> {
  const mod = getModule();
  if (!mod) return null;
  try {
    const result = await mod.setVoiceProcessing(enabled);
    if (Platform.OS === "android") {
      return {
        category: "playAndRecord",
        mode: enabled ? "voiceChat" : "normal",
        voiceProcessingActive: enabled,
        outputRoute: "speaker",
      };
    }
    return result;
  } catch (err) {
    console.warn(`[AudioSession] voiceChat 전환 실패(enabled=${enabled}):`, err);
    return null;
  }
}

/** 검증용 현재 세션 상태 조회. expo-audio가 모드를 덮었는지 확인하는 데 쓴다. */
export async function getSessionInfo(): Promise<AudioSessionInfo | null> {
  const mod = getModule();
  if (!mod) return null;
  try {
    const result = await mod.getSessionInfo();
    if (Platform.OS === "android") {
      const infoStr = typeof result === "string" ? result : "UNKNOWN";
      const isVoiceChat = infoStr.includes("COMMUNICATION");
      return {
        category: "playAndRecord",
        mode: isVoiceChat ? "voiceChat" : "normal",
        voiceProcessingActive: isVoiceChat,
        outputRoute: "speaker",
      };
    }
    return result;
  } catch {
    return null;
  }
}
