import { useEffect, useMemo, useRef, useState } from "react";
import type { DetectionGuidanceLogRow, LatencyStages } from "../types/monitor";
import { eventFrameUrl } from "../api/useDetectionLogs";

// 발표/면접 포인트:
// - 이 컴포넌트는 실시간 SSE DetectionFeed가 아니라,
//   detection_guidance_logs 테이블 기반 history/log table입니다.
// - frame_path가 있는 행은 이벤트 발생 시점 프레임 이미지를 함께 표시해
//   오탐 여부 판별과 안내 발화 당시 상황 확인에 사용합니다.
// - bbox는 이미지에 굽지 않고 detected_objects_json 좌표로 오버레이 렌더링합니다.
//   원본 이미지를 보존해야 임계값/모델을 바꿔 재검증할 수 있기 때문입니다.
// - 썸네일/상세 이미지를 클릭하면 라이트박스(확대 보기)가 열립니다.

const LOG_IMAGE_ROTATE_DEG: number = 90;

function getDisplayBBox(
  bbox: { x: number; y: number; w: number; h: number },
  natural: { w: number; h: number },
): { leftPct: number; topPct: number; widthPct: number; heightPct: number } {
  const { x, y, w, h } = bbox;
  const srcW = natural.w;
  const srcH = natural.h;

  if (LOG_IMAGE_ROTATE_DEG === 0) {
    return {
      leftPct: (x / srcW) * 100,
      topPct: (y / srcH) * 100,
      widthPct: (w / srcW) * 100,
      heightPct: (h / srcH) * 100,
    };
  }

  // 왼쪽으로 90도 꺾여 들어오는 프레임(Android 등)을 모바일 시점(CW 90도)으로 보정
  const rotatedX = srcH - (y + h);
  const rotatedY = x;
  const rotatedW = h;
  const rotatedH = w;
  const dstW = srcH;
  const dstH = srcW;

  return {
    leftPct: (rotatedX / dstW) * 100,
    topPct: (rotatedY / dstH) * 100,
    widthPct: (rotatedW / dstW) * 100,
    heightPct: (rotatedH / dstH) * 100,
  };
}

function getColorForClass(className: string): string {
  const c = className.toLowerCase();
  if (c.includes("person") || c.includes("pedestrian")) return "#10b981"; // Emerald Green
  if (c.includes("car") || c.includes("truck") || c.includes("bus") || c.includes("motorcycle") || c.includes("vehicle")) return "#ef4444"; // Vivid Red
  if (c.includes("bollard") || c.includes("pole") || c.includes("tree") || c.includes("obstacle") || c.includes("barrier")) return "#f59e0b"; // Alert Amber
  if (c.includes("caution") || c.includes("warning") || c.includes("danger") || c.includes("construction")) return "#ec4899"; // Pink/Magenta
  if (c.includes("crosswalk") || c.includes("sidewalk") || c.includes("walkway")) return "#3b82f6"; // Blue
  return "#8b5cf6"; // Purple
}

