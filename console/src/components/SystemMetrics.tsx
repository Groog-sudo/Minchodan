import type { SystemMetrics as SystemMetricsData } from "../types/monitor";

export function SystemMetrics({ metrics }: { metrics: SystemMetricsData | null }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>SystemMetrics</h2>
        <span className="panel-kicker">시스템 상태</span>
      </div>

      {/* TH HARDCODE AREA:
          metrics.gpu_usage_pct, memory_used_mb, current_provider,
          network_rtt_ms, queue_depth, dropped_frames를 카드로 직접 표시합니다. */}

      {/* 발표/면접 대응 포인트:
        SystemMetrics는 서버/GPU/네트워크 상태를 최신값으로 보여주는 관제 카드입니다.
        system_metrics와 gpu_status 이벤트는 로그처럼 누적하지 않고 useMonitorStream.ts에서 system 객체를 덮어씁니다.
        그래서 이 컴포넌트는 현재 서버 상태를 빠르게 확인하는 목적입니다. */}
      <div className="placeholder-box">
        { metrics ? (
            <>
            <div className="metric-grid">
              <div className="metric">
                <span>GPU</span>
                <strong>{metrics.gpu_usage_pct ?? "-"}%</strong>
              </div>
              <div className="metric">
                <span>Memory</span>
                <strong>{metrics.memory_used_mb ?? "-"} MB</strong>
              </div>
              <div className="metric">
                <span>Provider</span>
                <strong>{metrics.current_provider ?? "-"}</strong>
              </div>
              <div className="metric">
                <span>RTT</span>
                <strong>{metrics.network_rtt_ms ?? "-"} ms</strong>
              </div>
              <div className="metric">
                <span>Queue</span>
                <strong>{metrics.queue_depth ?? "-"}</strong>
              </div>
              <div className="metric">
                <span>Dropped</span>
                <strong>{metrics.dropped_frames ?? "-"}</strong>
              </div>
            </div>
        
            {metrics.last_error ? (
              <p className="error-line">{metrics.last_error}</p>
            ) : null}
          </>
        ):(
          <div className="placeholder-box">아직 시스템 메트릭이 없습니다.</div>
        )}
      </div>
      {/*
        SystemMetrics는 이벤트 로그가 아니라 최신 서버 상태 카드입니다.
        GPU 사용률, 메모리, RTT, 큐 적체, 드롭 프레임을 보면 YOLO/SEG/LLM/TTS 병목이 서버 자원 문제인지 판단할 수 있습니다.
      */}
      

    </section>
  );
}
