import { useMemo, useState } from "react";
import { AiPipelineMonitor } from "../components/AiPipelineMonitor";
import { DetectionFeed } from "../components/DetectionFeed";
import { GuidanceTraceTimeline } from "../components/GuidanceTraceTimeline";
import { RiskEventLog } from "../components/RiskEventLog";
import { SessionStatus } from "../components/SessionStatus";
import { SystemMetrics } from "../components/SystemMetrics";
import { useDetectionLogs } from "../api/useDetectionLogs";
import { DetectionGuidanceLogTable } from "../components/DetectionGuidanceLogTable";
import { LatencySummaryPanel } from "../components/LatencySummaryPanel";
import { LiveCameraFeed } from "../components/LiveCameraFeed";
import { DeviceTelemetryPanel } from "../components/DeviceTelemetryPanel";
import { McpValidationMonitor } from "../components/McpValidationMonitor";
import type { DetectionGuidanceLogRow, MonitorState } from "../types/monitor";
import type { useLiveFeed } from "../api/useLiveFeed";

const DEMO_LOG_STORAGE_DEFAULTS = {
  event_source: "detection",
  stt_transcript_text: null,
  stt_audio_path: null,
  stt_audio_storage_status: "not_applicable",
  stt_audio_format: null,
  stt_audio_size_bytes: null,
  stt_audio_duration_ms: null,
  stt_audio_sha256: null,
  stt_audio_error_code: null,
  stt_audio_consent_at: null,
  stt_audio_expires_at: null,
  writer_instance_id: null,
} satisfies Pick<
  DetectionGuidanceLogRow,
  | "event_source"
  | "stt_transcript_text"
  | "stt_audio_path"
  | "stt_audio_storage_status"
  | "stt_audio_format"
  | "stt_audio_size_bytes"
  | "stt_audio_duration_ms"
  | "stt_audio_sha256"
  | "stt_audio_error_code"
  | "stt_audio_consent_at"
  | "stt_audio_expires_at"
  | "writer_instance_id"
>;

