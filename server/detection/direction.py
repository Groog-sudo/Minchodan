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


FRONT_BAND = {
    "near": (0.20, 0.80),
    "medium": (0.30, 0.70),
    "far": (0.38, 0.62)
}


def estimate_direction(bbox: BBoxLike, frame_width: float, distance_class: Distance) -> Direction:
    """bbox의 좌우 끝점(x_min, x_max)을 이용해 거리에 따른 충돌 회랑 띠 포함 여부를 계산한다."""
    if frame_width <= 0:
        return "front"
    
    x_min = bbox.x
    x_max = bbox.x + bbox.w
    xmin_n = x_min / frame_width
    xmax_n = x_max / frame_width
    
    front_lo, front_hi = FRONT_BAND.get(distance_class, (0.33, 0.66))
    
    # 회랑 띠와 겹치면 front 우선 (충돌 회피 우선)
    if xmax_n >= front_lo and xmin_n <= front_hi:
        return "front"
    return "front-left" if xmax_n < front_lo else "front-right"


def estimate_distance(bbox: BBoxLike, frame_width: float, frame_height: float, class_name: str) -> Distance:
    """bbox 면적 비율과 클래스별 특성을 고려하여 거리를 계산한다."""
    area_ratio = bbox_area_ratio(bbox, frame_width, frame_height)
    
    # MVP 빠른 패치: 작은 객체는 면적 임계값을 하향 조정
    small_objects = {"bollard", "kickboard", "planter", "fire_hydrant"}
    normalized_class = class_name.strip().lower()
    
    if normalized_class in small_objects:
        if area_ratio >= 0.10:
            return "near"
        if area_ratio >= 0.04:
            return "medium"
        return "far"

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
