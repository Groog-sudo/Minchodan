import os
import sys
from typing import Literal, Protocol

from server.detection import distance_policy

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
#
# 2026-07-20: FRONT_BAND는 공간 라벨(front/front-left/front-right)·로그·콘솔용이다.
# 음성·햅틱 안내는 SPEECH_FRONT_BAND + is_speech_front()만 사용한다.
FRONT_BAND = {"near": (0.20, 0.80), "medium": (0.30, 0.70), "far": (0.38, 0.62)}


def _env_band(prefix: str, default_lo: float, default_hi: float) -> tuple[float, float]:
    lo = float(os.getenv(f"{prefix}_LO", str(default_lo)))
    hi = float(os.getenv(f"{prefix}_HI", str(default_hi)))
    if lo > hi:
        lo, hi = hi, lo
    return (lo, hi)


# 안내용 12시 진행축 회랑(bbox 중심 x). Near/Medium만 안내, Far는 무발화.
# 환경변수: SPEECH_FRONT_BAND_NEAR_LO/HI, SPEECH_FRONT_BAND_MEDIUM_LO/HI
SPEECH_FRONT_BAND = {
    "near": _env_band("SPEECH_FRONT_BAND_NEAR", 0.35, 0.65),
    "medium": _env_band("SPEECH_FRONT_BAND_MEDIUM", 0.40, 0.60),
    "far": (0.45, 0.55),  # far는 안내 게이트에서 차단; 상수만 정의해 둔다
}
# =========================================================================


def estimate_direction(bbox: BBoxLike, frame_width: float, distance_class: Distance) -> Direction:
    """bbox의 좌우 끝점(x_min, x_max)을 이용해 거리에 따른 충돌 회랑 띠 포함 여부를 계산한다.

    공간 라벨·로그용. 음성/햅틱 허용 여부는 is_speech_front()를 쓴다.
    """
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


def is_speech_front(
    bbox: BBoxLike, frame_width: float, distance_class: Distance | str = "medium"
) -> bool:
    """안내용 12시 진행축 회랑: bbox 중심 x가 SPEECH_FRONT_BAND 안일 때만 True.

    frame_width<=0 이면 False(모르면 정면으로 폴백하지 않음).
    far는 안내 대상이 아니므로 False.
    """
    if frame_width <= 0:
        return False
    zone = distance_class if distance_class in ("near", "medium", "far") else "medium"
    if zone == "far":
        return False
    front_lo, front_hi = SPEECH_FRONT_BAND.get(zone, SPEECH_FRONT_BAND["medium"])
    center_x = bbox.x + bbox.w / 2.0
    xn = center_x / frame_width
    return front_lo <= xn <= front_hi


def is_speech_front_x(
    x: float, frame_width: float, distance_class: Distance | str = "medium"
) -> bool:
    """centroid x 등 단일 좌표용 안내용 12시 회랑 판정."""
    if frame_width <= 0:
        return False
    zone = distance_class if distance_class in ("near", "medium", "far") else "medium"
    if zone == "far":
        return False
    front_lo, front_hi = SPEECH_FRONT_BAND.get(zone, SPEECH_FRONT_BAND["medium"])
    xn = float(x) / frame_width
    return front_lo <= xn <= front_hi


def estimate_distance(
    bbox: BBoxLike, frame_width: float, frame_height: float, class_name: str
) -> Distance:
    """bbox 면적 비율을 고려하여 거리를 계산한다. (class-agnostic)

    2026-07-18: server/detection/distance_policy.py(거리 정책 SSOT)의 순수 함수로
    위임하는 얇은 wrapper로 전환했다. 이 함수는 트랙별 이전 구역(prev_zone) 정보가
    없는 호출부(RAG 검색, L1 분류기 등)에서 쓰는 상태 비저장(stateless) 평가이므로
    raw_zone_from_area_ratio()를 사용한다 - 히스테리시스가 필요한 반사 경로는
    ByteTrackTracker가 부착하는 Detection.effective_distance_zone을 직접 사용해야 한다.
    """
    area_ratio = distance_policy.compute_area_ratio(bbox, frame_width, frame_height)
    return distance_policy.raw_zone_from_area_ratio(area_ratio)


def bbox_area_ratio(bbox: BBoxLike, frame_width: float, frame_height: float) -> float:
    return distance_policy.compute_area_ratio(bbox, frame_width, frame_height)


# 인지 경로 전용 - 반사 경로(estimate_direction, front/front-left/front-right 3분대)와는
# 무관하다. 카메라 전방 시야가 대략 90도라 6시(정면 카메라 기준 정후방)는 물리적으로
# 탐지 불가하므로, 12시(정면)를 중심으로 9시~3시 7단계만 다룬다.
CLOCK_HOURS = [9, 10, 11, 12, 1, 2, 3]


def estimate_clock_direction(bbox: BBoxLike, frame_width: float) -> str:
    """bbox 중심 x좌표를 12시(정면) 기준 9시~3시 사이 7단계 시계 방향 문자열로 변환한다.

    인지 경로 안내 문장의 "좌측/우측" 같은 모호한 표현을 실제 탐지 위치 기반의
    정확한 방향("2시 방향" 등)으로 대체하기 위해 도입했다(2026-07-13).
    안내 발화 허용은 is_speech_front()가 담당하며, speech_front일 때 호출부는
    clock_direction을 "12시"로 정규화한다.
    """
    if frame_width <= 0:
        return "12시"

    center_x = bbox.x + bbox.w / 2
    normalized = min(1.0, max(0.0, center_x / frame_width))
    index = round(normalized * (len(CLOCK_HOURS) - 1))
    return f"{CLOCK_HOURS[index]}시"


def estimate_avoid_clock_direction(bbox: BBoxLike, frame_width: float) -> str:
    """전방 장애물 기준 우회 제안 시각(10시/2시).

    객체가 화면 중심보다 왼쪽이면 오른쪽으로(2시), 오른쪽이면 왼쪽으로(10시) 우회한다.
    데드센터는 L2 예시("전방 볼라드, 2시로 우회하세요")에 맞춰 2시로 둔다.
    """
    if frame_width <= 0:
        return "2시"

    center_x = bbox.x + bbox.w / 2
    normalized = min(1.0, max(0.0, center_x / frame_width))
    if normalized < 0.48:
        return "2시"
    if normalized > 0.52:
        return "10시"
    return "2시"
