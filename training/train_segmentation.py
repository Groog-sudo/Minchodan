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
    # 💡 [면접 대비 주석]
    # Segmentation 파인튜닝 실행 엔트리포인트입니다.
    # 시각장애인 보행 시 치명적인 노면 상태(점자블록 파손, 횡단보도 진입, 계단/맨홀 등)를 단순 박스가 아닌 픽셀 단위 마스크로 정밀하게 파악하기 위해,
    # C2 아키텍처 원칙에 따라 노면 클래스를 독립적으로 분리하여 세그멘테이션 전용 파이프라인으로 학습시켰습니다.
    best_pt = run_yolo_train(**vars(args))
    # [/HARD CODE]

    # [VIBE CODE]
    print(f"학습 완료. best.pt: {best_pt}")
    return 0
    # [/VIBE CODE]


if __name__ == "__main__":
    raise SystemExit(main())
