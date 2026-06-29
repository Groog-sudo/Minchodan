# -*- coding: utf-8 -*-
import sys
from typing import Literal, Protocol

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


Direction = Literal["front-left", "front", "front-right"]
Distance = Literal["near", "medium", "far"]
RiskLevel = Literal["high", "medium", "low"]


class BBoxLike(Protocol):
    x: float
    y: float
    w: float
    h: float


def estimate_direction(bbox: BBoxLike, frame_width: float) -> Direction:
    """bbox 중심점 기준으로 좌/정면/우 방향을 계산한다."""
    if frame_width <= 0:
        return "front"

    center_x_ratio = (bbox.x + bbox.w / 2.0) / frame_width
    if center_x_ratio < 0.33:
        return "front-left"
    if center_x_ratio > 0.66:
        return "front-right"
    return "front"


def estimate_distance(bbox: BBoxLike, frame_width: float, frame_height: float) -> Distance:
    """bbox 면적 비율로 가까움 정도를 계산한다."""
    area_ratio = bbox_area_ratio(bbox, frame_width, frame_height)
    if area_ratio >= 0.25:
        return "near"
    if area_ratio >= 0.10:
        return "medium"
    return "far"


def bbox_area_ratio(bbox: BBoxLike, frame_width: float, frame_height: float) -> float:
    if frame_width <= 0 or frame_height <= 0:
        return 0.0
    width = max(0.0, bbox.w)
    height = max(0.0, bbox.h)
    return (width * height) / float(frame_width * frame_height)
