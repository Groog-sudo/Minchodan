"""Phase 2: 인지 경로 구조화 필드(distance, object_ko, 한국어 CLASS_TEXT) 검증."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.direction import estimate_distance
from server.detection.risk_rules import CLASS_TEXT, class_name_to_ko
from server.orchestration.nodes.fallback_node import fallback_node
from server.orchestration.nodes.l2_generator import l2_generator_node


class _Box:
    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x
        self.y = y
        self.w = w
        self.h = h


def test_class_name_to_ko_ssot():
    assert class_name_to_ko("scooter") == CLASS_TEXT["scooter"]
    assert class_name_to_ko("unknown_x") == "unknown_x"
    assert class_name_to_ko("") == "장애물"


def test_estimate_distance_near_for_large_bbox():
    bbox = _Box(x=200.0, y=200.0, w=200.0, h=200.0)
    assert estimate_distance(bbox, 640.0, 480.0, "scooter") == "near"


@pytest.mark.asyncio
async def test_l2_generator_prompt_includes_distance():
    state = {
        "detected_classes": ["전동 킥보드"],
        "risk_level": "mid",
        "rag_context": "관련 수칙 없음",
        "clock_direction": "10시",
        "distance": "near",
        "retry_count": 0,
        "validation_errors": [],
    }

    mock_response = AsyncMock()
    mock_response.content = "전동 킥보드 주의하세요"

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_factory.return_value = mock_client

        await l2_generator_node(state)

        user_prompt = mock_client.ainvoke.call_args[0][0][1].content
        assert "[탐지 장애물]: 전동 킥보드" in user_prompt
        assert "[탐지 방향]: 10시 방향" in user_prompt
        assert "[탐지 거리]: near" in user_prompt


@pytest.mark.asyncio
async def test_fallback_uses_korean_detected_class_as_is():
    state = {
        "event": {"event_id": "evt-1"},
        "detected_classes": ["전동 킥보드"],
        "clock_direction": "11시",
        "risk_level": "mid",
    }
    result = await fallback_node(state)
    assert "11시 방향" in result["guidance_text"]
    assert "전동 킥보드" in result["guidance_text"]
