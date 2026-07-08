import type { AiPipelineStatus } from "../types/monitor";

export function AiPipelineMonitor({ ai }: { ai: AiPipelineStatus | null }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>AI Pipeline Monitor</h2>
        <span className="panel-kicker">AI 상태</span>
      </div>

      {/* TH HARDCODE AREA:
          LLM provider, RAG query/score, TTS status, STT status,
          Reflex Path LLM 미경유 여부를 직접 표시합니다. */}
      <div className="placeholder-box">
        {ai ? (
          <>
            <div className="ai-grid">
              <div>
                <span>LLM</span>
                <strong>{ai.llm_provider ?? "-"}</strong>
              </div>
              <div>
                <span>RAG</span>
                <strong>{ai.rag_score ?? "-"}</strong>
              </div>
              <div>
                <span>TTS</span>
                <strong>{ai.tts_status ?? "-"}</strong>
              </div>
              <div>
                <span>STT</span>
                <strong>{ai.stt_status ?? "-"}</strong>
              </div>
            </div>
            <div className="guidance-line">
                <span>최근 안내문</span>
                <strong>{ai.last_guidance ?? "대기 중"}</strong>
            </div>
          </>
        ) : (
          <div className="placeholder-box">AI Pipeline 상태 대기 중</div>
        )}
        {/* 발표/면접 대응 포인트:
         이 컴포넌트는 AI를 실행하는 곳이 아니라 SSE로 받은 상태를 표시하는 관제 화면입니다.
        LLM/RAG/TTS/STT는 각각 따로 이벤트가 들어올 수 있으므로, useMonitorStream.ts에서 ai 객체를 누적 갱신한 뒤 여기서는 최신 값만 렌더링합니다.
        반사 경로는 LLM/RAG/실시간 TTS를 타면 안 되므로 reflex_bypass 값은 이중 경로 원칙 검증용 표시 필드입니다. */}
      </div>
    </section>
  );
}
