# -*- coding: utf-8 -*-
from __future__ import annotations
from ultralytics import YOLO

# [VIBE CODE]
# 외부 라이브러리 및 표준 라이브러리 임포트, 유틸리티 함수 등 담당자의 체력을 보호하기 위해 LLM이 작성한 보조 코드 영역입니다.
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (project_root() / candidate).resolve()


def add_common_train_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--batch",
        type=int,
        default=-1,
        help="배치 크기입니다. -1이면 GPU 메모리에 맞춰 자동 설정합니다.",
    )
    parser.add_argument("--device", default="0", help="학습 디바이스입니다. 예: 0, cpu")
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--resume", action="store_true", help="중단된 학습을 이어서 진행합니다.")
# [/VIBE CODE]


def run_yolo_train(
    *,
    data: str,
    model: str,
    project: str,
    name: str,
    epochs: int,
    imgsz: int,
    batch: int,
    device: str,
    patience: int,
    workers: int,
    resume: bool,
) -> Path:
    # [VIBE CODE] 경로 검증 및 디렉토리 생성
    data_path = resolve_path(data)
    model_path = resolve_path(model)
    if not data_path.is_file():
        raise FileNotFoundError(f"dataset yaml을 찾을 수 없습니다: {data_path}")
    if not model_path.is_file():
        raise FileNotFoundError(f"모델 weight를 찾을 수 없습니다: {model_path}")

    project_path = resolve_path(project)
    project_path.mkdir(parents=True, exist_ok=True)
    # [/VIBE CODE]

    # [HARD CODE] (담당자 직접 작성 영역)
    model_obj = YOLO(str(model_path))
    train_kwargs: dict = {
        "data": str(data_path),
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "project": str(project_path),
        "name": name,
        "patience": patience,
        "workers": workers,
        "exist_ok": True,
        "verbose": True,
    }
    if resume:
        train_kwargs["resume"] = True
    model_obj.train(**train_kwargs)
    return model_obj.path / name / "weights" / "best.pt"
    # [/HARD CODE]