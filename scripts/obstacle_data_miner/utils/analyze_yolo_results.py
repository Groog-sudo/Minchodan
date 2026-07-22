"""Analyze per-class YOLO prediction folders.

Expected input layout:

results/
  00_barricade/predict/labels/*.txt
  01_bench/predict/labels/*.txt
  ...

The script assumes class ids follow `config.TARGET_CLASSES`.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import TARGET_CLASSES

NAME_TO_ID = {name: class_id for class_id, name in TARGET_CLASSES.items()}


def expected_name_from_folder(folder_name: str) -> str:
    return folder_name.split("_", 1)[1]


def parse_label_ids(label_path: Path) -> list[int]:
    ids: list[int] = []
    for line in label_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        try:
            ids.append(int(float(parts[0])))
        except ValueError:
            continue
    return ids


def analyze(results_root: Path) -> tuple[list[dict[str, object]], Counter[tuple[str, str]]]:
    rows: list[dict[str, object]] = []
    confusions: Counter[tuple[str, str]] = Counter()

    for class_dir in sorted(path for path in results_root.iterdir() if path.is_dir()):
        expected = expected_name_from_folder(class_dir.name)
        expected_id = NAME_TO_ID.get(expected)
        image_count = sum(
            1 for path in class_dir.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        label_paths = list(class_dir.rglob("*.txt"))
        pred_counts: Counter[int] = Counter()
        hit_images = 0
        wrong_only_images = 0
        empty_labels = 0

        for label_path in label_paths:
            ids = parse_label_ids(label_path)
            pred_counts.update(ids)
            unique_ids = set(ids)
            if not ids:
                empty_labels += 1
            elif expected_id in unique_ids:
                hit_images += 1
            else:
                wrong_only_images += 1
                for pred_id in unique_ids:
                    confusions[(expected, TARGET_CLASSES.get(pred_id, f"id_{pred_id}"))] += 1

        total_boxes = sum(pred_counts.values())
        expected_boxes = pred_counts.get(expected_id, 0)
        rows.append(
            {
                "folder": class_dir.name,
                "expected": expected,
                "images": image_count,
                "labels": len(label_paths),
                "hit_images": hit_images,
                "wrong_only_images": wrong_only_images,
                "empty_labels": empty_labels,
                "expected_boxes": expected_boxes,
                "total_boxes": total_boxes,
                "top_predictions": pred_counts.most_common(6),
            }
        )
    return rows, confusions


def format_markdown(rows: list[dict[str, object]], confusions: Counter[tuple[str, str]]) -> str:
    lines = [
        "# YOLO Per-Class Hallucination Report",
        "",
        "Class ids are interpreted with the trained AI Hub detection order in `config.TARGET_CLASSES`.",
        "",
        "## Per-Class Summary",
        "",
        "| class | images | hit images | wrong-only images | expected boxes / all boxes | top predictions |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        images = max(int(row["images"]), int(row["labels"]), 1)
        hit = int(row["hit_images"])
        wrong = int(row["wrong_only_images"])
        expected_boxes = int(row["expected_boxes"])
        total_boxes = int(row["total_boxes"])
        top = ", ".join(
            f"{TARGET_CLASSES.get(class_id, f'id_{class_id}')}:{count}"
            for class_id, count in row["top_predictions"]  # type: ignore[index]
        )
        lines.append(
            f"| {row['expected']} | {images} | {hit} ({hit / images * 100:.1f}%) | "
            f"{wrong} ({wrong / images * 100:.1f}%) | {expected_boxes}/{total_boxes} | {top} |"
        )

    lines.extend(["", "## Priority Fix Classes", ""])
    low_hit = sorted(
        rows,
        key=lambda item: int(item["hit_images"]) / max(int(item["images"]), int(item["labels"]), 1),
    )
    for row in low_hit[:8]:
        images = max(int(row["images"]), int(row["labels"]), 1)
        hit = int(row["hit_images"])
        lines.append(f"- `{row['expected']}`: hit {hit}/{images} ({hit / images * 100:.1f}%)")

    lines.extend(["", "## Top Confusions", ""])
    for (expected, predicted), count in confusions.most_common(30):
        lines.append(f"- `{expected}` -> `{predicted}`: {count} images")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze per-class YOLO prediction result folders."
    )
    parser.add_argument("results_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows, confusions = analyze(args.results_root)
    report = format_markdown(rows, confusions)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
