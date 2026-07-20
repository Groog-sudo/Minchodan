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

# 2026-07-20: 노면(caution/roadway) 단독 안내도 route_after_l1에서 패스트 레인이
# 허용되지만(can_use_fast_lane L111 예외), 사전합성 스크립트가 이 두 클래스를
# 순회하지 않아 클립이 한 건도 없었다("전방 차도..." 안내가 항상 실시간 6초대
# LLM+TTS로 빠지던 원인). build_guide_clips.py가 이 목록도 함께 순회한다.
FAST_LANE_SURFACE_CLASS_NAMES = ("caution", "roadway")

FAST_LANE_OBJECT_KO = frozenset(
    CLASS_TEXT[c] for c in FAST_LANE_CLASS_NAMES + FAST_LANE_SURFACE_CLASS_NAMES
)

FAST_LANE_DISTANCES = frozenset({"near", "medium", "far"})
FAST_LANE_PATTERN = "caution"
# 12시 + 우회 방향이 있는 문구("전방 X, N시로 우회하세요")용 사전합성 대상.
FAST_LANE_AVOID_CLOCKS = ("10시", "2시")
_CLOCK_HOUR_PATTERN = re.compile(r"^(9|10|11|12|1|2|3)시$")


def _normalize_avoid_clock(avoid_clock: str | None) -> str | None:
    """우회 제안 시각을 10시/2시로 정규화한다. 불명확하면 None."""
    text = (avoid_clock or "").strip()
    if text in ("1시", "2시", "3시"):
        return "2시"
    if text in ("9시", "10시", "11시"):
        return "10시"
    return None


def make_fast_lane_cache_key(
    clock_direction: str,
    object_ko: str,
    distance: str,
    pattern: str = FAST_LANE_PATTERN,
    avoid_clock: str | None = None,
) -> str:
    """사전합성 TTS 클립 파일명/조회 키.

    형식: {clock}_{object_ko}_{distance}_{pattern}, 12시 + 우회 방향이 있으면
    {clock}_{object_ko}_{distance}_avoid{avoid}.

    2026-07-20: avoid_clock을 키에 반영하지 않으면 12시 + 우회 방향 문구
    ("전방 X, 2시로 우회하세요")와 12시 + 단순 주의 문구("전방 X 주의하세요")가
    같은 키로 충돌해, 실제 안내문과 다른 음성(잘못된 우회 방향 또는 방향 누락)이
    재생될 수 있는 결함이 있었다.
    """
    obj_slug = object_ko.replace(" ", "_")
    normalized_avoid = _normalize_avoid_clock(avoid_clock)
    if clock_direction == "12시" and normalized_avoid:
        return f"{clock_direction}_{obj_slug}_{distance}_avoid{normalized_avoid}"
    return f"{clock_direction}_{obj_slug}_{distance}_{pattern}"


def _format_direction_phrase(clock_direction: str) -> str:
    if clock_direction == "12시":
        return "전방"
    return f"{clock_direction} 방향"


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
    """L1 직후 LLM 대신 패스트 레인으로 분기할지 판단한다.

    2026-07-20: 프레임 내 전체 탐지 개수(detected_classes)가 아니라, 실제 안내
    대상인 주위험 객체(object_ko, consumer.py에서 confidence 최댓값 detection으로
    이미 선정됨) 하나만 기준으로 판단한다. 기존에는 프레임에 다른 객체가 하나만
    더 잡혀도(도로에서 흔함, 특히 사람) 패스트 레인이 통째로 차단돼 실시간
    LLM(~2초)으로 빠지며 안내가 늦게 나오는 문제가 실기기 테스트에서 확인됨.
    guidance_text는 항상 object_ko 하나만 언급하므로(L2 템플릿도 동일), 다른
    객체 존재 여부가 문구 정확성에 영향을 주지 않는다.
    """
    detected_classes = state.get("detected_classes") or []
    object_ko = (state.get("object_ko") or "").strip()
    if not detected_classes and object_ko not in (
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
    cache_key = make_fast_lane_cache_key(
        clock_direction, object_ko, distance, avoid_clock=avoid_clock
    )

    return {
        "guidance_text": guidance_text,
        "direction": extract_direction(guidance_text),
        "verified": True,
        "used_fast_lane": True,
        "fast_lane_cache_key": cache_key,
        "validation_errors": [],
        "retry_count": 0,
    }
