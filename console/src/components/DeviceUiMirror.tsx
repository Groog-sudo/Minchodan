import { useState } from "react";
import "./DeviceUiMirror.css";
import type { SessionStatus, AiPipelineStatus } from "../types/monitor";

interface DeviceUiMirrorProps {
  imageUrl: string | null;
  latestDetections: any[];
  connected: boolean;
  session: SessionStatus | null;
  ai: AiPipelineStatus | null;
}

export function DeviceUiMirror({ imageUrl, latestDetections, connected, session, ai }: DeviceUiMirrorProps) {
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null);

  // Default values or fallbacks
  const deviceId = session?.device_id ?? "dev-001";
  const platform = session?.platform ?? "iOS 26.5";
  const isOnline = session?.status === "connected" || connected;
  const rtt = session?.rtt_ms ?? 12;

  // Format active detections
  const activeDetectionsStr = latestDetections.length > 0
    ? latestDetections.map(d => {
        const areaRatio = (d.bbox.w * d.bbox.h) / (640 * 640);
        const dist = Math.min(3.0, Math.max(0.3, 0.22 / Math.sqrt(areaRatio)));
        return `${d.className} ${dist.toFixed(1)}m (${(d.confidence * 100).toFixed(0)}%)`;
      }).join(", ")
    : "없음";

  return (
    <section className="panel device-mirror-panel">
      <div className="panel-header">
        <h2>Device UI Mirror</h2>
        <span className="panel-kicker">단말기 디지털 트윈 (실기기 UI 미러링)</span>
      </div>

      <div className="mirror-viewport">
        {/* iPhone Style Shell Container */}
        <div className="phone-container">
          <div className="phone-notch"></div>

          {/* Internal Phone Screen */}
          <div className="phone-screen">
            {/* Top Status Bar */}
            <div className="screen-status-bar">
              <span className="status-time">11:42</span>
              <div className="status-icons">
                <span className="status-signal">📶</span>
                <span className="status-wifi">📶</span>
                <span className="status-battery">🔋 100%</span>
              </div>
            </div>

            {/* App Header */}
            <div className="app-header">
              <div className="app-brand-group">
                <img src="/gildang-symbol.png" alt="" className="app-brand-symbol" />
                <div className="app-title-group">
                  <span className="app-title">길댕</span>
                  <span className="app-subtitle">GILDANG 스마트 가이드독</span>
                </div>
              </div>
              <span className={`app-status-badge ${isOnline ? "online" : "offline"}`}>
                {isOnline ? "CONNECTED" : "OFFLINE"}
              </span>
            </div>

            {/* Camera View Area */}
            <div className="screen-camera-container frame-overlay-wrap">
              {imageUrl ? (
                <>
                  <img
                    src={imageUrl}
                    alt="단말기 카메라 화면"
                    className="screen-camera-image frame-overlay-image"
                    onLoad={(event) => {
                      const img = event.currentTarget;
                      setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
                    }}
                  />
                  {naturalSize &&
                    latestDetections.map((det: any, index: number) => {
                      if (!det.bbox) return null;
                      const { x, y, w, h } = det.bbox;
                      return (
                        <div
                          key={index}
                          className="frame-overlay-box"
                          style={{
                            left: `${(x / naturalSize.w) * 100}%`,
                            top: `${(y / naturalSize.h) * 100}%`,
                            width: `${(w / naturalSize.w) * 100}%`,
                            height: `${(h / naturalSize.h) * 100}%`,
                            borderWidth: "1px",
                          }}
                        >
                          <span className="frame-overlay-label" style={{ fontSize: "8px", top: "-14px", padding: "0 3px" }}>
                            {det.className}
                          </span>
                        </div>
                      );
                    })}
                </>
              ) : (
                <div className="screen-camera-placeholder">
                  <span>CAMERA TIMEOUT</span>
                </div>
              )}
            </div>

            {/* Debug Console Log inside phone screen */}
            <div className="screen-debug-logs">
              <div className="log-line">모드: REAL(실기기)</div>
              <div className="log-line">식별: {deviceId} / {platform}</div>
              <div className="log-line">WS: {isOnline ? "connected" : "disconnected"} ({rtt}ms)</div>
              <div className="log-line">로컬: seg(OK) / det(OK)</div>
              <div className="log-line text-truncate">
                안내: {ai?.last_guidance || "대기 상태"}
              </div>
            </div>

            {/* Confidence Display */}
            <div className="screen-conf-bar">
              <span>신뢰도 임계값: 40%</span>
              <div className="conf-adjust">
                <span className="conf-btn">-</span>
                <span className="conf-btn">+</span>
              </div>
            </div>

            {/* Realtime Detection Text */}
            <div className="screen-detections">
              <span className="det-title">[실시간 감지]</span>
              <span className="det-text text-truncate">{activeDetectionsStr}</span>
            </div>

            {/* Bottom Button Panel */}
            <div className="screen-stt-button">
              {ai?.stt_status === "transcribing" || ai?.stt_status === "recording" ? (
                <div className="stt-active-state">
                  <span className="pulse-mic">🎙️</span>
                  <span>{ai?.stt_status === "recording" ? "듣는 중..." : "음성 처리 중..."}</span>
                </div>
              ) : (
                <span>화면을 누르고 말하기</span>
              )}
            </div>

            {/* Floating Toggle Buttons */}
            <div className="screen-floating-toggles">
              <span className="toggle-btn">지도</span>
              <span className="toggle-btn">거리측정</span>
            </div>

            {/* iPhone Bottom Bar */}
            <div className="phone-home-indicator"></div>
          </div>
        </div>
      </div>
    </section>
  );
}
