# -*- coding: utf-8 -*-
"""비밀번호 해시와 JWT 발급·검증을 담당하는 보안 모듈."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import bcrypt
import jwt
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 인증 모듈은 다른 라우터보다 먼저 import될 수 있다. 이 파일 자체가 프로젝트 루트
# .env를 먼저 로드해 import 순서에 따라 개발용 인증으로 폴백하는 상황을 차단한다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

ALGORITHM = "HS256"
JWT_ISSUER = os.getenv("JWT_ISSUER", "minchodan-api").strip()
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "minchodan-clients").strip()
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "8"))

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
_FORBIDDEN_SECRET_KEYS = {
    "minchodan_secret_key_12345",
    "change-me",
    "changeme",
    "your-secret-key",
}
if len(SECRET_KEY) < 32 or SECRET_KEY.lower() in _FORBIDDEN_SECRET_KEYS:
    raise RuntimeError(
        "JWT_SECRET_KEY는 예측 불가능한 32자 이상의 값이어야 합니다. "
        "scripts/configure_security_secrets.py를 실행해 로컬 비밀값을 생성하세요."
    )


def get_password_hash(password: str) -> str:
    """bcrypt로 관리자 비밀번호를 해시한다."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 저장된 bcrypt 해시를 상수시간 비교한다."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """필수 표준 클레임을 포함한 서명 JWT를 발급한다."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    payload = data.copy()
    payload.update(
        {
            "aud": JWT_AUDIENCE,
            "exp": expire,
            "iat": now,
            "iss": JWT_ISSUER,
            "jti": uuid4().hex,
            "nbf": now,
        }
    )
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """서명, 만료, 발급자, 대상 및 필수 클레임을 모두 검증한다."""
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["aud", "exp", "iat", "iss", "jti", "nbf"]},
    )
