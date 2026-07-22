"""
tests/test_surface_departure.py
보도 이탈 1차 판정(point-in-polygon) 단위 테스트.
합성 사각형 폴리곤으로 point_in_polygon과 check_sidewalk_departure의 in/out 케이스를 검증한다.
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from server.detection.schemas import SurfaceResult
from server.detection.surface_departure import (
    REFERENCE_POINT_X_RATIO,
    REFERENCE_POINT_Y_RATIO,
    braille_follow_direction,
    check_sidewalk_departure,
    point_in_polygon,
    polygon_x_crossings_at_y,
)

# 640x640 프레임 기준 화면 하단 절반을 덮는 정사각형 폴리곤(차도를 가정).
ROADWAY_SQUARE = [[100.0, 400.0], [540.0, 400.0], [540.0, 640.0], [100.0, 640.0]]

# 화면 상단 절반만 덮는 정사각형(보도를 가정, 기준점과 겹치지 않아야 함).
SIDEWALK_SQUARE_TOP_ONLY = [[100.0, 0.0], [540.0, 0.0], [540.0, 200.0], [100.0, 200.0]]

# 기준점(320, 576) 높이를 세로로 관통하는 좁은 띠 폴리곤들(점자블록 가정).
# 왼쪽 띠: 중심 x=140, 오른쪽 띠: 중심 x=500, 가운데 띠: 중심 x=320(기준점과 동일).
BRAILLE_STRIP_LEFT = [[100.0, 0.0], [180.0, 0.0], [180.0, 640.0], [100.0, 640.0]]
BRAILLE_STRIP_RIGHT = [[460.0, 0.0], [540.0, 0.0], [540.0, 640.0], [460.0, 640.0]]
BRAILLE_STRIP_CENTER = [[280.0, 0.0], [360.0, 0.0], [360.0, 640.0], [280.0, 640.0]]


def test_point_in_polygon_inside():
    assert point_in_polygon((320.0, 500.0), ROADWAY_SQUARE) is True


def test_point_in_polygon_outside():
    assert point_in_polygon((320.0, 100.0), ROADWAY_SQUARE) is False


def test_point_in_polygon_boundary_case_degenerate():
    # 꼭짓점이 3개 미만이면 폴리곤으로 볼 수 없으므로 False.
    assert point_in_polygon((10.0, 10.0), [[0.0, 0.0], [1.0, 1.0]]) is False


def test_point_in_polygon_empty_polygon():
    assert point_in_polygon((10.0, 10.0), []) is False


def test_check_sidewalk_departure_true_when_roadway_covers_reference_point():
    surfaces = [
        SurfaceResult(class_name="roadway", centroid=[320.0, 520.0], polygon=ROADWAY_SQUARE),
    ]
    assert check_sidewalk_departure(surfaces, frame_width=640.0, frame_height=640.0) is True


def test_check_sidewalk_departure_false_when_only_sidewalk_present():
    surfaces = [
        SurfaceResult(
            class_name="sidewalk_normal", centroid=[320.0, 100.0], polygon=SIDEWALK_SQUARE_TOP_ONLY
        ),
    ]
    assert check_sidewalk_departure(surfaces, frame_width=640.0, frame_height=640.0) is False


def test_check_sidewalk_departure_false_when_roadway_far_from_reference_point():
    # roadway 클래스지만 기준점(화면 하단 중앙)과 겹치지 않는 상단 폴리곤.
    surfaces = [
        SurfaceResult(
            class_name="roadway", centroid=[320.0, 100.0], polygon=SIDEWALK_SQUARE_TOP_ONLY
        ),
    ]
    assert check_sidewalk_departure(surfaces, frame_width=640.0, frame_height=640.0) is False


def test_check_sidewalk_departure_ignores_non_departure_classes():
    surfaces = [
        SurfaceResult(class_name="braille_normal", centroid=[320.0, 520.0], polygon=ROADWAY_SQUARE),
    ]
    assert check_sidewalk_departure(surfaces, frame_width=640.0, frame_height=640.0) is False


def test_check_sidewalk_departure_empty_surfaces():
    assert check_sidewalk_departure([], frame_width=640.0, frame_height=640.0) is False


def test_check_sidewalk_departure_ignores_surface_without_polygon():
    # polygon이 채워지지 않은(레거시/실패) SurfaceResult는 판정에서 제외되어야 한다.
    surfaces = [
        SurfaceResult(class_name="roadway", centroid=[320.0, 520.0], polygon=[]),
    ]
    assert check_sidewalk_departure(surfaces, frame_width=640.0, frame_height=640.0) is False


def test_reference_point_ratio_matches_client_depth_probe_convention():
    # client/src/components/CameraView.tsx DEPTH_PROBE_POINTS "발밑" 지점(0.5, 0.9)과 일치해야 한다.
    assert REFERENCE_POINT_X_RATIO == 0.5
    assert REFERENCE_POINT_Y_RATIO == 0.9


def test_surface_result_polygon_excluded_from_serialization():
    # polygon은 서버 내부 전용 필드라 model_dump 시 항상 빠져야 한다(네트워크 비용 없음 보장).
    surf = SurfaceResult(class_name="roadway", centroid=[1.0, 2.0], polygon=ROADWAY_SQUARE)
    dumped = surf.model_dump()
    assert "polygon" not in dumped


def test_polygon_x_crossings_at_y_returns_both_edges():
    crossings = polygon_x_crossings_at_y(BRAILLE_STRIP_LEFT, y=576.0)
    assert sorted(crossings) == [100.0, 180.0]


def test_polygon_x_crossings_at_y_outside_range_returns_empty():
    assert polygon_x_crossings_at_y(BRAILLE_STRIP_LEFT, y=-10.0) == []


def test_braille_follow_direction_left():
    surfaces = [
        SurfaceResult(
            class_name="braille_normal", centroid=[140.0, 320.0], polygon=BRAILLE_STRIP_LEFT
        ),
    ]
    assert braille_follow_direction(surfaces, frame_width=640.0, frame_height=640.0) == "left"


def test_braille_follow_direction_right():
    surfaces = [
        SurfaceResult(
            class_name="braille_normal", centroid=[500.0, 320.0], polygon=BRAILLE_STRIP_RIGHT
        ),
    ]
    assert braille_follow_direction(surfaces, frame_width=640.0, frame_height=640.0) == "right"


def test_braille_follow_direction_center_within_margin():
    surfaces = [
        SurfaceResult(
            class_name="braille_normal", centroid=[320.0, 320.0], polygon=BRAILLE_STRIP_CENTER
        ),
    ]
    assert braille_follow_direction(surfaces, frame_width=640.0, frame_height=640.0) == "center"


def test_braille_follow_direction_none_when_not_visible():
    surfaces = [
        SurfaceResult(class_name="roadway", centroid=[320.0, 520.0], polygon=ROADWAY_SQUARE),
    ]
    assert braille_follow_direction(surfaces, frame_width=640.0, frame_height=640.0) is None


def test_braille_follow_direction_empty_surfaces():
    assert braille_follow_direction([], frame_width=640.0, frame_height=640.0) is None
