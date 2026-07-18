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


def compute_heuristic_distance_m(area_ratio: float) -> float:
    """면적비 기반 의사 거리(m)를 계산한다. 실측 거리가 아니라 파생값이다."""
    safe_ratio = max(area_ratio, 1e-6)
    raw_m = HEURISTIC_COEFFICIENT / sqrt(safe_ratio)
    return max(HEURISTIC_MIN_M, min(HEURISTIC_MAX_M, raw_m))


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
