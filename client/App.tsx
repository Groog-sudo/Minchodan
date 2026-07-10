import { useEffect } from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { setAudioModeAsync } from "expo-audio";

import { CameraView } from "./src/components/CameraView";

export default function App() {
  useEffect(() => {
    // 앱 기동 최상단에서 무음 모드 무시를 활성화하는 오디오 세션 선제 설정 (카메라 선점 우회)
    // [2026-07-09 실측 수정] interruptionMode를 audioEngine.ensureSession()과 다르게
    // "duckOthers"로 설정했었다. 두 setAudioModeAsync 호출 모두 await되지 않아 순서가
    // 보장되지 않으므로, 첫 안내 음성 재생 도중 세션 모드가 두 값 사이에서 뒤바뀌며
    // 하드웨어 레벨 순간 드롭아웃(음절 손실)을 유발할 수 있다는 의심이 있어 값을
    // audioEngine과 동일한 "mixWithOthers"로 통일한다.
    void setAudioModeAsync({
      allowsRecording: false,
      playsInSilentMode: true,
      shouldPlayInBackground: false,
      interruptionMode: "mixWithOthers",
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
