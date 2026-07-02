"""
WebSocket /ws/detect 엔드포인트 라우터.
단말(React Native)과 GPU 서버 간 실시간 양방향 통신 채널을 제공합니다.

핸드셰이크: accept -> welcome -> hello -> auth_ok -> heartbeat 루프
detection: decode_frame -> stream_splitter -> ack
"""

import asyncio
import contextlib
import json
import logging
import sys
import time

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from server.api.auth import verify_device
from server.api.config import settings
from server.api.heartbeat import HeartbeatManager
from server.api.schemas import now_iso, now_ts
from server.api.session_manager import manager
from server.bus.redis_client import redis_bus
from server.capture.frame_decoder import decode_frame
from server.capture.stream_splitter import get_default_splitter

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/detect")
async def ws_detect(
    ws: WebSocket,
    device_id: str = Query(..., description="단말 식별자"),
) -> None:
    """WebSocket /ws/detect 엔드포인트.

    핸드셰이크 절차:
        1. accept -> welcome 송신
        2. hello 수신 -> 디바이스 토큰 검증 -> auth_ok 송신
        3. heartbeat 루프 시작
        4. detection 메시지 수신 시 프레임 디코딩 -> 스트림 분기 -> ack 응답

    가드레일:
        - WebSocketDisconnect: 소켓 close + 리소스 해제
        - JSONDecodeError: 1003 종료
        - decode_frame None 반환: ack 정상 응답 (파이프라인 영속성)
    """
    await manager.connect(device_id, ws)

    heartbeat: HeartbeatManager | None = None
    heartbeat_task: asyncio.Task[None] | None = None

    try:
        await ws.send_json(
            {
                "type": "welcome",
                "session_id": device_id,
                "server_time": now_iso(),
            }
        )

        raw_hello = await ws.receive_text()
        hello_data = json.loads(raw_hello)

        if hello_data.get("type") != "hello":
            await ws.send_json(
                {
                    "type": "error",
                    "code": "bad_request",
                    "message": "expected hello message",
                }
            )
            await ws.close(code=1008, reason="expected hello message")
            return

        token = hello_data.get("token", "")
        is_valid = await verify_device(device_id, token)
        if not is_valid:
            await ws.send_json(
                {
                    "type": "error",
                    "code": "auth_failed",
                    "message": "디바이스 토큰 검증 실패",
                }
            )
            await ws.close(code=1008, reason="authentication failed")
            return

        await ws.send_json({"type": "auth_ok", "device_id": device_id})
        await redis_bus.connect()

        heartbeat = HeartbeatManager(
            ws,
            device_id,
            settings.HEARTBEAT_INTERVAL,
            settings.HEARTBEAT_TIMEOUT,
        )
        heartbeat_task = asyncio.create_task(heartbeat.start())

        splitter = get_default_splitter()

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "heartbeat_ack":
                if heartbeat:
                    heartbeat.record_ack()

            elif msg_type == "heartbeat":
                await ws.send_json(
                    {
                        "type": "heartbeat_ack",
                        "ts": now_ts(),
                    }
                )

            elif msg_type == "detection":
                payload = data.get("payload", {})
                event_id = payload.get("event_id", "unknown")
                frame_id = payload.get("frame_id", 0)

                decode_start = time.perf_counter()
                processed = await decode_frame(payload)
                decode_ms = (time.perf_counter() - decode_start) * 1000

                if processed is not None:
                    with contextlib.suppress(Exception):
                        await splitter.route_frame(processed)

                await ws.send_json(
                    {
                        "type": "ack",
                        "event_id": event_id,
                        "frame_id": frame_id,
                        "decode_ms": round(decode_ms, 2),
                    }
                )

            else:
                logger.warning(f"[WS] 알 수 없는 메시지 타입: {msg_type}")

    except WebSocketDisconnect as e:
        logger.info(f"[WS] 연결 끊김: device_id={device_id}, code={e.code}")
    except json.JSONDecodeError as e:
        logger.error(f"[WS] JSON 파싱 오류: {e}")
        with contextlib.suppress(Exception):
            await ws.close(code=1003, reason="invalid JSON")
    except Exception as e:
        logger.error(f"[WS] 예기치 않은 오류: device_id={device_id}, error={e}")
    finally:
        manager.disconnect(device_id)
        if heartbeat:
            heartbeat.stop()
        if heartbeat_task:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
        logger.info(f"[WS] 세션 종료: device_id={device_id}")
