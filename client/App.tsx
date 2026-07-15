import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { View, StyleSheet, Platform, StatusBar } from "react-native";
import { setAudioModeAsync } from "expo-audio";
import * as ExpoSplashScreen from "expo-splash-screen";

import { CameraView } from "./src/components/CameraView";
import { LoadingScreen } from "./src/components/LoadingScreen";
import { audioEngine } from "./src/services/audioEngine";

void ExpoSplashScreen.preventAutoHideAsync();

// CameraView가 아직 별도의 "준비 완료" 콜백을 제공하지 않아 고정 시간으로 처리한다.
const MIN_LOADING_DURATION_MS = 1800;

// 앱 시작 시 1회 재생하는 온보딩 안내 문구. 문구 확정은 담당자 영역(SKILLS.md 협업 규칙)이며,
// 실제 STT 트리거 흐름(길댕아 wake-word -> 길찾아줘/물어볼게, server/stt/stt_to_llm_bridge.py)과
// 정확히 일치해야 한다. 2026-07-10 정정: 옛 단일 트리거("네비게이션 켜줘") 안내였던 것을
// 현재의 2단계 흐름으로 갱신.
const ONBOARDING_MESSAGE =
  "길댕아 저는 여러분의 보행을 돕는 길댕이입니다. 화면을 누르고 '길댕아'라고 부르신 뒤, '길찾아줘'라고 하시면 목적지까지 안내해 드리고, '물어볼게'라고 하시면 궁금하신 걸 답해드립니다.";

export default function App() {
  // Fast Refresh로 이 컴포넌트가 다시 마운트돼도 같은 세션에서 온보딩 안내가 중복
  // 재생되지 않도록 막는다(카메라/반사 구동을 지연시키지 않기 위해 짧게 1회만 재생).
  const onboardingPlayedRef = useRef(false);
  const splashHiddenRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);

  useLayoutEffect(() => {
    if (splashHiddenRef.current) {
      return;
    }
    splashHiddenRef.current = true;
    void ExpoSplashScreen.hideAsync();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), MIN_LOADING_DURATION_MS);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    void setAudioModeAsync({
      allowsRecording: true,
      playsInSilentMode: true,
      shouldPlayInBackground: false,
      interruptionMode: "mixWithOthers",
    }).then(() => {
      console.log("[App] 최상단 오디오 세션 선제 설정 완료 (Silent Override)");
      if (!onboardingPlayedRef.current) {
        onboardingPlayedRef.current = true;
        setTimeout(() => {
          audioEngine.speakFallback(ONBOARDING_MESSAGE);
        }, 600);
      }
    }).catch((err) => {
      console.error("[App] 최상단 오디오 세션 선제 설정 실패:", err);
    });
  }, []);

  return (
    <View style={styles.container}>
      {isLoading ? <LoadingScreen /> : <CameraView />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: Platform.OS === "android" ? StatusBar.currentHeight : 0,
    backgroundColor: "#0A0D10",
  },
});
