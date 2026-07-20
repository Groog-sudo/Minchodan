"""
패스트 레인 안내 문장을 사전합성 WAV로 data/guide_clips/에 배치한다.

사용 예:
  .venv/bin/python scripts/build_guide_clips.py
  .venv/bin/python scripts/build_guide_clips.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from server.detection.direction import CLOCK_HOURS
from server.detection.risk_rules import CLASS_TEXT
from server.orchestration.nodes.fast_lane import (
    FAST_LANE_AVOID_CLOCKS,
    FAST_LANE_CLASS_NAMES,
    FAST_LANE_DISTANCES,
    FAST_LANE_PATTERN,
    FAST_LANE_SURFACE_CLASS_NAMES,
    build_fast_lane_guidance,
    make_fast_lane_cache_key,
)
from server.tts.tts_service import get_tts_service

GUIDE_CLIPS_DIR = os.path.join(root_dir, "data", "guide_clips")


def iter_fast_lane_combinations() -> list[tuple[str, str, str, str, str]]:
    """(clock, object_ko, distance, pattern, guidance_text) 목록.

    2026-07-20: object 클래스 10종 + 노면 2종(caution/roadway)을 모두 순회하고,
    12시 방향은 우회 방향 없는 기본 문구뿐 아니라 avoid_clock=10시/2시 문구도
    함께 사전합성한다(캐시 키에 우회 방향을 반영하는 변경과 짝을 이룸).
    """
    combos: list[tuple[str, str, str, str, str]] = []
    for class_name in FAST_LANE_CLASS_NAMES + FAST_LANE_SURFACE_CLASS_NAMES:
        object_ko = CLASS_TEXT[class_name]
        for hour in CLOCK_HOURS:
            clock = f"{hour}시"
            for distance in sorted(FAST_LANE_DISTANCES):
                avoid_variants: list[str | None] = [None]
                if clock == "12시":
                    avoid_variants.extend(FAST_LANE_AVOID_CLOCKS)
                for avoid_clock in avoid_variants:
                    text = build_fast_lane_guidance(
                        clock, object_ko, distance, avoid_clock=avoid_clock
                    )
                    if len(text) > 20:
                        continue
                    cache_key = make_fast_lane_cache_key(
                        clock, object_ko, distance, FAST_LANE_PATTERN, avoid_clock=avoid_clock
                    )
                    combos.append((clock, object_ko, distance, cache_key, text))
    return combos


async def build_clips(dry_run: bool = False, limit: int | None = None) -> int:
    os.makedirs(GUIDE_CLIPS_DIR, exist_ok=True)
    combos = iter_fast_lane_combinations()
    if limit is not None:
        combos = combos[:limit]

    if dry_run:
        for _, _, _, cache_key, text in combos:
            print(f"[dry-run] {cache_key}.wav <- {text}")
        print(f"총 {len(combos)}건 (합성 생략)")
        return len(combos)

    tts = get_tts_service()
    built = 0
    for _, _, _, cache_key, text in combos:
        out_path = os.path.join(GUIDE_CLIPS_DIR, f"{cache_key}.wav")
        if os.path.isfile(out_path):
            built += 1
            continue
        try:
            audio_bytes = await tts.generate(text=text, voice="ko")
        except Exception as e:
            print(f"[skip] {cache_key}: 합성 실패 ({e})")
            continue
        if not audio_bytes:
            print(f"[skip] {cache_key}: 빈 오디오")
            continue
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        built += 1
        print(f"[ok] {cache_key}.wav")
    print(f"완료: {built}/{len(combos)}건")
    return built


def main() -> None:
    parser = argparse.ArgumentParser(description="패스트 레인 guide_clips 사전합성")
    parser.add_argument("--dry-run", action="store_true", help="조합만 출력, 합성 생략")
    parser.add_argument("--limit", type=int, default=None, help="최대 생성 건수")
    args = parser.parse_args()
    asyncio.run(build_clips(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        main()
