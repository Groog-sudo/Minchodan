# -*- coding: utf-8 -*-
import sys
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

from server.detection.schemas import Detection, ReflexAlert

HIGH_RISK_CLASSES = {"car", "truck", "bus", "motorcycle"}
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
) -> Optional[ReflexAlert]:
    """고위험 클래스이고 프레임 하단에 근접하면 alert_id + 방향을 반환한다."""
    if detection.class_name not in HIGH_RISK_CLASSES:
        return None

    bottom_y = detection.bbox.y + detection.bbox.h
    if bottom_y <= frame_height * (1 - PROXIMITY_THRESHOLD):
        return None

    direction = _estimate_direction(detection.bbox, frame_width)
    alert_id = f"high_{direction}"
    return ReflexAlert(
        event_id="",
        alert_id=alert_id,
        direction=direction,
        clip=f"reflex_clips/{alert_id}.mp3",
        haptic=True,
        ts=0.0,
    )
