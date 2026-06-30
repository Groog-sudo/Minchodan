# -*- coding: utf-8 -*-
# server/api/session_manager.py
import logging
import sys
from typing import Dict
from fastapi import WebSocket

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

logger = logging.getLogger(__name__)

class SessionManager:
    """활성 WebSocket 연결을 추적하고 관리하는 싱글턴 클래스"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(f"[연결] device_id={device_id}, 현재 접속: {len(self.active_connections)}명")

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"[해제] device_id={device_id}, 현재 접속: {len(self.active_connections)}명")

    async def send_json(self, device_id: str, data: dict):
        ws = self.active_connections.get(device_id)
        if ws:
            await ws.send_json(data)

    def is_connected(self, device_id: str) -> bool:
        return device_id in self.active_connections

manager = SessionManager()
