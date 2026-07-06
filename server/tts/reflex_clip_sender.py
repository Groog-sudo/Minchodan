import logging
import sys
import time
from typing import Optional

from server.api.session_manager import manager
from server.tts.suppressor import Alert_suppressor

logger = logging.getLogger(__name__) # logger 객체 생성

# ============================================================
# 모듈 레벨 상수 (기본 틀)
# ============================================================
DEFAULT_TTL = 60

REFLEX_CLIP_MAP = {
    "high_front": "reflex_clips/high_front.mp3",
    "high_left": "reflex_clips/high_left.mp3",
    "high_right": "reflex_clips/high_right.mp3",
    "high_stop": "reflex_clips/high_stop.mp3",
    "surface_crosswalk": "reflex_clips/surface_crosswalk.mp3",
    "surface_manhole": "reflex_clips/surface_manhole.mp3",
    "surface_stairs": "reflex_clips/surface_stairs.mp3",
    "surface_grating": "reflex_clips/surface_grating.mp3",
    "surface_braille_damaged": "reflex_clips/surface_braille_damaged.mp3",
}

DEFAULT_REFLEX_CLIP = "reflex_clips/pingpong_default.mp3"


def _resolve_reflex_clip(alert_id: str, clip: Optional[str]) -> str:
    """alert_id에 맞는 사전합성 경보음 경로를 선택한다."""
    if clip:
        return clip
    return REFLEX_CLIP_MAP.get(alert_id, DEFAULT_REFLEX_CLIP)


def _resolve_beep_profile(
    distance: float,
    beep_interval_ms: Optional[int],
    haptic_pattern: Optional[str],
) -> tuple[int, str]:
    """거리 기준 기본 비프 주기와 햅틱 패턴을 보정한다."""
    if beep_interval_ms is not None and haptic_pattern:
        return beep_interval_ms, haptic_pattern

    if distance <= 0.5:
        return 0, "continuous"
    if distance <= 1.0:
        return 100, "continuous"
    if distance <= 1.5:
        return 250, "double"
    return 500, "short"


# ============================================================
# BASIC SKELETON: ReflexClipSender 기본 틀
# - 이 파일의 목적: 반사 경로에서 alert_id 기반 사전합성 클립을
#   WS로 고우선 전송하는 역할
# - 절대 real-time TTS 호출 금지 (반사 경로는 사전합성만)
# ============================================================

async def send_reflex_clip(
    device_id: str,
    alert_id: str,
    direction: str,
    event_id: str = "",
    haptic: bool = True,
    panning: float = 0.0,
    distance: float = 1.0,
    beep_interval_ms: Optional[int] = None,
    haptic_pattern: Optional[str] = None,
    clip: Optional[str] = None,
) -> bool:
    """
    반사 경로 사전합성 경보음을 클라이언트로 고우선 전송한다.

    [호출 시점]
    - DetectionPipeline에서 ReflexAlert가 생성되면 호출됨
    - Surface Gate에서도 동일하게 사용 가능

    [주의]
    - 이 함수 내부에서는 절대 실시간 TTS 합성을 하지 말 것
    - 중복 전송 방지를 위해 suppressor를 반드시 사용
    """

    # ============================================================
    # BASIC SKELETON: 1단계 - 입력 검증 (기초 틀)
    # ============================================================
    if not device_id or not alert_id or not direction:
        logger.warning("[ReflexClipSender] 필수 파라미터 누락")
        return False

    # ============================================================
    # CORE: 2단계 - 중복 억제 체크 (핵심 로직 영역)
    # - 이미 최근에 보냈다면 전송하지 않음
    # - 사용자(당신)가 실제 구현할 핵심 부분
    # ============================================================
    if await Alert_suppressor.should_supperss(device_id, alert_id):
        logger.info(f"[ReflexClipSender] 중복 억제: device_id={device_id}, alert_id={alert_id}")
        return False

    # ============================================================
    # BASIC SKELETON: 3단계 - 전송 페이로드 조립 (기초 틀)
    # - 반사 경로는 사전합성 경보음 + 비프/햅틱 프로파일만 전송한다.
    # ============================================================
    resolved_clip = _resolve_reflex_clip(alert_id, clip)
    resolved_beep_interval_ms, resolved_haptic_pattern = _resolve_beep_profile(
        distance,
        beep_interval_ms,
        haptic_pattern,
    )

    payload = {
        "type": "reflex_alert",
        "event_id": event_id or f"reflex-{device_id}-{alert_id}",
        "device_id": device_id,
        "alert_id": alert_id,
        "direction": direction,
        "risk_level": "high",
        "clip": resolved_clip,
        "haptic": haptic,
        "panning": max(-1.0, min(1.0, panning)),
        "distance": round(distance, 2),
        "beep_interval_ms": resolved_beep_interval_ms,
        "haptic_pattern": resolved_haptic_pattern,
        "ts": int(time.time() * 1000),
    }

    # ============================================================
    # CORE: 4단계 - 고우선 WS 전송 (핵심 로직 영역)
    # - 세션 매니저로 즉시 송신
    # - 반사 경로는 인지 경로보다 우선순위가 높아야 함 (선점)
    # ============================================================
    try:
        if not manager.is_connected(device_id):
            logger.warning(f"[ReflexClipSender] 연결 없음: device_id={device_id}")
            return False

        await manager.send_json(device_id, payload)
        await Alert_suppressor.mark_as_sent(device_id, alert_id)
    except Exception as e:
        logger.info(f"[ReflexClipSender] 전송 실패: {e}")
        return False
    return True


# ============================================================
# 사용 예시 (주석으로만 표시, 실제 호출은 detection_pipeline 등 상위에서)
# ============================================================
# from server.detection.schemas import ReflexAlert
#
# async def handle_reflex(device_id: str, alert: ReflexAlert):
#     success = await send_reflex_clip(
#         device_id=device_id,
#         alert_id=alert.alert_id,
#         clip=alert.clip,
#         direction=alert.direction,
#         event_id=alert.event_id,
#         haptic=alert.haptic,
#     )
#     return success
