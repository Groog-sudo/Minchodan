import type { DetectionFeedItem } from "../types/monitor";

export function DetectionFeed({ items }: { items: DetectionFeedItem[] }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>DetectionFeed</h2>
        <span className="panel-kicker">탐지 메타데이터</span>
      </div>

      {/* TH HARDCODE AREA:
          1차 MVP에서는 이미지 없이 stream, class_name,
          confidence, inference_ms, surface 텍스트 메타데이터를 직접 표시합니다. */}
      {items.length === 0 ? (
        <p className="empty-text">아직 탐지 이벤트가 없습니다.</p>
      ) : (
        <div className="feed-list">
          {items.map((item) => (
            <div key={item.id} className="feed-row">
              {/* 수정 메모:
                  event_id 제목 노출, stream 중복, confidence 조건식을 정리한 구간입니다. */}
              <div>
                <strong>{item.class_name}</strong>
                <span>{item.event_id}</span>
                <span>{item.device_id}</span>
              </div>

              <div>
                <span>{item.stream}</span>
                <span>{item.confidence !== undefined ? `${(item.confidence * 100).toFixed(1)}%` : "-"}</span>
                <span>{item.inference_ms !== undefined ? `${item.inference_ms}ms` : "-"}</span>
                <span>{item.surface ?? "-"}</span>
                <span>{new Date(item.ts).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
