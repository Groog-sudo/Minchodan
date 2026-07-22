import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from ultralytics import YOLO

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

RAW_ROOT = PROJECT_ROOT / "data" / "validation_samples" / "raw"
RESULT_ROOT = PROJECT_ROOT / "data" / "validation_samples" / "results"

DET_MODEL_PATH = PROJECT_ROOT / "server" / "models" / "yolo26n" / "det_best_20260705.pt"
SEG_MODEL_PATH = PROJECT_ROOT / "server" / "models" / "yolo26n" / "segbest.pt"

# Object Detection 29 클래스 (det_best_20260705.pt 학습 순서와 정합, useOnDeviceDetection.ts 참조)
DET_CLASS_NAMES = [
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

# Segmentation 4 클래스 (training/configs/aihub_yolo_segmentation.yaml 정합)
SEG_CLASS_NAMES = ["sidewalk_normal", "caution", "roadway", "braille_normal"]


def collect_class_images(class_name: str) -> list[Path]:
    class_dir = RAW_ROOT / class_name
    if not class_dir.is_dir():
        return []
    return sorted(
        path
        for path in class_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def run_group(model: YOLO, class_names: list[str], group_label: str, conf: float) -> list[dict]:
    result_dir = RESULT_ROOT / group_label
    result_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    for class_name in class_names:
        image_paths = collect_class_images(class_name)
        if not image_paths:
            summary.append({"class_name": class_name, "images": 0, "detections": 0})
            print(f"[{group_label}] {class_name}: 샘플 이미지 없음 (건너뜀)")
            continue

        class_result_dir = result_dir / class_name
        class_result_dir.mkdir(parents=True, exist_ok=True)

        total_detections = 0
        for image_path in image_paths:
            results = model.predict(source=str(image_path), conf=conf, verbose=False)
            result = results[0]
            num_boxes = 0 if result.boxes is None else len(result.boxes)
            total_detections += num_boxes

            annotated = result.plot(conf=True, labels=True)
            out_path = class_result_dir / f"{image_path.stem}_result.jpg"
            cv2.imwrite(str(out_path), annotated)

            top_conf = None
            if result.boxes is not None and len(result.boxes) > 0:
                top_conf = float(result.boxes.conf.max())
            print(
                f"[{group_label}] {class_name}/{image_path.name}: "
                f"박스={num_boxes} 최고신뢰도={top_conf if top_conf is not None else 'N/A'} -> {out_path.relative_to(PROJECT_ROOT)}"
            )

        summary.append(
            {
                "class_name": class_name,
                "images": len(image_paths),
                "detections": total_detections,
            }
        )

    return summary


def print_summary(title: str, summary: list[dict]) -> None:
    print(f"\n=== {title} 요약 ===")
    zero_hit = []
    no_sample = []
    for row in summary:
        print(f"{row['class_name']:<28} 이미지={row['images']} 총탐지수={row['detections']}")
        if row["images"] == 0:
            no_sample.append(row["class_name"])
        elif row["detections"] == 0:
            zero_hit.append(row["class_name"])
    if no_sample:
        print(f"샘플 이미지 없는 클래스: {', '.join(no_sample)}")
    if zero_hit:
        print(f"샘플은 있으나 탐지 0건인 클래스: {', '.join(zero_hit)}")


def main() -> None:
    if not DET_MODEL_PATH.exists():
        raise FileNotFoundError(f"Object Detection 가중치를 찾을 수 없습니다: {DET_MODEL_PATH}")
    if not SEG_MODEL_PATH.exists():
        raise FileNotFoundError(f"Segmentation 가중치를 찾을 수 없습니다: {SEG_MODEL_PATH}")

    det_model = YOLO(str(DET_MODEL_PATH))
    seg_model = YOLO(str(SEG_MODEL_PATH))

    det_summary = run_group(det_model, DET_CLASS_NAMES, "detection", conf=0.25)
    seg_summary = run_group(seg_model, SEG_CLASS_NAMES, "segmentation", conf=0.25)

    print_summary("Object Detection", det_summary)
    print_summary("Segmentation", seg_summary)


if __name__ == "__main__":
    main()
