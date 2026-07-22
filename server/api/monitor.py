"""
모니터링 SSE(Server-Sent Events) API 라우터.
관제 프론트엔드가 실시간으로 MCP 메트릭 데이터를 수신해 갈 수 있는 스트리밍 엔드포인트를 제공합니다.
"""

import asyncio
import contextlib
import json
import logging
import os
import sys

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from server.api.dependencies import get_current_admin

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from server.mcp.gpu_monitor import GPUMonitorMCP
from server.mcp.manager import mcp_manager
from server.orchestration.llm_client_factory import LLMClientFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitor", tags=["Monitor"])


# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# 미션 2: 여기에 Depends(get_current_admin) 자물쇠를 걸어주세요!
# ==========================================
def _sse_frame(payload: dict) -> str:
    """SSE data 프레임 한 건을 직렬화한다."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.get("/stream")
async def monitor_stream(request: Request, admin_id: str = Depends(get_current_admin)):
    """
    FastAPI StreamingResponse를 사용하여 실시간 MCP 및 시스템 메트릭 데이터를
    SSE(Server-Sent Events) 프로토콜로 브로드캐스트합니다.
    """
    # 전용 리스너 큐 등록
    queue = mcp_manager.register_listener()

    async def event_generator():
        try:
            # 최초 연결 시 연결 수립 알림 전송
            yield _sse_frame({"event_type": "connection_established", "status": "ok"})

            # 연결 직후 1회 스냅샷: 다음 GPU 루프(최대 2초)까지 카드가 비지 않게 한다.
            # Docker Desktop 등 중간 프록시가 소량 청크를 버퍼링해도, 첫 실데이터 프레임을
            # 바로 밀어 브라우저 EventSource onmessage가 살아나게 한다.
            try:
                status = await GPUMonitorMCP().get_gpu_status()
                provider = LLMClientFactory._current_provider or os.getenv("LLM_PROVIDER", "gemini")
                yield _sse_frame(
                    {
                        "event_type": "system_metrics",
                        "payload": {
                            "gpu_usage_pct": status.get("gpu_usage_pct", 0.0),
                            "memory_used_mb": status.get("memory_used_mb", 0.0),
                            "current_provider": str(provider).upper(),
                            "network_rtt_ms": 12,
                            "queue_depth": 0,
                            "dropped_frames": 0,
                        },
                    }
                )
            except Exception as e:
                logger.warning(f"[MONITOR API] 최초 system_metrics 스냅샷 실패: {e!s}")

            while True:
                # 클라이언트가 연결을 끊었는지 체크 (방어적 코딩)
                if await request.is_disconnected():
                    logger.info("[MONITOR API] 클라이언트 연결 끊김 감지")
                    break

                try:
                    # 큐로부터 1초간 대기하며 메시지 획득
                    event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield _sse_frame(event_data)
                except TimeoutError:
                    # RTT 유지 및 연결 끊김 감지를 위한 Keep-Alive 하트비트 전송
                    # 주석 형태 SSE 라인을 섞어 프록시 버퍼를 더 잘 깨뜨린다.
                    yield ": keepalive\n\n"
                    yield _sse_frame({"event_type": "ping"})
                except Exception as e:
                    logger.error(f"[MONITOR API] 이벤트 생성기 루프 예외: {e!s}")
                    break
        finally:
            # 제네레이터 종료 시 리스너 등록 해제
            mcp_manager.unregister_listener(queue)

    # Cache-Control/X-Accel-Buffering: Docker·리버스 프록시가 SSE 청크를 모았다가
    # 한꺼번에 보내 콘솔 SystemMetrics 행이 비는 문제를 막는다.
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
