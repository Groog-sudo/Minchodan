"""
server/models/yolo26n/*260714.pt 를 모바일 온디바이스용 TFLite로 변환한다.
산출물은 client/assets/models/yolo26n/<model>.tflite 에 배치한다.

사용법:
    python scripts/export_tflite.py
    python scripts/export_tflite.py --model object_detection
    python scripts/export_tflite.py --model segmentation
"""

import argparse
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from ultralytics import YOLO
except ImportError:
    print(
        "Error: ultralytics 라이브러리가 설치되어 있지 않습니다. requirements.txt를 확인해 주십시오."
    )
    sys.exit(1)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
WEIGHTS_DIR = os.path.join(PROJECT_ROOT, "server", "models", "yolo26n")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "client", "assets", "models", "yolo26n")

MODELS = ("object_detection", "segmentation")


def resolve_weights(model_name: str) -> str:
    primary = os.path.join(WEIGHTS_DIR, f"{model_name}260714.pt")
    fallback = os.path.join(WEIGHTS_DIR, f"{model_name}.pt")
    if os.path.exists(primary):
        return primary
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError(f"가중치 없음: {primary} 또는 {fallback}")


def export_one(model_name: str) -> str:
    weights = resolve_weights(model_name)
    print(f"[INFO] {model_name}: {weights} -> tflite")
    model = YOLO(weights)
    export_kwargs: dict = {"format": "tflite", "imgsz": 640, "int8": False}
    # detect는 NMS 내장([1,300,6])으로 내보내 서버·CoreML 계약과 맞춘다.
    if model_name == "object_detection" and model.task == "detect":
        export_kwargs["nms"] = True
    exported_path = str(model.export(**export_kwargs))
    if not os.path.isabs(exported_path):
        exported_path = os.path.join(PROJECT_ROOT, exported_path)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    target = os.path.join(OUTPUT_DIR, f"{model_name}.tflite")
    if os.path.exists(target):
        os.remove(target)
    # ultralytics는 종종 *_saved_model/ 디렉터리 + .tflite 파일을 만든다.
    if os.path.isdir(exported_path):
        candidates = [
            os.path.join(exported_path, name)
            for name in os.listdir(exported_path)
            if name.endswith(".tflite")
        ]
        if not candidates:
            raise FileNotFoundError(f"TFLite 산출물 없음: {exported_path}")
        exported_path = candidates[0]
    shutil.move(exported_path, target)
    print(f"[INFO] 배치 완료: {target}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="YOLO26n *260714.pt -> TFLite 변환")
    parser.add_argument(
        "--model",
        choices=list(MODELS),
        help="변환할 모델 (미지정 시 det+seg 모두)",
    )
    args = parser.parse_args()
    targets = [args.model] if args.model else list(MODELS)

    failed: list[str] = []
    for name in targets:
        try:
            export_one(name)
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            failed.append(name)

    if failed:
        print(f"[SUMMARY] 실패: {', '.join(failed)}")
        return 1
    print("[SUMMARY] 모든 TFLite 변환 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
