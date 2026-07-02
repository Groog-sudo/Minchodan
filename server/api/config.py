"""
WebSocket Gateway 환경 설정 모듈.
WS/Redis/Heartbeat 설정값을 중앙화하여 관리합니다.
"""

import contextlib
import os
import sys

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """WebSocket Gateway 설정 (환경 변수 기반)."""

    WS_HOST: str = os.getenv("WS_HOST", "0.0.0.0")  # nosec B104
    WS_PORT: int = int(os.getenv("WS_PORT", "8000"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    HEARTBEAT_INTERVAL: int = int(os.getenv("HEARTBEAT_INTERVAL", "5"))
    HEARTBEAT_TIMEOUT: int = int(os.getenv("HEARTBEAT_TIMEOUT", "5"))
    MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "3"))
    CORS_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
