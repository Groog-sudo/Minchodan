// 2026-07-19: 관제 콘솔 오디오 미러 컴포넌트.
// 서버가 단말에 보내는 것과 동일한 guide 오디오(WAV)와 반사 비프 클립을
// 콘솔에서도 재생하고, 햅틱 패턴을 시각 펄스로 표현한다.
//
// - 인지 가이드 / 반사 알림은 각각 활성·비활성 토글 가능(localStorage 유지).
// - 브라우저 자동재생 정책: "오디오 활성화" 클릭 후 자동 재생.

import { useEffect, useRef, useState } from "react";
import type { ConsoleGuideAudioEvent, ConsoleReflexAlertEvent } from "../api/useLiveFeed";

interface ConsoleAudioMirrorProps {
  guideAudioEvent: ConsoleGuideAudioEvent | null;
  reflexAlertEvent: ConsoleReflexAlertEvent | null;
}

const LS_COGNITIVE = "minchodan.console.audioMirror.cognitiveEnabled";
const LS_REFLEX = "minchodan.console.audioMirror.reflexEnabled";

function readBool(key: string, fallback: boolean): boolean {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return raw === "1" || raw === "true";
  } catch {
    return fallback;
  }
}

function writeBool(key: string, value: boolean): void {
  try {
    localStorage.setItem(key, value ? "1" : "0");
  } catch {
    // ignore
  }
}

/** 서버 clip은 "reflex_clips/high_front.wav" 형태. public 파일은 basename만 사용. */
function resolveReflexClipUrl(clip: string): string {
  const basename = clip.split("/").pop() || clip;
  return `/reflex_clips/${basename}`;
}

function ToggleChip({
  label,
  enabled,
  onToggle,
}: {
  label: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      style={{
        fontSize: "0.75rem",
        padding: "4px 10px",
        borderRadius: "4px",
        background: enabled ? "rgba(16, 185, 129, 0.2)" : "rgba(107, 114, 128, 0.25)",
        color: enabled ? "#34D399" : "#9CA3AF",
        border: enabled ? "1px solid rgba(16, 185, 129, 0.45)" : "1px solid rgba(107, 114, 128, 0.4)",
        cursor: "pointer",
        fontWeight: 600,
      }}
    >
      {label}: {enabled ? "활성" : "비활성"}
    </button>
  );
}

