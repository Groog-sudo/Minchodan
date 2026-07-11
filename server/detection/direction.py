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


# =========================================================================
# 👨‍💻 HARD CODE 영역 시작: 충돌 회랑(front band) 폭 정의 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 왜 화면을 단순 3등분하지 않고 거리별로 front band 폭을 다르게 잡았나요?
# 답변: 가까운 장애물은 조금만 좌우로 치우쳐도 실제 충돌 회랑에 걸릴 가능성이 크기 때문에
# front 판정 폭을 더 넓게 잡아 보수적으로 경고해야 합니다. 반대로 먼 장애물은 너무 이르게
# 정면으로 판정하면 과경보가 많아지므로 front 폭을 좁혀 정밀도를 높였습니다.
# 즉 이 값은 "영상 좌표계의 중심"이 아니라 "보행자 충돌 가능 회랑"을 하드코딩한 것입니다.
FRONT_BAND = {"near": (0.20, 0.80), "medium": (0.30, 0.70), "far": (0.38, 0.62)}
# =========================================================================


def estimate_direction(bbox: BBoxLike, frame_width: float, distance_class: Distance) -> Direction:
    """bbox의 좌우 끝점(x_min, x_max)을 이용해 거리에 따른 충돌 회랑 띠 포함 여부를 계산한다."""
    # 💡 [면접 대비 주석]
    # 중심점(center_x) 하나만 보면 길쭉한 장애물이나 큰 차량의 폭을 반영하지 못합니다.
    # 그래서 bbox의 좌우 끝점(x_min, x_max)이 충돌 회랑 띠를 침범하는지를 보고,
    # 회랑과 겹치면 front를 우선하는 방식으로 보행 안전 쪽에 보수적으로 설계했습니다.
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


def estimate_distance(
    bbox: BBoxLike, frame_width: float, frame_height: float, class_name: str
) -> Distance:
    """bbox 면적 비율과 클래스별 특성을 고려하여 거리를 계산한다."""
    area_ratio = bbox_area_ratio(bbox, frame_width, frame_height)

    # =========================================================================
    # 👨‍💻 HARD CODE 영역 시작: 클래스별 거리 임계값 보정 👨‍💻
    # 💡 [면접 대비 주석]
    # 질문: 왜 작은 객체(bollard, fire_hydrant 등)는 별도 거리 기준을 썼나요?
    # 답변: 같은 거리라도 작은 객체는 bbox 면적이 작게 잡히기 때문에, 일반 차량 기준 면적
    # 임계값을 그대로 쓰면 너무 멀다고 오판해 경보 시점이 늦어집니다.
    # 그래서 작은 객체는 near/medium 기준을 더 낮춰 실제 보행 위험 타이밍에 맞게 조정했습니다.
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
    # =========================================================================


def bbox_area_ratio(bbox: BBoxLike, frame_width: float, frame_height: float) -> float:
    if frame_width <= 0 or frame_height <= 0:
        return 0.0
    width = max(0.0, bbox.w)
    height = max(0.0, bbox.h)
    return (width * height) / float(frame_width * frame_height)
