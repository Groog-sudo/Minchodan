# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import server.stt.stt_config as stt_config
import server.stt.stt_runtime as stt_runtime


# ============================================================
# 테스트 파일 역할
# ============================================================
# [바이브 코딩 부분]
# - 현재 stt_config 정책값이 런타임 검증을 통과하는지 확인.
# - server/stt가 테스트 모드를 포함하지 않는 구조를 확인.
#
# [하드 코딩 부분]
# - 정책 경계값(언어 코드, beam_size, device/compute_type) 실패 케이스를 직접 추가.


def test_validate_stt_runtime_config_passes_with_current_policy() -> None:
    stt_runtime.validate_stt_runtime_config()


def test_server_stt_has_no_test_mode_helpers() -> None:
    assert hasattr(stt_config, "is_test_mode_enabled") is False
    assert hasattr(stt_config, "resolve_test_text") is False
