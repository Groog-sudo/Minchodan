import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dataclasses import dataclass

from server.detection import distance_policy as dp
from server.detection.schemas import BBox


@dataclass
class _FakeDetection:
    """select_primary_detection() 우선순위 로직만 검증하기 위한 최소 스텁."""

    class_name: str
    confidence: float
    bbox: BBox
    effective_distance_zone: str
    heuristic_distance_m: float


def test_clip_bbox_to_frame_clips_out_of_bounds():
    bbox = BBox(x=-10, y=-10, w=50, h=50)
    x, y, w, h = dp.clip_bbox_to_frame(bbox, frame_width=100, frame_height=100)
    assert x == 0.0
    assert y == 0.0
    assert w == 40.0
    assert h == 40.0


def test_clip_bbox_to_frame_zero_frame_returns_zero():
    bbox = BBox(x=0, y=0, w=10, h=10)
    assert dp.clip_bbox_to_frame(bbox, frame_width=0, frame_height=100) == (0.0, 0.0, 0.0, 0.0)


def test_compute_area_ratio_full_frame_bbox_is_one():
    bbox = BBox(x=0, y=0, w=100, h=100)
    assert dp.compute_area_ratio(bbox, frame_width=100, frame_height=100) == 1.0


def test_compute_bottom_ratio_bottom_edge():
    bbox = BBox(x=0, y=90, w=10, h=10)
    assert dp.compute_bottom_ratio(bbox, frame_height=100) == 1.0


def test_raw_zone_from_area_ratio_boundaries():
    assert dp.raw_zone_from_area_ratio(0.10) == "near"
    assert dp.raw_zone_from_area_ratio(0.099) == "medium"
    assert dp.raw_zone_from_area_ratio(0.03) == "medium"
    assert dp.raw_zone_from_area_ratio(0.0299) == "far"


def test_apply_hysteresis_no_prior_state_uses_raw_zone():
    assert dp.apply_hysteresis(None, 0.15) == "near"
    assert dp.apply_hysteresis(None, 0.05) == "medium"
    assert dp.apply_hysteresis(None, 0.01) == "far"


def test_apply_hysteresis_near_stays_until_exit_threshold():
    assert dp.apply_hysteresis("near", 0.09) == "near"
    assert dp.apply_hysteresis("near", 0.08) == "near"
    assert dp.apply_hysteresis("near", 0.079) == "medium"


def test_apply_hysteresis_medium_transitions():
    assert dp.apply_hysteresis("medium", 0.10) == "near"
    assert dp.apply_hysteresis("medium", 0.05) == "medium"
    assert dp.apply_hysteresis("medium", 0.025) == "medium"
    assert dp.apply_hysteresis("medium", 0.024) == "far"


def test_apply_hysteresis_far_transitions():
    assert dp.apply_hysteresis("far", 0.03) == "medium"
    assert dp.apply_hysteresis("far", 0.029) == "far"


def test_apply_bottom_override_promotes_small_bottom_object():
    zone, reason = dp.apply_bottom_override("far", area_ratio=0.045, bottom_ratio=0.85)
    assert zone == "near"
    assert reason == "bottom_close_override"


def test_apply_bottom_override_ignores_small_area_below_threshold():
    zone, reason = dp.apply_bottom_override("medium", area_ratio=0.02, bottom_ratio=0.95)
    assert zone == "medium"
    assert reason == "zone_medium"


def test_apply_bottom_override_ignores_when_not_at_bottom():
    zone, reason = dp.apply_bottom_override("far", area_ratio=0.05, bottom_ratio=0.5)
    assert zone == "far"
    assert reason == "zone_far"


def test_apply_bottom_override_noop_when_already_near():
    zone, reason = dp.apply_bottom_override("near", area_ratio=0.5, bottom_ratio=0.9)
    assert zone == "near"
    assert reason == "zone_near"


def test_route_for_zone():
    assert dp.route_for_zone("near") == "reflex"
    assert dp.route_for_zone("medium") == "cognitive"
    assert dp.route_for_zone("far") == "cognitive"


def test_compute_heuristic_distance_m_matches_formula():
    # area_ratio = 0.22^2 = 0.0484 -> 0.22 / sqrt(0.0484) == 1.0m
    assert dp.compute_heuristic_distance_m(0.0484) == 1.0


def test_compute_heuristic_distance_m_clamped_to_bounds():
    assert dp.compute_heuristic_distance_m(10.0) == dp.HEURISTIC_MIN_M
    assert dp.compute_heuristic_distance_m(1e-9) == dp.HEURISTIC_MAX_M


def test_evaluate_distance_near_bbox_routes_reflex():
    bbox = BBox(x=30, y=30, w=40, h=40)  # area_ratio = 0.16
    result = dp.evaluate_distance(bbox, frame_width=100, frame_height=100)
    assert result.effective_distance_zone == "near"
    assert result.route == "reflex"
    assert result.policy_version == dp.POLICY_VERSION
    assert result.distance_source == "bbox_heuristic"


def test_evaluate_distance_far_bbox_routes_cognitive():
    bbox = BBox(x=48, y=48, w=4, h=4)  # area_ratio = 0.0016
    result = dp.evaluate_distance(bbox, frame_width=100, frame_height=100)
    assert result.effective_distance_zone == "far"
    assert result.route == "cognitive"


