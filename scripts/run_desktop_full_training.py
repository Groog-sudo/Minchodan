# -*- coding: utf-8 -*-
from __future__ import annotations

# [VIBE CODE] 라이브러리 로드 및 기본 설정
import argparse
import os
import subprocess
import sys
from pathlib import Path

# 가이드 3.4: dotenv 사용 (python-dotenv가 설치되어 있을 경우)
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# docs/changelogs/th.md 및 .env.example 기준 AI Hub 하위 폴더명
BBOX_SUBDIR = "바운딩박스"
SEG_SUBDIR = "서피스마스킹"

DET_OUTPUT_DIR = "training/datasets/detection/aihub_full"
DET_YAML = "training/configs/aihub_yolo_detection.yaml"
SEG_OUTPUT_DIR = "training/datasets/segmentation/aihub_0820_26"
SEG_YAML = "training/configs/aihub_yolo_segmentation.yaml"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_env_value(key: str) -> str:
    env_path = project_root() / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(env_path)
    return os.getenv(key, "")


def resolve_dataset_root(arg_root: str | None) -> Path:
    root_text = arg_root or load_env_value("AIHUB_WALK_DATASET_ROOT")
    if not root_text:
        raise ValueError(
            "--dataset-root 또는 .env의 AIHUB_WALK_DATASET_ROOT 값을 지정해야 합니다."
        )
    root = Path(root_text).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"데이터셋 루트 폴더를 찾을 수 없습니다: {root}")
    return root


def run_step(command: list[str]) -> None:
    print(f"\n>>> {' '.join(command)}")
    subprocess.run(command, check=True, cwd=project_root())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="데스크탑에서 AI Hub 원천 데이터 변환과 YOLO 커스텀 풀 학습을 순서대로 실행합니다."
    )
    parser.add_argument(
        "--dataset-root",
        default=None,
        help="AI Hub 인도보행 영상 루트입니다. 기본값은 .env의 AIHUB_WALK_DATASET_ROOT 입니다.",
    )
    parser.add_argument("--skip-convert", action="store_true", help="데이터 변환 단계를 건너뜁니다.")
    parser.add_argument("--skip-train", action="store_true", help="학습 단계를 건너뜁니다.")
    parser.add_argument("--det-only", action="store_true", help="Detection만 실행합니다.")
    parser.add_argument("--seg-only", action="store_true", help="Segmentation만 실행합니다.")
    parser.add_argument("--device", default="0")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=-1)
    parser.add_argument("--det-limit", type=int, default=0, help="Detection 변환/학습용 이미지 제한입니다.")
    parser.add_argument("--seg-max-images", type=int, default=0, help="Segmentation 변환 이미지 제한입니다.")
    return parser.parse_args()
# [/VIBE CODE]


def main() -> int:
    args = parse_args()
    if args.det_only and args.seg_only:
        raise ValueError("--det-only 와 --seg-only 는 동시에 사용할 수 없습니다.")

    run_detection = not args.seg_only
    run_segmentation = not args.det_only
    dataset_root = resolve_dataset_root(args.dataset_root)
    bbox_root = dataset_root / BBOX_SUBDIR
    seg_root = dataset_root / SEG_SUBDIR
    python = sys.executable

    if not args.skip_convert:
        if run_detection:
            if not bbox_root.is_dir():
                raise FileNotFoundError(f"바운딩박스 데이터셋 폴더를 찾을 수 없습니다: {bbox_root}")
            
            det_cmd = [
                python, "scripts/prepare_aihub_yolo_detection.py",
                "--input-dir", str(bbox_root),
                "--output-dir", str(DET_OUTPUT_DIR),
                "--yaml-path", str(DET_YAML),
            ]
            if args.det_limit > 0: det_cmd.append(f"--limit {args.det_limit}")
            run_step(det_cmd)

        if run_segmentation:
            if not seg_root.is_dir():
                raise FileNotFoundError(f"서피스마스킹 폴더를 찾을 수 없습니다.! {seg_root}")
            seg_cmd = [
                python, "scripts/convert_aihub_seg_to_yolo.py",
                "--input-dir", str(seg_root),
                "--output-dir", str(SEG_OUTPUT_DIR),
                "--yaml-path", str(SEG_YAML),
            ]
            if args.seg_max_images > 0: seg_cmd.append(f"--max-images {args.seg_max_images}")
            run_step(seg_cmd)
    if not args.skip_train:
        train_common = ["--epochs", str(args.epochs), "--batch", str(args.batch), "--device", args.device]
        if run_detection:
            run_step([python, "training/train_detection.py", *train_common])
        if run_segmentation:
            run_step([python, "training/train_segmentation.py", *train_common])
        print("\n학습 완료.")
    # [/HARD CODE]

    # [VIBE CODE]
    print("\n데스크탑 커스텀 학습 파이프라인이 완료되었습니다.")
    if run_detection:
        print(f"Detection best.pt: outputs/yolo_train/aihub_det_v1/weights/best.pt")
    if run_segmentation:
        print(f"Segmentation best.pt: training/runs/seg_exp1/weights/best.pt")
    print("학습 후 .env 에 best.pt 경로를 지정하세요.")
    return 0
    # [/VIBE CODE]


if __name__ == "__main__":
    raise SystemExit(main())
