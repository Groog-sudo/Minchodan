#!/usr/bin/env python3
"""
P2-1(c) (2026-07-17): 세그멘테이션 5클래스 재학습 파이프라인.

필드 테스트 개선 계획서 M7/P2-1(c): 현재 4클래스(sidewalk_normal/caution/roadway/braille_normal)
통합 모델에서 caution(계단/맨홀/그레이팅)을 분리한 5클래스 모델 재학습 파이프라인.

5클래스 구성(제안):
    0: sidewalk_normal
    1: stair_down       (계단 - 내려막)
    2: manhole          (맨홀)
    3: roadway
    4: braille_normal

본 스크립트는 파이프라인 골격(데이터 검증 -> 학습 -> 검증 -> 모델 교체)을 제공한다.
실제 학습은 라벨링된 5클래스 데이터셋이 준비된 후 실행한다.

사용:
    python scripts/train_segmentation_5class.py --dataset data/seg_5class --epochs 100
    python scripts/train_segmentation_5class.py --dry-run

환경변수:
    SEG_5CLASS_MODEL_BASE - 베이스 가중치 경로 (기본 YOLO26N_SEG)
    SEG_5CLASS_OUTPUT_DIR  - 학습 결과 출력 디렉터리 (기본 training/runs/seg_5class)
"""

import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# 5클래스 클래스명 (제안 - 데이터셋 data.yaml과 일치해야 함)
SEG_5CLASS_NAMES = ["sidewalk_normal", "stair_down", "manhole", "roadway", "braille_normal"]


def _validate_dataset(dataset_dir: str) -> bool:
    """데이터셋 구조(images/, labels/, data.yaml) 검증."""
    required = ["images", "labels", "data.yaml"]
    for item in required:
        path = os.path.join(dataset_dir, item)
        if not os.path.exists(path):
            print(f"[ERROR] 데이터셋 구성 요소 누락: {path}")
            return False
    print(f"[OK] 데이터셋 검증 통과: {dataset_dir}")
    return True


def _train(dataset_dir: str, epochs: int, base_model: str, output_dir: str) -> int:
    """ultralytics YOLO seg 학습 실행. 실패 시 1 반환."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics 미설치. pip install ultralytics 후 실행.")
        return 1

    if not os.path.exists(base_model):
        print(f"[ERROR] 베이스 가중치 없음: {base_model}")
        return 1

    os.makedirs(output_dir, exist_ok=True)
    model = YOLO(base_model)
    data_yaml = os.path.join(dataset_dir, "data.yaml")
    print(f"[INFO] 5클래스 세그멘테이션 학습 시작: epochs={epochs}, base={base_model}")
    model.train(data=data_yaml, epochs=epochs, task="segment", project=output_dir, name="seg5c")
    print(f"[OK] 학습 완료. 결과 디렉터리: {output_dir}")
    return 0


def _validate_model(weights: str, dataset_dir: str) -> int:
    """학습된 5클래스 모델 검증 (정밀도/재현율)."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[WARN] ultralytics 미설치 - 검증 생략")
        return 0
    if not os.path.exists(weights):
        print(f"[WARN] 가중치 없음 - 검증 생략: {weights}")
        return 0
    model = YOLO(weights)
    data_yaml = os.path.join(dataset_dir, "data.yaml")
    print(f"[INFO] 5클래스 모델 검증: {weights}")
    metrics = model.val(data=data_yaml, task="segment")
    print(f"[OK] 검증 완료. mAP50={getattr(metrics, 'box', None)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="5클래스 세그멘테이션 재학습 파이프라인")
    parser.add_argument(
        "--dataset", default=os.getenv("SEG_5CLASS_DATASET", ""), help="데이터셋 디렉터리"
    )
    parser.add_argument("--epochs", type=int, default=100, help="학습 에폭")
    parser.add_argument("--dry-run", action="store_true", help="데이터 검증만 수행")
    parser.add_argument("--validate-only", default="", help="검증만 수행 (가중치 경로)")
    args = parser.parse_args()

    base_model = os.getenv("SEG_5CLASS_MODEL_BASE", os.getenv("YOLO26N_SEG", "")).strip()
    output_dir = os.getenv(
        "SEG_5CLASS_OUTPUT_DIR", os.path.join(PROJECT_ROOT, "training/runs/seg_5class")
    )

    print("[INFO] 5클래스 세그멘테이션 재학습 파이프라인")
    print(f"  클래스: {SEG_5CLASS_NAMES}")
    print(f"  베이스 가중치: {base_model or '(기본 .env YOLO26N_SEG)'}")
    print(f"  출력 디렉터리: {output_dir}")

    if args.validate_only:
        return _validate_model(args.validate_only, args.dataset)

    if not args.dataset:
        print("[ERROR] --dataset 또는 SEG_5CLASS_DATASET 환경변수 필요")
        return 1

    if not _validate_dataset(args.dataset):
        return 1

    if args.dry_run:
        print("[OK] dry-run 완료 (데이터 검증 통과)")
        return 0

    return _train(args.dataset, args.epochs, base_model, output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
