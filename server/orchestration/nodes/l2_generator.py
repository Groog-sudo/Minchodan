"""
L2 Generator Node.
탐지된 장애물 정보와 RAG 컨텍스트를 결합하여, LLM(gemma4-e4b/GPT-4o-mini)을 호출해
20자 이내의 한국어 우회 안내 문장을 비동기적으로 생성합니다.
"""

import contextlib
import logging
import re
import sys

from langchain_core.messages import HumanMessage, SystemMessage

from server.orchestration.llm_client_factory import LLMClientFactory

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# 설계서에 정의된 시스템 프롬프트 상수
# 2026-07-13: "좌측/우측" 같은 모호한 표현 대신, 실제 탐지 위치를 12시(정면) 기준
# 9시~3시 시계 방향으로 표현하도록 규칙을 바꿨다(실기기 실측으로 방향 모호성 제기됨).
GUIDANCE_SYSTEM_PROMPT = """당신은 시각장애인 보행 보조 AI입니다.
탐지된 장애물 정보와 안전 수칙을 바탕으로 즉각적인 회피 안내를 생성합니다.

[규칙]
1. 반드시 한국어 1문장으로 작성
2. 20자 이내 (공백 포함)
3. 방향은 반드시 "[탐지 방향]"에 주어진 값을 그대로 사용해 "N시 방향" 형식으로 표현
   (예: 2시 방향, 10시 방향). 정면(12시)은 "전방"이라고 표현. 정지가 필요하면 "정지"
4. [탐지 방향]이 주어지지 않으면(순수 노면 이탈 등) "좌측/우측" 없이 사실만 전달
5. 존댓말 (~하세요, ~세요) 사용
6. 간결하고 즉시 이해 가능한 표현 사용

[좋은 예시]
- "2시 방향 주의하세요" (10자)
- "10시 방향으로 이동하세요" (12자)
- "전방 주의, 정지하세요" (11자)
"""

_CLOCK_PATTERN = re.compile(r"(9|10|11|12|1|2|3)시")


def extract_direction(text: str) -> str:
    """
    텍스트 내에서 방향 표현을 찾아내어, 문장의 최종 회피 지시 방향을 추출합니다.
    "N시" 시계 방향 표현을 우선 탐색하고(정확도가 높음), 없으면 기존 좌/우/직진/정지
    키워드로 폴백한다(LLM이 지시를 안 따른 경우의 하위호환).
    """
    if not text:
        return ""

    clock_matches = list(_CLOCK_PATTERN.finditer(text))
    if clock_matches:
        # 가장 마지막에 나타난 시계 방향이 최종 지시일 확률이 높다.
        return f"{clock_matches[-1].group(1)}시"

    keyword_mapping = {
        "좌": ["좌측", "좌", "왼쪽", "왼"],
        "우": ["우측", "우", "오른쪽", "오른"],
        "직진": ["직진", "앞으로", "전방"],
        "정지": ["정지", "멈추", "서세요", "대기"],
    }

    found = []
    for direction, keywords in keyword_mapping.items():
        for kw in keywords:
            idx = text.rfind(kw)  # 가장 마지막에 나타난 위치 찾기
            if idx != -1:
                found.append((idx, direction))

    if not found:
        return ""

    # 가장 마지막에 나타난 방향을 핵심 지시 방향으로 판정
    found.sort(key=lambda x: x[0], reverse=True)
    return found[0][1]


