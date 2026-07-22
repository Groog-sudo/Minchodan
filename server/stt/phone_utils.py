"""STT 전화 걸기용 번호 정규화 및 발화 의도 판별."""

import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_KOREAN_DIGIT_MAP = {
    "공": "0",
    "영": "0",
    "일": "1",
    "이": "2",
    "삼": "3",
    "사": "4",
    "오": "5",
    "육": "6",
    "칠": "7",
    "팔": "8",
    "구": "9",
}

_DIAL_VERB_KEYWORDS = (
    "전화 걸",
    "전화해",
    "전화 연결",
    "통화 연결",
    "연결해줘",
    "연결해",
    "전화걸",
    "통화해",
    "에게 전화",
    "한테 전화",
    "로 전화",
    "에 전화",
)

_INFO_ONLY_KEYWORDS = (
    "알려",
    "알려줘",
    "뭐야",
    "뭐예요",
    "몇 번",
    "번호가",
    "번호는",
    "어디",
    "언제",
)

_EMERGENCY_NUMBERS = {
    "119": "119",
    "112": "112",
    "1339": "1339",
    "일일구": "119",
    "일일이": "112",
}


def normalize_phone_to_dialable(raw: str | None) -> str | None:
    """한글 음절·하이픈이 섞인 표기를 `tel:` URL용 숫자 문자열로 변환한다."""
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None

    if any(ch in _KOREAN_DIGIT_MAP for ch in text):
        converted = []
        for ch in text:
            if ch in _KOREAN_DIGIT_MAP:
                converted.append(_KOREAN_DIGIT_MAP[ch])
            elif ch.isdigit():
                converted.append(ch)
        digits = "".join(converted)
    else:
        digits = re.sub(r"\D", "", text)

    if not digits:
        return None
    if len(digits) < 3:
        return None
    return digits


def is_dial_intent(text: str | None) -> bool:
    """전화 연결 실행 의도인지 판별한다(번호 안내만 요청하는 발화는 제외)."""
    normalized = (text or "").strip()
    if not normalized:
        return False

    if any(kw in normalized for kw in _INFO_ONLY_KEYWORDS) and not any(
        kw in normalized for kw in _DIAL_VERB_KEYWORDS
    ):
        return False

    if "전화번호" in normalized and not any(verb in normalized for verb in ("걸", "연결", "통화")):
        return False

    if any(kw in normalized for kw in _DIAL_VERB_KEYWORDS):
        return True

    for token, number in _EMERGENCY_NUMBERS.items():
        if token in normalized and any(
            hint in normalized for hint in ("연결", "전화", "걸", "통화", "불러")
        ):
            return True
        if token in normalized and number in ("119", "112", "1339"):
            return True

    return "보호자" in normalized and any(
        hint in normalized for hint in ("전화", "연결", "통화", "걸")
    )


def resolve_emergency_number(text: str | None) -> tuple[str | None, str]:
    """긴급번호(119/112/1339)를 추출한다."""
    normalized = (text or "").strip()
    for token, number in _EMERGENCY_NUMBERS.items():
        if token in normalized:
            label = {
                "119": "119 소방서",
                "112": "112 경찰",
                "1339": "1339 보건복지상담",
            }.get(number, number)
            return number, label
    return None, ""
