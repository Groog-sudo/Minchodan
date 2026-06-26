# -*- coding: utf-8 -*-
"""
OrchState 데이터 모델 정의 파일.
LangGraph의 상태 관리를 담당하는 TypedDict 형태의 데이터 컨테이너를 포함합니다.
"""

import sys
from typing import List, Literal, TypedDict

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

class OrchState(TypedDict, total=False):
    """
    LangGraph StateGraph에서 사용되는 인지 경로 상태 정의 (TypedDict).
    total=False 설정을 통해 노드 간 부분 상태 업데이트가 용이하도록 합니다.
    """
    event: dict
    detected_classes: List[str]
    risk_level: Literal["high", "mid", "low"]
    rag_context: str
    positions: List[str]
    guidance_text: str
    direction: Literal["좌", "우", "직진", "정지", ""]
    verified: bool
    retry_count: int
    validation_errors: List[str]
    used_fallback_llm: bool
    used_static_fallback: bool
    total_latency_ms: float
