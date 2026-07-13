# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from types import SimpleNamespace

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
# - 목적지 파싱 -> navigation 연동 핵심 분기를 고정 케이스로 검증.
# - 최소 핵심 시나리오:
#   1) Wake-up 명령으로 WAITING_FOR_DESTINATION 상태 전환
#   2) Shutdown 명령으로 IDLE 상태 및 경로 초기화
#   3) WAITING 상태에서 목적지 입력 시 경로 수립 성공
#   4) 목적지 검색 실패 시 navigation-setup-fail 폴백


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


class _FakeNavManager:
    """테스트에서 navigation 상태 전이와 경로 갱신 호출만 추적한다."""

    def __init__(self, status: str = "IDLE", detection_enabled: bool = False):
        self.status = status
        self.last_route: list[dict] = []
        self.session = SimpleNamespace(lat=None, lon=None)
        self.awaiting_question = False
        self.awaiting_intent = False
        self.detection_enabled = detection_enabled

    def get_status(self, device_id: str) -> str:
        _ = device_id
        return self.status

    def set_status(self, device_id: str, status: str) -> None:
        _ = device_id
        self.status = status

    def update_route(self, device_id: str, waypoints: list[dict]) -> None:
        _ = device_id
        self.last_route = waypoints

    def _get_or_create_session(self, device_id: str):
        _ = device_id
        return self.session

    def is_awaiting_question(self, device_id: str) -> bool:
        _ = device_id
        return self.awaiting_question

    def set_awaiting_question(self, device_id: str, value: bool) -> None:
        _ = device_id
        self.awaiting_question = value

    def is_awaiting_intent(self, device_id: str) -> bool:
        _ = device_id
        return self.awaiting_intent

    def set_awaiting_intent(self, device_id: str, value: bool) -> None:
        _ = device_id
        self.awaiting_intent = value

    def is_detection_enabled(self, device_id: str) -> bool:
        _ = device_id
        return self.detection_enabled

    def set_detection_enabled(self, device_id: str, enabled: bool) -> None:
        _ = device_id
        self.detection_enabled = enabled
        if not enabled and self.status == "WAITING_FOR_DESTINATION":
            self.status = "IDLE"
        if not enabled:
            self.awaiting_intent = False


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

    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "stt-bridge-empty"
    assert response["used_fallback_llm"] is True


@pytest.mark.asyncio
async def test_invoke_existing_llm_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import server.navigation.manager as nav_manager_module

    async def _fake_run_orchestrator(state: dict) -> dict:
        assert state["event"]["source"] == "stt"
        return {
            "guidance_text": "오른쪽으로 피해 이동하세요",
            "used_fallback_llm": False,
        }

    monkeypatch.setattr(stt_bridge_module, "run_orchestrator", _fake_run_orchestrator)
    # 탐지 ON일 때만 장애물 orch 경로를 탄다(2026-07-13 분기).
    monkeypatch.setattr(
        nav_manager_module,
        "nav_manager",
        _FakeNavManager(status="IDLE", detection_enabled=True),
    )

    bridge = SttToLlmBridge()
    result = _make_stt_result("테스트")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response == {
        "guidance_text": "오른쪽으로 피해 이동하세요",
        "used_fallback_llm": False,
        "source": "stt-bridge",
    }


@pytest.mark.asyncio
async def test_invoke_existing_llm_error_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import server.navigation.manager as nav_manager_module

    async def _fake_run_orchestrator(_state: dict) -> dict:
        raise RuntimeError("forced-error")

    monkeypatch.setattr(stt_bridge_module, "run_orchestrator", _fake_run_orchestrator)
    monkeypatch.setattr(
        nav_manager_module,
        "nav_manager",
        _FakeNavManager(status="IDLE", detection_enabled=True),
    )

    bridge = SttToLlmBridge()
    result = _make_stt_result("테스트")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "stt-bridge-error"
    assert response["used_fallback_llm"] is True


@pytest.mark.asyncio
async def test_detection_off_routes_to_free_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """탐지 OFF면 일반 발화가 물체탐지 orch가 아니라 자유 질문으로 간다."""
    import server.navigation.manager as nav_manager_module

    async def _fake_answer(self, _device_id: str, question: str) -> dict:
        return {
            "guidance_text": f"답:{question}",
            "used_fallback_llm": False,
            "source": "question-llm",
        }

    monkeypatch.setattr(
        nav_manager_module,
        "nav_manager",
        _FakeNavManager(status="IDLE", detection_enabled=False),
    )
    monkeypatch.setattr(SttToLlmBridge, "_answer_free_question", _fake_answer)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("날씨 알려줘"), "test-device")

    assert response["source"] == "question-llm"
    assert "날씨" in response["guidance_text"]


