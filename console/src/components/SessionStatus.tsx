import type { SessionStatus as SessionStatusData } from "../types/monitor";
import { StatusBadge } from "./StatusBadge";

function sessionTone(status: SessionStatusData["status"]): "good" | "bad" | "idle" {
  if (status === "connected") return "good";
  if (status === "disconnected") return "bad";
  return "idle";
}

export function SessionStatus({ sessions }: { sessions: SessionStatusData[] }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>SessionStatus</h2>
        <span className="panel-kicker">단말 연결</span>
      </div>

      {/* TH HARDCODE AREA:
          sessions.map으로 device_id, platform, status, rtt_ms, last_seen을 직접 렌더링합니다.
          device_id 기준 upsert는 useMonitorStream.ts에서 직접 작성합니다. */}
      {/*
        발표/면접 대응 포인트:
        SessionStatus는 WebSocket에 연결된 단말 상태를 운영자가 확인하는 보드입니다.
        useMonitorStream.ts에서 device_id 기준 upsert를 처리하므로 여기서는 sessions 배열을 그대로 렌더링만 합니다.
        RTT는 단말과 서버 사이 실시간 통신 지연을 보는 값이라 반사 경로 지연 판단의 보조 지표가 됩니다.
      */}
      {sessions.length > 0 ? (
        <div className="session-list">
          {sessions.map((session) => (
            <div className="session-row" key={session.device_id}>
              <div>
                <strong>{session.device_id}</strong>
                <span>
                  {session.platform ?? "unknown"} · RTT {session.rtt_ms ?? "-"}ms
                </span>
              </div>
              <div className="session-meta">
                <span>
                  {session.last_seen
                    ? new Date(session.last_seen).toLocaleTimeString()
                    : "-"}
                </span>
                <StatusBadge label={session.status} tone={sessionTone(session.status)} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="placeholder-box">연결된 단말이 없습니다.</div>
      )}
    </section>
  );
}
