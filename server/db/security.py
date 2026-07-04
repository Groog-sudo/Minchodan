# -*- coding: utf-8 -*-
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt

# ==========================================
# 🤖 VIBE AREA (AI 위임 영역)
# JWT 토큰 발급 및 Bcrypt 암호화 로직은 규격화된 보일러플레이트입니다.
# 라이브러리 사용법에 불과하므로 면접 비중이 낮습니다. AI 코드 복붙 권장.
# ==========================================

# 환경 변수에서 가져오되 없으면 임시 키 사용
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "minchodan_secret_key_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
