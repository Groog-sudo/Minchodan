import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# STT 패키지 진입점
# ============================================================
# - 설정/런타임 검증/스키마/서비스/브리지를 외부에서 일관되게 import 하도록 export를 모은다.
# - server/stt 내부 구현 세부 경로를 감추고, 상위 계층에는 안정된 공개 심볼만 노출한다.
# - 2026-07-19: SttToLlmBridge를 지연 임포트로 전환. phone_utils 같은 순수 유틸 임포트에
#   RAG/LangChain 스택이 끌려오는 것을 방지하고 단위 테스트 격리를 개선한다.

from .stt_config import (
    DEFAULT_REQUEST_MODEL,
    MODEL_NAME_MAP,
    TRANSCRIBE_BEAM_SIZE,
    TRANSCRIBE_LANGUAGE,
    TRANSCRIBE_VAD_FILTER,
    load_optional_stt_env,
)
from .stt_runtime import validate_stt_bridge_config, validate_stt_runtime_config
from .stt_schema import SegmentOut, SttTranscribeResult
from .stt_service import SttService

__all__ = [
    "DEFAULT_REQUEST_MODEL",
    "MODEL_NAME_MAP",
    "TRANSCRIBE_BEAM_SIZE",
    "TRANSCRIBE_LANGUAGE",
    "TRANSCRIBE_VAD_FILTER",
    "SegmentOut",
    "SttService",
    "SttToLlmBridge",
    "SttTranscribeResult",
    "load_optional_stt_env",
    "validate_stt_bridge_config",
    "validate_stt_runtime_config",
]


def __getattr__(name: str) -> Any:
    if name == "SttToLlmBridge":
        from .stt_to_llm_bridge import SttToLlmBridge

        return SttToLlmBridge
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
