import argparse
import asyncio
import os
import sys
from statistics import mean, median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.db.connection import async_sessionmaker_factory
from server.db.repositories import LidarDistanceValidationRepository


async def _fetch(limit: int):
    async with async_sessionmaker_factory() as session:
        repo = LidarDistanceValidationRepository(session)
        return await repo.list_recent(limit=limit)


def _print_heuristic_class_breakdown(rows) -> None:
    """휴리스틱 라벨(near/medium/far)별로 LiDAR 실측(m) 분포를 출력한다.

    판정 임계값(예: "near는 몇 m 이하여야 정상")은 자동으로 정하지 않는다.
    출력된 분포를 담당자가 직접 읽고 휴리스틱이 타당한지 해석해야 한다.
    """
    by_class: dict[str, list[float]] = {"near": [], "medium": [], "far": []}
    missing_count = 0
    for row in rows:
        if row.lidar_meters is None:
            missing_count += 1
            continue
        by_class.setdefault(row.heuristic_distance_class, []).append(row.lidar_meters)

    print("\n[휴리스틱 라벨별 LiDAR 실측 거리(m) 분포]")
    for label in ("near", "medium", "far"):
        meters = by_class.get(label, [])
        if not meters:
            print(f"  {label:8s}: 샘플 없음")
            continue
        print(
            f"  {label:8s}: n={len(meters):4d}  "
            f"mean={mean(meters):.2f}  median={median(meters):.2f}  "
            f"min={min(meters):.2f}  max={max(meters):.2f}"
        )
    print(f"  LiDAR 실측 없음(유효 depth 샘플 부족): {missing_count}건")


def _print_class_name_breakdown(rows) -> None:
    by_class: dict[str, list[tuple[str, float | None]]] = {}
    for row in rows:
        by_class.setdefault(row.class_name, []).append(
            (row.heuristic_distance_class, row.lidar_meters)
        )

    print("\n[탐지 클래스별 건수 및 LiDAR 실측 평균(m)]")
    for class_name, entries in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        meters = [m for _, m in entries if m is not None]
        avg = f"{mean(meters):.2f}" if meters else "-"
        print(f"  {class_name:20s}: n={len(entries):4d}  lidar_avg={avg}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="lidar_distance_validation_samples 테이블의 LiDAR 실측 vs "
        "휴리스틱 거리 라벨을 집계 출력한다 (검증 전용, 판정 자동화 없음)."
    )
    parser.add_argument("--limit", type=int, default=500, help="조회할 최근 샘플 수 (기본 500)")
    args = parser.parse_args()

    rows = await _fetch(args.limit)
    if not rows:
        print("lidar_distance_validation_samples 테이블에 데이터가 없습니다.")
        return

    print(f"총 {len(rows)}건 조회 (최신 {args.limit}건 이내)")
    _print_heuristic_class_breakdown(rows)
    _print_class_name_breakdown(rows)


if __name__ == "__main__":
    asyncio.run(main())
