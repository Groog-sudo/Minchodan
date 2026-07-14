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
    # 2026-07-13 추가: 보도 이탈 판정(point-in-polygon)용 서버 내부 전용 폴리곤 좌표.
    # exclude=True로 model_dump/model_dump_json 시 항상 제외되어 Redis publish, WS 전송,
    # 콘솔 API 등 이 스키마가 직렬화되는 모든 경계에서 자동으로 빠진다(네트워크 비용 없음).
    polygon: list[list[float]] = Field(default_factory=list, exclude=True)


class DetectionResult(BaseModel):
    event_id: str
    detections: list[Detection]
    surface: list[SurfaceResult]
    risk_hint: str  # "high" | "mid" | "low" | "none"
    inference_ms: float
    # 2026-07-13 추가: 사용자 발밑 근사 기준점이 차도/위험 노면(roadway·caution) 폴리곤
    # 안에 있는지 여부(단일 프레임 기준, 히스테리시스 확정 전). 로그·콘솔 노출용.
    is_departing: bool = False
    # 2026-07-13 추가: 점자블록(braille_normal) 추종 보정 방향("left"/"right"/"center"),
    # 점자블록이 화면에 없으면 None(판단 불가와 "잘 따라가는 중"을 구분).
    braille_direction: str | None = None


class RiskEvent(BaseModel):
    event_id: str
    detections: list[Detection]
    surface: list[SurfaceResult]
    risk_hint: str
    inference_ms: float
    is_departing: bool = False
    braille_direction: str | None = None


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
    inference_ms: float = 0.0
    # 2026-07-14 추가: 발화 추적용 객체 정보 (reflex_gate/head_level_gate가 채움).
    # track_id는 ByteTrack이 부여한 식별자, class_name은 탐지된 객체 클래스,
    # hit_count는 동일 track_id의 연속 프레임 유지 횟수(오탐 완화 MIN_HIT_COUNT 기반).
    track_id: str | None = None
    class_name: str = ""
    hit_count: int = 0
