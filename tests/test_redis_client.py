import sys
from unittest.mock import AsyncMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pytest

from server.bus import redis_client as rc
from server.bus.redis_client import RedisBus


class TestPublishEventTrimming:
    """2026-07-20: xadd에 maxlen이 없어 risk.events가 무제한 누적된 결함(실기기 29시간
    테스트에서 236,529건 확인) 회귀 방지. publish_event가 항상 approximate MAXLEN을
    xadd에 전달하는지 검증."""

    @pytest.mark.asyncio
    async def test_publish_event_passes_maxlen_and_approximate(self, monkeypatch):
        monkeypatch.setattr(rc, "REDIS_STREAM_MAXLEN", 5000)
        bus = RedisBus(url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xadd = AsyncMock(return_value="1-0")

        message_id = await bus.publish_event("risk.events", {"foo": "bar"})

        assert message_id == "1-0"
        bus._redis.xadd.assert_called_once_with(
            "risk.events", {"foo": "bar"}, maxlen=5000, approximate=True
        )

    @pytest.mark.asyncio
    async def test_publish_event_returns_none_when_disconnected(self):
        bus = RedisBus(url="redis://localhost:6379")
        bus._redis = None
        result = await bus.publish_event("risk.events", {"foo": "bar"})
        assert result is None

    @pytest.mark.asyncio
    async def test_publish_event_swallows_xadd_exception(self):
        bus = RedisBus(url="redis://localhost:6379")
        bus._redis = AsyncMock()
        bus._redis.xadd = AsyncMock(side_effect=RuntimeError("boom"))
        result = await bus.publish_event("risk.events", {"foo": "bar"})
        assert result is None
