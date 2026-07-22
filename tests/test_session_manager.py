import sys
from typing import cast

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pytest
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from server.api.session_manager import SessionManager


class _FakeWebSocket:
    def __init__(self, state: WebSocketState) -> None:
        self.application_state = state
        self.json_payloads: list[dict] = []
        self.binary_payloads: list[bytes] = []

    async def send_json(self, payload: dict) -> None:
        self.json_payloads.append(payload)

    async def send_bytes(self, payload: bytes) -> None:
        self.binary_payloads.append(payload)


@pytest.mark.asyncio
async def test_send_returns_false_for_disconnected_socket() -> None:
    manager = SessionManager()
    ws = _FakeWebSocket(WebSocketState.DISCONNECTED)
    manager.active_connections["device-1"] = cast(WebSocket, ws)

    assert await manager.send_json("device-1", {"type": "reflex_alert"}) is False
    assert await manager.send_bytes("device-1", b"audio") is False
    assert ws.json_payloads == []
    assert ws.binary_payloads == []


@pytest.mark.asyncio
async def test_send_returns_true_after_delivery() -> None:
    manager = SessionManager()
    ws = _FakeWebSocket(WebSocketState.CONNECTED)
    manager.active_connections["device-1"] = cast(WebSocket, ws)

    assert await manager.send_json("device-1", {"type": "reflex_alert"}) is True
    assert await manager.send_bytes("device-1", b"audio") is True
    assert ws.json_payloads == [{"type": "reflex_alert"}]
    assert ws.binary_payloads == [b"audio"]
