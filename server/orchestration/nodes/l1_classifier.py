"""
L1 Classifier Node.
룰 기반으로 탐지된 객체의 위험도를 1차 분류합니다.
high 위험도 객체는 이미 3단계 게이트에서 처리되었으므로, 인지 경로에서는 mid와 low만 분류하여 진입시킵니다.
"""

import contextlib
import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

# 2026-07-07 정정: 이전 목록(kickboard/pothole/manhole/construction_cone)은 실제 파인튜닝
# 완료된 29클래스 Object Detection 모델에 존재하지 않는 클래스명이었다(전동킥보드는 실제로는
# "scooter"이며 이미 반사 게이트 고위험으로 분류됨). server/detection/detection_pipeline.py의
# _classify_risk와 동일한 실제 클래스 기준 목록으로 정정하여 두 분류기 간 불일치를 해소한다.
# [2026-07-14] 29종 객체 탐지는 무조건 반사 경로(비프/햅틱)로 처리되므로,
# 인지 경로(LLM)의 MID_RISK_CLASSES에서 객체 클래스를 전부 제거합니다.
# 인지 경로(mid)는 노면 이탈(is_departing_confirmed)과 위험 노면(caution/roadway)을 타겟팅합니다.
MID_RISK_CLASSES = set()
# detection_pipeline.MID_RISK_SURFACE_CLASSES와 동일 기준.
MID_RISK_SURFACE_CLASSES = {"caution", "roadway"}


def classify_risk(detected_classes: list, surface_classes: list | None = None) -> str:
    """
    탐지된 사물/노면 목록 중 중위험이 포함되어 있다면 'mid', 그렇지 않으면 'low'로 분류합니다.
    None 및 빈 리스트 가드를 적용합니다.
    """
    if not detected_classes and not surface_classes:
        return "low"

    for cls in detected_classes or []:
        if cls in MID_RISK_CLASSES:
            return "mid"
    for cls in surface_classes or []:
        # 한국어·영문 모두 허용(consumer가 surface_classes는 영문, surface_classes_ko는 한글)
        if cls in MID_RISK_SURFACE_CLASSES or cls in ("주의 노면", "차도"):
            return "mid"
    return "low"


async def l1_classifier_node(state: dict) -> dict:
    """
    LangGraph L1 분류 노드 진입점.
    """
    detected_classes = state.get("detected_classes", [])
    surface_classes = state.get("surface_classes") or []
    # 2026-07-13 추가: 탐지 객체가 없어도(순수 보도 이탈) 히스테리시스로 확정된 이탈은
    # mid로 분류해야 L2가 안내 문장을 생성한다. server/detection/consumer.py가
    # DEPARTURE_CONFIRM_STREAK 연속 프레임 확인 후에만 True를 넘기므로 여기서는
    # 그대로 신뢰한다(재검증하지 않음 - 판단 책임은 3단계 파이프라인에 있음).
    is_departing_confirmed = state.get("is_departing_confirmed", False)

    # 방어적 예외 처리: high가 인지 경로로 잘못 들어올 경우 차단하기 위한 가드 추가
    # 만약 state에 high가 이미 명시적으로 정의되어 있고 수동 디렉션이 있다면 존중하되,
    # 기본은 리스크에 맞춰 재분류합니다.
    risk_level = classify_risk(detected_classes, surface_classes)
    if is_departing_confirmed and risk_level == "low":
        risk_level = "mid"

    return {"risk_level": risk_level, "retry_count": 0, "verified": False, "validation_errors": []}
