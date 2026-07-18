import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import base64

import pytest

import server.api.ws_router as ws_router_module
from server.api.session_manager import manager
from server.api.ws_router import _estimate_stt_hold_seconds, _handle_stt_audio
from server.services.remote_storage_client import RemoteStoreResult
from server.stt.stt_schema import SttTranscribeResult

# ============================================================
# 테스트 파일 역할
# ============================================================
# server/api/ws_router.py의 stt_audio 메시지 핸들러(_handle_stt_audio)를 검증한다.
# 2026-07-09 이전에는 SttService/SttToLlmBridge가 완성돼 있어도 어떤 라우터에서도
# 호출되지 않아 STT 요청을 받을 경로 자체가 없었다(회귀 방지 목적).
# faster-whisper 실제 모델 로드/추론과 Piper 실제 합성은 무겁고 이 테스트의 검증
# 대상이 아니므로 monkeypatch로 대체한다.


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.sent_bytes: list[bytes] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def send_bytes(self, payload: bytes) -> None:
        self.sent_bytes.append(payload)


def _fake_wav_b64() -> str:
    # jh 병합(2026-07-13)으로 추가된 MIN_STT_AUDIO_BYTES(4096) 가드를 통과시키기 위해
    # 원래의 16바이트 더미보다 넉넉하게 패딩한다(이 테스트의 검증 대상은 길이 가드가
    # 아니라 그 이후의 전사/가이드 생성 흐름이므로 최소 길이만 만족시키면 된다).
    return base64.b64encode(b"RIFF....WAVEfmt " + b"\x00" * 4096).decode("utf-8")


@pytest.mark.asyncio
async def test_stt_audio_slow_path_sends_wait_notice_before_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_result = SttTranscribeResult(
        model_name="faster-whisper-medium",
        text="서울역으로 가줘",
        language="ko",
        duration=1.2,
        segments=[],
        has_input=True,
        saved_file="dummy.wav",
    )
    monkeypatch.setattr(
        ws_router_module.SttService,
        "transcribe_file",
        classmethod(lambda cls, saved_path, model_name: fake_result),
    )

    async def _fake_invoke(self, stt_result, device_id):
        return {
            "guidance_text": "서울역까지 보행 경로 안내를 시작합니다.",
            "used_fallback_llm": True,
            "source": "navigation-setup-success",
        }

    monkeypatch.setattr(ws_router_module.SttToLlmBridge, "invoke_existing_llm", _fake_invoke)

    synth_calls: list[str] = []

    async def _fake_synthesize(self, text, voice="ko", speed=0.9):
        synth_calls.append(text)
        return "ZmFrZS1hdWRpbw==", 900.0

    monkeypatch.setattr(
        ws_router_module.realtime_tts,
        "synthesize",
        _fake_synthesize.__get__(ws_router_module.realtime_tts),
    )

    class _FakeNav:
        def get_status(self, device_id: str) -> str:
            return "WAITING_FOR_DESTINATION"

        def is_awaiting_question(self, device_id: str) -> bool:
            return False

        def is_awaiting_intent(self, device_id: str) -> bool:
            return False

        def is_detection_enabled(self, device_id: str) -> bool:
            return True

    monkeypatch.setattr("server.navigation.manager.nav_manager", _FakeNav())

    async def _fake_persist(**_kwargs):
        return None

    monkeypatch.setattr(ws_router_module, "persist_detection_guidance_log", _fake_persist)

    ws = _FakeWebSocket()
    await _handle_stt_audio(ws, "dev-001", {"type": "stt_audio", "audio_b64": _fake_wav_b64()})

    assert len(ws.sent) == 2
    assert ws.sent[0]["source"] == "stt-wait-notice"
    assert ws.sent[0]["guidance_text"] == "잠시만 기다려주세요!"
    assert ws.sent[1]["source"] == "navigation-setup-success"
    assert "잠시만 기다려주세요!" in synth_calls
    assert len(ws.sent_bytes) == 2


