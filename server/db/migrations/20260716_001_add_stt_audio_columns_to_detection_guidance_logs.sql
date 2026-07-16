-- detection_guidance_logs STT 원본 음성 저장 메타데이터 컬럼 추가
-- 기존 데이터 보존 원칙: DROP/CREATE 없이 ALTER TABLE ADD COLUMN + backfill만 수행합니다.

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS event_source VARCHAR(20) NULL DEFAULT 'unknown' AFTER created_at;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_transcript_text TEXT NULL AFTER event_source;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_path VARCHAR(255) NULL AFTER stt_transcript_text;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_storage_status VARCHAR(30) NULL DEFAULT 'not_applicable' AFTER stt_audio_path;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_format VARCHAR(10) NULL AFTER stt_audio_storage_status;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_size_bytes BIGINT NULL AFTER stt_audio_format;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_duration_ms INT NULL AFTER stt_audio_size_bytes;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_sha256 VARCHAR(64) NULL AFTER stt_audio_duration_ms;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_error_code VARCHAR(64) NULL AFTER stt_audio_sha256;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_consent_at DATETIME(6) NULL AFTER stt_audio_error_code;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS stt_audio_expires_at DATETIME(6) NULL AFTER stt_audio_consent_at;

ALTER TABLE detection_guidance_logs
    ADD COLUMN IF NOT EXISTS writer_instance_id VARCHAR(100) NULL AFTER stt_audio_expires_at;

UPDATE detection_guidance_logs
SET event_source = CASE
    WHEN event_id LIKE 'stt-%' THEN 'stt'
    WHEN event_id LIKE 'nav-%' THEN 'navigation'
    ELSE 'detection'
END
WHERE event_source IS NULL OR event_source = '' OR event_source = 'unknown';

UPDATE detection_guidance_logs
SET stt_audio_storage_status = CASE
    WHEN event_source = 'stt' THEN 'not_saved'
    ELSE 'not_applicable'
END
WHERE stt_audio_storage_status IS NULL OR stt_audio_storage_status = '';

ALTER TABLE detection_guidance_logs
    MODIFY COLUMN event_source VARCHAR(20) NOT NULL DEFAULT 'unknown',
    MODIFY COLUMN stt_audio_storage_status VARCHAR(30) NOT NULL DEFAULT 'not_applicable';

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_event_source_detected_at
    ON detection_guidance_logs (event_source, detected_at);

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_stt_audio_status
    ON detection_guidance_logs (stt_audio_storage_status, detected_at);

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_stt_audio_path
    ON detection_guidance_logs (stt_audio_path);

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_writer_instance_id
    ON detection_guidance_logs (writer_instance_id);
