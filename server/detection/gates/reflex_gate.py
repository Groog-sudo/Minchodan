import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.direction import estimate_direction
from server.detection.schemas import Detection, ReflexAlert

# =========================================================================
# 👨‍💻 담당자 직접 코딩 영역 시작: 1. 위험 사물 및 거리 임계치 정의 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 29개 클래스를 모두 학습시켰는데 왜 5개만 Reflex Gate로 분기했나요?
# 답변: 29개 사물을 전부 즉시 햅틱(Reflex)으로 울리면 피로도 때문에 실사용이 불가능합니다.
# 따라서 시각장애인에게 가장 치명적인 동적 객체 5종만 1차 필터링하여 즉각적인 햅틱 경보로 빼고,
# 나머지는 6단계 인지 경로(LangGraph, RAG)로 넘겨 상세 음성 가이드로 제공하도록 물리적 이중 분기를 설계했습니다.
#
# 2026-07-07 실내 오탐 완화 추가: AI Hub 학습 데이터가 전부 실외(한국 인도) 이미지라
# 모델이 실내 환경을 미학습 도메인으로 취급해, 실내에서 car/bus 등이 종종 오탐된다.
# 두 가지 방어선을 추가한다.
#   (1) 클래스별 최소 confidence - 실내 오탐이 잦은 차량류는 문턱을 0.5~0.6대로 올림.
#   (2) 최소 연속 프레임 수(hit_count) - ByteTrack이 같은 track_id를 N프레임 연속
#       유지해야만 발동. 실외의 진짜 차량은 어차피 여러 프레임 지속되므로 반응 속도
#       손해가 적고, 실내에서 한 프레임만 튀는 오탐은 이 조건에서 걸러진다.
# =========================================================================
# 시각장애인에게 가장 치명적인 동적/돌발 장애물 클래스와 클래스별 최소 confidence.
HIGH_RISK_CLASSES: dict[str, float] = {
    "barricade": 0.35,
    "bench": 0.3,
    "bicycle": 0.3,
    "bollard": 0.3,
    "bus": 0.35,
    "car": 0.35,
    "carrier": 0.3,
    "cat": 0.3,
    "chair": 0.3,
    "dog": 0.3,
    "fire_hydrant": 0.35,
    "kiosk": 0.3,
    "motorcycle": 0.35,
    "movable_signage": 0.3,
    "parking_meter": 0.35,
    "person": 0.3,
    "pole": 0.3,
    "potted_plant": 0.3,
    "power_controller": 0.3,
    "scooter": 0.3,
    "stop": 0.35,
    "stroller": 0.3,
    "table": 0.3,
    "traffic_light": 0.35,
    "traffic_light_controller": 0.35,
    "traffic_sign": 0.35,
    "tree_trunk": 0.3,
    "truck": 0.35,
    "wheelchair": 0.3,
}
# 화면 하단(발밑) 접근 임계치 (하단 15% 영역)
PROXIMITY_THRESHOLD = 0.15
# 동일 track_id가 최소 이만큼 연속 프레임 유지되어야 반사 경보를 발동한다.
MIN_HIT_COUNT = 3
# =========================================================================


def reflex_gate(
    detection: Detection,
    frame_height: float,
    frame_width: float,
) -> ReflexAlert | None:
    # =========================================================================
    # 👨‍💻 담당자 직접 코딩 영역 시작: 2. 위험도 필터링 및 거리 판별 👨‍💻
    # 💡 [면접 대비 주석]
    # 질문: 시각장애인에게 사물의 위치와 거리를 어떻게 직관적으로 전달했나요?
    # 답변: 단순히 사물이 있다는 것을 넘어, BBox의 X좌표를 기준으로 -1.0~1.0 사이의
    #       Panning(입체음향 밸런스) 값을 도출해 해당 방향에서 소리가 나도록 했습니다.
    #       또한, BBox의 하단(bottom_y)이 프레임 맨 밑바닥에 가까울수록 거리를 역산하여,
    #       자동차 주차 센서처럼 거리가 가까워질수록 비프음이 급격히 빨라지고 진동이 강해지게 연산 로직을 직접 짰습니다.
    # =========================================================================
    # 1. 감지된 사물이 HIGH_RISK_CLASSES에 없으면 통과(None 반환)
    min_confidence = HIGH_RISK_CLASSES.get(detection.class_name)
    if min_confidence is None:
        return None

    # 1-1. 클래스별 최소 confidence 미달 시 통과 (실내 오탐 완화)
    if detection.confidence < min_confidence:
        return None

    # 2. [2026-07-14] 끊임없는 비프음 방지 및 큐 지연 해소를 위한 직접 충돌 위험 객체 필터
    # 조건 A: 사물의 바닥(bottom_y)이 화면 최하단 5% 영역 안으로 들어왔는가 (극도 인접)
    bottom_y = detection.bbox.y + detection.bbox.h
    is_very_close = bottom_y > frame_height * 0.95 if frame_height > 0 else True

    # 조건 B: 사물의 중심(center_x)이 좌우 30% 여백을 제외한 중앙 40% 영역 내에 있는가 (정면 충돌 회랑)
    center_x = detection.bbox.x + detection.bbox.w / 2
    is_centered = (frame_width * 0.3) <= center_x <= (frame_width * 0.7) if frame_width > 0 else True

    # 두 조건 중 하나라도 충족되지 않으면 즉각 반사(정지)에서 제외
    if not (is_very_close and is_centered):
        return None
    # =========================================================================

    direction = estimate_direction(detection.bbox, frame_width, distance_class="near")
    alert_id = f"high_{detection.class_name}_{direction}"

    # 1. Panning 계산: center_x 위치 기준 -1.0(좌) ~ 1.0(우)
    center_x = detection.bbox.x + detection.bbox.w / 2
    panning = (center_x / frame_width) * 2 - 1.0
    panning = max(-1.0, min(1.0, panning))

    # 2. Distance 계산: 화면 전체(bottom_y: 0 ~ frame_height)에 따른 거리 역산 (0.4m ~ 1.5m 매핑)
    ratio = bottom_y / frame_height if frame_height > 0 else 1.0
    ratio = max(0.0, min(1.0, ratio))

    # ratio가 1.0일수록 최하단에 인접해있으므로 거리(distance)는 짧아짐 (1.5m -> 0.4m)
    distance = 1.5 - (ratio * 1.1)
    distance = max(0.4, min(1.5, distance))

    # 3. 거리 기준 비프음 간격 및 햅틱 패턴 매핑
    if distance <= 0.5:
        beep_interval_ms = 0
        haptic_pattern = "continuous"
    elif distance <= 1.0:
        beep_interval_ms = 100
        haptic_pattern = "continuous"
    elif distance <= 1.5:
        beep_interval_ms = 250
        haptic_pattern = "double"
    else:
        beep_interval_ms = 500
        haptic_pattern = "short"

    return ReflexAlert(
        event_id="",
        alert_id=alert_id,
        direction=direction,
        # 클라이언트가 client/assets/sounds/reflex_clips/에 동일 파일명으로 번들 재생한다.
        # (2026-07-09: mp3 인코더 없이 macOS say로 생성 가능한 wav로 확정)
        clip=f"reflex_clips/high_{direction}.wav",
        haptic=True,
        panning=panning,
        distance=round(distance, 2),
        beep_interval_ms=beep_interval_ms,
        haptic_pattern=haptic_pattern,
        ts=0.0,
        # 2026-07-14 추가: 관제 콘솔 발화 추적용 객체 정보 전달.
        track_id=detection.track_id,
        class_name=detection.class_name,
        hit_count=detection.hit_count,
    )
