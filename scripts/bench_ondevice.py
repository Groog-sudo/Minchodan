#!/usr/bin/env python3
"""
온디바이스 타당성 검증용 벤치마크 스크립트.
서버 사이드 YOLO26n 추론 레이턴시 기준선을 측정한다.

측정 항목:
    - 프레임당 추론 시간 (ms)
    - FPS (초당 처리 가능 프레임 수)
    - 모델 로드 시간 (ms)
    - 평균/최소/최대/p50/p95/p99 레이턴시
    - CPU vs GPU device 비교

사용법:
    python scripts/bench_ondevice.py --rounds 100
    python scripts/bench_ondevice.py --rounds 50 --device cpu
    python scripts/bench_ondevice.py --rounds 50 --device cuda
"""

import argparse
import os
import statistics
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

import numpy as np

DEFAULT_ROUNDS = 100
FRAME_SIZE = 640

MODELS = {
    "object_detection": os.path.join(
        project_root, "server", "models", "yolo26n", "object_detection.pt"
    ),
    "segmentation": os.path.join(project_root, "server", "models", "yolo26n", "segmentation.pt"),
}


def get_available_device() -> str:
    """CUDA 가용 여부 확인."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # nosec # noqa: S110
        pass
    return "cpu"


def percentile(data: list[float], p: float) -> float:
    """데이터의 p 백분위수 반환."""
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 0:
        return 0.0
    idx = int(n * p / 100)
    if idx >= n:
        idx = n - 1
    return sorted_data[idx]


def benchmark_model(
    model_path: str,
    device: str,
    rounds: int,
    frame_size: int = FRAME_SIZE,
) -> dict:
    """단일 모델의 추론 레이턴시 벤치마크 수행.

    Returns:
        측정 결과 dict.
    """
    from ultralytics import YOLO

    print(f"\n[INFO] 모델 로드 중: {model_path} (device={device})")
    load_start = time.perf_counter()
    model = YOLO(model_path)
    load_ms = (time.perf_counter() - load_start) * 1000
    print(f"[INFO] 모델 로드 완료: {load_ms:.1f}ms")

    frame = np.zeros((frame_size, frame_size, 3), dtype=np.uint8)

    print("[INFO] 워밍업 5회...")
    for _ in range(5):
        try:
            model.predict(source=frame, device=device, verbose=False)
        except Exception as e:
            print(f"[WARN] 워밍업 오류: {e}")

    print(f"[INFO] 벤치마크 시작: {rounds}회")
    latencies: list[float] = []
    for i in range(rounds):
        try:
            t0 = time.perf_counter()
            model.predict(source=frame, device=device, verbose=False)
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)
        except Exception as e:
            print(f"[WARN] 라운드 {i} 오류: {e}")
            latencies.append(float("inf"))

    valid = [lat for lat in latencies if lat != float("inf")]

    if not valid:
        return {
            "model": os.path.basename(model_path),
            "device": device,
            "rounds": rounds,
            "successful": 0,
            "load_ms": load_ms,
            "error": "모든 라운드 실패",
        }

    return {
        "model": os.path.basename(model_path),
        "device": device,
        "rounds": rounds,
        "successful": len(valid),
        "load_ms": round(load_ms, 2),
        "avg_ms": round(statistics.mean(valid), 2),
        "min_ms": round(min(valid), 2),
        "max_ms": round(max(valid), 2),
        "stdev_ms": round(statistics.stdev(valid), 2) if len(valid) > 1 else 0.0,
        "p50_ms": round(percentile(valid, 50), 2),
        "p95_ms": round(percentile(valid, 95), 2),
        "p99_ms": round(percentile(valid, 99), 2),
        "fps": round(1000.0 / statistics.mean(valid), 2) if valid else 0.0,
    }


def print_result(result: dict) -> None:
    """벤치마크 결과를 표 형태로 출력."""
    print()
    print(f"+{'=' * 60}+")
    print(f"| 모델: {result['model']}")
    print(f"| 디바이스: {result['device']}")
    print(f"| 라운드: {result['rounds']} (성공: {result['successful']})")
    print(f"+{'-' * 60}+")
    print(f"| 모델 로드 시간   : {result['load_ms']:.1f} ms")
    if "avg_ms" in result:
        print(f"| 평균 추론 시간   : {result['avg_ms']:.2f} ms")
        print(f"| 최소 추론 시간   : {result['min_ms']:.2f} ms")
        print(f"| 최대 추론 시간   : {result['max_ms']:.2f} ms")
        print(f"| 표준편차         : {result['stdev_ms']:.2f} ms")
        print(f"| p50 (중앙값)     : {result['p50_ms']:.2f} ms")
        print(f"| p95              : {result['p95_ms']:.2f} ms")
        print(f"| p99              : {result['p99_ms']:.2f} ms")
        print(f"| 처리 속도 (FPS)  : {result['fps']:.2f} fps")
    else:
        print(f"| 오류             : {result.get('error', 'N/A')}")
    print(f"+{'=' * 60}+")


def main() -> int:
    parser = argparse.ArgumentParser(description="Minchodan 온디바이스 타당성 검증 벤치마크")
    parser.add_argument(
        "--rounds",
        type=int,
        default=DEFAULT_ROUNDS,
        help=f"벤치마크 라운드 수 (기본: {DEFAULT_ROUNDS})",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default=None,
        help="추론 디바이스 (기본: 자동 감지)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=list(MODELS.keys()),
        default=list(MODELS.keys()),
        help="벤치마크할 모델 (기본: 전체)",
    )
    args = parser.parse_args()

    device = args.device or get_available_device()
    print(f"[INFO] 추론 디바이스: {device}")
    print(f"[INFO] 프레임 크기: {FRAME_SIZE}x{FRAME_SIZE}")
    print(f"[INFO] 라운드 수: {args.rounds}")

    all_results: list[dict] = []
    for key in args.models:
        model_path = MODELS[key]
        if not os.path.exists(model_path):
            print(f"[ERROR] 모델 파일 없음: {model_path}")
            continue
        result = benchmark_model(model_path, device, args.rounds)
        all_results.append(result)
        print_result(result)

    if len(all_results) >= 2:
        print(f"\n+{'=' * 60}+")
        print("| 비교 요약")
        print(f"+{'-' * 60}+")
        for r in all_results:
            if "avg_ms" in r:
                print(
                    f"| {r['model']:30s} | avg={r['avg_ms']:7.1f}ms | "
                    f"p50={r['p50_ms']:7.1f}ms | fps={r['fps']:6.1f}"
                )
        print(f"+{'=' * 60}+")

    print("\n[INFO] 벤치마크 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
