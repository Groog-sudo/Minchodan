"""
관리자용 시각장애인 회원(app_users) 등록/조회 라우터.

콘솔의 "회원 관리" 화면이 사용한다:
- GET  /api/v1/admin/members: 등록 회원 목록(기기 포함, 페이지네이션)
- POST /api/v1/admin/members: 회원 등록 - device_uuid가 이미 익명 자동등록
  상태(server/services/device_registry_service.py)면 실명으로 전환, 없으면 신규 등록.

인증: get_current_admin (다른 관리자 API와 동일 수준 - 세분화된 역할 권한 체크는
이번 스코프 밖).
"""

import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.dependencies import get_current_admin
from server.db.connection import get_db
from server.db.schemas import AppUserResponse, AppUserWithDevicesResponse, MemberRegisterRequest
from server.services.user_service import UserService

router = APIRouter(prefix="/api/v1/admin/members", tags=["admin"])


@router.get("", response_model=list[AppUserWithDevicesResponse])
async def list_members(
    response: Response,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_id: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AppUserWithDevicesResponse]:
    """등록된 회원 목록을 최신순으로 반환한다. 전체 건수는 X-Total-Count 헤더로
    함께 내려준다(콘솔 페이지네이션이 detection-logs와 동일 패턴으로 사용)."""
    service = UserService(db)
    total = await service.count_members()
    response.headers["X-Total-Count"] = str(total)
    return await service.list_members(limit=limit, offset=offset)


@router.post("", response_model=AppUserResponse, status_code=status.HTTP_201_CREATED)
async def register_member(
    payload: MemberRegisterRequest,
    admin_id: str = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> AppUserResponse:
    """회원을 등록하거나(신규 device_uuid) 기존 익명 자동등록 레코드를 실명으로 전환한다."""
    service = UserService(db)
    return await service.register_or_convert_member(payload)
