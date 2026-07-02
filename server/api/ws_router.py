<<<<<<< HEAD
# -*- coding: utf-8 -*-
# server/api/ws_router.py
import asyncio
from datetime import datetime
=======
"""
WebSocket /ws/detect 엔드포인트 라우터.
단말(React Native)과 GPU 서버 간 실시간 양방향 통신 채널을 제공합니다.

핸드셰이크: accept -> welcome -> hello -> auth_ok -> heartbeat 루프
detection: decode_frame -> stream_splitter -> ack
"""

import asyncio
import contextlib
>>>>>>> dev
import json
import logging
import sys
import time
<<<<<<< HEAD
=======

>>>>>>> dev
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from server.api.auth import verify_device
from server.api.config import settings
from server.api.heartbeat import HeartbeatManager
<<<<<<< HEAD
from server.api.session_manager import manager
from server.bus.redis_client import redis_bus

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")
=======
from server.api.schemas import now_iso, now_ts
from server.api.session_manager import manager
from server.bus.redis_client import redis_bus
from server.capture.frame_decoder import decode_frame
from server.capture.stream_splitter import get_default_splitter

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")
>>>>>>> dev

logger = logging.getLogger(__name__)
router = APIRouter()

<<<<<<< HEAD
@router.websocket("/ws/detect")
async def ws_detect(ws: WebSocket, device_id: str = Query(...)):
    await manager.connect(device_id, ws)

    try:
        welcome = {
            "type": "welcome",
            "session_id": device_id,
            "server_time": datetime.now().isoformat()
        }
        await ws.send_json(welcome)
=======

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
>>>>>>> dev

        raw_hello = await ws.receive_text()
        hello_data = json.loads(raw_hello)

        if hello_data.get("type") != "hello":
<<<<<<< HEAD
=======
            await ws.send_json(
                {
                    "type": "error",
                    "code": "bad_request",
                    "message": "expected hello message",
                }
            )
>>>>>>> dev
            await ws.close(code=1008, reason="expected hello message")
            return

        token = hello_data.get("token", "")
        is_valid = await verify_device(device_id, token)
        if not is_valid:
<<<<<<< HEAD
            await ws.send_json({"type": "error", "message": "인증 실패"})
=======
            await ws.send_json(
                {
                    "type": "error",
                    "code": "auth_failed",
                    "message": "디바이스 토큰 검증 실패",
                }
            )
>>>>>>> dev
            await ws.close(code=1008, reason="authentication failed")
            return

        await ws.send_json({"type": "auth_ok", "device_id": device_id})
<<<<<<< HEAD
        
        # Redis Bus 연결
        # await redis_bus.connect() 
        # (주의: redis_bus.connect()는 lifespan에서 관리될 수 있으므로 환경에 따라 다름)

        hb = HeartbeatManager(ws, device_id, settings.HEARTBEAT_INTERVAL, settings.HEARTBEAT_TIMEOUT)
        heartbeat_task = asyncio.create_task(hb.start())

        # =========================================================================
        # 👨‍💻 담당자 직접 코딩 영역 시작 👨‍💻
        # 클라이언트 메시지 루프를 돌면서 "detection" 타입 메시지를 받아 
        # redis_bus.publish_event() 로 발행하고, "ack"를 반환하는 로직을 작성해 주세요.
        # =========================================================================
        
        # while True:
        #     # 1. ws.receive_text() 로 메시지 수신 후 json.loads()
        #     # 2. 메시지 타입(msg_type) 분류 ("pong", "ping", "detection")
        #     # 3. "detection" 인 경우 payload 추출 후 redis_bus.publish_event("risk.events", {...})
        #     # 4. ws.send_json() 으로 ack 응답 전송
        while True:
                # 1. 메시지 수신 및 파싱
                raw = await ws.receive_text()
                data = json.loads(raw)
                msg_type = data.get("type")
                
                # 2. 메시지 타입별 처리
                if msg_type == "pong":
                    hb.record_pong()
                
                elif msg_type == "ping":
                    await ws.send_json({"type": "pong", "ts" : time.time() })
                
                elif msg_type == "detection":
                    
                    # 3. 탐지 이벤트인 경우 Redis Bus에 발행
                    payload = data.get("payload", {})
                    event_id = payload.get("event_id", "unknown")

                    await redis_bus.publish_event("risk.events",
                    {
                        "event_id": event_id,
                        "device_id": device_id,
                        "timestamp": payload.get("timestamp", datetime.now().isoformat()),
                        "stream": payload.get("stream", "cognitive"),
                        "frame_data": payload.get("thumbnail_jpeg_b64", "")
                    })
                
                    # 4. 앱에 수신 확인 (ACK) 응답
                    await ws.send_json({
                        "type" : "ack",
                        "event_id": event_id,
                        "received_at": datetime.now().isoformat()
                    })
                else:
                    logger.warning(f"[WS] 알 수 없는 메시지 타입: {msg_type}")


        # =========================================================================
        # 👨‍💻 담당자 직접 코딩 영역 끝 👨‍💻
        # =========================================================================
=======
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
>>>>>>> dev

    except WebSocketDisconnect as e:
        logger.info(f"[WS] 연결 끊김: device_id={device_id}, code={e.code}")
    except json.JSONDecodeError as e:
        logger.error(f"[WS] JSON 파싱 오류: {e}")
<<<<<<< HEAD
        await ws.close(code=1003, reason="invalid JSON")
=======
        with contextlib.suppress(Exception):
            await ws.close(code=1003, reason="invalid JSON")
>>>>>>> dev
    except Exception as e:
        logger.error(f"[WS] 예기치 않은 오류: device_id={device_id}, error={e}")
    finally:
        manager.disconnect(device_id)
<<<<<<< HEAD
        if 'hb' in locals():
            hb.stop()
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
=======
        if heartbeat:
            heartbeat.stop()
        if heartbeat_task:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
>>>>>>> dev
        logger.info(f"[WS] 세션 종료: device_id={device_id}")
