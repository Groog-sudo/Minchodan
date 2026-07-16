import { useEffect, useMemo, useRef, useState } from "react";
import type { DetectionGuidanceLogRow, LatencyStages, PipelineDebug } from "../types/monitor";
import { eventFrameUrl } from "../api/useDetectionLogs";

// 발표/면접 포인트:
// - 이 컴포넌트는 실시간 SSE DetectionFeed가 아니라,
//   detection_guidance_logs 테이블 기반 history/log table입니다.
// - frame_path가 있는 행은 이벤트 발생 시점 프레임 이미지를 함께 표시해
//   오탐 여부 판별과 안내 발화 당시 상황 확인에 사용합니다.
// - bbox는 이미지에 굽지 않고 detected_objects_json 좌표로 오버레이 렌더링합니다.
//   원본 이미지를 보존해야 임계값/모델을 바꿔 재검증할 수 있기 때문입니다.
// - 썸네일/상세 이미지를 클릭하면 라이트박스(확대 보기)가 열립니다.

// iOS 정자세 JPEG 재배포 후 Live Feed와 동일하게 0.
const LOG_IMAGE_ROTATE_DEG: number = 0;

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

function parsePipelineDebug(raw: string | PipelineDebug | null | undefined): PipelineDebug | null {
  if (!raw) return null;
  if (typeof raw === "object") return raw as PipelineDebug;
  if (typeof raw !== "string") return null;
  try {
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? (parsed as PipelineDebug) : null;
  } catch {
    return null;
  }
}

/** 테이블 한 줄 요약용: STT 전사 / LLM 응답 / 패스트레인 등 핵심 텍스트 추출. */
function summarizePipelineDebug(
  debugJson: string | PipelineDebug | null | undefined,
  detectedObjectsJson: string,
): string {
  const debug = parsePipelineDebug(debugJson);
  if (debug?.response_skipped && debug.stt_transcript) {
    return `[에코 스킵] ${debug.stt_transcript}`;
  }
  if (debug?.stt_transcript) {
    const parts = [debug.stt_transcript];
    if (debug.llm_text && debug.llm_text !== debug.stt_transcript) {
      parts.push(`-> ${debug.llm_text}`);
    } else if (debug.template_text && debug.template_text !== debug.stt_transcript) {
      parts.push(`-> ${debug.template_text}`);
    } else if (debug.response_text && debug.response_text !== debug.stt_transcript) {
      parts.push(`-> ${debug.response_text}`);
    }
    return parts.join(" ");
  }
  if (debug?.llm_text) return debug.llm_text;
  if (debug?.response_text) return debug.response_text;
  if (debug?.detections_summary?.length) {
    const det = debug.detections_summary[0];
    const cls = String(det.class_name ?? "");
    const conf = det.confidence != null ? ` ${det.confidence}` : "";
    return `${cls}${conf}`;
  }
  if (debug?.rag_context) return debug.rag_context.slice(0, 80);

  // pipeline_debug_json 이전 STT 로그 폴백: detected_objects_json.stt_transcript
  try {
    const objs = JSON.parse(detectedObjectsJson);
    if (Array.isArray(objs)) {
      const sttObj = objs.find((o) => o && typeof o === "object" && o.source === "stt");
      if (sttObj?.stt_transcript) return String(sttObj.stt_transcript);
    }
  } catch {
    // ignore
  }
  return "";
}

const PATH_LABEL: Record<string, string> = {
  reflex: "반사",
  cognitive: "인지(비전)",
  stt: "STT 음성",
};

function formatJsonPreview(value: unknown): string {
  try {
    return JSON.stringify(value, null, 0);
  } catch {
    return String(value);
  }
}

function pushDetectionRows(
  rows: Array<{ label: string; value: string; mono?: boolean }>,
  detections: Array<Record<string, unknown>> | undefined,
) {
  if (!detections?.length) return;
  detections.forEach((det, idx) => {
    const cls = String(det.class_name ?? "-");
    const conf = det.confidence != null ? ` conf=${det.confidence}` : "";
    const hit = det.hit_count != null ? ` hit=${det.hit_count}` : "";
    const dir = det.direction ? ` dir=${det.direction}` : "";
    rows.push({
      label: `YOLO 탐지 #${idx + 1}`,
      value: `${cls}${conf}${hit}${dir}`,
      mono: true,
    });
  });
}

