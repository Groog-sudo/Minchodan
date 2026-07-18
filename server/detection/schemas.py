import sys

from pydantic import BaseModel, Field

from server.detection.distance_policy import POLICY_VERSION

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
    # P0-3 (2026-07-17): Approach-Lost 플래그. 동일 track_id가 1초 이내 소실 후 재탐지되어
    # hit_count가 MIN_HIT_COUNT를 이미 충족했던 객체로 복원된 경우 True. reflex_gate는 이 때
    # MIN_HIT_COUNT 재충족 대기 없이 즉시 발동해 접근 객체의 재등장 지연(S4)을 해소한다.
    reacquired: bool = False
    # 2026-07-18 거리 정책 SSOT(distance_policy.py) 도입: ByteTrackTracker.update()가
    # track별 이전 구역(prev_zone)을 반영한 히스테리시스 평가 결과를 매 프레임 부착한다.
    # reflex_gate/detection_pipeline은 이 필드들을 신뢰의 단일 소스로 사용하고 별도로
    # 면적비·의사거리를 재계산하지 않는다.
    area_ratio: float = 0.0
    bottom_ratio: float = 0.0
    raw_distance_zone: str = "far"  # "near" | "medium" | "far"
    effective_distance_zone: str = "far"  # "near" | "medium" | "far" (override 반영 최종값)
    heuristic_distance_m: float = 0.0
    distance_source: str = "bbox_heuristic"
    route: str = "cognitive"  # "reflex" | "cognitive"
    route_reason: str = ""
    policy_version: str = POLICY_VERSION


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


class DistanceProbeSample(BaseModel):
    """LiDAR 실거리 검증 캡처 1건(=탐지 bbox 1개)의 클라이언트 보고값.

    거리측정(depthMode) 프로토타입에서 얻은 LiDAR 실측(lidar_meters)만 클라이언트가
    전송하고, 이 값과 비교할 휴리스틱 라벨(near/medium/far)은 서버가
    server/detection/direction.py:estimate_distance()로 동일 bbox를 재계산해 채운다
    (휴리스틱 계산의 단일 소스를 서버로 유지).
    """

    class_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BBox
    lidar_meters: float | None = None
    lidar_sample_count: int = 0
    lidar_accuracy: str | None = None  # "absolute" | "relative"
    lidar_quality: str | None = None  # "high" | "low"
    lidar_calibrated: bool = False


class DistanceProbeReport(BaseModel):
    event_id: str
    samples: list[DistanceProbeSample] = Field(default_factory=list)


class FixedPointProbeSample(BaseModel):
    """거리측정(depthMode) 화면의 고정 3지점(중앙/전방 하단/발밑) LiDAR 실측 1건.

    2026-07-19: 객체 탐지 결과와 무관하게, 화면에 이미 표시 중인 고정 지점 값을 그대로
    캡처해 줄자 대조용으로 저장한다. YOLO 탐지·휴리스틱 비교가 필요 없으므로 서버 왕복
    (detection 경로) 없이 클라이언트가 이미 보유한 probeDepth() 결과를 바로 보고한다.
    """

    point_label: str  # "중앙" | "전방 하단" | "발밑" 등 DEPTH_PROBE_POINTS의 label
    x: float  # 정규화 좌표(0~1)
    y: float
    lidar_meters: float | None = None
    axial_meters: float | None = None
    lidar_sample_count: int = 0
    lidar_accuracy: str | None = None  # "absolute" | "relative"
    lidar_quality: str | None = None  # "high" | "low"
    lidar_calibrated: bool = False


class FixedPointProbeReport(BaseModel):
    event_id: str
    samples: list[FixedPointProbeSample] = Field(default_factory=list)


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
    # P0-1 (2026-07-17): 억제 재무장 정책용 거리 밴드 ("near"|"medium"|"far").
    # suppressor가 track_id+distance_band 조합 키로 억제하므로 거리 악화 시 재발화 가능.
    distance_band: str = "medium"
    # 2026-07-18 거리 정책 SSOT: 안전 예외(머리 높이·노면)와 일반 객체 반사가 억제 키를
    # 교차 오염하지 않도록 출처를 명시한다("object" | "head_level" | "surface").
    alert_source: str = "object"
    # Near episode 상태("enter" | "update"). exit은 별도 ReflexClear 메시지로 전달한다.
    event_state: str = "enter"
    # distance_policy.evaluate_distance()가 계산한 파생 거리(m). 레거시 필드 distance와
    # 동일한 값이지만 이름으로 "휴리스틱 파생값"임을 명확히 한다.
    estimated_distance_m: float = 0.0
    policy_version: str = POLICY_VERSION


class ReflexClear(BaseModel):
    """Near episode 종료(이탈 또는 track 소실) 시 전송하는 반사 해제 이벤트.

    단말은 이 메시지를 받으면 해당 track_id의 반사 비프·햅틱 출력을 즉시 정지한다.
    구버전 클라이언트는 이 메시지 타입을 모르므로 기존 짧은 비프 자동 종료가
    안전 폴백으로 남는다(호환 기간 동안 하위 호환).
    """

    event_id: str = ""
    alert_id: str
    track_id: str | None = None
    alert_source: str = "object"
    reason: str = "zone_exit"  # "zone_exit" | "track_lost"
    ts: float = 0.0
    policy_version: str = POLICY_VERSION
