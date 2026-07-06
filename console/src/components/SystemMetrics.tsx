import type { SystemMetrics as SystemMetricsData } from "../types/monitor";

export function SystemMetrics({ metrics }: { metrics: SystemMetricsData | null }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>SystemMetrics</h2>
        <span className="panel-kicker">TH 직접 구현</span>
      </div>

      {/* TH HARDCODE AREA:
          metrics.gpu_usage_pct, memory_used_mb, current_provider,
          network_rtt_ms, queue_depth, dropped_frames를 카드로 직접 표시합니다. */}
      <div className="placeholder-box">
        {metrics ? "시스템 메트릭 수신됨" : "아직 시스템 메트릭이 없습니다."}
      </div>
    </section>
  );
}
