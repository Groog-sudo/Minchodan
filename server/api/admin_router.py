# -*- coding: utf-8 -*-
"""관리자 부트스트랩, 계정 생성, 로그인 및 단말 토큰 발급 API."""

from __future__ import annotations

import hmac
import os
import re
import sys

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.auth import issue_device_token
from server.api.dependencies import require_operator, require_super_admin
from server.api.rate_limit import enforce_rate_limit
from server.db.connection import get_db
from server.db.models import AdminAccountStatus, AdminRole
from server.db.schemas import (
    AdminAccountCreate,
    AdminAccountResponse,
    AdminBootstrapCreate,
    TokenResponse,
)
from server.services.admin_service import AdminService

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/bootstrap", response_model=AdminAccountResponse, status_code=status.HTTP_201_CREATED)
async def bootstrap_admin(
    payload: AdminBootstrapCreate,
    request: Request,
    bootstrap_token: str | None = Header(default=None, alias="X-Admin-Bootstrap-Token"),
    db: AsyncSession = Depends(get_db),
) -> AdminAccountResponse:
    """관리자 테이블이 비어 있을 때만 최초 최고관리자를 1회 생성한다."""
    await enforce_rate_limit(
        "admin-bootstrap",
        _client_ip(request),
        limit=3,
        window_seconds=600,
    )
    expected = os.getenv("ADMIN_BOOTSTRAP_TOKEN", "").strip()
    if (
        len(expected) < 32
        or not bootstrap_token
        or not hmac.compare_digest(expected, bootstrap_token)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    service = AdminService(db)
    if await service.admin_repo.count() != 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="관리자 부트스트랩이 이미 완료되었습니다.",
        )
    create = AdminAccountCreate(
        employee_no=payload.employee_no,
        name=payload.name,
        password=payload.password,
        role=AdminRole.SUPER_ADMIN,
        status=AdminAccountStatus.ACTIVE,
    )
    return await service.register_admin(create)


@router.post("/register", response_model=AdminAccountResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(
    admin_data: AdminAccountCreate,
    _super_admin: str = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminAccountResponse:
    """최고관리자가 추가 관리자 계정을 생성한다."""
    return await AdminService(db).register_admin(admin_data)


@router.post("/login", response_model=TokenResponse)
async def login_admin(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    employee_no = form_data.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,50}", employee_no):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    await enforce_rate_limit(
        "admin-login-ip",
        _client_ip(request),
        limit=20,
        window_seconds=300,
    )
    await enforce_rate_limit(
        "admin-login",
        f"{_client_ip(request)}:{employee_no}",
        limit=5,
        window_seconds=300,
    )
    return await AdminService(db).login(
        employee_no=employee_no,
        password=form_data.password,
    )


@router.post("/device-tokens/{device_id}", response_model=TokenResponse)
async def create_device_token(
    device_id: str,
    _operator: str = Depends(require_operator),
) -> TokenResponse:
    """인증된 운영자가 만료 가능한 단말 JWT를 발급한다."""
    normalized = device_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="device_id가 올바르지 않습니다."
        )
    await enforce_rate_limit(
        "device-token-issue",
        _operator,
        limit=30,
        window_seconds=60,
    )
    return TokenResponse(access_token=issue_device_token(normalized))
