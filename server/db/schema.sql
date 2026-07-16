-- Minchodan SQLite 초기 스키마 DDL
-- FastAPI 비동기 SQLite 연결에서 앱 사용자, 단말, 관리자, 로그인 감사, 탐지 안내 로그 테이블을 생성합니다.
-- AI(Vibe) 위임 영역: DDL은 반복 산출물이므로 AI로 생성하되, FK와 UNIQUE 제약은 반드시 검토합니다.
-- 발표 방어의 핵심 설명은 server/db/models.py의 ORM 매핑 주석을 기준으로 준비합니다.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    disability_severity VARCHAR(30) NOT NULL,
    birth_date DATE,
    guardian_phone VARCHAR(30),
    address VARCHAR(255),
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

-- 클라이언트 프레임 이벤트 기준의 탐지 시각, YOLO 결과, LLM/TTS 안내 문장을 보관합니다.
-- 사용자/기기 삭제 후에도 로그 이력은 남기기 위해 외래키는 ON DELETE SET NULL을 사용합니다.
CREATE TABLE IF NOT EXISTS detection_guidance_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id VARCHAR(64),
    user_id INTEGER,
    device_id INTEGER,
    detected_at DATETIME NOT NULL,
    stream_type VARCHAR(10) NOT NULL DEFAULT 'unknown'
        CHECK (stream_type IN ('reflex', 'cognitive', 'unknown')),
    detected_objects_json JSON NOT NULL,
    tts_text TEXT NOT NULL,
    frame_path VARCHAR(255),
    false_positive INTEGER CHECK (false_positive IN (0, 1)),
    latency_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_source VARCHAR(20) NOT NULL DEFAULT 'unknown',
    stt_transcript_text TEXT,
    stt_audio_path VARCHAR(255),
    stt_audio_storage_status VARCHAR(30) NOT NULL DEFAULT 'not_applicable',
    stt_audio_format VARCHAR(10),
    stt_audio_size_bytes BIGINT,
    stt_audio_duration_ms INTEGER,
    stt_audio_sha256 VARCHAR(64),
    stt_audio_error_code VARCHAR(64),
    stt_audio_consent_at DATETIME,
    stt_audio_expires_at DATETIME,
    writer_instance_id VARCHAR(100),
    CONSTRAINT UK_DETECTION_GUIDANCE_LOGS_EVENT_ID UNIQUE (event_id),
    CONSTRAINT FK_DETECTION_GUIDANCE_LOGS_APP_USERS
        FOREIGN KEY (user_id)
        REFERENCES app_users (user_id)
        ON DELETE SET NULL,
    CONSTRAINT FK_DETECTION_GUIDANCE_LOGS_USER_DEVICES
        FOREIGN KEY (device_id)
        REFERENCES user_devices (device_id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS IDX_DETECTION_GUIDANCE_LOGS_DETECTED_AT
    ON detection_guidance_logs (detected_at);

CREATE INDEX IF NOT EXISTS IDX_DETECTION_GUIDANCE_LOGS_USER_ID
    ON detection_guidance_logs (user_id);

CREATE INDEX IF NOT EXISTS IDX_DETECTION_GUIDANCE_LOGS_DEVICE_ID
    ON detection_guidance_logs (device_id);

CREATE INDEX IF NOT EXISTS IDX_DETECTION_GUIDANCE_LOGS_STREAM_TYPE
    ON detection_guidance_logs (stream_type);

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_event_source_detected_at
    ON detection_guidance_logs (event_source, detected_at);

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_stt_audio_status
    ON detection_guidance_logs (stt_audio_storage_status, detected_at);

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_stt_audio_path
    ON detection_guidance_logs (stt_audio_path);

CREATE INDEX IF NOT EXISTS idx_detection_guidance_logs_writer_instance_id
    ON detection_guidance_logs (writer_instance_id);
