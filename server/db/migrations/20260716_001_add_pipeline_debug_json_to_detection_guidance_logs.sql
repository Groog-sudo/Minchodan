-- detection_guidance_logs: 관리자 콘솔 파이프라인 텍스트 디버그용 JSON 컬럼 추가.
-- STT 전사문, RAG 수칙, LLM/패스트레인 응답, 브릿지 분기 등 경로별 중간 텍스트를
-- 이벤트 단위로 영속화한다(관리자 전용 REST/WS guidance_log_event).
ALTER TABLE detection_guidance_logs
    ADD COLUMN pipeline_debug_json JSON NULL
    AFTER latency_json;
