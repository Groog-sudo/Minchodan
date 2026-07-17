"""반사 후속 행동 안내(Avoidance) 모듈.

P1-1 (2026-07-17): 반사 경보(정지) 800ms 후 인지 가이드(LangGraph L2) 대신
단일 객체 + 방향 확정 시 템플릿으로 즉시 우회 방향 안내를 생성한다.
LangGraph 전체(L1/L2/L3)를 돌리는 수 초 소요를 없애 반사 후속 안내 지연(S7)을 해소한다.

비협상 원칙 준수: 본 모듈은 순수 함수(템플릿)로 LLM/RAG/실시간 TTS를 경유하지 않는다.
반사 경로(server/detection/gates/)가 아닌 인지 경로 진입점(consumer)에서 호출된다.
"""

import contextlib
import sys

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import ReflexAlert
from server.orchestration.nodes.l3_validator import MAX_LEN

# panning 기준 우회 방향 판정 임계 (정면 장애물일 때 좌/우 우회 결정).
# panning은 -1(완전 왼쪽) ~ +1(완전 오른쪽). 0.2 초과/미만이면 좌/우 우회 제안.
FRONT_PANNING_THRESHOLD = 0.2


def build_avoidance_guidance(alert: ReflexAlert) -> str | None:
    """반사 alert의 direction/panning 기반 우회 방향 템플릿 (20자 이내).

    # [면접 대비 주석]
    # 반사 후속 행동 안내의 핵심: "정지" 경보 직후 사용자에게 즉시 "어디로 비켜야 하는지"를 제안.
    # 설계 의도: LangGraph L2(LLM 문장 생성)는 2~10s 소요되어 반사 후속 안내가 늦어지는 문제(S7)가 있음.
    # 단일 객체 + 방향 확정 시 템플릿으로 즉시 우회 방향을 제안해 지연을 제거.
    # 다중 객체/방향 불확정 시 None을 반환해 기존 LangGraph 경로로 폴백한다(안전 측면).
    #
    # direction 매핑 (estimate_direction 반환값):
    #   "front"       -> 정면 장애물, panning 기준 좌/우 우회 또는 정지
    #   "front-left"  -> 왼쪽에 장애물 -> 오른쪽으로 우회
    #   "front-right" -> 오른쪽에 장애물 -> 왼쪽으로 우회
    # panning: -1(완전 왼쪽) ~ +1(완전 오른쪽). 정면 장애물의 미세 위치 기준 우회 방향 세분화.

    Returns:
        20자 이내 우회 안내문, 또는 None(fast lane 불가 - LangGraph 폴백).
    """
    direction = alert.direction or ""

    if direction == "front-left":
        return "오른쪽으로 비켜주세요"
    if direction == "front-right":
        return "왼쪽으로 비켜주세요"
    if direction == "front":
        # 정면 장애물: panning 기준 좌/우 우회 제안
        panning = alert.panning or 0.0
        if panning > FRONT_PANNING_THRESHOLD:
            return "오른쪽으로 비켜주세요"
        if panning < -FRONT_PANNING_THRESHOLD:
            return "왼쪽으로 비켜주세요"
        # 정면 중앙 가까이 장애물: 우회 방향 불확정 -> 정지 우선
        return "멈추세요"
    if direction == "stop":
        return "멈추세요"
    # 알 수 없는 direction -> LangGraph 폴백
    return None


def can_use_avoidance_fast_lane(alert: ReflexAlert, detections: list) -> bool:
    """avoidance fast lane 사용 가능 여부 판정.

    조건:
        1. 단일 객체 (다중 객체는 우회 방향 충돌 가능성 -> LangGraph 폴백).
        2. build_avoidance_guidance가 유효한 텍스트를 반환.
        3. 생성 텍스트가 20자 이내 (L3 가드레일과 동일 기준).
    """
    if len(detections) != 1:
        return False
    guidance = build_avoidance_guidance(alert)
    if guidance is None:
        return False
    return len(guidance) <= MAX_LEN
