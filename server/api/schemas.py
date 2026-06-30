# -*- coding: utf-8 -*-
# server/api/schemas.py
import sys
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

class WSMessage(BaseModel):
    type: str                        # "hello" | "ping" | "pong" | "detection" | "welcome" | "ack" | "alert_reflex" | "guide"
    device_id: Optional[str] = None
    token: Optional[str] = None
    session_id: Optional[str] = None
    server_time: Optional[str] = None
    ts: Optional[float] = None
    payload: Optional[dict[str, Any]] = None

class WelcomeMessage(BaseModel):
    type: str = "welcome"
    session_id: str
    server_time: str

class AckMessage(BaseModel):
    type: str = "ack"
    event_id: str
    received_at: str
