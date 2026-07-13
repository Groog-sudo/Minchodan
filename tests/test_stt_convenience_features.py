# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from types import SimpleNamespace

import pytest

from server.stt.contact_store import ContactStore
from server.stt.stt_schema import SegmentOut, SttTranscribeResult
from server.stt.stt_to_llm_bridge import SttToLlmBridge

# ============================================================
# 테스트 파일 역할
# ============================================================
# [바이브 코딩 부분]
# - 2026-07-12 추가 음성 편의기능 3종(긴급전화/연락처 저장/이름으로 전화걸기)의
#   인텐트 분기와 dial_action 응답 계약을 검증한다.
# - test_stt_to_llm_bridge_template.py와 동일한 픽스처 패턴(_make_stt_result,
#   _FakeNavManager)을 재사용해 기존 컨벤션을 따른다.


def _make_stt_result(text: str) -> SttTranscribeResult:
    return SttTranscribeResult(
        model_name="faster-whisper-base",
        text=text,
        language="ko",
        duration=1.0,
        segments=[SegmentOut(start=0.0, end=1.0, text=text)],
        has_input=True,
        saved_file=Path("dummy.wav").name,
    )


class _FakeNavManager:
    """긴급전화가 nav 상태와 무관하게 최우선 처리되는지 확인하는 용도로만 사용."""

    def __init__(self, status: str = "IDLE"):
        self.status = status
        self.session = SimpleNamespace(lat=None, lon=None)
        self.awaiting_question = False
        self.awaiting_intent = False

    def get_status(self, device_id: str) -> str:
        _ = device_id
        return self.status

    def set_status(self, device_id: str, status: str) -> None:
        _ = device_id
        self.status = status

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
        return False


@pytest.fixture(autouse=True)
def _clear_contact_store():
    """ContactStore는 ClassVar dict라 테스트 간 상태가 새면 안 된다."""
    ContactStore._contacts.clear()
    yield
    ContactStore._contacts.clear()


# ============================================================
# 연락처 저장 / 이름으로 전화걸기 (TH HARDCODE - 프로세스 메모리 저장소)
# ============================================================


@pytest.mark.asyncio
async def test_contact_save_then_call_success() -> None:
    bridge = SttToLlmBridge()

    save_response = await bridge.invoke_existing_llm(
        _make_stt_result("엄마 번호는 01012345678 저장해줘"), "test-device"
    )
    assert save_response["source"] == "contact-save-success"
    assert "엄마" in save_response["guidance_text"]

    call_response = await bridge.invoke_existing_llm(
        _make_stt_result("엄마한테 전화 걸어줘"), "test-device"
    )
    assert call_response["source"] == "contact-call-success"
    assert call_response["dial_action"] == {
        "contact_name": "엄마",
        "phone_number": "010-1234-5678",
    }


@pytest.mark.asyncio
async def test_contact_save_accepts_korean_spoken_digits() -> None:
    # 2026-07-13 실기기 실측: Whisper가 전화번호를 아라비아 숫자 대신 한글 숫자로
    # 전사하는 경우(예: "공일공일이삼사오육칠팔") 저장이 안 되던 문제의 회귀 테스트.
    bridge = SttToLlmBridge()

    save_response = await bridge.invoke_existing_llm(
        _make_stt_result("아빠 번호는 공일공일이삼사오육칠팔 저장해줘"), "test-device"
    )
    assert save_response["source"] == "contact-save-success"

    call_response = await bridge.invoke_existing_llm(
        _make_stt_result("아빠한테 전화 걸어줘"), "test-device"
    )
    assert call_response["dial_action"] == {
        "contact_name": "아빠",
        "phone_number": "010-1234-5678",
    }


@pytest.mark.asyncio
async def test_contact_call_without_saved_number_uses_device_lookup() -> None:
    # 서버 RAM에 번호가 없어도 단말이 주소록에서 찾도록 dial_action + device_lookup을 보낸다.
    bridge = SttToLlmBridge()

    response = await bridge.invoke_existing_llm(
        _make_stt_result("아빠한테 전화 걸어줘"), "test-device"
    )
    assert response["source"] == "contact-call-device-lookup"
    assert response["dial_action"] == {
        "contact_name": "아빠",
        "phone_number": "",
        "device_lookup": True,
    }


@pytest.mark.asyncio
async def test_contact_save_without_phone_number_is_not_treated_as_save() -> None:
    # "저장" 키워드만 있고 전화번호 패턴이 없으면 저장 트리거로 인정하지 않는다
    # (오탐 방지 - is_contact_save_trigger 계산 참조). 일반 대화(오케스트레이션)로 흘러간다.
    bridge = SttToLlmBridge()

    response = await bridge.invoke_existing_llm(
        _make_stt_result("이거 저장해줘"), "test-device"
    )
    assert response["source"] != "contact-save-success"


# ============================================================
# 긴급전화 (실제 DB 연동 - guardian_phone 조회 / 미등록 시 119 폴백)
# ============================================================


@pytest.mark.asyncio
async def test_emergency_call_uses_guardian_phone_from_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.db.repositories as repositories_module
    import server.services.device_registry_service as device_registry_module

    monkeypatch.setattr(
        device_registry_module, "get_cached_device_ids", lambda device_id: (1, 1)
    )

    async def _fake_get_by_id(self, user_id: int):
        _ = self, user_id
        return SimpleNamespace(guardian_phone="010-9999-8888")

    monkeypatch.setattr(repositories_module.UserRepository, "get_by_id", _fake_get_by_id)

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("긴급전화"), "test-device")

    assert response["source"] == "emergency-call-guardian"
    assert response["dial_action"] == {
        "contact_name": "보호자",
        "phone_number": "010-9999-8888",
    }


@pytest.mark.asyncio
async def test_emergency_call_falls_back_to_119_when_guardian_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import server.services.device_registry_service as device_registry_module

    # 캐시에 없는(등록 안 된) device_id -> (None, None)
    monkeypatch.setattr(
        device_registry_module, "get_cached_device_ids", lambda device_id: (None, None)
    )

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(
        _make_stt_result("보호자한테 전화해줘"), "test-device"
    )

    assert response["source"] == "emergency-call-fallback"
    assert response["dial_action"] == {
        "contact_name": "119 안전신고센터",
        "phone_number": "119",
    }


@pytest.mark.asyncio
async def test_emergency_call_overrides_navigation_waiting_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """목적지 대기 상태 중에도 긴급전화가 최우선 처리되는지 확인한다."""
    import server.navigation.manager as nav_manager_module
    import server.services.device_registry_service as device_registry_module

    fake_manager = _FakeNavManager(status="WAITING_FOR_DESTINATION")
    monkeypatch.setattr(nav_manager_module, "nav_manager", fake_manager)
    monkeypatch.setattr(
        device_registry_module, "get_cached_device_ids", lambda device_id: (None, None)
    )

    bridge = SttToLlmBridge()
    response = await bridge.invoke_existing_llm(_make_stt_result("긴급전화"), "test-device")

    assert response["source"] == "emergency-call-fallback"
    # 긴급전화 처리는 nav 상태를 바꾸지 않는다(목적지 대기 상태 그대로 유지되어야 함).
    assert fake_manager.status == "WAITING_FOR_DESTINATION"
