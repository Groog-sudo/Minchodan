"""
Minchodan 관계형 DB SQLAlchemy 2.0 ORM 모델.
SQLite 비동기 연결에서도 동작하도록 enum은 문자열 제약으로 저장합니다.

하드코딩 및 발표 방어 영역:
- 이 파일은 DB 테이블을 파이썬 클래스로 매핑하는 핵심 데이터 구조입니다.
- `Mapped[타입]`은 파이썬 객체에서 보이는 필드 타입을 설명합니다.
- `mapped_column(...)`은 실제 DB 컬럼 타입, PK, UNIQUE, FK, 기본값을 설명합니다.
- `relationship(...)`과 `ForeignKey(...)`는 테이블 사이의 연관 관계를 코드로 증명하는 부분입니다.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# 모든 ORM 모델은 Base를 상속받아야 Base.metadata에 테이블 정의가 모입니다.
# 발표 포인트: DB 초기화 코드는 이 metadata를 보고 CREATE TABLE을 수행할 수 있습니다.
class Base(DeclarativeBase):
    """프로젝트 전체 ORM 모델의 공통 Declarative Base.

    DB 초기화 시 연결 모듈에서 Base.metadata를 기준으로 테이블을 생성합니다.
    """


# 아래 enum들은 DB에 들어갈 수 있는 값의 후보를 파이썬 타입으로 고정합니다.
# 발표 포인트: 문자열을 아무렇게나 넣지 못하게 하고, API DTO와 ORM이 같은 값을 공유합니다.
class UserStatus(StrEnum):
    """앱 사용자 계정 상태."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class DevicePlatform(StrEnum):
    """등록 단말 플랫폼."""

    IOS = "ios"
    ANDROID = "android"
    UNKNOWN = "unknown"


