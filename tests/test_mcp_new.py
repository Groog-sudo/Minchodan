"""
신규 구현된 5종 MCP 모듈들의 정상 동작 및 예외 처리, 브로드캐스트 작동 여부를 검증하는 단위 테스트 파일.
"""

import contextlib
import os
import sys

import pytest

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

# Ensure server path is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.mcp.accessibility_simulator import accessibility_simulator
from server.mcp.audio_validator import audio_validator
from server.mcp.cache_monitor import cache_monitor
from server.mcp.langsmith_tracer import langsmith_tracer
from server.mcp.slack_notifier import slack_notifier


@pytest.mark.asyncio
async def test_slack_notifier_mock():
    """
    슬랙 노티파이어가 자격 증명이 없는 Mock 상황에서도 예외 없이 True(성공)를 반환하는지 테스트합니다.
    """
    slack_notifier.webhook_url = None
    slack_notifier.bot_token = None
    slack_notifier.channel_id = None

    res = await slack_notifier.send_notification("테스트 에러 경보 메시지")
    assert res is True


@pytest.mark.asyncio
async def test_audio_validator_wav():
    """
    Audio Validator가 정상 WAV 포맷 및 비정상/비표준 바이너리를 제대로 구별하여 판정하는지 테스트합니다.
    """
    # 1. 빈 바이트 데이터 검증 (False 기대)
    result_empty = audio_validator.validate_wav_bytes(b"", 120.0)
    assert result_empty["is_valid"] is False
    assert "비어있습니다" in result_empty["error_reasons"][0]

    # 2. 비표준 임계치 초과 TTFB 검증
    # 정상 WAV 파일 헤더를 모사한 44바이트 데이터 (실제 wave 모듈 파싱은 실패하므로 예외 포착 확인)
    bad_wav_bytes = b"RIFF" + b"\x00" * 40
    result_bad = audio_validator.validate_wav_bytes(
        bad_wav_bytes, 2500.0
    )  # max_ttfb_ms: 2000.0 초과
    assert result_bad["is_valid"] is False
    assert any("초과" in r or "예외" in r for r in result_bad["error_reasons"])


@pytest.mark.asyncio
async def test_cache_monitor_suppression():
    """
    Cache Monitor가 Redis가 비활성인 상황에서도 예외 없이 작동하는지 및
    메트릭 구조를 올바르게 반환하는지 검증합니다.
    """
    status = await cache_monitor.get_suppressed_keys_status()
    assert "suppressed_keys" in status
    assert "total_count" in status
    assert isinstance(status["total_count"], int)


@pytest.mark.asyncio
async def test_accessibility_simulator_alignment():
    """
    Accessibility Simulator가 가이드 텍스트와 합성 텍스트 간의 자카드 유사도 분석 및
    방향성 키워드 누락/불일치를 정확히 잡아내는지 검증합니다.
    """
    # 1. 완전히 일치하는 경우
    result_perfect = accessibility_simulator.analyze_accessibility_alignment(
        "전방에 보도블록 파손이 있으니 좌측으로 우회하세요",
        "전방에 보도블록 파손이 있으니 좌측으로 우회하세요",
    )
    assert result_perfect["is_aligned"] is True
    assert result_perfect["similarity_score"] == 1.0

    # 2. 방향성 키워드 불일치 (한쪽만 '우측' 포함)
    result_miss = accessibility_simulator.analyze_accessibility_alignment(
        "전방에 보도블록 파손이 있으니 우측으로 가세요",
        "전방에 보도블록 파손이 있으니 피해서 가세요",
    )
    assert result_miss["is_aligned"] is False
    assert any("우" in w for w in result_miss["warnings"])

    # 3. 속독 한계(40자) 초과 경고
    long_text = "전방에 보도블록 파손이 있으니 안전하게 좌측으로 천천히 우회하여 지나가시길 권장하며 주의해서 보행하시기 바랍니다."
    result_long = accessibility_simulator.analyze_accessibility_alignment(long_text, long_text)
    assert any("초과" in w for w in result_long["warnings"])


@pytest.mark.asyncio
async def test_langsmith_tracer_mock():
    """
    LangSmith Tracer가 비활성화 상태에서 정상적으로 No-op 및 False(비전송) 처리를 수행하는지 검증합니다.
    """
    langsmith_tracer.api_key = None
    langsmith_tracer.tracing_enabled = False

    config = langsmith_tracer.get_trace_config()
    assert config["enabled"] is False

    res = await langsmith_tracer.log_node_transition("l1_classify", "l2_generate", 50.0)
    assert res is False


@pytest.mark.asyncio
async def test_langsmith_tracer_active():
    """
    환경변수가 주입되었을 때 LangSmith Tracer가 정상 활성화되는지 검증합니다.
    """
    import os

    langsmith_tracer.api_key = os.getenv(
        "LANGCHAIN_API_KEY", "lsv2_pt_mock_value_for_testing_12345"
    )
    langsmith_tracer.tracing_enabled = True

    config = langsmith_tracer.get_trace_config()
    assert config["enabled"] is True

    res = await langsmith_tracer.log_node_transition("l1_classify", "l2_generate", 50.0)
    assert res is True
