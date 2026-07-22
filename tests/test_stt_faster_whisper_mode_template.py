import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from typing import Any, ClassVar

import pytest

from server.stt.stt_schema import SegmentOut, SttTranscribeResult

try:
    from faster_whisper import WhisperModel

    WhisperModelType = WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except Exception:
    WhisperModel = None  # type: ignore[assignment]
    WhisperModelType = Any
    FASTER_WHISPER_AVAILABLE = False


# ============================================================
# 테스트 모드 전용 STT 템플릿 (tests 전용)
# ============================================================
# [바이브 코딩 부분]
# - tests 계층에서만 faster-whisper import/검증을 수행한다.
# - server/stt 정식 백엔드에는 테스트 모드 로직을 넣지 않는다.
#
# [하드 코딩 부분]
# - 모델 선택 정책, Whisper 인스턴스 생성, 실제 transcribe 호출은 직접 작성.
# - 현재 파일은 위 하드코딩 항목을 구현한 기준 예시다.


class FasterWhisperTestModeHarness:
    """
    tests 전용 하네스.
    운영 코드와 분리된 테스트 모드 실험을 위해 사용한다.
    """

    # [하드 코딩 부분] 직접 작성 영역
    # 작성 조건:
    # 1) key는 테스트 입력 모델명, value는 faster-whisper 내부 모델명으로 작성한다.
    # 2) 최소 1개 이상 매핑한다.
    # 3) key는 "faster-whisper-<size>" 형식을 권장한다.
    # 4) value는 tiny/base/small/medium/large-v* 중 실제 지원값만 사용한다.
    # 5) key/value 공백, 오타를 허용하지 않는다.
    MODEL_NAME_MAP: ClassVar[dict[str, str]] = {
        # "faster-whisper-base": "base",
        "faster-whisper-base": "base",
        "faster-whisper-tiny": "tiny",
        "faster-whisper-small": "small",
        "faster-whisper-medium": "medium",
    }

    # [하드 코딩 부분] 직접 작성 영역
    # 작성 조건:
    # 1) MODEL_NAME_MAP의 key 중 하나를 사용한다.
    # 2) 미매핑 입력은 이 기본값으로 폴백한다.
    # 3) 공백 금지. 문자열 비교는 대소문자 완전일치로 처리한다.
    DEFAULT_MODEL_NAME = "faster-whisper-base"

    # [하드 코딩 부분] 직접 작성 영역
    # 작성 조건:
    # 1) 테스트 추론 언어를 명시한다 (예: "ko").
    # 2) beam_size는 1 이상의 정수로 작성한다.
    # 3) vad_filter는 bool로 작성한다.
    # 4) beam_size는 권장 1~5 범위에서 시작한다.
    # 5) vad_filter=True면 무음구간 제거에 유리하다.
    TRANSCRIBE_LANGUAGE = "ko"
    TRANSCRIBE_BEAM_SIZE = 1
    TRANSCRIBE_VAD_FILTER = True

    # [하드 코딩 부분] 직접 작성 영역
    # 작성 조건:
    # 1) 테스트 장비가 CPU면 "cpu", GPU면 "cuda"로 명시.
    # 2) compute_type은 장비에 맞게 선택 (cpu: int8 권장, gpu: float16 권장).
    WHISPER_DEVICE = "cpu"
    WHISPER_COMPUTE_TYPE = "int8"

    # [바이브 코딩 부분] 선택 캐시
    _model_cache: ClassVar[dict[str, Any]] = {}

    @classmethod
    def has_input(cls, text: str) -> bool:
        # [바이브 코딩 부분]
        return bool((text or "").strip())

    @classmethod
    def build_fake_result(cls, text: str, model_name: str = "test-model") -> SttTranscribeResult:
        # [바이브 코딩 부분]
        clean_text = (text or "").strip()
        has_input = cls.has_input(clean_text)
        segments = [SegmentOut(start=0.0, end=0.0, text=clean_text)] if has_input else []

        return SttTranscribeResult(
            model_name=model_name,
            text=clean_text,
            language=cls.TRANSCRIBE_LANGUAGE or None,
            duration=0.0,
            segments=segments,
            has_input=has_input,
            saved_file=Path("dummy.wav").name,
        )

    @classmethod
    def build_model(cls, request_model_name: str) -> Any:
        """
        [하드 코딩 부분] 직접 작성 영역 (코드 자동 작성 금지)

        작성 조건:
          1) request_model_name을 strip()으로 정규화한다.
          2) 미매핑이면 DEFAULT_MODEL_NAME으로 폴백한다.
          3) 내부 모델명은 MODEL_NAME_MAP[resolved_request_name]로 조회한다.
          4) _model_cache를 사용한다면 key는 내부 모델명을 사용한다.
          5) WhisperModel 생성 시 아래 인자를 반드시 넣는다.
              - model_size_or_path: 내부 모델명
              - device: WHISPER_DEVICE
              - compute_type: WHISPER_COMPUTE_TYPE
          6) 정책 누락/오류는 ValueError 또는 KeyError를 명확히 발생시킨다.
          7) 반환 타입은 WhisperModel 단일 인스턴스로 고정한다.
        """
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError("faster-whisper import가 준비되지 않았습니다.")

        resolved_request_name = (request_model_name or "").strip() or cls.DEFAULT_MODEL_NAME
        internal_model_name = (
            cls.MODEL_NAME_MAP.get(resolved_request_name)
            or cls.MODEL_NAME_MAP[cls.DEFAULT_MODEL_NAME]
        )

        if internal_model_name not in cls._model_cache:
            model = WhisperModelType(
                model_size_or_path=internal_model_name,
                device=cls.WHISPER_DEVICE,
                compute_type=cls.WHISPER_COMPUTE_TYPE,
            )
            cls._model_cache[internal_model_name] = model

        return cls._model_cache[internal_model_name]

    @classmethod
    def transcribe_with_model(cls, wav_path: Path, request_model_name: str) -> SttTranscribeResult:
        """
        [하드 코딩 부분] 직접 작성 영역 (코드 자동 작성 금지)

        작성 조건:
        1) wav_path 존재 여부를 먼저 확인하고 없으면 FileNotFoundError를 발생시킨다.
        2) build_model(...)로 WhisperModel을 획득한다.
        3) model.transcribe(...)에 language/beam_size/vad_filter를 반영한다.
        4) segments_iter를 list로 확정한다.
        5) full_text는 세그먼트 text를 strip 후 공백으로 join 해서 만든다.
        6) has_input은 cls.has_input(full_text)로 계산한다.
        7) SttTranscribeResult 필드를 누락 없이 채워 반환한다.
        8) 예외는 RuntimeError("faster-whisper test transcribe failed: ...")로 래핑한다.
        """
        if not wav_path.exists():
            raise FileNotFoundError(f"wav 파일이 존재하지 않습니다: {wav_path}")

        try:
            model = cls.build_model(request_model_name)
            segments_iter, info = model.transcribe(
                str(wav_path),
                language=cls.TRANSCRIBE_LANGUAGE,
                beam_size=cls.TRANSCRIBE_BEAM_SIZE,
                vad_filter=cls.TRANSCRIBE_VAD_FILTER,
            )
            segments = list(segments_iter)
            full_text = " ".join(segment.text.strip() for segment in segments).strip()
            has_input = cls.has_input(full_text)
            segment_outputs = [
                SegmentOut(start=segment.start, end=segment.end, text=segment.text.strip())
                for segment in segments
            ]

            return SttTranscribeResult(
                model_name=(request_model_name or "").strip() or cls.DEFAULT_MODEL_NAME,
                text=full_text,
                language=getattr(info, "language", None),
                duration=getattr(info, "duration", None),
                segments=segment_outputs,
                has_input=has_input,
                saved_file=wav_path.name,
            )
        except FileNotFoundError:
            raise
        except Exception as exc:
            raise RuntimeError(f"faster-whisper test transcribe failed: {exc}") from exc


