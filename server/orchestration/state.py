"""
OrchState 데이터 모델 정의 파일.
LangGraph의 상태 관리를 담당하는 TypedDict 형태의 데이터 컨테이너를 포함합니다.
"""

import contextlib
import sys
from typing import Literal, TypedDict

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")


class OrchState(TypedDict, total=False):
    """
    LangGraph StateGraph에서 사용되는 인지 경로 상태 정의 (TypedDict).
    total=False 설정을 통해 노드 간 부분 상태 업데이트가 용이하도록 합니다.
    """

    event: dict
    detected_classes: list[str]
    risk_level: Literal["high", "mid", "low"]
    rag_context: str
    navigation_guidance: str
    positions: list[str]
    # 2026-07-13 추가: 보도 이탈 히스테리시스 확정 여부와 점자블록 추종 보정 방향.
    # server/detection/surface_departure.py의 판정 결과를 인지 경로 문장 생성에 전달한다.
    is_departing_confirmed: bool
    braille_direction: str
    # 2026-07-13 추가: 주 탐지 객체의 실제 화면 위치를 12시(정면) 기준 9시~3시 시계
    # 방향으로 환산한 값("2시" 등). L2가 "좌측/우측" 대신 이 값을 문장에 반영한다.
    clock_direction: str
    guidance_text: str
    # 2026-07-13: extract_direction()이 "N시" 시계 방향을 우선 추출하도록 바뀌어
    # 좌/우/직진/정지 외에 "9시"~"3시" 값도 들어올 수 있다.
    direction: str
    verified: bool
    retry_count: int
    validation_errors: list[str]
    used_fallback_llm: bool
    used_static_fallback: bool
    total_latency_ms: float
