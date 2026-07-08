import { AiPipelineMonitor } from "./components/AiPipelineMonitor";
import { DetectionFeed } from "./components/DetectionFeed";
import { RiskEventLog } from "./components/RiskEventLog";
import { SessionStatus } from "./components/SessionStatus";
import { StatusBadge } from "./components/StatusBadge";
import { SystemMetrics } from "./components/SystemMetrics";
import { useMonitorStream } from "./api/useMonitorStream";

function connectionTone(connection: string) {
  if (connection === "connected") return "good";
  if (connection === "connecting") return "warn";
  if (connection === "error") return "bad";
  return "idle";
}

export default function App() {
  const { state, streamUrl, injectDemoEvents } = useMonitorStream();

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Minchodan Operator Console</p>
          <h1>스마트 가이드독 실시간 관제</h1>
        </div>
        <div className="topbar-actions">
          <StatusBadge label={state.connection} tone={connectionTone(state.connection)} />
          <button type="button" onClick={injectDemoEvents}>샘플 이벤트</button>
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

      <RiskEventLog events={state.risks} />
    </main>
  );
}
