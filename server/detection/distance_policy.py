import sys
from dataclasses import dataclass
from math import sqrt
from typing import Literal, Protocol

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


Zone = Literal["near", "medium", "far"]
Route = Literal["reflex", "cognitive"]

# docs/design/risk_ssot_contract.md §2-C(예정)와 tests/test_distance_policy.py가 참조하는
# 정책 버전 식별자. 경계값을 바꾸면 반드시 이 문자열도 함께 올린다(서버/클라이언트
# policy_version 불일치를 로그로 감지할 수 있게 하기 위함).
POLICY_VERSION = "distance-alert-v1"


class BBoxLike(Protocol):
    x: float
    y: float
    w: float
    h: float


# =========================================================================
# 👨‍💻 담당자 직접 코딩 영역 시작: 거리 정책 SSOT 상수 및 순수 함수 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 왜 근접(Near) 판정에 진입값과 이탈값을 다르게 뒀나요(0.10 vs 0.08)?
# 답변: 경계값 하나만 쓰면 area_ratio가 그 값 근처에서 프레임마다 미세하게 흔들릴 때
# (세그멘테이션/bbox 경계 노이즈) near<->medium 상태가 초당 여러 번 반복 전환되어
# 반사 경보가 깜빡입니다. 진입은 더 엄격하게(0.10), 이탈은 더 관대하게(0.08) 잡는
# 히스테리시스를 두면 한 번 Near에 진입한 트랙이 그 근방에서 안정적으로 유지됩니다.
HEURISTIC_COEFFICIENT = 0.22
HEURISTIC_MIN_M = 0.3
HEURISTIC_MAX_M = 3.0

NEAR_ENTER_AREA_RATIO = 0.10
NEAR_EXIT_AREA_RATIO = 0.08
MEDIUM_ENTER_AREA_RATIO = 0.03
MEDIUM_EXIT_AREA_RATIO = 0.025

# 소형 하단 장애물(볼라드·소화전 등) 보정: 화면 하단 80% 이하에 위치하고 면적비가
# 0.04 이상이면 아직 Near 진입값(0.10)에 못 미쳐도 근접으로 간주한다. 카메라가 전방을
# 약간 아래로 향해 거치되므로, 화면 하단은 실제로는 가까운 발밑 장애물을 의미한다.
BOTTOM_OVERRIDE_MIN_BOTTOM_RATIO = 0.80
BOTTOM_OVERRIDE_MIN_AREA_RATIO = 0.04
# =========================================================================


@dataclass(frozen=True)
class PolicyResult:
    raw_distance_zone: Zone
    effective_distance_zone: Zone
    area_ratio: float
    bottom_ratio: float
    heuristic_distance_m: float
    distance_source: str
    route: Route
    route_reason: str
    policy_version: str = POLICY_VERSION


def clip_bbox_to_frame(
    bbox: BBoxLike, frame_width: float, frame_height: float
) -> tuple[float, float, float, float]:
    """bbox를 프레임 경계 [0, width] x [0, height]로 클리핑해 (x, y, w, h)를 반환한다.

    bbox가 프레임 밖으로 나간 부분까지 면적으로 계산하면 화면 가장자리에 걸친
    큰 객체의 면적비가 실제보다 과대평가된다.
    """
    if frame_width <= 0 or frame_height <= 0:
        return 0.0, 0.0, 0.0, 0.0

    x_min = max(0.0, min(bbox.x, frame_width))
    y_min = max(0.0, min(bbox.y, frame_height))
    x_max = max(0.0, min(bbox.x + bbox.w, frame_width))
    y_max = max(0.0, min(bbox.y + bbox.h, frame_height))
    return x_min, y_min, max(0.0, x_max - x_min), max(0.0, y_max - y_min)


def compute_area_ratio(bbox: BBoxLike, frame_width: float, frame_height: float) -> float:
    """클리핑한 bbox 면적을 프레임 면적으로 나눈 값을 반환한다."""
    if frame_width <= 0 or frame_height <= 0:
        return 0.0
    _x, _y, w, h = clip_bbox_to_frame(bbox, frame_width, frame_height)
    return (w * h) / float(frame_width * frame_height)


def compute_bottom_ratio(bbox: BBoxLike, frame_height: float) -> float:
    """bbox 하단(y + h)이 프레임 높이에서 차지하는 정규화 위치(0~1)를 반환한다."""
    if frame_height <= 0:
        return 0.0
    bottom = bbox.y + bbox.h
    return max(0.0, min(1.0, bottom / frame_height))


