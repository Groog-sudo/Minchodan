# -*- coding: utf-8 -*-
"""관리자 인증과 역할 기반 접근 제어 의존성."""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.connection import get_db
from server.db.models import AdminAccount, AdminAccountStatus, AdminRole
from server.db.repositories import AdminRepository
from server.db.security import decode_access_token

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admin/login", auto_error=False)


def _unauthorized(detail: str = "유효한 관리자 인증이 필요합니다.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authenticate_admin_token(token: str, db: AsyncSession) -> AdminAccount:
    """JWT와 현재 DB 관리자 계정 상태·역할을 함께 검증한다."""
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        logger.warning("서명 또는 만료 검증에 실패한 관리자 토큰 접근 시도")
        raise _unauthorized("토큰이 만료되었거나 유효하지 않습니다.") from None

    employee_no = payload.get("sub")
    if payload.get("type") != "admin" or not isinstance(employee_no, str) or not employee_no:
        raise _unauthorized("관리자 토큰 형식이 올바르지 않습니다.")

    admin = await AdminRepository(db).get_by_employee_no(employee_no)
    if admin is None or admin.status is not AdminAccountStatus.ACTIVE:
        raise _unauthorized("활성 관리자 계정을 찾을 수 없습니다.")
    if payload.get("role") != admin.role.value:
        raise _unauthorized("관리자 역할 정보가 변경되었습니다. 다시 로그인하세요.")
    return admin


async def get_current_admin_account(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminAccount:
    if not token:
        raise _unauthorized()
    return await authenticate_admin_token(token, db)


async def get_current_admin(admin: AdminAccount = Depends(get_current_admin_account)) -> str:
    """읽기 권한을 포함한 모든 활성 관리자 사번을 반환한다."""
    return admin.employee_no


async def require_operator(admin: AdminAccount = Depends(get_current_admin_account)) -> str:
    """데이터 변경이 가능한 운영자 또는 최고관리자만 허용한다."""
    if admin.role not in {AdminRole.SUPER_ADMIN, AdminRole.OPERATOR}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="운영자 권한이 필요합니다."
        )
    return admin.employee_no


async def require_super_admin(admin: AdminAccount = Depends(get_current_admin_account)) -> str:
    """최고관리자 전용 작업을 보호한다."""
    if admin.role is not AdminRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="최고관리자 권한이 필요합니다.",
        )
    return admin.employee_no
