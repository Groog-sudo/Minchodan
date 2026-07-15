import { useMemo } from "react";
import type { DetectionGuidanceLogRow, GuidanceTraceRow, TrackedObject } from "../types/monitor";

const MAX_TRACE_ROWS = 30;

/**
 * detected_objects_json 데이터를 TrackedObject 배열로 안전하게 파싱한다.
 * REST API(이미 역직렬화된 Array) 및 WS/데모(JSON string) 양쪽 모두 지원(방어적 코딩).
 */
function parseTrackedObjects(jsonVal: any): TrackedObject[] {
  if (!jsonVal) return [];
  if (Array.isArray(jsonVal)) {
    return jsonVal as TrackedObject[];
  }
  if (typeof jsonVal === "object") {
    return [jsonVal] as any;
  }
  if (typeof jsonVal === "string") {
    try {
      const parsed = JSON.parse(jsonVal);
      if (Array.isArray(parsed)) return parsed as TrackedObject[];
      if (typeof parsed === "object" && parsed !== null) return [parsed] as any;
      return [];
    } catch {
      return [];
    }
  }
  return [];
}

/**
 * 로그 행에서 대표 객체를 선택한다.
 * 인지 경로: confidence가 가장 높은 객체.
 * 반사 경로: 첫 번째 객체(단일 객체가 전제).
 */
function pickPrimaryObject(objects: TrackedObject[]): TrackedObject | null {
  if (objects.length === 0) return null;
  if (objects.length === 1) return objects[0];
  return objects.reduce((best, cur) =>
    (cur.confidence ?? 0) > (best.confidence ?? 0) ? cur : best,
  );
}

/**
 * 발화 트리거 원인을 추론한다 (화면 표시용).
 *
 * 반사 경로:
 *   distance <= 0.5  -> "근접+연속히트" (가장 위험, 연속 비프음)
 *   distance > 0.5   -> "연속히트"      (MIN_HIT_COUNT 도달)
 *   surface 게이트   -> "위험 노면"     (caution 클래스)
 * 인지 경로:
 *   direction "approaching" -> "접근"
 *   direction "departing"   -> "이탈"
 *   track_id 없음           -> "노면/기타"
 *   그 외                   -> "인지 가이드"
 */
function inferTriggerReason(
  row: DetectionGuidanceLogRow,
  obj: TrackedObject | null,
): string {
  if (row.stream_type === "reflex") {
    // surface 게이트: alert_id가 "surface_"로 시작하면 노면 경보
    const alertId = obj?.alert_id ?? "";
    if (alertId.startsWith("surface_") || alertId.startsWith("head_level_")) {
      if (alertId.startsWith("head_level_")) return "상체 위험";
      return "위험 노면";
    }
    const dist = obj?.distance ?? 1.0;
    if (dist <= 0.5) return "근접+연속히트";
    return "연속히트";
  }
  // 인지 경로
  const dir = obj?.direction ?? "";
  if (dir === "approaching") return "접근";
  if (dir === "departing") return "이탈";
  if (!obj?.track_id) return "노면/기타";
  return "인지 가이드";
}

/**
 * DetectionGuidanceLogRow 배열을 GuidanceTraceRow 배열로 변환한다.
 * detected_objects_json을 파싱하여 대표 객체의 track_id, class_name, hit_count 등을 추출.
 */
function rowsToTraces(rows: DetectionGuidanceLogRow[]): GuidanceTraceRow[] {
  return rows
    .map((row): GuidanceTraceRow | null => {
      const objects = parseTrackedObjects(row.detected_objects_json);
      const obj = pickPrimaryObject(objects);
      const trigger = inferTriggerReason(row, obj);
      // 위험도: 반사는 항상 high, 인지는 tts_text가 비어있지 않으면 risk_level 추정
      let riskLevel = "unknown";
      if (row.stream_type === "reflex") {
        riskLevel = "high";
      } else if (obj?.risk_level) {
        riskLevel = obj.risk_level;
      } else {
        // 인지 경로는 log에 risk_level이 없으므로 stream_type으로 추정
        riskLevel = "mid";
      }
      const text = row.tts_text ?? "";
      const inferredClassName = obj?.class_name
        ? obj.class_name
        : (() => {
            if (text.includes("경로") || text.includes("회전") || text.includes("방향") || text.includes("우회")) {
              return "[GPS 내비게이션]";
            }
            if (text.includes("직진") || text.includes("안전") || text.includes("정상")) {
              return "[정기 안전안내]";
            }
            if (text.includes("연결") || text.includes("서버") || text.includes("시작") || text.includes("종료")) {
              return "[시스템 알림]";
            }
            return "[일반 안내]";
          })();

      return {
        log_id: row.log_id,
        detected_at: row.detected_at,
        stream_type: row.stream_type,
        track_id: obj?.track_id ?? null,
        class_name: inferredClassName,
        hit_count: obj?.hit_count ?? 0,
        direction: obj?.direction ?? "-",
        risk_level: riskLevel,
        trigger_reason: trigger,
        tts_text: row.tts_text,
      };
    })
    .filter((r): r is GuidanceTraceRow => r !== null)
    .slice(0, MAX_TRACE_ROWS);
}

