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
    # 2026-07-07 추가: 동일 track_id가 연속으로 몇 프레임 유지됐는지(ByteTrackTracker가 채움).
    # 실내 오탐 완화용 - reflex_gate가 이 값을 확인해 한 프레임짜리 순간 오탐을 걸러낸다.
    hit_count: int = 0


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
