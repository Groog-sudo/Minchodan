"""
tests/test_clock_direction.py
인지 경로 "N시 방향" 안내(2026-07-13 도입) 단위 테스트.
- server/detection/direction.py: estimate_clock_direction (bbox -> 9시~3시)
- server/orchestration/nodes/l2_generator.py: extract_direction, 프롬프트 주입
- server/orchestration/nodes/l3_validator.py: 시계 방향도 방향 키워드로 인정
"""

import os
import sys
from unittest.mock import AsyncMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

import pytest

from server.detection.direction import estimate_clock_direction
from server.orchestration.nodes.l2_generator import extract_direction, l2_generator_node
from server.orchestration.nodes.l3_validator import validate_guidance


class _Box:
    def __init__(self, x, w):
        self.x = x
        self.y = 0.0
        self.w = w
        self.h = 100.0


def test_estimate_clock_direction_left_edge_is_9_oclock():
    assert estimate_clock_direction(_Box(x=0.0, w=0.0), frame_width=640.0) == "9시"


def test_estimate_clock_direction_center_is_12_oclock():
    assert estimate_clock_direction(_Box(x=300.0, w=40.0), frame_width=640.0) == "12시"


def test_estimate_clock_direction_right_edge_is_3_oclock():
    assert estimate_clock_direction(_Box(x=640.0, w=0.0), frame_width=640.0) == "3시"


def test_estimate_clock_direction_zero_frame_width_falls_back_to_front():
    assert estimate_clock_direction(_Box(x=10.0, w=10.0), frame_width=0.0) == "12시"


def test_extract_direction_prefers_clock_pattern_over_keywords():
    # "좌"라는 글자가 없어도 시계 방향이 우선 추출된다.
    assert extract_direction("2시 방향 주의하세요") == "2시"


def test_extract_direction_falls_back_to_keywords_when_no_clock_pattern():
    assert extract_direction("왼쪽으로 이동하세요") == "좌"


def test_extract_direction_empty_text():
    assert extract_direction("") == ""


def test_validate_guidance_accepts_clock_direction_only():
    """구 키워드(좌/우 등)가 전혀 없어도 'N시 방향' 표현만으로 방향 키워드 검사를 통과해야 한다."""
    is_valid, errors = validate_guidance("2시 방향 주의하세요")
    assert is_valid is True
    assert errors == []


def test_validate_guidance_still_rejects_no_direction_at_all():
    is_valid, errors = validate_guidance("조심해서 천천히 가세요")
    assert is_valid is False
    assert "방향 키워드 미포함" in errors


@pytest.mark.asyncio
async def test_l2_generator_prompt_includes_clock_direction():
    state = {
        "detected_classes": ["car"],
        "risk_level": "mid",
        "rag_context": "관련 수칙 없음",
        "clock_direction": "2시",
        "retry_count": 0,
        "validation_errors": [],
    }

    mock_response = AsyncMock()
    mock_response.content = "2시 방향 주의하세요"

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_factory.return_value = mock_client

        result = await l2_generator_node(state)

        sent_messages = mock_client.ainvoke.call_args[0][0]
        user_prompt = sent_messages[1].content
        assert "[탐지 방향]: 2시 방향" in user_prompt
        assert result["direction"] == "2시"


@pytest.mark.asyncio
async def test_l2_generator_omits_direction_line_when_no_clock_direction():
    """순수 노면 이탈 등 clock_direction이 없는 경우 [탐지 방향] 줄 자체가 생략돼야 한다."""
    state = {
        "detected_classes": [],
        "risk_level": "mid",
        "rag_context": "관련 수칙 없음",
        "clock_direction": "",
        "retry_count": 0,
        "validation_errors": [],
    }

    mock_response = AsyncMock()
    mock_response.content = "전방 주의하세요"

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_factory.return_value = mock_client

        await l2_generator_node(state)

        sent_messages = mock_client.ainvoke.call_args[0][0]
        user_prompt = sent_messages[1].content
        assert "[탐지 방향]" not in user_prompt
