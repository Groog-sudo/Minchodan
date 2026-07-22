import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { View, StyleSheet, Platform, StatusBar, AppState, LogBox } from "react-native";
import { setAudioModeAsync } from "expo-audio";
import * as ExpoSplashScreen from "expo-splash-screen";

import { CameraView } from "./src/components/CameraView";
import { LoadingScreen } from "./src/components/LoadingScreen";
import { audioEngine } from "./src/services/audioEngine";

void ExpoSplashScreen.preventAutoHideAsync();

// 2026-07-18: 실기기 테스트 중 반복 확인된 무해한 경고들이 LogBox 알림 토스트를 계속
// 재노출시켜(각 console.warn/error마다 다시 뜸) 하단 버튼 dock을 가려 닫을 수 없게 만드는
// 문제가 있었다. 원인이 이미 파악되고 안전하게 처리되는(catch됨) 경고만 화이트리스트로
// 무시한다 - 새로운 유형의 경고는 계속 정상적으로 노출된다.
LogBox.ignoreLogs([
  "Packager status check returned unexpected result",
  "오디오 세션 전환 실패",
]);

// CameraView가 아직 별도의 "준비 완료" 콜백을 제공하지 않아 고정 시간으로 처리한다.
const MIN_LOADING_DURATION_MS = 1800;
// Metro/HMR 재연결로 App이 반복 마운트돼도 로딩 타이머가 리셋되지 않게 모듈 스코프로 고정.
// (재연결마다 1.8s가 다시 시작되면 Loading 화면에 영구 고착될 수 있다.)
let loadingEpochMs = 0;
let loadingCompleted = false;

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
  const [isLoading, setIsLoading] = useState(!loadingCompleted);

  useLayoutEffect(() => {
    if (splashHiddenRef.current) {
      return;
    }
    splashHiddenRef.current = true;
    void ExpoSplashScreen.hideAsync();
  }, []);

  useEffect(() => {
    if (loadingCompleted) {
      setIsLoading(false);
      return;
    }
    if (!loadingEpochMs) {
      loadingEpochMs = Date.now();
    }
    const remainingMs = Math.max(0, MIN_LOADING_DURATION_MS - (Date.now() - loadingEpochMs));
    const timer = setTimeout(() => {
      loadingCompleted = true;
      setIsLoading(false);
    }, remainingMs);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let onboardingTimer: ReturnType<typeof setTimeout> | null = null;

    void setAudioModeAsync({
      allowsRecording: true,
      playsInSilentMode: true,
      shouldPlayInBackground: false,
      interruptionMode: "mixWithOthers",
    })
      .then(() => {
        if (cancelled) return;
        console.log("[App] 최상단 오디오 세션 선제 설정 완료 (Silent Override)");
        if (!onboardingPlayedRef.current) {
          onboardingPlayedRef.current = true;
          onboardingTimer = setTimeout(() => {
            if (!cancelled) {
              audioEngine.speakFallback(ONBOARDING_MESSAGE);
            }
          }, 600);
          // cleanup이 setTimeout 할당 직전에 돌았을 수 있으므로 즉시 재확인한다.
          if (cancelled) {
            clearTimeout(onboardingTimer);
            onboardingTimer = null;
          }
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error("[App] 최상단 오디오 세션 선제 설정 실패:", err);
        }
      });

    return () => {
      cancelled = true;
      if (onboardingTimer) {
        clearTimeout(onboardingTimer);
      }
    };
  }, []);

  const [appState, setAppState] = useState(AppState.currentState);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextAppState) => {
      setAppState(nextAppState);
    });
    return () => subscription.remove();
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
