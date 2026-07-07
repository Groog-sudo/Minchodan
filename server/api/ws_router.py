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
from server.capture.frame_decoder import decode_frame, decode_frame_binary
from server.capture.stream_splitter import get_default_splitter

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)
router = APIRouter()


async def _finish_detection(
    ws: WebSocket,
    splitter,
    processed,
    event_id: str,
    frame_id: int,
    decode_ms: float,
    b64_len_for_log: int = 0,
) -> None:
    """디코딩 결과를 스트림 스플리터로 라우팅하고 ack를 응답한다.

    base64 경로(단일 JSON 메시지)와 바이너리 경로(메타 + 바이너리 프레임) 양쪽이
    공유하는 후처리 로직 - route_frame + ack 응답 (guide 17.1 계층 분리 준수).
    """
    logger.info(
        f"[WS] detection 수신 - event_id: {event_id}, frame_id: {frame_id}, decode_ms: {decode_ms:.2f}ms"
    )
    print(
        f"[DEBUG_WS] detection 수신 - event_id: {event_id}, frame_id: {frame_id}, decode_ms: {decode_ms:.2f}ms",
        flush=True,
    )

    if processed is not None:
        with contextlib.suppress(Exception):
            await splitter.route_frame(processed)
    else:
        print(
            f"[DEBUG_WS] 디코딩 실패! event_id={event_id}, base64길이={b64_len_for_log}",
            flush=True,
        )

    await ws.send_json(
        {
            "type": "ack",
            "event_id": event_id,
            "frame_id": frame_id,
            "decode_ms": round(decode_ms, 2),
        }
    )


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
        logger.info(f"[WS] welcome 송신 완료 - device_id: {device_id}")
        print(f"[DEBUG_WS] welcome 송신 완료 - device_id: {device_id}", flush=True)

        raw_hello = await ws.receive_text()
        logger.info(f"[WS] hello 수신 - raw: {raw_hello}")
        print(f"[DEBUG_WS] hello 수신 - raw: {raw_hello}", flush=True)
        hello_data = json.loads(raw_hello)

        if hello_data.get("type") != "hello":
            logger.warning(f"[WS] expected hello, but got: {hello_data.get('type')}")
            print(f"[DEBUG_WS] expected hello, but got: {hello_data.get('type')}", flush=True)
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
            logger.warning(f"[WS] 디바이스 토큰 검증 실패 - device_id: {device_id}, token: {token}")
            print(
                f"[DEBUG_WS] 디바이스 토큰 검증 실패 - device_id: {device_id}, token: {token}",
                flush=True,
            )
            await ws.send_json(
                {
                    "type": "error",
                    "code": "auth_failed",
                    "message": "디바이스 토큰 검증 실패",
                }
            )
            await ws.close(code=1008, reason="authentication failed")
            return

        logger.info(f"[WS] 토큰 검증 성공 - auth_ok 송신 - device_id: {device_id}")
        print(f"[DEBUG_WS] 토큰 검증 성공 - auth_ok 송신 - device_id: {device_id}", flush=True)
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

        # 바이너리 전송 프로토콜: 클라이언트가 detection 메타(JSON, transport="binary")를
        # 먼저 보내고 곧바로 raw JPEG 바이트를 바이너리 WS 프레임으로 전송한다. 단일 WS
        # 연결에서는 프레임 전송 순서가 보장되므로, 직전에 받은 메타를 여기에 잠시 보관해뒀다가
        # 바로 뒤이어 오는 바이너리 프레임과 짝지어 처리한다.
        pending_binary_meta: dict | None = None

        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000), message.get("reason"))

            raw_bytes = message.get("bytes")
            if raw_bytes is not None:
                if pending_binary_meta is None:
                    logger.warning("[WS] 대기 중인 메타데이터 없이 바이너리 프레임 수신 - 무시")
                    continue

                meta = pending_binary_meta
                pending_binary_meta = None
                event_id = meta.get("event_id", "unknown")
                frame_id = meta.get("frame_id", 0)

                decode_start = time.perf_counter()
                processed = await decode_frame_binary(raw_bytes, meta)
                decode_ms = (time.perf_counter() - decode_start) * 1000

                await _finish_detection(
                    ws, splitter, processed, event_id, frame_id, decode_ms, len(raw_bytes)
                )
                continue

            raw = message.get("text")
            if raw is None:
                continue
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type in ("heartbeat_ack", "pong"):
                if heartbeat:
                    heartbeat.record_ack()

            elif msg_type == "ping":
                await ws.send_json(
                    {
                        "type": "pong",
                        "ts": now_ts(),
                    }
                )

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

                if payload.get("transport") == "binary":
                    # 뒤이어 도착할 바이너리 프레임을 대기 (ack는 그때 응답)
                    pending_binary_meta = payload
                    continue

                # 구버전 호환 경로: base64 JPEG가 payload에 직접 포함된 단일 메시지
                decode_start = time.perf_counter()
                processed = await decode_frame(payload)
                decode_ms = (time.perf_counter() - decode_start) * 1000

                b64_val = payload.get("thumbnail_jpeg_b64")
                b64_len = len(b64_val) if b64_val else 0
                await _finish_detection(
                    ws, splitter, processed, event_id, frame_id, decode_ms, b64_len
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
