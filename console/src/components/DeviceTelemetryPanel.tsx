import { useState, useEffect } from "react";
import "./DeviceTelemetryPanel.css";
import type { SessionStatus, AiPipelineStatus } from "../types/monitor";

interface DeviceTelemetryPanelProps {
  latestDetections: any[];
  connected: boolean;
  session: SessionStatus | null;
  ai: AiPipelineStatus | null;
}

export function DeviceTelemetryPanel({ latestDetections, connected, session, ai }: DeviceTelemetryPanelProps) {
  const [blink, setBlink] = useState(false);

  // Blinking effect for live indicators
  useEffect(() => {
    const interval = setInterval(() => {
      setBlink(b => !b);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const deviceId = session?.device_id ?? "dev-001";
  const platform = session?.platform ?? "iOS 26.5";
  const isOnline = session?.status === "connected" || connected;
  const rtt = session?.rtt_ms ?? 12;

  // Detect critical hazards to trigger visual alarm states
  const hasCriticalHazard = latestDetections.some(
    d => d.className === "car" || d.className === "person" || d.className === "caution"
  );

  return (
    <section className="panel telemetry-panel">
      {/* Corner Corner-ticks for military console styling */}
      <div className="panel-corner-tick top-left"></div>
      <div className="panel-corner-tick top-right"></div>
      <div className="panel-corner-tick bottom-left"></div>
      <div className="panel-corner-tick bottom-right"></div>

      <div className="panel-header telemetry-header">
        <div className="header-title-row">
          <span className="live-telemetry-indicator">
            <span className={`live-telemetry-dot ${isOnline ? "green-glow" : "red-glow"}`}></span>
            TELEMETRY FEED
          </span>
          <h2>Device Telemetry & Control</h2>
        </div>
        <span className="panel-kicker">단말기 실시간 분석 & 원격 세션 모니터링</span>
      </div>

      <div className="telemetry-body">
        {/* User Operating Mode HUD Banner */}
        <div className="telemetry-mode-banner">
          <div className="mode-banner-title">USER OPERATING MODE</div>
          {ai?.navigation_status === "NAVIGATING" ? (
            <div className="mode-status-container mode-navigating">
              <span className="mode-pulse-green blinking">🟢</span>
              <div className="mode-details">
                <span className="mode-name green-text font-bold">ROUTE_GUIDANCE_ACTIVE (실시간 길안내 활성)</span>
                <span className="mode-desc">사용자가 목적지 경로 안내를 수신하며 보행 중입니다.</span>
              </div>
            </div>
          ) : ai?.navigation_status === "WAITING_FOR_DESTINATION" ? (
            <div className="mode-status-container mode-waiting">
              <span className="mode-pulse-yellow blinking">🟡</span>
              <div className="mode-details">
                <span className="mode-name yellow-text font-bold">ROUTE_CONFIGURATION (목적지 설정 대기)</span>
                <span className="mode-desc">음성 입력 후 경로 생성을 기다리는 중입니다.</span>
              </div>
            </div>
          ) : ai?.stt_status === "transcribing" ? (
            <div className="mode-status-container mode-question">
              <span className="mode-pulse-blue blinking">🔵</span>
              <div className="mode-details">
                <span className="mode-name blue-text font-bold">INTERACTIVE_QUESTION_MODE (질문 답변 처리 중)</span>
                <span className="mode-desc">음성 명령을 전사하거나 LLM/RAG 지식을 로드 중입니다.</span>
              </div>
            </div>
          ) : (
            <div className="mode-status-container mode-standby">
              <span className="mode-pulse-gray">⚪</span>
              <div className="mode-details">
                <span className="mode-name text-dim font-bold">STANDBY_PATHWAY_DETECTING (보행 탐지 대기)</span>
                <span className="mode-desc">길안내나 대화 상태가 아니며, 로컬 장애물 감지만 작동하고 있습니다.</span>
              </div>
            </div>
          )}
        </div>

        {/* Row 1: Telemetry Data */}
        <div className="telemetry-grid">
          {/* Section 1: System Status */}
          <div className="telemetry-box system-status-box">
            <div className="box-title">SYSTEM STATUS</div>
            <div className="telemetry-row">
              <span className="label">DEVICE ID:</span>
              <span className="value highlight">{deviceId}</span>
            </div>
            <div className="telemetry-row">
              <span className="label">PLATFORM:</span>
              <span className="value">{platform}</span>
            </div>
            <div className="telemetry-row">
              <span className="label">NET LATENCY:</span>
              <span className="value green">{isOnline ? `${rtt}ms` : "OFFLINE"}</span>
            </div>
            <div className="telemetry-row">
              <span className="label">LINK LAYER:</span>
              <span className={`value status-badge-tactical ${isOnline ? "green" : "red"}`}>
                {isOnline ? "WEBSOCKET_UP" : "LINK_DOWN"}
              </span>
            </div>
          </div>

          {/* Section 2: AI Runtime Engines */}
          <div className="telemetry-box ai-engines-box">
            <div className="box-title">AI MODELS RUNTIME</div>
            <div className="telemetry-row">
              <span className="label">DETECTION MODEL:</span>
              <span className="value green">object_detection260714.pt</span>
            </div>
            <div className="telemetry-row">
              <span className="label">SEGMENT MODEL:</span>
              <span className="value green">segmentation260714.pt</span>
            </div>
            <div className="telemetry-row">
              <span className="label">REFLEX FRAME RATE:</span>
              <span className="value highlight">4.0 FPS (DYN)</span>
            </div>
            <div className="telemetry-row">
              <span className="label">COGNITIVE RATE:</span>
              <span className="value">2.0 FPS</span>
            </div>
          </div>
        </div>

        {/* Row 2: Hazards and Warnings */}
        <div className="telemetry-alert-section">
          <div className={`alert-header ${hasCriticalHazard && blink ? "critical-alert" : ""}`}>
            <span>ACTIVE HAZARD MATRIX</span>
            <span className="alert-count">{latestDetections.length} OBJECTS</span>
          </div>
          <div className="hazard-list">
            {latestDetections.length > 0 ? (
              latestDetections.map((det: any, index: number) => {
                const areaRatio = (det.bbox.w * det.bbox.h) / (640 * 640);
                const dist = Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));
                const isCritical = det.className === "car" || det.className === "person" || det.className === "caution";

                return (
                  <div key={index} className={`hazard-item ${isCritical ? "critical" : ""}`}>
                    <span className="hazard-index">[{String(index + 1).padStart(2, "0")}]</span>
                    <span className="hazard-class">{det.className.toUpperCase()}</span>
                    <span className="hazard-dist">{dist.toFixed(2)}m</span>
                    <span className="hazard-conf">CONF: {(det.confidence * 100).toFixed(0)}%</span>
                  </div>
                );
              })
            ) : (
              <div className="hazard-placeholder">
                <span className="scanning-line"></span>
                NO HAZARD DETECTED IN PATHWAY - SCANNING...
              </div>
            )}
          </div>
        </div>

        {/* Row 3: Voice Guidance System */}
        <div className="telemetry-speech-section">
          <div className="speech-box">
            <div className="box-title">SPEECH INTERACTION LOG (STT/TTS)</div>
            <div className="speech-row">
              <span className="label">MIC STATE:</span>
              {ai?.stt_status === "recording" || ai?.stt_status === "transcribing" ? (
                <span className="value recording-blink">
                  🎙️ {ai?.stt_status === "recording" ? "AUDIO_CAPTURING (말씀하세요)" : "SPEECH_TRANSCRIBING"}
                </span>
              ) : (
                <span className="value text-dim">STANDBY (화면 누르고 대기)</span>
              )}
            </div>
            <div className="speech-row last-guidance-row">
              <span className="label">TTS GUIDANCE:</span>
              <span className="value guidance-text highlight-blue">
                {ai?.last_guidance ? `"${ai.last_guidance}"` : "무발화 대기 중"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
