import { useEffect, useRef } from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { setAudioModeAsync } from "expo-audio";

import { CameraView } from "./src/components/CameraView";
import { audioEngine } from "./src/services/audioEngine";

// 앱 시작 시 1회 재생하는 온보딩 안내 문구. 문구 확정은 담당자 영역(SKILLS.md 협업 규칙)이며,
// 실제 STT 트리거 흐름(길댕아 wake-word -> 길찾아줘/물어볼게, server/stt/stt_to_llm_bridge.py)과
// 정확히 일치해야 한다. 2026-07-10 정정: 옛 단일 트리거("네비게이션 켜줘") 안내였던 것을
// 현재의 2단계 흐름으로 갱신.
const ONBOARDING_MESSAGE =
  "길댕아~ 저는 여러분의 보행을 돕는 길댕이입니다. 화면을 누르고 '길댕아'라고 부르신 뒤, '길찾아줘'라고 하시면 목적지까지 안내해 드리고, '물어볼게'라고 하시면 궁금하신 걸 답해드립니다.";

export default function App() {
  // Fast Refresh로 이 컴포넌트가 다시 마운트돼도 같은 세션에서 온보딩 안내가 중복
  // 재생되지 않도록 막는다(카메라/반사 구동을 지연시키지 않기 위해 짧게 1회만 재생).
  const onboardingPlayedRef = useRef(false);

  useEffect(() => {
    // 앱 기동 최상단에서 무음 모드 무시를 활성화하는 오디오 세션 선제 설정 (카메라 선점 우회)
    // [2026-07-09 실측 수정] interruptionMode를 audioEngine.ensureSession()과 다르게
    // "duckOthers"로 설정했었다. 두 setAudioModeAsync 호출 모두 await되지 않아 순서가
    // 보장되지 않으므로, 첫 안내 음성 재생 도중 세션 모드가 두 값 사이에서 뒤바뀌며
    // 하드웨어 레벨 순간 드롭아웃(음절 손실)을 유발할 수 있다는 의심이 있어 값을
    // audioEngine과 동일한 "mixWithOthers"로 통일한다.
    // [2026-07-10 정정] allowsRecording을 false로 두면 이 useEffect가 audioEngine.ensureSession()의
    // allowsRecording:true 설정보다 먼저(앱 마운트 시점) 실행되어 세션을 false로 덮어써,
    // STT useAudioRecorder().record()가 항상 RecordingDisabledException으로 실패했다
    // (실기기 실측 확인). audioEngine.ts와 동일하게 true로 맞춘다.
    void setAudioModeAsync({
      allowsRecording: true,
      playsInSilentMode: true,
      shouldPlayInBackground: false,
      interruptionMode: "mixWithOthers",
    }).then(() => {
      console.log("[App] 최상단 오디오 세션 선제 설정 완료 (Silent Override)");
      if (!onboardingPlayedRef.current) {
        onboardingPlayedRef.current = true;
        audioEngine.speakFallback(ONBOARDING_MESSAGE);
      }
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
