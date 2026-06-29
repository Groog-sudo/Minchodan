# -*- coding: utf-8 -*-
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DEFAULT_OUTPUT_DIR = Path("outputs") / "aihub_walk_dataset_scan"
DEFAULT_TARGET_LABELS = {
    "barricade",
    "bicycle",
    "bollard",
    "bus",
    "car",
    "motorcycle",
    "movable_signage",
    "person",
    "pole",
    "scooter",
    "stairs",
    "stop",
    "traffic_light",
    "traffic_sign",
    "truck",
}


@dataclass
class BoxRecord:
    label: str
    bbox: list[float]
    occluded: bool
    direction: str
    distance: str
    area_ratio: float


@dataclass
class ImageRecord:
    image_id: str
    name: str
    width: int
    height: int
    boxes: list[BoxRecord]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Hub CVAT 바운딩박스 XML을 읽어 데모 후보 이미지를 요약합니다."
    )
    parser.add_argument("--xml-path", required=True, help="분석할 CVAT XML 경로입니다.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="분석 결과 저장 폴더입니다. 기본값은 outputs/aihub_walk_dataset_scan 입니다.",
    )
    parser.add_argument(
        "--target-labels",
        default=",".join(sorted(DEFAULT_TARGET_LABELS)),
        help="데모 후보로 볼 라벨 목록입니다. 쉼표로 구분합니다.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="보고서에 표시할 데모 후보 이미지 수입니다.",
    )
    return parser.parse_args()


def parse_bool(value: str | None) -> bool:
    return str(value or "0").lower() in {"1", "true", "yes"}


