"""Export and print class-aware collection plans."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from class_specs import CLASS_SPECS, ClassSpec


def specs_to_rows(specs: list[ClassSpec]) -> list[dict[str, str | int]]:
    return [
        {
            "class_id": spec.class_id,
            "name": spec.name,
            "include": spec.include,
            "exclude": spec.exclude,
            "search_queries": " | ".join(spec.search_queries),
            "hard_negatives": " | ".join(spec.hard_negatives),
        }
        for spec in sorted(specs, key=lambda item: item.class_id)
    ]


def print_plan(specs: list[ClassSpec]) -> None:
    for spec in sorted(specs, key=lambda item: item.class_id):
        print(f"[{spec.class_id:02d}] {spec.name}")
        print(f"  include: {spec.include}")
        print(f"  exclude: {spec.exclude}")
        print(f"  queries: {', '.join(spec.search_queries)}")
        if spec.hard_negatives:
            print(f"  hard negatives: {', '.join(spec.hard_negatives)}")


def export_plan(output_path: Path, specs: list[ClassSpec] | None = None) -> Path:
    specs = specs or list(CLASS_SPECS.values())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = specs_to_rows(specs)
    if output_path.suffix.lower() == ".json":
        output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return output_path
