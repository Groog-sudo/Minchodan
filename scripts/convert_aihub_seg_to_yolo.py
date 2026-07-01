# -*- coding: utf-8 -*-
import argparse
import json
import os
import random
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LABEL_MAP = {
    "sidewalk": 0,
    "caution_zone": 1,
    "roadway": 2,
    "alley": 2,
    "bike_lane": 2,
    "braille_guide_blocks": 3,
}

CLASS_NAMES = {
    0: "sidewalk_normal",
    1: "caution",
    2: "roadway",
    3: "braille_normal",
}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Hub 서피스마스킹 XML을 YOLO Segmentation 포맷으로 변환합니다."
    )
    parser.add_argument("--input-dir", required=True, help="서피스마스킹 최상위 폴더 경로입니다.")
    parser.add_argument(
        "--output-dir",
        default="training/datasets/segmentation/aihub_0820_26",
        help="결과 저장 폴더입니다.",
    )
    parser.add_argument(
        "--yaml-path",
        default="training/configs/aihub_yolo_segmentation.yaml",
        help="생성할 Ultralytics dataset yaml 경로입니다.",
    )
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation 비율입니다.")
    parser.add_argument("--max-images", type=int, default=0, help="0이면 전체 이미지를 사용합니다.")
    return parser.parse_args()


def process_xml(xml_path: Path) -> list[tuple[str, int, int, list[dict]]]:
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as exc:
        print(f"Error parsing XML {xml_path}: {exc}")
        return []

    data: list[tuple[str, int, int, list[dict]]] = []
    for image in root.findall("image"):
        img_name = image.get("name")
        if not img_name:
            continue
        width = int(image.get("width") or 0)
        height = int(image.get("height") or 0)

        polygons: list[dict] = []
        for poly in image.findall("polygon"):
            label = poly.get("label")
            points_str = poly.get("points")
            if not label or not points_str or label not in LABEL_MAP:
                continue

            class_id = LABEL_MAP[label]
            points: list[float] = []
            for pt in points_str.split(";"):
                if not pt.strip():
                    continue
                x, y = map(float, pt.split(","))
                points.extend([max(0.0, min(1.0, x / width)), max(0.0, min(1.0, y / height))])

            if points:
                polygons.append({"class_id": class_id, "points": points})

        if polygons:
            data.append((img_name, width, height, polygons))

    return data


def write_dataset_yaml(output_dir: Path, yaml_path: Path) -> None:
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {output_dir.resolve().as_posix()}",
                "train: images/train",
                "val: images/val",
                "names:",
                *[f"  {class_id}: {name}" for class_id, name in sorted(CLASS_NAMES.items())],
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"입력 폴더를 찾을 수 없습니다: {input_dir}")

    output_dir = project_root() / args.output_dir
    yaml_path = project_root() / args.yaml_path

    img_train_dir = output_dir / "images" / "train"
    img_val_dir = output_dir / "images" / "val"
    lbl_train_dir = output_dir / "labels" / "train"
    lbl_val_dir = output_dir / "labels" / "val"

    for target in [img_train_dir, img_val_dir, lbl_train_dir, lbl_val_dir]:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

    xml_files = list(input_dir.rglob("*.xml"))
    print(f"Found {len(xml_files)} XML files.")

    all_image_data: list[tuple[Path, list[dict], str]] = []
    used_names: set[str] = set()
    for xml_path in xml_files:
        xml_parent = xml_path.parent
        for img_name, _width, _height, polygons in process_xml(xml_path):
            img_src = xml_parent / img_name
            if not img_src.exists():
                continue

            output_name = img_name
            if output_name in used_names:
                output_name = f"{xml_path.parent.name}_{img_name}"
            used_names.add(output_name)
            all_image_data.append((img_src, polygons, output_name))

    print(f"Found {len(all_image_data)} valid images with annotations.")

    if args.max_images > 0:
        all_image_data = all_image_data[: args.max_images]
        print(f"Limiting to {args.max_images} images as requested.")

    random.seed(42)
    random.shuffle(all_image_data)

    val_count = int(len(all_image_data) * args.val_ratio)
    train_data = all_image_data[:-val_count] if val_count else all_image_data
    val_data = all_image_data[-val_count:] if val_count else []

    def copy_and_convert(
        data: list[tuple[Path, list[dict], str]],
        split_name: str,
        img_dir: Path,
        lbl_dir: Path,
    ) -> None:
        print(f"Processing {split_name} set ({len(data)} images)...")
        for idx, (img_src, polygons, output_name) in enumerate(data):
            img_dst = img_dir / output_name
            if not img_dst.exists():
                try:
                    os.link(img_src, img_dst)
                except OSError:
                    shutil.copy2(img_src, img_dst)

            lbl_dst = lbl_dir / f"{Path(output_name).stem}.txt"
            with lbl_dst.open("w", encoding="utf-8", newline="\n") as handle:
                for poly in polygons:
                    points_str = " ".join(f"{value:.6f}" for value in poly["points"])
                    handle.write(f"{poly['class_id']} {points_str}\n")

            if (idx + 1) % 500 == 0:
                print(f"  [{idx + 1}/{len(data)}] processed.")

    copy_and_convert(train_data, "train", img_train_dir, lbl_train_dir)
    copy_and_convert(val_data, "val", img_val_dir, lbl_val_dir)
    write_dataset_yaml(output_dir, yaml_path)

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir.resolve()),
        "yaml_path": str(yaml_path.resolve()),
        "train_images": len(train_data),
        "val_images": len(val_data),
        "class_names": CLASS_NAMES,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