def test_evaluate_distance_applies_prev_zone_hysteresis():
    # area_ratio == 0.09 -> raw zone medium without history, but stays near with prior state.
    bbox = BBox(x=25, y=25, w=30, h=30)  # area_ratio = 0.09
    result = dp.evaluate_distance(bbox, frame_width=100, frame_height=100, prev_zone="near")
    assert result.raw_distance_zone == "near"
    assert result.effective_distance_zone == "near"


def test_evaluate_distance_bottom_override_reason_surfaces():
    bbox = BBox(x=35, y=85, w=30, h=15)  # area_ratio = 0.045, bottom_ratio = 1.0
    result = dp.evaluate_distance(bbox, frame_width=100, frame_height=100)
    assert result.effective_distance_zone == "near"
    assert result.route_reason == "bottom_close_override"


def test_lidar_meter_boundaries_derived_from_area_ratio_boundaries():
    # meters = coefficient / sqrt(area_ratio) 역산이므로 area_ratio가 클수록(가까울수록)
    # 미터 경계는 작다. near_enter(0.10)가 near_exit(0.08)보다 더 가까운 미터여야 한다.
    assert dp.LIDAR_NEAR_ENTER_METERS < dp.LIDAR_NEAR_EXIT_METERS
    assert dp.LIDAR_NEAR_EXIT_METERS < dp.LIDAR_MEDIUM_ENTER_METERS
    assert dp.LIDAR_MEDIUM_ENTER_METERS < dp.LIDAR_MEDIUM_EXIT_METERS
    assert dp.compute_heuristic_distance_m(dp.NEAR_ENTER_AREA_RATIO) == dp.LIDAR_NEAR_ENTER_METERS


def test_zone_from_lidar_meters_near():
    assert dp.zone_from_lidar_meters(0.5) == "near"
    assert dp.zone_from_lidar_meters(dp.LIDAR_NEAR_ENTER_METERS) == "near"


def test_zone_from_lidar_meters_medium():
    assert dp.zone_from_lidar_meters(1.0) == "medium"
    assert dp.zone_from_lidar_meters(dp.LIDAR_MEDIUM_ENTER_METERS) == "medium"


def test_zone_from_lidar_meters_far():
    assert dp.zone_from_lidar_meters(2.0) == "far"
    assert dp.zone_from_lidar_meters(3.0) == "far"


class TestSelectPrimaryDetection:
    """2026-07-20: confidence 최댓값 대신 거리 구역/실측 거리/12시 회랑 근접도 기준
    주위험 객체 선정. 실기기 로그(자동차+사람+트럭 동시 탐지 시 confidence 흔들림으로
    안내 대상이 프레임마다 바뀌는 문제) 회귀 방지."""

    def test_empty_list_returns_none(self):
        assert dp.select_primary_detection([], frame_width=640.0) is None

    def test_single_detection_returned(self):
        det = _FakeDetection(
            class_name="car",
            confidence=0.5,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="medium",
            heuristic_distance_m=1.0,
        )
        assert dp.select_primary_detection([det], frame_width=640.0) is det

    def test_near_beats_medium_even_with_lower_confidence(self):
        """실기기 로그 재현: confidence 낮은 near 객체가 confidence 높은 medium
        객체보다 우선해야 한다(거리가 confidence보다 우선)."""
        near_low_conf = _FakeDetection(
            class_name="car",
            confidence=0.55,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="near",
            heuristic_distance_m=0.8,
        )
        medium_high_conf = _FakeDetection(
            class_name="person",
            confidence=0.95,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="medium",
            heuristic_distance_m=2.0,
        )
        result = dp.select_primary_detection([medium_high_conf, near_low_conf], frame_width=640.0)
        assert result is near_low_conf

    def test_same_zone_closer_distance_wins(self):
        far_in_zone = _FakeDetection(
            class_name="truck",
            confidence=0.9,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="medium",
            heuristic_distance_m=1.8,
        )
        near_in_zone = _FakeDetection(
            class_name="car",
            confidence=0.5,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="medium",
            heuristic_distance_m=1.0,
        )
        result = dp.select_primary_detection([far_in_zone, near_in_zone], frame_width=640.0)
        assert result is near_in_zone

    def test_same_zone_same_distance_corridor_center_wins(self):
        off_center = _FakeDetection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=550, y=0, w=40, h=40),  # center_x=570/640≈0.89, 회랑 밖
            effective_distance_zone="medium",
            heuristic_distance_m=1.0,
        )
        centered = _FakeDetection(
            class_name="person",
            confidence=0.5,
            bbox=BBox(x=300, y=0, w=40, h=40),  # center_x=320/640=0.5, 정중앙
            effective_distance_zone="medium",
            heuristic_distance_m=1.0,
        )
        result = dp.select_primary_detection([off_center, centered], frame_width=640.0)
        assert result is centered

    def test_full_tie_breaks_by_confidence(self):
        low_conf = _FakeDetection(
            class_name="car",
            confidence=0.4,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="medium",
            heuristic_distance_m=1.0,
        )
        high_conf = _FakeDetection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="medium",
            heuristic_distance_m=1.0,
        )
        result = dp.select_primary_detection([low_conf, high_conf], frame_width=640.0)
        assert result is high_conf

    def test_zero_frame_width_treats_all_as_off_corridor(self):
        det = _FakeDetection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=300, y=0, w=40, h=40),
            effective_distance_zone="medium",
            heuristic_distance_m=1.0,
        )
        # frame_width<=0이어도 예외 없이 동작해야 한다(단일 후보이므로 그대로 반환).
        assert dp.select_primary_detection([det], frame_width=0.0) is det
