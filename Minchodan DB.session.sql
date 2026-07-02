-- Minchodan 임시 DB 초기 스키마 생성 스크립트
-- 대상 DB: minchodan_tmp
-- 목적: 운영자 콘솔 관리자, 앱 사용자, 사용자 단말, 관리자 로그인 감사 테이블을 생성합니다.
-- 주의: CREATE TABLE IF NOT EXISTS는 기존 테이블 구조를 자동 변경하지 않으므로,
--       운영 환경의 컬럼/인덱스 변경은 별도 마이그레이션으로 관리해야 합니다.

-- minchodan_tmp 데이터베이스가 이미 생성되어 있다는 전제로 실행합니다.
-- 새 DB부터 만들어야 한다면 관리자 권한 계정에서 아래 CREATE DATABASE 예시를 먼저 실행하십시오.
-- utf8mb4는 한글, 접근성 메모, User-Agent 등 유니코드 문자열 저장을 안정적으로 처리합니다.
-- CREATE DATABASE IF NOT EXISTS minchodan_tmp
--     DEFAULT CHARACTER SET utf8mb4
--     DEFAULT COLLATE utf8mb4_unicode_ci;

-- 이후 모든 DDL이 minchodan_tmp에 적용되도록 현재 SQL 세션의 기본 DB를 전환합니다.
USE minchodan_tmp;

-- 공통 설계:
-- - InnoDB: 트랜잭션, 외래 키, 행 단위 잠금을 지원합니다.
-- - DATETIME(6): 로그인/접속/수정 시각을 마이크로초 단위까지 기록합니다.
-- - status + deleted_at: 실제 삭제 전 소프트 삭제 흐름을 지원합니다.

