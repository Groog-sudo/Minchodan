"""
tests/test_langgraph.py
6단계 LangGraph 오케스트레이션 단위 테스트 및 기능 검증 파일.
테스트 사양서(docs/test_specification.md)의 6단계(TC-LG-001 ~ 008) 기준을 따릅니다.
"""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add server directory to path (guide 3.3)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

import contextlib

from server.orchestration.graph import run_orchestrator
from server.orchestration.nodes.l1_classifier import classify_risk
from server.orchestration.nodes.l3_validator import l3_validator_node, validate_guidance

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")


def test_l1_risk_classification():
    """
    TC-LG-003: L1 위험도 분류 검증.
    중위험 클래스 포함 시 'mid', 미포함 시 'low' 분류를 검증합니다.
    """
    # mid 위험 분류 확인
    assert classify_risk(["kickboard"]) == "mid"
    assert classify_risk(["bollard", "person"]) == "mid"
    assert classify_risk(["bicycle"]) == "mid"
    assert classify_risk(["pothole"]) == "mid"

    # low 위험 분류 확인 (기본값)
    assert classify_risk(["tree"]) == "low"
    assert classify_risk([]) == "low"
    assert classify_risk(None) == "low"


def test_l3_guidance_validation_rules():
    """
    TC-LG-002: 방향 키워드 및 길이(20자 이내), 한국어 포함 규칙 검증.
    """
    # 정상 문장
    is_valid, errors = validate_guidance("좌측으로 피하세요")
    assert is_valid is True
    assert len(errors) == 0

    is_valid, errors = validate_guidance("앞에 정지하세요")
    assert is_valid is True

    # 오류 문장: 길이 초과 (20자 초과)
    long_text = "전방에 보도블록 파손 구역이 존재하오니 즉시 우측으로 이동하여 피해 가시기 바랍니다"
    is_valid, errors = validate_guidance(long_text)
    assert is_valid is False
    assert any("길이 초과" in e for e in errors)

    # 오류 문장: 방향 키워드 미포함
    is_valid, errors = validate_guidance("조심해서 천천히 가세요")
    assert is_valid is False
    assert any("방향 키워드 미포함" in e for e in errors)

    # 오류 문장: 한국어 미포함
    is_valid, errors = validate_guidance("Move to the left side")
    assert is_valid is False
    assert any("한국어 미포함" in e for e in errors)

    # 오류 문장: 빈 문장
    is_valid, errors = validate_guidance("")
    assert is_valid is False
    assert "빈 문장" in errors


@pytest.mark.asyncio
async def test_l3_validator_retry_logic():
    """
    TC-LG-005 & TC-LG-006: L3 검증 실패 시 재시도(RETRY) 카운트 제어 및 최종 정적 폴백 검증.
    """
    # 최초 실패 시 -> retry_count가 1로 증가하고 verified=False
    state_first_fail = {"guidance_text": "오류 가이드라인 (방향키워드없음)", "retry_count": 0}
    res = await l3_validator_node(state_first_fail)
    assert res["verified"] is False
    assert res["retry_count"] == 1
    assert len(res["validation_errors"]) > 0

    # 2차 실패 시 (retry_count == 1) -> 최종 고정 Fallback 메시지 주입 및 verified=True
    state_final_fail = {
        "guidance_text": "두번째 오류 가이드라인 (방향키워드없음)",
        "retry_count": 1,
    }
    res = await l3_validator_node(state_final_fail)
    assert res["verified"] is True
    assert res["guidance_text"] == "전방 주의, 천천히 멈추세요"
    assert res["direction"] == "정지"
    assert res["used_static_fallback"] is True


@pytest.mark.asyncio
async def test_langgraph_flow_with_mock_llm():
    """
    TC-LG-001, 002, 007: Mock LLM을 사용하여 전체 LangGraph StateGraph의 흐름과 분기 검증.
    """
    initial_state = {
        "detected_classes": ["bollard"],
        "rag_context": "볼라드 충돌 시 무릎 부상 위험이 있습니다. 우측으로 피하십시오.",
    }

    # L2 LLM 호출부 Mocking하여 정상 가이드 생성 시뮬레이션
    mock_response = AsyncMock()
    mock_response.content = "우측으로 피하세요"

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = mock_response
        mock_factory.return_value = mock_client

        # 전체 그래프 실행
        result = await run_orchestrator(initial_state)

        # 1. 20자 이내 검증
        assert len(result["guidance_text"]) <= 20
        # 2. 방향 키워드 매핑 확인
        assert result["direction"] == "우"
        # 3. 검증 성공 상태
        assert result["verified"] is True
        # 4. 재시도 없었음
        assert result.get("retry_count", 0) == 0
        # 5. 지연 시간 계산됨
        assert "total_latency_ms" in result
        assert result["total_latency_ms"] >= 0.0


@pytest.mark.asyncio
async def test_langgraph_retry_recovery_flow():
    """
    TC-LG-007: 가드레일 위반 시 RETRY 엣지를 탄 후, 2차 시도에서 성공하여 END에 도달하는 흐름 검증.
    """
    initial_state = {
        "detected_classes": ["kickboard"],
        "rag_context": "킥보드는 속도가 빠릅니다. 우측으로 피하세요.",
    }

    # 1차 시도는 비정상 문장(길이 초과), 2차 시도는 정상 문장 반환하도록 설정
    mock_response_1 = AsyncMock()
    mock_response_1.content = "전방 우측 도로에 킥보드가 빠르게 접근하고 있으니 좌측으로 조심해서 이동하세요"  # 44자 (길이 초과)

    mock_response_2 = AsyncMock()
    mock_response_2.content = "좌측으로 피하세요"  # 정상 (9자, 방향포함)

    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        # ainvoke 연속 호출 시 다른 응답 반환하도록 side_effect 설정
        mock_client.ainvoke.side_effect = [mock_response_1, mock_response_2]
        mock_factory.return_value = mock_client

        # 실행
        result = await run_orchestrator(initial_state)

        # 2차 시도에 성공하였으므로 guidance_text는 2차 시도의 것
        assert result["guidance_text"] == "좌측으로 피하세요"
        assert result["direction"] == "좌"
        assert result["verified"] is True
        assert result["retry_count"] == 1
        assert result.get("used_static_fallback", False) is False


@pytest.mark.asyncio
async def test_langgraph_api_error_fallback():
    """
    TC-LG-008: LLM API 호출 장애 발생 시 정적 Fallback으로 즉시 우회하여 파이프라인 영속성이 확보되는지 검증.
    """
    initial_state = {"detected_classes": ["kickboard"]}

    # ainvoke 호출 시 강제로 Exception을 발생시킴
    with patch(
        "server.orchestration.llm_client_factory.LLMClientFactory.get_client"
    ) as mock_factory:
        mock_client = AsyncMock()
        mock_client.ainvoke.side_effect = Exception("Ollama Connection Timeout")
        mock_factory.return_value = mock_client

        # 실행 (오케스트레이터가 충돌하지 않고 fallback 텍스트를 반환하는지 검증)
        result = await run_orchestrator(initial_state)

        assert result["guidance_text"] == "전방 주의, 천천히 멈추세요"
        assert result["direction"] == "정지"
        assert result["used_static_fallback"] is True
        assert result["verified"] is True
        assert "total_latency_ms" in result
