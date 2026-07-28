"""INT8 양자화 캘리브레이션용 대표 이미지 세트를 로컬 자산에서 조립한다.

INT8은 활성값(activation) 범위를 대표 데이터로 재서 스케일을 정하므로, 실제 추론
분포와 다른 데이터로 캘리브레이션하면 스케일이 어긋나 정확도가 크게 떨어진다.
ultralytics는 `data`를 주지 않으면 coco8을 내려받아 쓰는데, 보도 29클래스와 분포가
전혀 다르므로 반드시 본 스크립트로 만든 세트를 사용한다.

우선순위:
    1. data/event_frames  - 실기기가 실제 파이프라인으로 캡처한 640x640 프레임(최우선)
    2. data/seg_compare_real - 동일 규격 실촬영 프레임
    3. data/validation_samples - 해상도가 섞인 검증용 이미지(부족분 보충)

산출물은 data/int8_calibration/ 아래에 놓이며 이미지는 Git에 올라가지 않는다
(.gitignore의 전역 *.jpg 규칙). 실사용자 촬영 프레임이 포함되므로 저장소나 외부로
내보내지 않는다.

사용법:
    python scripts/build_int8_calibration_set.py
    python scripts/build_int8_calibration_set.py --limit 300
"""

import argparse
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# 우선순위 순서. 앞쪽이 실제 추론 분포에 가깝다.
SOURCE_DIRS = (
    os.path.join(PROJECT_ROOT, "data", "event_frames"),
    os.path.join(PROJECT_ROOT, "data", "seg_compare_real"),
    os.path.join(PROJECT_ROOT, "data", "validation_samples"),
)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "int8_calibration")
WEIGHTS_DIR = os.path.join(PROJECT_ROOT, "server", "models", "yolo26n")
IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def resolve_weights(model_name: str) -> str:
    """export_tflite.py와 동일한 가중치 탐색 규칙을 따른다."""
    primary = os.path.join(WEIGHTS_DIR, f"{model_name}260714.pt")
    fallback = os.path.join(WEIGHTS_DIR, f"{model_name}.pt")
    if os.path.exists(primary):
        return primary
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError(f"가중치 없음: {primary} 또는 {fallback}")


DET_NAMES = [
    "barricade",
    "bench",
    "bicycle",
    "bollard",
    "bus",
    "car",
    "carrier",
    "cat",
    "chair",
    "dog",
    "fire_hydrant",
    "kiosk",
    "motorcycle",
    "movable_signage",
    "parking_meter",
    "person",
    "pole",
    "potted_plant",
    "power_controller",
    "scooter",
    "stop",
    "stroller",
    "table",
    "traffic_light",
    "traffic_light_controller",
    "traffic_sign",
    "tree_trunk",
    "truck",
    "wheelchair",
]
SEG_NAMES = ["sidewalk_normal", "caution", "roadway", "braille_normal"]


def collect_images(limit: int) -> list[str]:
    """우선순위 순서로 이미지를 모은다. limit에 도달하면 즉시 중단한다."""
    collected: list[str] = []
    for source in SOURCE_DIRS:
        if not os.path.isdir(source):
            print(f"[WARN] 원본 디렉터리 없음, 건너뜀: {source}")
            continue
        found = 0
        for root, _, files in os.walk(source):
            for name in sorted(files):
                if not name.lower().endswith(IMAGE_EXTS):
                    continue
                collected.append(os.path.join(root, name))
                found += 1
                if len(collected) >= limit:
                    print(f"[INFO] {os.path.relpath(source, PROJECT_ROOT)}: {found}장")
                    return collected
        print(f"[INFO] {os.path.relpath(source, PROJECT_ROOT)}: {found}장")
    return collected


def write_yaml(path: str, root: str, names: list[str]) -> None:
    """ultralytics가 캘리브레이션에 쓰는 최소 데이터셋 yaml을 만든다.

    ultralytics는 val 스플릿을 캘리브레이션 표본으로 읽는다. 양자화 스케일은 이미지가
    모델을 통과하며 나오는 활성값으로 정해지므로 라벨 내용 자체는 결과에 영향이 없으나,
    데이터로더가 "라벨 전부 비어 있음"을 오류로 처리하기 때문에 라벨 파일이 필요하다.
    아래 pseudo_label()이 원본 모델의 예측을 라벨로 적어 이 요건을 채운다.
    """
    lines = [
        "# 자동 생성 파일 - scripts/build_int8_calibration_set.py",
        "# INT8 캘리브레이션 전용. 라벨이 원본 모델의 의사 라벨이므로 mAP 평가에 쓸 수 없다.",
        f"path: {root}",
        "train: images/val",
        "val: images/val",
        "names:",
    ]
    lines.extend(f"  {i}: {n}" for i, n in enumerate(names))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[INFO] yaml 생성: {path}")


