import type { RiskEvent } from "../types/monitor";

export function RiskEventLog({ events }: { events: RiskEvent[] }) {
  return (
    <section className="panel panel-table">
      <div className="panel-header">
        <h2>RiskEventLog</h2>
        <span className="panel-kicker">위험 로그</span>
      </div>

      {/* TH HARDCODE AREA:
          events.map으로 위험도, 객체명, 신뢰도, 방향, 안내문, 시간을 테이블에 표시합니다.
          high/mid/low 색상 분기도 담당자가 직접 작성합니다. */}
      <div className="placeholder-box">
        위험 이벤트 {events.length}개
      </div>
    </section>
  );
}
