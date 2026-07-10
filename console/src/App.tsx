import { AiPipelineMonitor } from "./components/AiPipelineMonitor";
import { DetectionFeed } from "./components/DetectionFeed";
import { RiskEventLog } from "./components/RiskEventLog";
import { SessionStatus } from "./components/SessionStatus";
import { StatusBadge } from "./components/StatusBadge";
import { SystemMetrics } from "./components/SystemMetrics";
import { useMonitorStream } from "./api/useMonitorStream";
import { OperatorLiveMap } from "./components/OperatorLiveMap";
import { DetectionGuidanceLogTable } from "./components/DetectionGuidanceLogTable";
import type { DetectionGuidanceLogRow } from "./types/monitor";
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
  console.log("app token", token);

  // 기존 useMonitorStream 코드 유지 (여기에 나중에 ?token= 붙일 예정)
  // 로그인 안 해도 무조건 이 Hook이 실행되어 백엔드를 두드립니다!
  const { state, streamUrl, injectDemoEvents } = useMonitorStream(token);

  // 발표/면접 포인트:
  // - detection_guidance_logs는 현재 SSE 실시간 producer 소스가 아니라
  //   백엔드 DB 적재 로그 테이블입니다.
  // - 그래서 운영자 콘솔에서는 DetectionFeed와 분리된 history/log table로 먼저 배치합니다.
  // - 지금은 백엔드 조회 API 연결 전 단계라 mock rows로 화면 구조를 먼저 고정합니다.
  const mockDetectionGuidanceLogs: DetectionGuidanceLogRow[] = [
    {
      log_id: 1,
      event_id: "demo-event-001",
      user_id: 1,
      device_id: 101,
      detected_at: "2026-07-10T10:15:00Z",
      stream_type: "reflex",
      detected_objects_json: '[{"class_name":"pole","confidence":0.91}]',
      tts_text: "전방에 기둥이 있습니다.",
      created_at: "2026-07-10T10:15:12Z",
    },
  ];

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

      {/* TH HARDCODE AREA:
          8001 지도 서버 미실행 상태에서는 iframe load fail이 발생하므로
          OperatorLiveMap은 임시 비활성화합니다. */}
      {/* <OperatorLiveMap /> */}

      {/* 발표/면접 포인트:
          DetectionFeed는 실시간 스트림 모니터링,
          DetectionGuidanceLogTable은 사후 이력 조회 영역입니다.
          실시간 이벤트와 영속 로그를 분리해 운영자 해석 혼선을 줄입니다. */}
      {/* 수정 메모: backend 조회 API 전이라 mock rows를 먼저 연결한 상태입니다. */}
      <DetectionGuidanceLogTable rows={mockDetectionGuidanceLogs} />
      <RiskEventLog events={state.risks} />
    </main>
  );
}
