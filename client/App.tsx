import { useEffect } from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { setAudioModeAsync } from "expo-audio";

import { CameraView } from "./src/components/CameraView";

export default function App() {
  useEffect(() => {
    // 앱 기동 최상단에서 무음 모드 무시를 활성화하는 오디오 세션 선제 설정 (카메라 선점 우회)
    void setAudioModeAsync({
      allowsRecording: false,
      playsInSilentMode: true,
      shouldPlayInBackground: false,
      interruptionMode: "duckOthers",
    }).then(() => {
      console.log("[App] 최상단 오디오 세션 선제 설정 완료 (Silent Override)");
    }).catch((err) => {
      console.error("[App] 최상단 오디오 세션 선제 설정 실패:", err);
    });
  }, []);

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
