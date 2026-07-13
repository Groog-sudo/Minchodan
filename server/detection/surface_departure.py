import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import SurfaceResult

# =========================================================================
# 👨‍💻 HARD CODE 영역 시작: 보도 이탈 1차 판정 (point-in-polygon) 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 왜 centroid 비교(surface_gate 방식)가 아니라 point-in-polygon을 새로 썼나요?
# 답변: surface_gate는 "위험 노면이 화면 하단에 존재하는가"만 보는 존재 기반 판정이라
# caution 클래스 전용으로는 충분하지만, "사용자가 지금 차도를 밟았는가"는 사용자 위치
# 기준점이 실제 폴리곤 경계 안에 들어왔는지를 기하학적으로 봐야 한다. YOLO segmentation은
# 폴리곤(mask.xy)을 그대로 주므로, 별도 라이브러리 없이 레이캐스팅(ray casting) 짝/홀
# 규칙만으로 점-폴리곤 포함 여부를 O(n) (n=폴리곤 꼭짓점 수)에 판정할 수 있다.
# =========================================================================

# 사용자 발밑 근사 기준점(정규화 좌표). client/src/components/CameraView.tsx의
# DEPTH_PROBE_POINTS "발밑" 지점(0.5, 0.9)과 동일한 관례를 서버 판정에도 맞춘다.
REFERENCE_POINT_X_RATIO = 0.5
REFERENCE_POINT_Y_RATIO = 0.9

# 이 두 클래스의 폴리곤 안에 기준점이 들어오면 "이탈"로 본다.
# roadway: 차도 자체. caution: 계단/맨홀/그레이팅 통합 위험 구간(surface_gate.py와 동일 근거).
DEPARTURE_SURFACE_CLASSES = {"roadway", "caution"}


def point_in_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    """레이캐스팅(ray casting) 알고리즘으로 점이 폴리곤 내부에 있는지 판정한다.

    점에서 오른쪽으로 무한히 뻗는 반직선이 폴리곤 변과 몇 번 교차하는지 세어,
    홀수면 내부, 짝수면 외부로 판정하는 짝/홀 규칙(even-odd rule)이다.
    """
    if len(polygon) < 3:
        return False

    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        # (yi > y) != (yj > y): 변이 point의 y높이를 위아래로 가로지르는 변만 검사한다.
        if (yi > y) != (yj > y):
            # 그 변이 point의 y높이를 지나는 x좌표를 구해 point.x보다 오른쪽이면 교차로 센다.
            x_intersect = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_intersect:
                inside = not inside
        j = i
    return inside


def check_sidewalk_departure(
    surfaces: list[SurfaceResult],
    frame_width: float,
    frame_height: float,
) -> bool:
    """사용자 발밑 근사 기준점이 차도/위험 노면 폴리곤 안에 있으면 True를 반환한다."""
    reference_point = (
        frame_width * REFERENCE_POINT_X_RATIO,
        frame_height * REFERENCE_POINT_Y_RATIO,
    )
    for surf in surfaces:
        if surf.class_name not in DEPARTURE_SURFACE_CLASSES:
            continue
        if not surf.polygon:
            continue
        if point_in_polygon(reference_point, surf.polygon):
            return True
    return False


# =========================================================================
# 👨‍💻 HARD CODE 영역 끝
# =========================================================================

# =========================================================================
# 👨‍💻 HARD CODE 영역 시작: 점자블록 추종 방향 계산 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 점자블록 "추종"을 왜 폴리곤 전체 centroid가 아니라 기준점과 같은 높이(y)의
# 가로 교차 구간으로 계산했나요?
# 답변: 점자블록은 보도를 따라 길게 뻗은 좁은 띠 모양이라, 폴리곤 전체의 무게중심(centroid)은
# 카메라가 위/아래를 보는 각도에 따라 좌우로 크게 흔들린다(원근 때문에 먼 쪽 점자블록이
# 화면 위쪽에서 좁게 보이는 왜곡이 포함됨). 대신 point_in_polygon과 같은 레이캐스팅
# 원리로 "기준점과 같은 높이(y)에서 폴리곤 변들이 x축을 가로지르는 지점"만 모아
# 그 구간의 중점을 쓰면, 지금 발을 딛는 바로 그 높이에서 점자블록이 화면 어디에 있는지를
# 원근 왜곡 없이 알 수 있다.
# =========================================================================

# 점자블록이 기준점 x좌표에서 이 비율(프레임 너비 기준) 이상 벗어나야 방향 보정을 낸다.
# 너무 작으면 세그멘테이션 경계 노이즈로 좌우 안내가 자주 뒤집힌다(플리커 방지 여유값).
BRAILLE_FOLLOW_MARGIN_RATIO = 0.05


def polygon_x_crossings_at_y(polygon: list[list[float]], y: float) -> list[float]:
    """폴리곤 변들이 높이 y를 가로지르는 지점의 x좌표 목록을 반환한다(레이캐스팅과 동일 원리)."""
    if len(polygon) < 3:
        return []

    crossings: list[float] = []
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            x_intersect = (xj - xi) * (y - yi) / (yj - yi) + xi
            crossings.append(x_intersect)
        j = i
    return crossings


def braille_follow_direction(
    surfaces: list[SurfaceResult],
    frame_width: float,
    frame_height: float,
) -> str | None:
    """기준점 높이에서 점자블록(braille_normal) 위치를 보고 "left"/"right"/"center" 보정 방향을 낸다.

    점자블록이 화면에 안 보이면(교차 구간 없음) None을 반환해 "판단 불가"를 구분한다.
    """
    reference_x = frame_width * REFERENCE_POINT_X_RATIO
    reference_y = frame_height * REFERENCE_POINT_Y_RATIO
    margin = frame_width * BRAILLE_FOLLOW_MARGIN_RATIO

    all_crossings: list[float] = []
    for surf in surfaces:
        if surf.class_name != "braille_normal":
            continue
        if not surf.polygon:
            continue
        all_crossings.extend(polygon_x_crossings_at_y(surf.polygon, reference_y))

    if not all_crossings:
        return None

    braille_center_x = (min(all_crossings) + max(all_crossings)) / 2.0

    if braille_center_x < reference_x - margin:
        return "left"
    if braille_center_x > reference_x + margin:
        return "right"
    return "center"


# =========================================================================
# 👨‍💻 HARD CODE 영역 끝
# =========================================================================
