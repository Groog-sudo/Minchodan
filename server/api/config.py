# -*- coding: utf-8 -*-
# server/api/config.py
import os
import sys
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# 환경 변수 로드 (가이드 3.3, 3.4 준수)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    WS_HOST: str = os.getenv("WS_HOST", "0.0.0.0")
    WS_PORT: int = int(os.getenv("WS_PORT", "8000"))
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "5"))      # 초 단위
    HEARTBEAT_TIMEOUT: int = int(os.getenv("HEARTBEAT_TIMEOUT", "5"))       # pong 응답 대기 시간
    MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "3"))  # 클라이언트 재접속 최대 횟수
    CORS_ORIGINS: list[str] = ["*"]  # 개발 시 전체 허용, 운영 시 제한

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