function pushSurfaceRows(
  rows: Array<{ label: string; value: string; mono?: boolean }>,
  surfaces: Array<Record<string, unknown>> | undefined,
) {
  if (!surfaces?.length) return;
  surfaces.forEach((surf, idx) => {
    const cls = String(surf.class_name ?? "-");
    const centroid = Array.isArray(surf.centroid) ? ` @${surf.centroid.join(",")}` : "";
    rows.push({
      label: `노면 분할 #${idx + 1}`,
      value: `${cls}${centroid}`,
      mono: true,
    });
  });
}

/** 경로별 파이프라인 중간 텍스트를 관리자 디버그 패널로 표시한다. */
function PipelineDebugPanel({
  debugJson,
  detectedObjectsJson,
}: {
  debugJson: string | PipelineDebug | null | undefined;
  detectedObjectsJson?: string;
}) {
  const debug = parsePipelineDebug(debugJson);
  if (!debug?.path) {
    const fallback = detectedObjectsJson
      ? summarizePipelineDebug(null, detectedObjectsJson)
      : "";
    if (fallback) {
      return (
        <div className="pipeline-debug-panel">
          <div className="pipeline-debug-row">
            <span className="pipeline-debug-label">STT 전사 (메타)</span>
            <span className="pipeline-debug-value mono">{fallback}</span>
          </div>
        </div>
      );
    }
    return <span className="pipeline-debug-empty">파이프라인 디버그 없음 (배포 이전 이력)</span>;
  }

  const rows: Array<{ label: string; value: string; mono?: boolean }> = [];
  const pathLabel = PATH_LABEL[debug.path] ?? debug.path;
  rows.push({ label: "경로", value: pathLabel });

  if (debug.path === "stt") {
    if (debug.generation_mode) rows.push({ label: "생성 모드", value: debug.generation_mode, mono: true });
    if (debug.response_skipped) rows.push({ label: "응답 스킵", value: debug.skip_reason ?? "true", mono: true });
    if (debug.stt_transcript) rows.push({ label: "STT 전사 (Whisper)", value: debug.stt_transcript, mono: true });
    if (debug.bridge_source) rows.push({ label: "브릿지 분기", value: debug.bridge_source, mono: true });
    if (debug.rag_query) rows.push({ label: "RAG 쿼리", value: debug.rag_query, mono: true });
    if (debug.rag_context) rows.push({ label: "RAG 수칙", value: debug.rag_context, mono: true });
    if (debug.rag_results?.length) {
      rows.push({ label: "RAG 검색 결과", value: formatJsonPreview(debug.rag_results), mono: true });
    }
    if (debug.template_text) rows.push({ label: "템플릿 안내문", value: debug.template_text, mono: true });
    if (debug.llm_text) rows.push({ label: "LLM 응답", value: debug.llm_text, mono: true });
    if (debug.response_text && !debug.response_skipped) {
      rows.push({ label: "최종 안내문", value: debug.response_text, mono: true });
    }
    if (typeof debug.used_fallback_llm === "boolean") {
      rows.push({ label: "LLM 폴백", value: debug.used_fallback_llm ? "예" : "아니오" });
    }
  } else if (debug.path === "cognitive") {
    if (debug.generation_mode) rows.push({ label: "생성 모드", value: debug.generation_mode, mono: true });
    if (debug.pipeline_risk_hint) rows.push({ label: "파이프라인 위험도", value: debug.pipeline_risk_hint });
    if (debug.l1_risk_level) rows.push({ label: "L1 분류 위험도", value: debug.l1_risk_level });
    if (debug.detected_classes_ko?.length) {
      rows.push({ label: "탐지 클래스(한글)", value: debug.detected_classes_ko.join(", ") });
    }
    pushDetectionRows(rows, debug.detections_summary);
    pushSurfaceRows(rows, debug.surfaces_summary);
    if (typeof debug.is_departing === "boolean") {
      rows.push({ label: "보도 이탈(프레임)", value: debug.is_departing ? "예" : "아니오" });
    }
    if (typeof debug.is_departing_confirmed === "boolean") {
      rows.push({ label: "보도 이탈(확정)", value: debug.is_departing_confirmed ? "예" : "아니오" });
    }
    if (debug.braille_direction) rows.push({ label: "점자블록 방향", value: debug.braille_direction });
    if (debug.object_ko) rows.push({ label: "객체(한글)", value: debug.object_ko });
    if (debug.clock_direction) rows.push({ label: "시계 방향", value: debug.clock_direction });
    if (debug.distance_class) rows.push({ label: "거리 밴드", value: debug.distance_class });
    if (debug.navigation_guidance) rows.push({ label: "내비 융합 멘트", value: debug.navigation_guidance, mono: true });
    if (debug.rag_query) rows.push({ label: "RAG 쿼리", value: debug.rag_query, mono: true });
    if (debug.rag_context) rows.push({ label: "RAG 수칙", value: debug.rag_context, mono: true });
    if (debug.used_fast_lane && debug.fast_lane_cache_key) {
      rows.push({ label: "패스트 레인 키", value: debug.fast_lane_cache_key, mono: true });
    }
    if (debug.llm_provider) rows.push({ label: "LLM 제공자", value: debug.llm_provider, mono: true });
    if (debug.l2_drafts?.length) {
      debug.l2_drafts.forEach((draft, idx) => {
        rows.push({ label: `L2 초안 #${idx + 1}`, value: draft, mono: true });
      });
    }
    if (debug.llm_text) rows.push({ label: "LLM 응답", value: debug.llm_text, mono: true });
    if (debug.response_text) rows.push({ label: "최종 안내문", value: debug.response_text, mono: true });
    if (typeof debug.l3_verified === "boolean") {
      rows.push({ label: "L3 검증", value: debug.l3_verified ? "통과" : "미통과" });
    }
    if (debug.validation_errors && debug.validation_errors.length > 0) {
      rows.push({ label: "검증 오류", value: debug.validation_errors.join(", "), mono: true });
    }
    if (typeof debug.retry_count === "number" && debug.retry_count > 0) {
      rows.push({ label: "LLM 재시도", value: String(debug.retry_count) });
    }
    if (typeof debug.inference_ms === "number") {
      rows.push({ label: "YOLO 추론(ms)", value: String(debug.inference_ms) });
    }
  } else if (debug.path === "reflex") {
    if (debug.generation_mode) rows.push({ label: "생성 모드", value: debug.generation_mode, mono: true });
    if (debug.alert_id) rows.push({ label: "alert_id", value: debug.alert_id, mono: true });
    if (debug.clip) rows.push({ label: "반사 클립", value: debug.clip, mono: true });
    if (debug.class_name) rows.push({ label: "클래스", value: debug.class_name, mono: true });
    if (debug.risk_level) rows.push({ label: "위험도", value: debug.risk_level });
    if (typeof debug.hit_count === "number") rows.push({ label: "hit_count", value: String(debug.hit_count) });
    if (debug.track_id) rows.push({ label: "track_id", value: debug.track_id, mono: true });
    if (debug.direction) rows.push({ label: "방향", value: debug.direction });
    if (debug.distance) rows.push({ label: "거리", value: debug.distance });
    if (typeof debug.inference_ms === "number") {
      rows.push({ label: "YOLO 추론(ms)", value: String(debug.inference_ms) });
    }
    pushDetectionRows(rows, debug.detections_summary);
  }

  return (
    <div className="pipeline-debug-panel">
      {rows.map((row, index) => (
        <div key={`${row.label}-${index}`} className="pipeline-debug-row">
          <span className="pipeline-debug-label">{row.label}</span>
          <span className={row.mono ? "pipeline-debug-value mono" : "pipeline-debug-value"}>
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
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

const PAGE_BUTTON_WINDOW = 10;

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
            <div className="frame-detail-item frame-detail-item-full">
              <span className="frame-detail-label">파이프라인 텍스트</span>
              <div className="frame-detail-value">
                <PipelineDebugPanel
                  debugJson={row.pipeline_debug_json}
                  detectedObjectsJson={row.detected_objects_json}
                />
              </div>
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
  streamFilter = "all",
  onStreamFilterChange,
  page = 0,
  pageSize = 10,
  totalCount,
  onPrevPage,
  onNextPage,
  onSetPage,
}: {
  rows: DetectionGuidanceLogRow[];
  token?: string | null;
  onUpdateFalsePositive?: (logId: number, falsePositive: boolean | null) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
  live?: boolean;
  streamFilter?: StreamFilter;
  onStreamFilterChange?: (filter: StreamFilter) => void;
  // 2026-07-12: 서버 페이지네이션으로 전환 - rows는 이미 서버가 offset/limit으로 잘라
  // 보낸 "현재 페이지" 데이터라 여기서 다시 슬라이싱하지 않는다. 페이지 이동은
  // onPrevPage/onNextPage로 부모(App.tsx)에 위임해 실제 REST 재조회를 트리거한다.
  page?: number;
  pageSize?: number;
  totalCount?: number;
  onPrevPage?: () => void;
  onNextPage?: () => void;
  onSetPage?: (page: number) => void;
}) {
  const [selectedLogId, setSelectedLogId] = useState<number | null>(null);
  const [lightboxLogId, setLightboxLogId] = useState<number | null>(null);
  const [isStreamFilterOpen, setIsStreamFilterOpen] = useState(false);
  const [isPageSearchOpen, setIsPageSearchOpen] = useState(false);
  const [pageSearchInput, setPageSearchInput] = useState("");
  const streamFilterRef = useRef<HTMLDivElement | null>(null);
  const pageSearchRef = useRef<HTMLDivElement | null>(null);
  const displayRows = useMemo(
    () =>
      [...rows]
        .filter(
          (row) =>
            streamFilter === "all" ||
            (streamFilter === "reflex" && row.stream_type === "reflex") ||
            (streamFilter === "cognitive" && row.stream_type === "cognitive"),
        )
        .sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime()),
    [rows, streamFilter],
  );
  const totalPages = Math.max(1, Math.ceil((totalCount ?? rows.length) / pageSize));
  const disablePaginationControls = (totalCount ?? rows.length) <= 11;
  const pageWindowStart = Math.floor(page / PAGE_BUTTON_WINDOW) * PAGE_BUTTON_WINDOW;
  const pageWindowEnd = Math.min(totalPages, pageWindowStart + PAGE_BUTTON_WINDOW);
  const visiblePages = Array.from(
    { length: pageWindowEnd - pageWindowStart },
    (_, index) => pageWindowStart + index,
  );
  const selected = displayRows.find((row) => row.log_id === selectedLogId) ?? null;
  const lightboxRow = displayRows.find((row) => row.log_id === lightboxLogId) ?? null;
  const canShowFrame = (row: DetectionGuidanceLogRow) =>
    Boolean(token && row.event_id && row.frame_path);

  useEffect(() => {
    if (selectedLogId !== null && !displayRows.some((row) => row.log_id === selectedLogId)) {
      setSelectedLogId(null);
    }
    if (lightboxLogId !== null && !displayRows.some((row) => row.log_id === lightboxLogId)) {
      setLightboxLogId(null);
    }
  }, [displayRows, selectedLogId, lightboxLogId]);

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

  useEffect(() => {
    if (!isPageSearchOpen) {
      return;
    }

    const handleOutsideClick = (event: MouseEvent) => {
      if (!pageSearchRef.current) {
        return;
      }
      if (!pageSearchRef.current.contains(event.target as Node)) {
        setIsPageSearchOpen(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isPageSearchOpen]);

  const jumpToPage = () => {
    const parsed = Number.parseInt(pageSearchInput.trim(), 10);
    if (Number.isNaN(parsed)) {
      return;
    }
    const clampedPage = Math.min(totalPages, Math.max(1, parsed));
    onSetPage?.(clampedPage - 1);
    setPageSearchInput("");
    setIsPageSearchOpen(false);
  };

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
                  onStreamFilterChange?.(option);
                  onSetPage?.(0);
                  setIsStreamFilterOpen(false);
                }}
              >
                {STREAM_FILTER_LABEL[option]}
              </button>
            ))}
          </div>
        )}
      </div>

      {displayRows.length === 0 ? (
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
                <th>파이프라인 텍스트</th>
                <th>TTS 안내문</th>
                <th>지연(ms)</th>
                <th>오탐 판정</th>
                <th>사용자</th>
                <th>기기</th>
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row) => {
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
                    <td className="pipeline-preview-cell">
                      {summarizePipelineDebug(row.pipeline_debug_json, row.detected_objects_json) || "-"}
                    </td>
                    <td className="tts-text-cell">{row.tts_text}</td>
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

      <nav className="log-pagination" aria-label="이력 페이지 이동">
        <button
          type="button"
          className="page-btn"
          onClick={() => onPrevPage?.()}
          disabled={disablePaginationControls || page === 0}
          aria-label="이전 페이지"
        >
          ←
        </button>

        <div className="page-number-strip" aria-label="페이지 번호 목록">
          {visiblePages.map((pageIndex) => (
            <button
              key={pageIndex}
              type="button"
              className={`page-btn ${page === pageIndex ? "page-btn-active" : ""}`}
              onClick={() => onSetPage?.(pageIndex)}
              disabled={disablePaginationControls}
            >
              {pageIndex + 1}
            </button>
          ))}

          {pageWindowEnd < totalPages && (
            <>
              <div className="page-search-anchor" ref={pageSearchRef}>
                <button
                  type="button"
                  className={`page-btn page-jump-btn ${isPageSearchOpen ? "page-btn-active" : ""}`}
                  onClick={() => setIsPageSearchOpen((open) => !open)}
                  disabled={disablePaginationControls}
                  aria-label="페이지 번호 검색"
                >
                  ...
                </button>

                {isPageSearchOpen && (
                  <div className="page-search-popover">
                    <label className="page-search-label" htmlFor="log-page-search-input">
                      페이지 번호
                    </label>
                    <div className="page-search-row">
                      <input
                        id="log-page-search-input"
                        type="number"
                        className="page-search-input"
                        min={1}
                        max={totalPages}
                        placeholder={`1-${totalPages}`}
                        value={pageSearchInput}
                        onChange={(event) => setPageSearchInput(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            jumpToPage();
                          }
                        }}
                      />
                      <button type="button" className="page-btn" onClick={jumpToPage}>
                        이동
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <button
                type="button"
                className={`page-btn ${page === totalPages - 1 ? "page-btn-active" : ""}`}
                onClick={() => onSetPage?.(totalPages - 1)}
                disabled={disablePaginationControls}
              >
                {totalPages}
              </button>
            </>
          )}
        </div>

        <button
          type="button"
          className="page-btn"
          onClick={() => onNextPage?.()}
          disabled={disablePaginationControls || page >= totalPages - 1}
          aria-label="다음 페이지"
        >
          →
        </button>
      </nav>

      {selected && (
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
                <div className="frame-detail-item frame-detail-item-full">
                  <span className="frame-detail-label">파이프라인 텍스트</span>
                  <div className="frame-detail-value">
                    <PipelineDebugPanel
                      debugJson={selected.pipeline_debug_json}
                      detectedObjectsJson={selected.detected_objects_json}
                    />
                  </div>
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
              {canShowFrame(selected) && token && (
                <div className="frame-detail-image">
                  <FrameWithOverlay
                    src={eventFrameUrl(selected.event_id!, token)}
                    detections={parseDetections(selected.detected_objects_json)}
                    onClick={() => setLightboxLogId(selected.log_id)}
                  />
                </div>
              )}
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
