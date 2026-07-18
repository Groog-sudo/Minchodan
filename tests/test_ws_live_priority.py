"""실행 중 FastAPI(uvicorn)에 대한 WS 라이브 통합 검증.

Docker 컨테이너 내부에서 `localhost:8000`으로 접속한다.
"""

import asyncio
import json
import sys
import time

import cv2
import numpy as np
import pytest
import websockets

from server.api.auth import issue_device_token

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SERVER_URL = "ws://127.0.0.1:8000/ws/detect"
DEVICE_ID = "dev-live-priority-test"
TOKEN = issue_device_token(DEVICE_ID)


def _make_jpeg_bytes(width: int = 640, height: int = 480) -> bytes:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[150:400, 180:460] = 255
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    assert ok
    return buf.tobytes()


async def _auth(ws) -> None:
    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
    welcome = json.loads(raw)
    assert welcome["type"] == "welcome"
    await ws.send(json.dumps({"type": "hello", "device_id": DEVICE_ID, "token": TOKEN}))
    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
    auth_ok = json.loads(raw)
    assert auth_ok["type"] == "auth_ok"


async def _collect_messages(ws, timeout_s: float = 12.0) -> list[dict]:
    deadline = time.monotonic() + timeout_s
    received: list[dict] = []
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=min(1.0, remaining))
        except TimeoutError:
            continue
        except websockets.exceptions.ConnectionClosed:
            break
        if isinstance(raw, bytes):
            continue
        received.append(json.loads(raw))
    return received


@pytest.mark.asyncio
async def test_live_ws_detection_control_and_server_detection():
    """탐지 ON + cognitive 프레임 전송 시 ack 및 server_detection 수신."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        await _auth(ws)

        await ws.send(json.dumps({"type": "detection_control", "enabled": True, "ts": time.time()}))

        event_id = f"live-priority-{int(time.time())}"
        await ws.send(
            json.dumps(
                {
                    "type": "detection",
                    "payload": {
                        "event_id": event_id,
                        "device_id": DEVICE_ID,
                        "frame_id": 1,
                        "stream": "cognitive",
                        "transport": "binary",
                        "ts": int(time.time() * 1000),
                    },
                }
            )
        )
        await ws.send(_make_jpeg_bytes())

        messages = await _collect_messages(ws, timeout_s=15.0)
        types = {m.get("type") for m in messages}
        assert "ack" in types, f"ack missing, got={types}"
        ack = next(m for m in messages if m.get("type") == "ack")
        assert ack.get("event_id") == event_id
        assert ack.get("decode_ms", 0) > 0

        assert "server_detection" in types, f"server_detection missing, got={types}"
        det_msg = next(m for m in messages if m.get("type") == "server_detection")
        assert det_msg.get("event_id") == event_id
        assert isinstance(det_msg.get("detections"), list)


@pytest.mark.asyncio
async def test_live_ws_reflex_stream_ack():
    """reflex 스트림 바이너리 프레임이 파이프라인까지 수용되는지 확인."""
    async with websockets.connect(f"{SERVER_URL}?device_id={DEVICE_ID}") as ws:
        await _auth(ws)
        await ws.send(json.dumps({"type": "detection_control", "enabled": True, "ts": time.time()}))

        event_id = f"live-reflex-{int(time.time())}"
        await ws.send(
            json.dumps(
                {
                    "type": "detection",
                    "payload": {
                        "event_id": event_id,
                        "device_id": DEVICE_ID,
                        "frame_id": 2,
                        "stream": "reflex",
                        "transport": "binary",
                        "ts": int(time.time() * 1000),
                    },
                }
            )
        )
        await ws.send(_make_jpeg_bytes())

        messages = await _collect_messages(ws, timeout_s=10.0)
        assert any(m.get("type") == "ack" and m.get("event_id") == event_id for m in messages)
