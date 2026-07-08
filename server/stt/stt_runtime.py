# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.stt.stt_config import (
    DEFAULT_REQUEST_MODEL,
    MODEL_NAME_MAP,
    STT_ORCH_CLASS_NAME,
    STT_ORCH_RISK_HINT,
    TRANSCRIBE_BEAM_SIZE,
    TRANSCRIBE_LANGUAGE,
    TRANSCRIBE_VAD_FILTER,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
)


# ============================================================
# STT 런타임 검증 모듈
# ============================================================
# [바이브 코딩 부분]
# - 실행 직전 필요한 설정 조합이 유효한지 검증한다.
# - 설정값 자체는 stt_config.py 에 두고, 검증 책임만 분리한다.
# - validate_stt_runtime_config는 Whisper 실행 정책을, validate_stt_bridge_config는 오케스트레이션 연동 정책을 검증한다.


def validate_stt_runtime_config() -> None:
    """Whisper 실행에 필요한 STT 설정 조합을 검증한다."""
    if not MODEL_NAME_MAP:
        raise ValueError("MODEL_NAME_MAP이 비어 있습니다.")

    for request_name, internal_name in MODEL_NAME_MAP.items():
        if not request_name.strip() or not internal_name.strip():
            raise ValueError("MODEL_NAME_MAP의 key/value 공백 값을 제거하세요.")

    if not DEFAULT_REQUEST_MODEL:
        raise ValueError("DEFAULT_REQUEST_MODEL을 설정하세요.")

    if DEFAULT_REQUEST_MODEL not in MODEL_NAME_MAP:
        raise ValueError("DEFAULT_REQUEST_MODEL은 MODEL_NAME_MAP key여야 합니다.")

    if not TRANSCRIBE_LANGUAGE or len(TRANSCRIBE_LANGUAGE) < 2:
        raise ValueError("TRANSCRIBE_LANGUAGE는 2글자 이상 언어 코드여야 합니다.")

    if TRANSCRIBE_BEAM_SIZE <= 0:
        raise ValueError("TRANSCRIBE_BEAM_SIZE는 1 이상의 정수여야 합니다.")

    if not isinstance(TRANSCRIBE_VAD_FILTER, bool):
        raise ValueError("TRANSCRIBE_VAD_FILTER는 bool 타입이어야 합니다.")

    if WHISPER_DEVICE not in {"cpu", "cuda"}:
        raise ValueError('WHISPER_DEVICE는 "cpu" 또는 "cuda"여야 합니다.')

    if not WHISPER_COMPUTE_TYPE:
        raise ValueError("WHISPER_COMPUTE_TYPE을 설정하세요.")


def validate_stt_bridge_config() -> None:
    """STT 결과를 기존 오케스트레이션 입력으로 연결할 때 필요한 설정을 검증한다."""
    if STT_ORCH_RISK_HINT not in {"low", "mid"}:
        raise ValueError("STT_ORCH_RISK_HINT는 'low' 또는 'mid'여야 합니다.")

    if not STT_ORCH_CLASS_NAME:
        raise ValueError("STT_ORCH_CLASS_NAME을 설정하세요.")

    if " " in STT_ORCH_CLASS_NAME:
        raise ValueError("STT_ORCH_CLASS_NAME에는 공백을 포함할 수 없습니다.")