def raw_zone_from_area_ratio(area_ratio: float) -> Zone:
    """이전 상태(히스테리시스) 없이 area_ratio 단일 값만으로 구역을 판정한다."""
    if area_ratio >= NEAR_ENTER_AREA_RATIO:
        return "near"
    if area_ratio >= MEDIUM_ENTER_AREA_RATIO:
        return "medium"
    return "far"


def apply_hysteresis(prev_zone: Zone | None, area_ratio: float) -> Zone:
    """직전 프레임 구역(prev_zone)을 반영해 경계 진동을 억제한 유효 구역을 계산한다.

    이전 상태가 없으면(신규 트랙) 히스테리시스를 적용할 기준점이 없으므로
    raw_zone_from_area_ratio()로 초기 구역을 확정한다.
    """
    if prev_zone is None:
        return raw_zone_from_area_ratio(area_ratio)

    if prev_zone == "near":
        return "near" if area_ratio >= NEAR_EXIT_AREA_RATIO else "medium"

    if prev_zone == "medium":
        if area_ratio >= NEAR_ENTER_AREA_RATIO:
            return "near"
        if area_ratio < MEDIUM_EXIT_AREA_RATIO:
            return "far"
        return "medium"

    # prev_zone == "far"
    return "medium" if area_ratio >= MEDIUM_ENTER_AREA_RATIO else "far"


def apply_bottom_override(zone: Zone, area_ratio: float, bottom_ratio: float) -> tuple[Zone, str]:
    """소형 하단 장애물 override를 적용하고 (최종 구역, route_reason)을 반환한다."""
    if (
        zone != "near"
        and bottom_ratio >= BOTTOM_OVERRIDE_MIN_BOTTOM_RATIO
        and area_ratio >= BOTTOM_OVERRIDE_MIN_AREA_RATIO
    ):
        return "near", "bottom_close_override"
    return zone, f"zone_{zone}"


def route_for_zone(zone: Zone) -> Route:
    return "reflex" if zone == "near" else "cognitive"


_ZONE_PRIORITY: dict[str, int] = {"near": 0, "medium": 1, "far": 2}


class PrioritizableDetection(Protocol):
    effective_distance_zone: str
    heuristic_distance_m: float
    confidence: float
    bbox: BBoxLike


def _corridor_offset(bbox: BBoxLike, frame_width: float) -> float:
    """bbox 중심 x가 화면 중앙(0.5)에서 얼마나 떨어졌는지(0에 가까울수록 중앙)."""
    if frame_width <= 0:
        return 1.0
    center_x = bbox.x + bbox.w / 2.0
    return abs(center_x / frame_width - 0.5)


def select_primary_detection(
    detections: list[PrioritizableDetection], frame_width: float
) -> PrioritizableDetection | None:
    """여러 탐지 중 안내/반사 판단 대상이 될 "주위험 객체" 하나를 선정한다.

    # [면접 대비 주석]
    # 질문: 왜 confidence 최댓값만으로는 부족한가요?
    # 답변: confidence는 "이 객체가 그 클래스가 맞는가"에 대한 모델의 확신도일 뿐,
    # "이 객체가 보행자에게 얼마나 위협적인가"와는 무관하다. 자동차·사람·트럭이 매
    # 프레임 함께 잡히는 실외 도로에서는 confidence가 프레임마다 미세하게 흔들려
    # "이번 프레임의 대표 객체"가 계속 바뀌고, 실제로 정면에 있는 위험 객체가 confidence
    # 경쟁에서 밀려 안내/반사 대상에서 간헐적으로 빠지는 문제가 실기기 로그로 확인됨.
    #
    # 우선순위(순서대로 비교): (1) 거리 구역(near>medium>far) - confidence보다 물리적
    # 거리가 안전에 직결, (2) 동일 구역 내 실측 거리(heuristic_distance_m) 오름차순 -
    # 더 가까운 객체 우선, (3) 12시 회랑 중심 근접도 - 진행 경로상 위협일 가능성 반영,
    # (4) confidence - 위 세 조건이 모두 동률일 때만 최종 tie-break.
    """
    if not detections:
        return None

    def _priority_key(det: PrioritizableDetection) -> tuple[int, float, float, float]:
        zone_rank = _ZONE_PRIORITY.get(det.effective_distance_zone, 2)
        corridor_offset = _corridor_offset(det.bbox, frame_width)
        return (zone_rank, det.heuristic_distance_m, corridor_offset, -det.confidence)

    return min(detections, key=_priority_key)