async def l2_generator_node(state: dict) -> dict:
    """
    LangGraph L2 생성기 노드 진입점.
    Ollama(gemma4-e4b) 비동기 호출을 처리하며, 예외 상황 발생 시 OpenAI 핫스왑을 시도합니다.
    """
    detected_classes = state.get("detected_classes", [])
    risk_level = state.get("risk_level", "low")
    rag_context = state.get("rag_context", "관련 수칙 없음")
    navigation_guidance = state.get("navigation_guidance", "")
    retry_count = state.get("retry_count", 0)
    errors = state.get("validation_errors", [])
    is_departing_confirmed = state.get("is_departing_confirmed", False)
    braille_direction = state.get("braille_direction", "")
    clock_direction = state.get("clock_direction", "")

    classes_str = ", ".join(detected_classes) if detected_classes else "장애물 없음"
    nav_str = f"[길안내 멘트]: {navigation_guidance}\n" if navigation_guidance else ""
    # 2026-07-13 추가: 주 탐지 객체의 실측 bbox 위치를 12시 기준 시계 방향으로 알려준다.
    # LLM이 "좌측/우측"을 임의로 지어내지 않고 이 실측값을 그대로 문장에 반영하게 한다.
    direction_str = f"[탐지 방향]: {clock_direction} 방향\n" if clock_direction else ""

    # 2026-07-13 추가: 보도 이탈이 확정되면(3단계 히스테리시스 통과) LLM 프롬프트에
    # 노면 상태를 별도 줄로 명시한다. 점자블록 방향을 알면 "왼쪽/오른쪽으로"까지
    # 함께 안내할 수 있어(GUIDANCE_SYSTEM_PROMPT의 방향 키워드 규칙과도 자연히 맞음),
    # 모르면(점자블록이 화면에 없음) 방향 없이 이탈 사실만 전달하도록 문장을 나눈다.
    departure_str = ""
    if is_departing_confirmed:
        if braille_direction == "left":
            departure_str = (
                "[노면 상태]: 보도를 벗어나 차도 방향입니다. 점자블록이 왼쪽에 있습니다.\n"
            )
        elif braille_direction == "right":
            departure_str = (
                "[노면 상태]: 보도를 벗어나 차도 방향입니다. 점자블록이 오른쪽에 있습니다.\n"
            )
        else:
            departure_str = "[노면 상태]: 보도를 벗어나 차도 방향입니다.\n"

    # 사용자 프롬프트 조립 (설계서 10.2절 프롬프트 및 내비게이션 멘트 융합)
    user_prompt = (
        f"[탐지 장애물]: {classes_str}\n"
        f"{direction_str}"
        f"[위험도]: {risk_level}\n"
        f"[안전 수칙]:\n{rag_context}\n"
        f"{nav_str}"
        f"{departure_str}\n"
        f"위 정보를 바탕으로, 장애물 회피 안내와 길안내 멘트를 자연스럽게 조합하여 20자 이내 한국어 1문장 보행 안내 가이드를 작성하세요."
    )

    # 1차 검증에 실패하여 다시 재생성(RETRY)을 수행하는 경우 에러 피드백 피딩
    if retry_count > 0 and errors:
        user_prompt += (
            f"\n\n[피드백]: 이전 생성 문장('{state.get('guidance_text', '')}')은 "
            f"다음 오류로 인해 거절되었습니다: {', '.join(errors)}.\n"
            f"이번에는 반드시 위의 위반 사항을 보완하여 올바른 안내문을 생성하세요."
        )

    messages = [SystemMessage(content=GUIDANCE_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

    used_fallback = False
    response_content = ""

    try:
        # 1차 시도: 기본 설정된 클라이언트 호출 (Ollama)
        client = LLMClientFactory.get_client()
        logger.info(f"Invoking primary LLM client for user prompt: {user_prompt[:50]}...")
        response = await client.ainvoke(messages)
        response_content = response.content.strip()
    except Exception as e:
        logger.warning(
            f"Primary LLM client invocation failed: {e!s}. Attempting OpenAI Fallback..."
        )
        try:
            # 2차 시도: OpenAI gpt-4o-mini로 자동 핫스왑
            fallback_client = LLMClientFactory.get_client(provider="openai")
            response = await fallback_client.ainvoke(messages)
            response_content = response.content.strip()
            used_fallback = True
            logger.info("OpenAI Fallback invocation completed successfully.")
        except Exception as fallback_err:
            # 모든 LLM 호출 실패 시: 안내 텍스트를 빈 값으로 넘겨 L3 검증기에서 정적 Fallback이 트리거되도록 함
            logger.critical(f"All LLM clients failed to respond: {fallback_err!s}")
            response_content = ""

    direction = extract_direction(response_content)

    return {
        "guidance_text": response_content,
        "direction": direction,
        "used_fallback_llm": used_fallback,
    }
