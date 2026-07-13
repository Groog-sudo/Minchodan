import { useEffect, useRef } from "react";
import { SafeAreaView, StyleSheet } from "react-native";
import { setAudioModeAsync } from "expo-audio";

import { CameraView } from "./src/components/CameraView";
import { audioEngine } from "./src/services/audioEngine";

// 앱 시작 시 1회 재생하는 온보딩 안내 문구. 문구 확정은 담당자 영역(SKILLS.md 협업 규칙)이며,
// 실제 STT 트리거 흐름(길댕아 wake-word -> 길찾아줘/물어볼게, server/stt/stt_to_llm_bridge.py)과
// 정확히 일치해야 한다. 2026-07-10 정정: 옛 단일 트리거("네비게이션 켜줘") 안내였던 것을
// 현재의 2단계 흐름으로 갱신.
// 2026-07-13 강화: 시각장애인 보행 편의성 기능(보호자 번호 저장/긴급전화) 사용법 안내 추가.
//   - 보호자 번호 음성 저장: "엄마 번호는 010-xxxx-xxxx 저장해줘" (RAG 영속)
//   - 긴급전화: "긴급전화" / "SOS" / "보호자한테 전화해줘" (guardian_phone 우선, 119 폴백)
const ONBOARDING_MESSAGE =
  "길댕이를 시작합니다. 화면을 누르고 '길댕아'라고 부르신 뒤, '길찾아줘'라고 하시면 목적지까지 안내해 드리고, '물어볼게'라고 하시면 궁금하신 걸 답해드립니다. 보호자 번호를 저장하려면 '엄마 번호는 010-0000-0000 저장해줘'처럼 말씀해 주세요. 긴급 상황이면 '긴급전화' 또는 'SOS'라고 외쳐 주세요.";

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
    // [2026-07-13 타이밍 보정] CameraView가 동시 마운트되며 카메라/오디오 세션을 선점해
    // 온보딩 음성이 무음으로 밀리는 현상을 회피하기 위해, 세션 설정 완료 후 600ms 대기
    // 뒤 온보딩을 재생한다(카메라 프리뷰/반사 비프가 오디오 세션을 안정화시킬 시간).
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
