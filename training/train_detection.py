# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLO detection 모델 학습을 실행합니다.")
    parser.add_argument(
        "--data",
        default="training/configs/aihub_yolo_detection.yaml",
        help="Ultralytics dataset yaml 경로입니다.",
    )
    parser.add_argument(
        "--model",
        default="server/models/yolo26n/object_detection.pt",
        help="학습 시작 weight 경로입니다.",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--name", default="aihub_yolo_detection_smoke")
    parser.add_argument("--project", default="outputs/yolo_train")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_path = Path(args.data)
    model_path = Path(args.model)
    if not data_path.is_file():
        raise FileNotFoundError(f"dataset yaml을 찾을 수 없습니다: {data_path}")
    if not model_path.is_file():
        raise FileNotFoundError(f"모델 weight를 찾을 수 없습니다: {model_path}")

    from ultralytics import YOLO

    project_path = Path(args.project).resolve()
    project_path.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(model_path))
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(project_path),
        name=args.name,
        exist_ok=True,
        verbose=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