-- 1. 운영자 콘솔 관리자 계정
-- 관리자 사번, 전화번호, 비밀번호 해시, 권한, 상태를 저장합니다.
-- password_hash에는 평문 비밀번호를 넣지 말고 bcrypt 또는 argon2 해시만 저장해야 합니다.
CREATE TABLE IF NOT EXISTS admin_accounts (
    admin_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    employee_no VARCHAR(50) NOT NULL COMMENT '관리자 사번 또는 내부 ID',
    name VARCHAR(50) NOT NULL COMMENT '관리자 이름',
    phone VARCHAR(30) NOT NULL COMMENT '관리자 전화번호',
    password_hash VARCHAR(255) NOT NULL COMMENT '평문 비밀번호 저장 금지: bcrypt 또는 argon2 해시',
    role ENUM('super_admin', 'operator', 'viewer') NOT NULL DEFAULT 'operator' COMMENT '관리자 권한',
    status ENUM('active', 'inactive', 'locked', 'deleted') NOT NULL DEFAULT 'active' COMMENT '계정 상태',
    last_login_at DATETIME(6) NULL COMMENT '마지막 로그인 시각',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    deleted_at DATETIME(6) NULL COMMENT '소프트 삭제 시각',
    PRIMARY KEY (admin_id),
    UNIQUE KEY uk_admin_accounts_employee_no (employee_no),
    UNIQUE KEY uk_admin_accounts_phone (phone),
    KEY idx_admin_accounts_role_status (role, status),
    KEY idx_admin_accounts_created_at (created_at)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='운영자 콘솔 관리자 계정';

-- admin_accounts 인덱스 의도:
-- - employee_no, phone은 중복 관리자 등록을 막습니다.
-- - role + status는 활성 운영자, 조회 전용 계정, 잠긴 계정 목록 조회에 유리합니다.
-- - created_at은 생성일 기준 정렬과 기간 조회에 사용합니다.

-- 2. 앱 사용자 기본 정보
-- 시각장애인 앱 사용자의 이름, 장애 등급 또는 정도, 전화번호, 비상 연락처,
-- 접근성 메모를 저장합니다.
CREATE TABLE IF NOT EXISTS app_users (
    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL COMMENT '사용자 이름',
    disability_grade VARCHAR(30) NOT NULL COMMENT '장애 등급 또는 장애 정도',
    phone VARCHAR(30) NOT NULL COMMENT '사용자 전화번호',
    emergency_contact_name VARCHAR(50) NULL COMMENT '비상 연락처 이름',
    emergency_contact_phone VARCHAR(30) NULL COMMENT '비상 연락처 전화번호',
    accessibility_note VARCHAR(500) NULL COMMENT '보행 안내, 음성 안내, 접근성 관련 메모',
    status ENUM('active', 'inactive', 'deleted') NOT NULL DEFAULT 'active' COMMENT '사용자 상태',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    deleted_at DATETIME(6) NULL COMMENT '소프트 삭제 시각',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_app_users_phone (phone),
    KEY idx_app_users_status (status),
    KEY idx_app_users_disability_grade (disability_grade),
    KEY idx_app_users_created_at (created_at)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='시각장애인 앱 사용자 기본 정보';

-- app_users 인덱스 의도:
-- - phone은 사용자 중복 등록을 방지합니다.
-- - status는 활성/비활성/삭제 처리 사용자 필터링에 사용합니다.
-- - disability_grade는 장애 정도별 통계와 운영 조회에 활용할 수 있습니다.

-- 3. 앱 사용자 단말 및 WebSocket 인증 정보
-- React Native 앱 설치 단말을 사용자와 연결하고,
-- device_uuid, 플랫폼, WebSocket 토큰 해시, 마지막 접속 시각을 관리합니다.
-- ws_token_hash에도 인증 토큰 원문이 아니라 해시값만 저장하는 것을 전제로 합니다.
CREATE TABLE IF NOT EXISTS user_devices (
    device_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    device_uuid VARCHAR(100) NOT NULL COMMENT '앱 설치 단말 고유 식별자',
    device_name VARCHAR(100) NULL COMMENT '기기 이름',
    platform ENUM('ios', 'android', 'unknown') NOT NULL DEFAULT 'unknown',
    ws_token_hash VARCHAR(255) NULL COMMENT 'WebSocket 인증 토큰 해시',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    last_seen_at DATETIME(6) NULL COMMENT '마지막 접속 시각',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (device_id),
    UNIQUE KEY uk_user_devices_device_uuid (device_uuid),
    KEY idx_user_devices_user_id_active (user_id, is_active),
    KEY idx_user_devices_last_seen_at (last_seen_at),
    CONSTRAINT fk_user_devices_app_users
        FOREIGN KEY (user_id)
        REFERENCES app_users (user_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='앱 사용자 단말 및 WebSocket 인증 정보';

-- user_devices 관계와 인덱스 의도:
-- - user_id 외래 키로 사용자 없는 단말 등록을 방지합니다.
-- - ON DELETE CASCADE는 사용자를 물리 삭제할 때 단말도 함께 삭제합니다.
--   운영에서는 가능하면 app_users.status와 deleted_at 기반 소프트 삭제를 우선 검토하십시오.
-- - user_id + is_active는 특정 사용자의 활성 단말 목록 조회에 유리합니다.
-- - last_seen_at은 최근 접속 단말과 장기 미접속 단말 정리에 활용합니다.

-- 4. 관리자 로그인 감사 로그
-- 관리자 로그인 성공/실패 이력을 남겨 보안 감사와 계정 잠금 정책에 활용합니다.
-- 계정이 없거나 삭제된 사번으로 실패해도 employee_no 문자열 기준으로 추적할 수 있습니다.
CREATE TABLE IF NOT EXISTS admin_login_audits (
    audit_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    admin_id BIGINT UNSIGNED NULL,
    employee_no VARCHAR(50) NOT NULL COMMENT '로그인 시도 사번',
    success TINYINT(1) NOT NULL DEFAULT 0,
    failure_reason VARCHAR(100) NULL,
    ip_address VARCHAR(45) NULL COMMENT 'IPv4 또는 IPv6 주소',
    user_agent VARCHAR(255) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (audit_id),
    KEY idx_admin_login_audits_admin_id_created_at (admin_id, created_at),
    KEY idx_admin_login_audits_employee_no_created_at (employee_no, created_at),
    CONSTRAINT fk_admin_login_audits_admin_accounts
        FOREIGN KEY (admin_id)
        REFERENCES admin_accounts (admin_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='관리자 로그인 성공 및 실패 이력';

-- admin_login_audits 관계와 인덱스 의도:
-- - admin_id + created_at은 특정 관리자 계정의 로그인 이력 조회에 유리합니다.
-- - employee_no + created_at은 없는 사번 또는 반복 실패 사번 추적에 유리합니다.
-- - ON DELETE SET NULL은 관리자 계정이 물리 삭제되어도 감사 로그 자체를 보존합니다.

-- 5. 실행 후 빠른 확인
-- 테이블 생성 여부를 눈으로 확인합니다. 상세 구조 검증은 SHOW CREATE TABLE을 사용하십시오.
SHOW TABLES;

-- 필요 시 아래 검증 쿼리를 선택 실행하십시오.
-- SHOW CREATE TABLE admin_accounts;
-- SHOW CREATE TABLE app_users;
-- SHOW CREATE TABLE user_devices;
-- SHOW CREATE TABLE admin_login_audits;
-- SELECT table_name, constraint_name, referenced_table_name
-- FROM information_schema.key_column_usage
-- WHERE table_schema = 'minchodan_tmp'
--   AND referenced_table_name IS NOT NULL;
