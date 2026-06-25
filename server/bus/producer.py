# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import sys
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from server.bus.redis_client import RedisBus, redis_bus

if TYPE_CHECKING:
    from server.detection.schemas import Detection

logger = logging.getLogger(__name__)

DEFAULT_STREAM = "risk.events"
DEFAULT_TRACK_TTL = 30


class RiskEventProducer:
    """mid/low 위험 이벤트를 Redis Streams로 발행하고 Track 컨텍스트를 관리한다."""

    def __init__(self, bus: RedisBus = redis_bus, stream: str = DEFAULT_STREAM):
        self.bus = bus
        self.stream = stream

    async def publish_detection(
        self,
        event_id: str,
        detection: Detection,
        risk_hint: str,
    ) -> Optional[str]:
        payload: Dict[str, Any] = {
            "event_id": event_id,
            "track_id": detection.track_id or "unknown",
            "class_name": detection.class_name,
            "confidence": str(detection.confidence),
            "bbox": json.dumps(detection.bbox.model_dump()),
            "speed": str(detection.speed or 0.0),
            "direction": detection.direction or "unknown",
            "risk": risk_hint,
            "timestamp": str(time.time()),
        }
        return await self.bus.publish_event(self.stream, payload)

    async def update_track_context(
        self,
        track_id: str,
        bbox: Dict[str, float],
        speed: float,
        direction: str,
        class_name: str,
        ttl: int = DEFAULT_TRACK_TTL,
    ) -> bool:
        mapping = {
            "last_pos": json.dumps(bbox),
            "speed": str(speed),
            "direction": direction,
            "class_name": class_name,
            "updated_at": str(time.time()),
        }
        return await self.bus.set_track_context(track_id, mapping, ttl=ttl)
