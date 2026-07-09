import contextlib
import json
import logging
import os
import sys
import time

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from server.api.session_manager import manager
from server.tts.suppressor import Alert_suppressor

logger = logging.getLogger(__name__)

# ============================================================
# reflex_guidelines.json 설정 로드 및 캐시
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
guidelines_path = os.path.join(project_root, "data", "reflex_guidelines.json")

# 2026-07-09 정정: 이 맵은 실제로는 어디서도 호출되지 않는다(반사 알림 실전송은
# consumer.py의 DetectionConsumer._send_reflex_alert()가 reflex_gate/surface_gate/
# head_level_gate가 채운 ReflexAlert.clip을 그대로 사용). 예전 값은 클래스명이 섞인
# alert_id(예: "high_car_front")와도, 실제 세그멘테이션 모델이 출력하는 단일 P0 클래스
# "caution"과도 맞지 않는 상상 속 파일명이었다. 실제 게이트 3곳이 생성하는 clip 값과
# 일치하도록 정정한다(값은 direction/alert_id 기준, client/assets/sounds/reflex_clips/
# 번들 파일명과 동일).
REFLEX_CLIP_MAP = {
    "front": "reflex_clips/high_front.wav",
    "front-left": "reflex_clips/high_front-left.wav",
    "front-right": "reflex_clips/high_front-right.wav",
    "surface_caution": "reflex_clips/surface_caution.wav",
    "head_level": "reflex_clips/head_level_warning.wav",
}

DEFAULT_REFLEX_CLIP = "reflex_clips/high_front.wav"

REFLEX_GUIDELINES = []
try:
    if os.path.exists(guidelines_path):
        with open(guidelines_path, encoding="utf-8") as f:
            REFLEX_GUIDELINES = json.load(f)
        print(
            f"[ReflexClipSender] Loaded {len(REFLEX_GUIDELINES)} guidelines from {guidelines_path}"
        )
except Exception as e:
    logger.error(f"[ReflexClipSender] Failed to load reflex_guidelines.json: {e}")


def _resolve_reflex_patterns(alert_id: str) -> tuple[dict, dict]:
    """
    alert_id에 매핑되는 비프음 및 햅틱 패턴을 reflex_guidelines.json에서 찾아 반환합니다.
    """
    # 기본 폴백 패턴
    default_beep = {"frequency": 1000, "duration_ms": 100, "repeat_count": 1}
    default_haptic = {"intensity": "medium", "duration_ms": 300, "pattern": "single"}

    # alert_id를 기반으로 가이드라인 인덱싱 매핑
    target_object = None
    if "roadway" in alert_id:
        target_object = "roadway"
    elif "stairs" in alert_id:
        target_object = "stairs"
    elif "manhole" in alert_id:
        target_object = "manhole"
    elif "crosswalk" in alert_id:
        target_object = "stairs"
    elif "grating" in alert_id:
        target_object = "manhole"

    if "front" in alert_id or "left" in alert_id or "right" in alert_id:
        target_object = "scooter"

    for gl in REFLEX_GUIDELINES:
        if target_object and target_object in gl.get("objects", []):
            return gl.get("beep_pattern", default_beep), gl.get("haptic_pattern", default_haptic)
        if target_object and target_object == gl.get("scene_type"):
            return gl.get("beep_pattern", default_beep), gl.get("haptic_pattern", default_haptic)

    return default_beep, default_haptic


async def send_reflex_clip(
    device_id: str,
    alert_id: str,
    direction: str,
    event_id: str = "",
    haptic: bool = True,
    panning: float = 0.0,
    distance: float = 1.0,
    beep_interval_ms: int | None = None,
    haptic_pattern: str | None = None,
    clip: str | None = None,
) -> bool:
    """
    반사 경로 경보 신호(비프음 및 햅틱 패턴)를 단말기로 초저지연 고우선 송출합니다.
    (주의: 지연 최소화를 위해 음성 파일 송출을 배제하고 비프/햅틱 패턴 데이터만 전송함)
    """
    if not device_id or not alert_id or not direction:
        logger.warning("[ReflexClipSender] 필수 파라미터 누락")
        return False

    # 중복 전송 억제 필터링
    if await Alert_suppressor.should_suppress(device_id, alert_id):
        logger.info(f"[ReflexClipSender] 중복 억제: device_id={device_id}, alert_id={alert_id}")
        return False

    # 비프 및 햅틱 패턴 획득
    beep_pat, haptic_pat = _resolve_reflex_patterns(alert_id)

    payload = {
        "type": "reflex_alert",
        "event_id": event_id or f"reflex-{device_id}-{alert_id}",
        "device_id": device_id,
        "alert_id": alert_id,
        "direction": direction,
        "risk_level": "high",
        "clip": "",  # 음성 배제 (지연 최소화)
        "haptic": haptic,
        "panning": max(-1.0, min(1.0, panning)),
        "distance": round(distance, 2),
        "beep_pattern": beep_pat,
        "haptic_pattern": haptic_pat,
        "ts": int(time.time() * 1000),
    }

    try:
        if not manager.is_connected(device_id):
            logger.warning(f"[ReflexClipSender] 연결 없음: device_id={device_id}")
            return False

        # WebSocket 채널로 즉시 송신 (인지 경로 대비 고우선 송출)
        await manager.send_json(device_id, payload)
        await Alert_suppressor.mark_as_sent(device_id, alert_id)
    except Exception as e:
        logger.error(f"[ReflexClipSender] 전송 실패: {e}")
        return False
    return True
