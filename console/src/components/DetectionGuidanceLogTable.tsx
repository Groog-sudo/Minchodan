import { useState } from "react";
import type { DetectionGuidanceLogRow } from "../types/monitor";
import { eventFrameUrl } from "../api/useDetectionLogs";

// 발표/면접 포인트:
// - 이 컴포넌트는 실시간 SSE DetectionFeed가 아니라,
//   detection_guidance_logs 테이블 기반 history/log table입니다.
// - frame_path가 있는 행은 이벤트 발생 시점 프레임 이미지를 함께 표시해
//   오탐 여부 판별과 안내 발화 당시 상황 확인에 사용합니다.
// - bbox는 이미지에 굽지 않고 detected_objects_json 좌표로 오버레이 렌더링합니다.
//   원본 이미지를 보존해야 임계값/모델을 바꿔 재검증할 수 있기 때문입니다.

interface LoggedDetection {
  class_name?: string;
  confidence?: number;
  direction?: string | null;
  bbox?: { x: number; y: number; w: number; h: number };
  // 반사 로그는 bbox 없이 alert 메타데이터만 가집니다.
  alert_id?: string;
  risk_level?: string;
  distance?: string | null;
}

function parseDetections(json: string): LoggedDetection[] {
  try {
    const parsed = JSON.parse(json);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** 프레임 이미지 위에 bbox를 비율 좌표로 오버레이합니다. */
function FrameWithOverlay({
  src,
  detections,
}: {
  src: string;
  detections: LoggedDetection[];
}) {
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const boxes = detections.filter(
    (det) => det.bbox && det.bbox.w > 0 && det.bbox.h > 0,
  );

  return (
    <div className="frame-overlay-wrap">
      <img
        src={src}
        alt="이벤트 프레임"
        className="frame-overlay-image"
        onLoad={(event) => {
          const img = event.currentTarget;
          setNatural({ w: img.naturalWidth, h: img.naturalHeight });
        }}
      />
      {natural &&
        boxes.map((det, index) => {
          const { x, y, w, h } = det.bbox!;
          return (
            <div
              key={`${det.class_name ?? "obj"}-${index}`}
              className="frame-overlay-box"
              style={{
                left: `${(x / natural.w) * 100}%`,
                top: `${(y / natural.h) * 100}%`,
                width: `${(w / natural.w) * 100}%`,
                height: `${(h / natural.h) * 100}%`,
              }}
            >
              <span className="frame-overlay-label">
                {det.class_name ?? "?"}
                {typeof det.confidence === "number"
                  ? ` ${(det.confidence * 100).toFixed(0)}%`
                  : ""}
              </span>
            </div>
          );
        })}
    </div>
  );
}

export function DetectionGuidanceLogTable({
  rows,
  token,
}: {
  rows: DetectionGuidanceLogRow[];
  token?: string | null;
}) {
  const [selectedLogId, setSelectedLogId] = useState<number | null>(null);
  const selected = rows.find((row) => row.log_id === selectedLogId) ?? null;
  const canShowFrame = (row: DetectionGuidanceLogRow) =>
    Boolean(token && row.event_id && row.frame_path);

  return (
    <section className="panel panel-table">
      <div className="panel-header">
        <h2>Detection Guidance Log</h2>
        <span className="panel-kicker">이력 로그</span>
      </div>

      {rows.length === 0 ? (
        <p className="empty-text">아직 저장된 탐지/안내 이력이 없습니다.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>상황</th>
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
                <tr
                  key={row.log_id}
                  className={row.log_id === selectedLogId ? "row-selected" : undefined}
                  onClick={() =>
                    setSelectedLogId(row.log_id === selectedLogId ? null : row.log_id)
                  }
                >
                  <td>
                    {canShowFrame(row) ? (
                      <img
                        src={eventFrameUrl(row.event_id!, token!)}
                        alt="이벤트 썸네일"
                        className="frame-thumb"
                        loading="lazy"
                      />
                    ) : (
                      "-"
                    )}
                  </td>
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

      {selected && canShowFrame(selected) && (
        <div className="frame-detail">
          <div className="frame-detail-meta">
            <strong>{selected.event_id}</strong>
            <span>{selected.tts_text}</span>
          </div>
          <FrameWithOverlay
            src={eventFrameUrl(selected.event_id!, token!)}
            detections={parseDetections(selected.detected_objects_json)}
          />
        </div>
      )}
    </section>
  );
}
