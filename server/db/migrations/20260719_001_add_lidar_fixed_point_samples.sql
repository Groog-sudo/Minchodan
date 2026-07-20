-- Minchodan MariaDB 운영 변경 이력 스크립트입니다.
-- 목적: 거리측정(depthMode) 화면 고정 3지점(중앙/전방 하단/발밑) LiDAR 실측 로그 테이블 추가.
-- 배경: 기존 lidar_distance_validation_samples는 YOLO 탐지 객체 bbox와 짝지어야 저장되는데,
--       사용자가 객체 탐지 여부와 무관하게 화면에 이미 표시 중인 고정 지점 값을 바로
--       캡처해 줄자 대조에 쓰고 싶어함. 휴리스틱 비교 대상(bbox·area_ratio)이 없으므로
--       별도 테이블로 분리한다.
-- 주의: 운영 DB 반영 전 대상 DB, 백업, 실행 권한을 먼저 확인합니다.

CREATE TABLE IF NOT EXISTS lidar_fixed_point_samples (
    sample_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '고정 지점 LiDAR 샘플 고유 식별자',
    event_id VARCHAR(64) NOT NULL COMMENT '검증 캡처 이벤트 식별자 (클라이언트 생성)',
    device_id BIGINT UNSIGNED NULL COMMENT '사용자 기기 식별자. 알 수 없거나 삭제된 경우 NULL',
    point_label VARCHAR(32) NOT NULL COMMENT '고정 지점 라벨 (중앙/전방 하단/발밑 등)',
    x FLOAT NOT NULL COMMENT '정규화 x좌표(0~1)',
    y FLOAT NOT NULL COMMENT '정규화 y좌표(0~1)',
    lidar_meters FLOAT NULL COMMENT 'LiDAR 보정 거리(m). 유효 심도 샘플 없으면 NULL',
    axial_meters FLOAT NULL COMMENT 'LiDAR 원본 z축 거리(m, 보정 전)',
    lidar_sample_count INT NOT NULL DEFAULT 0 COMMENT '유효 depth 샘플 수',
    lidar_accuracy VARCHAR(16) NULL COMMENT 'absolute(LiDAR 실측) 또는 relative(시차 기반)',
    lidar_quality VARCHAR(16) NULL COMMENT 'high 또는 low',
    lidar_calibrated TINYINT(1) NOT NULL DEFAULT 0 COMMENT '카메라 캘리브레이션 보정 적용 여부',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT 'DB 로그 적재 시각',
    PRIMARY KEY (sample_id),
    KEY idx_lidar_fixed_point_event_id (event_id),
    KEY idx_lidar_fixed_point_created_at (created_at),
    CONSTRAINT FK_LIDAR_FIXED_POINT_USER_DEVICES
        FOREIGN KEY (device_id)
        REFERENCES user_devices (device_id)
        ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='거리측정 모드 고정 지점(중앙/전방 하단/발밑) LiDAR 실측 로그 테이블 (검증 전용)';

-- 선택 검증 쿼리
-- SHOW CREATE TABLE lidar_fixed_point_samples;
-- SELECT point_label, COUNT(*) AS n, ROUND(AVG(lidar_meters),3) AS avg_m
-- FROM lidar_fixed_point_samples GROUP BY point_label;
