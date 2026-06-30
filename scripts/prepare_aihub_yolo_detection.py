# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DEFAULT_CLASSES = [
    "barricade",
    "bench",
    "bicycle",
    "bollard",
    "bus",
    "car",
    "carrier",
    "chair",
    "motorcycle",
    "movable_signage",
    "person",
    "pole",
    "potted_plant",
    "stop",
    "traffic_light",
    "traffic_sign",
    "tree_trunk",
    "truck",
]


@dataclass
class Box:
    label: str
    xtl: float
    ytl: float
    xbr: float
    ybr: float


@dataclass
class ImageItem:
    name: str
    width: int
    height: int
    boxes: list[Box]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Hub CVAT XML을 YOLO detection 학습 데이터셋으로 변환합니다."
    )
    parser.add_argument("--xml-path", required=True, help="CVAT XML 파일 경로입니다.")
    parser.add_argument(
        "--output-dir",
        default="training/datasets/detection/aihub_0820_26",
        help="YOLO 데이터셋 출력 폴더입니다.",
    )
    parser.add_argument(
        "--yaml-path",
        default="training/configs/aihub_yolo_detection.yaml",
        help="생성할 Ultralytics dataset yaml 경로입니다.",
    )
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=0, help="0이면 전체 이미지를 사용합니다.")
    return parser.parse_args()


def parse_float(value: str | None) -> float:
    try:
        return float(value or 0.0)
    except ValueError:
        return 0.0


def parse_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def normalize_label(label: str) -> str:
    return label.strip().lower().replace("-", "_")


def parse_xml(xml_path: Path) -> list[ImageItem]:
    root = ET.parse(xml_path).getroot()
    items: list[ImageItem] = []
    for image_node in root.findall("./image"):
        boxes: list[Box] = []
        for box_node in image_node.findall("./box"):
            boxes.append(
                Box(
                    label=normalize_label(box_node.get("label") or ""),
                    xtl=parse_float(box_node.get("xtl")),
                    ytl=parse_float(box_node.get("ytl")),
                    xbr=parse_float(box_node.get("xbr")),
                    ybr=parse_float(box_node.get("ybr")),
                )
            )
        items.append(
            ImageItem(
                name=image_node.get("name") or "",
                width=parse_int(image_node.get("width")),
                height=parse_int(image_node.get("height")),
                boxes=boxes,
            )
        )
    return items


def yolo_line(box: Box, width: int, height: int, class_id: int) -> str | None:
    if width <= 0 or height <= 0:
        return None

    x1 = max(0.0, min(box.xtl, box.xbr))
    y1 = max(0.0, min(box.ytl, box.ybr))
    x2 = min(float(width), max(box.xtl, box.xbr))
    y2 = min(float(height), max(box.ytl, box.ybr))
    box_width = max(0.0, x2 - x1)
    box_height = max(0.0, y2 - y1)
    if box_width <= 0 or box_height <= 0:
        return None

    x_center = (x1 + x2) / 2.0 / width
    y_center = (y1 + y2) / 2.0 / height
    norm_width = box_width / width
    norm_height = box_height / height
    return (
        f"{class_id} {x_center:.6f} {y_center:.6f} "
        f"{norm_width:.6f} {norm_height:.6f}"
    )


def clear_generated_dataset(output_dir: Path) -> None:
    for split in ("train", "val"):
        for kind in ("images", "labels"):
            target = output_dir / kind / split
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)


def write_dataset(
    xml_path: Path,
    items: list[ImageItem],
    output_dir: Path,
    yaml_path: Path,
    val_ratio: float,
    seed: int,
    limit: int,
) -> dict[str, Any]:
    class_to_id = {label: index for index, label in enumerate(DEFAULT_CLASSES)}
    image_dir = xml_path.parent
    valid_items = [
        item
        for item in items
        if item.name and (image_dir / item.name).is_file() and item.boxes
    ]

    rng = random.Random(seed)
    rng.shuffle(valid_items)
    if limit > 0:
        valid_items = valid_items[:limit]

    val_count = max(1, round(len(valid_items) * val_ratio)) if len(valid_items) > 1 else 0
    val_names = {item.name for item in valid_items[:val_count]}
    clear_generated_dataset(output_dir)

    split_counts = {"train": 0, "val": 0}
    box_counts = {"train": 0, "val": 0}
    skipped_labels: dict[str, int] = {}

    for item in valid_items:
        split = "val" if item.name in val_names else "train"
        source_image = image_dir / item.name
        target_image = output_dir / "images" / split / item.name
        target_label = output_dir / "labels" / split / f"{Path(item.name).stem}.txt"

        lines: list[str] = []
        for box in item.boxes:
            class_id = class_to_id.get(box.label)
            if class_id is None:
                skipped_labels[box.label] = skipped_labels.get(box.label, 0) + 1
                continue
            line = yolo_line(box, item.width, item.height, class_id)
            if line:
                lines.append(line)

        if not lines:
            continue

        shutil.copy2(source_image, target_image)
        target_label.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        split_counts[split] += 1
        box_counts[split] += len(lines)

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {output_dir.resolve().as_posix()}",
                "train: images/train",
                "val: images/val",
                "names:",
                *[
                    f"  {class_id}: {label}"
                    for label, class_id in sorted(class_to_id.items(), key=lambda item: item[1])
                ],
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )

    return {
        "xml_path": str(xml_path),
        "output_dir": str(output_dir),
        "yaml_path": str(yaml_path),
        "split_counts": split_counts,
        "box_counts": box_counts,
        "skipped_labels": skipped_labels,
    }


def main() -> int:
    args = parse_args()
    xml_path = Path(args.xml_path).expanduser().resolve()
    if not xml_path.is_file():
        raise FileNotFoundError(f"XML 파일을 찾을 수 없습니다: {xml_path}")

    summary = write_dataset(
        xml_path=xml_path,
        items=parse_xml(xml_path),
        output_dir=Path(args.output_dir),
        yaml_path=Path(args.yaml_path),
        val_ratio=args.val_ratio,
        seed=args.seed,
        limit=args.limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
