"""Phase 3: 패스트 레인 노드·LangGraph 분기·TTS 클립 캐시 검증."""

import os
import sys
import wave
from unittest.mock import AsyncMock, patch

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from server.orchestration.graph import run_orchestrator
from server.orchestration.nodes.fast_lane import (
    build_fast_lane_guidance,
    can_use_fast_lane,
    fast_lane_node,
    make_fast_lane_cache_key,
)
from server.orchestration.nodes.l3_validator import validate_guidance
from server.tts.realtime_tts import RealtimeTTS


def _fast_lane_state(**overrides) -> dict:
    base = {
        "detected_classes": ["전동 킥보드"],
        "object_ko": "전동 킥보드",
        "clock_direction": "10시",
        "distance": "near",
        "is_departing_confirmed": False,
        "navigation_guidance": "",
        "rag_context": "관련 수칙 없음",
    }
    base.update(overrides)
    return base


def test_build_fast_lane_guidance_near():
    text = build_fast_lane_guidance("10시", "전동 킥보드", "near")
    assert text == "10시 방향 전동 킥보드 주의하세요"
    assert len(text) <= 20


def test_build_fast_lane_guidance_medium_matches_near_pattern():
    text = build_fast_lane_guidance("10시", "전동 킥보드", "medium")
    assert text == "10시 방향 전동 킥보드 주의하세요"
    assert "확인하세요" not in text


def test_build_fast_lane_guidance_front_12_oclock_with_avoid():
    text = build_fast_lane_guidance("12시", "볼라드", "medium", avoid_clock="2시")
    assert text == "전방 볼라드, 2시로 우회하세요"
    assert len(text) <= 20


def test_build_fast_lane_guidance_front_12_oclock():
    text = build_fast_lane_guidance("12시", "볼라드", "near")
    assert text == "전방 볼라드 주의하세요"


def test_make_fast_lane_cache_key():
    key = make_fast_lane_cache_key("10시", "전동 킥보드", "near")
    assert key == "10시_전동_킥보드_near_caution"


def test_make_fast_lane_cache_key_ignores_avoid_clock_off_front():
    """12시가 아니면 avoid_clock이 있어도 무시(해당 방향에는 우회 문구 자체가 없음)."""
    key = make_fast_lane_cache_key("10시", "전동 킥보드", "near", avoid_clock="2시")
    assert key == "10시_전동_킥보드_near_caution"


def test_make_fast_lane_cache_key_front_without_avoid():
    key = make_fast_lane_cache_key("12시", "볼라드", "medium")
    assert key == "12시_볼라드_medium_caution"


def test_make_fast_lane_cache_key_front_with_avoid_differs_from_plain():
    """2026-07-20 수정: 12시 + 우회 방향은 단순 주의 문구와 다른 키를 가져야
    한다(같은 키면 잘못된 오디오가 재생되는 정확성 결함)."""
    plain_key = make_fast_lane_cache_key("12시", "볼라드", "medium")
    avoid_key = make_fast_lane_cache_key("12시", "볼라드", "medium", avoid_clock="2시")
    assert avoid_key != plain_key
    assert avoid_key == "12시_볼라드_medium_avoid2시"


def test_make_fast_lane_cache_key_front_avoid_normalizes_1_2_3_to_2():
    key = make_fast_lane_cache_key("12시", "볼라드", "medium", avoid_clock="1시")
    assert key == "12시_볼라드_medium_avoid2시"


def test_can_use_fast_lane_single_object():
    assert can_use_fast_lane(_fast_lane_state()) is True


def test_can_use_fast_lane_allows_multiple_detected_classes():
    """2026-07-20: 프레임 내 다른 객체가 더 잡혀도(주위험 객체 object_ko 기준으로 완화)
    패스트 레인을 차단하지 않는다 - 안내문은 항상 object_ko 하나만 언급하므로 안전."""
    state = _fast_lane_state(detected_classes=["전동 킥보드", "볼라드"])
    assert can_use_fast_lane(state) is True


