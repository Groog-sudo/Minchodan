"""
통합 MCP 매니저 모듈.
Redis Streams(mcp:metrics)로부터 모니터링 메트릭을 비동기로 수집하고,
FastAPI SSE 채널 및 관제 프론트엔드로 브로드캐스트할 이벤트를 큐잉 관리합니다.
"""

import asyncio
import contextlib
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Redis Streams 기반 아웃오브밴드 메트릭 수집 및 브로드캐스트 관리 클래스.
    """

    def __init__(self, stream_key: str = "mcp:metrics"):
        self.stream_key = stream_key
        self.listeners: set[asyncio.Queue] = set()
        self._consume_task: asyncio.Task = None
        self._redis_client = None

    def register_listener(self) -> asyncio.Queue:
        """
        SSE 클라이언트 등 실시간 스트림 이벤트를 받고자 하는 리스너 큐를 등록합니다.
        """
        queue = asyncio.Queue(maxsize=100)
        self.listeners.add(queue)
        logger.info(
            f"[MCP MANAGER] 새로운 모니터링 리스너 등록됨. 총 리스너: {len(self.listeners)}"
        )
        return queue

    def unregister_listener(self, queue: asyncio.Queue):
        """
        리스너 큐 해제.
        """
        if queue in self.listeners:
            self.listeners.remove(queue)
            logger.info(f"[MCP MANAGER] 모니터링 리스너 해제됨. 남은 리스너: {len(self.listeners)}")

    async def broadcast_event(self, event_type: str, payload: dict[str, Any]):
        """
        등록된 모든 리스너 큐로 실시간 이벤트를 브로드캐스트합니다. (방어적 큐 삽입 적용)
        """
        event_data = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "payload": payload,
        }

        # 비활성화된 리스너 자동 정리를 위한 리스트
        stale_queues = []
        for queue in self.listeners:
            try:
                if queue.full():
                    # 큐가 꽉 차있다면 가장 오래된 메시지를 버리고 삽입
                    queue.get_nowait()
                queue.put_nowait(event_data)
            except asyncio.QueueFull:
                pass
            except Exception as e:
                logger.error(f"[MCP MANAGER] 리스너 브로드캐스트 중 예외: {e!s}")
                stale_queues.append(queue)

        for sq in stale_queues:
            self.unregister_listener(sq)

    async def start_consumer(self, redis_url: str | None = None):
        """
        Redis Streams(mcp:metrics)를 백그라운드에서 상시 모니터링하는 태스크를 시작합니다.
        """
        import redis.asyncio as aioredis

        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self._redis_client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
            logger.info(f"[MCP MANAGER] Redis Connection Successful: {url}")
        except Exception as e:
            logger.error(f"[MCP MANAGER] Redis Connection Failed: {e!s}")
            return

        async def _consume_loop():
            # 스트림이 존재하지 않는 경우 대비해 초기 생성 체크
            with contextlib.suppress(Exception):
                # XADD dummy to create stream if not exists
                await self._redis_client.xadd(self.stream_key, {"init": "true"}, id="0-1")

            last_id = "$"  # 최초 기동 시점 이후의 메시지만 읽기
            logger.info(f"[MCP MANAGER] Redis Stream '{self.stream_key}' 모니터링 루프 시작")

            while True:
                try:
                    # xread 블로킹 1초
                    streams = await self._redis_client.xread(
                        {self.stream_key: last_id}, count=10, block=1000
                    )
                    if streams:
                        for _, messages in streams:
                            for msg_id, data in messages:
                                last_id = msg_id
                                # 수집된 로우 데이터 파싱 및 정규화
                                event_type = data.get("event_type", "system_status")
                                try:
                                    payload = json.loads(data.get("payload", "{}"))
                                except json.JSONDecodeError:
                                    payload = {"raw_data": data}

                                await self.broadcast_event(event_type, payload)
                except Exception as e:
                    logger.error(f"[MCP MANAGER] Stream 읽기 예외: {e!s}")
                    await asyncio.sleep(2.0)

        if self._consume_task is None or self._consume_task.done():
            self._consume_task = asyncio.create_task(_consume_loop())

    async def stop_consumer(self):
        """
        소비 태스크를 취소하고 리소스를 해제합니다.
        """
        if self._consume_task and not self._consume_task.done():
            self._consume_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consume_task
        if self._redis_client:
            await self._redis_client.close()
            logger.info("[MCP MANAGER] Redis connection closed.")


# 싱글톤 인스턴스
mcp_manager = MCPManager()
