# -*- coding: utf-8 -*-
"""최초 관리자 부트스트랩과 공개 관리자 생성 차단 회귀 테스트."""

import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.api.admin_router import router
from server.db.connection import get_db
from server.db.models import Base

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BOOTSTRAP_TOKEN = "test-bootstrap-token-with-more-than-32-characters"  # noqa: S105


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(router)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setenv("ADMIN_BOOTSTRAP_TOKEN", BOOTSTRAP_TOKEN)
    with TestClient(app) as test_client:
        yield test_client


def test_bootstrap_requires_secret_and_runs_only_once(client: TestClient) -> None:
    payload = {
        "employee_no": "SEC-ADMIN-1",
        "name": "최초 관리자",
        "password": "StrongPassword!1",
    }

    missing_secret = client.post("/api/v1/admin/bootstrap", json=payload)
    assert missing_secret.status_code == 404

    created = client.post(
        "/api/v1/admin/bootstrap",
        json=payload,
        headers={"X-Admin-Bootstrap-Token": BOOTSTRAP_TOKEN},
    )
    assert created.status_code == 201
    assert created.json()["role"] == "super_admin"
    assert created.json()["status"] == "active"

    duplicate = client.post(
        "/api/v1/admin/bootstrap",
        json={**payload, "employee_no": "SEC-ADMIN-2"},
        headers={"X-Admin-Bootstrap-Token": BOOTSTRAP_TOKEN},
    )
    assert duplicate.status_code == 409


def test_public_admin_register_is_unauthorized(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/register",
        json={
            "employee_no": "SEC-ADMIN-2",
            "name": "공개 생성 차단",
            "password": "StrongPassword!2",
            "role": "super_admin",
            "status": "active",
        },
    )
    assert response.status_code == 401