@pytest.mark.asyncio
async def test_stt_audio_success_sends_guide_with_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_result = SttTranscribeResult(
        model_name="faster-whisper-medium",
        text="네비게이션 켜줘",
        language="ko",
        duration=1.2,
        segments=[],
        has_input=True,
        saved_file="dummy.wav",
    )
    monkeypatch.setattr(
        ws_router_module.SttService,
        "transcribe_file",
        classmethod(lambda cls, saved_path, model_name: fake_result),
    )

    async def _fake_invoke(self, stt_result, device_id):
        assert device_id == "dev-001"
        return {
            "guidance_text": "네비게이션 기능을 시작합니다. 목적지를 말씀해 주세요.",
            "used_fallback_llm": True,
            "source": "navigation-setup-wakeup",
        }

    monkeypatch.setattr(ws_router_module.SttToLlmBridge, "invoke_existing_llm", _fake_invoke)

    async def _fake_synthesize(self, text, voice="ko", speed=0.9):
        assert text == "네비게이션 기능을 시작합니다. 목적지를 말씀해 주세요."
        return "ZmFrZS1hdWRpbw==", 900.0

    monkeypatch.setattr(
        ws_router_module.realtime_tts,
        "synthesize",
        _fake_synthesize.__get__(ws_router_module.realtime_tts),
    )

    async def _fake_upload_stt_audio(event_id, audio_bytes, content_type, format_):
        assert event_id.startswith("stt-dev-001-")
        assert audio_bytes.startswith(b"RIFF")
        assert content_type == "audio/wav"
        assert format_ == "wav"
        return RemoteStoreResult(
            object_key=f"20260716/{event_id}.wav",
            status="available",
            format="wav",
            size_bytes=len(audio_bytes),
            sha256="a" * 64,
        )

    monkeypatch.setattr(ws_router_module, "upload_stt_audio", _fake_upload_stt_audio)

    persisted: list[dict] = []

    async def _fake_persist(**kwargs):
        persisted.append(kwargs)

    monkeypatch.setattr(ws_router_module, "persist_detection_guidance_log", _fake_persist)

    class _FakeNavIdle:
        def get_status(self, device_id: str) -> str:
            return "IDLE"

        def is_awaiting_question(self, device_id: str) -> bool:
            return False

        def is_awaiting_intent(self, device_id: str) -> bool:
            return False

        def is_detection_enabled(self, device_id: str) -> bool:
            return True

    monkeypatch.setattr("server.navigation.manager.nav_manager", _FakeNavIdle())

    ws = _FakeWebSocket()
    await _handle_stt_audio(ws, "dev-001", {"type": "stt_audio", "audio_b64": _fake_wav_b64()})

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "guide"
    assert payload["guidance_text"] == "네비게이션 기능을 시작합니다. 목적지를 말씀해 주세요."
    assert payload["transport"] == "binary"
    assert payload["duration_ms"] == 900.0
    assert payload["source"] == "navigation-setup-wakeup"
    assert ws.sent_bytes == [b"fake-audio"]
    assert persisted[0]["detections"] == [
        {"source": "stt", "text_length": len(fake_result.text), "stt_transcript": fake_result.text}
    ]
    assert persisted[0]["event_source"] == "stt"
    assert persisted[0]["stt_transcript_text"] == fake_result.text
    assert persisted[0]["stt_audio_path"].endswith(".wav")
    assert persisted[0]["stt_audio_storage_status"] == "available"
    assert persisted[0]["stt_audio_format"] == "wav"
    assert persisted[0]["stt_audio_duration_ms"] == 1200
    assert persisted[0]["stt_audio_sha256"] == "a" * 64


@pytest.mark.asyncio
async def test_stt_audio_success_extends_stt_active_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    """T3-S (2026-07-18): 응답 전송 직후 즉시 해제하지 않고, 예상 재생시간까지
    manager.is_stt_active(device_id)가 True로 유지되는지 검증한다(재생 구간의
    인지 가이드 발행 억제 - 회귀 방지: 이전에는 전송 직후 즉시 해제되어 재생
    구간 동안 억제가 풀려 있었다)."""
    fake_result = SttTranscribeResult(
        model_name="faster-whisper-medium",
        text="네비게이션 켜줘",
        language="ko",
        duration=1.2,
        segments=[],
        has_input=True,
        saved_file="dummy.wav",
    )
    monkeypatch.setattr(
        ws_router_module.SttService,
        "transcribe_file",
        classmethod(lambda cls, saved_path, model_name: fake_result),
    )

    async def _fake_invoke(self, stt_result, device_id):
        return {
            "guidance_text": "네비게이션 기능을 시작합니다. 목적지를 말씀해 주세요.",
            "used_fallback_llm": True,
            "source": "navigation-setup-wakeup",
        }

    monkeypatch.setattr(ws_router_module.SttToLlmBridge, "invoke_existing_llm", _fake_invoke)

    async def _fake_synthesize(self, text, voice="ko", speed=0.9):
        return "ZmFrZS1hdWRpbw==", 900.0

    monkeypatch.setattr(
        ws_router_module.realtime_tts,
        "synthesize",
        _fake_synthesize.__get__(ws_router_module.realtime_tts),
    )

    async def _fake_upload_stt_audio(event_id, audio_bytes, content_type, format_):
        return RemoteStoreResult(
            object_key=f"20260716/{event_id}.wav",
            status="available",
            format="wav",
            size_bytes=len(audio_bytes),
            sha256="a" * 64,
        )

    monkeypatch.setattr(ws_router_module, "upload_stt_audio", _fake_upload_stt_audio)

    async def _fake_persist(**_kwargs):
        return None

    monkeypatch.setattr(ws_router_module, "persist_detection_guidance_log", _fake_persist)

    class _FakeNavIdle:
        def get_status(self, device_id: str) -> str:
            return "IDLE"

        def is_awaiting_question(self, device_id: str) -> bool:
            return False

        def is_awaiting_intent(self, device_id: str) -> bool:
            return False

        def is_detection_enabled(self, device_id: str) -> bool:
            return True

    monkeypatch.setattr("server.navigation.manager.nav_manager", _FakeNavIdle())

    manager.set_stt_active("dev-ttl-test", False)
    try:
        ws = _FakeWebSocket()
        await _handle_stt_audio(
            ws, "dev-ttl-test", {"type": "stt_audio", "audio_b64": _fake_wav_b64()}
        )
        # 응답 전송은 이미 끝났지만(ws.sent 채워짐), 예상 재생시간(duration_ms=900ms)
        # + 마진(1200ms) 동안은 여전히 STT 활성 상태로 유지돼야 한다.
        assert len(ws.sent) == 1
        assert manager.is_stt_active("dev-ttl-test") is True
    finally:
        manager.set_stt_active("dev-ttl-test", False)


