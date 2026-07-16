import os
import sys
from unittest.mock import MagicMock

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.detection.consumer import DetectionConsumer


@pytest.mark.asyncio
async def test_broadcast_risk_event_payload(monkeypatch):
    consumer = DetectionConsumer(splitter=MagicMock(), pipeline=MagicMock())
    captured: list[dict] = []

    async def _fake_broadcast(event_type: str, payload: dict):
        captured.append({"event_type": event_type, "payload": payload})

    monkeypatch.setattr(
        "server.mcp.manager.mcp_manager.broadcast_event",
        _fake_broadcast,
    )

    await consumer._broadcast_risk_event(
        event_id="evt-001",
        risk_level="high",
        class_name="scooter",
        confidence=0.91,
        direction="front",
        guidance_text="[반사 클립] reflex_clips/high_front.wav",
        device_id="dev-001",
    )

    assert len(captured) == 1
    assert captured[0]["event_type"] == "risk_event"
    payload = captured[0]["payload"]
    assert payload["event_id"] == "evt-001"
    assert payload["risk_level"] == "high"
    assert payload["class_name"] == "scooter"
    assert payload["confidence"] == 0.91
    assert payload["direction"] == "front"
    assert payload["guidance_text"].startswith("[반사 클립]")


def test_normalize_risk_level_fallback():
    assert DetectionConsumer._normalize_risk_level("high") == "high"
    assert DetectionConsumer._normalize_risk_level("none") == "low"
    assert DetectionConsumer._normalize_risk_level(None) == "low"
