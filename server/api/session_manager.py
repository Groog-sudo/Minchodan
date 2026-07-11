"""
WebSocket 세션 관리자.
활성 WebSocket 연결을 추적하고 관리하는 싱글턴 클래스.
"""

import contextlib
import logging
import sys

from fastapi import WebSocket
from starlette.websockets import WebSocketState

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

    async def send_json(self, device_id: str, data: dict) -> bool:
        """특정 디바이스에 JSON 메시지 송신.

        2026-07-11: WebSocket application_state가 CONNECTED인 경우에만 송신한다.
        WS 연결이 끊어진 뒤에도 active_connections에서 즉시 제거되지 않는 경쟁
        창(consumer 태스크가 독립적으로 실행 중)에서 send를 시도하면
        "Cannot call send once a close message has been sent" 에러가 스팸으로
        발생했던 문제(13:26:47~52 로그, 17회 반복)를 방지한다.
        """
        ws = self.active_connections.get(device_id)
        if not ws or ws.application_state != WebSocketState.CONNECTED:
            return False
        await ws.send_json(data)
        return True

    async def send_bytes(self, device_id: str, data: bytes) -> bool:
        """특정 디바이스에 바이너리(raw bytes) 프레임 송신.

        인지 경로 guide 오디오(WAV)를 base64 문자열로 JSON에 실어 보내는 대신
        원본 바이트를 그대로 전송한다(2026-07-09 도입). base64는 페이로드를
        33% 부풀리고, RN 구 브릿지에서 대용량 문자열을 다루는 경로를 추가로
        거치게 한다 - 실기기에서 문장 중간 음절이 산발적으로 사라지는 현상의
        원인 후보를 좁히기 위해, 카메라 프레임 전송(client->server)에 이미
        적용된 바이너리 프레임 패턴을 반대 방향(server->client)에도 적용한다.
        """
        ws = self.active_connections.get(device_id)
        if not ws or ws.application_state != WebSocketState.CONNECTED:
            return False
        await ws.send_bytes(data)
        return True

    def is_connected(self, device_id: str) -> bool:
        """디바이스 연결 여부 확인. application_state도 함께 검증한다."""
        ws = self.active_connections.get(device_id)
        return ws is not None and ws.application_state == WebSocketState.CONNECTED


manager = SessionManager()
