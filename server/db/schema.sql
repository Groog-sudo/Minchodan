-- Minchodan SQLite 초기 스키마 DDL
-- FastAPI 비동기 SQLite 연결에서 앱 사용자, 단말, 관리자, 로그인 감사 테이블을 생성합니다.
-- AI(Vibe) 위임 영역: DDL은 반복 산출물이므로 AI로 생성하되, FK와 UNIQUE 제약은 반드시 검토합니다.
-- 발표 방어의 핵심 설명은 server/db/models.py의 ORM 매핑 주석을 기준으로 준비합니다.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    disability_severity VARCHAR(30) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'deleted')),
    CONSTRAINT UK_APP_USERS_PHONE UNIQUE (phone)
);

CREATE INDEX IF NOT EXISTS IDX_APP_USERS_DISABILITY_SEVERITY
    ON app_users (disability_severity);

CREATE INDEX IF NOT EXISTS IDX_APP_USERS_STATUS
    ON app_users (status);

CREATE TABLE IF NOT EXISTS user_devices (
    device_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    device_uuid VARCHAR(100) NOT NULL,
    platform VARCHAR(10) NOT NULL DEFAULT 'unknown'
        CHECK (platform IN ('ios', 'android', 'unknown')),
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    CONSTRAINT UK_USER_DEVICES_DEVICE_UUID UNIQUE (device_uuid),
    CONSTRAINT FK_USER_DEVICES_APP_USERS
        FOREIGN KEY (user_id)
        REFERENCES app_users (user_id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS IDX_USER_DEVICES_USER_ID
    ON user_devices (user_id);

CREATE TABLE IF NOT EXISTS admin_accounts (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_no VARCHAR(50) NOT NULL,
    name VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'operator'
        CHECK (role IN ('super_admin', 'operator', 'viewer')),
    status VARCHAR(10) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'locked', 'deleted')),
    CONSTRAINT UK_ADMIN_ACCOUNTS_EMPLOYEE_NO UNIQUE (employee_no)
);

CREATE INDEX IF NOT EXISTS IDX_ADMIN_ACCOUNTS_ROLE
    ON admin_accounts (role);

CREATE TABLE IF NOT EXISTS admin_login_audits (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_no VARCHAR(50) NOT NULL,
    success INTEGER NOT NULL DEFAULT 0
        CHECK (success IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS IDX_ADMIN_LOGIN_AUDITS_EMPLOYEE_NO
    ON admin_login_audits (employee_no);
