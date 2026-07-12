-- app_users 테이블에 회원 상세 프로필 필드(생년월일/보호자 연락처/주소)를 추가합니다.
-- 익명 자동등록(server/services/device_registry_service.py)은 이 값들을 채우지 않으므로
-- NULL을 허용한다 - 관리자 회원 등록/전환 화면에서 선택적으로 입력한다.
ALTER TABLE app_users
    ADD COLUMN birth_date DATE NULL AFTER disability_severity,
    ADD COLUMN guardian_phone VARCHAR(30) NULL AFTER birth_date,
    ADD COLUMN address VARCHAR(255) NULL AFTER guardian_phone;
