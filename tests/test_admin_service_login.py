import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.db.models import AdminAccount, AdminAccountStatus, AdminLoginAudit, AdminRole, Base
from server.db.repositories import AuditRepository
from server.db.security import get_password_hash
from server.services.admin_service import AdminService

# ============================================================
# 테스트 파일 역할
# ============================================================
# server/services/admin_service.py의 login()이 실제로 DB 검증을 거치는지 검증한다.
# 2026-07-09 이전에는 employee_no/password 조합과 무관하게 무조건 통과해 유효한 JWT를
# 발급하는 우회 코드가 dev 브랜치에 병합돼 있었다(회귀 방지 목적). 실제 원격 MariaDB
# 없이도 검증 가능하도록 in-memory SQLite로 스키마를 구성한다.


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_admin(
    session: AsyncSession,
    employee_no: str = "EMP001",
    password: str = "correct-password",  # noqa: S107 (테스트 픽스처 기본값, 실제 비밀번호 아님)
    status: AdminAccountStatus = AdminAccountStatus.ACTIVE,
    role: AdminRole = AdminRole.OPERATOR,
) -> None:
    session.add(
        AdminAccount(
            employee_no=employee_no,
            name="테스트 관리자",
            password_hash=get_password_hash(password),
            role=role,
            status=status,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_login_wrong_password_raises_401(db_session: AsyncSession) -> None:
    await _seed_admin(db_session, employee_no="EMP001", password="correct-password")
    service = AdminService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(employee_no="EMP001", password="wrong-password")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_employee_no_raises_401_not_500(db_session: AsyncSession) -> None:
    service = AdminService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(employee_no="NOT-EXIST", password="anything")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_locked_account_raises_403(db_session: AsyncSession) -> None:
    await _seed_admin(
        db_session,
        employee_no="EMP002",
        password="correct-password",
        status=AdminAccountStatus.LOCKED,
    )
    service = AdminService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(employee_no="EMP002", password="correct-password")

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_login_success_issues_token_with_real_role(db_session: AsyncSession) -> None:
    await _seed_admin(
        db_session,
        employee_no="EMP003",
        password="correct-password",
        role=AdminRole.SUPER_ADMIN,
    )
    service = AdminService(db_session)

    result = await service.login(employee_no="EMP003", password="correct-password")

    assert result.access_token
    assert result.token_type == "bearer"  # noqa: S105 (OAuth2 표준 토큰 타입 상수, 비밀값 아님)


@pytest.mark.asyncio
async def test_login_failure_is_recorded_in_audit_log(db_session: AsyncSession) -> None:
    await _seed_admin(db_session, employee_no="EMP004", password="correct-password")
    service = AdminService(db_session)

    with pytest.raises(HTTPException):
        await service.login(employee_no="EMP004", password="wrong-password")

    audit_repo = AuditRepository(db_session)
    result = await audit_repo.session.execute(select(AdminLoginAudit))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].employee_no == "EMP004"