const DEMO_GUIDANCE_LOGS: DetectionGuidanceLogRow[] = [
  {
    ...DEMO_LOG_STORAGE_DEFAULTS,
    log_id: 1,
    event_id: "demo-event-001",
    user_id: 1,
    device_id: 101,
    detected_at: "2026-07-10T10:15:00Z",
    stream_type: "reflex",
    detected_objects_json: '[{"class_name":"scooter","confidence":0.91,"track_id":"3","hit_count":5,"distance":0.4}]',
    tts_text: "[반사 클립] reflex_clips/high_front.wav",
    frame_path: null,
    false_positive: null,
    latency_json: '{"decode_ms":12.3,"inference_ms":58.1,"total_ms":70.4}',
    pipeline_debug_json: '{"path":"reflex","alert_id":"high_obstacle","clip":"reflex_clips/high_front.wav","class_name":"scooter"}',
    created_at: "2026-07-10T10:15:01Z",
  },
  {
    ...DEMO_LOG_STORAGE_DEFAULTS,
    log_id: 2,
    event_id: "demo-event-002",
    user_id: 1,
    device_id: 101,
    detected_at: "2026-07-10T10:15:20Z",
    stream_type: "cognitive",
    detected_objects_json: '[{"class_name":"bollard","confidence":0.88,"track_id":"8","hit_count":12,"direction":"approaching"}]',
    tts_text: "전방 오른쪽에 볼라드가 있습니다. 왼쪽으로 우회하십시오.",
    frame_path: null,
    false_positive: null,
    latency_json: '{"decode_ms":11.2,"inference_ms":60.5,"rag_ms":22.1,"llm_ms":210.3,"tts_ms":180.2,"total_ms":484.3}',
    pipeline_debug_json: '{"path":"cognitive","rag_query":"bollard","rag_context":"볼라드 충돌 시 무릎 부상 위험","generation_mode":"langgraph_l2_l3","llm_text":"전방 오른쪽에 볼라드가 있습니다. 왼쪽으로 우회하십시오.","response_text":"전방 오른쪽에 볼라드가 있습니다. 왼쪽으로 우회하십시오.","l3_verified":true}',
    created_at: "2026-07-10T10:15:21Z",
  },
  {
    ...DEMO_LOG_STORAGE_DEFAULTS,
    log_id: 3,
    event_id: "demo-event-003",
    user_id: 1,
    device_id: 101,
    detected_at: "2026-07-10T10:15:40Z",
    stream_type: "reflex",
    detected_objects_json: '[{"class_name":"crosswalk","confidence":1.0,"alert_id":"surface_crosswalk"}]',
    tts_text: "[반사 클립] reflex_clips/surface_alert.wav",
    frame_path: null,
    false_positive: null,
    latency_json: '{"decode_ms":10.5,"inference_ms":52.4,"total_ms":62.9}',
    pipeline_debug_json: null,
    created_at: "2026-07-10T10:15:41Z",
  },
  {
    ...DEMO_LOG_STORAGE_DEFAULTS,
    log_id: 4,
    event_id: "demo-event-004",
    user_id: 1,
    device_id: 101,
    detected_at: "2026-07-10T10:16:00Z",
    stream_type: "cognitive",
    detected_objects_json: '[]',
    tts_text: "약 50미터 앞 우회전입니다. 경로를 유지하십시오.",
    frame_path: null,
    false_positive: null,
    latency_json: '{"decode_ms":10.2,"inference_ms":54.1,"rag_ms":18.2,"llm_ms":195.4,"tts_ms":150.2,"total_ms":428.1}',
    pipeline_debug_json: null,
    created_at: "2026-07-10T10:16:01Z",
  },
  {
    ...DEMO_LOG_STORAGE_DEFAULTS,
    log_id: 5,
    event_id: "demo-event-005",
    user_id: 1,
    device_id: 101,
    detected_at: "2026-07-10T10:16:20Z",
    stream_type: "cognitive",
    detected_objects_json: '[]',
    tts_text: "경로가 안전합니다. 계속 직진하십시오.",
    frame_path: null,
    false_positive: null,
    latency_json: '{"decode_ms":10.1,"inference_ms":53.2,"rag_ms":19.4,"llm_ms":201.2,"tts_ms":160.4,"total_ms":444.3}',
    pipeline_debug_json: null,
    created_at: "2026-07-10T10:16:21Z",
  },
];

type DashboardWidgetKey =
  | "latency"
  | "liveFeed"
  | "telemetry"
  | "timeline"
  | "guidanceLog"
  | "riskLog";

const DASHBOARD_WIDGETS: Array<{ key: DashboardWidgetKey; label: string; fullWidth?: boolean }> = [
  { key: "latency", label: "파이프라인 지연 요약", fullWidth: true },
  { key: "liveFeed", label: "Live Feed" },
  { key: "telemetry", label: "Device Telemetry & Control" },
  { key: "timeline", label: "발화 추적 타임라인", fullWidth: true },
  { key: "guidanceLog", label: "Detection Guidance Log", fullWidth: true },
  { key: "riskLog", label: "RiskEventLog", fullWidth: true },
];

const DEFAULT_DASHBOARD_WIDGET_ORDER: DashboardWidgetKey[] = [
  "latency",
  "liveFeed",
  "telemetry",
  "timeline",
  "guidanceLog",
  "riskLog",
];

