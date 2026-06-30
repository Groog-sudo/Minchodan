# -*- coding: utf-8 -*-
# server/api/heartbeat.py
import asyncio
import logging
import sys
import time
from fastapi import WebSocket

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

logger = logging.getLogger(__name__)

class HeartbeatManager:
    """서버->클라이언트: 5초마다 ping, 5초 내 pong 없으면 종료"""

    def __init__(self, ws: WebSocket, device_id: str, interval: int = 5, timeout: int = 5):
        self.ws = ws
        self.device_id = device_id
        self.interval = interval
        self.timeout = timeout
        self.last_pong_time: float = time.time()
        self._running = True

    async def start(self):
        while self._running:
            await asyncio.sleep(self.interval)
            elapsed = time.time() - self.last_pong_time
            if elapsed > (self.interval + self.timeout):
                logger.warning(f"[하트비트] 타임아웃: device_id={self.device_id}")
                await self.ws.close(code=1001, reason="heartbeat timeout")
                break
            try:
                await self.ws.send_json({"type": "ping", "ts": time.time()})
            except Exception as e:
                logger.error(f"[하트비트] ping 전송 실패: {e}")
                break

    def record_pong(self):
        self.last_pong_time = time.time()

    def stop(self):
        self._running = False
