"""
tests/test_departure_hysteresis.py
보도 이탈 N프레임 히스테리시스(DetectionConsumer)와 LangGraph 인지 경로 연동 테스트.
"""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from server.detection.consumer import DEPARTURE_CONFIRM_STREAK, DetectionConsumer
from server.orchestration.graph import run_orchestrator
from server.orchestration.nodes.l1_classifier import l1_classifier_node


def _make_consumer() -> DetectionConsumer:
    # splitter/pipeline은 실제 Redis/큐 연결이 필요 없는 더미 객체로 대체한다.
    # _update_departure_streak는 두 속성 모두 참조하지 않는 순수 상태 갱신 메서드다.
    return DetectionConsumer(splitter=object(), pipeline=object())


def test_departure_streak_confirms_after_threshold():
    consumer = _make_consumer()
    device_id = "device-1"

    for i in range(DEPARTURE_CONFIRM_STREAK - 1):
        confirmed = consumer._update_departure_streak(device_id, True)
        assert confirmed is False, f"{i + 1}번째 프레임에서 조기 확정됨"

    confirmed = consumer._update_departure_streak(device_id, True)
    assert confirmed is True


def test_departure_streak_resets_on_non_departure_frame():
    consumer = _make_consumer()
    device_id = "device-1"

    for _ in range(DEPARTURE_CONFIRM_STREAK - 1):
        consumer._update_departure_streak(device_id, True)

    # 임계값 도달 직전 한 프레임이라도 이탈이 아니면 카운터가 리셋되어야 한다.
    confirmed = consumer._update_departure_streak(device_id, False)
    assert confirmed is False
    assert consumer._departure_streak[device_id] == 0


def test_departure_streak_is_per_device():
    consumer = _make_consumer()
    for _ in range(DEPARTURE_CONFIRM_STREAK):
        consumer._update_departure_streak("device-A", True)
    # device-B는 별도 카운터라 확정되지 않아야 한다.
    confirmed_b = consumer._update_departure_streak("device-B", True)
    assert confirmed_b is False
    assert consumer._departure_streak["device-A"] == DEPARTURE_CONFIRM_STREAK
    assert consumer._departure_streak["device-B"] == 1


@pytest.mark.asyncio
async def test_l1_classifier_upgrades_low_to_mid_when_departure_confirmed():
    state = {"detected_classes": [], "is_departing_confirmed": True}
    result = await l1_classifier_node(state)
    assert result["risk_level"] == "mid"


@pytest.mark.asyncio
async def test_l1_classifier_stays_low_when_departure_not_confirmed():
    state = {"detected_classes": [], "is_departing_confirmed": False}
    result = await l1_classifier_node(state)
    assert result["risk_level"] == "low"


@pytest.mark.asyncio
async def test_l1_classifier_object_stays_low_without_departure():
    # 2026-07-14: 객체 클래스만으로는 mid가 아니다. 이탈 확정 없으면 low 유지.
    state = {"detected_classes": ["bollard"], "is_departing_confirmed": False}
    result = await l1_classifier_node(state)
    assert result["risk_level"] == "low"


@pytest.mark.asyncio
async def test_orchestrator_generates_guidance_for_pure_surface_departure():
    """탐지 객체 없이(순수 보도 이탈) 히스테리시스가 확정된 이벤트도 안내 문장이 나와야 한다."""
    initial_state = {
        "detected_classes": [],
        "rag_context": "관련 수칙 없음",
        "is_departing_confirmed": True,
        "braille_direction": "left",
    }

    mock_response = AsyncMock()
    mock_response.content = "왼쪽으로 이동하세요"

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_factory.return_value = mock_client

        result = await run_orchestrator(initial_state)

        assert result["verified"] is True
        assert result["direction"] == "좌"
        assert len(result["guidance_text"]) <= 20


@pytest.mark.asyncio
async def test_l2_generator_prompt_includes_braille_direction():
    from server.orchestration.nodes.l2_generator import l2_generator_node

    state = {
        "detected_classes": [],
        "risk_level": "mid",
        "rag_context": "관련 수칙 없음",
        "is_departing_confirmed": True,
        "braille_direction": "right",
        "retry_count": 0,
        "validation_errors": [],
    }

    mock_response = AsyncMock()
    mock_response.content = "오른쪽으로 이동하세요"

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_factory.return_value = mock_client

        await l2_generator_node(state)

        sent_messages = mock_client.ainvoke.call_args[0][0]
        user_prompt = sent_messages[1].content
        assert "점자블록이 오른쪽에 있습니다" in user_prompt
