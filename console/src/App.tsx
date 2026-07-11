import { AiPipelineMonitor } from "./components/AiPipelineMonitor";
import { DetectionFeed } from "./components/DetectionFeed";
import { RiskEventLog } from "./components/RiskEventLog";
import { SessionStatus } from "./components/SessionStatus";
import { StatusBadge } from "./components/StatusBadge";
import { SystemMetrics } from "./components/SystemMetrics";
import { useMonitorStream } from "./api/useMonitorStream";
import { useDetectionLogs } from "./api/useDetectionLogs";
import { OperatorLiveMap } from "./components/OperatorLiveMap";
import { DetectionGuidanceLogTable } from "./components/DetectionGuidanceLogTable";
import type { DetectionGuidanceLogRow } from "./types/monitor";
import { useState } from "react";
import { Login } from "./components/Login";

const DEMO_GUIDANCE_LOGS: DetectionGuidanceLogRow[] = [
  {
    log_id: 1,
    event_id: "demo-event-001",
    user_id: 1,
    device_id: 101,
    detected_at: "2026-07-10T10:15:00Z",
    stream_type: "reflex",
    detected_objects_json: '[{"class_name":"pole","confidence":0.91}]',
    tts_text: "전방에 기둥이 있습니다.",
    frame_path: null,
    created_at: "2026-07-10T10:15:12Z",
  },
];

function connectionTone(connection: string) {
  if (connection === "connected") return "good";
  if (connection === "connecting") return "warn";
  if (connection === "error") return "bad";
  return "idle";
}
export default function App() {
  // MVP 단계에서는 토큰을 브라우저 저장소가 아닌 메모리에만 보관한다.
  const [token, setToken] = useState<string | null>(null);
  const { state, streamUrl, injectDemoEvents } = useMonitorStream(token);
  // 사후 이력 로그는 REST 폴링으로 조회한다 (frame_path 이미지 포함).
  const { rows: fetchedLogs } = useDetectionLogs(token);
  const isDemoMode =
    import.meta.env.DEV && import.meta.env.VITE_ENABLE_DEMO_DATA === "true";
  const detectionGuidanceLogs =
    isDemoMode && fetchedLogs.length === 0 ? DEMO_GUIDANCE_LOGS : fetchedLogs;

  // 토큰이 없으면 무조건 로그인 화면만 띄움!
  if(!token){
    return <Login onLogin={(newToken) => setToken(newToken)} />;
  }

  // 토큰이 있으면 원래 화면(대시보드) 랜더링!
  return (
    <main className="app-shell">
          {/* ... 기존 헤더, 대시보드, 지도 등 전체 코드 그대로 ... */}
      <header className="topbar">
        <div>
          <p className="eyebrow">Minchodan Operator Console</p>
          <h1>스마트 가이드독 실시간 관제</h1>
        </div>
        <div className="topbar-actions">
          <StatusBadge label={state.connection} tone={connectionTone(state.connection)} />
          {isDemoMode && (
            <button type="button" onClick={injectDemoEvents}>샘플 이벤트</button>
          )}
        </div>
      </header>

      <section className="stream-line">
        <span>SSE</span>
        <strong>{streamUrl}</strong>
        <span>마지막 이벤트</span>
        <strong>
          {state.last_event_at ? new Date(state.last_event_at).toLocaleTimeString() : "-"}
        </strong>
      </section>

      <section className="dashboard-grid">
        <SystemMetrics metrics={state.system} />
        <SessionStatus sessions={state.sessions} />
        <AiPipelineMonitor ai={state.ai} />
        <DetectionFeed items={state.detections} />
      </section>

      {/* 2026-07-11 재활성화: 지도 서브앱이 8001 독립 포트에서 메인 서버(8000)
          하위 /navigation 마운트로 통합되어 iframe load fail 원인이 해소됨.
          주소는 VITE_NAV_MAP_URL로 재정의 가능(기본 localhost:8000). */}
      <OperatorLiveMap />

      {/* 발표/면접 포인트:
          DetectionFeed는 실시간 스트림 모니터링,
          DetectionGuidanceLogTable은 사후 이력 조회 영역입니다.
          실시간 이벤트와 영속 로그를 분리해 운영자 해석 혼선을 줄입니다. */}
      <DetectionGuidanceLogTable rows={detectionGuidanceLogs} token={token} />
      <RiskEventLog events={state.risks} />
    </main>
  );
}
