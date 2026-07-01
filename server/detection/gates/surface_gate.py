import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import ReflexAlert, SurfaceResult

# MVP 범위: 학습된 가중치는 COCO 80클래스이므로 노면/보행 안전 P0 클래스 없음.
# 향후 커스텀 노면 학습(crosswalk/manhole/stair/grating/braille_damaged) 시 자동 활성화.
P0_SURFACE_CLASSES = {
    "crosswalk",
    "manhole",
    "stair",
    "stairs",
    "grating",
    "braille_damaged",
}


def surface_gate(
    surface_result: SurfaceResult,
    frame_height: float,
) -> ReflexAlert | None:
    """P0 노면 클래스가 프레임 하단에 검출되면 alert_id를 반환한다.

    커스텀 노면 학습 전까지는 COCO 클래스와 매칭되지 않아 None을 반환한다.
    """
    if surface_result.class_name not in P0_SURFACE_CLASSES:
        return None

    centroid_y = surface_result.centroid[1]
    if centroid_y <= frame_height * 0.6:
        return None

    alert_id = f"surface_{surface_result.class_name}"
    return ReflexAlert(
        event_id="",
        alert_id=alert_id,
        direction="front",
        clip=f"reflex_clips/{alert_id}.mp3",
        haptic=True,
        ts=0.0,
    )
