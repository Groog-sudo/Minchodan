import type { DetectionGuidanceLogRow, LatencyStages, LiveLatencyEvent } from "../types/monitor";

// 발표/면접 포인트:
// - docs/design/pipeline_stage_design.md §4 "단계별 지연 목표" 표에서 L6(LLM ainvoke)와
//   L7(실시간 TTS 합성)이 "측정 필요"로 남아 있던 항목이었다. 이 패널이 그 실측치를
//   최근 이벤트 기준으로 채워 넣는다.
// - 두 데이터 소스를 쓴다: liveEvents(WS 실시간 푸시, useLiveFeed)가 있으면 그것을 우선
//   사용해 진짜 실시간으로 갱신되고, 아직 하나도 안 쌓였으면(페이지 갓 로드 등) REST 폴링된
//   rows(detection_guidance_logs)로 폴백한다. liveEvents는 db_save_ms가 빠져 있는데(비동기
//   확정 전 시점에 푸시하므로), REST rows는 db_save_ms까지 포함한다.

interface StageStat {
  key: keyof LatencyStages;
  label: string;
  count: number;
  avgMs: number;
  maxMs: number;
  targetMs: number | null; // 설계 문서 목표치. 없으면 null(중립 색상).
}

const STAGE_DEFS: Array<{ key: keyof LatencyStages; label: string; targetMs: number | null }> = [
  { key: "decode_ms", label: "디코딩", targetMs: 50 },
  { key: "stt_ms", label: "STT", targetMs: null },
  { key: "inference_ms", label: "추론", targetMs: 80 },
  { key: "rag_ms", label: "RAG 검색", targetMs: 50 },
  { key: "llm_ms", label: "LLM(ainvoke)", targetMs: null },
  { key: "tts_ms", label: "실시간 TTS", targetMs: null },
  { key: "db_save_ms", label: "DB 저장", targetMs: null },
  { key: "total_ms", label: "종단 총합", targetMs: null },
];

function parseLatency(json: string | null): LatencyStages {
  if (!json) return {};
  try {
    const parsed = JSON.parse(json);
    return typeof parsed === "object" && parsed !== null ? (parsed as LatencyStages) : {};
  } catch {
    return {};
  }
}

function computeStats(samples: LatencyStages[], windowSize: number): StageStat[] {
  const recent = samples.slice(0, windowSize);

  return STAGE_DEFS.map(({ key, label, targetMs }) => {
    const values = recent
      .map((stage) => stage[key])
      .filter((v): v is number => typeof v === "number");
    if (values.length === 0) {
      return { key, label, count: 0, avgMs: 0, maxMs: 0, targetMs };
    }
    const avgMs = values.reduce((sum, v) => sum + v, 0) / values.length;
    const maxMs = Math.max(...values);
    return { key, label, count: values.length, avgMs, maxMs, targetMs };
  });
}

function statusClass(stat: StageStat): string {
  if (stat.count === 0) return "latency-stat-neutral";
  if (stat.targetMs === null) return "latency-stat-neutral";
  return stat.avgMs <= stat.targetMs ? "latency-stat-ok" : "latency-stat-over";
}

export function LatencySummaryPanel({
  rows,
  liveEvents,
  windowSize = 30,
}: {
  rows: DetectionGuidanceLogRow[];
  liveEvents?: LiveLatencyEvent[];
  windowSize?: number;
}) {
  const isLive = Boolean(liveEvents && liveEvents.length > 0);
  const samples = isLive
    ? liveEvents!.map((event) => event.latency)
    : rows.map((row) => parseLatency(row.latency_json));
  const stats = computeStats(samples, windowSize);

  return (
    <section className="panel panel-latency">
      <div className="panel-header">
        <h2>파이프라인 지연 요약</h2>
        <span className="panel-kicker">
          {isLive ? (
            <>
              <span className="latency-live-dot" aria-hidden="true" />
              실시간 · 최근 {windowSize}건
            </>
          ) : (
            `최근 ${windowSize}건 평균/최대 (폴링)`
          )}
        </span>
      </div>
      {stats.length === 0 ? (
        <p className="empty-text">아직 레이턴시 데이터가 없습니다.</p>
      ) : (
        <div className="latency-stat-grid">
          {stats.map((stat) => (
            <div key={stat.key} className={`latency-stat-card ${statusClass(stat)}`}>
              <span className="latency-stat-label">{stat.label}</span>
              <span className="latency-stat-avg">
                {stat.count > 0 ? `${stat.avgMs.toFixed(0)}ms` : "-"}
              </span>
              <span className="latency-stat-sub">
                <span>
                  {stat.count > 0 ? `최대 ${stat.maxMs.toFixed(0)}ms · ${stat.count}건` : "데이터 없음"}
                </span>
                {stat.targetMs !== null && (
                  <span className="latency-stat-target-line">목표 · &lt;{stat.targetMs}ms</span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
