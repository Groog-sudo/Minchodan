import sys

from pydantic import BaseModel, Field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class BBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Detection(BaseModel):
    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BBox
    track_id: str | None = None
    speed: float | None = None
    direction: str | None = None
    risk: str | None = None  # "high" | "mid" | "low"


class SurfaceResult(BaseModel):
    class_name: str
    mask: str | None = None
    centroid: list[float]


class DetectionResult(BaseModel):
    event_id: str
    detections: list[Detection]
    surface: list[SurfaceResult]
    risk_hint: str  # "high" | "mid" | "low" | "none"
    inference_ms: float


class RiskEvent(BaseModel):
    event_id: str
    detections: list[Detection]
    surface: list[SurfaceResult]
    risk_hint: str
    inference_ms: float


class ReflexAlert(BaseModel):
    event_id: str
    alert_id: str
    direction: str  # "front" | "left" | "right" | "stop"
    risk_level: str = "high"
    clip: str
    haptic: bool = True
    panning: float = 0.0
    distance: float = 1.0
    beep_interval_ms: int = 250
    haptic_pattern: str = "double"
    ts: float
