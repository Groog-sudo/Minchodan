# -*- coding: utf-8 -*-
"""TTS 입력용 한국어 발화 문자열 정규화."""

import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


_PHONE_NUMBER_PATTERN = re.compile(
    r"(?<!\d)(?:(0\d{1,2})[-\s](\d{3,4})[-\s](\d{4})|(1[568]\d{2})[-\s](\d{4}))(?!\d)"
)
_SPOKEN_DIGITS = {
    "0": "공",
    "1": "일",
    "2": "이",
    "3": "삼",
    "4": "사",
    "5": "오",
    "6": "육",
    "7": "칠",
    "8": "팔",
    "9": "구",
}


def _speak_digit_group(group: str) -> str:
    return " ".join(_SPOKEN_DIGITS[digit] for digit in group)


def normalize_text_for_speech(text: str | None) -> str:
    """하이픈 전화번호를 자릿수 단위 한국어 발화로 변환한다.

    주소 번지·거리처럼 하이픈이 없는 일반 숫자는 보존하고, 화면 표시와 DB 저장에
    쓰이는 원문도 변경하지 않는다. 반환값만 TTS 엔진 입력으로 사용한다.
    """
    if not text:
        return ""

    def replace_phone(match: re.Match[str]) -> str:
        spoken_groups = ", ".join(_speak_digit_group(group) for group in match.groups() if group)
        return f"{spoken_groups} "

    return _PHONE_NUMBER_PATTERN.sub(replace_phone, str(text))
