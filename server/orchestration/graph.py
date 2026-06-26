# -*- coding: utf-8 -*-
"""
graph.py
LangGraph StateGraph를 조립하고 컴파일된 실행 객체(싱글톤)를 반환하는 오케스트레이터 모듈입니다.
"""

import sys
import time

from langgraph.graph import END, StateGraph

from server.orchestration.state import OrchState
from server.orchestration.nodes.l1_classifier import l1_classifier_node
from server.orchestration.nodes.l2_generator import l2_generator_node
from server.orchestration.nodes.l3_validator import l3_validator_node
from server.orchestration.nodes.fallback_node import fallback_node

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def route_after_l3(state: dict) -> str:
    """
    L3 검증 노드 이후의 조건부 라우팅 판단 함수.
    검증이 통과되었거나 최종 폴백에 도달하면 END로, 그렇지 않으면 L2(생성) 노드로 회귀합니다.
    """
    if state.get("verified"):
        return "end"
    return "l2_generate"

def build_graph() -> StateGraph:
    """
    LangGraph StateGraph 객체를 조립 및 컴파일하여 반환합니다.
    """
    workflow = StateGraph(OrchState)
    
    # 노드 등록
    workflow.add_node("l1_classify", l1_classifier_node)
    workflow.add_node("l2_generate", l2_generator_node)
    workflow.add_node("l3_validate", l3_validator_node)
    workflow.add_node("fallback", fallback_node)
    
    # 진입점 설정
    workflow.set_entry_point("l1_classify")
    
    # 엣지 연결
    workflow.add_edge("l1_classify", "l2_generate")
    workflow.add_edge("l2_generate", "l3_validate")
    
    # 조건부 엣지 정의
    workflow.add_conditional_edges(
        "l3_validate",
        route_after_l3,
        {
            "l2_generate": "l2_generate",
            "end": END
        }
    )
    
    return workflow.compile()

# 모듈 단위 컴파일 캐시 싱글톤 인스턴스
_compiled_orchestrator = None

def get_orchestrator():
    """
    컴파일된 LangGraph 실행 객체 싱글톤을 반환합니다.
    """
    global _compiled_orchestrator
    if _compiled_orchestrator is None:
        _compiled_orchestrator = build_graph()
    return _compiled_orchestrator

async def run_orchestrator(state: dict) -> dict:
    """
    전체 오케스트레이션 파이프라인을 구동하고 총 지연 시간(total_latency_ms)을 계산하는 헬퍼 함수.
    """
    orchestrator = get_orchestrator()
    start_time = time.time()
    
    # 방어적 탑레벨 에러 핸들링 (중단 방지 가드)
    try:
        result = await orchestrator.ainvoke(state)
    except Exception as e:
        sys.stderr.write(f"[CRITICAL] LangGraph orchestration crashed: {str(e)}. Triggering Emergency Fallback.\n")
        # 비상 상황 발생 시 Fallback Node 직접 구동
        result = await fallback_node(state)
        
    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000.0
    
    # 결과 상태 갱신
    result["total_latency_ms"] = latency_ms
    return result
