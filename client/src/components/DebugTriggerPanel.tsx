/**
 * 디버그 트리거 패널 (개발 빌드 전용, CameraView에서 __DEV__일 때만 마운트).
 * 실제 탐지 없이도 비프음/햅틱/위험등급을 수동 발화하여 청취·햅틱을 즉시 검증.
 * docs/reflex_audio_specification.md 3.1 위험 등급 테이블 준수.
 */

import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { audioEngine } from "../services/audioEngine";
import { hapticEngine } from "../services/hapticEngine";

interface RiskLevel {
  label: string;
  interval: number;
  pattern: string;
  color: string;
}

const RISK_LEVELS: RiskLevel[] = [
  { label: "주의 Low (500ms)", interval: 500, pattern: "short", color: "#F59E0B" },
  { label: "경고 Mid (250ms)", interval: 250, pattern: "double", color: "#F97316" },
  { label: "위험 High (100ms)", interval: 100, pattern: "continuous", color: "#EF4444" },
  { label: "정지 Critical (0ms)", interval: 0, pattern: "continuous", color: "#991B1B" },
];

const PAN_PRESETS = [
  { label: "L -1.0", v: -1 },
  { label: "L -0.5", v: -0.5 },
  { label: "C 0", v: 0 },
  { label: "R +0.5", v: 0.5 },
  { label: "R +1.0", v: 1 },
];

/**
 * [하드 코딩 부분 - 핵심] 문자 TTS 실험 샘플.
 * 서버 `debug_router._DEFAULT_SMS_TEXT` / speak-to-device 기본값과 동일 계약을 유지한다.
 *
 * 면접 팁: 서버 푸시(`/api/v1/debug/speak-to-device`)는 guide+WAV(인지 계약),
 * 이 버튼은 단말 expo-speech `speakFallback`만 사용해 네트워크 없이도 UI 청취 검증이 가능하다.
 */
const SAMPLE_SMS_TEXT =
  "새 문자가 도착했습니다. 엄마에게서. 오늘 저녁 몇 시에 오실 건가요?";

export function DebugTriggerPanel() {
  const [panning, setPanning] = useState(0);
  const [lastFired, setLastFired] = useState<string>("-");

  const fire = (lvl: RiskLevel) => {
    audioEngine.playBeep(panning, lvl.interval);
    hapticEngine.trigger(lvl.pattern);
    setLastFired(`${lvl.label} @ pan ${panning.toFixed(2)}`);
  };

  /** [바이브 코딩 부분] 단말 TTS로 샘플 문자 즉시 재생(서버 불필요). */
  const speakSmsSample = () => {
    audioEngine.speakFallback(SAMPLE_SMS_TEXT);
    setLastFired("문자 TTS(단말)");
  };

  return (
    // 2026-07-10: 화면 전체 STT 터치 레이어(CameraView) 도입에 맞춰, 이 패널의 라벨/여백
    // 영역은 터치를 그대로 통과시키고 실제 버튼만 반응하도록 box-none 처리한다.
    <View style={styles.container} pointerEvents="box-none">
      <Text style={styles.title}>DEBUG 트리거 패널</Text>

      <Text style={styles.label}>패닝: {panning.toFixed(2)}</Text>
      <View style={styles.row} pointerEvents="box-none">
        {PAN_PRESETS.map((p) => (
          <Pressable
            key={p.label}
            style={[styles.btn, panning === p.v && styles.btnActive]}
            onPress={() => setPanning(p.v)}
          >
            <Text style={styles.btnText}>{p.label}</Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.row} pointerEvents="box-none">
        {RISK_LEVELS.map((lvl) => (
          <Pressable
            key={lvl.label}
            style={[styles.btn, { backgroundColor: lvl.color }]}
            onPress={() => fire(lvl)}
          >
            <Text style={styles.btnText}>{lvl.label}</Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.row} pointerEvents="box-none">
        <Pressable
          style={[styles.btn, styles.smsBtn]}
          onPress={speakSmsSample}
          accessibilityLabel="문자 TTS 샘플 읽기"
        >
          <Text style={styles.btnText}>문자 TTS 읽기</Text>
        </Pressable>
        <Pressable
          style={[styles.btn, styles.stopBtn]}
          onPress={() => {
            audioEngine.stopBeep();
            hapticEngine.stopContinuous();
            audioEngine.stopGuideAudio();
            setLastFired("정지");
          }}
        >
          <Text style={styles.btnText}>정지</Text>
        </Pressable>
      </View>

      <Text style={styles.last}>최근: {lastFired}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "rgba(10, 13, 16, 0.9)",
    borderTopWidth: 1,
    borderColor: "#222A30",
    padding: 8,
  },
  title: {
    color: "#39FF14",
    fontSize: 12,
    fontWeight: "700",
    fontFamily: "monospace",
    marginBottom: 4,
  },
  label: {
    color: "#9DA7BA",
    fontSize: 11,
    fontFamily: "monospace",
  },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 4,
  },
  btn: {
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 6,
    margin: 2,
    backgroundColor: "#12161A",
    borderWidth: 1,
    borderColor: "#222A30",
  },
  btnActive: {
    backgroundColor: "rgba(0, 210, 255, 0.2)",
    borderColor: "#00D2FF",
  },
  smsBtn: {
    backgroundColor: "rgba(0, 210, 255, 0.18)",
    borderColor: "#00D2FF",
  },
  stopBtn: {
    backgroundColor: "rgba(255, 51, 51, 0.18)",
    borderColor: "#FF3333",
  },
  btnText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontFamily: "monospace",
  },
  last: {
    color: "#39FF14",
    fontSize: 10,
    fontFamily: "monospace",
    marginTop: 4,
  },
});
