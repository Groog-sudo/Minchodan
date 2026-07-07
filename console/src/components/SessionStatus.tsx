import type { SessionStatus as SessionStatusData } from "../types/monitor";

export function SessionStatus({ sessions }: { sessions: SessionStatusData[] }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>SessionStatus</h2>
        <span className="panel-kicker">TH 직접 구현</span>
      </div>

      {/* TH HARDCODE AREA:
          sessions.map으로 device_id, platform, status, rtt_ms, last_seen을 직접 렌더링합니다.
          device_id 기준 upsert는 useMonitorStream.ts에서 직접 작성합니다. */}
      <div className="placeholder-box">
        단말 세션 {sessions.length}개
      </div>
    </section>
  );
}
