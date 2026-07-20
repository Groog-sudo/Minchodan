# -*- coding: utf-8 -*-
"""WebSocket 디바이스 토큰 발급·검증 모듈."""

from __future__ import annotations

import contextlib
import hmac
import logging
import os
import sys
from datetime import timedelta

import jwt

from server.db.security import create_access_token, decode_access_token

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_registered_devices() -> dict[str, str]:
    """명시적으로 허용한 개발 환경에서만 정적 토큰을 로드한다."""
    raw = os.getenv("DEVICE_STATIC_TOKENS", "").strip()
    if not raw:
        return {}
    if not _env_flag("ALLOW_STATIC_DEVICE_TOKENS"):
        logger.warning(
            "[Auth] DEVICE_STATIC_TOKENS가 설정됐지만 ALLOW_STATIC_DEVICE_TOKENS가 "
            "비활성화되어 정적 토큰을 사용하지 않습니다."
        )
        return {}

    devices: dict[str, str] = {}
    for item in raw.split(","):
        device_id, separator, token = item.strip().partition(":")
        if not separator or not device_id or len(token) < 32:
            logger.warning("[Auth] 형식 또는 길이가 잘못된 정적 디바이스 토큰을 무시합니다.")
            continue
        devices[device_id] = token
    return devices


REGISTERED_DEVICES: dict[str, str] = _load_registered_devices()


def issue_device_token(device_id: str) -> str:
    """기본 30일 만료의 단말 전용 JWT를 발급한다."""
    expire_days = max(1, int(os.getenv("DEVICE_TOKEN_EXPIRE_DAYS", "30")))
    return create_access_token(
        {"device_id": device_id, "sub": device_id, "type": "device"},
        expires_delta=timedelta(days=expire_days),
    )


def _verify_static_token(device_id: str, token: str) -> bool:
    expected_token = REGISTERED_DEVICES.get(device_id)
    return expected_token is not None and hmac.compare_digest(expected_token, token)


def _verify_jwt_token(device_id: str, token: str) -> bool:
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        return False
    return (
        payload.get("type") == "device"
        and payload.get("device_id") == device_id
        and payload.get("sub") == device_id
    )


async def verify_device(device_id: str, token: str) -> bool:
    """정적 개발 토큰 또는 만료 가능한 단말 JWT를 검증한다."""
    if not device_id or not token:
        return False
    if _verify_static_token(device_id, token) or _verify_jwt_token(device_id, token):
        logger.info("[Auth] 디바이스 인증 성공: device_id=%s", device_id)
        return True
    logger.warning("[Auth] 디바이스 토큰 검증 실패: device_id=%s", device_id)
    return False
