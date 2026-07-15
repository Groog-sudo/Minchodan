import type {
  AudioValidationStatus,
  CacheSuppressionStatus,
  AccessibilityValidationStatus,
  LangsmithTraceStatus,
} from "../types/monitor";

interface McpValidationMonitorProps {
  audio: AudioValidationStatus | null | undefined;
  cache: CacheSuppressionStatus | null | undefined;
  accessibility: AccessibilityValidationStatus | null | undefined;
  trace: LangsmithTraceStatus | null | undefined;
}

export function McpValidationMonitor({
  audio,
  cache,
  accessibility,
  trace,
}: McpValidationMonitorProps) {
  return (
    <section className="panel panel-mcp">
      <div className="panel-header">
        <h3 className="panel-title">MCP 검증 및 저지연 모니터</h3>
      </div>
      <div className="panel-content mcp-grid">
        {/* 1. Audio Validator Card */}
        <div className="mcp-card">
          <h4 style={{ margin: "0 0 0.5rem 0", color: "#60A5FA", display: "flex", justifyContent: "space-between" }}>
            <span>Audio Validator</span>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "2px 6px",
                borderRadius: "4px",
                background: audio ? (audio.is_valid ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)") : "rgba(255, 255, 255, 0.1)",
                color: audio ? (audio.is_valid ? "#34D399" : "#F87171") : "#9CA3AF",
              }}
            >
              {audio ? (audio.is_valid ? "정상" : "결함") : "대기"}
            </span>
          </h4>
          {audio ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <div>TTFB 지연: <strong style={{ color: audio.ttfb_ms > 2000 ? "#F87171" : "#34D399" }}>{audio.ttfb_ms.toFixed(1)}ms</strong></div>
              <div>샘플 레이트: <strong>{audio.sample_rate}Hz</strong></div>
              <div>오디오 채널: <strong>{audio.channels}ch (Mono)</strong></div>
              <div>재생 시간: <strong>{audio.duration_sec.toFixed(2)}초</strong></div>
              {audio.error_reasons.length > 0 && (
                <div style={{ color: "#F87171", fontSize: "0.8rem", marginTop: "4px" }}>
                  오류: {audio.error_reasons.join(", ")}
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>TTS 생성 대기 중...</p>
          )}
        </div>

        {/* 2. Accessibility Simulator Card */}
        <div className="mcp-card">
          <h4 style={{ margin: "0 0 0.5rem 0", color: "#F59E0B", display: "flex", justifyContent: "space-between" }}>
            <span>Accessibility Simulator</span>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "2px 6px",
                borderRadius: "4px",
                background: accessibility ? (accessibility.is_valid ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)") : "rgba(255, 255, 255, 0.1)",
                color: accessibility ? (accessibility.is_valid ? "#34D399" : "#F87171") : "#9CA3AF",
              }}
            >
              {accessibility ? (accessibility.is_valid ? "일치" : "비정합") : "대기"}
            </span>
          </h4>
          {accessibility ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <div>자카드 유사도: <strong>{(accessibility.similarity_score * 100).toFixed(0)}%</strong></div>
              {accessibility.details && (
                <>
                  <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={accessibility.details.guidance_text}>
                    가이드: <span style={{ color: "#9CA3AF" }}>{accessibility.details.guidance_text}</span>
                  </div>
                </>
              )}
              {accessibility.warnings.length > 0 && (
                <div style={{ color: "#F87171", fontSize: "0.8rem", marginTop: "4px" }}>
                  경고: {accessibility.warnings.join(", ")}
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>안내문 정합 대조 대기 중...</p>
          )}
        </div>

        {/* 3. Redis Cache Monitor Card */}
        <div className="mcp-card">
          <h4 style={{ margin: "0 0 0.5rem 0", color: "#10B981", display: "flex", justifyContent: "space-between" }}>
            <span>Redis Cache Monitor</span>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "2px 6px",
                borderRadius: "4px",
                background: cache && cache.suppressed_keys.length > 0 ? "rgba(16, 185, 129, 0.2)" : "rgba(255, 255, 255, 0.1)",
                color: cache && cache.suppressed_keys.length > 0 ? "#34D399" : "#9CA3AF",
              }}
            >
              {cache ? `${cache.suppressed_keys.length}개 억제 중` : "대기"}
            </span>
          </h4>
          {cache ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <div>최대 남은 TTL: <strong>{cache.ttl_seconds}초</strong></div>
              <div style={{ marginTop: "4px" }}>
                <span style={{ color: "#9CA3AF", fontSize: "0.8rem" }}>억제 중인 경보 목록:</span>
                {cache.details && cache.details.length > 0 ? (
                  <ul style={{ margin: "4px 0 0 0", paddingLeft: "1.2rem", fontSize: "0.8rem", color: "#A7F3D0" }}>
                    {cache.details.map((item, idx) => (
                      <li key={idx}>
                        {item.alert_id} ({item.ttl_seconds}s 남음)
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div style={{ color: "#9CA3AF", fontSize: "0.8rem", fontStyle: "italic", marginTop: "2px" }}>활성 억제 경보 없음</div>
                )}
              </div>
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>캐시 정보 수집 중...</p>
          )}
        </div>

        {/* 4. LangSmith Trace Card */}
        <div className="mcp-card">
          <h4 style={{ margin: "0 0 0.5rem 0", color: "#EC4899", display: "flex", justifyContent: "space-between" }}>
            <span>LangSmith Trace</span>
            <span
              style={{
                fontSize: "0.75rem",
                padding: "2px 6px",
                borderRadius: "4px",
                background: trace?.enabled ? "rgba(16, 185, 129, 0.2)" : "rgba(255, 255, 255, 0.1)",
                color: trace?.enabled ? "#34D399" : "#9CA3AF",
              }}
            >
              {trace?.enabled ? "활성" : "Mock 폴백"}
            </span>
          </h4>
          {trace ? (
            <div style={{ fontSize: "0.85rem", color: "#D1D5DB", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
              <div>프로젝트: <strong>{trace.project}</strong></div>
              <div>노드 경로: <strong>{trace.from_node} → {trace.to_node}</strong></div>
              <div>파이프라인 RTT: <strong>{trace.latency_ms.toFixed(1)}ms</strong></div>
            </div>
          ) : (
            <p style={{ color: "#9CA3AF", fontSize: "0.85rem", margin: 0 }}>오케스트레이션 실행 대기 중...</p>
          )}
        </div>
      </div>
    </section>
  );
}
