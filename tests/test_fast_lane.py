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


def test_can_use_fast_lane_single_object():
    assert can_use_fast_lane(_fast_lane_state()) is True


def test_can_use_fast_lane_rejects_multiple_objects():
    state = _fast_lane_state(detected_classes=["전동 킥보드", "볼라드"])
    assert can_use_fast_lane(state) is False


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
async def test_run_orchestrator_multi_object_uses_llm():
    state = _fast_lane_state(detected_classes=["전동 킥보드", "볼라드"])
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
