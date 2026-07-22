"""Import AI Hub Segmentation data (JSON Polygon) into local YOLO format."""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seg_config import SEG_CLASS_ALIASES, SEG_CLASS_TO_ID, SEG_DATASET_ROOT
from utils.format_converter import HashIndex, safe_image_open


def extract_seg_label(raw_label: str) -> str | None:
    """Extract and map segmentation labels."""
    raw_label = raw_label.lower().strip()

    if raw_label in SEG_CLASS_TO_ID:
        return raw_label
    if raw_label in SEG_CLASS_ALIASES:
        return SEG_CLASS_ALIASES[raw_label]

    # Heuristics based on AI Hub common labels
    if (
        "floor_normal" in raw_label
        or "sidewalk" in raw_label
        or "보도" in raw_label
        or "인도" in raw_label
    ):
        return "sidewalk_normal"
    if "braille" in raw_label or "점자" in raw_label or "유도블록" in raw_label:
        return "braille_normal"
    if "road" in raw_label or "차도" in raw_label or "도로" in raw_label:
        return "roadway"
    if (
        "damage" in raw_label
        or "파손" in raw_label
        or "턱" in raw_label
        or "경사로" in raw_label
        or "웅덩이" in raw_label
        or "공사" in raw_label
        or "curb" in raw_label
        or "계단" in raw_label
        or "stairs" in raw_label
        or "step" in raw_label
    ):
        return "caution"

    return None


def process_aihub_seg_json(
    json_path: Path, image_dir: Path, label_dir: Path, hash_index: HashIndex
) -> int:
    """Process JSON containing polygon segmentations."""
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read JSON {json_path.name}: {e}")
        return 0

    info = data.get("info", {})
    filename = info.get("filename") or data.get("images", {}).get("file_name")

    width = info.get("width") or data.get("images", {}).get("width")
    height = info.get("height") or data.get("images", {}).get("height")

    if not filename or not width or not height:
        return 0

    annotations = data.get("annotations", [])
    yolo_lines = []

    for ann in annotations:
        raw_label = str(ann.get("category_id", "") or ann.get("label_name", ""))
        label = extract_seg_label(raw_label)
        if not label:
            continue

        class_id = SEG_CLASS_TO_ID[label]

        # In YOLO Segmentation, the format is class_id x1 y1 x2 y2 ... (normalized 0-1)
        segmentation = ann.get("segmentation", [])
        if not segmentation:
            continue

        # segmentation might be a list of [x,y] pairs or a flat list [x1, y1, x2, y2...]
        flat_coords = []
        if isinstance(segmentation[0], list):
            for point in segmentation:
                if len(point) >= 2:
                    flat_coords.extend(
                        [float(point[0]) / float(width), float(point[1]) / float(height)]
                    )
        else:
            for i in range(0, len(segmentation), 2):
                flat_coords.extend(
                    [
                        float(segmentation[i]) / float(width),
                        float(segmentation[i + 1]) / float(height),
                    ]
                )

        if len(flat_coords) < 6:  # Minimum 3 points for a polygon
            continue

        # Clip coordinates to 0.0 - 1.0 to avoid YOLO errors
        flat_coords = [max(0.0, min(1.0, c)) for c in flat_coords]

        yolo_lines.append(f"{class_id} " + " ".join(f"{v:.6f}" for v in flat_coords))

    if not yolo_lines:
        return 0

    # Locate image
    img_candidates = [
        json_path.parent / filename,
        json_path.parent.parent / "images" / filename,
        json_path.parent.parent / "원천데이터" / filename,
    ]

    img_path = None
    for cand in img_candidates:
        if cand.exists():
            img_path = cand
            break

    if not img_path:
        # Search from the dataset root (e.g. New_sample) instead of just the json's parent
        # We assume the parent of the parent of the parent might be the root,
        # or we can just search from SETTINGS.dataset_root / "raw"
        raw_dir = Path(str(json_path).split("raw")[0]) / "raw"
        found = list((raw_dir / "New_sample").rglob(filename))
        if not found:
            # Fallback search globally in raw
            found = list(raw_dir.rglob(filename))

        if found:
            img_path = found[0]

    if not img_path or not img_path.exists():
        print(f"[WARN] Image {filename} not found for {json_path.name}")
        return 0

    output_stem = f"aihub_seg_{json_path.stem}"
    out_img = image_dir / f"{output_stem}.jpg"
    out_lbl = label_dir / f"{output_stem}.txt"

    with safe_image_open(img_path) as img:
        if img is None:
            return 0
        if hash_index.duplicate_source(img):
            return 0
        hash_index.add(img, str(out_img))
        shutil.copy(img_path, out_img)

    out_lbl.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Import AI Hub Segmentation Annotations.")
    parser.add_argument(
        "input_dir", type=Path, help="Directory containing raw AI Hub JSON and images"
    )
    parser.add_argument("--output", type=Path, default=SEG_DATASET_ROOT, help="Output dataset root")
    parser.add_argument(
        "--env",
        type=str,
        choices=["indoor", "outdoor", "mixed"],
        default="mixed",
        help="Environment tag to split the dataset folder",
    )
    args = parser.parse_args()

    env_output = args.output / args.env
    image_dir = env_output / "images"
    label_dir = env_output / "labels"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    hash_index = HashIndex(env_output / f"hash_index_aihub_seg_{args.env}.json")
    exported = 0

    print(f"Scanning {args.input_dir} for Segmentation labels...")

    # Process AI Hub JSONs
    for json_path in args.input_dir.rglob("*.json"):
        print(f"Processing JSON: {json_path.name}")
        exported += process_aihub_seg_json(json_path, image_dir, label_dir, hash_index)

    hash_index.save()
    print(f"Exported {exported} new images to {env_output}")


if __name__ == "__main__":
    main()
