-- Minchodan MariaDB 초기 스키마 세션 스크립트입니다.
-- 기준: `.env.example`의 DB_NAME=minchodan_db, `server/db/models.py`, `server/db/schema.sql`.
-- 과거 초안의 `minchodan_tmp` 또는 `minchodan_app` 기준과 다르게 현재 대상 DB는 `minchodan_db`입니다.
-- DBeaver에서 실행할 때는 이전 DB를 먼저 USE하지 말고 아래 `CREATE DATABASE`부터
-- 순서대로 실행해 현재 세션 DB를 명확히 고정합니다.
-- 주의: `CREATE TABLE IF NOT EXISTS`는 중복 생성 오류만 피하며,
-- 기존 테이블의 컬럼, 인덱스, FK 구조를 자동 마이그레이션하지 않습니다.

-- 1. DB 생성 및 선택
-- 한글 이름, 권한 설명, 상태값 저장을 위해 `utf8mb4`와 `utf8mb4_unicode_ci`를 사용합니다.
-- 접속 계정에 DB 생성/사용 권한이 필요하며, 서버 설정의 `DB_NAME`도 `minchodan_db`와 맞춰야 합니다.
CREATE DATABASE IF NOT EXISTS minchodan_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE minchodan_db;

-- 2. 관리자 계정
-- 운영자 콘솔 로그인 계정의 식별자, 권한, 상태를 저장합니다.
-- `employee_no`는 로그인 ID이므로 UNIQUE로 중복 가입을 막습니다.
-- `password_hash`에는 bcrypt/Argon2ID 같은 단방향 해시만 저장하고 평문은 금지합니다.
-- `role` 인덱스는 권한별 관리자 조회에 사용하며, 삭제/잠금은 `status` 값으로 표현합니다.
CREATE TABLE IF NOT EXISTS admin_accounts (
    admin_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '관리자 계정 고유 식별자',
    employee_no VARCHAR(50) NOT NULL COMMENT '로그인 식별자, 중복 등록 불가',
    name VARCHAR(50) NOT NULL COMMENT '관리자 실명',
    password_hash VARCHAR(255) NOT NULL COMMENT '단방향 해시(bcrypt/Argon2ID) 저장, 평문 저장 금지',
    role ENUM('super_admin', 'operator', 'viewer') NOT NULL DEFAULT 'operator' COMMENT 'super_admin(최고관리자) / operator(운영자) / viewer(읽기전용)',
    status ENUM('active', 'inactive', 'locked', 'deleted') NOT NULL DEFAULT 'active' COMMENT 'active / inactive / locked(비밀번호 오류 잠금) / deleted',
    PRIMARY KEY (admin_id),
    UNIQUE KEY UK_ADMIN_ACCOUNTS_EMPLOYEE_NO (employee_no),
    KEY IDX_ADMIN_ACCOUNTS_ROLE (role)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='관리자 계정 테이블';

-- 3. 관리자 로그인 감사 로그
-- 관리자 로그인 성공/실패 시도를 INSERT 중심으로 남기는 감사 테이블입니다.
-- FK 대신 입력된 `employee_no` 문자열을 저장해 실패 계정, 삭제된 계정의 시도도 보존합니다.
-- `created_at`은 마이크로초 단위 기록 시각이며, `employee_no` 인덱스는 사번별 이력 조회용입니다.
CREATE TABLE IF NOT EXISTS admin_login_audits (
    audit_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '감사 로그 고유 식별자',
    employee_no VARCHAR(50) NOT NULL COMMENT '로그인을 시도한 사번',
    success TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1: 성공, 0: 실패',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) COMMENT '로그인 시도 타임스탬프. 삽입 후 변경 불가',
    PRIMARY KEY (audit_id),
    KEY IDX_ADMIN_LOGIN_AUDITS_EMPLOYEE_NO (employee_no)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='관리자 로그인 감사 로그 테이블';

-- 4. 단말 앱 사용자
-- 시각장애인 보행 보조 앱 사용자의 기본 가입 정보를 저장합니다.
-- `phone`은 앱 인증/연락용 식별자이므로 UNIQUE로 중복 가입을 방지합니다.
-- `disability_severity`는 안내 상세도 분기와 통계 조회에 쓰기 위해 인덱스로 둡니다.
-- 탈퇴/정지는 물리 삭제보다 `status` 값으로 먼저 표현하는 구조입니다.
CREATE TABLE IF NOT EXISTS app_users (
    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '사용자 고유 식별자',
    name VARCHAR(50) NOT NULL COMMENT '사용자 성명',
    phone VARCHAR(30) NOT NULL COMMENT '앱 인증/연락용, 중복 가입 방지',
    disability_severity VARCHAR(30) NOT NULL COMMENT '심한 장애/경증 등. 보행 안내 상세도 분기에 참고',
    status ENUM('active', 'inactive', 'deleted') NOT NULL DEFAULT 'active' COMMENT 'active(사용중) / inactive(정지) / deleted(탈퇴)',
    PRIMARY KEY (user_id),
    UNIQUE KEY UK_APP_USERS_PHONE (phone),
    KEY IDX_APP_USERS_DISABILITY_SEVERITY (disability_severity),
    KEY IDX_APP_USERS_STATUS (status)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='단말 앱 사용자 테이블';

-- 5. 사용자 기기
-- 앱 사용자가 등록한 스마트폰 단말을 `app_users`와 연결합니다.
-- `device_uuid`는 단말 중복 등록 방지를 위해 UNIQUE로 제한합니다.
-- `user_id` 인덱스는 사용자별 기기 조회와 FK 검증에 사용합니다.
-- `ON DELETE RESTRICT`는 기기가 남은 사용자의 하드 삭제를 막아 참조 무결성을 보존합니다.
CREATE TABLE IF NOT EXISTS user_devices (
    device_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '등록 기기 고유 식별자',
    user_id BIGINT UNSIGNED NOT NULL COMMENT '기기 소유 사용자',
    device_uuid VARCHAR(100) NOT NULL COMMENT '단말 하드웨어 UUID, 중복 등록 불가',
    platform ENUM('ios', 'android', 'unknown') NOT NULL DEFAULT 'unknown' COMMENT 'ios / android / unknown',
    is_active TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1: 사용가능, 0: 사용불가',
    PRIMARY KEY (device_id),
    UNIQUE KEY UK_USER_DEVICES_DEVICE_UUID (device_uuid),
    KEY IDX_USER_DEVICES_USER_ID (user_id),
    CONSTRAINT FK_USER_DEVICES_APP_USERS
        FOREIGN KEY (user_id)
        REFERENCES app_users (user_id)
        ON DELETE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='사용자 기기 테이블';

-- 6. 탐지 및 안내 로그
-- 클라이언트 프레임 이벤트 기준으로 탐지 시각, YOLO 탐지 결과, LLM 최종 안내 문장을 저장합니다.
-- `detected_objects_json`에는 class_name, confidence, bbox, track_id, risk_hint 등을 JSON 배열로 보관합니다.
-- 로그는 분석/감사용 이력이므로 사용자 또는 기기가 삭제되어도 `ON DELETE SET NULL`로 레코드를 보존합니다.
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

-- 7. 기본 확인
-- 다섯 개 테이블이 현재 DB(`minchodan_db`)에 생성되었는지 먼저 확인합니다.
SHOW TABLES;

-- 8. 선택 검증 쿼리
-- 구조, 컬럼, FK까지 확인해야 할 때 필요한 쿼리만 주석 해제해 실행합니다.
-- SHOW DATABASES LIKE 'minchodan_db';
-- SHOW CREATE TABLE admin_accounts;
-- SHOW CREATE TABLE app_users;
-- SHOW CREATE TABLE user_devices;
-- SHOW CREATE TABLE admin_login_audits;
-- SHOW CREATE TABLE detection_guidance_logs;
-- SELECT table_name, column_name, column_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'minchodan_db'
-- ORDER BY table_name, ordinal_position;
-- SELECT table_name, constraint_name, referenced_table_name
-- FROM information_schema.key_column_usage
-- WHERE table_schema = 'minchodan_db'
--   AND referenced_table_name IS NOT NULL;
