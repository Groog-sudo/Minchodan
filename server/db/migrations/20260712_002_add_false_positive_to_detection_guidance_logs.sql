-- Minchodan MariaDB 운영 변경 이력 스크립트입니다.
-- 목적: 탐지/안내 로그에 오탐 여부(false_positive) 컬럼 추가.
--       운영자 콘솔에서 오탐 판정 시 True/False 값을 저장하여 향후 재학습 데이터 선별에 활용합니다.
-- 주의: 운영 DB 반영 전 대상 DB, 백업, 실행 권한을 먼저 확인합니다.

USE minchodan_db;

ALTER TABLE detection_guidance_logs
    ADD COLUMN false_positive BOOLEAN NULL
        COMMENT '오탐 판정 여부 (NULL: 미판정, 0: 정상 탐지, 1: 오탐)'
        AFTER frame_path;

-- 선택 검증 쿼리
-- SHOW CREATE TABLE detection_guidance_logs;
-- SELECT column_name, column_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'minchodan_db'
--   AND table_name = 'detection_guidance_logs'
--   AND column_name = 'false_positive';