/**
 * track_id에서 일관된 색상을 생성한다 (해시 기반).
 * 같은 track_id는 항상 같은 색상을 받아 운영자가 객체를 시각적으로 추적할 수 있다.
 */
const TRACK_COLORS = [
  "#00D2FF", // tech-blue
  "#39FF14", // op-green
  "#F9B700", // gildang-yellow
  "#FF6B6B", // soft red
  "#BD93F9", // purple
  "#FF79C6", // pink
  "#8BE9FD", // cyan
  "#50FA7B", // bright green
];

function trackColor(trackId: string | null): string {
  if (!trackId) return "var(--color-text-dim)";
  let hash = 0;
  for (let i = 0; i < trackId.length; i++) {
    hash = (hash * 31 + trackId.charCodeAt(i)) | 0;
  }
  return TRACK_COLORS[Math.abs(hash) % TRACK_COLORS.length];
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function GuidanceTraceTimeline({
  rows,
}: {
  rows: DetectionGuidanceLogRow[];
}) {
  const traces = useMemo(() => rowsToTraces(rows), [rows]);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>발화 추적 타임라인</h2>
        <span className="panel-kicker">
          트랙 ID별 발화 트리거 ({traces.length}건)
        </span>
      </div>
      <div className="table-wrap">
        {traces.length === 0 ? (
          <div className="placeholder-box">발화 이력 대기 중</div>
        ) : (
          <table className="trace-timeline-table">
            <thead>
              <tr>
                <th>시간</th>
                <th>트랙</th>
                <th>클래스</th>
                <th>Hit</th>
                <th>방향</th>
                <th>위험도</th>
                <th>경로</th>
                <th>트리거</th>
                <th>발화문</th>
              </tr>
            </thead>
            <tbody>
              {traces.map((t) => {
                const color = trackColor(t.track_id);
                return (
                  <tr key={t.log_id}>
                    <td className="trace-time">{formatTime(t.detected_at)}</td>
                    <td>
                      <span
                        className="track-badge"
                        style={{
                          color: color,
                          borderColor: color,
                        }}
                      >
                        {t.track_id ? `#${t.track_id}` : "-"}
                      </span>
                    </td>
                    <td className="trace-class">{t.class_name}</td>
                    <td className="trace-hit">
                      {t.hit_count > 0 ? t.hit_count : "-"}
                    </td>
                    <td className="trace-dir">{t.direction}</td>
                    <td>
                      <span className={`risk-pill risk-${t.risk_level}`}>
                        {t.risk_level}
                      </span>
                    </td>
                    <td>
                      <span className={`stream-pill stream-${t.stream_type}`}>
                        {t.stream_type === "reflex" ? "반사" : "인지"}
                      </span>
                    </td>
                    <td className="trace-trigger">{t.trigger_reason}</td>
                    <td className="trace-tts">{t.tts_text}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      {/* 발표/면접 포인트:
          이 패널은 "어떤 트랙 ID의 객체가 어떤 행동(연속 히트, 접근, 이탈)을 했을 때
          어떤 발화가 나왔는지"를 한눈에 추적하기 위한 관제 전용 뷰입니다.
          DetectionGuidanceLogTable이 사후 이력의 전체 상세(썸네일, 오탐 판정 등)를
          담당한다면, 이 타임라인은 발화 원인-결과 인과 관계에 집중합니다. */}
    </section>
  );
}