class AdminRole(StrEnum):
    """관리자 권한 등급."""

    SUPER_ADMIN = "super_admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class AdminAccountStatus(StrEnum):
    """관리자 계정 상태."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    DELETED = "deleted"


class StreamType(StrEnum):
    """탐지 스트림 유형 (반사/인지/미분류)."""

    REFLEX = "reflex"
    COGNITIVE = "cognitive"
    UNKNOWN = "unknown"


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """SQLAlchemy Enum이 enum name 대신 value를 저장하도록 값 목록을 반환합니다."""
    return [item.value for item in enum_cls]


# 발표 포인트:
# - Mapped[int]는 파이썬 객체에서 다룰 타입입니다.
# - mapped_column(...)은 실제 DB 컬럼 타입, PK, UNIQUE, FK 같은 제약을 선언합니다.
# - SQLite AUTOINCREMENT는 INTEGER PRIMARY KEY에서 가장 안정적이므로 sqlite만 Integer로 바꿉니다.
BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")


class AppUser(Base):
    """단말 앱 사용자."""

    # 하드코딩 포인트 1:
    # 클래스명은 파이썬에서 쓰는 이름이고, __tablename__은 실제 DB 테이블명입니다.
    # AppUser 클래스의 객체 1개는 app_users 테이블의 행 1개와 대응합니다.
    __tablename__ = "app_users"

    # 하드코딩 포인트 2:
    # __table_args__에는 컬럼 하나로 끝나지 않는 테이블 단위 제약과 인덱스를 둡니다.
    # phone은 회원 중복 가입을 막기 위해 UNIQUE, status는 조회 조건이 될 수 있어 INDEX를 둡니다.
    __table_args__ = (
        UniqueConstraint("phone", name="UK_APP_USERS_PHONE"),
        Index("IDX_APP_USERS_DISABILITY_SEVERITY", "disability_severity"),
        Index("IDX_APP_USERS_STATUS", "status"),
        {"sqlite_autoincrement": True},
    )

    # 하드코딩 포인트 3:
    # 왼쪽 `Mapped[int]`는 파이썬에서 user_id를 int로 다룬다는 뜻입니다.
    # 오른쪽 `mapped_column(...)`은 DB에서는 PK이자 자동 증가 컬럼이라는 뜻입니다.
    user_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)

    # 하드코딩 포인트 4:
    # nullable=False는 SQL의 NOT NULL입니다. 사용자 이름, 전화번호, 장애 정도는 필수값입니다.
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    disability_severity: Mapped[str] = mapped_column(String(30), nullable=False)

    # 하드코딩 포인트 5:
    # status는 단순 문자열이 아니라 UserStatus enum으로 제한합니다.
    # native_enum=False는 SQLite에서도 CHECK 제약 기반 문자열 enum처럼 동작하게 합니다.
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(
            UserStatus,
            name="user_status",
            values_callable=_enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )

    # 하드코딩 포인트 6:
    # 1명의 앱 사용자는 여러 단말을 가질 수 있으므로 AppUser -> UserDevice는 1:N입니다.
    # `list["UserDevice"]`가 바로 "여러 개"를 뜻합니다.
    # back_populates="user"는 UserDevice.user와 서로 연결되는 양방향 관계 이름입니다.
    # passive_deletes="all"은 부모 삭제 시 ORM이 자식 FK를 NULL로 바꾸지 않고 DB 제약에 맡깁니다.
    devices: Mapped[list[UserDevice]] = relationship(
        back_populates="user",
        passive_deletes="all",
    )

    # 발표 포인트:
    # app_users.user_id를 참조하는 로그 테이블(1:N) 관계입니다.
    # user가 삭제되면 로그의 user_id는 NULL로 남겨 이력 보존이 가능합니다.
    detection_guidance_logs: Mapped[list[DetectionGuidanceLog]] = relationship(
        back_populates="user",
        passive_deletes="all",
    )


class UserDevice(Base):
    """사용자 등록 단말."""

    # 하드코딩 포인트 7:
    # UserDevice 클래스의 객체 1개는 user_devices 테이블의 행 1개와 대응합니다.
    __tablename__ = "user_devices"

    # 하드코딩 포인트 8:
    # device_uuid는 실제 단말을 식별하므로 중복되면 안 됩니다.
    # user_id 인덱스는 "특정 사용자의 단말 목록 조회"를 빠르게 하기 위해 둡니다.
    __table_args__ = (
        UniqueConstraint("device_uuid", name="UK_USER_DEVICES_DEVICE_UUID"),
        Index("IDX_USER_DEVICES_USER_ID", "user_id"),
        {"sqlite_autoincrement": True},
    )

    device_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)

    # 하드코딩 포인트 9:
    # user_id는 user_devices가 app_users를 가리키는 외래키 컬럼입니다.
    # ForeignKey("app_users.user_id")는 DB 테이블명.컬럼명을 문자열로 적습니다.
    # ON DELETE RESTRICT는 단말이 남아 있는 사용자를 실수로 삭제하지 못하게 막습니다.
    # CASCADE는 부모 삭제 시 자식 단말까지 자동 삭제하므로 운영 데이터 손실 위험이 있습니다.
    user_id: Mapped[int] = mapped_column(
        BIGINT_PK,
        ForeignKey("app_users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_uuid: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[DevicePlatform] = mapped_column(
        SQLEnum(
            DevicePlatform,
            name="device_platform",
            values_callable=_enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=DevicePlatform.UNKNOWN,
        server_default=DevicePlatform.UNKNOWN.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    # 하드코딩 포인트 10:
    # user_devices의 각 행은 app_users의 부모 행 1개에 속합니다.
    # 따라서 UserDevice -> AppUser는 N:1 관계이고, 타입은 list가 아닌 단일 "AppUser"입니다.
    # back_populates 값은 AppUser.devices와 서로 맞물려 양방향 탐색을 가능하게 합니다.
    user: Mapped[AppUser] = relationship(back_populates="devices")

    # 발표 포인트:
    # user_devices.device_id를 참조하는 로그 테이블(1:N) 관계입니다.
    # 기기 삭제 시 로그는 남고 device_id만 NULL 처리됩니다.
    detection_guidance_logs: Mapped[list[DetectionGuidanceLog]] = relationship(
        back_populates="device",
        passive_deletes="all",
    )


class AdminAccount(Base):
    """운영자 콘솔 관리자 계정."""

    # 관리자 계정은 운영자 콘솔 로그인 주체입니다.
    # app_users와 직접 연결하지 않아 종단 사용자 계정과 운영자 계정을 분리합니다.
    __tablename__ = "admin_accounts"
    __table_args__ = (
        UniqueConstraint("employee_no", name="UK_ADMIN_ACCOUNTS_EMPLOYEE_NO"),
        Index("IDX_ADMIN_ACCOUNTS_ROLE", "role"),
        {"sqlite_autoincrement": True},
    )

    admin_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        SQLEnum(
            AdminRole,
            name="admin_role",
            values_callable=_enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=AdminRole.OPERATOR,
        server_default=AdminRole.OPERATOR.value,
    )
    status: Mapped[AdminAccountStatus] = mapped_column(
        SQLEnum(
            AdminAccountStatus,
            name="admin_account_status",
            values_callable=_enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=AdminAccountStatus.ACTIVE,
        server_default=AdminAccountStatus.ACTIVE.value,
    )


class AdminLoginAudit(Base):
    """외래키 없이 보존하는 관리자 로그인 감사 로그.

    계정 삭제 또는 사번 재등록과 무관하게 과거 로그인 시도 기록을 유지합니다.
    """

    # 하드코딩 포인트 11:
    # 이 테이블은 일부러 ForeignKey를 걸지 않습니다.
    # 이유: 관리자 계정이 삭제되거나 사번이 재등록되어도 과거 로그인 시도 기록은 감사 목적으로 남겨야 합니다.
    __tablename__ = "admin_login_audits"
    __table_args__ = (
        Index("IDX_ADMIN_LOGIN_AUDITS_EMPLOYEE_NO", "employee_no"),
        {"sqlite_autoincrement": True},
    )

    audit_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )


class DetectionGuidanceLog(Base):
    """탐지/안내 결과 영속 로그 테이블 매핑.

    주의:
    - 테이블명은 요청 원문 기준으로 detction_guidance_logs(오탈자 포함)를 유지합니다.
    - event_id는 NULL 허용 + UNIQUE입니다(MySQL은 NULL을 여러 건 허용).
    - user/device 삭제 시 FK는 SET NULL로 이력 보존합니다.
    """

    __tablename__ = "detction_guidance_logs"
    __table_args__ = (
        UniqueConstraint("event_id", name="UK_DETCTION_GUIDANCE_LOGS_EVENT_ID"),
        Index("IDX_DETCTION_GUIDANCE_LOGS_USER_ID", "user_id"),
        Index("IDX_DETCTION_GUIDANCE_LOGS_DEVICE_ID", "device_id"),
        Index("IDX_DETCTION_GUIDANCE_LOGS_DETECTED_AT", "detected_at"),
        Index("IDX_DETCTION_GUIDANCE_LOGS_STREAM_TYPE", "stream_type"),
        {"sqlite_autoincrement": True},
    )

    log_id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        BIGINT_PK,
        ForeignKey("app_users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    device_id: Mapped[int | None] = mapped_column(
        BIGINT_PK,
        ForeignKey("user_devices.device_id", ondelete="SET NULL"),
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stream_type: Mapped[StreamType] = mapped_column(
        SQLEnum(
            StreamType,
            name="stream_type",
            values_callable=_enum_values,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=StreamType.UNKNOWN,
        server_default=StreamType.UNKNOWN.value,
    )
    detected_objects_json: Mapped[str] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"),
        nullable=False,
    )
    tts_text: Mapped[str] = mapped_column(Text, nullable=False)
    create_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    user: Mapped[AppUser | None] = relationship(back_populates="detection_guidance_logs")
    device: Mapped[UserDevice | None] = relationship(back_populates="detection_guidance_logs")


__all__ = [
    "AdminAccount",
    "AdminAccountStatus",
    "AdminLoginAudit",
    "AdminRole",
    "AppUser",
    "Base",
    "DetectionGuidanceLog",
    "DevicePlatform",
    "StreamType",
    "UserDevice",
    "UserStatus",
]
