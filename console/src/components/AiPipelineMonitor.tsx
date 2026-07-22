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
                <span>LLM(L2)</span>
                <strong>{ai.llm_provider ?? "대기"}</strong>
              </div>
              <div>
                <span>RAG (유사도)</span>
                <strong>{ai.rag_score ?? "-"}</strong>
              </div>
              <div>
                <span>TTS (출력)</span>
                <strong>{ai.tts_status ?? "대기"}</strong>
              </div>
              <div>
                <span>Reflex Bypass</span>
                {/* 💡 [면접 대비 주석 - 이중 경로 모니터링]
                    반사 경로를 탓다면 이 값이 true가 되면. LLM/RAG/TTS 상태는 멈춰 있어야 합니다. */}
                <strong>
                  {typeof ai.reflex_bypass === "boolean"
                    ? ai.reflex_bypass
                    ? " ⚡ 즉시 우회 " : "거침"
                    : "-"}
                </strong>
              </div>
              <div>
                <span>LLM Verified</span>
                <strong>
                  {typeof ai.llm_verified === "boolean"
                    ? ai.llm_verified
                      ? "true"
                      : "false"
                    : "-"}
                </strong>
              </div>
              <div>
                <span>Retry</span>
                <strong>{ai.llm_retry_count ?? "-"}</strong>
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