def test_can_use_fast_lane_rejects_empty_classes_for_non_surface_object():
    """detected_classes가 비었는데 object_ko가 노면(caution/roadway)이 아니면 차단."""
    state = _fast_lane_state(detected_classes=[])
    assert can_use_fast_lane(state) is False


def test_can_use_fast_lane_allows_empty_classes_for_surface_object():
    """detected_classes가 비어도 object_ko가 노면(caution/roadway)이면 허용."""
    state = _fast_lane_state(detected_classes=[], object_ko="주의 노면")
    assert can_use_fast_lane(state) is True


def test_can_use_fast_lane_rejects_departure():
    state = _fast_lane_state(is_departing_confirmed=True)
    assert can_use_fast_lane(state) is False


def test_can_use_fast_lane_rejects_navigation():
    state = _fast_lane_state(navigation_guidance="100m 직진")
    assert can_use_fast_lane(state) is False


@pytest.mark.asyncio
async def test_fast_lane_node_sets_verified_without_llm():
    state = _fast_lane_state()
    result = await fast_lane_node(state)
    assert result["used_fast_lane"] is True
    assert result["verified"] is True
    assert result["fast_lane_cache_key"] == "10시_전동_킥보드_near_caution"
    is_valid, _ = validate_guidance(result["guidance_text"])
    assert is_valid is True


@pytest.mark.asyncio
async def test_fast_lane_node_front_avoid_cache_key_matches_guidance_text():
    """2026-07-20 회귀 방지: 12시+우회 시나리오의 cache_key가 guidance_text와
    일치하는 변형을 가리켜야 한다(다른 클립이 잘못 재생되는 것 방지)."""
    state = _fast_lane_state(
        object_ko="볼라드",
        clock_direction="12시",
        avoid_clock_direction="2시",
    )
    result = await fast_lane_node(state)
    assert result["guidance_text"] == "전방 볼라드, 2시로 우회하세요"
    assert result["fast_lane_cache_key"] == "12시_볼라드_near_avoid2시"


@pytest.mark.asyncio
async def test_run_orchestrator_fast_lane_skips_llm():
    state = _fast_lane_state()
    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_factory.return_value = mock_client

        result = await run_orchestrator(state)

        mock_client.ainvoke.assert_not_called()
        assert result["used_fast_lane"] is True
        assert result["guidance_text"] == "10시 방향 전동 킥보드 주의하세요"
        assert result["verified"] is True
        assert result["total_latency_ms"] < 500


@pytest.mark.asyncio
async def test_run_orchestrator_missing_clock_uses_llm():
    """구조화 필드(clock_direction)가 없으면 여전히 L2 LLM으로 빠진다."""
    state = _fast_lane_state(clock_direction="")
    mock_response = AsyncMock()
    mock_response.content = "10시 방향 주의하세요"

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_factory.return_value = mock_client

        result = await run_orchestrator(state)

        mock_client.ainvoke.assert_called()
        assert result.get("used_fast_lane") is not True


@pytest.mark.asyncio
async def test_run_orchestrator_multi_object_still_uses_fast_lane():
    """2026-07-20: 다중 객체 탐지여도 주위험 객체(object_ko) 기준으로 패스트 레인을 탄다."""
    state = _fast_lane_state(detected_classes=["전동 킥보드", "볼라드"])
    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_factory.return_value = mock_client

        result = await run_orchestrator(state)

        mock_client.ainvoke.assert_not_called()
        assert result["used_fast_lane"] is True


@pytest.mark.asyncio
async def test_synthesize_fast_lane_loads_presynthesized_clip(tmp_path):
    cache_key = "10시_전동_킥보드_near_caution"
    clip_path = tmp_path / f"{cache_key}.wav"
    with wave.open(str(clip_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 1600)

    tts = RealtimeTTS(tts_service=AsyncMock(), guide_clips_dir=str(tmp_path))
    orch = {
        "guidance_text": "10시 방향 전동 킥보드 주의하세요",
        "fast_lane_cache_key": cache_key,
        "used_fast_lane": True,
    }
    b64_audio, duration_ms = await tts.synthesize_fast_lane(orch)
    assert b64_audio is not None
    assert duration_ms > 0
    tts.tts.generate.assert_not_called()
