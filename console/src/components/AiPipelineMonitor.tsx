import type { AiPipelineStatus } from "../types/monitor";

export function AiPipelineMonitor({ ai }: { ai: AiPipelineStatus | null }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>AI Pipeline Monitor</h2>
        <span className="panel-kicker">TH 직접 구현</span>
      </div>

      {/* TH HARDCODE AREA:
          LLM provider, RAG query/score, TTS status, STT status,
          Reflex Path LLM 미경유 여부를 직접 표시합니다. */}
      <div className="placeholder-box">
        {ai ? "AI 파이프라인 이벤트 수신됨" : "AI 파이프라인 상태 대기 중"}
      </div>
    </section>
  );
}
