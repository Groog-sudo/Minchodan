import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

# ==========================================
# 🤖 VIBE AREA (AI 위임 영역)
# JWT 토큰 발급 및 Bcrypt 암호화 로직은 규격화된 보일러플레이트입니다.
# 라이브러리 사용법에 불과하므로 면접 비중이 낮습니다. AI 코드 복붙 권장.
# ==========================================

# 2026-07-11 인증 기본값 제거(dev 개선 계획서 §2): 운영 환경(APP_ENV=production)에서는
# JWT_SECRET_KEY 미설정 시 서버 기동을 거부한다(fail-closed). 개발 환경에서만 기존
# 임시 키로 폴백해 로컬 개발·테스트 하위 호환을 유지한다.
# 개발 전용 폴백 키(기존 코드의 getenv 기본 인자를 상수로 분리한 것으로 신규 비밀 아님).
# production에서는 위 fail-closed 가드가 이 값 사용을 차단한다.
_DEV_DEFAULT_SECRET_KEY = "minchodan_secret_key_12345"  # noqa: S105  # nosec B105

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
if not SECRET_KEY:
    if os.getenv("APP_ENV", "development").strip().lower() == "production":
        raise RuntimeError(
            "APP_ENV=production에서는 JWT_SECRET_KEY 환경 변수가 필수입니다. "
            "개발용 임시 키로는 운영 기동을 허용하지 않습니다."
        )
    SECRET_KEY = _DEV_DEFAULT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """발급된 JWT를 검증하고 payload를 반환한다.

    서명/만료 검증 실패 시 jwt.InvalidTokenError(만료 포함)를 그대로 전파한다.
    호출부(Depends 등)에서 401 응답으로 변환한다.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
