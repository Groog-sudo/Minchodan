import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import SurfaceResult
from server.detection.surface_departure import point_in_polygon

# =========================================================================
# 강사님 추천 알고리즘(Depth Map + 주행 ROI + 위험 픽셀 비율) 저비용 근사 실험.
# 실제 깊이맵/모노큘러 깊이 추정 모델은 도입하지 않고, 이미 있는 세그멘테이션
# 폴리곤을 재사용해 "주행 통로 안에서 위험 노면(roadway/caution)이 차지하는
# 비율"을 point-in-polygon 샘플링으로 근사한다(픽셀 카운트 대신 격자점 카운트).
#
# 사다리꼴 ROI 좌우 대역은 기존 반사 게이트 충돌회랑(FRONT_BAND, direction.py)의
# near/far 값을 그대로 재사용한다 - 새 임계값을 발명하지 않고 이미 튜닝된 값과
# 정합성을 맞추기 위함이다.
# =========================================================================
PATH_ROI_NEAR_BAND = (0.20, 0.80)
PATH_ROI_FAR_BAND = (0.38, 0.62)
PATH_ROI_FAR_Y_RATIO = 0.35  # ROI 상단(가장 먼 지점)의 화면 높이 비율

DANGEROUS_SURFACE_CLASSES = {"roadway", "caution"}

GRID_ROWS = 12
GRID_COLS = 12

# classify_path_risk 임계값 (강사님 추천안의 5%/20% 기준을 그대로 채택)
CAUTION_THRESHOLD = 0.08
BLOCKED_THRESHOLD = 0.20


def _sample_path_roi_points(frame_width: float, frame_height: float) -> list[tuple[float, float]]:
    """사다리꼴 주행 통로 ROI 내부를 균등 격자로 샘플링한다.

    행(y)마다 근/원 대역을 선형보간해 좌우 경계를 구하고 그 범위 안에서만 점을
    뽑는다(바운딩박스 전체를 뽑고 걸러내는 방식보다 샘플 낭비가 없다).
    """
    points = []
    near_lo, near_hi = PATH_ROI_NEAR_BAND
    far_lo, far_hi = PATH_ROI_FAR_BAND
    y_top = frame_height * PATH_ROI_FAR_Y_RATIO
    y_bottom = frame_height

    for row in range(GRID_ROWS):
        row_t = row / max(1, GRID_ROWS - 1)  # 0(맨 위/가장 먼 곳) -> 1(맨 아래/가장 가까운 곳)
        y = y_top + (y_bottom - y_top) * row_t
        x_lo = (far_lo + (near_lo - far_lo) * row_t) * frame_width
        x_hi = (far_hi + (near_hi - far_hi) * row_t) * frame_width
        for col in range(GRID_COLS):
            col_t = col / max(1, GRID_COLS - 1)
            x = x_lo + (x_hi - x_lo) * col_t
            points.append((x, y))
    return points


def compute_path_risk_ratio(
    surfaces: list[SurfaceResult],
    frame_width: float,
    frame_height: float,
) -> float:
    """주행 통로 ROI 샘플 점 중 위험 노면(roadway/caution) 폴리곤 안에 든 비율(0~1)을 반환한다.

    폴리곤이 없는 surfaces(빈 리스트)는 계산에서 제외한다. 위험 폴리곤이 하나도
    없으면 샘플링 없이 즉시 0.0을 반환한다(불필요한 연산 회피).
    """
    if frame_width <= 0 or frame_height <= 0:
        return 0.0

    dangerous_polygons = [
        s.polygon for s in surfaces if s.class_name in DANGEROUS_SURFACE_CLASSES and s.polygon
    ]
    if not dangerous_polygons:
        return 0.0

    sample_points = _sample_path_roi_points(frame_width, frame_height)
    hits = sum(
        1
        for point in sample_points
        if any(point_in_polygon(point, polygon) for polygon in dangerous_polygons)
    )
    return hits / len(sample_points)


def classify_path_risk(ratio: float) -> str:
    """강사님 추천안의 임계값(5%/20%)을 그대로 채택한 3단계 판정."""
    if ratio >= BLOCKED_THRESHOLD:
        return "BLOCKED"
    if ratio >= CAUTION_THRESHOLD:
        return "CAUTION"
    return "CLEAR"
