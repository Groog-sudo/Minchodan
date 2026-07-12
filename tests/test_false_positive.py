import os
import sys
from datetime import UTC, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.db.connection import get_db
from server.db.models import Base, DetectionGuidanceLog, StreamType
from server.db.repositories import DetectionGuidanceLogRepository
from server.main import app
from server.services.detection_guidance_log_service import DetectionGuidanceLogService

# ============================================================
# 테스트 파일 역할
# ============================================================
# 오탐 판정(false_positive) 업데이트 기능의 Repository, Service, Router API를 검증합니다.
# 인메모리 SQLite DB를 활용하여 데이터베이스의 정밀한 상태 변화를 체크합니다.


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # 테스트용 관리자 의존성도 우회 설정 (테스트 클라이언트에서 get_current_admin 우회)
    from server.api.dependencies import get_current_admin

    app.dependency_overrides[get_current_admin] = lambda: "admin-id-001"

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


async def _seed_log(session: AsyncSession) -> DetectionGuidanceLog:
    log = DetectionGuidanceLog(
        event_id="event-test-12345",
        detected_at=datetime.now(UTC),
        stream_type=StreamType.COGNITIVE,
        detected_objects_json="[]",
        tts_text="테스트 안내",
        frame_path="20260712/test.jpg",
        false_positive=None,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


@pytest.mark.asyncio
async def test_repository_update_false_positive(db_session: AsyncSession) -> None:
    log = await _seed_log(db_session)
    repo = DetectionGuidanceLogRepository(db_session)

    # 1. True로 업데이트
    updated = await repo.update_false_positive(log.log_id, True)
    assert updated is not None
    assert updated.false_positive is True

    # 2. 다시 False로 업데이트
    updated = await repo.update_false_positive(log.log_id, False)
    assert updated is not None
    assert updated.false_positive is False

    # 3. 존재하지 않는 log_id
    not_found = await repo.update_false_positive(9999, True)
    assert not_found is None


@pytest.mark.asyncio
async def test_service_update_false_positive(db_session: AsyncSession) -> None:
    log = await _seed_log(db_session)
    service = DetectionGuidanceLogService(db_session)

    # 1. True로 업데이트
    res = await service.update_false_positive(log.log_id, True)
    assert res is not None
    assert res.false_positive is True

    # 2. 존재하지 않는 log_id
    res_none = await service.update_false_positive(9999, True)
    assert res_none is None


@pytest.mark.asyncio
async def test_api_update_false_positive(client: TestClient, db_session: AsyncSession) -> None:
    log = await _seed_log(db_session)

    # 1. API 호출 (True)
    payload = {"false_positive": True}
    response = client.put(f"/api/v1/admin/detection-logs/{log.log_id}/false-positive", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["false_positive"] is True

    # 2. 존재하지 않는 로그 (404)
    response_404 = client.put("/api/v1/admin/detection-logs/9999/false-positive", json=payload)
    assert response_404.status_code == 404
