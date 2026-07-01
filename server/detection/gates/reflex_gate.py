import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import Detection, ReflexAlert

# MVC 범위: 학습된 가중치(COCO 80클래스) 기반 high risk 차량/이동체.
# 향후 커스텀 보행 클래스(kickboard 등) 학습 시 여기에 추가한다.
HIGH_RISK_CLASSES = {
    "car",
    "truck",
    "bus",
    "motorcycle",
    "train",
    "boat",
}
PROXIMITY_THRESHOLD = 0.15


def _estimate_direction(bbox, frame_width: float) -> str:
    center_x = bbox.x + bbox.w / 2
    if center_x < frame_width / 3:
        return "left"
    if center_x > frame_width * 2 / 3:
        return "right"
    return "front"


def reflex_gate(
    detection: Detection,
    frame_height: float,
    frame_width: float,
) -> ReflexAlert | None:
    """고위험 클래스이고 프레임 하단에 근접하면 alert_id + 방향을 반환한다."""
    if detection.class_name not in HIGH_RISK_CLASSES:
        return None

    bottom_y = detection.bbox.y + detection.bbox.h
    if bottom_y <= frame_height * (1 - PROXIMITY_THRESHOLD):
        return None

    direction = _estimate_direction(detection.bbox, frame_width)
    alert_id = f"high_{detection.class_name}_{direction}"

    # 1. Panning 계산: center_x 위치 기준 -1.0(좌) ~ 1.0(우)
    center_x = detection.bbox.x + detection.bbox.w / 2
    panning = (center_x / frame_width) * 2 - 1.0
    panning = max(-1.0, min(1.0, panning))

    # 2. Distance 계산: 하단 경계부 밀착 정도에 따른 거리 역산 (0.4m ~ 1.5m 매핑)
    # PROXIMITY_THRESHOLD는 0.15이므로 bottom_y가 frame_height * 0.85 ~ 1.0 범위에 속함
    min_gate_y = frame_height * (1 - PROXIMITY_THRESHOLD)
    range_y = frame_height * PROXIMITY_THRESHOLD
    ratio = (bottom_y - min_gate_y) / range_y if range_y > 0 else 1.0
    ratio = max(0.0, min(1.0, ratio))

    # ratio가 1.0일수록 최하단에 인접해있으므로 거리(distance)는 짧아짐 (1.5m -> 0.4m)
    distance = 1.5 - (ratio * 1.1)
    distance = max(0.4, min(1.5, distance))

    # 3. 거리 기준 비프음 간격 및 햅틱 패턴 매핑
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
        clip=f"reflex_clips/high_{direction}.mp3",
        haptic=True,
        panning=panning,
        distance=round(distance, 2),
        beep_interval_ms=beep_interval_ms,
        haptic_pattern=haptic_pattern,
        ts=0.0,
    )