def pseudo_label(weights: str, images_dir: str, labels_dir: str, task: str) -> int:
    """원본 .pt 모델로 캘리브레이션 이미지에 의사 라벨을 적는다.

    라벨이 하나도 없으면 ultralytics 데이터로더가 export를 중단시킨다. 사람이 단 정답이
    아니라 원본 모델의 예측이므로 정확도 평가 용도로는 쓸 수 없다.
    """
    from ultralytics import YOLO

    model = YOLO(weights)
    os.makedirs(labels_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(images_dir) if f.lower().endswith(IMAGE_EXTS))
    labeled = 0
    for name in files:
        stem = os.path.splitext(name)[0]
        result = model.predict(os.path.join(images_dir, name), verbose=False, conf=0.25)[0]
        lines: list[str] = []
        if task == "segment" and result.masks is not None:
            for cls, poly in zip(result.boxes.cls.tolist(), result.masks.xyn, strict=False):
                if len(poly) < 3:
                    continue
                coords = " ".join(f"{x:.6f} {y:.6f}" for x, y in poly)
                lines.append(f"{int(cls)} {coords}")
        elif task == "detect" and result.boxes is not None:
            for cls, box in zip(
                result.boxes.cls.tolist(), result.boxes.xywhn.tolist(), strict=False
            ):
                cx, cy, w, h = box
                lines.append(f"{int(cls)} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        # 예측이 0건인 이미지도 캘리브레이션 표본으로는 유효하다. 다만 데이터로더가
        # 전부 비어 있으면 중단하므로, 최소 1건이라도 남는지 아래에서 확인한다.
        if lines:
            labeled += 1
        with open(os.path.join(labels_dir, f"{stem}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"[INFO] 의사 라벨 {labeled}/{len(files)}장 생성 ({task})")
    return labeled


def main() -> int:
    parser = argparse.ArgumentParser(description="INT8 캘리브레이션 이미지 세트 조립")
    parser.add_argument(
        "--limit",
        type=int,
        default=300,
        help="사용할 최대 이미지 수 (기본값: 300). INT8 캘리브레이션은 통상 100~500장이면 충분합니다.",
    )
    args = parser.parse_args()

    images = collect_images(args.limit)
    if not images:
        print("[ERROR] 캘리브레이션에 쓸 이미지를 찾지 못했습니다.")
        return 1

    # ultralytics는 이미지 경로의 /images/를 /labels/로 바꿔 라벨을 찾는다. det와 seg가
    # 같은 루트를 쓰면 라벨이 서로 덮이므로 태스크별로 루트를 나눈다.
    tasks = (
        ("detection", "object_detection", "detect", DET_NAMES),
        ("segmentation", "segmentation", "segment", SEG_NAMES),
    )
    for root_name, model_name, task, names in tasks:
        root = os.path.join(OUTPUT_DIR, root_name)
        images_dir = os.path.join(root, "images", "val")
        labels_dir = os.path.join(root, "labels", "val")
        if os.path.isdir(root):
            shutil.rmtree(root)
        os.makedirs(images_dir, exist_ok=True)

        for idx, src in enumerate(images):
            ext = os.path.splitext(src)[1].lower()
            shutil.copy2(src, os.path.join(images_dir, f"calib_{idx:04d}{ext}"))

        weights = resolve_weights(model_name)
        labeled = pseudo_label(weights, images_dir, labels_dir, task)
        if labeled == 0:
            print(
                f"[ERROR] {root_name}: 의사 라벨이 한 건도 생성되지 않아 "
                "ultralytics 데이터로더가 export를 중단시킵니다."
            )
            return 1

        write_yaml(os.path.join(OUTPUT_DIR, f"{root_name}.yaml"), root, names)
        print(f"[SUMMARY] {root_name}: 이미지 {len(images)}장 -> {images_dir}")

    print("[SUMMARY] 다음 단계:")
    print(
        "  .venv/bin/python scripts/export_tflite.py --model object_detection --int8 "
        f"--data {os.path.join(OUTPUT_DIR, 'detection.yaml')} --out-suffix _int8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
