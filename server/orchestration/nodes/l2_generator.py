# -*- coding: utf-8 -*-
"""
L2 Generator Node.
탐지된 장애물 정보와 RAG 컨텍스트를 결합하여, LLM(Gemma2/GPT-4o-mini)을 호출해
20자 이내의 한국어 우회 안내 문장을 비동기적으로 생성합니다.
"""

import sys
import logging

from langchain_core.messages import HumanMessage, SystemMessage


from server.orchestration.llm_client_factory import LLMClientFactory

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

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
    텍스트 내에서 방향성 키워드를 찾아내어 단일 방향 문자로 매핑합니다.
    """
    if not text:
        return ""
        
    keyword_mapping = {
        "좌": ["좌측", "좌", "왼쪽", "왼"],
        "우": ["우측", "우", "오른쪽", "오른"],
        "직진": ["직진", "앞으로", "전방"],
        "정지": ["정지", "멈추", "서세요", "대기"]
    }
    
    for direction, keywords in keyword_mapping.items():
        if any(kw in text for kw in keywords):
            return direction
    return ""

async def l2_generator_node(state: dict) -> dict:
    """
    LangGraph L2 생성기 노드 진입점.
    Ollama(Gemma2) 비동기 호출을 처리하며, 예외 상황 발생 시 OpenAI 핫스왑을 시도합니다.
    """
    detected_classes = state.get("detected_classes", [])
    risk_level = state.get("risk_level", "low")
    rag_context = state.get("rag_context", "관련 수칙 없음")
    
    classes_str = ", ".join(detected_classes) if detected_classes else "장애물 없음"
    
    # 사용자 프롬프트 조립 (설계서 10.2절 프롬프트 준수)
    user_prompt = (
        f"[탐지 장애물]: {classes_str}\n"
        f"[위험도]: {risk_level}\n"
        f"[안전 수칙]:\n{rag_context}\n\n"
        f"위 정보를 바탕으로 20자 이내 한국어 1문장 회피 안내를 작성하세요."
    )
    
    messages = [
        SystemMessage(content=GUIDANCE_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]
    
    used_fallback = False
    response_content = ""
    
    try:
        # 1차 시도: 기본 설정된 클라이언트 호출 (Ollama)
        client = LLMClientFactory.get_client()
        logger.info(f"Invoking primary LLM client for user prompt: {user_prompt[:50]}...")
        response = await client.ainvoke(messages)
        response_content = response.content.strip()
    except Exception as e:
        logger.warning(f"Primary LLM client invocation failed: {str(e)}. Attempting OpenAI Fallback...")
        try:
            # 2차 시도: OpenAI gpt-4o-mini로 자동 핫스왑
            fallback_client = LLMClientFactory.get_client(provider="openai")
            response = await fallback_client.ainvoke(messages)
            response_content = response.content.strip()
            used_fallback = True
            logger.info("OpenAI Fallback invocation completed successfully.")
        except Exception as fallback_err:
            # 모든 LLM 호출 실패 시: 안내 텍스트를 빈 값으로 넘겨 L3 검증기에서 정적 Fallback이 트리거되도록 함
            logger.critical(f"All LLM clients failed to respond: {str(fallback_err)}")
            response_content = ""
            
    direction = extract_direction(response_content)
    
    return {
        "guidance_text": response_content,
        "direction": direction,
        "used_fallback_llm": used_fallback
    }