def test_faster_whisper_import_available_or_skip() -> None:
    if not FASTER_WHISPER_AVAILABLE:
        pytest.skip("faster-whisper 미설치/미인식 환경이므로 테스트를 건너뜁니다.")

    assert WhisperModel is not None


def test_fake_result_shape_for_test_mode() -> None:
    result = FasterWhisperTestModeHarness.build_fake_result("좌측으로 이동하세요")
    assert result.has_input is True
    assert result.saved_file == "dummy.wav"
    assert len(result.segments) == 1


def test_build_model_creates_and_reuses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    created_calls: list[tuple[str, str, str]] = []

    class FakeWhisperModel:
        def __init__(self, model_size_or_path: str, device: str, compute_type: str) -> None:
            created_calls.append((model_size_or_path, device, compute_type))

    monkeypatch.setitem(globals(), "FASTER_WHISPER_AVAILABLE", True)
    monkeypatch.setitem(globals(), "WhisperModelType", FakeWhisperModel)
    FasterWhisperTestModeHarness._model_cache.clear()

    model_a = FasterWhisperTestModeHarness.build_model("faster-whisper-base")
    model_b = FasterWhisperTestModeHarness.build_model("unknown-model")

    assert model_a is model_b
    assert created_calls == [("base", "cpu", "int8")]


def test_transcribe_with_model_returns_stt_result(
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
        duration = 1.25

    class FakeModel:
        def transcribe(self, path: str, language: str, beam_size: int, vad_filter: bool):
            assert path == str(wav_path)
            assert language == FasterWhisperTestModeHarness.TRANSCRIBE_LANGUAGE
            assert beam_size == FasterWhisperTestModeHarness.TRANSCRIBE_BEAM_SIZE
            assert vad_filter is FasterWhisperTestModeHarness.TRANSCRIBE_VAD_FILTER
            return [FakeSegment(0.0, 0.5, "안녕 "), FakeSegment(0.5, 1.0, " 하세요")], FakeInfo()

    monkeypatch.setattr(
        FasterWhisperTestModeHarness,
        "build_model",
        classmethod(lambda cls, request_model_name: FakeModel()),
    )

    result = FasterWhisperTestModeHarness.transcribe_with_model(
        wav_path=wav_path,
        request_model_name="faster-whisper-base",
    )

    assert result.model_name == "faster-whisper-base"
    assert result.text == "안녕 하세요"
    assert result.language == "ko"
    assert result.duration == 1.25
    assert result.has_input is True
    assert result.saved_file == "sample.wav"
    assert len(result.segments) == 2


def test_transcribe_with_model_raises_when_file_missing() -> None:
    with pytest.raises(FileNotFoundError):
        FasterWhisperTestModeHarness.transcribe_with_model(
            wav_path=Path("missing.wav"),
            request_model_name="faster-whisper-base",
        )
