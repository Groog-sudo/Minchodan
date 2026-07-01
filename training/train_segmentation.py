# -*- coding: utf-8 -*-
from __future__ import annotations

# [VIBE CODE] 표준 라이브러리 및 경로 설정
import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from training.train_common import add_common_train_args, run_yolo_train

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
# [/VIBE CODE]


def parse_args() -> argparse.Namespace:
    # [VIBE CODE] 단순 CLI 인자 설정
    parser = argparse.ArgumentParser(description="YOLO segmentation 모델 커스텀 학습을 실행합니다.")
    parser.add_argument(
        "--data",
        default="training/configs/aihub_yolo_segmentation.yaml",
        help="Ultralytics dataset yaml 경로입니다.",
    )
    parser.add_argument(
        "--model",
        default="server/models/yolo26n/segmentation.pt",
        help="학습 시작 weight 경로입니다.",
    )
    parser.add_argument("--project", default="training/runs")
    parser.add_argument("--name", default="seg_exp1")
    add_common_train_args(parser)
    return parser.parse_args()
    # [/VIBE CODE]


def main() -> int:
    args = parse_args()
    
    # [HARD CODE] (담당자 직접 작성 영역)
    best_pt = run_yolo_train(
        data=args.data,
        model=args.model,
        project=args.project,
        name=args.name,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        workers=args.workers,
        resume=args.resume,
    )
    # [/HARD CODE]
    
    # [VIBE CODE]
    print(f"학습 완료. best.pt: {best_pt}")
    return 0
    # [/VIBE CODE]


if __name__ == "__main__":
    raise SystemExit(main())
