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


def export_one(
    model_name: str,
    half: bool = True,
    int8: bool = False,
    imgsz: int = 640,
    data: str | None = None,
    out_suffix: str = "",
) -> str:
    weights = resolve_weights(model_name)
    print(f"[INFO] {model_name}: {weights} -> tflite (half={half}, int8={int8}, imgsz={imgsz})")
    model = YOLO(weights)
    export_kwargs: dict = {"format": "tflite", "imgsz": imgsz, "int8": int8, "half": half}
    # INT8은 대표 데이터로 활성값 범위를 재는 캘리브레이션이 필요하다. data를 넘기지 않으면
    # ultralytics가 조용히 coco8을 내려받아 캘리브레이션하는데, 보도 29클래스와 분포가 달라
    # 양자화 스케일이 어긋난다. main()에서 필수로 강제하고 여기서도 실제 경로를 전달한다.
    if int8:
        if not data:
            raise ValueError("INT8 export에는 --data 캘리브레이션 데이터셋이 필요합니다.")
        export_kwargs["data"] = data
        print(f"[INFO] INT8 캘리브레이션 데이터셋: {data}")
    # detect는 NMS 미포함([1, 4+nc, 8400] channels-first)으로 보낸다.
    # NON_MAX_SUPPRESSION_V4 가 NNAPI/GPU delegate와 비호환이라 JS NMS로 후처리한다.
    # (CoreML iOS 경로는 nms=True 유지 — scripts/export_mobile.py / convert_yolo_to_coreml.py)
    if model_name == "object_detection" and model.task == "detect":
        export_kwargs["nms"] = False
    exported_path = str(model.export(**export_kwargs))
    if not os.path.isabs(exported_path):
        exported_path = os.path.join(PROJECT_ROOT, exported_path)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # out_suffix를 주면 배포본을 덮지 않고 별도 파일로 떨군다. 정확도 검증 전의 실험용
    # 산출물이 그대로 앱에 실려 나가는 것을 막는다.
    target = os.path.join(OUTPUT_DIR, f"{model_name}{out_suffix}.tflite")
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
    parser.add_argument(
        "--half",
        action="store_true",
        default=True,
        help="FP16(half) 정밀도로 TFLite export (기본값: True)",
    )
    parser.add_argument(
        "--fp32",
        action="store_true",
        help="FP32(full) 정밀도로 TFLite export",
    )
    parser.add_argument(
        "--int8",
        action="store_true",
        help="INT8 정밀도로 TFLite export",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="입력 이미지 크기 (기본값: 640)",
    )
    parser.add_argument(
        "--data",
        help="INT8 캘리브레이션 데이터셋 yaml 경로 (--int8 사용 시 필수). "
        "scripts/build_int8_calibration_set.py로 생성할 수 있습니다.",
    )
    parser.add_argument(
        "--out-suffix",
        default="",
        help="산출물 파일명 접미사 (예: _int8). 미지정 시 배포본을 덮어씁니다.",
    )
    args = parser.parse_args()
    targets = [args.model] if args.model else list(MODELS)
    use_half = False if args.fp32 else (args.half and not args.int8)

    if args.int8 and not args.data:
        print(
            "[ERROR] --int8에는 --data가 필요합니다. data 없이 내보내면 ultralytics가 coco8을 "
            "내려받아 캘리브레이션하며, 보도 29클래스 분포와 달라 양자화 스케일이 어긋납니다.\n"
            "        먼저 python scripts/build_int8_calibration_set.py 를 실행하십시오."
        )
        return 1

    failed: list[str] = []
    for name in targets:
        try:
            export_one(
                name,
                half=use_half,
                int8=args.int8,
                imgsz=args.imgsz,
                data=args.data,
                out_suffix=args.out_suffix,
            )
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