class TestEstimateSttHoldSeconds:
    """T3-S (2026-07-18): STT 응답 재생 예상 시간 추정 헬퍼 단위 테스트."""

    def test_empty_text_returns_zero(self) -> None:
        assert _estimate_stt_hold_seconds("") == 0.0

    def test_short_text_uses_minimum_with_margin(self) -> None:
        # 최소 텍스트 추정치(2000ms) + 마진(1200ms) = 3.2초. duration_ms=0이면 텍스트
        # 추정치가 그대로 쓰인다.
        assert _estimate_stt_hold_seconds("짧은 안내") == pytest.approx(3.2)

    def test_long_duration_ms_overrides_short_text_estimate(self) -> None:
        # 서버 duration_ms(5000ms)가 텍스트 추정치(2000ms)보다 크면 duration_ms 기준.
        assert _estimate_stt_hold_seconds("짧은 안내", duration_ms=5000.0) == pytest.approx(6.2)

    def test_long_text_uses_char_based_estimate(self) -> None:
        text = "가" * 20  # 20자 * 180ms = 3600ms > 최소 2000ms
        assert _estimate_stt_hold_seconds(text) == pytest.approx((3600.0 + 1200.0) / 1000.0)


@pytest.mark.asyncio
async def test_stt_audio_missing_audio_b64_sends_nothing() -> None:
    ws = _FakeWebSocket()
    await _handle_stt_audio(ws, "dev-001", {"type": "stt_audio"})
    assert ws.sent == []


@pytest.mark.asyncio
async def test_stt_audio_transcribe_failure_sends_fallback_guide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(cls, saved_path, model_name):
        raise RuntimeError("STT transcribe failed: file=dummy.wav, model=faster-whisper-medium")

    monkeypatch.setattr(ws_router_module.SttService, "transcribe_file", classmethod(_raise))

    ws = _FakeWebSocket()
    await _handle_stt_audio(ws, "dev-001", {"type": "stt_audio", "audio_b64": _fake_wav_b64()})

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "guide"
    assert payload["source"] == "stt-transcribe-error"
    assert payload["transport"] == "none"
    assert ws.sent_bytes == []


@pytest.mark.asyncio
async def test_stt_audio_dial_action_sends_after_guide(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_result = SttTranscribeResult(
        model_name="faster-whisper-medium",
        text="119로 연결해줘",
        language="ko",
        duration=1.0,
        segments=[],
        has_input=True,
        saved_file="dummy.wav",
    )
    monkeypatch.setattr(
        ws_router_module.SttService,
        "transcribe_file",
        classmethod(lambda cls, saved_path, model_name: fake_result),
    )

    monkeypatch.setattr(
        ws_router_module._stt_bridge,
        "should_play_stt_wait_notice",
        lambda device_id, normalized_text=None: False,
    )

    async def _fake_synthesize(*_args, **_kwargs):
        return "ZmFrZS1hdWRpbw==", 1200.0

    monkeypatch.setattr(ws_router_module.realtime_tts, "synthesize", _fake_synthesize)

    async def _fake_persist(**_kwargs):
        return None

    monkeypatch.setattr(ws_router_module, "persist_detection_guidance_log", _fake_persist)

    ws = _FakeWebSocket()
    await _handle_stt_audio(ws, "dev-001", {"type": "stt_audio", "audio_b64": _fake_wav_b64()})

    assert len(ws.sent) == 2
    assert ws.sent[0]["type"] == "guide"
    assert ws.sent[0]["source"] == "stt-dial-emergency"
    assert ws.sent[1]["type"] == "dial_action"
    assert ws.sent[1]["phone_number"] == "119"
    assert ws.sent[1]["delay_ms"] == 2000
