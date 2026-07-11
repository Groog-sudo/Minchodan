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
      {events.length === 0 ? (
        <p className="empty-text">아직 위험 이벤트가 없습니다.</p>
      ) : (
        /* 수정 메모:
            placeholder 대신 위험 로그 테이블 렌더를 넣은 구간입니다. */
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>위험도</th>
                <th>객체</th>
                <th>신뢰도</th>
                <th>방향</th>
                <th>안내문</th>
                <th>시각</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>
                    <span className={`risk-pill risk-${event.risk_level}`}>
                      {event.risk_level}
                    </span>
                  </td>
                  <td>{event.class_name}</td>
                  <td>
                    {event.confidence !== undefined
                      ? `${(event.confidence * 100).toFixed(1)}%`
                      : "-"}
                  </td>
                  <td>{event.direction ?? "-"}</td>
                  <td>{event.guidance_text ?? "-"}</td>
                  <td>{new Date(event.ts).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
