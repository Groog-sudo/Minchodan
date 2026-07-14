"""
Redis Cache Monitor MCP 모듈.
중복 경보 억제 캐시 키(`suppress:*`)의 정밀 상태 및 남은 TTL을 실시간 모니터링하고
관제 프론트엔드로 브로드캐스트합니다.
"""

import asyncio
import contextlib
import logging
import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class RedisCacheMonitorMCP:
    """
    Redis 억제 캐시 키들의 정밀 상태(남은 TTL 등)를 모니터링하는 MCP 모듈.
    """

    def __init__(self, stream_interval_seconds: float = 5.0):
        self.stream_interval_seconds = stream_interval_seconds
        self._monitor_task: asyncio.Task = None

    async def get_suppressed_keys_status(self) -> dict:
        """
        현재 Redis에 등록되어 억제 중인 경보 키 목록과 각각의 남은 TTL을 조회합니다.
        """
        from server.bus.redis_client import redis_bus

        suppressed_keys = []
        try:
            if redis_bus._redis is None:
                await redis_bus.connect()

            if redis_bus._redis is not None:
                # suppress:* 패턴의 모든 키 검색 (프로덕션 환경 등에서 scan 활용 권장되나 로컬/데모 환경이므로 keys 사용)
                keys = await redis_bus._redis.keys("suppress:*")
                for key in keys:
                    ttl = await redis_bus._redis.ttl(key)
                    # key 형식: suppress:device_id:alert_id
                    parts = key.split(":")
                    device_id = parts[1] if len(parts) > 1 else "unknown"
                    alert_id = parts[2] if len(parts) > 2 else parts[-1]

                    suppressed_keys.append(
                        {
                            "key": key,
                            "device_id": device_id,
                            "alert_id": alert_id,
                            "ttl_seconds": ttl,
                        }
                    )
        except Exception as e:
            logger.error(f"[CACHE MONITOR] Redis 캐시 키 조회 중 예외 발생: {e!s}")

        return {"suppressed_keys": suppressed_keys, "total_count": len(suppressed_keys)}

    async def check_and_broadcast(self):
        """
        캐시 상태를 진단하여 관제 콘솔에 브로드캐스트합니다.
        """
        status = await self.get_suppressed_keys_status()

        # 관제 모니터링 SSE 채널로 전송 (Redis Streams 발행)
        payload = {
            "suppressed_keys": [item["key"] for item in status["suppressed_keys"]],
            "ttl_seconds": max([item["ttl_seconds"] for item in status["suppressed_keys"]])
            if status["suppressed_keys"]
            else 0,
            "details": status["suppressed_keys"],
        }
        from server.mcp.manager import mcp_manager

        await mcp_manager.publish_metric("cache_suppression", payload)

    def start_monitoring(self):
        """
        백그라운드에서 캐시 상태를 상시 감시하는 비동기 루프를 기동합니다.
        """

        async def _loop():
            # 의도적인 쿨다운을 가진 상시 모니터링 루프
            while True:
                try:
                    await self.check_and_broadcast()
                except Exception as e:
                    logger.error(f"[CACHE MONITOR] 감시 루프 내 예외: {e!s}")
                await asyncio.sleep(self.stream_interval_seconds)

        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(_loop())
            logger.info("Redis Cache Monitor MCP 백그라운드 태스크가 활성화되었습니다.")

    def stop_monitoring(self):
        """
        백그라운드 감시 루프를 정지합니다.
        """
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            logger.info("Redis Cache Monitor MCP 백그라운드 태스크가 중지되었습니다.")


# 싱글톤 인스턴스 제공
cache_monitor = RedisCacheMonitorMCP()
