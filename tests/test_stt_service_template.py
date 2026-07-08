import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path

import pytest

import server.stt.stt_service as stt_service_module
from server.stt.stt_schema import SttTranscribeResult
from server.stt.stt_service import SttService

# ============================================================
# 테스트 파일 역할
# ============================================================
# [바이브 코딩 부분]
# - 운영 진입점이 _transcribe_production으로 위임되는지 검증.
# - get_model 캐시 재사용과 _transcribe_production 결과 조립을 검증.
#
# [하드 코딩 부분]
# - 운영 Whisper 예외/실패 경로 테스트는 정책 요구에 맞춰 추가한다.
# - 최소 추가 권장 시나리오:
#   1) 모델 로드 성공 시 segments/text 정합성 검증
#   2) 잘못된 model_name 입력 시 KeyError 또는 ValueError 검증
#   3) wav 파일 없음(FileNotFoundError) 검증
#   4) transcribe 예외 발생 시 RuntimeError 래핑 검증


def test_has_stt_input_true_false() -> None:
    assert SttService.has_stt_input("안녕하세요") is True
    assert SttService.has_stt_input("   ") is False


def test_transcribe_file_delegates_to_production(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_production(cls, saved_path: Path, model_name: str) -> SttTranscribeResult:
        return SttTranscribeResult(
            model_name=model_name,
            text="테스트",
            language="ko",
            duration=0.1,
            segments=[],
            has_input=True,
            saved_file=saved_path.name,
        )

    monkeypatch.setattr(SttService, "_transcribe_production", classmethod(_fake_production))

    result = SttService.transcribe_file(saved_path=Path("dummy.wav"), model_name="manual-model")

    assert result.saved_file == "dummy.wav"
    assert result.has_input is True
    assert result.text == "테스트"


def test_get_model_builds_and_reuses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    created_calls: list[tuple[str, str, str]] = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, device: str, compute_type: str) -> None:
            created_calls.append((model_name, device, compute_type))

    monkeypatch.setattr(stt_service_module, "WhisperModel", FakeWhisperModel)
    SttService._model_cache.clear()

    model_a = SttService.get_model("faster-whisper-medium")
    model_b = SttService.get_model("faster-whisper-medium")

    assert model_a is model_b
    assert created_calls == [("medium", "cpu", "int8")]


def test_transcribe_production_returns_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wav_path = tmp_path / "sample.wav"
    wav_path.write_bytes(b"fake-wav")

    class FakeSegment:
        def __init__(self, start: float, end: float, text: str) -> None:
            self.start = start
            self.end = end
            self.text = text

    class FakeInfo:
        language = "ko"
        duration = 1.5

    class FakeModel:
        def transcribe(self, path: str, language: str, beam_size: int, vad_filter: bool):
            assert path == str(wav_path)
            assert language == "ko"
            assert beam_size == 3
            assert vad_filter is False
            return [FakeSegment(0.0, 0.5, "안녕 "), FakeSegment(0.5, 1.0, " 하세요")], FakeInfo()

    monkeypatch.setattr(SttService, "get_model", classmethod(lambda cls, model_name: FakeModel()))

    result = SttService._transcribe_production(
        saved_path=wav_path,
        model_name="faster-whisper-small",
    )

    assert result.model_name == "faster-whisper-small"
    assert result.text == "안녕 하세요"
    assert result.language == "ko"
    assert result.duration == 1.5
    assert result.has_input is True
    assert result.saved_file == "sample.wav"
    assert len(result.segments) == 2
