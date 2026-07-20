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
    # ngrok 등 공인망 릴레이 경유 시 왕복 지연이 커질 수 있어, 기존 5초(총 유예 10초)는
    # 무선 환경에서 정상 연결도 오탐 종료시켰다(2026-07-10 실기기 LTE/ngrok 테스트로 확인).
    HEARTBEAT_TIMEOUT: int = int(os.getenv("HEARTBEAT_TIMEOUT", "15"))
    MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "3"))
    WS_AUTH_TIMEOUT_SECONDS: int = int(os.getenv("WS_AUTH_TIMEOUT_SECONDS", "10"))
    # 운영자 콘솔(React) 개발 서버 기본 출처만 허용. 프로덕션 배포 시 .env의
    # CORS_ORIGINS(JSON 배열 문자열, 예: ["https://console.example.com"])로 반드시 override.
    CORS_ORIGINS: list[str] = []

    def __init__(self, **values):
        super().__init__(**values)
        import json

        raw_cors = os.getenv("CORS_ORIGINS")
        if raw_cors:
            try:
                parsed = json.loads(raw_cors)
                if isinstance(parsed, list):
                    self.CORS_ORIGINS = parsed
                else:
                    self.CORS_ORIGINS = [str(parsed)]
            except Exception:
                # 쉼표 구분자 형태 폴백
                self.CORS_ORIGINS = [x.strip() for x in raw_cors.split(",") if x.strip()]
        else:
            self.CORS_ORIGINS = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:5174",
            ]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
