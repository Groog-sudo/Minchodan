-- lidar_distance_validation_samples에 LiDAR 자문 구역(lidar_distance_zone) 컬럼 추가.
-- 배경: 거리 정책 SSOT 2단계(온디맨드 토글 유지 결정) - server/detection/distance_policy.py의
-- zone_from_lidar_meters()가 계산하는 값을 heuristic_distance_class와 나란히 저장해
-- scripts/analyze_lidar_validation.py가 구역 혼동 행렬을 출력할 수 있게 한다.
-- 반사/인지 실시간 라우팅에는 관여하지 않는 검증 전용 컬럼이다.
-- 기존 데이터 보존 원칙: DROP/CREATE 없이 ALTER TABLE ADD COLUMN만 수행합니다.

ALTER TABLE lidar_distance_validation_samples
    ADD COLUMN IF NOT EXISTS lidar_distance_zone VARCHAR(16) NULL
        COMMENT 'zone_from_lidar_meters() 계산 결과(near/medium/far). lidar_meters가 없으면 NULL'
        AFTER heuristic_area_ratio;

-- 선택 검증 쿼리
-- SHOW CREATE TABLE lidar_distance_validation_samples;
-- SELECT heuristic_distance_class, lidar_distance_zone, COUNT(*) AS cnt
-- FROM lidar_distance_validation_samples
-- WHERE lidar_distance_zone IS NOT NULL
-- GROUP BY heuristic_distance_class, lidar_distance_zone
-- ORDER BY heuristic_distance_class, lidar_distance_zone;
