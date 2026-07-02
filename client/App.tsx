/**
 * Minchodan 앱 엔트리 포인트.
 * 카메라 캡처 + WebSocket 프레임 전송 (1+2단계).
 */

import { SafeAreaView, StyleSheet } from "react-native";

import { CameraView } from "./src/components/CameraView";

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <CameraView />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000000",
  },
});
