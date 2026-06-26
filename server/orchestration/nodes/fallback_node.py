# -*- coding: utf-8 -*-
"""
Fallback Node.
모든 시나리오 및 LLM 생성이 최종 실패했을 때 도달하는 최후의 안전망입니다.
가이드라인을 준수하는 고정 정지 메시지를 즉시 반환합니다.
"""

import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

FALLBACK_MESSAGE = "전방 주의, 천천히 멈추세요"

async def fallback_node(state: dict) -> dict:
    """
    LangGraph 폴백 노드 진입점.
    최후의 안전 안내 문자열을 주입하여 전체 파이프라인의 중단을 예방합니다.
    """
    return {
        "guidance_text": FALLBACK_MESSAGE,
        "direction": "정지",
        "used_static_fallback": True,
        "verified": True
    }
