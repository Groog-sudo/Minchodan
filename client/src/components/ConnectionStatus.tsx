/**
 * WebSocket 연결 상태 시각화 컴포넌트.
 * 접근성 accessibilityLabel로 상태를 음성 전달.
 * 콘솔(console/src/components/StatusBadge.tsx)과 동일한 "톤 배지" 패턴
 * (저채도 배경 + 원색 텍스트 + 0.3 알파 테두리)을 공유한다.
 */

import { StyleSheet, Text, View } from "react-native";

import type { WSStatus } from "../types/detection";

interface ConnectionStatusProps {
  status: WSStatus;
}

interface StatusTone {
  background: string;
  text: string;
  border: string;
}

const STATUS_TONES: Record<WSStatus, StatusTone> = {
  connecting: { background: "rgba(249, 183, 0, 0.15)", text: "#F9B700", border: "rgba(249, 183, 0, 0.3)" },
  connected: { background: "rgba(57, 255, 20, 0.15)", text: "#39FF14", border: "rgba(57, 255, 20, 0.3)" },
  disconnected: { background: "rgba(255, 51, 51, 0.15)", text: "#FF3333", border: "rgba(255, 51, 51, 0.3)" },
  fallback: { background: "rgba(107, 117, 144, 0.15)", text: "#94A3B8", border: "rgba(107, 117, 144, 0.3)" },
};

const STATUS_LABELS: Record<WSStatus, string> = {
  connecting: "연결 중",
  connected: "연결됨",
  disconnected: "연결 끊김",
  fallback: "폴백 모드",
};

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const tone = STATUS_TONES[status];
  const label = STATUS_LABELS[status];

  return (
    <View
      style={[styles.container, { backgroundColor: tone.background, borderColor: tone.border }]}
      accessibilityLabel={`연결 상태: ${label}`}
    >
      <Text style={[styles.text, { color: tone.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
    borderWidth: 1,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: 14,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
});
