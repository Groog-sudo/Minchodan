import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.direction import estimate_direction
from server.detection.gates.reflex_gate import MIN_HIT_COUNT
from server.detection.schemas import Detection, ReflexAlert

# =========================================================================
# 👨‍💻 HARD CODE 영역 시작: 머리 높이 위험물 반사 경로 격상 규칙 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 왜 별도의 head-level gate가 필요했나요?
# 답변: reflex_gate는 기본적으로 "발밑 근접 위험"을 잡는 규칙입니다. 그런데 시각장애인의
# 흰지팡이는 지면/무릎 높이 위험에는 강하지만, 머리나 어깨 높이에 튀어나온 장애물에는 약합니다.
# 따라서 상체 높이 장애물은 mid risk 객체라도 별도 게이트에서 high로 격상해,
# LLM 설명을 기다리지 않고 즉시 반사 경보를 내보내도록 분리했습니다.
#
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
# 너무 보수적으로 잡으면 천장/표지판까지 과경보가 나고, 너무 좁히면 실제 상체 위험을 놓친다.
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
    HEAD_LEVEL_ESCALATION_CLASSES를 전달한다(인지 mid MID_RISK_CLASSES와 분리).
    """
    # 💡 [면접 대비 주석]
    # 격상 대상 클래스를 이 파일에 또 따로 하드코딩하지 않고 detection_pipeline에서 주입받는 이유:
    # head-level 격상 대상은 detection_pipeline.HEAD_LEVEL_ESCALATION_CLASSES로
    # 단일 SSOT를 유지한다(2026-07-17: 인지 mid 객체 목록과 분리).
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
        # 2026-07-14 추가: 관제 콘솔 발화 추적용 객체 정보 전달.
        track_id=detection.track_id,
        class_name=detection.class_name,
        hit_count=detection.hit_count,
    )
