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


@dataclass
class ResolvedImage:
    source_image: Path
    output_name: str
    item: ImageItem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Hub CVAT XML을 YOLO detection 학습 데이터셋으로 변환합니다."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--xml-path", help="단일 CVAT XML 파일 경로입니다.")
    source_group.add_argument(
        "--input-dir",
        help="바운딩박스 루트 폴더입니다. 하위 모든 *.xml을 변환합니다.",
    )
    parser.add_argument(
        "--output-dir",
        default="training/datasets/detection/aihub_full",
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


def collect_class_names(resolved_images: list[ResolvedImage]) -> list[str]:
    labels: set[str] = set()
    for resolved in resolved_images:
        for box in resolved.item.boxes:
            if box.label:
                labels.add(box.label)
    return sorted(labels)


def collect_from_xml(xml_path: Path) -> list[ResolvedImage]:
    image_dir = xml_path.parent
    resolved: list[ResolvedImage] = []
    for item in parse_xml(xml_path):
        source_image = image_dir / item.name
        if item.name and source_image.is_file() and item.boxes:
            resolved.append(
                ResolvedImage(
                    source_image=source_image,
                    output_name=item.name,
                    item=item,
                )
            )
    return resolved


def collect_from_input_dir(input_dir: Path) -> list[ResolvedImage]:
    resolved: list[ResolvedImage] = []
    used_names: set[str] = set()
    for xml_path in sorted(input_dir.rglob("*.xml")):
        for entry in collect_from_xml(xml_path):
            output_name = entry.output_name
            if output_name in used_names:
                output_name = f"{xml_path.parent.name}_{entry.output_name}"
            used_names.add(output_name)
            resolved.append(
                ResolvedImage(
                    source_image=entry.source_image,
                    output_name=output_name,
                    item=entry.item,
                )
            )
    return resolved


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


def write_dataset_yaml(
    output_dir: Path,
    yaml_path: Path,
    class_to_id: dict[str, int],
) -> None:
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


def write_dataset(
    resolved_images: list[ResolvedImage],
    output_dir: Path,
    yaml_path: Path,
    val_ratio: float,
    seed: int,
    limit: int,
    source_hint: str,
) -> dict[str, Any]:
    if not resolved_images:
        raise ValueError("변환할 이미지가 없습니다. XML 경로와 이미지 폴더를 확인하세요.")

    if limit > 0:
        resolved_images = resolved_images[:limit]

    class_names = collect_class_names(resolved_images)
    class_to_id = {label: index for index, label in enumerate(class_names)}

    rng = random.Random(seed)
    shuffled = list(resolved_images)
    rng.shuffle(shuffled)

    val_count = max(1, round(len(shuffled) * val_ratio)) if len(shuffled) > 1 else 0
    val_names = {entry.output_name for entry in shuffled[:val_count]}
    clear_generated_dataset(output_dir)

    split_counts = {"train": 0, "val": 0}
    box_counts = {"train": 0, "val": 0}
    skipped_labels: dict[str, int] = {}

    for entry in shuffled:
        split = "val" if entry.output_name in val_names else "train"
        target_image = output_dir / "images" / split / entry.output_name
        target_label = output_dir / "labels" / split / f"{Path(entry.output_name).stem}.txt"

        lines: list[str] = []
        for box in entry.item.boxes:
            class_id = class_to_id.get(box.label)
            if class_id is None:
                skipped_labels[box.label] = skipped_labels.get(box.label, 0) + 1
                continue
            line = yolo_line(box, entry.item.width, entry.item.height, class_id)
            if line:
                lines.append(line)

        if not lines:
            continue

        shutil.copy2(entry.source_image, target_image)
        target_label.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        split_counts[split] += 1
        box_counts[split] += len(lines)

    write_dataset_yaml(output_dir, yaml_path, class_to_id)

    return {
        "source": source_hint,
        "output_dir": str(output_dir.resolve()),
        "yaml_path": str(yaml_path.resolve()),
        "class_names": class_names,
        "split_counts": split_counts,
        "box_counts": box_counts,
        "skipped_labels": skipped_labels,
    }


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    yaml_path = Path(args.yaml_path)

    if args.xml_path:
        xml_path = Path(args.xml_path).expanduser().resolve()
        if not xml_path.is_file():
            raise FileNotFoundError(f"XML 파일을 찾을 수 없습니다: {xml_path}")
        resolved_images = collect_from_xml(xml_path)
        source_hint = str(xml_path)
    else:
        input_dir = Path(args.input_dir).expanduser().resolve()
        if not input_dir.is_dir():
            raise FileNotFoundError(f"입력 폴더를 찾을 수 없습니다: {input_dir}")
        resolved_images = collect_from_input_dir(input_dir)
        source_hint = str(input_dir)

    summary = write_dataset(
        resolved_images=resolved_images,
        output_dir=output_dir,
        yaml_path=yaml_path,
        val_ratio=args.val_ratio,
        seed=args.seed,
        limit=args.limit,
        source_hint=source_hint,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
