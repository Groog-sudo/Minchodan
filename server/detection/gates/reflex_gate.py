import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.direction import estimate_direction
from server.detection.schemas import Detection, ReflexAlert

# =========================================================================
# 👨‍💻 담당자 직접 코딩 영역 시작: 1. 반사 게이트 상수 (Option A class-agnostic) 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 29개 클래스를 학습했는데 왜 게이트 본문은 클래스명으로 분기하지 않나요?
# 답변: 클래스별로 반사하면 인도 상주 정적 객체(벤치·화분·기둥)에서도 알림 폭탄이 납니다.
# 진행 방향 정면의 "근접·중앙" 지오메트리만으로 즉시 경보하고, 세부 안내(클래스·거리·행동)는
# 인지 경로(LangGraph)에 맡깁니다. (outdoor_guidance_refinement_roadmap Option A)
#
# HIGH_RISK_CLASSES는 게이트 분기용이 아니라, 단말 온디바이스 CLASS_MIN_CONFIDENCE와의
# SSOT 계약(tests/test_risk_ssot.py)을 위한 참조 테이블로 유지합니다.
#
# 오탐 완화:
#   (1) 존재 confidence 하한 (AGNOSTIC_MIN_CONFIDENCE)
#   (2) ByteTrack hit_count >= MIN_HIT_COUNT
#   (3) 중앙 존 + 면적 비율 (원거리 작은 bbox 제외)
#   (4) alert_id를 방향 버킷과 분리해 억제 우회 방지
# =========================================================================
# 단말 SSOT 정합용 참조 테이블 (게이트 본문 미사용).
HIGH_RISK_CLASSES: dict[str, float] = {
    "barricade": 0.35,
    "bench": 0.3,
    "bicycle": 0.3,
    "bollard": 0.3,
    "bus": 0.35,
    "car": 0.35,
    "carrier": 0.3,
    "cat": 0.3,
    "chair": 0.3,
    "dog": 0.3,
    "fire_hydrant": 0.35,
    "kiosk": 0.3,
    "motorcycle": 0.35,
    "movable_signage": 0.3,
    "parking_meter": 0.35,
    "person": 0.3,
    "pole": 0.3,
    "potted_plant": 0.3,
    "power_controller": 0.3,
    "scooter": 0.3,
    "stop": 0.35,
    "stroller": 0.3,
    "table": 0.3,
    "traffic_light": 0.35,
    "traffic_light_controller": 0.35,
    "traffic_sign": 0.35,
    "tree_trunk": 0.3,
    "truck": 0.35,
    "wheelchair": 0.3,
}

# class-agnostic 게이트 임계 (서버 실행 경로)
AGNOSTIC_MIN_CONFIDENCE = 0.35
CENTER_X_MIN = 0.30
CENTER_X_MAX = 0.70
# 2026-07-16 Option A: 0.08 → 0.10 (실외 원거리/상주 객체 알림 완화)
MIN_AREA_RATIO = 0.10
# 화면 하단(발밑) 접근 임계치 — 레거시/단말 참고용 (본문 미사용, 면적 비율로 근접 판정)
PROXIMITY_THRESHOLD = 0.15
# 동일 track_id가 최소 이만큼 연속 프레임 유지되어야 반사 경보를 발동한다.
MIN_HIT_COUNT = 3
# 억제 키용. 방향은 clip/direction 필드에만 두고 alert_id에서는 제외한다.
SUPPRESS_ALERT_ID = "high_obstacle"
# =========================================================================


def reflex_gate(
    detection: Detection,
    frame_height: float,
    frame_width: float,
) -> ReflexAlert | None:
    # =========================================================================
    # 👨‍💻 담당자 직접 코딩 영역 시작: 2. 위험도 필터링 및 거리 판별 (class-agnostic) 👨‍💻
    # 💡 [설계 의도]
    # 클래스명으로 분기하지 않고 "진행 방향 정면 근접 구역에 물체가 존재하는가" 자체로
    # 반사 경보를 가동해 복잡성과 오탐 위험도를 줄입니다.
    # =========================================================================
    if frame_width <= 0 or frame_height <= 0:
        return None

    if detection.hit_count < MIN_HIT_COUNT:
        return None

    if detection.confidence < AGNOSTIC_MIN_CONFIDENCE:
        return None

    center_x = detection.bbox.x + detection.bbox.w / 2
    center_x_norm = center_x / frame_width
    is_centered = CENTER_X_MIN <= center_x_norm <= CENTER_X_MAX

    bbox_area = detection.bbox.w * detection.bbox.h
    frame_area = frame_width * frame_height
    area_ratio = bbox_area / frame_area
    is_very_close = area_ratio >= MIN_AREA_RATIO

    if not (is_very_close and is_centered):
        return None
    # =========================================================================

    direction = estimate_direction(detection.bbox, frame_width, distance_class="near")
    # 억제는 방향 버킷과 무관하게 동일 키를 쓴다 (front ↔ front-left TTL 우회 방지).
    alert_id = SUPPRESS_ALERT_ID

    panning = (center_x / frame_width) * 2 - 1.0
    panning = max(-1.0, min(1.0, panning))

    bottom_y = detection.bbox.y + detection.bbox.h
    ratio = bottom_y / frame_height
    ratio = max(0.0, min(1.0, ratio))

    distance = 1.5 - (ratio * 1.1)
    distance = max(0.4, min(1.5, distance))

    if distance <= 0.5:
        beep_interval_ms = 0
        haptic_pattern = "continuous"
    elif distance <= 1.0:
        beep_interval_ms = 100
        haptic_pattern = "continuous"
    elif distance <= 1.5:
        beep_interval_ms = 250
        haptic_pattern = "double"
    else:
        beep_interval_ms = 500
        haptic_pattern = "short"

    return ReflexAlert(
        event_id="",
        alert_id=alert_id,
        direction=direction,
        # 클라이언트가 client/assets/sounds/reflex_clips/에 동일 파일명으로 번들 재생한다.
        clip=f"reflex_clips/high_{direction}.wav",
        haptic=True,
        panning=panning,
        distance=round(distance, 2),
        beep_interval_ms=beep_interval_ms,
        haptic_pattern=haptic_pattern,
        ts=0.0,
        track_id=detection.track_id,
        class_name="obstacle",
        hit_count=detection.hit_count,
    )