@pytest.mark.asyncio
async def test_destination_wait_question_escapes_to_free_qa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """목적지 대기 중 질문형 발화는 POI 검색 대신 자유 질문으로 탈출한다."""
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION", detection_enabled=True)

    async def _fake_answer(self, _device_id: str, question: str) -> dict:
        return {
            "guidance_text": f"답:{question}",
            "used_fallback_llm": False,
            "source": "question-llm",
        }

    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)
    monkeypatch.setattr(SttToLlmBridge, "_answer_free_question", _fake_answer)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(
        _make_stt_result("지금 몇 시야"), "test-device"
    )

    assert response["source"] == "question-llm"
    assert fake_manager.status == "IDLE"


# [바이브 코딩 부분]
# - 아래 테스트는 부가 설명보다 실제 사용자 음성 흐름(켜기/목적지/끄기)에 맞춰 동작 검증을 제공한다.
# - 명령어 문구 자체보다 상태 전환과 source 값이 기대대로 나오는지에 집중한다.


@pytest.mark.asyncio
async def test_navigation_wakeup_command_sets_waiting_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="IDLE")
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    result = _make_stt_result("네비게이션 시작")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-wakeup"
    assert fake_manager.status == "WAITING_FOR_DESTINATION"


@pytest.mark.asyncio
async def test_navigation_shutdown_command_resets_status_and_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="NAVIGATING")
    fake_manager.last_route = [{"index": 1, "lat": 37.1, "lon": 127.1}]
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    result = _make_stt_result("네비게이션 꺼줘")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-shutdown"
    assert fake_manager.status == "IDLE"
    assert fake_manager.last_route == []


# [하드 코딩 부분 - 핵심]
# - 목적지 파싱 후 helper_search_poi/helper_fetch_route를 거쳐 waypoints를 구성하는 경로를 검증한다.
# - WAITING_FOR_DESTINATION 상태에서만 목적지 처리 분기가 타도록 고정한다.


@pytest.mark.asyncio
async def test_navigation_destination_setup_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    def _fake_search_poi(keyword: str) -> dict:
        _ = keyword
        return {"name": "서울역", "x": "126.9707", "y": "37.5547"}

    def _fake_fetch_route(_start: dict, _end: dict) -> dict:
        return {
            "features": [
                {
                    "geometry": {"type": "Point", "coordinates": [126.9710, 37.5550]},
                    "properties": {
                        "description": "직진",
                        "facilityType": "crosswalk",
                    },
                }
            ]
        }

    monkeypatch.setattr(nav_server_module, "helper_search_poi", _fake_search_poi)
    monkeypatch.setattr(nav_server_module, "helper_fetch_route", _fake_fetch_route)

    bridge = SttToLlmBridge()
    result = _make_stt_result("서울역으로 설정")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-success"
    assert fake_manager.status == "NAVIGATING"
    assert len(fake_manager.last_route) == 1
    assert fake_manager.last_route[0]["description"] == "직진"


@pytest.mark.asyncio
async def test_navigation_destination_setup_fail_when_poi_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.navigation.manager as nav_manager_module
    import server.navigation.server as nav_server_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    def _fake_search_poi(_keyword: str):
        return None

    def _fake_fetch_route(_start: dict, _end: dict):
        return None

    monkeypatch.setattr(nav_server_module, "helper_search_poi", _fake_search_poi)
    monkeypatch.setattr(nav_server_module, "helper_fetch_route", _fake_fetch_route)

    bridge = SttToLlmBridge()
    result = _make_stt_result("없는목적지로 설정")
    response = await bridge.invoke_existing_llm(result, "test-device")

    assert response["source"] == "navigation-setup-fail"
    assert fake_manager.status == "WAITING_FOR_DESTINATION"


@pytest.mark.asyncio
async def test_recent_guidance_echo_is_ignored() -> None:
    bridge = SttToLlmBridge()
    bridge._recent_guidance.clear()
    bridge._record_guidance("echo-device", "길찾아줘 또는 물어볼게 중 하나로 다시 말씀해 주세요.")

    response = await bridge.invoke_existing_llm(
        _make_stt_result("길찾아줘 또는 물어볼게 중 하나로 다시 말씀해 주세요"),
        "echo-device",
    )

    assert response["source"] == "stt-echo-detected"
    assert response["guidance_text"] == ""
    bridge._recent_guidance.clear()


@pytest.mark.asyncio
async def test_navigation_intent_wins_over_repeated_wake(monkeypatch: pytest.MonkeyPatch) -> None:
    import server.navigation.manager as nav_manager_module

    fake_manager = _FakeNavManager(status="IDLE")
    fake_manager.awaiting_intent = True
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(
        _make_stt_result("길댕아 길찾아줘"),
        "test-device",
    )

    assert response["source"] == "navigation-setup-wakeup"
    assert fake_manager.status == "WAITING_FOR_DESTINATION"
    assert fake_manager.awaiting_intent is False
