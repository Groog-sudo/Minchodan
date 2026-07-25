-- Dummy Data Seeding Script for MariaDB (minchodan_db)

-- 1. 관리자 계정 추가 (비밀번호 해시는 임시로 'admin123'을 bcrypt로 돌린 값 등, 여기선 평문 해시 스텁)
INSERT INTO admin_accounts (employee_no, name, password_hash, role, status) VALUES 
('EMP001', '시스템 관리자', '$2b$12$eImiTXuWVxfM37uY4JANjQ==', 'super_admin', 'active'),
('EMP002', '운영 담당자', '$2b$12$eImiTXuWVxfM37uY4JANjQ==', 'operator', 'active')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 2. 앱 사용자 추가
INSERT INTO app_users (user_id, name, phone, disability_severity, birth_date, guardian_phone, address, status) VALUES 
(1, '홍길동', '010-1234-5678', 'severe', '1990-01-01', '010-9876-5432', '서울시 강남구', 'active'),
(2, '김철수', '010-1111-2222', 'mild', '1985-05-05', '010-3333-4444', '서울시 서초구', 'active')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 3. 기기 정보 추가 (dev-001 은 현재 앱에서 테스트하는 디바이스 ID)
INSERT INTO user_devices (device_id, user_id, device_uuid, platform, is_active) VALUES 
(1, 1, 'dev-001', 'android', 1),
(2, 2, 'dev-002', 'ios', 1)
ON DUPLICATE KEY UPDATE device_uuid=VALUES(device_uuid);

-- 4. 초기 테스트 탐지 로그 (옵션)
INSERT INTO detection_guidance_logs (event_id, user_id, device_id, detected_at, stream_type, detected_objects_json, tts_text, false_positive) VALUES 
('EVT-0001', 1, 1, NOW(), 'cognitive', '{"objects": ["bollard"]}', '전방에 볼라드가 있습니다. 주의하세요.', 0)
ON DUPLICATE KEY UPDATE tts_text=VALUES(tts_text);
