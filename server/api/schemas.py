"""
WebSocket 메시지 Pydantic 스키마.
API 명세서 v0.2.0 기준 메시지 타입별 스키마를 정의합니다.
"""

import contextlib
import sys
from datetime import UTC, datetime
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
    """현재 시각을 ISO 8601 문자열로 반환한다 (UTC, 타임존 오프셋 포함).

    2026-07-12 수정: 이전에는 datetime.now()(naive, 컨테이너 시스템 시각=UTC)를 그대로
    직렬화해 "+00:00"/"Z" 같은 타임존 표시가 없었다. JS의 `new Date(...)`는 오프셋이
    없는 ISO 문자열을 "브라우저 로컬 시각"으로 해석하므로, UTC 09:53을 KST 09:53으로
    잘못 표시하는 9시간 오차가 콘솔 전역(마지막 이벤트 시각, welcome server_time 등)에서
    발생했다. datetime.now(UTC)로 오프셋을 명시해 브라우저가 올바르게 KST로 변환하게 한다.
    """
    return datetime.now(UTC).isoformat()


def now_ts() -> float:
    """현재 시각을 epoch ms로 반환."""
    return float(datetime.now().timestamp() * 1000)
