#!/usr/bin/env python3
"""
Post-MVP 포스트 A: 모바일 추론용 모델 익스포트 스크립트.

학습된 YOLO26n *260714.pt (server/models/yolo26n/)를 CoreML/TFLite 포맷으로 변환한다.
변환된 파일은 client/assets/models/yolo26n/ 에 적재되어 단말 NPU 추론에 사용된다.

Post-MVP 하이브리드 온디바이스 로드맵 (docs/post_mvp_hybrid_roadmap.md) 7.2절 참조.

검증 항목:
    - CoreML 익스포트 성공 (.mlpackage 파일 생성)
    - NMS-Free 정합성 (서버 대비 탐지 결과 일치율 >= 90%)
    - 모바일 NPU 추론 레이턴시 10~30ms 이내
    - 탐지 정확도 손실 mAP <= 5% (서버 대비)

사용법:
    # 환경 변수는 .env에서 자동 로드 (guide 3.4)
    python scripts/export_mobile.py --model object_detection --format coreml
    python scripts/export_mobile.py --model segmentation --format tflite
    python scripts/export_mobile.py --all --format coreml
"""

import argparse
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

env_path = os.path.join(project_root, ".env")
if load_dotenv is not None and os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

MODELS = {
    # 2026-07-15: 서버·앱 공통 기준선은 *260714.pt (object_detection.pt는 동일 해시 별칭)
    "object_detection": os.path.join(
        project_root, "server", "models", "yolo26n", "object_detection260714.pt"
    ),
    "segmentation": os.path.join(
        project_root, "server", "models", "yolo26n", "segmentation260714.pt"
    ),
}

OUTPUT_DIR = os.path.join(project_root, "client", "assets", "models", "yolo26n")

SUPPORTED_FORMATS = ("coreml", "tflite", "onnx", "openvino")


def replace_path(src: str, dst: str) -> None:
    """기존 대상 파일 또는 디렉터리를 제거하고 src를 dst로 이동한다."""
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    elif os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)


def target_path_for(model_key: str, fmt: str, export_path: str, output_dir: str) -> str:
    """모바일 에셋 디렉터리에 저장할 표준 파일명을 계산한다."""
    if fmt == "coreml":
        return os.path.join(output_dir, f"{model_key}.mlpackage")
    ext = os.path.splitext(export_path)[1] or f".{fmt}"
    return os.path.join(output_dir, f"{model_key}{ext}")


def export_model(model_key: str, fmt: str, output_dir: str) -> str | None:
    """지정한 모델을 지정한 포맷으로 익스포트한다.

    Returns:
        익스포트된 파일 경로 또는 실패 시 None.
    """
    if model_key not in MODELS:
        print(f"[ERROR] 알 수 없는 모델 키: {model_key}")
        print(f"  지원 모델: {', '.join(MODELS.keys())}")
        return None

    weights_path = MODELS[model_key]
    if not os.path.exists(weights_path):
        print(f"[ERROR] 가중치 파일 없음: {weights_path}")
        return None

    if fmt not in SUPPORTED_FORMATS:
        print(f"[ERROR] 지원하지 않는 포맷: {fmt}")
        print(f"  지원 포맷: {', '.join(SUPPORTED_FORMATS)}")
        return None

    os.makedirs(output_dir, exist_ok=True)

    print(f"[INFO] {model_key}: {weights_path} -> {fmt}")
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics 미설치. pip install ultralytics 후 재시도.")
        return None

    try:
        model = YOLO(weights_path)
        export_kwargs = {"format": fmt}
        if model_key == "object_detection":
            # TFLite: NMS 그래프 제외(Android NNAPI/GPU 호환). JS nonMaxSuppression 후처리.
            # CoreML: iOS Vision 계약용 nms=True 유지.
            if fmt == "tflite":
                export_kwargs["nms"] = False
            elif fmt == "coreml":
                export_kwargs["nms"] = True
        export_path = str(model.export(**export_kwargs))
        target_path = target_path_for(model_key, fmt, export_path, output_dir)
        replace_path(export_path, target_path)
        print(f"[INFO] 익스포트 성공: {target_path}")
        return target_path
    except Exception as e:
        print(f"[ERROR] 익스포트 실패 ({model_key} -> {fmt}): {e}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Minchodan Post-MVP 모바일 모델 익스포트 (포스트 A)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--model",
        choices=list(MODELS.keys()),
        help="익스포트할 모델 키",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="MODELS에 정의된 모든 모델 익스포트",
    )
    parser.add_argument(
        "--format",
        choices=SUPPORTED_FORMATS,
        default="coreml",
        help="타겟 포맷 (기본: coreml)",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"출력 디렉토리 (기본: {OUTPUT_DIR})",
    )
    args = parser.parse_args()

    targets = list(MODELS.keys()) if args.all else [args.model]

    success_count = 0
    failed: list[str] = []
    for key in targets:
        result = export_model(key, args.format, args.output_dir)
        if result is None:
            failed.append(key)
        else:
            success_count += 1

    print()
    print(f"[SUMMARY] 성공 {success_count}/{len(targets)}")
    if failed:
        print(f"[SUMMARY] 실패 모델: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
