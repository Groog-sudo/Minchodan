# -*- coding: utf-8 -*-
import sys
from typing import List, Optional

from pydantic import BaseModel, Field

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Detection(BaseModel):
    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BBox
    track_id: Optional[str] = None
    speed: Optional[float] = None
    direction: Optional[str] = None
    risk: Optional[str] = None  # "high" | "mid" | "low"


class SurfaceResult(BaseModel):
    class_name: str
    mask: Optional[str] = None
    centroid: List[float]


class DetectionResult(BaseModel):
    event_id: str
    detections: List[Detection]
    surface: List[SurfaceResult]
    risk_hint: str  # "high" | "mid" | "low" | "none"
    inference_ms: float


class RiskEvent(BaseModel):
    event_id: str
    detections: List[Detection]
    surface: List[SurfaceResult]
    risk_hint: str
    inference_ms: float


class ReflexAlert(BaseModel):
    event_id: str
    alert_id: str
    direction: str  # "front" | "left" | "right" | "stop"
    risk_level: str = "high"
    clip: str
    haptic: bool = True
    ts: float
