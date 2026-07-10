-- Minchodan MariaDB 운영 변경 이력 스크립트입니다.
-- 목적: 클라이언트 프레임 이벤트 기준의 YOLO 탐지 결과와 LLM/TTS 안내 문장 로그 테이블 추가.
-- 주의: 운영 DB 반영 전 대상 DB, 백업, 실행 권한을 먼저 확인합니다.

USE minchodan_db;

CREATE TABLE IF NOT EXISTS detection_guidance_logs (
    log_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '탐지/안내 로그 고유 식별자',
    event_id VARCHAR(64) NULL COMMENT '프레임 또는 탐지 이벤트 식별자. 서버/클라이언트 중복 전송 추적용',
    user_id BIGINT UNSIGNED NULL COMMENT '앱 사용자 식별자. 알 수 없거나 삭제된 경우 NULL',
    device_id BIGINT UNSIGNED NULL COMMENT '사용자 기기 식별자. 알 수 없거나 삭제된 경우 NULL',
    detected_at DATETIME(6) NOT NULL COMMENT '클라이언트 프레임 기준 탐지 시각',
    stream_type ENUM('reflex', 'cognitive', 'unknown') NOT NULL DEFAULT 'unknown' COMMENT '반사/인지/미분류 스트림 구분',
    detected_objects_json JSON NOT NULL COMMENT 'YOLO 탐지 객체 정보 JSON 배열',
    tts_text TEXT NOT NULL COMMENT 'LLM이 사용자에게 출력한 TTS 전체 문장',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT 'DB 로그 적재 시각',
    PRIMARY KEY (log_id),
    UNIQUE KEY UK_DETECTION_GUIDANCE_LOGS_EVENT_ID (event_id),
    KEY IDX_DETECTION_GUIDANCE_LOGS_DETECTED_AT (detected_at),
    KEY IDX_DETECTION_GUIDANCE_LOGS_USER_ID (user_id),
    KEY IDX_DETECTION_GUIDANCE_LOGS_DEVICE_ID (device_id),
    KEY IDX_DETECTION_GUIDANCE_LOGS_STREAM_TYPE (stream_type),
    CONSTRAINT FK_DETECTION_GUIDANCE_LOGS_APP_USERS
        FOREIGN KEY (user_id)
        REFERENCES app_users (user_id)
        ON DELETE SET NULL,
    CONSTRAINT FK_DETECTION_GUIDANCE_LOGS_USER_DEVICES
        FOREIGN KEY (device_id)
        REFERENCES user_devices (device_id)
        ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='탐지 결과 및 TTS 안내 로그 테이블';

-- 선택 검증 쿼리
-- SHOW CREATE TABLE detection_guidance_logs;
-- SELECT table_name, column_name, column_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'minchodan_db'
--   AND table_name = 'detection_guidance_logs'
-- ORDER BY ordinal_position;
