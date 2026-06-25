# -*- coding: utf-8 -*-
import sys
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from server.detection.schemas import ReflexAlert, SurfaceResult

P0_SURFACE_CLASSES = {
    "crosswalk",
    "manhole",
    "stair",
    "grating",
    "braille_damaged",
}


def surface_gate(
    surface_result: SurfaceResult,
    frame_height: float,
) -> Optional[ReflexAlert]:
    """P0 노면 클래스가 프레임 하단에 검출되면 alert_id를 반환한다."""
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
