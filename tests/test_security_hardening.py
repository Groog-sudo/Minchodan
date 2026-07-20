# -*- coding: utf-8 -*-
"""인증 기본값, JWT 계약, 비밀번호 정책 및 요청 제한 회귀 테스트."""

import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from server.api.auth import issue_device_token, verify_device
from server.api.rate_limit import enforce_rate_limit
from server.db.schemas import AdminAccountCreate
from server.db.security import create_access_token, decode_access_token

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def test_admin_password_policy_rejects_weak_password() -> None:
    with pytest.raises(ValidationError):
        AdminAccountCreate(
            employee_no="EMP-SEC-1",
            name="보안 테스트",
            password="password1234",
        )


def test_admin_token_contains_required_security_claims() -> None:
    token = create_access_token({"sub": "EMP-SEC-2", "role": "operator", "type": "admin"})
    payload = decode_access_token(token)

    assert payload["sub"] == "EMP-SEC-2"
    assert payload["type"] == "admin"
    assert all(claim in payload for claim in ("aud", "exp", "iat", "iss", "jti", "nbf"))


@pytest.mark.asyncio
async def test_device_jwt_is_bound_to_device_id() -> None:
    token = issue_device_token("device-secure-1")

    assert await verify_device("device-secure-1", token) is True
    assert await verify_device("device-secure-2", token) is False


@pytest.mark.asyncio
async def test_public_development_device_token_is_not_accepted() -> None:
    assert await verify_device("dev-001", "token-abc-001") is False


@pytest.mark.asyncio
async def test_rate_limiter_rejects_request_over_limit() -> None:
    identity = uuid4().hex
    await enforce_rate_limit("security-test", identity, limit=1, window_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        await enforce_rate_limit("security-test", identity, limit=1, window_seconds=60)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    assert "Retry-After" in exc_info.value.headers
