import type { DetectionGuidanceLogRow } from "../types/monitor";
// 발표/면접 포인트:
// - 이 컴포넌트는 실시간 SSE DetectionFeed가 아니라,
//   detection_guidance_logs 테이블 기반 history/log table 자리입니다.
// - 즉시 경보용 반사 스트림 화면과, 사후 조회용 로그 화면을 분리해
//   운영자 콘솔 역할을 명확히 나눕니다.
// - 현재는 console 데모/확장 계약 단계이며,
//   실제 backend 조회 API 추가 확인이 필요합니다.

export function DetectionGuidanceLogTable({
  rows,
}: {
  rows: DetectionGuidanceLogRow[];
}) {
  return (
    <section className="panel panel-table">
      <div className="panel-header">
        <h2>Detection Guidance Log</h2>
        <span className="panel-kicker">이력 로그</span>
      </div>

      {rows.length === 0 ? (
        <p className="empty-text">아직 저장된 탐지/안내 이력이 없습니다.</p>
      ) : (
        /* 수정 메모:
            placeholder 대신 최소 history/log table 렌더를 넣은 구간입니다. */
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>감지 시각</th>
                <th>스트림</th>
                <th>이벤트 ID</th>
                <th>TTS 안내문</th>
                <th>사용자</th>
                <th>기기</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.log_id}>
                  <td>{new Date(row.detected_at).toLocaleString()}</td>
                  <td>{row.stream_type}</td>
                  <td>{row.event_id ?? "-"}</td>
                  <td>{row.tts_text}</td>
                  <td>{row.user_id ?? "-"}</td>
                  <td>{row.device_id ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
