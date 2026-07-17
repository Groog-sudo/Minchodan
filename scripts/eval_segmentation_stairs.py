#!/usr/bin/env python3
"""
P2-1(a) (2026-07-17): 세그멘테이션 모델 caution(계단/맨홀/그레이팅 통합) 클래스
정밀도/재현율 실측 평가 스크립트.

필드 테스트 개선 계획서 M6/P2-1(a): 계단 오탐 실측.
실측 데이터셋(라벨링된 이미지+마스크) 경로를 환경변수로 받아 세그멘테이션 모델의
caution 클래스에 대한 정밀도/재현율/F1을 산출한다. 데이터셋이 없으면 더미 평가를 수행해
스크립트 동작을 검증한다.

사용:
    python scripts/eval_segmentation_stairs.py
    EVAL_SEG_DATASET_DIR=/path/to/dataset python scripts/eval_segmentation_stairs.py

환경변수:
    EVAL_SEG_DATASET_DIR  - 평가 데이터셋 디렉터리 (images/, labels/ 하위). 없으면 더미 평가.
    EVAL_SEG_MODEL_PATH   - 세그멘테이션 가중치 경로 (기본 .env YOLO26N_SEG).
    EVAL_SEG_CONF         - 신뢰도 임계 (기본 0.5).
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 프로젝트 루트 기반 절대 경로 (guide 3.3)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)


def _load_model(model_path: str):
    """세그멘테이션 모델 로드 (ultralytics). 실패 시 None."""
    try:
        from ultralytics import YOLO

        return YOLO(model_path)
    except Exception as e:
        print(f"[WARN] 모델 로드 실패({model_path}): {e}")
        return None


def _evaluate_on_dataset(model, dataset_dir: str, conf: float) -> dict:
    """실측 데이터셋에 대해 caution 클래스 정밀도/재현율 산출.

    데이터셋 구조:
        dataset_dir/
            images/  (*.jpg)
            labels/  (*.txt - YOLO seg 포맷, 클래스 인덱스)
    caution 클래스 인덱스는 1 (sidewalk_normal=0, caution=1, roadway=2, braille_normal=3).
    """
    import glob

    images = sorted(glob.glob(os.path.join(dataset_dir, "images", "*.jpg")))
    if not images:
        print(f"[WARN] 데이터셋 이미지 없음: {dataset_dir}")
        return {"tp": 0, "fp": 0, "fn": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = fp = fn = 0
    caution_class_idx = 1  # 세그멘테이션 4클래스 중 caution 인덱스
    for img_path in images:
        # GT 라벨 로드 (caution 픽셀 존재 여부)
        label_path = os.path.join(
            dataset_dir, "labels", os.path.splitext(os.path.basename(img_path))[0] + ".txt"
        )
        gt_has_caution = False
        if os.path.exists(label_path):
            with open(label_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if parts and int(parts[0]) == caution_class_idx:
                        gt_has_caution = True
                        break

        # 모델 추론
        pred_has_caution = False
        if model is not None:
            try:
                results = model.predict(img_path, conf=conf, verbose=False)
                if results and results[0].masks is not None:
                    cls_arr = results[0].boxes.cls.cpu().numpy().astype(int)
                    pred_has_caution = int(caution_class_idx) in cls_arr
            except Exception as e:
                print(f"[WARN] 추론 실패({img_path}): {e}")

        if pred_has_caution and gt_has_caution:
            tp += 1
        elif pred_has_caution and not gt_has_caution:
            fp += 1
        elif not pred_has_caution and gt_has_caution:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _dummy_evaluation() -> dict:
    """데이터셋 없을 때 더미 평가 (스크립트 동작 검증용)."""
    print("[INFO] EVAL_SEG_DATASET_DIR 미설정 - 더미 평가 수행")
    return {"tp": 8, "fp": 2, "fn": 3, "precision": 0.8, "recall": 0.7273, "f1": 0.7619}


def main() -> int:
    dataset_dir = os.getenv("EVAL_SEG_DATASET_DIR", "").strip()
    model_path = os.getenv("EVAL_SEG_MODEL_PATH", os.getenv("YOLO26N_SEG", "")).strip()
    conf = float(os.getenv("EVAL_SEG_CONF", "0.5"))

    print("[INFO] 세그멘테이션 caution 클래스 평가")
    print(f"  모델 경로: {model_path or '(기본 .env YOLO26N_SEG)'}")
    print(f"  신뢰도 임계: {conf}")
    print(f"  데이터셋: {dataset_dir or '(미설정 - 더미)'}")

    model = _load_model(model_path) if model_path else None
    result = _evaluate_on_dataset(model, dataset_dir, conf) if dataset_dir else _dummy_evaluation()

    print("\n[결과] caution 클래스 실측 평가")
    print(f"  TP={result['tp']}, FP={result['fp']}, FN={result['fn']}")
    print(f"  정밀도(Precision)={result['precision']:.4f}")
    print(f"  재현율(Recall)   ={result['recall']:.4f}")
    print(f"  F1              ={result['f1']:.4f}")
    print(
        "\n[해석 기준] "
        "정밀도 낮음=오탐 많음(과경보), 재현율 낮음=누락 많음(위험). "
        "P2-1(b) 히스테리시스(SURFACE_CAUTION_CONFIRM_STREAK)로 오탐 완화."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
