import { useMemo, useState } from "react";
import { AiPipelineMonitor } from "../components/AiPipelineMonitor";
import { DetectionFeed } from "../components/DetectionFeed";
import { RiskEventLog } from "../components/RiskEventLog";
import { SessionStatus } from "../components/SessionStatus";
import { SystemMetrics } from "../components/SystemMetrics";
import { useDetectionLogs } from "../api/useDetectionLogs";
import { DetectionGuidanceLogTable } from "../components/DetectionGuidanceLogTable";
import { LatencySummaryPanel } from "../components/LatencySummaryPanel";
import { LiveCameraFeed } from "../components/LiveCameraFeed";
import { DeviceTelemetryPanel } from "../components/DeviceTelemetryPanel";
import type { DetectionGuidanceLogRow, MonitorState } from "../types/monitor";
import type { useLiveFeed } from "../api/useLiveFeed";

const DEMO_GUIDANCE_LOGS: DetectionGuidanceLogRow[] = [
  {
    log_id: 1,
    event_id: "demo-event-001",
    user_id: 1,
    device_id: 101,
    detected_at: "2026-07-10T10:15:00Z",
    stream_type: "reflex",
    detected_objects_json: '[{"class_name":"pole","confidence":0.91}]',
    tts_text: "전방에 기둥이 있습니다.",
    frame_path: null,
    false_positive: null,
    latency_json: '{"decode_ms":12.3,"inference_ms":58.1,"total_ms":75.4}',
    created_at: "2026-07-10T10:15:12Z",
  },
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
  const { imageUrl, latestDetections, connected: liveFeedConnected, latencyEvents, guidanceLogEvents, lastGps } =
    liveFeed;

  // 사후 이력 로그는 REST로 페이지 단위(offset/limit) 조회한다 (frame_path 이미지 포함).
  // 2026-07-12: 클라이언트가 최근 50건만 받아 그 안에서 슬라이싱하던 방식은 하단 건수
  // 표시가 DB 전체 건수와 안 맞았다 - 서버가 X-Total-Count로 전체 건수를 내려주고,
  // 페이지를 넘길 때마다 해당 offset을 다시 조회하는 진짜 서버 페이지네이션으로 전환.
  const LOG_PAGE_SIZE = 10;
  const [logPage, setLogPage] = useState(0);
  const {
    rows: fetchedLogs,
    totalCount: logsTotalCount,
    updateLogFalsePositive,
    refresh: refreshLogs,
    loading: logsLoading,
  } = useDetectionLogs(token, logPage, LOG_PAGE_SIZE);

  // REST 페이지(fetchedLogs)와 WS 실시간 푸시(guidanceLogEvents)를 log_id 기준으로 병합한다.
  // 1페이지(최신)에서만 병합한다 - 2페이지 이후는 특정 offset의 과거 스냅샷이라 실시간
  // 이벤트가 끼어들면 페이지 경계가 흔들린다. 병합 후에도 페이지 크기를 유지하도록 자른다.
  const detectionGuidanceLogs = useMemo(() => {
    if (logPage !== 0) {
      return isDemoMode && fetchedLogs.length === 0 ? DEMO_GUIDANCE_LOGS : fetchedLogs;
    }
    const byId = new Map<number, DetectionGuidanceLogRow>();
    for (const row of fetchedLogs) byId.set(row.log_id, row);
    for (const row of guidanceLogEvents) byId.set(row.log_id, row);
    const merged = Array.from(byId.values())
      .sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime())
      .slice(0, LOG_PAGE_SIZE);
    return isDemoMode && merged.length === 0 ? DEMO_GUIDANCE_LOGS : merged;
  }, [fetchedLogs, guidanceLogEvents, isDemoMode, logPage]);

  return (
    <>
      <section className="stream-line">
        <span>SSE</span>
        <strong>{streamUrl}</strong>
        <span>마지막 이벤트</span>
        <strong>
          {state.last_event_at ? new Date(state.last_event_at).toLocaleTimeString() : "-"}
        </strong>
      </section>

      <section className="dashboard-grid">
        {/* 4열 그리드: LiveCameraFeed/DeviceTelemetryPanel이 각 2칸(span 2)을 차지하므로,
            1칸짜리 패널 4개(SystemMetrics/SessionStatus/AiPipelineMonitor/DetectionFeed)를
            먼저 배치해 1행을 꽉 채운 뒤 span-2 패널 2개가 2행을 채우게 한다.
            순서가 바뀌면(예: span-2 패널이 먼저 오면) 1행에 빈 칸이 생기고 1칸짜리
            패널이 다음 행에 혼자 떨어져 보이니 이 순서를 유지할 것. */}
        <SystemMetrics metrics={state.system} />
        <SessionStatus sessions={state.sessions} />
        <AiPipelineMonitor ai={state.ai} />
        <DetectionFeed items={state.detections} />
        <LiveCameraFeed
          imageUrl={imageUrl}
          latestDetections={latestDetections}
          connected={liveFeedConnected}
          lastGps={lastGps}
        />
        <DeviceTelemetryPanel
          latestDetections={latestDetections}
          connected={liveFeedConnected}
          session={state.sessions.find((s) => s.device_id === "dev-001") || state.sessions[0] || null}
          ai={state.ai}
        />
      </section>

      {/* 발표/면접 포인트:
          DetectionFeed는 실시간 스트림 모니터링,
          DetectionGuidanceLogTable은 사후 이력 조회 영역입니다.
          실시간 이벤트와 영속 로그를 분리해 운영자 해석 혼선을 줄입니다. */}
      <LatencySummaryPanel rows={detectionGuidanceLogs} liveEvents={latencyEvents} />
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
        page={logPage}
        pageSize={LOG_PAGE_SIZE}
        totalCount={logsTotalCount}
        onPrevPage={() => setLogPage((p) => Math.max(0, p - 1))}
        onNextPage={() =>
          setLogPage((p) =>
            Math.min(Math.max(0, Math.ceil(logsTotalCount / LOG_PAGE_SIZE) - 1), p + 1),
          )
        }
      />
      <RiskEventLog events={state.risks} />
    </>
  );
}
