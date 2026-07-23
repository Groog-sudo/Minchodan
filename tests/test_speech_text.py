# -*- coding: utf-8 -*-
"""TTS 발화 문자열 정규화 테스트."""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.tts.speech_text import normalize_text_for_speech


def test_normalize_phone_number_for_korean_speech() -> None:
    text = "대표전화는 02-0000-2001이고 상담전화는 010-1234-5678입니다."

    result = normalize_text_for_speech(text)

    assert "공 이, 공 공 공 공, 이 공 공 일 이고" in result
    assert "공 일 공, 일 이 삼 사, 오 육 칠 팔 입니다" in result


def test_preserve_non_phone_numbers_and_empty_values() -> None:
    assert normalize_text_for_speech("주소는 기술로 55이며 약 200미터입니다.") == (
        "주소는 기술로 55이며 약 200미터입니다."
    )
    assert normalize_text_for_speech(None) == ""


def test_normalize_nationwide_service_phone_number() -> None:
    text = "복지콜은 1600-4477이고 장애인콜택시는 1588-4388입니다."

    result = normalize_text_for_speech(text)

    assert "일 육 공 공, 사 사 칠 칠 이고" in result
    assert "일 오 팔 팔, 사 삼 팔 팔 입니다" in result