export function DashboardPage({
  token,
  state,
  streamUrl,
  liveFeed,
  isDemoMode,
}: {
  token: string;
  state: MonitorState;
  streamUrl: string;
  liveFeed: ReturnType<typeof useLiveFeed>;
  isDemoMode: boolean;
}) {
  type WidgetMenuMode = "root" | "add";
  const [widgetOrder, setWidgetOrder] = useState<DashboardWidgetKey[]>(
    DEFAULT_DASHBOARD_WIDGET_ORDER,
  );
  const [isWidgetPickerOpen, setIsWidgetPickerOpen] = useState(false);
  const [widgetMenuMode, setWidgetMenuMode] = useState<WidgetMenuMode>("root");
  const [openWidgetOptionKey, setOpenWidgetOptionKey] = useState<DashboardWidgetKey | null>(null);
  const [movingWidgetKey, setMovingWidgetKey] = useState<DashboardWidgetKey | null>(null);
  const [dragOverWidgetKey, setDragOverWidgetKey] = useState<DashboardWidgetKey | null>(null);

  const { imageUrl, latestDetections, connected: liveFeedConnected, latencyEvents, guidanceLogEvents, lastGps } =
    liveFeed;

  // 사후 이력 로그는 REST로 페이지 단위(offset/limit) 조회한다 (frame_path 이미지 포함).
  // 2026-07-12: 클라이언트가 최근 50건만 받아 그 안에서 슬라이싱하던 방식은 하단 건수
  // 표시가 DB 전체 건수와 안 맞았다 - 서버가 X-Total-Count로 전체 건수를 내려주고,
  // 페이지를 넘길 때마다 해당 offset을 다시 조회하는 진짜 서버 페이지네이션으로 전환.
  const LOG_PAGE_SIZE = 10;
  const [logPage, setLogPage] = useState(0);
  const [logStreamFilter, setLogStreamFilter] = useState<"all" | "reflex" | "cognitive">("all");
  const {
    rows: fetchedLogs,
    totalCount: logsTotalCount,
    updateLogFalsePositive,
    refresh: refreshLogs,
    loading: logsLoading,
  } = useDetectionLogs(token, logPage, LOG_PAGE_SIZE, logStreamFilter);

  const demoFilteredLogs = useMemo(() => {
    const base =
      logStreamFilter === "all"
        ? DEMO_GUIDANCE_LOGS
        : DEMO_GUIDANCE_LOGS.filter((row) => row.stream_type === logStreamFilter);
    return [...base].sort(
      (a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
    );
  }, [logStreamFilter]);

  const demoTotalCount = demoFilteredLogs.length;

  // REST 페이지(fetchedLogs)와 WS 실시간 푸시(guidanceLogEvents)를 log_id 기준으로 병합한다.
  // 1페이지(최신)에서만 병합한다 - 2페이지 이후는 특정 offset의 과거 스냅샷이라 실시간
  // 이벤트가 끼어들면 페이지 경계가 흔들린다. 병합 후에도 페이지 크기를 유지하도록 자른다.
  const detectionGuidanceLogs = useMemo(() => {
    if (isDemoMode) {
      const offset = logPage * LOG_PAGE_SIZE;
      return demoFilteredLogs.slice(offset, offset + LOG_PAGE_SIZE);
    }
    if (logStreamFilter !== "all") {
      return fetchedLogs;
    }
    if (logPage !== 0) {
      return fetchedLogs;
    }
    const byId = new Map<number, DetectionGuidanceLogRow>();
    for (const row of fetchedLogs) byId.set(row.log_id, row);
    for (const row of guidanceLogEvents) byId.set(row.log_id, row);
    const merged = Array.from(byId.values())
      .sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime())
      .slice(0, LOG_PAGE_SIZE);
    return merged;
  }, [fetchedLogs, guidanceLogEvents, isDemoMode, logPage, logStreamFilter, demoFilteredLogs]);

  const effectiveTotalCount = isDemoMode ? demoTotalCount : logsTotalCount;
  const availableWidgets = DASHBOARD_WIDGETS.filter((widget) => !widgetOrder.includes(widget.key));

  const removeWidget = (widgetKey: DashboardWidgetKey) => {
    setWidgetOrder((prev) => prev.filter((key) => key !== widgetKey));
    if (movingWidgetKey === widgetKey) {
      setMovingWidgetKey(null);
    }
    setOpenWidgetOptionKey(null);
  };

  const addWidget = (widgetKey: DashboardWidgetKey) => {
    setWidgetOrder((prev) => (prev.includes(widgetKey) ? prev : [...prev, widgetKey]));
    setIsWidgetPickerOpen(false);
    setWidgetMenuMode("root");
  };

  const removeAllWidgets = () => {
    setWidgetOrder([]);
    setIsWidgetPickerOpen(false);
    setWidgetMenuMode("root");
    setOpenWidgetOptionKey(null);
    setMovingWidgetKey(null);
    setDragOverWidgetKey(null);
  };

  const enableMoveMode = (widgetKey: DashboardWidgetKey) => {
    setMovingWidgetKey(widgetKey);
    setDragOverWidgetKey(null);
    setOpenWidgetOptionKey(null);
  };

  const moveWidget = (fromKey: DashboardWidgetKey, toKey: DashboardWidgetKey) => {
    if (fromKey === toKey) {
      return;
    }
    setWidgetOrder((prev) => {
      const fromIndex = prev.indexOf(fromKey);
      const toIndex = prev.indexOf(toKey);
      if (fromIndex < 0 || toIndex < 0) {
        return prev;
      }
      const next = [...prev];
      const [dragged] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, dragged);
      return next;
    });
  };

  const renderWidget = (widgetKey: DashboardWidgetKey) => {
    if (widgetKey === "latency") {
      return <LatencySummaryPanel rows={detectionGuidanceLogs} liveEvents={latencyEvents} />;
    }

    if (widgetKey === "liveFeed") {
      return (
        <LiveCameraFeed
          imageUrl={imageUrl}
          latestDetections={latestDetections}
          connected={liveFeedConnected}
          lastGps={lastGps}
          platform={state.sessions.find((s) => s.device_id === "dev-001")?.platform || state.sessions[0]?.platform || "unknown"}
        />
      );
    }

    if (widgetKey === "telemetry") {
      return (
        <DeviceTelemetryPanel
          latestDetections={latestDetections}
          connected={liveFeedConnected}
          session={state.sessions.find((s) => s.device_id === "dev-001") || state.sessions[0] || null}
          ai={state.ai}
        />
      );
    }

    if (widgetKey === "timeline") {
      return <GuidanceTraceTimeline rows={detectionGuidanceLogs} />;
    }

    if (widgetKey === "guidanceLog") {
      return (
        <DetectionGuidanceLogTable
          rows={detectionGuidanceLogs}
          token={token}
          onUpdateFalsePositive={updateLogFalsePositive}
          onRefresh={() => {
            setLogPage(0);
            refreshLogs();
          }}
          refreshing={logsLoading}
          live={logPage === 0 && guidanceLogEvents.length > 0}
          streamFilter={logStreamFilter}
          onStreamFilterChange={(nextFilter) => {
            setLogStreamFilter(nextFilter);
            setLogPage(0);
          }}
          page={logPage}
          pageSize={LOG_PAGE_SIZE}
          totalCount={effectiveTotalCount}
          onPrevPage={() => setLogPage((p) => Math.max(0, p - 1))}
          onNextPage={() =>
            setLogPage((p) =>
              Math.min(Math.max(0, Math.ceil(effectiveTotalCount / LOG_PAGE_SIZE) - 1), p + 1),
            )
          }
          onSetPage={(nextPage) =>
            setLogPage(
              Math.min(
                Math.max(0, Math.ceil(effectiveTotalCount / LOG_PAGE_SIZE) - 1),
                Math.max(0, nextPage),
              ),
            )
          }
        />
      );
    }

    return <RiskEventLog events={state.risks} />;
  };

  return (
    <>
      <section className="widget-toolbar" aria-label="대시보드 위젯 관리">
        <button
          type="button"
          className="widget-add-btn"
          onClick={() => {
            setIsWidgetPickerOpen((prev) => {
              const next = !prev;
              if (next) {
                setWidgetMenuMode("root");
              }
              return next;
            });
          }}
          aria-expanded={isWidgetPickerOpen}
        >
          기능상자
        </button>
        {isWidgetPickerOpen && (
          <div className="widget-picker-menu" role="menu" aria-label="기능상자 메뉴">
            <button
              type="button"
              className="widget-picker-item"
              onClick={() => setWidgetMenuMode("add")}
            >
              추가
            </button>
            <button
              type="button"
              className="widget-picker-item widget-picker-item-danger"
              onClick={removeAllWidgets}
              disabled={widgetOrder.length === 0}
            >
              전체 삭제
            </button>

            {widgetMenuMode === "add" && (
              <>
                <div className="widget-picker-divider" />
                {availableWidgets.length === 0 ? (
                  <span className="widget-picker-empty">추가 가능한 위젯이 없습니다.</span>
                ) : (
                  availableWidgets.map((widget) => (
                    <button
                      key={widget.key}
                      type="button"
                      className="widget-picker-item"
                      onClick={() => addWidget(widget.key)}
                    >
                      {widget.label}
                    </button>
                  ))
                )}
              </>
            )}
          </div>
        )}
      </section>

      <section className="stream-line">
        <span>SSE</span>
        <strong>{streamUrl}</strong>
        <span>마지막 이벤트</span>
        <strong>
          {state.last_event_at ? new Date(state.last_event_at).toLocaleTimeString() : "-"}
        </strong>
      </section>

      <section className="dashboard-widget-grid">
        {widgetOrder.map((widgetKey) => {
          const widgetMeta = DASHBOARD_WIDGETS.find((widget) => widget.key === widgetKey);
          const moveModeActive = movingWidgetKey !== null;
          const isMovableTarget = movingWidgetKey === widgetKey;
          return (
            <div
              key={widgetKey}
              className={`dashboard-widget-item widget-${widgetKey} ${widgetMeta?.fullWidth ? "dashboard-widget-item-full" : ""} ${moveModeActive ? "widget-move-mode" : ""} ${isMovableTarget ? "widget-move-target" : ""} ${dragOverWidgetKey === widgetKey ? "widget-drop-target" : ""}`}
              draggable={isMovableTarget}
              onDragStart={() => {
                if (!isMovableTarget) {
                  return;
                }
                setDragOverWidgetKey(null);
              }}
              onDragOver={(event) => {
                if (!moveModeActive || !movingWidgetKey || movingWidgetKey === widgetKey) {
                  return;
                }
                event.preventDefault();
                setDragOverWidgetKey(widgetKey);
              }}
              onDragLeave={() => {
                if (dragOverWidgetKey === widgetKey) {
                  setDragOverWidgetKey(null);
                }
              }}
              onDrop={(event) => {
                if (!moveModeActive || !movingWidgetKey) {
                  return;
                }
                event.preventDefault();
                moveWidget(movingWidgetKey, widgetKey);
                setDragOverWidgetKey(null);
                setMovingWidgetKey(null);
              }}
              onDragEnd={() => {
                setDragOverWidgetKey(null);
                setMovingWidgetKey(null);
              }}
            >
              <div className="widget-card-actions">
                <button
                  type="button"
                  className="widget-option-trigger"
                  aria-label="위젯 옵션"
                  onClick={() =>
                    setOpenWidgetOptionKey((prev) => (prev === widgetKey ? null : widgetKey))
                  }
                >
                  ⋮
                </button>
                {openWidgetOptionKey === widgetKey && (
                  <div className="widget-option-menu" role="menu" aria-label="위젯 옵션 메뉴">
                    <button
                      type="button"
                      className="widget-option-move"
                      onClick={() => enableMoveMode(widgetKey)}
                    >
                      옮기기
                    </button>
                    <button
                      type="button"
                      className="widget-option-delete"
                      onClick={() => removeWidget(widgetKey)}
                    >
                      삭제
                    </button>
                  </div>
                )}
              </div>
              {renderWidget(widgetKey)}
            </div>
          );
        })}
      </section>
    </>
  );
}