export function ConsoleAudioMirror({ guideAudioEvent, reflexAlertEvent }: ConsoleAudioMirrorProps) {
  const [muted, setMuted] = useState(false);
  const [audioUnlocked, setAudioUnlocked] = useState(false);
  const [playBlockedHint, setPlayBlockedHint] = useState(false);
  const [cognitiveEnabled, setCognitiveEnabled] = useState(() => readBool(LS_COGNITIVE, true));
  const [reflexEnabled, setReflexEnabled] = useState(() => readBool(LS_REFLEX, true));
  const [hapticPulseKey, setHapticPulseKey] = useState(0);
  const guideAudioRef = useRef<HTMLAudioElement | null>(null);
  const reflexAudioRef = useRef<HTMLAudioElement | null>(null);
  const hapticTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioUnlockedRef = useRef(false);
  const mutedRef = useRef(false);

  useEffect(() => {
    audioUnlockedRef.current = audioUnlocked;
  }, [audioUnlocked]);
  useEffect(() => {
    mutedRef.current = muted;
  }, [muted]);

  const toggleCognitive = () => {
    setCognitiveEnabled((prev) => {
      const next = !prev;
      writeBool(LS_COGNITIVE, next);
      if (!next) {
        const audio = guideAudioRef.current;
        if (audio) {
          audio.pause();
          audio.removeAttribute("src");
        }
      }
      return next;
    });
  };

  const toggleReflex = () => {
    setReflexEnabled((prev) => {
      const next = !prev;
      writeBool(LS_REFLEX, next);
      if (!next) {
        const audio = reflexAudioRef.current;
        if (audio) {
          audio.pause();
          audio.removeAttribute("src");
        }
      }
      return next;
    });
  };

  const unlockAudio = async () => {
    try {
      const silent = new Audio(
        "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
      );
      silent.volume = 0.01;
      await silent.play();
      silent.pause();
    } catch {
      // 제스처 없이 호출되면 실패할 수 있음. 아래 상태만 갱신하고 다음 재생에서 재시도.
    }
    audioUnlockedRef.current = true;
    setAudioUnlocked(true);
    setPlayBlockedHint(false);
  };

  const playElement = async (audio: HTMLAudioElement, label: string) => {
    if (!audioUnlockedRef.current || mutedRef.current) return;
    const tryPlay = async () => {
      if (!audioUnlockedRef.current || mutedRef.current) return;
      try {
        audio.currentTime = 0;
        await audio.play();
        setPlayBlockedHint(false);
      } catch (err) {
        const name = err instanceof DOMException || err instanceof Error ? err.name : "";
        // 새 src로 교체되며 이전 play()가 취소된 경우 - 자동재생 차단이 아님.
        if (name === "AbortError") return;
        console.warn(`[ConsoleAudioMirror] ${label} 재생 차단:`, err);
        if (name === "NotAllowedError") {
          setPlayBlockedHint(true);
          audioUnlockedRef.current = false;
          setAudioUnlocked(false);
        }
      }
    };

    if (audio.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
      await tryPlay();
      return;
    }

    await new Promise<void>((resolve) => {
      const onReady = () => {
        audio.removeEventListener("loadeddata", onReady);
        audio.removeEventListener("error", onReady);
        resolve();
      };
      audio.addEventListener("loadeddata", onReady, { once: true });
      audio.addEventListener("error", onReady, { once: true });
    });
    await tryPlay();
  };

  // 브라우저 자동재생 정책: 첫 클릭/키 입력으로 AudioContext 잠금 해제.
  useEffect(() => {
    const onGesture = () => {
      void unlockAudio();
    };
    window.addEventListener("pointerdown", onGesture, { once: true, capture: true });
    window.addEventListener("keydown", onGesture, { once: true, capture: true });
    return () => {
      window.removeEventListener("pointerdown", onGesture, true);
      window.removeEventListener("keydown", onGesture, true);
    };
  }, []);

  useEffect(() => {
    if (!cognitiveEnabled) return;
    if (!guideAudioEvent?.audio_url) return;
    const audio = guideAudioRef.current;
    if (!audio) return;
    audio.src = guideAudioEvent.audio_url;
    audio.volume = muted ? 0 : 0.7;
    void playElement(audio, "guide");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [guideAudioEvent?.audio_url, muted, audioUnlocked, cognitiveEnabled]);

  useEffect(() => {
    if (!reflexEnabled) return;
    if (!reflexAlertEvent?.clip) return;
    const audio = reflexAudioRef.current;
    if (!audio) return;
    audio.src = resolveReflexClipUrl(reflexAlertEvent.clip);
    audio.volume = muted ? 0 : 0.8;
    void playElement(audio, "reflex");

    setHapticPulseKey((k) => k + 1);
    const haptic = reflexAlertEvent.haptic_pattern;
    const durationMs = haptic?.duration_ms ?? 300;
    if (hapticTimerRef.current) clearTimeout(hapticTimerRef.current);
    hapticTimerRef.current = setTimeout(() => setHapticPulseKey(0), durationMs);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reflexAlertEvent?.event_id, reflexAlertEvent?.clip, muted, audioUnlocked, reflexEnabled]);

  useEffect(() => {
    return () => {
      if (hapticTimerRef.current) clearTimeout(hapticTimerRef.current);
    };
  }, []);

  const haptic = reflexAlertEvent?.haptic_pattern;
  const hapticIntensity = haptic?.intensity ?? "medium";
  const hapticPattern = haptic?.pattern ?? "single";
  const hapticDurationMs = haptic?.duration_ms ?? 300;
  const intensityStyle: Record<string, { color: string; scale: number }> = {
    heavy: { color: "#F87171", scale: 1.4 },
    medium: { color: "#FBBF24", scale: 1.15 },
    light: { color: "#60A5FA", scale: 0.95 },
  };
  const style = intensityStyle[hapticIntensity] ?? intensityStyle.medium;

  return (
    <section className="panel panel-audio-mirror" style={{ marginBottom: "0.5rem" }}>
      <div
        className="panel-header"
        style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}
      >
        <h3 className="panel-title">단말 오디오 미러</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <ToggleChip label="인지 가이드" enabled={cognitiveEnabled} onToggle={toggleCognitive} />
          <ToggleChip label="반사 알림" enabled={reflexEnabled} onToggle={toggleReflex} />
          {!audioUnlocked ? (
            <button
              type="button"
              onClick={() => void unlockAudio()}
              style={{
                fontSize: "0.75rem",
                padding: "4px 10px",
                borderRadius: "4px",
                background: "rgba(96, 165, 250, 0.25)",
                color: "#93C5FD",
                border: "1px solid rgba(96, 165, 250, 0.5)",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              오디오 활성화
            </button>
          ) : (
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
              {muted ? "음소거" : "재생 중"}
            </button>
          )}
        </div>
      </div>
      {(playBlockedHint || !audioUnlocked) && (cognitiveEnabled || reflexEnabled) && (
        <div
          style={{
            margin: "0 0 0.5rem 0",
            padding: "6px 10px",
            borderRadius: 4,
            background: "rgba(251, 191, 36, 0.12)",
            color: "#FBBF24",
            fontSize: "0.75rem",
          }}
        >
          브라우저 자동재생 정책으로 소리가 막혀 있습니다. 화면을 한 번 클릭하거나 &quot;오디오 활성화&quot;를 눌러 주세요.
        </div>
      )}
      <div className="panel-content" style={{ display: "flex", gap: "1rem", alignItems: "stretch", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 240px", minWidth: 240, opacity: cognitiveEnabled ? 1 : 0.45 }}>
          <h4 style={{ margin: "0 0 0.25rem 0", color: "#60A5FA", fontSize: "0.85rem" }}>인지 가이드</h4>
          {!cognitiveEnabled ? (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>비활성 — 재생·표시 중지</p>
          ) : guideAudioEvent ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB", marginBottom: 6 }}>
              <div style={{ marginBottom: 4 }}>
                <strong>{guideAudioEvent.guidance_text || "(빈 안내문)"}</strong>
              </div>
              <div style={{ fontSize: "0.75rem", color: "#9CA3AF" }}>
                {guideAudioEvent.duration_ms.toFixed(0)}ms · {guideAudioEvent.source ?? "cognitive"} ·{" "}
                {guideAudioEvent.device_id}
                {guideAudioEvent.audio_url ? "" : " · 오디오 수신 중…"}
              </div>
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: "0 0 6px 0" }}>대기 중…</p>
          )}
          <audio
            ref={guideAudioRef}
            controls
            style={{ width: "100%", opacity: cognitiveEnabled && guideAudioEvent?.audio_url ? 1 : 0.35 }}
          />
        </div>

        <div style={{ flex: "1 1 240px", minWidth: 240, opacity: reflexEnabled ? 1 : 0.45 }}>
          <h4 style={{ margin: "0 0 0.25rem 0", color: "#F59E0B", fontSize: "0.85rem" }}>반사 알림</h4>
          {!reflexEnabled ? (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>비활성 — 재생·표시 중지</p>
          ) : reflexAlertEvent ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB", marginBottom: 6 }}>
              <div style={{ marginBottom: 4 }}>
                <strong>{reflexAlertEvent.alert_id}</strong>
                {reflexAlertEvent.class_name ? ` · ${reflexAlertEvent.class_name}` : ""}
                {reflexAlertEvent.direction ? ` · ${reflexAlertEvent.direction}` : ""}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#9CA3AF" }}>
                clip: {reflexAlertEvent.clip ?? "(없음)"} · band: {reflexAlertEvent.distance_band ?? "-"}
              </div>
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: "0 0 6px 0" }}>대기 중…</p>
          )}
          <audio
            ref={reflexAudioRef}
            controls
            style={{ width: "100%", opacity: reflexEnabled && reflexAlertEvent ? 1 : 0.35 }}
          />
          {reflexEnabled && reflexAlertEvent && (
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
          )}
        </div>
      </div>
    </section>
  );
}
