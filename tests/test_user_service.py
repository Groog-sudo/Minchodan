"""
관리자 회원 등록/전환(UserService.register_or_convert_member) 검증.

인메모리 SQLite로 실제 DB 왕복을 확인한다:
- 신규 device_uuid 등록 시 신규 AppUser/UserDevice 생성
- 같은 phone으로 다른 기기 추가 시 기존 회원 재사용(신규 AppUser 미생성)
- 익명 자동등록 상태(anon: 접두사)인 device_uuid에 실명 등록 시 기존 행이
  UPDATE되고 새 행이 생기지 않는지(user_id 불변)
- 다른 회원이 쓰는 phone으로 전환 시도 시 409
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.db.models import AppUser, Base, DevicePlatform, UserDevice
from server.db.schemas import MemberRegisterRequest
from server.services.user_service import UserService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed_anonymous_device(session: AsyncSession, device_uuid: str) -> tuple[int, int]:
    """device_registry_service.ensure_device_registered가 만드는 것과 동일한 형태로
    익명 회원+기기 행을 미리 만들어둔다(실제 함수를 호출하지 않고 직접 시딩)."""
    user = AppUser(
        name=f"익명 단말({device_uuid})",
        phone=f"anon:{device_uuid}",
        disability_severity="미상",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    device = UserDevice(
        user_id=user.user_id, device_uuid=device_uuid, platform=DevicePlatform.UNKNOWN
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return user.user_id, device.device_id


@pytest.mark.asyncio
async def test_register_new_device_creates_user_and_device(db_session: AsyncSession) -> None:
    service = UserService(db_session)
    payload = MemberRegisterRequest(
        device_uuid="dev-new-001", name="홍길동", phone="010-1111-2222", disability_severity="1급"
    )

    result = await service.register_or_convert_member(payload)

    assert result.name == "홍길동"
    assert result.phone == "010-1111-2222"

    device_count = await db_session.execute(select(UserDevice))
    assert len(device_count.scalars().all()) == 1


@pytest.mark.asyncio
async def test_register_same_phone_reuses_existing_user(db_session: AsyncSession) -> None:
    service = UserService(db_session)
    first = await service.register_or_convert_member(
        MemberRegisterRequest(
            device_uuid="dev-a", name="김철수", phone="010-3333-4444", disability_severity="2급"
        )
    )
    second = await service.register_or_convert_member(
        MemberRegisterRequest(
            device_uuid="dev-b", name="김철수", phone="010-3333-4444", disability_severity="2급"
        )
    )

    assert first.user_id == second.user_id
    user_count = await db_session.execute(select(AppUser))
    assert len(user_count.scalars().all()) == 1
    device_count = await db_session.execute(select(UserDevice))
    assert len(device_count.scalars().all()) == 2


@pytest.mark.asyncio
async def test_register_anonymous_device_converts_in_place(db_session: AsyncSession) -> None:
    device_uuid = "dev-001"
    anon_user_id, anon_device_id = await _seed_anonymous_device(db_session, device_uuid)

    service = UserService(db_session)
    result = await service.register_or_convert_member(
        MemberRegisterRequest(
            device_uuid=device_uuid, name="이영희", phone="010-5555-6666", disability_severity="3급"
        )
    )

    # 기존 익명 레코드가 그대로 갱신됐어야 한다 (user_id 불변, 신규 행 미생성).
    assert result.user_id == anon_user_id
    assert result.name == "이영희"
    assert result.phone == "010-5555-6666"
    assert not result.phone.startswith("anon:")

    user_count = await db_session.execute(select(AppUser))
    assert len(user_count.scalars().all()) == 1
    device_count = await db_session.execute(select(UserDevice))
    devices = device_count.scalars().all()
    assert len(devices) == 1
    assert devices[0].device_id == anon_device_id
    assert devices[0].user_id == anon_user_id


@pytest.mark.asyncio
async def test_register_conflicting_phone_raises_409(db_session: AsyncSession) -> None:
    device_uuid = "dev-002"
    await _seed_anonymous_device(db_session, device_uuid)

    service = UserService(db_session)
    # 다른 회원이 이미 쓰고 있는 phone
    await service.register_or_convert_member(
        MemberRegisterRequest(
            device_uuid="dev-other", name="박민수", phone="010-7777-8888", disability_severity="1급"
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.register_or_convert_member(
            MemberRegisterRequest(
                device_uuid=device_uuid,
                name="이영희",
                phone="010-7777-8888",
                disability_severity="3급",
            )
        )
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_list_members_includes_devices_and_anonymous_flag(db_session: AsyncSession) -> None:
    await _seed_anonymous_device(db_session, "dev-anon")
    service = UserService(db_session)
    await service.register_or_convert_member(
        MemberRegisterRequest(
            device_uuid="dev-real", name="정real", phone="010-9999-0000", disability_severity="2급"
        )
    )

    members = await service.list_members(limit=20, offset=0)
    assert await service.count_members() == 2

    by_uuid = {m.devices[0].device_uuid: m for m in members if m.devices}
    assert by_uuid["dev-anon"].is_anonymous is True
    assert by_uuid["dev-real"].is_anonymous is False
