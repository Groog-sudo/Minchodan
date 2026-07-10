import type { DetectionFeedItem } from "../types/monitor";

export function DetectionFeed({ items }: { items: DetectionFeedItem[] }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>DetectionFeed</h2>
        <span className="panel-kicker">탐지 메타데이터</span>
      </div>

      {/* TH HARDCODE AREA:
          1차 MVP에서는 이미지 없이 event_id, stream, class_name,
          confidence, inference_ms, surface 텍스트 메타데이터를 직접 표시합니다. */}
      {items.length === 0 ? (
        <p className="empty-text">아직 탐지 이벤트가 없습니다.</p>
      ) : (
        <div className="feed-list">
          {items.map((item) => (
            <div key={item.id} className="feed-row">
              <div>
                  <strong>  
                    {item.event_id}
                  </strong>
                <span>{item.stream}</span>
                <span>{item.device_id}</span>
              </div>

              <div>
                <span>{item.stream}</span>
                <span>{item.confidence ? `[(item.confidence * 100).toFixed(1)]%` : "-"}</span>
                <span>{item.inference_ms ? `${item.inference_ms}ms` : "-"}</span>
                <span>{item.surface ??  "-"}</span>
                <span>{new Date(item.ts).toLocaleTimeString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="placeholder-box">
        탐지 이벤트 {items.length}개
      </div>
    </section>
  );
}
