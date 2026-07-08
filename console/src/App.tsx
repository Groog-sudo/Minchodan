import { AiPipelineMonitor } from "./components/AiPipelineMonitor";
import { DetectionFeed } from "./components/DetectionFeed";
import { RiskEventLog } from "./components/RiskEventLog";
import { SessionStatus } from "./components/SessionStatus";
import { StatusBadge } from "./components/StatusBadge";
import { SystemMetrics } from "./components/SystemMetrics";
import { useMonitorStream } from "./api/useMonitorStream";
import { OperatorLiveMap } from "./components/OperatorLiveMap";
import { useState } from "react";
import { Login } from "./components/Login";

function connectionTone(connection: string) {
  if (connection === "connected") return "good";
  if (connection === "connecting") return "warn";
  if (connection === "error") return "bad";
  return "idle";
}

export default function App() {
  // 💡 [면접 대비 주석 - 토큰 관리]
  // MVP 단계라 일단 메모리(useState)에만 들고 있습니다. 
  // 새로고침하면 로그아웃되지만, 보안상 XSS 등 탈취 위험이 가장 적은 안전한 방식입니다!
  const [token, setToken] = useState<string | null>(null);

  // 기존 useMonitorStream 코드 유지 (여기에 나중에 ?token= 붙일 예정)
  // 로그인 안 해도 무조건 이 Hook이 실행되어 백엔드를 두드립니다!
  const { state, streamUrl, injectDemoEvents } = useMonitorStream(token);

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

      {/* 📍 여기에 지도 컴포넌트 추가! */}
      <OperatorLiveMap />

      <RiskEventLog events={state.risks} />
    </main>
  );
}
