"""
tests/test_path_risk.py
"주행 통로 위험 비율" 실험(2026-07-13, 강사님 추천 Depth+ROI 알고리즘의 저비용 근사) 단위 테스트.
새 깊이 모델 없이 기존 세그멘테이션 폴리곤을 point-in-polygon 샘플링으로 재사용하는지 검증한다.
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from server.detection.path_risk import (
    BLOCKED_THRESHOLD,
    CAUTION_THRESHOLD,
    classify_path_risk,
    compute_path_risk_ratio,
)
from server.detection.schemas import SurfaceResult

FRAME_W = 640.0
FRAME_H = 640.0

# ROI 전체(근/원 대역 전부)를 넉넉히 덮는 사각형. 상하 여유를 둬서(y=200~700) ROI
# 경계(y=224~640)의 샘플 점이 폴리곤 변과 정확히 겹치는 경계 케이스를 피한다
# (point_in_polygon의 레이캐스팅은 변 위의 점 판정이 불안정할 수 있음).
FULL_COVER_ROADWAY = [[0.0, 200.0], [640.0, 200.0], [640.0, 700.0], [0.0, 700.0]]
# ROI 좌측 최소 경계(근접 대역 기준 x=128)보다도 왼쪽에 있는 세로 띠 - ROI와 전혀 안 겹침
NO_OVERLAP_STRIP = [[0.0, 0.0], [50.0, 0.0], [50.0, 640.0], [0.0, 640.0]]
# ROI 우측 절반만 덮는 사각형(대략 절반 정도 겹침을 기대)
RIGHT_HALF_COVER = [[320.0, 200.0], [640.0, 200.0], [640.0, 700.0], [320.0, 700.0]]


def test_no_surfaces_returns_zero():
    assert compute_path_risk_ratio([], FRAME_W, FRAME_H) == 0.0


def test_only_safe_surface_returns_zero():
    surfaces = [
        SurfaceResult(
            class_name="sidewalk_normal", centroid=[320.0, 400.0], polygon=FULL_COVER_ROADWAY
        )
    ]
    assert compute_path_risk_ratio(surfaces, FRAME_W, FRAME_H) == 0.0


def test_dangerous_surface_without_polygon_is_ignored():
    surfaces = [SurfaceResult(class_name="roadway", centroid=[320.0, 400.0], polygon=[])]
    assert compute_path_risk_ratio(surfaces, FRAME_W, FRAME_H) == 0.0


def test_full_coverage_gives_ratio_near_one():
    surfaces = [
        SurfaceResult(class_name="roadway", centroid=[320.0, 400.0], polygon=FULL_COVER_ROADWAY)
    ]
    ratio = compute_path_risk_ratio(surfaces, FRAME_W, FRAME_H)
    assert ratio == 1.0


def test_no_overlap_gives_ratio_zero():
    surfaces = [
        SurfaceResult(class_name="caution", centroid=[25.0, 400.0], polygon=NO_OVERLAP_STRIP)
    ]
    assert compute_path_risk_ratio(surfaces, FRAME_W, FRAME_H) == 0.0


def test_partial_coverage_gives_intermediate_ratio():
    surfaces = [
        SurfaceResult(class_name="roadway", centroid=[480.0, 400.0], polygon=RIGHT_HALF_COVER)
    ]
    ratio = compute_path_risk_ratio(surfaces, FRAME_W, FRAME_H)
    assert 0.2 < ratio < 0.8


def test_zero_frame_dimensions_return_zero():
    surfaces = [
        SurfaceResult(class_name="roadway", centroid=[320.0, 400.0], polygon=FULL_COVER_ROADWAY)
    ]
    assert compute_path_risk_ratio(surfaces, 0.0, FRAME_H) == 0.0
    assert compute_path_risk_ratio(surfaces, FRAME_W, 0.0) == 0.0


def test_classify_path_risk_thresholds():
    assert classify_path_risk(0.0) == "CLEAR"
    assert classify_path_risk(CAUTION_THRESHOLD - 0.01) == "CLEAR"
    assert classify_path_risk(CAUTION_THRESHOLD) == "CAUTION"
    assert classify_path_risk(BLOCKED_THRESHOLD - 0.01) == "CAUTION"
    assert classify_path_risk(BLOCKED_THRESHOLD) == "BLOCKED"
    assert classify_path_risk(1.0) == "BLOCKED"
