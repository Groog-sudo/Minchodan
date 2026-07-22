import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.stt.phone_utils import (
    is_dial_intent,
    normalize_phone_to_dialable,
    resolve_emergency_number,
)


def test_normalize_korean_phone() -> None:
    assert normalize_phone_to_dialable("공이-이이이이-삼육구공") == "0222223690"
    assert normalize_phone_to_dialable("010-1234-5678") == "01012345678"


def test_is_dial_intent_excludes_info_only() -> None:
    assert is_dial_intent("서울시 장애인 생활지원센터 전화번호 알려줘") is False
    assert is_dial_intent("서울시 장애인 생활지원센터에 전화 걸어줘") is True


def test_resolve_emergency_number() -> None:
    number, label = resolve_emergency_number("119로 연결해줘")
    assert number == "119"
    assert "119" in label
