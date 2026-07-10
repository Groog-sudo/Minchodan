"""
Minchodan DB 클라이언트 요청/응답 검증용 Pydantic V2 DTO 스키마.
Create 스키마와 Response 스키마를 분리합니다.

AI(Vibe) 위임 영역:
- 이 파일은 클라이언트 요청/응답 형태를 검증하는 반복 DTO 정의입니다.
- 핵심 DB 연관 관계는 `models.py`에서 설명하고, 이 파일은 API 경계의 데이터 모양만 관리합니다.
- 발표 때는 각 DTO가 "생성 입력"인지 "응답 출력"인지, Response에 `from_attributes=True`가 왜 필요한지만 설명하면 됩니다.
"""

from __future__ import annotations

import sys
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from server.db.models import (
    AdminAccountStatus,
    AdminRole,
    DevicePlatform,
    StreamType,
    UserStatus,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class AppUserCreate(BaseModel):
    """앱 사용자 생성 요청 DTO."""

    name: str = Field(..., min_length=1, max_length=50)
    phone: str = Field(..., min_length=1, max_length=30)
    disability_severity: str = Field(..., min_length=1, max_length=30)
    status: UserStatus = UserStatus.ACTIVE


class AppUserResponse(BaseModel):
    """앱 사용자 응답 DTO."""

    # ORM 객체를 Pydantic 응답 모델로 변환하기 위한 Pydantic V2 설정입니다.
    # 예: AppUser ORM 인스턴스 -> AppUserResponse
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    phone: str
    disability_severity: str
    status: UserStatus


class UserDeviceCreate(BaseModel):
    """사용자 단말 생성 요청 DTO."""

    user_id: int = Field(..., ge=1)
    device_uuid: str = Field(..., min_length=1, max_length=100)
    platform: DevicePlatform = DevicePlatform.UNKNOWN
    is_active: bool = True


class UserDeviceResponse(BaseModel):
    """사용자 단말 응답 DTO."""

    # Response 스키마는 DB에서 조회한 ORM 객체를 그대로 응답 형태로 바꿀 수 있어야 합니다.
    model_config = ConfigDict(from_attributes=True)

    device_id: int
    user_id: int
    device_uuid: str
    platform: DevicePlatform
    is_active: bool


class AdminAccountCreate(BaseModel):
    """관리자 계정 생성 요청 DTO."""

    employee_no: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=255)
    role: AdminRole = AdminRole.OPERATOR
    status: AdminAccountStatus = AdminAccountStatus.ACTIVE


class AdminAccountResponse(BaseModel):
    """관리자 계정 응답 DTO. 비밀번호 해시는 응답에 노출하지 않습니다."""

    # password_hash는 생성에는 필요하지만 응답에는 포함하지 않습니다.
    # 발표 포인트: API 응답 DTO는 DB 컬럼 전체를 그대로 노출하는 파일이 아닙니다.
    model_config = ConfigDict(from_attributes=True)

    admin_id: int
    employee_no: str
    name: str
    role: AdminRole
    status: AdminAccountStatus


class AdminLoginAuditCreate(BaseModel):
    """관리자 로그인 감사 로그 생성 요청 DTO."""

    employee_no: str = Field(..., min_length=1, max_length=50)
    success: bool = False


class AdminLoginAuditResponse(BaseModel):
    """관리자 로그인 감사 로그 응답 DTO."""

    # 감사 로그 조회 결과도 ORM 객체에서 바로 변환할 수 있게 합니다.
    model_config = ConfigDict(from_attributes=True)

    audit_id: int
    employee_no: str
    success: bool
    created_at: datetime


class DetectionGuidanceLogCreate(BaseModel):
    """탐지/안내 로그 생성 요청 DTO."""

    event_id: str | None = Field(default=None, max_length=64)
    user_id: int | None = Field(default=None, ge=1)
    device_id: int | None = Field(default=None, ge=1)
    detected_at: datetime
    stream_type: StreamType = StreamType.UNKNOWN
    detected_objects_json: str = Field(..., min_length=2)
    tts_text: str = Field(..., min_length=1)


class DetectionGuidanceLogResponse(BaseModel):
    """탐지/안내 로그 응답 DTO."""

    model_config = ConfigDict(from_attributes=True)

    log_id: int
    event_id: str | None
    user_id: int | None
    device_id: int | None
    detected_at: datetime
    stream_type: StreamType
    detected_objects_json: str
    tts_text: str
    created_at: datetime


class TokenResponse(BaseModel):
    """OAuth2 액세스 토큰 응답 DTO."""

    access_token: str
    token_type: str = "bearer"


__all__ = [
    "AdminAccountCreate",
    "AdminAccountResponse",
    "AdminLoginAuditCreate",
    "AdminLoginAuditResponse",
    "AppUserCreate",
    "AppUserResponse",
    "DetectionGuidanceLogCreate",
    "DetectionGuidanceLogResponse",
    "TokenResponse",
    "UserDeviceCreate",
    "UserDeviceResponse",
]
