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

from server.detection.risk_rules import class_name_to_ko
from server.detection.schemas import ReflexAlert
from server.orchestration.nodes.l3_validator import MAX_LEN

# panning 기준 우회 방향 판정 임계 (정면 장애물일 때 좌/우 우회 결정).
# panning은 -1(완전 왼쪽) ~ +1(완전 오른쪽). 0.2 초과/미만이면 좌/우 우회 제안.
FRONT_PANNING_THRESHOLD = 0.2


def build_avoidance_guidance(alert: ReflexAlert, object_ko: str = "") -> str | None:
    """반사 alert의 direction/panning 기반 우회 방향 템플릿 (20자 이내).

    # [면접 대비 주석]
    # 반사 후속 행동 안내의 핵심: "정지" 경보 직후 사용자에게 즉시 "어디로 비켜야 하는지"를 제안.
    # 설계 의도: LangGraph L2(LLM 문장 생성)는 2~10s 소요되어 반사 후속 안내가 늦어지는 문제(S7)가 있음.
    # 단일 객체 + 방향 확정 시 템플릿으로 즉시 우회 방향을 제안해 지연을 제거.
    # 다중 객체/방향 불확정 시 None을 반환해 기존 LangGraph 경로로 폴백한다(안전 측면).
    #
    # direction 매핑 (estimate_direction 반환값):
    #   "front"       -> 정면(12시 회랑) 장애물, panning 기준 좌/우 우회 또는 정지
    #   "front-left"  -> 왼쪽에 장애물(12시 회랑 밖)
    #   "front-right" -> 오른쪽에 장애물(12시 회랑 밖)
    #   "stop"        -> "정지" 표지판 클래스 탐지(공간 방향 아님)
    # panning: -1(완전 왼쪽) ~ +1(완전 오른쪽). 정면 장애물의 미세 위치 기준 우회 방향 세분화.
    #
    # 2026-07-20 (실기기 필드 테스트 피드백):
    # (1) 12시 회랑 밖(front-left/front-right)까지 TTS로 안내하면 "안전한 방향에도 안내가
    #     나온다"는 혼란을 유발한다. 해당 방향은 반사 비프·햅틱의 스테레오 패닝으로 이미
    #     방향 정보가 전달되므로, 인지 TTS는 12시(front)만 담당하고 나머지는 None(무발화).
    # (2) 명사(객체명) 없는 "멈추세요" 단독 안내는 무엇에 대한 경보인지 알 수 없어 더
    #     헷갈린다. L2 프롬프트가 "멈추세요/정지/대기" 등 정지 명령을 금지하는 것과
    #     동일한 이유(반사 경로가 이미 정지시켰으므로 중복 명령 대신 객체를 알려준다) -
    #     모든 분기에서 object_ko가 있으면 반드시 문장에 포함한다.

    Returns:
        20자 이내 우회 안내문, 또는 None(12시 회랑 밖이거나 fast lane 불가 - 무발화/LangGraph 폴백).
    """
    direction = alert.direction or ""
    obj = (object_ko or "").strip()

    if direction == "stop":
        # 공간 방향이 아니라 "정지 표지판" 클래스 자체가 탐지된 경우.
        text = f"전방 {obj} 있어요" if obj else "전방 정지 표지판 있어요"
        return text if len(text) <= MAX_LEN else "전방 정지 표지판"

    if direction != "front":
        # 12시 회랑 밖(front-left/front-right)은 반사 비프·햅틱 방향 정보로 충분.
        return None

    # 정면(12시) 장애물: panning 기준 좌/우 우회 제안
    panning = alert.panning or 0.0
    if panning > FRONT_PANNING_THRESHOLD:
        text = f"전방 {obj}, 오른쪽으로 비켜주세요" if obj else "오른쪽으로 비켜주세요"
    elif panning < -FRONT_PANNING_THRESHOLD:
        text = f"전방 {obj}, 왼쪽으로 비켜주세요" if obj else "왼쪽으로 비켜주세요"
    else:
        # 정면 중앙 가까이 장애물: 좌우 우회 방향 불확정 -> 객체명만 명시(정지 명령 재사용 금지)
        text = f"전방 {obj} 있어요" if obj else "전방 주의하세요"

    if len(text) <= MAX_LEN:
        return text
    # 객체명이 길어 상한을 넘으면 방향 안내만 남긴다(무명사 폴백은 길이 초과 시에만 허용).
    if panning > FRONT_PANNING_THRESHOLD:
        return "오른쪽으로 비켜주세요"
    if panning < -FRONT_PANNING_THRESHOLD:
        return "왼쪽으로 비켜주세요"
    return f"전방 {obj}" if obj else "전방 주의하세요"


def can_use_avoidance_fast_lane(alert: ReflexAlert, detections: list) -> bool:
    """avoidance fast lane 사용 가능 여부 판정.

    조건:
        1. 단일 객체 (다중 객체는 우회 방향 충돌 가능성 -> LangGraph 폴백).
        2. build_avoidance_guidance가 유효한 텍스트를 반환(12시 회랑 밖이면 None -> 무발화).
        3. 생성 텍스트가 20자 이내 (L3 가드레일과 동일 기준).
    """
    if len(detections) != 1:
        return False
    object_ko = class_name_to_ko(detections[0].class_name)
    guidance = build_avoidance_guidance(alert, object_ko)
    if guidance is None:
        return False
    return len(guidance) <= MAX_LEN
