"""
L3 Validator Node.
생성된 안내 문장이 길이(20자 이내), 방향 키워드 포함, 한국어 포함 등의 안전 규정을 준수하는지 검증합니다.
위반 시 1회에 한해 재시도(RETRY)를 트리거하며, 최종 실패 시 안전한 정적 메시지(Fallback)로 변환합니다.
"""

import contextlib
import re
import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

MAX_LEN = 20
MAX_RETRY = 1
FALLBACK_MESSAGE = "전방 주의, 천천히 멈추세요"

# 2026-07-13: L2가 "좌측/우측" 대신 "N시 방향"(9시~3시) 형식을 쓰도록 바뀌어
# 방향 키워드 검사에도 시계 방향 패턴을 추가한다(안 넣으면 정상 문장이 전부
# "방향 키워드 미포함"으로 재시도/폴백 처리되는 회귀가 생김).
_CLOCK_PATTERN = re.compile(r"(9|10|11|12|1|2|3)시")


def validate_guidance(text: str) -> tuple:
    """
    안내 문장의 유효성을 다중 검사합니다.
    Returns:
        (is_valid: bool, errors: list)
    """
    errors = []

    # 1. 빈 문장 검사
    if not text or not text.strip():
        return False, ["빈 문장"]

    # 2. 길이 검사 (20자 이내)
    text_len = len(text)
    if text_len > MAX_LEN:
        errors.append(f"길이 초과: {text_len}자 > {MAX_LEN}자")

    # 3. 방향 키워드 포함 여부 검사
    valid_keywords = ["좌", "우", "왼", "오른", "직진", "정지", "멈추", "서세요", "대기", "전방"]
    has_clock_direction = bool(_CLOCK_PATTERN.search(text))
    if not has_clock_direction and not any(kw in text for kw in valid_keywords):
        errors.append("방향 키워드 미포함")

    # 4. 한국어 포함 검사 (가~힣)
    if not any("\uac00" <= c <= "\ud7a3" for c in text):
        errors.append("한국어 미포함")

    return len(errors) == 0, errors


async def l3_validator_node(state: dict) -> dict:
    """
    LangGraph L3 검증 노드 진입점.
    """
    text = state.get("guidance_text", "")
    retry = state.get("retry_count", 0)

    is_valid, errors = validate_guidance(text)

    if is_valid:
        return {"verified": True, "validation_errors": []}

    # 검증 실패 시 재시도 횟수 판정
    if retry < MAX_RETRY:
        return {"verified": False, "retry_count": retry + 1, "validation_errors": errors}
    else:
        # 최대 재시도 횟수 초과 시, 상태를 미검증(verified=False)으로 두고 retry_count를 2로 올림
        # route_after_l3 조건부 엣지가 이 상태를 받아 fallback 노드로 보냅니다.
        return {
            "verified": False,
            "retry_count": retry + 1,
            "validation_errors": errors,
        }
