# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path

import pytest

import server.stt.stt_to_llm_bridge as stt_bridge_module
from server.stt.stt_schema import SegmentOut, SttTranscribeResult
from server.stt.stt_to_llm_bridge import SttToLlmBridge


# ============================================================
# 테스트 파일 역할
# ============================================================
# [바이브 코딩 부분]
# - STT 결과를 오케스트레이션 입력으로 변환하는 틀을 검증.
# - invoke_existing_llm의 빈 입력 폴백/정상 응답 매핑을 검증.
#
# [하드 코딩 부분]
# - invoke_existing_llm 예외 폴백(source=stt-bridge-error) 시나리오를 직접 추가.
# - 최소 추가 권장 시나리오:
#   1) stt_result.text 빈 값에서 폴백 dict 키/값 검증
#   2) run_orchestrator 정상 응답 시 guidance_text 전달 검증
#   3) run_orchestrator 예외 발생 시 오류 폴백(source 구분) 검증
#   4) 로그에 원문 전체 미기록(길이/파일명만 기록) 정책 검증


def _make_stt_result(text: str, has_input: bool = True) -> SttTranscribeResult:
    return SttTranscribeResult(
        model_name="faster-whisper-base",
        text=text,
        language="ko",
        duration=1.0,
        segments=[SegmentOut(start=0.0, end=1.0, text=text)] if has_input else [],
        has_input=has_input,
        saved_file=Path("dummy.wav").name,
    )


def test_build_orch_input_success() -> None:
    bridge = SttToLlmBridge()
    result = _make_stt_result("전방에 장애물이 있습니다")

    orch_input = bridge.build_orch_input(result)

    assert orch_input["event"]["source"] == "stt"
    assert orch_input["rag_context"] == "전방에 장애물이 있습니다"
    assert orch_input["detected_classes"] == ["speech_to_text"]


@pytest.mark.asyncio
async def test_invoke_existing_llm_empty_fallback() -> None:
    bridge = SttToLlmBridge()
    result = _make_stt_result("", has_input=False)

    response = await bridge.invoke_existing_llm(result)

    assert response["source"] == "stt-bridge-empty"
    assert response["used_fallback_llm"] is True


@pytest.mark.asyncio
async def test_invoke_existing_llm_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_run_orchestrator(state: dict) -> dict:
        assert state["event"]["source"] == "stt"
        return {
            "guidance_text": "오른쪽으로 피해 이동하세요",
            "used_fallback_llm": False,
        }

    monkeypatch.setattr(stt_bridge_module, "run_orchestrator", _fake_run_orchestrator)

    bridge = SttToLlmBridge()
    result = _make_stt_result("테스트")
    response = await bridge.invoke_existing_llm(result)

    assert response == {
        "guidance_text": "오른쪽으로 피해 이동하세요",
        "used_fallback_llm": False,
        "source": "stt-bridge",
    }
