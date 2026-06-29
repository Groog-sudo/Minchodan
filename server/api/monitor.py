"""
모니터링 SSE(Server-Sent Events) API 라우터.
관제 프론트엔드가 실시간으로 MCP 메트릭 데이터를 수신해 갈 수 있는 스트리밍 엔드포인트를 제공합니다.
"""

import asyncio
import contextlib
import json
import logging
import sys

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from server.mcp.manager import mcp_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitor", tags=["Monitor"])


@router.get("/stream")
async def monitor_stream(request: Request):
    """
    FastAPI StreamingResponse를 사용하여 실시간 MCP 및 시스템 메트릭 데이터를
    SSE(Server-Sent Events) 프로토콜로 브로드캐스트합니다.
    """
    # 전용 리스너 큐 등록
    queue = mcp_manager.register_listener()

    async def event_generator():
        try:
            # 최초 연결 시 연결 수립 알림 전송
            yield (
                "data: "
                + json.dumps({"event_type": "connection_established", "status": "ok"})
                + "\n\n"
            )

            while True:
                # 클라이언트가 연결을 끊었는지 체크 (방어적 코딩)
                if await request.is_disconnected():
                    logger.info("[MONITOR API] 클라이언트 연결 끊김 감지")
                    break

                try:
                    # 큐로부터 1초간 대기하며 메시지 획득
                    event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                except TimeoutError:
                    # RTT 유지 및 연결 끊김 감지를 위한 Keep-Alive 하트비트 전송
                    yield 'data: {"event_type": "ping"}\n\n'
                except Exception as e:
                    logger.error(f"[MONITOR API] 이벤트 생성기 루프 예외: {e!s}")
                    break
        finally:
            # 제네레이터 종료 시 리스너 등록 해제
            mcp_manager.unregister_listener(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
