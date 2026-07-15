"""Import ScooterDet LabelMe annotations into the local AIHUB YOLO order."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import CLASS_TO_ID, SETTINGS
from utils.format_converter import HashIndex, safe_image_open, xyxy_to_yolo

LABEL_MAP = {
    "bench": "bench",
    "bicycle": "bicycle",
    "bus": "bus",
    "car": "car",
    "fire hydrant": "fire_hydrant",
    "motorcycle": "motorcycle",
    "parking meter": "parking_meter",
    "person": "person",
    "scooter": "scooter",
    "stop sign": "traffic_sign",
    "traffic light": "traffic_light",
    "truck": "truck",
}


def import_scooterdet(zip_path: Path, output_root: Path, limit: int | None = None) -> int:
    image_dir = output_root / "images"
    label_dir = output_root / "labels"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    hash_index = HashIndex(SETTINGS.hash_index_path)
    exported = 0

    with zipfile.ZipFile(zip_path) as archive:
        label_entries = [
            entry
            for entry in archive.namelist()
            if entry.startswith("Mixed/labels/") and entry.endswith(".json")
        ]
        for label_entry in label_entries:
            data = json.loads(archive.read(label_entry).decode("utf-8"))
            shapes = data.get("shapes", [])
            if not any(shape.get("label") == "scooter" for shape in shapes):
                continue

            width = int(data.get("imageWidth") or 0)
            height = int(data.get("imageHeight") or 0)
            if width <= 0 or height <= 0:
                continue

            lines: list[str] = []
            for shape in shapes:
                target_label = LABEL_MAP.get(str(shape.get("label", "")).strip())
                points = shape.get("points") or []
                if target_label is None or len(points) < 2:
                    continue
                x1, y1 = points[0]
                x2, y2 = points[1]
                values = xyxy_to_yolo(float(x1), float(y1), float(x2), float(y2), width, height)
                class_id = CLASS_TO_ID[target_label]
                lines.append(f"{class_id} " + " ".join(f"{value:.6f}" for value in values))

            if not lines:
                continue

            stem = Path(label_entry).stem
            image_entry = f"Mixed/images/{stem}.jpg"
            if image_entry not in archive.namelist():
                continue

            output_image = image_dir / f"scooterdet_{stem}.jpg"
            output_label = label_dir / f"scooterdet_{stem}.txt"
            temp_image = output_image.with_suffix(".tmp.jpg")
            with archive.open(image_entry) as source, temp_image.open("wb") as target:
                shutil.copyfileobj(source, target)

            with safe_image_open(temp_image) as image:
                if image is None:
                    temp_image.unlink(missing_ok=True)
                    continue
                duplicate_source = hash_index.duplicate_source(image)
                if duplicate_source:
                    print(f"[SKIP] duplicate {image_entry} ~= {duplicate_source}")
                    temp_image.unlink(missing_ok=True)
                    continue
                hash_index.add(image, str(output_image))

            temp_image.replace(output_image)
            output_label.write_text("\n".join(lines) + "\n", encoding="utf-8")
            exported += 1
            if limit and exported >= limit:
                break

    hash_index.save()
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import ScooterDet scooter frames into YOLO format."
    )
    parser.add_argument("zip_path", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=SETTINGS.object_detection_root / "external_exports" / "scooterdet_scooter",
    )
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    exported = import_scooterdet(args.zip_path, args.output, limit=args.limit)
    print(f"Exported {exported} ScooterDet samples to {args.output}")


if __name__ == "__main__":
    main()
