-- detection_guidance_logs 테이블에 스테이지별 처리 지연(ms) 기록 컬럼을 추가합니다.
-- 실기기 -> STT -> LLM -> 추론 -> DB저장 등 파이프라인 종단 지연을 콘솔에서 확인하기 위함
-- (docs/design/pipeline_stage_design.md §4 "L6 ainvoke/L7 TTS 합성 측정 필요" 항목의 후속 조치).
ALTER TABLE detection_guidance_logs
    ADD COLUMN latency_json JSON NULL
    AFTER false_positive;
