# -*- coding: utf-8 -*-
"""
Medium 인지 경로용 짧은 회피 힌트 (인메모리 dict).

완성 문장 RAG를 L2가 20자로 압축하던 구조를 대체한다.
벡터검색/임베딩을 거치지 않으며, 클래스별 5~12자 행동 조각만 제공한다.
방향(N시/좌/우)은 L2가 [탐지 방향]으로만 쓰고, 힌트에는 넣지 않는다.
"""

from __future__ import annotations

import contextlib
import hashlib
import re
import sys

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

# 힌트 길이 상한 (한글 기준 문자 수). L2가 방향·장애물명과 조합해도 20자 여유를 둔다.
HINT_MAX_LEN = 12
HINT_MIN_LEN = 4

# 힌트에 넣으면 L2 [탐지 방향]과 충돌하는 표현.
_FORBIDDEN_DIRECTION_RE = re.compile(r"(좌측|우측|왼쪽|오른쪽|좌우|(9|10|11|12|1|2|3)시)")

DEFAULT_HINT = "주의하며 우회"

# YOLO Object Detection 29클래스 + 인지에 자주 나오는 노면 라벨.
# 노면(caution/roadway)은 consumer의 departure_str가 우선이지만, 빈 컨텍스트 방지용으로 둔다.
GUIDANCE_HINTS: dict[str, list[str]] = {
    "barricade": ["가림막 피해 통과", "안전거리 두고 우회"],
    "bench": ["벤치 피해 통과", "앉을자리 비껴 이동"],
    "bicycle": ["자전거 피해 통과", "바퀴 접촉 주의"],
    "bollard": ["옆으로 피해서 통과", "충돌 주의하며 우회"],
    "bus": ["버스 가장자리 주의", "여유 두고 우회"],
    "car": ["차체 가장자리 주의", "여유 두고 우회"],
    "carrier": ["캐리어 피해 통과", "손잡이 접촉 주의"],
    "cat": ["동물 간격 유지", "천천히 비껴 통과"],
    "chair": ["의자 피해 통과", "다리 걸림 주의"],
    "dog": ["동물 간격 유지", "천천히 비껴 통과"],
    "fire_hydrant": ["소화전 피해 통과", "돌출부 주의"],
    "kiosk": ["키오스크 피해 통과", "모서리 주의하며 우회"],
    "motorcycle": ["오토바이 피해 통과", "사이드미러 주의"],
    "movable_signage": ["입간판 피해 통과", "쓰러짐 주의하며 우회"],
    "parking_meter": ["계량기 피해 통과", "돌출부 주의"],
    "person": ["보행자 간격 유지", "천천히 비껴 통과"],
    "pole": ["기둥 피해 통과", "어깨 높이 주의"],
    "potted_plant": ["화분 피해 통과", "받침 걸림 주의"],
    "power_controller": ["설비함 피해 통과", "모서리 주의"],
    "scooter": ["여유 확인 후 우회", "비껴서 통과"],
    "stop": ["표지 피해 통과", "받침 걸림 주의"],
    "stroller": ["유모차 간격 유지", "천천히 비껴 통과"],
    "table": ["테이블 피해 통과", "모서리 주의하며 우회"],
    "traffic_light": ["신호등 기둥 주의", "받침 피해 통과"],
    "traffic_light_controller": ["제어함 피해 통과", "모서리 주의"],
    "traffic_sign": ["표지판 피해 통과", "받침 걸림 주의"],
    "tree_trunk": ["나무 피해 통과", "뿌리턱 주의"],
    "truck": ["트럭 가장자리 주의", "여유 두고 우회"],
    "wheelchair": ["휠체어 간격 유지", "천천히 비껴 통과"],
    "caution": ["발끝 높이 확인", "서행하며 통과"],
    "roadway": ["보도 쪽 유지", "차도 가장자리 주의"],
    "sidewalk_normal": ["보도 중앙 유지", "가장자리 주의"],
    "braille_normal": ["점자블록 따라 이동", "이탈 주의"],
}


def _normalize_class_name(class_name: str | None) -> str:
    if not class_name:
        return ""
    return str(class_name).lower().strip()


def validate_hint(hint: str) -> None:
    """힌트 길이·금지어 규칙을 검사한다. 위반 시 ValueError."""
    text = (hint or "").strip()
    if not text:
        raise ValueError("빈 힌트")
    if len(text) < HINT_MIN_LEN:
        raise ValueError(f"힌트 너무 짧음: {len(text)} < {HINT_MIN_LEN}")
    if len(text) > HINT_MAX_LEN:
        raise ValueError(f"힌트 너무 김: {len(text)} > {HINT_MAX_LEN}")
    if _FORBIDDEN_DIRECTION_RE.search(text):
        raise ValueError(f"힌트에 방향 표현 금지: {text}")


def assert_hints_valid(hints_map: dict[str, list[str]] | None = None) -> None:
    """모듈 로드·테스트용: 전체 힌트 맵 규칙 검증."""
    target = hints_map if hints_map is not None else GUIDANCE_HINTS
    for class_name, hints in target.items():
        if not hints:
            raise ValueError(f"힌트 목록 비어 있음: {class_name}")
        for hint in hints:
            validate_hint(hint)


def select_guidance_hint(
    class_name: str | None,
    seed: str | None = None,
) -> str:
    """
    클래스별 짧은 회피 힌트 1개를 반환한다.

    seed(event_id/track_id 등)가 있으면 결정적으로 순환 선택해
    같은 상황에서 재현 가능하고, 연속 이벤트에서는 문구가 바뀌게 한다.
    미등록 클래스는 DEFAULT_HINT로 폴백한다.
    """
    key = _normalize_class_name(class_name)
    hints = GUIDANCE_HINTS.get(key) or [DEFAULT_HINT]
    if len(hints) == 1:
        return hints[0]

    material = f"{key}:{seed or ''}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(hints)
    return hints[index]


# 임포트 시점에 규칙 위반을 조기 발견한다.
assert_hints_valid()
