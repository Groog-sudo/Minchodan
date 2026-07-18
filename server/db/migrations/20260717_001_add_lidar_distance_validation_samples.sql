-- Minchodan MariaDB 운영 변경 이력 스크립트입니다.
-- 목적: iOS LiDAR 실거리 검증 캡처 로그 테이블 추가 (검증 전용, 반사/인지 경로 판단에는 미관여).
-- 배경: 거리측정(depthMode) 프로토타입에서 얻은 LiDAR 실측값과, 서버가 동일 bbox에 재계산한
--       휴리스틱(near/medium/far) 라벨을 나란히 저장해 담당자가 사후 SQL/스크립트로 정확도를
--       검증할 수 있게 한다. detection_guidance_logs와 카디널리티(1 캡처 = N bbox 행)가 달라
--       컬럼 추가 대신 별도 테이블로 분리했다.
-- 주의: 운영 DB 반영 전 대상 DB, 백업, 실행 권한을 먼저 확인합니다.

USE minchodan_db;

CREATE TABLE IF NOT EXISTS lidar_distance_validation_samples (
    sample_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'LiDAR 검증 샘플 고유 식별자',
    event_id VARCHAR(64) NOT NULL COMMENT '검증 캡처 이벤트 식별자 (클라이언트 생성)',
    device_id BIGINT UNSIGNED NULL COMMENT '사용자 기기 식별자. 알 수 없거나 삭제된 경우 NULL',
    class_name VARCHAR(64) NOT NULL COMMENT '서버 YOLO 탐지 클래스명',
    confidence FLOAT NOT NULL COMMENT '서버 YOLO 탐지 신뢰도',
    bbox_json JSON NOT NULL COMMENT '탐지 bbox 좌표(x, y, w, h) JSON',
    lidar_meters FLOAT NULL COMMENT 'LiDAR 실측 거리(m). 유효 심도 샘플 없으면 NULL',
    lidar_sample_count INT NOT NULL DEFAULT 0 COMMENT 'bbox 영역 내 유효 depth 픽셀 수',
    lidar_accuracy VARCHAR(16) NULL COMMENT 'absolute(LiDAR 실측) 또는 relative(시차 기반)',
    lidar_quality VARCHAR(16) NULL COMMENT 'high 또는 low',
    lidar_calibrated TINYINT(1) NOT NULL DEFAULT 0 COMMENT '카메라 캘리브레이션 보정 적용 여부',
    heuristic_distance_class VARCHAR(16) NOT NULL COMMENT '서버 bbox 면적 비율 휴리스틱 라벨(near/medium/far)',
    heuristic_area_ratio FLOAT NOT NULL COMMENT '휴리스틱 계산에 사용된 bbox 면적 비율',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT 'DB 로그 적재 시각',
    PRIMARY KEY (sample_id),
    KEY idx_lidar_validation_event_id (event_id),
    KEY idx_lidar_validation_created_at (created_at),
    CONSTRAINT FK_LIDAR_VALIDATION_USER_DEVICES
        FOREIGN KEY (device_id)
        REFERENCES user_devices (device_id)
        ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='iOS LiDAR 실거리 검증 캡처 로그 테이블 (검증 전용)';

-- 선택 검증 쿼리
-- SHOW CREATE TABLE lidar_distance_validation_samples;
-- SELECT table_name, column_name, column_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'minchodan_db'
--   AND table_name = 'lidar_distance_validation_samples'
-- ORDER BY ordinal_position;