interface LoggedDetection {
  track_id?: string | null;
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

// 탐지 시각을 한국 표준시(KST) 기준 "YYYY-MM-DD HH:mm:ss"로 고정 표기합니다.
// 운영자 브라우저의 로케일/타임존 설정과 무관하게 항상 동일한 형식으로 보이도록
// Intl.DateTimeFormat에 timeZone을 명시적으로 지정합니다(toLocaleString 기본값은
// 브라우저 로케일에 따라 형식이 들쭉날쭉해 로그 대조가 어려웠습니다).
const koreanDateTimeFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

function formatDetectedAt(iso: string): string {
  const parts = koreanDateTimeFormatter.formatToParts(new Date(iso));
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}:${get("second")}`;
}

function parseLatency(json: string | null): LatencyStages {
  if (!json) return {};
  try {
    const parsed = JSON.parse(json);
    return typeof parsed === "object" && parsed !== null ? (parsed as LatencyStages) : {};
  } catch {
    return {};
  }
}

// 실기기 -> STT/추론 -> RAG -> LLM -> TTS -> DB저장 순서로 고정 표시한다.
// 각 로그는 실제로 경유한 스테이지 키만 latency_json에 담겨 있으므로(반사 경로는
// decode/inference/total뿐) 없는 키는 자동으로 생략된다.
const LATENCY_STAGE_ORDER: Array<[keyof LatencyStages, string]> = [
  ["decode_ms", "디코딩"],
  ["stt_ms", "STT"],
  ["inference_ms", "추론"],
  ["rag_ms", "RAG"],
  ["llm_ms", "LLM"],
  ["tts_ms", "TTS"],
  ["db_save_ms", "DB저장"],
  ["total_ms", "총합"],
];

/** 스테이지별 ms를 칩 형태로 나열합니다. total_ms는 강조 표시합니다. */
function LatencyBadges({ latencyJson }: { latencyJson: string | null }) {
  const stages = parseLatency(latencyJson);
  const entries = LATENCY_STAGE_ORDER.filter(([key]) => typeof stages[key] === "number");
  if (entries.length === 0) return <span className="latency-empty">-</span>;
  return (
    <span className="latency-badges">
      {entries.map(([key, label]) => (
        <span
          key={key}
          className={key === "total_ms" ? "latency-chip latency-chip-total" : "latency-chip"}
        >
          {label} {stages[key]!.toFixed(0)}ms
        </span>
      ))}
    </span>
  );
}

const STREAM_LABEL: Record<string, string> = {
  reflex: "반사",
  cognitive: "인지",
  unknown: "미분류",
};

type StreamFilter = "all" | "reflex" | "cognitive";

const STREAM_FILTER_LABEL: Record<StreamFilter, string> = {
  all: "전체",
  cognitive: "인지",
  reflex: "반사",
};

/** 반사/인지/미분류를 한눈에 구분하는 배지. */
function StreamBadge({ streamType }: { streamType: string }) {
  const known = streamType in STREAM_LABEL ? streamType : "unknown";
  return (
    <span className={`stream-pill stream-${known}`}>
      {STREAM_LABEL[known]}
    </span>
  );
}

/** 오탐 판정 배지 */
function FalsePositiveBadge({ value }: { value: boolean | null }) {
  if (value === null) return <span className="fp-pill fp-unmarked">미판정</span>;
  if (value) return <span className="fp-pill fp-true">오탐 (FP)</span>;
  return <span className="fp-pill fp-false">정탐 (TP)</span>;
}

/** 프레임 이미지 위에 bbox를 비율 좌표로 오버레이합니다. */
function FrameWithOverlay({
  src,
  detections,
  className,
  onClick,
}: {
  src: string;
  detections: LoggedDetection[];
  className?: string;
  onClick?: () => void;
}) {
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [isImageBroken, setIsImageBroken] = useState(false);
  const boxes = detections.filter(
    (det) => det.bbox && det.bbox.w > 0 && det.bbox.h > 0,
  );

  return (
    <div
      className={`frame-overlay-wrap${className ? ` ${className}` : ""}${isImageBroken ? " frame-overlay-broken" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") onClick();
            }
          : undefined
      }
    >
      <img
        src={src}
        alt="이벤트 프레임"
        className="frame-overlay-image live-feed-rotated"
        style={{ transform: `rotate(${LOG_IMAGE_ROTATE_DEG}deg)` }}
        onLoad={(event) => {
          const img = event.currentTarget;
          setIsImageBroken(false);
          setNatural({ w: img.naturalWidth, h: img.naturalHeight });
        }}
        onError={() => {
          setIsImageBroken(true);
          setNatural(null);
        }}
      />
      {natural &&
        boxes.map((det, index) => {
          const { x, y, w, h } = det.bbox!;
          const className = det.class_name ?? "unknown";
          const color = getColorForClass(className);
          const displayBBox = getDisplayBBox({ x, y, w, h }, natural);
          return (
            <div
              key={det.track_id ?? `${className}-${index}`}
              className="frame-overlay-box"
              style={{
                left: `${displayBBox.leftPct}%`,
                top: `${displayBBox.topPct}%`,
                width: `${displayBBox.widthPct}%`,
                height: `${displayBBox.heightPct}%`,
                borderColor: color,
                boxShadow: `0 0 6px ${color}`,
              }}
            >
              <span
                className="frame-overlay-label"
                style={{
                  backgroundColor: color,
                  color: "#000000",
                  fontWeight: 900
                }}
              >
                {(det.class_name ?? "?").toUpperCase()}
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

/** 이미지 확대 보기 모달. 배경 클릭/닫기 버튼/Esc로 닫습니다. */
function FrameLightbox({
  row,
  token,
  onUpdateFalsePositive,
  onClose,
}: {
  row: DetectionGuidanceLogRow;
  token: string;
  onUpdateFalsePositive?: (logId: number, falsePositive: boolean | null) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div
      className="lightbox-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="이벤트 프레임 확대 보기"
      onClick={onClose}
    >
      <div className="lightbox-content" onClick={(event) => event.stopPropagation()}>
        <div className="lightbox-header">
          <button
            type="button"
            className="lightbox-close"
            onClick={onClose}
            aria-label="닫기"
          >
            닫기 (Esc)
          </button>
        </div>
        <div className="lightbox-summary frame-detail-header">
          <div className="frame-detail-headline">
            <strong>{row.event_id}</strong>
            <StreamBadge streamType={row.stream_type} />
            <FalsePositiveBadge value={row.false_positive} />
          </div>

          <div className="frame-detail-grid">
            <div className="frame-detail-item">
              <span className="frame-detail-label">감지 시각</span>
              <span className="frame-detail-value">{formatDetectedAt(row.detected_at)}</span>
            </div>
            <div className="frame-detail-item">
              <span className="frame-detail-label">지연 스테이지</span>
              <div className="frame-detail-value">
                <LatencyBadges latencyJson={row.latency_json} />
              </div>
            </div>
            <div className="frame-detail-item frame-detail-item-full">
              <span className="frame-detail-label">TTS 안내문</span>
              <span className="frame-detail-value">{row.tts_text}</span>
            </div>
          </div>

          <div className="frame-detail-actions">
            <button
              type="button"
              className={`fp-btn ${row.false_positive === false ? "fp-btn-active-false" : ""}`}
              onClick={() => onUpdateFalsePositive?.(row.log_id, false)}
            >
              정탐 판정
            </button>
            <button
              type="button"
              className={`fp-btn ${row.false_positive === true ? "fp-btn-active-true" : ""}`}
              onClick={() => onUpdateFalsePositive?.(row.log_id, true)}
            >
              오탐 판정
            </button>
            {row.false_positive !== null && (
              <button
                type="button"
                className="fp-btn"
                onClick={() => onUpdateFalsePositive?.(row.log_id, null)}
              >
                판정 취소
              </button>
            )}
          </div>
        </div>
        <div className="frame-detail-image">
          <FrameWithOverlay
            src={eventFrameUrl(row.event_id!, token)}
            detections={parseDetections(row.detected_objects_json)}
            className="frame-overlay-lightbox"
          />
        </div>
      </div>
    </div>
  );
}

export function DetectionGuidanceLogTable({
  rows,
  token,
  onUpdateFalsePositive,
  onRefresh,
  refreshing,
  live,
  page = 0,
  pageSize = 10,
  totalCount,
  onPrevPage,
  onNextPage,
}: {
  rows: DetectionGuidanceLogRow[];
  token?: string | null;
  onUpdateFalsePositive?: (logId: number, falsePositive: boolean | null) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
  live?: boolean;
  // 2026-07-12: 서버 페이지네이션으로 전환 - rows는 이미 서버가 offset/limit으로 잘라
  // 보낸 "현재 페이지" 데이터라 여기서 다시 슬라이싱하지 않는다. 페이지 이동은
  // onPrevPage/onNextPage로 부모(App.tsx)에 위임해 실제 REST 재조회를 트리거한다.
  page?: number;
  pageSize?: number;
  totalCount?: number;
  onPrevPage?: () => void;
  onNextPage?: () => void;
}) {
  const [selectedLogId, setSelectedLogId] = useState<number | null>(null);
  const [lightboxLogId, setLightboxLogId] = useState<number | null>(null);
  const [streamFilter, setStreamFilter] = useState<StreamFilter>("all");
  const [isStreamFilterOpen, setIsStreamFilterOpen] = useState(false);
  const streamFilterRef = useRef<HTMLDivElement | null>(null);
  const filteredRows = useMemo(
    () =>
      rows.filter(
        (row) =>
          streamFilter === "all" ||
          (streamFilter === "reflex" && row.stream_type === "reflex") ||
          (streamFilter === "cognitive" && row.stream_type === "cognitive"),
      ),
    [rows, streamFilter],
  );
  const totalPages = Math.max(1, Math.ceil((totalCount ?? rows.length) / pageSize));
  const selected = filteredRows.find((row) => row.log_id === selectedLogId) ?? null;
  const lightboxRow = filteredRows.find((row) => row.log_id === lightboxLogId) ?? null;
  const canShowFrame = (row: DetectionGuidanceLogRow) =>
    Boolean(token && row.event_id && row.frame_path);

  useEffect(() => {
    if (selectedLogId !== null && !filteredRows.some((row) => row.log_id === selectedLogId)) {
      setSelectedLogId(null);
    }
    if (lightboxLogId !== null && !filteredRows.some((row) => row.log_id === lightboxLogId)) {
      setLightboxLogId(null);
    }
  }, [filteredRows, selectedLogId, lightboxLogId]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!streamFilterRef.current) return;
      if (!streamFilterRef.current.contains(event.target as Node)) {
        setIsStreamFilterOpen(false);
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  return (
    <section className="panel panel-table">
      <div className="panel-header">
        <h2>Detection Guidance Log</h2>
        <div className="panel-header-actions">
          <button
            type="button"
            className="refresh-btn"
            onClick={() => onRefresh?.()}
            disabled={refreshing}
          >
            {refreshing ? "새로고침 중..." : "새로고침"}
          </button>
          <span className="panel-kicker">
            {live ? (
              <>
                <span className="latency-live-dot" aria-hidden="true" />
                실시간 이력 로그
              </>
            ) : (
              "이력 로그"
            )}
          </span>
        </div>
      </div>

      <div className="stream-filter-row" ref={streamFilterRef}>
        <button
          type="button"
          className="stream-filter-trigger"
          aria-haspopup="listbox"
          aria-expanded={isStreamFilterOpen}
          onClick={() => setIsStreamFilterOpen((prev) => !prev)}
        >
          스트림 선택: {STREAM_FILTER_LABEL[streamFilter]}
          <span className="stream-filter-caret" aria-hidden="true">
            {isStreamFilterOpen ? "▲" : "▼"}
          </span>
        </button>

        {isStreamFilterOpen && (
          <div className="stream-filter-menu" role="listbox" aria-label="스트림 필터 목록">
            {(["all", "cognitive", "reflex"] as StreamFilter[]).map((option) => (
              <button
                key={option}
                type="button"
                role="option"
                aria-selected={streamFilter === option}
                className={`stream-filter-option ${streamFilter === option ? "stream-filter-option-active" : ""}`}
                onClick={() => {
                  setStreamFilter(option);
                  setIsStreamFilterOpen(false);
                }}
              >
                {STREAM_FILTER_LABEL[option]}
              </button>
            ))}
          </div>
        )}
      </div>

      {filteredRows.length === 0 ? (
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
                <th>지연(ms)</th>
                <th>오탐 판정</th>
                <th>사용자</th>
                <th>기기</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => {
                const totalMs = parseLatency(row.latency_json).total_ms;
                return (
                  <tr
                    key={row.log_id}
                    className={row.log_id === selectedLogId ? "row-selected" : undefined}
                    tabIndex={0}
                    onClick={() =>
                      setSelectedLogId(row.log_id === selectedLogId ? null : row.log_id)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedLogId(row.log_id === selectedLogId ? null : row.log_id);
                      }
                    }}
                  >
                    <td>
                      {canShowFrame(row) ? (
                        <button
                          type="button"
                          className="frame-thumb-btn"
                          onClick={(event) => {
                            event.stopPropagation();
                            setLightboxLogId(row.log_id);
                          }}
                        >
                          <img
                            src={eventFrameUrl(row.event_id!, token!)}
                            alt="이벤트 썸네일 (클릭하면 확대)"
                            className="frame-thumb"
                            loading="lazy"
                          />
                        </button>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td>{formatDetectedAt(row.detected_at)}</td>
                    <td>
                      <StreamBadge streamType={row.stream_type} />
                    </td>
                    <td>{row.event_id ?? "-"}</td>
                    <td>{row.tts_text}</td>
                    <td className="latency-total-cell">
                      {typeof totalMs === "number" ? totalMs.toFixed(0) : "-"}
                    </td>
                    <td>
                      <FalsePositiveBadge value={row.false_positive} />
                    </td>
                    <td>{row.user_id ?? "-"}</td>
                    <td>{row.device_id ?? "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <nav className="log-pagination" aria-label="이력 페이지 이동">
          <button
            type="button"
            className="page-btn"
            onClick={() => onPrevPage?.()}
            disabled={page === 0}
          >
            이전
          </button>
          <span className="page-indicator">
            {page + 1} / {totalPages} 페이지 · 전체 {totalCount ?? rows.length}건
          </span>
          <button
            type="button"
            className="page-btn"
            onClick={() => onNextPage?.()}
            disabled={page >= totalPages - 1}
          >
            다음
          </button>
        </nav>
      )}

      {selected && canShowFrame(selected) && (
        <div className="frame-detail">
          <div className="frame-detail-body">
            <div className="frame-detail-header">
              <div className="frame-detail-headline">
                <strong>{selected.event_id}</strong>
                <StreamBadge streamType={selected.stream_type} />
                <FalsePositiveBadge value={selected.false_positive} />
              </div>

              <div className="frame-detail-grid">
                <div className="frame-detail-item">
                  <span className="frame-detail-label">감지 시각</span>
                  <span className="frame-detail-value">{formatDetectedAt(selected.detected_at)}</span>
                </div>
                <div className="frame-detail-item">
                  <span className="frame-detail-label">지연 스테이지</span>
                  <div className="frame-detail-value">
                    <LatencyBadges latencyJson={selected.latency_json} />
                  </div>
                </div>
                <div className="frame-detail-item frame-detail-item-full">
                  <span className="frame-detail-label">TTS 안내문</span>
                  <span className="frame-detail-value">{selected.tts_text}</span>
                </div>
              </div>

              <div className="frame-detail-actions">
                <button
                  type="button"
                  className={`fp-btn ${selected.false_positive === false ? "fp-btn-active-false" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onUpdateFalsePositive?.(selected.log_id, false);
                  }}
                >
                  정탐 판정
                </button>
                <button
                  type="button"
                  className={`fp-btn ${selected.false_positive === true ? "fp-btn-active-true" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onUpdateFalsePositive?.(selected.log_id, true);
                  }}
                >
                  오탐 판정
                </button>
                {selected.false_positive !== null && (
                  <button
                    type="button"
                    className="fp-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onUpdateFalsePositive?.(selected.log_id, null);
                    }}
                  >
                    판정 취소
                  </button>
                )}
              </div>
              <div className="frame-detail-image">
                <FrameWithOverlay
                  src={eventFrameUrl(selected.event_id!, token!)}
                  detections={parseDetections(selected.detected_objects_json)}
                  onClick={() => setLightboxLogId(selected.log_id)}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {lightboxRow && canShowFrame(lightboxRow) && token && (
        <FrameLightbox
          row={lightboxRow}
          token={token}
          onUpdateFalsePositive={onUpdateFalsePositive}
          onClose={() => setLightboxLogId(null)}
        />
      )}
    </section>
  );
}
