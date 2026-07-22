import os
import sys

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.stt.stt_to_llm_bridge import SttToLlmBridge


class _FakeNavManager:
    def __init__(
        self,
        *,
        status: str = "IDLE",
        awaiting_question: bool = False,
        awaiting_intent: bool = False,
        detection_enabled: bool = True,
    ):
        self._status = status
        self._awaiting_question = awaiting_question
        self._awaiting_intent = awaiting_intent
        self._detection_enabled = detection_enabled

    def get_status(self, device_id: str) -> str:
        return self._status

    def is_awaiting_question(self, device_id: str) -> bool:
        return self._awaiting_question

    def is_awaiting_intent(self, device_id: str) -> bool:
        return self._awaiting_intent

    def is_detection_enabled(self, device_id: str) -> bool:
        return self._detection_enabled


@pytest.fixture
def bridge() -> SttToLlmBridge:
    return SttToLlmBridge()


def test_should_play_wait_pre_stt_destination(bridge, monkeypatch):
    fake_nav = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    monkeypatch.setattr("server.navigation.manager.nav_manager", fake_nav)
    assert bridge.should_play_stt_wait_notice("dev-001") is True


def test_should_play_wait_post_stt_question_answer(bridge, monkeypatch):
    fake_nav = _FakeNavManager(awaiting_question=True)
    monkeypatch.setattr("server.navigation.manager.nav_manager", fake_nav)
    assert bridge.should_play_stt_wait_notice("dev-001", "가까운 지하철역이 어디야") is True


def test_should_not_play_wait_for_wakeup(bridge, monkeypatch):
    fake_nav = _FakeNavManager()
    monkeypatch.setattr("server.navigation.manager.nav_manager", fake_nav)
    assert bridge.should_play_stt_wait_notice("dev-001", "네비게이션 켜줘") is False


def test_should_not_play_wait_for_question_mode_wakeup(bridge, monkeypatch):
    fake_nav = _FakeNavManager()
    monkeypatch.setattr("server.navigation.manager.nav_manager", fake_nav)
    assert bridge.should_play_stt_wait_notice("dev-001", "질문할게") is False


def test_should_not_play_wait_for_intent_mode(bridge, monkeypatch):
    fake_nav = _FakeNavManager(awaiting_intent=True)
    monkeypatch.setattr("server.navigation.manager.nav_manager", fake_nav)
    assert bridge.should_play_stt_wait_notice("dev-001", "길찾아줘") is False
