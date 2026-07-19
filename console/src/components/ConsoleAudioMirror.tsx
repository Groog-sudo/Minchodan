// 2026-07-19: 관제 콘솔 오디오 미러 컴포넌트.
// 서버가 단말에 보내는 것과 동일한 guide 오디오(WAV)와 반사 비프 클립을
// 콘솔에서도 재생하고, 햅틱 패턴을 시각 펄스로 표현한다.
//
// - 인지 가이드 오디오: useLiveFeed.guideAudioEvent.audio_url(Blob URL)을
//   <audio>로 재생. 단말과 동일 WAV 원본이므로 "동일"에 가장 근접.
// - 반사 비프: reflexAlertEvent.clip 파일명으로 console/public/reflex_clips/
//   에 복사된 동일 wav를 재생. 단말 번들과 동일 파일이므로 "동일".
// - 햅틱: 진동은 소리가 아니므로 청각 재현 불가. 강도/지속/패턴을 펄스
//   인디케이터로 시각화하되 "시각 근사"임을 라벨에 명시.
//
// 컴포넌트는 단말 오디오 재생과 충돌하지 않도록 볼륨을 기본 0.7로 낮추고,
// 사용자가 음소거 토글로 끌 수 있다(운영자가 데모 중일 때 선택).

import { useEffect, useRef, useState } from "react";
import type { ConsoleGuideAudioEvent, ConsoleReflexAlertEvent } from "../api/useLiveFeed";

interface ConsoleAudioMirrorProps {
  guideAudioEvent: ConsoleGuideAudioEvent | null;
  reflexAlertEvent: ConsoleReflexAlertEvent | null;
}

const REFLEX_CLIP_BASE = "/reflex_clips/";

