"""
WebSocket 메시지 Pydantic 스키마.
API 명세서 v0.2.0 기준 메시지 타입별 스키마를 정의합니다.
"""

import contextlib
import sys
from datetime import datetime
from typing import Any

from pydantic import BaseModel

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")


class WSMessage(BaseModel):
    """공통 WebSocket 메시지 래퍼."""

    type: str
    device_id: str | None = None
    token: str | None = None
    session_id: str | None = None
    server_time: str | None = None
    ts: float | None = None
    payload: dict[str, Any] | None = None


class WelcomeMessage(BaseModel):
    """서버 -> 단말 welcome 메시지 (핸드셰이크)."""

    type: str = "welcome"
    session_id: str
    server_time: str


class AuthOkMessage(BaseModel):
    """서버 -> 단말 인증 성공 메시지."""

    type: str = "auth_ok"
    device_id: str


class AckMessage(BaseModel):
    """서버 -> 단말 프레임 수신 ack (API 명세서 §3.2)."""

    type: str = "ack"
    event_id: str
    frame_id: int = 0
    decode_ms: float = 0.0


class ErrorMessage(BaseModel):
    """서버 -> 단말 에러 메시지 (API 명세서 §2.4)."""

    type: str = "error"
    event_id: str | None = None
    code: str = "internal"
    message: str = ""


class HeartbeatMessage(BaseModel):
    """서버 -> 단말 하트비트 (API 명세서 §2.3)."""

    type: str = "heartbeat"
    ts: float


class HeartbeatAckMessage(BaseModel):
    """단말 -> 서버 하트비트 응답 (API 명세서 §2.3)."""

    type: str = "heartbeat_ack"
    ts: float


def now_iso() -> str:
    """현재 시각을 ISO 8601 문자열로 반환."""
    return datetime.now().isoformat()


def now_ts() -> float:
    """현재 시각을 epoch ms로 반환."""
    return float(datetime.now().timestamp() * 1000)
