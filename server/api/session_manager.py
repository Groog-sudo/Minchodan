"""
WebSocket 세션 관리자.
활성 WebSocket 연결을 추적하고 관리하는 싱글턴 클래스.
"""

import contextlib
import logging
import sys

from fastapi import WebSocket

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class SessionManager:
    """활성 WebSocket 연결을 추적하고 관리하는 싱글턴 클래스."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        """새 연결 수락 및 등록."""
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(
            f"[Session] 연결: device_id={device_id}, 현재 접속: {len(self.active_connections)}명"
        )

    def disconnect(self, device_id: str) -> None:
        """연결 해제 및 등록 삭제."""
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(
                f"[Session] 해제: device_id={device_id}, "
                f"현재 접속: {len(self.active_connections)}명"
            )

    async def send_json(self, device_id: str, data: dict) -> None:
        """특정 디바이스에 JSON 메시지 송신."""
        ws = self.active_connections.get(device_id)
        if ws:
            await ws.send_json(data)

    def is_connected(self, device_id: str) -> bool:
        """디바이스 연결 여부 확인."""
        return device_id in self.active_connections


manager = SessionManager()
