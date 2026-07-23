import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
from threading import Lock
from typing import Any, ClassVar

from .stt_config import (
    DEFAULT_REQUEST_MODEL,
    MODEL_NAME_MAP,
    TRANSCRIBE_BEAM_SIZE,
    TRANSCRIBE_HOTWORDS,
    TRANSCRIBE_LANGUAGE,
    TRANSCRIBE_VAD_FILTER,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
)
from .stt_runtime import validate_stt_runtime_config
from .stt_schema import SegmentOut, SttTranscribeResult

try:
    from faster_whisper import WhisperModel as _WhisperModel

    WhisperModel: Any = _WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except Exception:
    WhisperModel = None
    FASTER_WHISPER_AVAILABLE = False

# ============================================================
# STT 서비스 파일
# ============================================================
# [바이브 코딩 부분]
# - 세그먼트 스키마 변환, 입력 여부 판별, 요청 모델명 정규화.
#
# [하드 코딩 부분]
# - Whisper 정책(모델/디바이스/추론옵션), 운영 예외 정책, 성능 튜닝.


class SttService:
    """
    STT 실행 서비스 기본 골격.
    운영 경로는 transcribe_file()에서 실행된다.
    테스트 제어는 tests 계층에서만 수행한다.
    """

    _model_cache: ClassVar[dict[str, Any]] = {}
    _model_init_lock: ClassVar[Lock] = Lock()

    @staticmethod
    def _preload_ct2_cuda_libs() -> None:
        """CTranslate2(faster-whisper 백엔드)가 요구하는 CUDA 12 라이브러리를 사전 로드한다.

        2026-07-23 실측: ctranslate2 4.8.1은 libcublas.so.12를 dlopen하는데, 컨테이너에는
        PyTorch cu130 wheel의 CUDA 13 라이브러리만 있어 transcribe() 시점에
        "Library libcublas.so.12 is not found" RuntimeError가 발생했다(모델 초기화는 성공해
        CPU 폴백도 발동하지 않음). nvidia-cublas-cu12 wheel의 so를 RTLD_GLOBAL로 명시
        로드해 해결한다. LD_LIBRARY_PATH는 프로세스 기동 후 변경이 반영되지 않으므로
        ctypes 로드가 정본 경로다. 라이브러리 부재 시 조용히 스킵(CPU 폴백에 위임).
        """
        try:
            import contextlib
            import ctypes
            import site

            names = ("libcublas.so.12", "libcublasLt.so.12")
            for base in site.getsitepackages() + [site.getusersitepackages()]:
                lib_dir = Path(base) / "nvidia" / "cublas" / "lib"
                if not lib_dir.is_dir():
                    continue
                for name in names:
                    so_path = lib_dir / name
                    if so_path.is_file():
                        with contextlib.suppress(OSError):
                            ctypes.CDLL(str(so_path), mode=ctypes.RTLD_GLOBAL)
        except Exception:
            pass

    @classmethod
    def has_stt_input(cls, text: str) -> bool:
        """
        [바이브 코딩 부분]
        공백 제거 후 입력 존재 여부를 판단한다.
        """
        return bool((text or "").strip())

    @classmethod
    def resolve_requested_model(cls, model_name: str | None) -> str:
        """
        [바이브 코딩 부분]
        요청 모델명을 정규화하고, 미매핑 값은 기본 모델로 폴백한다.
        """
        requested = (model_name or "").strip()
        if requested in MODEL_NAME_MAP:
            return requested
        return DEFAULT_REQUEST_MODEL

    @staticmethod
    def build_segments_payload(segments: list[Any]) -> list[SegmentOut]:
        """
        [바이브 코딩 부분]
        Whisper 세그먼트를 API 응답 스키마로 변환한다.
        """
        return [
            SegmentOut(start=segment.start, end=segment.end, text=segment.text.strip())
            for segment in segments
        ]

    @classmethod
    def get_model(cls, model_name: str) -> WhisperModel:
        """
        [하드 코딩 부분]
        요청 모델명을 내부 모델명으로 매핑하고 WhisperModel 인스턴스를 캐시 기반으로 생성/재사용한다.
        설정 검증 실패는 ValueError, 모델명 미매핑은 KeyError, 초기화 실패는 RuntimeError로 구분한다.
        """
        validate_stt_runtime_config()

        request_model_name = (model_name or "").strip() or DEFAULT_REQUEST_MODEL
        if request_model_name not in MODEL_NAME_MAP:
            raise KeyError(f"모델명 '{request_model_name}'이 MODEL_NAME_MAP에 없습니다.")

        internal_model_name = MODEL_NAME_MAP[request_model_name]
        cache_key = internal_model_name

        if cache_key in cls._model_cache:
            return cls._model_cache[cache_key]

        with cls._model_init_lock:
            if cache_key in cls._model_cache:
                return cls._model_cache[cache_key]

            device = WHISPER_DEVICE
            if device != "cpu":
                cls._preload_ct2_cuda_libs()
            candidates: list[tuple[str, str]] = [(device, WHISPER_COMPUTE_TYPE)]
            if device == "cpu":
                candidates.extend([("cpu", "int8_float32"), ("cpu", "float32")])
            else:
                # 2026-07-23: CUDA 초기화 실패(드라이버/라이브러리 부재) 시 CPU 폴백.
                # GPU 미탑재 환경에서도 STT가 죽지 않도록 방어한다.
                candidates.extend([("cpu", "int8"), ("cpu", "int8_float32"), ("cpu", "float32")])

            last_exc: Exception | None = None
            for candidate_device, compute_type in dict.fromkeys(candidates):
                try:
                    model = WhisperModel(
                        internal_model_name,
                        device=candidate_device,
                        compute_type=compute_type,
                    )
                    break
                except Exception as exc:
                    last_exc = exc
            else:
                raise RuntimeError(
                    f"WhisperModel 초기화 중 예외 발생: model={internal_model_name}, "
                    f"candidates={candidates}"
                ) from last_exc

            cls._model_cache[cache_key] = model
            return model

    @classmethod
    def transcribe_file(
        cls, saved_path: Path, model_name: str | None = None
    ) -> SttTranscribeResult:
        """
        [바이브 코딩 부분]
        운영 STT 실행 진입점.
        server/stt는 테스트 모드를 포함하지 않으며, 테스트 제어는 tests 계층에서 수행한다.
        """
        resolved_model_name = cls.resolve_requested_model(model_name)

        # 운영 모드: 핵심 STT 구현은 하드코딩 파트에서 직접 작성
        return cls._transcribe_production(saved_path=saved_path, model_name=resolved_model_name)

    @classmethod
    def _transcribe_production(cls, saved_path: Path, model_name: str) -> SttTranscribeResult:
        """
        [하드 코딩 부분]
        운영 전사 경로를 수행한다.
        Whisper transcribe 결과를 SttTranscribeResult로 조립하고, 실패 시 파일명/모델명을 포함한 RuntimeError로 래핑한다.
        """
        validate_stt_runtime_config()

        normalized_path = str(saved_path)
        try:
            model = cls.get_model(model_name)
        except KeyError as exc:
            raise KeyError(f"모델명 '{model_name}'이 MODEL_NAME_MAP에 없습니다.") from exc

        try:
            try:
                segments_iter, info = model.transcribe(
                    normalized_path,
                    language=TRANSCRIBE_LANGUAGE,
                    beam_size=TRANSCRIBE_BEAM_SIZE,
                    vad_filter=TRANSCRIBE_VAD_FILTER,
                    hotwords=TRANSCRIBE_HOTWORDS,
                )
                segments = list(segments_iter)
            except RuntimeError:
                # 2026-07-23: CUDA 모델은 초기화가 lazy라 라이브러리 부재가 transcribe
                # 시점에 드러난다(예: libcublas.so.12 미발견). get_model의 초기화 폴백이
                # 발동하지 않으므로 여기서 CPU 모델로 1회 재시도한다.
                if getattr(getattr(model, "model", None), "device", "") != "cuda":
                    raise
                cpu_model = WhisperModel(
                    MODEL_NAME_MAP[model_name], device="cpu", compute_type="int8"
                )
                cls._model_cache[MODEL_NAME_MAP[model_name]] = cpu_model
                segments_iter, info = cpu_model.transcribe(
                    normalized_path,
                    language=TRANSCRIBE_LANGUAGE,
                    beam_size=TRANSCRIBE_BEAM_SIZE,
                    vad_filter=TRANSCRIBE_VAD_FILTER,
                    hotwords=TRANSCRIBE_HOTWORDS,
                )
                segments = list(segments_iter)
            full_text = " ".join(segment.text.strip() for segment in segments).strip()
            has_input = cls.has_stt_input(full_text)
            segment_outputs = cls.build_segments_payload(segments)

            return SttTranscribeResult(
                model_name=model_name,
                text=full_text,
                language=getattr(info, "language", None),
                duration=getattr(info, "duration", None),
                segments=segment_outputs,
                has_input=has_input,
                saved_file=saved_path.name,
            )
        except Exception as exc:
            raise RuntimeError(
                f"STT transcribe failed: file={saved_path.name}, model={model_name}"
            ) from exc
