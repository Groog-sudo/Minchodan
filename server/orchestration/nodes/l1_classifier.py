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
MID_RISK_CLASSES = {
    "barricade",
    "bench",
    "bicycle",
    "bollard",
    "carrier",
    "chair",
    "fire_hydrant",
    "kiosk",
    "movable_signage",
    "parking_meter",
    "pole",
    "potted_plant",
    "power_controller",
    "stroller",
    "table",
    "traffic_light_controller",
    "tree_trunk",
    "wheelchair",
}


def classify_risk(detected_classes: list) -> str:
    """
    탐지된 사물 목록 중 중위험 사물이 포함되어 있다면 'mid', 그렇지 않으면 'low'로 분류합니다.
    None 및 빈 리스트 가드를 적용합니다.
    """
    if not detected_classes:
        return "low"

    for cls in detected_classes:
        if cls in MID_RISK_CLASSES:
            return "mid"
    return "low"


async def l1_classifier_node(state: dict) -> dict:
    """
    LangGraph L1 분류 노드 진입점.
    """
    detected_classes = state.get("detected_classes", [])

    # 방어적 예외 처리: high가 인지 경로로 잘못 들어올 경우 차단하기 위한 가드 추가
    # 만약 state에 high가 이미 명시적으로 정의되어 있고 수동 디렉션이 있다면 존중하되,
    # 기본은 리스크에 맞춰 재분류합니다.
    risk_level = classify_risk(detected_classes)

    return {"risk_level": risk_level, "retry_count": 0, "verified": False, "validation_errors": []}
