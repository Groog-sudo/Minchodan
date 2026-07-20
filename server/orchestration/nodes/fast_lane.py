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

FAST_LANE_OBJECT_KO = frozenset(CLASS_TEXT[c] for c in FAST_LANE_CLASS_NAMES) | {
    CLASS_TEXT["caution"],
    CLASS_TEXT["roadway"],
}

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


def _normalize_avoid_clock(avoid_clock: str | None) -> str | None:
    """우회 제안 시각을 10시/2시로 정규화한다. 불명확하면 None."""
    text = (avoid_clock or "").strip()
    if text in ("1시", "2시", "3시"):
        return "2시"
    if text in ("9시", "10시", "11시"):
        return "10시"
    return None


def build_fast_lane_guidance(
    clock_direction: str,
    object_ko: str,
    distance: str,
    avoid_clock: str | None = None,
) -> str:
    """단일 객체 Medium/Near 인지용 고정 템플릿 (20자 이내).

    목표 패턴 (L2 예시와 동일):
    - 측면: "10시 방향 전동 킥보드 주의하세요"
    - 전방: "전방 볼라드, 2시로 우회하세요" (avoid_clock 있을 때)
    """
    obj = (object_ko or "").strip()
    if clock_direction == "12시":
        avoid = _normalize_avoid_clock(avoid_clock)
        if avoid and obj:
            detour = f"전방 {obj}, {avoid}로 우회하세요"
            if len(detour) <= MAX_LEN:
                return detour
        caution = f"전방 {obj} 주의하세요" if obj else "전방 주의하세요"
        if len(caution) <= MAX_LEN:
            return caution
        return "전방 주의하세요"

    dir_phrase = _format_direction_phrase(clock_direction)
    # near/medium/far 모두 "주의하세요"로 통일 (Medium도 확인하세요 대신 동일 패턴).
    text = f"{dir_phrase} {obj} 주의하세요" if obj else f"{dir_phrase} 주의하세요"
    if len(text) <= MAX_LEN:
        return text
    # 긴 객체명은 방향+주의만 남긴다.
    short = f"{dir_phrase} 주의하세요"
    return short if len(short) <= MAX_LEN else "전방 주의하세요"


def can_use_fast_lane(state: dict) -> bool:
    """L1 직후 LLM 대신 패스트 레인으로 분기할지 판단한다."""
    detected_classes = state.get("detected_classes") or []
    object_ko = (state.get("object_ko") or "").strip()
    if len(detected_classes) > 1:
        return False
    if len(detected_classes) == 0 and object_ko not in (
        CLASS_TEXT["caution"],
        CLASS_TEXT["roadway"],
    ):
        return False
    if state.get("is_departing_confirmed"):
        return False
    # 보도 이탈 확정은 L2 노면 멘트 유지. Medium 노면 단독·단일 객체는 패스트 레인.
    if (state.get("navigation_guidance") or "").strip():
        return False

    clock_direction = (state.get("clock_direction") or "").strip()
    distance = (state.get("distance") or "").strip() or "medium"
    avoid_clock = (state.get("avoid_clock_direction") or "").strip() or None
    if not clock_direction or not object_ko:
        return False
    if not _CLOCK_HOUR_PATTERN.match(clock_direction):
        return False
    if distance not in FAST_LANE_DISTANCES:
        return False
    if object_ko not in FAST_LANE_OBJECT_KO:
        return False

    guidance_text = build_fast_lane_guidance(
        clock_direction, object_ko, distance, avoid_clock=avoid_clock
    )
    return len(guidance_text) <= MAX_LEN


async def fast_lane_node(state: dict) -> dict:
    """LangGraph 패스트 레인 노드 진입점."""
    clock_direction = state.get("clock_direction", "")
    object_ko = state.get("object_ko", "")
    distance = state.get("distance", "")
    avoid_clock = (state.get("avoid_clock_direction") or "").strip() or None

    guidance_text = build_fast_lane_guidance(
        clock_direction, object_ko, distance, avoid_clock=avoid_clock
    )
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
