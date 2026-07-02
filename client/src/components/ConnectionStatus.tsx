/**
 * WebSocket 연결 상태 시각화 컴포넌트.
 * 접근성 accessibilityLabel로 상태를 음성 전달.
 */

import { StyleSheet, Text, View } from "react-native";

import type { WSStatus } from "../types/detection";

interface ConnectionStatusProps {
  status: WSStatus;
}

const STATUS_COLORS: Record<WSStatus, string> = {
  connecting: "#F59E0B",
  connected: "#10B981",
  disconnected: "#EF4444",
  fallback: "#6B7280",
};

const STATUS_LABELS: Record<WSStatus, string> = {
  connecting: "연결 중",
  connected: "연결됨",
  disconnected: "연결 끊김",
  fallback: "폴백 모드",
};

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const color = STATUS_COLORS[status];
  const label = STATUS_LABELS[status];

  return (
    <View
      style={[styles.container, { backgroundColor: color }]}
      accessibilityLabel={`연결 상태: ${label}`}
    >
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    alignSelf: "flex-start",
  },
  text: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
});
