import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection import distance_policy as dp
from server.detection.schemas import BBox


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
