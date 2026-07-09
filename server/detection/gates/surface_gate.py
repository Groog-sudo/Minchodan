import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import ReflexAlert, SurfaceResult

# 2026-07-07 정정: 최초 계획은 crosswalk/manhole/stair/grating/braille_damaged를 별도 클래스로
# 학습하는 것이었으나, 실제 파인튜닝 완료된 Segmentation 모델(segbest.pt)은 이들을 전부 "caution"
# 하나로 통합한 4클래스(sidewalk_normal/caution/roadway/braille_normal)로 확정됐다
# (stage3_detection_design.md §5 참조). 예전 클래스명 그대로 두면 실제 모델 출력과 절대
# 매칭되지 않아 이 게이트가 영구히 발동하지 않는 문제가 있어, 실제 클래스명으로 교체한다.
P0_SURFACE_CLASSES = {
    "caution",  # 계단/맨홀/그레이팅 통합 클래스 - 즉시 물리적 낙상/충돌 위험
}


def surface_gate(
    surface_result: SurfaceResult,
    frame_height: float,
) -> ReflexAlert | None:
    """P0 노면 클래스가 프레임 하단에 검출되면 alert_id를 반환한다."""
    if surface_result.class_name not in P0_SURFACE_CLASSES:
        return None

    centroid_y = surface_result.centroid[1]
    if centroid_y <= frame_height * 0.6:
        return None

    alert_id = f"surface_{surface_result.class_name}"
    return ReflexAlert(
        event_id="",
        alert_id=alert_id,
        direction="front",
        # 클라이언트 번들 자산과 동일 파일명(client/assets/sounds/reflex_clips/).
        clip=f"reflex_clips/{alert_id}.wav",
        haptic=True,
        ts=0.0,
    )
