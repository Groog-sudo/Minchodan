-- Minchodan MariaDB 운영 변경 이력 스크립트입니다.
-- 목적: 탐지/안내 로그에 이벤트 발생 시점 프레임 이미지 경로 컬럼 추가.
--       콘솔 오탐 검증 및 안내 발화 상황 이미지 확인용. 이미지 파일 자체는
--       data/event_frames/ 아래 파일 시스템에 저장하고 DB에는 상대 경로만 남깁니다.
-- 주의: 운영 DB 반영 전 대상 DB, 백업, 실행 권한을 먼저 확인합니다.

USE minchodan_db;

ALTER TABLE detection_guidance_logs
    ADD COLUMN frame_path VARCHAR(255) NULL
        COMMENT '이벤트 프레임 이미지 상대 경로 (data/event_frames/ 기준). 저장 실패 또는 프레임 없는 이벤트는 NULL'
        AFTER tts_text;

-- 선택 검증 쿼리
-- SHOW CREATE TABLE detection_guidance_logs;
-- SELECT column_name, column_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'minchodan_db'
--   AND table_name = 'detection_guidance_logs'
--   AND column_name = 'frame_path';
