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
# =========================================================================
# 시각장애인에게 가장 치명적인 동적/돌발 장애물 클래스를 Set으로 선언합니다.
HIGH_RISK_CLASSES = {
    "car",
    "truck",
    "bus",
    "motorcycle",
    "scooter",
}
# 화면 하단(발밑) 접근 임계치 (하단 15% 영역)
PROXIMITY_THRESHOLD = 0.15
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
    if detection.class_name not in HIGH_RISK_CLASSES:
        return None

    # 2. 사물의 바닥(bottom_y)이 화면 하단 15% 영역 안으로 들어왔는지 확인
    bottom_y = detection.bbox.y + detection.bbox.h
    if bottom_y <= frame_height * (1 - PROXIMITY_THRESHOLD):
        return None
    # =========================================================================

    direction = estimate_direction(detection.bbox, frame_width, distance_class="near")
    alert_id = f"high_{detection.class_name}_{direction}"

    # 1. Panning 계산: center_x 위치 기준 -1.0(좌) ~ 1.0(우)
    center_x = detection.bbox.x + detection.bbox.w / 2
    panning = (center_x / frame_width) * 2 - 1.0
    panning = max(-1.0, min(1.0, panning))

    # 2. Distance 계산: 하단 경계부 밀착 정도에 따른 거리 역산 (0.4m ~ 1.5m 매핑)
    # PROXIMITY_THRESHOLD는 0.15이므로 bottom_y가 frame_height * 0.85 ~ 1.0 범위에 속함
    min_gate_y = frame_height * (1 - PROXIMITY_THRESHOLD)
    range_y = frame_height * PROXIMITY_THRESHOLD
    ratio = (bottom_y - min_gate_y) / range_y if range_y > 0 else 1.0
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
        clip=f"reflex_clips/high_{direction}.mp3",
        haptic=True,
        panning=panning,
        distance=round(distance, 2),
        beep_interval_ms=beep_interval_ms,
        haptic_pattern=haptic_pattern,
        ts=0.0,
    )
