"""
하트비트 관리 모듈.
서버 -> 단말 5초 heartbeat 송신, 타임아웃 시 연결 종료.
API 명세서 v0.2.0 기준 heartbeat/heartbeat_ack 프로토콜 사용.
"""

import asyncio
import contextlib
import logging
import sys
import time

from fastapi import WebSocket

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """서버 -> 단말 하트비트 관리자.

    5초 간격으로 heartbeat 메시지를 송신하고,
    단말의 heartbeat_ack 응답을 감시하여 타임아웃 시 연결을 종료합니다.
    """

    def __init__(
        self,
        ws: WebSocket,
        device_id: str,
        interval: int = 5,
        timeout: int = 5,
    ) -> None:
        self.ws = ws
        self.device_id = device_id
        self.interval = interval
        self.timeout = timeout
        self.last_ack_time: float = time.time()
        self._running: bool = True

    async def start(self) -> None:
        """하트비트 루프 시작 (비동기 태스크로 실행)."""
        while self._running:
            await asyncio.sleep(self.interval)
            if not self._running:
                break

            elapsed = time.time() - self.last_ack_time
            if elapsed > (self.interval + self.timeout):
                logger.warning(
                    f"[Heartbeat] 타임아웃: device_id={self.device_id}, elapsed={elapsed:.1f}s"
                )
                with contextlib.suppress(Exception):
                    await self.ws.close(code=1001, reason="heartbeat timeout")
                break

            try:
                await self.ws.send_json(
                    {
                        "type": "heartbeat",
                        "ts": time.time() * 1000,
                    }
                )
            except Exception as e:
                logger.error(f"[Heartbeat] 송신 실패: {e}")
                break

    def record_ack(self) -> None:
        """heartbeat_ack 수신 시 호출."""
        self.last_ack_time = time.time()

    def stop(self) -> None:
        """하트비트 루프 중지."""
        self._running = False
