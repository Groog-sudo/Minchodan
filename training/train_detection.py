# -*- coding: utf-8 -*-
from __future__ import annotations

# [VIBE CODE] 표준 라이브러리 및 경로 설정
import argparse
import sys
from datetime import datetime
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
    parser = argparse.ArgumentParser(description="YOLO detection 모델 커스텀 학습을 실행합니다.")
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
    parser.add_argument("--project", default="outputs/yolo_train")
    current_time = datetime.now().strftime("%Y%m%d")
    parser.add_argument("--name", default=f"aihub_det_v1_{current_time}")
    add_common_train_args(parser)
    return parser.parse_args()
    # [/VIBE CODE]


def main() -> int:
    args = parse_args()
    
    # [HARD CODE] (담당자 직접 작성 영역)
    # 💡 [면접 대비 주석] 
    # Object Detection (YOLO 26N) 학습 실행 엔트리포인트입니다.
    # 54만 장 전체를 단순 풀 학습하는 대신, 클래스별 오탐 비중이 가장 낮은 이미지를 선별(클래스당 2,000장 수준)하여 학습을 수행했습니다.
    # 이 접근을 통해 데이터 라벨링 및 학습 시간을 획기적으로 줄이면서도 실무 환경에 최적화된 높은 정확도를 확보했습니다.
    best_pt = run_yolo_train(**vars(args))
    # [/HARD CODE]
    
    # [VIBE CODE]
    print(f"학습 완료. best.pt: {best_pt}")
    return 0
    # [/VIBE CODE]


if __name__ == "__main__":
    raise SystemExit(main())
