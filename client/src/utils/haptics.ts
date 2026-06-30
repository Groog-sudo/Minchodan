/**
 * 햅틱 및 접근성 알림 래퍼 (7단계 준비 stub).
 * 7단계 반사/인지 음성 재생 시 본격 활용.
 */

import { Alert } from "react-native";

import * as Haptics from "expo-haptics";

export function triggerHaptic(
  type: "light" | "medium" | "heavy" = "medium",
): void {
  try {
    const style =
      type === "light"
        ? Haptics.ImpactFeedbackStyle.Light
        : type === "heavy"
          ? Haptics.ImpactFeedbackStyle.Heavy
          : Haptics.ImpactFeedbackStyle.Medium;
    Haptics.impactAsync(style);
  } catch (err) {
    console.error("[Haptics] 햅틱 오류:", err);
  }
}

export function announce(message: string): void {
  Alert.alert("", message);
}
