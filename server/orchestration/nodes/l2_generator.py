"""
L2 Generator Node.
탐지된 장애물 정보와 RAG 컨텍스트를 결합하여, LLM(gemma4-e4b/GPT-4o-mini)을 호출해
20자 이내의 한국어 우회 안내 문장을 비동기적으로 생성합니다.
"""

import contextlib
import logging
import sys

from langchain_core.messages import HumanMessage, SystemMessage

from server.orchestration.llm_client_factory import LLMClientFactory

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# 설계서에 정의된 시스템 프롬프트 상수
GUIDANCE_SYSTEM_PROMPT = """당신은 시각장애인 보행 보조 AI입니다.
탐지된 장애물 정보와 안전 수칙을 바탕으로 즉각적인 회피 안내를 생성합니다.

[규칙]
1. 반드시 한국어 1문장으로 작성
2. 20자 이내 (공백 포함)
3. 방향 키워드(좌/우/직진/정지) 중 하나를 반드시 포함
4. 존댓말 (~하세요, ~세요) 사용
5. 간결하고 즉시 이해 가능한 표현 사용

[좋은 예시]
- "좌측으로 피하세요" (9자)
- "우측 보도로 이동하세요" (11자)
- "전방 주의, 정지하세요" (11자)
"""


def extract_direction(text: str) -> str:
    """
    텍스트 내에서 방향성 키워드를 찾아내어, 문장의 최종 회피 지시 방향을 추출합니다.
    (문장에서 가장 마지막에 등장하는 키워드가 최종 결정 지시어일 확률이 높습니다)
    """
    if not text:
        return ""

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

    classes_str = ", ".join(detected_classes) if detected_classes else "장애물 없음"
    nav_str = f"[길안내 멘트]: {navigation_guidance}\n" if navigation_guidance else ""

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
