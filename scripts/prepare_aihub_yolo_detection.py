from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import xml.etree.ElementTree as ET  # nosec B405
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
    root = ET.parse(xml_path).getroot()  # nosec B314 # noqa: S314
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
    return f"{class_id} {x_center:.6f} {y_center:.6f} " f"{norm_width:.6f} {norm_height:.6f}"


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

    # 전체 가능한 클래스 자동 수집 (AI Hub 전체 클래스)
    all_possible_labels = set(collect_class_names(resolved_images))
    target_labels = all_possible_labels

    # 클래스 균형 추출을 위해 전체를 먼저 무작위 셔플
    rng = random.Random(seed)  # nosec B311 # noqa: S311
    all_shuffled = list(resolved_images)
    rng.shuffle(all_shuffled)

    # 클래스별로 수집된 이미지 장수 카운트
    class_limits = limit if limit > 0 else 2000
    class_collected_counts = dict.fromkeys(target_labels, 0)

    balanced_images = []
    for entry in all_shuffled:
        image_w = entry.item.width
        image_h = entry.item.height
        image_area = image_w * image_h
        if image_area <= 0:
            continue

        reliable_boxes = []
        for box in entry.item.boxes:
            box_w = abs(box.xbr - box.xtl)
            box_h = abs(box.ybr - box.ytl)
            box_area = box_w * box_h

            # 1. 적정 면적 비율 (1% ~ 80%) - 너무 작거나(노이즈 오탐 방지) 꽉 찬 객체 제외
            area_ratio = box_area / image_area
            if not (0.01 <= area_ratio <= 0.80):
                continue

            # 2. 정중앙 기준 (가운데 10% ~ 90% 영역 내에 중심점 존재) - 가장자리 잘린 객체 오탐 방지
            center_x = (box.xtl + box.xbr) / 2
            center_y = (box.ytl + box.ybr) / 2
            if not (0.1 * image_w <= center_x <= 0.9 * image_w):
                continue
            if not (0.1 * image_h <= center_y <= 0.9 * image_h):
                continue

            reliable_boxes.append(box)

        # 확실한 사물이 최소 1개 이상 들어있는 경우만 처리
        if len(reliable_boxes) >= 1:
            labels_in_image = {
                box.label.strip().lower().replace("-", "_") for box in reliable_boxes
            }

            # 아직 목표 수량을 못 채운 사물이 포함되어 있는지 확인
            has_needed_class = False
            for label in labels_in_image.intersection(target_labels):
                if class_collected_counts[label] < class_limits:
                    has_needed_class = True
                    break

            if has_needed_class:
                balanced_images.append(entry)
                # 이 이미지에 포함된 모든 핵심 클래스의 수집 카운트 누적 갱신
                for label in labels_in_image.intersection(target_labels):
                    class_collected_counts[label] += 1

    print(
        f"\n>>> 확실한 크기(1~80% 면적) 및 정중앙 타겟 클래스별 최대 {class_limits}장 타겟 균형 필터링 완료."
    )
    print(f">>> 수집된 최종 이미지 장수: {len(balanced_images)}")
    print(">>> 확실한 사물 수집 상세 현황:")
    for label, count in sorted(class_collected_counts.items()):
        print(f"    - {label}: {count}장")

    shuffled = balanced_images
    class_names = collect_class_names(shuffled)
    class_to_id = {label: index for index, label in enumerate(class_names)}

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