def compute_heuristic_distance_m(area_ratio: float) -> float:
    """면적비 기반 의사 거리(m)를 계산한다. 실측 거리가 아니라 파생값이다."""
    safe_ratio = max(area_ratio, 1e-6)
    raw_m = HEURISTIC_COEFFICIENT / sqrt(safe_ratio)
    return max(HEURISTIC_MIN_M, min(HEURISTIC_MAX_M, raw_m))


# =========================================================================
# 2026-07-19 (2단계, 온디맨드 유지 결정): LiDAR 실측 미터를 area_ratio 경계와 같은
# 정책으로 비교하기 위한 미터 환산 경계.
# 💡 [면접 대비 주석]
# 질문: 왜 LiDAR 미터 경계를 area_ratio 경계와 별도로 하드코딩하지 않았나요?
# 답변: compute_heuristic_distance_m()의 공식(0.22/sqrt(area_ratio))을 area_ratio에
# 대해 역산하면 area_ratio = (0.22/meters)^2 이므로, 기존 area_ratio 경계값(0.10/0.08/
# 0.03/0.025)을 그대로 미터로 환산할 수 있다. 두 값을 따로 하드코딩하면 area_ratio
# 경계를 바꿀 때 미터 경계를 깜빡하고 안 바꾸는 정책 드리프트가 생긴다.
def _area_ratio_to_meters(area_ratio: float) -> float:
    return HEURISTIC_COEFFICIENT / sqrt(area_ratio)


LIDAR_NEAR_ENTER_METERS = _area_ratio_to_meters(NEAR_ENTER_AREA_RATIO)  # ≈ 0.696m
LIDAR_NEAR_EXIT_METERS = _area_ratio_to_meters(NEAR_EXIT_AREA_RATIO)  # ≈ 0.778m
LIDAR_MEDIUM_ENTER_METERS = _area_ratio_to_meters(MEDIUM_ENTER_AREA_RATIO)  # ≈ 1.270m
LIDAR_MEDIUM_EXIT_METERS = _area_ratio_to_meters(MEDIUM_EXIT_AREA_RATIO)  # ≈ 1.391m


def zone_from_lidar_meters(meters: float) -> Zone:
    """LiDAR 실측 거리(m)를 area_ratio 경계와 동일한 스케일의 구역으로 변환한다.

    **자문(advisory) 전용 함수다.** `evaluate_distance()`의 route 결정에는 관여하지
    않는다 - `docs/research/lidar_fusion_sequencing_plan.md` §4.2에 따라 실시간 반사/
    인지 라우팅은 여전히 area_ratio(히스테리시스 포함) 단독 기준이며, 이 함수는
    `lidar_distance_validation_samples`의 온디맨드 검증 캡처(거리측정 모드)에서
    "면적비 휴리스틱 구역"과 "LiDAR 구역"을 나란히 비교하는 캘리브레이션 용도로만
    쓰인다. 히스테리시스(진입/이탈 경계 분리)는 상태가 없는 단발 캡처에는 적용할
    근거(이전 프레임)가 없으므로 진입 경계만 사용한다.
    """
    if meters <= LIDAR_NEAR_ENTER_METERS:
        return "near"
    if meters <= LIDAR_MEDIUM_ENTER_METERS:
        return "medium"
    return "far"


# =========================================================================


def evaluate_distance(
    bbox: BBoxLike,
    frame_width: float,
    frame_height: float,
    prev_zone: Zone | None = None,
) -> PolicyResult:
    """bbox 하나에 대한 거리 정책 평가 결과 전체를 계산하는 진입점.

    raw_distance_zone은 override 이전, 히스테리시스만 반영한 값이다.
    effective_distance_zone은 override까지 반영한 최종 라우팅 기준 값이다.
    """
    area_ratio = compute_area_ratio(bbox, frame_width, frame_height)
    bottom_ratio = compute_bottom_ratio(bbox, frame_height)

    raw_zone = apply_hysteresis(prev_zone, area_ratio)
    effective_zone, route_reason = apply_bottom_override(raw_zone, area_ratio, bottom_ratio)

    return PolicyResult(
        raw_distance_zone=raw_zone,
        effective_distance_zone=effective_zone,
        area_ratio=area_ratio,
        bottom_ratio=bottom_ratio,
        heuristic_distance_m=compute_heuristic_distance_m(area_ratio),
        distance_source="bbox_heuristic",
        route=route_for_zone(effective_zone),
        route_reason=route_reason,
    )
