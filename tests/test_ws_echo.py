"""
1단계 WebSocket Gateway echo 검증 테스트.
연결 수립, hello/welcome, echo 왕복 RTT < 100ms, 하트비트, 재연결, 정리 검증.
"""

import asyncio
import json

import pytest
import websockets

SERVER_URL = "ws://localhost:8000/ws/detect"
DEVICE_ID = "dev-001"
TOKEN = "token-abc-001"  # noqa: S105 - MVP 테스트용 하드코딩 토큰
RTT_THRESHOLD_MS = 100


@pytest.fixture(scope="module")
def event_loop():
    """모듈 스코프 이벤트 루프."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_handshake_welcome_and_auth():
    """연결 수립 후 welcome 및 auth_ok 수신 검증."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
        welcome = json.loads(raw)
        assert welcome["type"] == "welcome"
        assert "session_id" in welcome
        assert "server_time" in welcome

        await ws.send(
            json.dumps(
                {
                    "type": "hello",
                    "device_id": DEVICE_ID,
                    "token": TOKEN,
                }
            )
        )

        raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
        auth_ok = json.loads(raw)
        assert auth_ok["type"] == "auth_ok"
        assert auth_ok["device_id"] == DEVICE_ID


@pytest.mark.asyncio
async def test_echo_rtt_under_100ms():
    """echo 왕복 RTT < 100ms 검증."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        await asyncio.wait_for(ws.recv(), timeout=3.0)

        await ws.send(
            json.dumps(
                {
                    "type": "hello",
                    "device_id": DEVICE_ID,
                    "token": TOKEN,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=3.0)

        test_msg = {"type": "heartbeat", "ts": 0}
        start = asyncio.get_event_loop().time()
        await ws.send(json.dumps(test_msg))
        raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
        elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

        response = json.loads(raw)
        assert response["type"] == "heartbeat_ack"
        assert elapsed_ms < RTT_THRESHOLD_MS, f"RTT {elapsed_ms:.1f}ms >= {RTT_THRESHOLD_MS}ms"


@pytest.mark.asyncio
async def test_heartbeat_response():
    """클라이언트 heartbeat에 대한 heartbeat_ack 응답 검증."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        await asyncio.wait_for(ws.recv(), timeout=3.0)
        await ws.send(
            json.dumps(
                {
                    "type": "hello",
                    "device_id": DEVICE_ID,
                    "token": TOKEN,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=3.0)

        await ws.send(json.dumps({"type": "heartbeat", "ts": 12345}))
        raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
        response = json.loads(raw)
        assert response["type"] == "heartbeat_ack"
        assert "ts" in response


@pytest.mark.asyncio
async def test_auth_failure():
    """잘못된 토큰 인증 실패 검증."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        await asyncio.wait_for(ws.recv(), timeout=3.0)

        await ws.send(
            json.dumps(
                {
                    "type": "hello",
                    "device_id": DEVICE_ID,
                    "token": "wrong-token",
                }
            )
        )

        raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
        error = json.loads(raw)
        assert error["type"] == "error"
        assert error["code"] == "auth_failed"


@pytest.mark.asyncio
async def test_detection_ack():
    """detection 메시지 ack 응답 검증 (빈 프레임 가드레일)."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        await asyncio.wait_for(ws.recv(), timeout=3.0)
        await ws.send(
            json.dumps(
                {
                    "type": "hello",
                    "device_id": DEVICE_ID,
                    "token": TOKEN,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=3.0)

        await ws.send(
            json.dumps(
                {
                    "type": "detection",
                    "payload": {
                        "event_id": "test-evt-001",
                        "device_id": DEVICE_ID,
                        "ts": 1719216000000,
                        "frame_id": 1,
                        "stream": "reflex",
                        "thumbnail_jpeg_b64": "",
                    },
                }
            )
        )

        raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
        ack = json.loads(raw)
        assert ack["type"] == "ack"
        assert ack["event_id"] == "test-evt-001"
        assert "decode_ms" in ack


@pytest.mark.asyncio
async def test_disconnect_cleanup():
    """연결 종료 후 세션 정리 검증."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        await asyncio.wait_for(ws.recv(), timeout=3.0)
        await ws.send(
            json.dumps(
                {
                    "type": "hello",
                    "device_id": DEVICE_ID,
                    "token": TOKEN,
                }
            )
        )
        await asyncio.wait_for(ws.recv(), timeout=3.0)

    await asyncio.sleep(0.5)
    from server.api.session_manager import manager

    assert not manager.is_connected(DEVICE_ID), "연결 종료 후 세션이 정리되지 않음"