export function ConsoleAudioMirror({ guideAudioEvent, reflexAlertEvent }: ConsoleAudioMirrorProps) {
  const [muted, setMuted] = useState(false);
  const [hapticPulseKey, setHapticPulseKey] = useState(0);
  const guideAudioRef = useRef<HTMLAudioElement | null>(null);
  const reflexAudioRef = useRef<HTMLAudioElement | null>(null);
  const hapticTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 인지 가이드 오디오 재생. audio_url이 바뀔 때마다 새로 로드해 재생.
  useEffect(() => {
    if (!guideAudioEvent?.audio_url) return;
    const audio = guideAudioRef.current;
    if (!audio) return;
    audio.src = guideAudioEvent.audio_url;
    audio.volume = muted ? 0 : 0.7;
    // 재생은 브라우저 자동재생 정책에 따라 사용자 제스처가 필요할 수 있다.
    // 대시보드 진입 후 사용자가 한 번이라도 상호작용한 이후엔 허용되는 경우가 많다.
    audio.play().catch((err) => {
      // 자동재생 차단 시 사용자에게 안내. 콘솔은 운영자용이므로 클릭 한 번이면 해제.
      console.warn("[ConsoleAudioMirror] guide 재생 차단(자동재생 정책):", err);
    });
  }, [guideAudioEvent?.audio_url, muted]);

  // 반사 비프 재생. clip 파일명으로 public/reflex_clips/에서 로드.
  useEffect(() => {
    if (!reflexAlertEvent?.clip) return;
    const audio = reflexAudioRef.current;
    if (!audio) return;
    audio.src = `${REFLEX_CLIP_BASE}${reflexAlertEvent.clip}`;
    audio.volume = muted ? 0 : 0.8;
    audio.play().catch((err) => {
      console.warn("[ConsoleAudioMirror] reflex 비프 재생 차단:", err);
    });

    // 햅틱 시각화 펄스 트리거. 진동은 소리가 아니므로 청각 재현은 불가하고,
    // 강도/지속을 펄스 애니메이션으로만 표현한다.
    setHapticPulseKey((k) => k + 1);
    const haptic = reflexAlertEvent.haptic_pattern;
    const durationMs = haptic?.duration_ms ?? 300;
    if (hapticTimerRef.current) clearTimeout(hapticTimerRef.current);
    hapticTimerRef.current = setTimeout(() => setHapticPulseKey(0), durationMs);
  }, [reflexAlertEvent?.event_id, reflexAlertEvent?.clip, muted]);

  useEffect(() => {
    return () => {
      if (hapticTimerRef.current) clearTimeout(hapticTimerRef.current);
    };
  }, []);

  const haptic = reflexAlertEvent?.haptic_pattern;
  const hapticIntensity = haptic?.intensity ?? "medium";
  const hapticPattern = haptic?.pattern ?? "single";
  const hapticDurationMs = haptic?.duration_ms ?? 300;
  // 강도별 펄스 색상/크기 매핑(시각 근사).
  const intensityStyle: Record<string, { color: string; scale: number }> = {
    heavy: { color: "#F87171", scale: 1.4 },
    medium: { color: "#FBBF24", scale: 1.15 },
    light: { color: "#60A5FA", scale: 0.95 },
  };
  const style = intensityStyle[hapticIntensity] ?? intensityStyle.medium;

  return (
    <section className="panel panel-audio-mirror" style={{ marginBottom: "0.5rem" }}>
      <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 className="panel-title">단말 오디오 미러</h3>
        <button
          type="button"
          onClick={() => setMuted((m) => !m)}
          style={{
            fontSize: "0.75rem",
            padding: "4px 10px",
            borderRadius: "4px",
            background: muted ? "rgba(239,68, 68, 0.2)" : "rgba(16, 185, 129, 0.2)",
            color: muted ? "#F87171" : "#34D399",
            border: "none",
            cursor: "pointer",
          }}
        >
          {muted ? "음소거됨" : "재생 중"}
        </button>
      </div>
      <div className="panel-content" style={{ display: "flex", gap: "1rem", alignItems: "stretch", flexWrap: "wrap" }}>
        {/* 인지 가이드 */}
        <div style={{ flex: "1 1 240px", minWidth: 240 }}>
          <h4 style={{ margin: "0 0 0.25rem 0", color: "#60A5FA", fontSize: "0.85rem" }}>인지 가이드</h4>
          {guideAudioEvent ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB" }}>
              <div style={{ marginBottom: 4 }}>
                <strong>{guideAudioEvent.guidance_text || "(빈 안내문)"}</strong>
              </div>
              <div style={{ fontSize: "0.75rem", color: "#9CA3AF" }}>
                {guideAudioEvent.duration_ms.toFixed(0)}ms · {guideAudioEvent.source ?? "cognitive"} ·{" "}
                {guideAudioEvent.device_id}
              </div>
              <audio ref={guideAudioRef} controls style={{ width: "100%", marginTop: 6 }} />
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>대기 중…</p>
          )}
        </div>

        {/* 반사 비프 + 햅틱 시각화 */}
        <div style={{ flex: "1 1 240px", minWidth: 240 }}>
          <h4 style={{ margin: "0 0 0.25rem 0", color: "#F59E0B", fontSize: "0.85rem" }}>반사 알림</h4>
          {reflexAlertEvent ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB" }}>
              <div style={{ marginBottom: 4 }}>
                <strong>{reflexAlertEvent.alert_id}</strong>
                {reflexAlertEvent.class_name ? ` · ${reflexAlertEvent.class_name}` : ""}
                {reflexAlertEvent.direction ? ` · ${reflexAlertEvent.direction}` : ""}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#9CA3AF", marginBottom: 6 }}>
                clip: {reflexAlertEvent.clip ?? "(없음)"} · band: {reflexAlertEvent.distance_band ?? "-"}
              </div>
              <audio ref={reflexAudioRef} controls style={{ width: "100%" }} />
              {/* 햅틱 시각화: 진동은 소리가 아니므로 청각 재현이 아닌 시각 근사. */}
              <div
                style={{
                  marginTop: 8,
                  padding: 8,
                  borderRadius: 6,
                  background: "rgba(255,255,255,0.04)",
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <div
                  key={hapticPulseKey}
                  style={{
                    width: 24 * style.scale,
                    height: 24 * style.scale,
                    borderRadius: "50%",
                    background: style.color,
                    opacity: hapticPulseKey ? 0.9 : 0.3,
                    transition: "opacity 120ms ease-out, transform 120ms ease-out",
                    transform: hapticPulseKey ? `scale(${style.scale})` : "scale(1)",
                  }}
                />
                <div style={{ fontSize: "0.75rem", color: "#9CA3AF" }}>
                  <div>
                    햅틱 패턴: <strong style={{ color: style.color }}>{hapticPattern}</strong> · 강도{" "}
                    <strong style={{ color: style.color }}>{hapticIntensity}</strong> · {hapticDurationMs}ms
                  </div>
                  <div style={{ fontSize: "0.7rem", marginTop: 2, color: "#6B7280" }}>
                    시각 근사 표시 (진동은 청각 재현 불가)
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>대기 중…</p>
          )}
        </div>
      </div>
    </section>
  );
}
