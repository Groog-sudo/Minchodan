"""
Fast Lane Node.
단일 객체 + 시계 방향 + 거리가 확정된 일상 안내는 LLM 없이 템플릿으로 즉시 생성한다.
Phase 3: outdoor_guidance_refinement_roadmap §9.
"""

import contextlib
import re
import sys

from server.detection.risk_rules import CLASS_TEXT
from server.orchestration.nodes.l2_generator import extract_direction
from server.orchestration.nodes.l3_validator import MAX_LEN

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

# Option A(class-agnostic) 기준 인지 패스트 레인 커버리지: 빈도·위험 상위 객체.
FAST_LANE_CLASS_NAMES = (
    "scooter",
    "bicycle",
    "car",
    "motorcycle",
    "bollard",
    "pole",
    "person",
    "barricade",
    "bus",
    "truck",
)

FAST_LANE_OBJECT_KO = frozenset(CLASS_TEXT[c] for c in FAST_LANE_CLASS_NAMES)

FAST_LANE_DISTANCES = frozenset({"near", "medium", "far"})
FAST_LANE_PATTERN = "caution"
_CLOCK_HOUR_PATTERN = re.compile(r"^(9|10|11|12|1|2|3)시$")


def make_fast_lane_cache_key(
    clock_direction: str,
    object_ko: str,
    distance: str,
    pattern: str = FAST_LANE_PATTERN,
) -> str:
    """사전합성 TTS 클립 파일명/조회 키. 형식: {clock}_{object_ko}_{distance}_{pattern}."""
    obj_slug = object_ko.replace(" ", "_")
    return f"{clock_direction}_{obj_slug}_{distance}_{pattern}"


def _format_direction_phrase(clock_direction: str) -> str:
    if clock_direction == "12시":
        return "전방"
    return f"{clock_direction} 방향"


def build_fast_lane_guidance(clock_direction: str, object_ko: str, distance: str) -> str:
    """거리 밴드별 고정 템플릿으로 20자 이내 안내문을 생성한다."""
    dir_phrase = _format_direction_phrase(clock_direction)
    if distance == "near":
        return f"{dir_phrase} {object_ko} 주의하세요"
    if distance == "medium":
        return f"{dir_phrase} {object_ko} 확인하세요"
    return f"{dir_phrase} {object_ko} 있습니다"


def can_use_fast_lane(state: dict) -> bool:
    """L1 직후 LLM 대신 패스트 레인으로 분기할지 판단한다."""
    detected_classes = state.get("detected_classes") or []
    if len(detected_classes) != 1:
        return False
    if state.get("is_departing_confirmed"):
        return False
    # 2026-07-19: caution/roadway 노면 mid는 L2 노면 멘트가 필요하므로 패스트 레인 제외.
    surface_classes = state.get("surface_classes") or []
    if any(cls in ("caution", "roadway", "주의 노면", "차도") for cls in surface_classes):
        return False
    if (state.get("navigation_guidance") or "").strip():
        return False

    clock_direction = (state.get("clock_direction") or "").strip()
    distance = (state.get("distance") or "").strip()
    object_ko = (state.get("object_ko") or "").strip()
    if not clock_direction or not distance or not object_ko:
        return False
    if not _CLOCK_HOUR_PATTERN.match(clock_direction):
        return False
    if distance not in FAST_LANE_DISTANCES:
        return False
    if object_ko not in FAST_LANE_OBJECT_KO:
        return False

    guidance_text = build_fast_lane_guidance(clock_direction, object_ko, distance)
    return len(guidance_text) <= MAX_LEN


async def fast_lane_node(state: dict) -> dict:
    """LangGraph 패스트 레인 노드 진입점."""
    clock_direction = state.get("clock_direction", "")
    object_ko = state.get("object_ko", "")
    distance = state.get("distance", "")

    guidance_text = build_fast_lane_guidance(clock_direction, object_ko, distance)
    cache_key = make_fast_lane_cache_key(clock_direction, object_ko, distance)

    return {
        "guidance_text": guidance_text,
        "direction": extract_direction(guidance_text),
        "verified": True,
        "used_fast_lane": True,
        "fast_lane_cache_key": cache_key,
        "validation_errors": [],
        "retry_count": 0,
    }
