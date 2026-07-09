import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.direction import estimate_direction
from server.detection.gates.reflex_gate import MIN_HIT_COUNT
from server.detection.schemas import Detection, ReflexAlert

# =========================================================================
# 머리 높이(상체) 위험물 격상 게이트.
# 근거: docs/design/behavior_and_risk_insight.md
#   "머리나 어깨 등 상체 높이에 있는 나뭇가지, 열려 있는 트럭 적재함 등은 흰지팡이로
#    감지하기 힘들어 충돌 사고 위험이 매우 높다. 카메라 상단 임계 영역(Y축 상단 40%
#    이상)에 위치한 위험 객체 감지 시, 중위험 사물이라도 고위험 수준으로 격상한다."
#
# reflex_gate.py는 발밑(화면 하단 15%) 근접만 감지하므로, 발밑에는 아직 닿지 않았지만
# 몸통보다 높은 위치에서 튀어나온 장애물(머리 위 가지, 개방된 적재함 등)은 그대로 두면
# 인지 경로(mid, 수 초 지연되는 LLM 안내)로만 흘러가 충돌 전에 경보가 늦을 수 있다.
# =========================================================================

# 화면 상단 이 비율 이내에 물체 중심이 있으면 "머리 위" 후보로 본다.
TOP_REGION_RATIO = 0.40
# 오탐 방지를 위한 최소 confidence (reflex_gate.py의 HIGH_RISK_CLASSES 수준과 동일하게 보수적으로).
MIN_CONFIDENCE = 0.5


def head_level_gate(
    detection: Detection,
    frame_height: float,
    frame_width: float,
    escalation_classes: frozenset[str],
) -> ReflexAlert | None:
    """중위험(mid) 클래스 객체가 화면 상단 40% 영역(머리 높이)에 위치하면 고위험으로 격상한다.

    escalation_classes: 격상 대상 클래스 집합. 호출측(detection_pipeline)이
    MID_RISK_CLASSES를 그대로 전달해 두 목록이 따로 어긋나지 않도록 한다.
    """
    if detection.class_name not in escalation_classes:
        return None

    if detection.confidence < MIN_CONFIDENCE:
        return None

    # 일시적 오탐(1프레임 튐) 방지: reflex_gate와 동일한 최소 연속 프레임 기준 적용.
    if detection.hit_count < MIN_HIT_COUNT:
        return None

    if frame_height <= 0:
        return None

    center_y = detection.bbox.y + detection.bbox.h / 2
    center_y_ratio = center_y / frame_height
    if center_y_ratio > TOP_REGION_RATIO:
        return None

    direction = estimate_direction(detection.bbox, frame_width, distance_class="near")
    center_x = detection.bbox.x + detection.bbox.w / 2
    panning = (center_x / frame_width) * 2 - 1.0 if frame_width > 0 else 0.0
    panning = max(-1.0, min(1.0, panning))

    return ReflexAlert(
        event_id="",
        alert_id=f"head_level_{detection.class_name}",
        direction=direction,
        clip="reflex_clips/head_level_warning.wav",
        haptic=True,
        panning=panning,
        distance=1.0,
        beep_interval_ms=100,
        haptic_pattern="continuous",
        ts=0.0,
    )
