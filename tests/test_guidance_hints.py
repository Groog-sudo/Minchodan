# -*- coding: utf-8 -*-
"""GUIDANCE_HINTS 인메모리 회피 힌트 단위 테스트."""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pytest

from server.rag.guidance_hints import (
    DEFAULT_HINT,
    GUIDANCE_HINTS,
    HINT_MAX_LEN,
    assert_hints_valid,
    select_guidance_hint,
    validate_hint,
)


def test_all_registered_hints_valid():
    assert_hints_valid()


def test_select_known_class_returns_registered_hint():
    hint = select_guidance_hint("bollard", seed="event-1")
    assert hint in GUIDANCE_HINTS["bollard"]
    assert len(hint) <= HINT_MAX_LEN


def test_select_unknown_class_uses_default():
    assert select_guidance_hint("unknown_xyz") == DEFAULT_HINT
    assert select_guidance_hint(None) == DEFAULT_HINT
    assert select_guidance_hint("") == DEFAULT_HINT


def test_select_is_deterministic_for_same_seed():
    a = select_guidance_hint("person", seed="track-42")
    b = select_guidance_hint("person", seed="track-42")
    assert a == b


def test_select_can_vary_across_seeds():
    hints = {select_guidance_hint("person", seed=f"e-{i}") for i in range(40)}
    # person has 2 hints; enough seeds should hit both
    assert hints == set(GUIDANCE_HINTS["person"])


def test_validate_hint_rejects_direction_and_length():
    with pytest.raises(ValueError):
        validate_hint("좌측으로 우회")
    with pytest.raises(ValueError):
        validate_hint("10시 방향 주의")
    with pytest.raises(ValueError):
        validate_hint("아주아주긴회피행동안내문구초과")
    with pytest.raises(ValueError):
        validate_hint("짧")
