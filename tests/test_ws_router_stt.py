import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import base64

import pytest

import server.api.ws_router as ws_router_module
from server.api.ws_router import _handle_stt_audio
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

    persisted: list[dict] = []

    async def _fake_persist(**kwargs):
        persisted.append(kwargs)

    monkeypatch.setattr(ws_router_module, "persist_detection_guidance_log", _fake_persist)

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
    assert persisted[0]["detections"] == [{"source": "stt", "text_length": len(fake_result.text)}]


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
