import contextlib
import json
import logging
import os
import sys

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# ============================================================
# reflex_guidelines.json 설정 로드 및 캐시
# ============================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
guidelines_path = os.path.join(project_root, "data", "reflex_guidelines.json")

REFLEX_GUIDELINES = []
try:
    if os.path.exists(guidelines_path):
        with open(guidelines_path, encoding="utf-8") as f:
            REFLEX_GUIDELINES = json.load(f)
        logger.info(
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