def parse_float(value: str | None) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_int(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def normalize_label(label: str) -> str:
    return label.strip().lower().replace("-", "_")


def estimate_direction(bbox: list[float], width: int) -> str:
    if width <= 0:
        return "front"
    x_center_ratio = ((bbox[0] + bbox[2]) / 2.0) / width
    if x_center_ratio < 0.33:
        return "front-left"
    if x_center_ratio > 0.66:
        return "front-right"
    return "front"


def estimate_distance(bbox: list[float], width: int, height: int) -> tuple[str, float]:
    if width <= 0 or height <= 0:
        return "far", 0.0
    box_width = max(0.0, bbox[2] - bbox[0])
    box_height = max(0.0, bbox[3] - bbox[1])
    area_ratio = (box_width * box_height) / float(width * height)
    if area_ratio >= 0.25:
        return "near", area_ratio
    if area_ratio >= 0.10:
        return "medium", area_ratio
    return "far", area_ratio


def parse_xml(xml_path: Path) -> tuple[list[str], list[ImageRecord]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    labels = [
        normalize_label(node.text or "")
        for node in root.findall("./meta/task/labels/label/name")
        if (node.text or "").strip()
    ]

    images: list[ImageRecord] = []
    for image_node in root.findall("./image"):
        width = parse_int(image_node.get("width"))
        height = parse_int(image_node.get("height"))
        boxes: list[BoxRecord] = []
        for box_node in image_node.findall("./box"):
            label = normalize_label(box_node.get("label") or "")
            bbox = [
                parse_float(box_node.get("xtl")),
                parse_float(box_node.get("ytl")),
                parse_float(box_node.get("xbr")),
                parse_float(box_node.get("ybr")),
            ]
            direction = estimate_direction(bbox, width)
            distance, area_ratio = estimate_distance(bbox, width, height)
            boxes.append(
                BoxRecord(
                    label=label,
                    bbox=bbox,
                    occluded=parse_bool(box_node.get("occluded")),
                    direction=direction,
                    distance=distance,
                    area_ratio=area_ratio,
                )
            )

        images.append(
            ImageRecord(
                image_id=image_node.get("id") or "",
                name=image_node.get("name") or "",
                width=width,
                height=height,
                boxes=boxes,
            )
        )
    return labels, images


def box_to_dict(box: BoxRecord) -> dict[str, Any]:
    return {
        "label": box.label,
        "bbox": [round(value, 2) for value in box.bbox],
        "occluded": box.occluded,
        "direction": box.direction,
        "distance": box.distance,
        "area_ratio": round(box.area_ratio, 5),
    }


def image_to_dict(image: ImageRecord, target_labels: set[str]) -> dict[str, Any]:
    target_boxes = [box for box in image.boxes if box.label in target_labels]
    return {
        "image_id": image.image_id,
        "name": image.name,
        "width": image.width,
        "height": image.height,
        "box_count": len(image.boxes),
        "target_box_count": len(target_boxes),
        "target_labels": sorted({box.label for box in target_boxes}),
        "target_boxes": [box_to_dict(box) for box in target_boxes],
    }


def candidate_score(image: ImageRecord, target_labels: set[str]) -> tuple[int, float, int]:
    target_boxes = [box for box in image.boxes if box.label in target_labels]
    max_area_ratio = max((box.area_ratio for box in target_boxes), default=0.0)
    high_priority_count = sum(
        1
        for box in target_boxes
        if box.label in {"bicycle", "bollard", "bus", "car", "motorcycle", "scooter", "truck"}
    )
    return high_priority_count, max_area_ratio, len(target_boxes)


def build_summary(
    xml_path: Path,
    labels: list[str],
    images: list[ImageRecord],
    target_labels: set[str],
    top_k: int,
) -> dict[str, Any]:
    label_counts: Counter[str] = Counter()
    for image in images:
        label_counts.update(box.label for box in image.boxes)

    candidates = [
        image
        for image in images
        if any(box.label in target_labels for box in image.boxes)
    ]
    candidates.sort(
        key=lambda image: candidate_score(image, target_labels),
        reverse=True,
    )

    xml_dir = xml_path.parent
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "xml_path": str(xml_path),
        "image_dir": str(xml_dir),
        "declared_labels": labels,
        "target_labels": sorted(target_labels),
        "counts": {
            "image_count": len(images),
            "box_count": sum(len(image.boxes) for image in images),
            "candidate_image_count": len(candidates),
            "label_counts": dict(sorted(label_counts.items())),
        },
        "top_candidates": [
            image_to_dict(image, target_labels)
            for image in candidates[: max(0, top_k)]
        ],
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def render_report(summary: dict[str, Any]) -> str:
    count_rows = [
        ["이미지 수", summary["counts"]["image_count"]],
        ["박스 수", summary["counts"]["box_count"]],
        ["데모 후보 이미지 수", summary["counts"]["candidate_image_count"]],
    ]
    label_rows = [
        [label, count]
        for label, count in summary["counts"]["label_counts"].items()
    ]
    candidate_rows = [
        [
            item["name"],
            item["target_box_count"],
            ", ".join(item["target_labels"]),
            item["target_boxes"][0]["direction"] if item["target_boxes"] else "",
            item["target_boxes"][0]["distance"] if item["target_boxes"] else "",
        ]
        for item in summary["top_candidates"]
    ]

    metadata = "\n".join(
        [
            f"> **작성일**: {summary['generated_at'][:10]}",
            "> **버전**: v0.1.0",
            f"> **XML**: `{summary['xml_path']}`",
            f"> **이미지 폴더**: `{summary['image_dir']}`",
        ]
    )

    return "\n\n".join(
        [
            "# AI Hub 바운딩박스 XML 검증 보고서",
            metadata,
            "---",
            "## 1. 구조 요약",
            markdown_table(["항목", "값"], count_rows),
            "---",
            "## 2. 라벨 분포",
            markdown_table(["라벨", "박스 수"], label_rows),
            "---",
            "## 3. 데모 후보 이미지",
            markdown_table(
                ["이미지", "대상 박스 수", "대상 라벨", "대표 방향", "대표 거리"],
                candidate_rows,
            ),
            "---",
            "## 4. 판단",
            markdown_table(
                ["구분", "내용"],
                [
                    ["데이터 구조", "CVAT XML 1개와 같은 폴더 JPG 다수로 구성됩니다."],
                    ["이번 주 사용", "바운딩박스 폴더에서 이미지 1~3장만 골라 YOLO 데모 입력으로 사용합니다."],
                    ["Git 처리", "원천데이터와 weight 파일은 Git에 올리지 않습니다."],
                ],
            ),
        ]
    ) + "\n"


def write_outputs(summary: dict[str, Any], output_dir: Path, xml_path: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = xml_path.stem
    json_path = output_dir / f"bbox_{stem}_summary.json"
    report_path = output_dir / f"bbox_{stem}_report.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    report_path.write_text(render_report(summary), encoding="utf-8", newline="\n")
    return report_path, json_path


def main() -> None:
    args = parse_args()
    xml_path = Path(args.xml_path).expanduser().resolve()
    if not xml_path.exists() or not xml_path.is_file():
        raise FileNotFoundError(f"XML 파일을 찾을 수 없습니다: {xml_path}")

    target_labels = {
        normalize_label(label)
        for label in args.target_labels.split(",")
        if label.strip()
    }
    labels, images = parse_xml(xml_path)
    summary = build_summary(xml_path, labels, images, target_labels, args.top_k)
    report_path, json_path = write_outputs(summary, Path(args.output_dir), xml_path)

    print(f"XML 분석 완료: {xml_path}")
    print(f"이미지 수: {summary['counts']['image_count']}")
    print(f"박스 수: {summary['counts']['box_count']}")
    print(f"데모 후보 이미지 수: {summary['counts']['candidate_image_count']}")
    print(f"보고서: {report_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
