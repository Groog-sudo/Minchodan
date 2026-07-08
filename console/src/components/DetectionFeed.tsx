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
      <div className="placeholder-box">
        탐지 이벤트 {items.length}개
      </div>
    </section>
  );
}
