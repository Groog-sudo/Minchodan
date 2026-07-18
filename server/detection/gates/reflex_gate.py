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
# 2026-07-18: 거리(Near/Medium/Far) 판정과 하단 소형 장애물 override는 더 이상 이 파일이
# 계산하지 않습니다. server/detection/distance_policy.py(SSOT)가 ByteTrackTracker.update()
# 단계에서 트랙별 히스테리시스까지 반영해 Detection.route/effective_distance_zone에
# 부착해두므로, 이 게이트는 route == "reflex"(= effective_distance_zone == "near") 여부만
# 소비합니다. 오탐 완화는 여전히 이 파일이 담당합니다.
#   (1) 존재 confidence 하한 (AGNOSTIC_MIN_CONFIDENCE)
#   (2) ByteTrack hit_count >= MIN_HIT_COUNT
#   (3) 중앙 존 (원거리·측면 오탐 제외는 distance_policy의 Near 진입 조건이 담당)
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
# 동일 track_id가 최소 이만큼 연속 프레임 유지되어야 반사 경보를 발동한다.
MIN_HIT_COUNT = 3
# 억제 키용. 방향은 clip/direction 필드에만 두고 alert_id에서는 제외한다.
SUPPRESS_ALERT_ID = "high_obstacle"
ALERT_SOURCE = "object"
# =========================================================================


def reflex_gate(
    detection: Detection,
    frame_height: float,
    frame_width: float,
) -> ReflexAlert | None:
    # =========================================================================
    # 👨‍💻 담당자 직접 코딩 영역 시작: 2. 위험도 필터링 및 거리 판별 (class-agnostic) 👨‍💻
    # 💡 [설계 의도]
    # 클래스명으로 분기하지 않고 "진행 방향 정면 Near 구역에 물체가 존재하는가" 자체로
    # 반사 경보를 가동해 복잡성과 오탐 위험도를 줄입니다.
    # =========================================================================
    if frame_width <= 0 or frame_height <= 0:
        return None

    # P0-3 (2026-07-17): Approach-Lot 재획득 객체는 MIN_HIT_COUNT 재충족 대기 없이 즉시 발동.
    # [면접 대비 주석] 접근 중 가려짐 후 1초 내 재등장 시 0.3s(3프레임) 대기가 30cm 추가 접근을
    # 허용해 안전 마진을 깎는 문제(S4)를 해소. 신뢰도/중앙/근접 조건은 여전히 유효해야 한다.
    if not detection.reacquired and detection.hit_count < MIN_HIT_COUNT:
        return None

    if detection.confidence < AGNOSTIC_MIN_CONFIDENCE:
        return None

    center_x = detection.bbox.x + detection.bbox.w / 2
    center_x_norm = center_x / frame_width
    is_centered = CENTER_X_MIN <= center_x_norm <= CENTER_X_MAX
    if not is_centered:
        return None

    # 거리 정책 SSOT의 route 불변식: Near(reflex)만 이 게이트를 통과한다.
    # Medium/Far는 route == "cognitive"이므로 여기서 바로 탈락한다(일반 객체 반사 0건).
    if detection.route != "reflex":
        return None
    # =========================================================================

    direction = estimate_direction(detection.bbox, frame_width, distance_class="near")
    # 억제는 방향 버킷과 무관하게 동일 키를 쓴다 (front ↔ front-left TTL 우회 방지).
    alert_id = SUPPRESS_ALERT_ID

    panning = (center_x / frame_width) * 2 - 1.0
    panning = max(-1.0, min(1.0, panning))

    # Near 구역 내에서도 접근 급박도에 따라 비프·햅틱 강도를 세분화한다(새 반사 구역을
    # 만드는 것이 아니라, 이미 Near로 확정된 단일 반사 구역 내부의 UX 강도 조절).
    distance_m = detection.heuristic_distance_m
    if distance_m <= 0.5:
        beep_interval_ms = 0
        haptic_pattern = "continuous"
    elif distance_m <= 0.6:
        beep_interval_ms = 100
        haptic_pattern = "continuous"
    else:
        beep_interval_ms = 250
        haptic_pattern = "double"

    return ReflexAlert(
        event_id="",
        alert_id=alert_id,
        direction=direction,
        # 클라이언트가 client/assets/sounds/reflex_clips/에 동일 파일명으로 번들 재생한다.
        clip=f"reflex_clips/high_{direction}.wav",
        haptic=True,
        panning=panning,
        distance=round(distance_m, 2),
        estimated_distance_m=round(distance_m, 2),
        beep_interval_ms=beep_interval_ms,
        haptic_pattern=haptic_pattern,
        ts=0.0,
        track_id=detection.track_id,
        class_name="obstacle",
        hit_count=detection.hit_count,
        distance_band="near",
        alert_source=ALERT_SOURCE,
        policy_version=detection.policy_version,
    )
