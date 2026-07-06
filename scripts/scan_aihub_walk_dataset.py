# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
LABEL_EXTENSIONS = {".json", ".xml", ".txt", ".csv", ".yaml", ".yml"}
DEPTH_EXTENSIONS = {".npy", ".npz", ".pfm", ".exr", ".tiff", ".tif"}
IGNORED_DIR_NAMES = {"__MACOSX", ".ipynb_checkpoints", "__pycache__"}

DEFAULT_OUTPUT_DIR = Path("outputs") / "aihub_walk_dataset_scan"
MAX_SAMPLE_PER_CATEGORY = 20
MAX_TREE_ITEMS_PER_DIR = 80


@dataclass
class FileInfo:
    path: str
    size_bytes: int


def project_root() -> Path:
    current_dir = Path(__file__).resolve().parent
    return current_dir.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Hub 인도보행 영상 데이터셋 폴더 구조와 파일 통계를 스캔합니다."
    )
    parser.add_argument(
        "--dataset-root",
        default=None,
        help="AI Hub 인도보행 영상 데이터셋 루트 경로입니다.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="스캔 결과 저장 폴더입니다. 기본값은 outputs/aihub_walk_dataset_scan 입니다.",
    )
    parser.add_argument(
        "--max-tree-depth",
        type=int,
        default=3,
        help="보고서에 표시할 폴더 트리 깊이입니다.",
    )
    return parser.parse_args()


def load_env_value(key: str) -> str:
    env_path = project_root() / ".env"
    if not env_path.exists():
        return ""

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""

    prefix = f"{key}="
    for line in lines:
        stripped = line.strip().lstrip("\ufeff")
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        return stripped[len(prefix) :].strip().strip('"').strip("'")
    return ""


def resolve_dataset_root(arg_root: str | None) -> Path:
    root_text = arg_root or os.getenv("AIHUB_WALK_DATASET_ROOT", "")
    root_text = root_text or load_env_value("AIHUB_WALK_DATASET_ROOT")
    if not root_text:
        raise ValueError(
            "--dataset-root 또는 .env의 AIHUB_WALK_DATASET_ROOT 값을 지정해야 합니다."
        )

    root = Path(root_text).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"데이터셋 루트 폴더를 찾을 수 없습니다: {root}")
    return root


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def classify_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in LABEL_EXTENSIONS:
        return "label"
    if suffix in DEPTH_EXTENSIONS:
        return "depth"
    return "other"


def make_file_info(path: Path, root: Path) -> FileInfo:
    try:
        size_bytes = path.stat().st_size
    except OSError:
        size_bytes = 0
    return FileInfo(path=relative_path(path, root), size_bytes=size_bytes)


def iter_dataset_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)
        dir_names[:] = [
            dir_name
            for dir_name in sorted(dir_names)
            if dir_name not in IGNORED_DIR_NAMES
        ]
        for file_name in sorted(file_names):
            files.append(current_path / file_name)
    return files


def get_top_level_name(path: Path, root: Path) -> str:
    rel_parts = path.relative_to(root).parts
    return rel_parts[0] if rel_parts else "."


def build_tree_lines(root: Path, max_depth: int) -> list[str]:
    lines = [root.name + "/"]

    def add_children(directory: Path, depth: int, prefix: str) -> None:
        if depth > max_depth:
            return
        try:
            children = [
                child
                for child in directory.iterdir()
                if child.name not in IGNORED_DIR_NAMES
            ]
        except OSError:
            return

        children.sort(key=lambda child: (child.is_file(), child.name.lower()))
        visible = children[:MAX_TREE_ITEMS_PER_DIR]
        for index, child in enumerate(visible):
            connector = "└── " if index == len(visible) - 1 else "├── "
            suffix = "/" if child.is_dir() else ""
            lines.append(f"{prefix}{connector}{child.name}{suffix}")
            if child.is_dir():
                next_prefix = prefix + ("    " if index == len(visible) - 1 else "│   ")
                add_children(child, depth + 1, next_prefix)
        if len(children) > len(visible):
            omitted = len(children) - len(visible)
            lines.append(f"{prefix}└── ... ({omitted}개 생략)")

    add_children(root, 1, "")
    return lines


def summarize_files(files: list[Path], root: Path) -> dict[str, Any]:
    extension_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    top_level_counts: dict[str, Counter[str]] = defaultdict(Counter)
    top_level_sizes: Counter[str] = Counter()
    category_samples: dict[str, list[FileInfo]] = defaultdict(list)

    total_size = 0
    for path in files:
        suffix = path.suffix.lower() or "(no extension)"
        category = classify_file(path)
        top_level = get_top_level_name(path, root)
        try:
            size_bytes = path.stat().st_size
        except OSError:
            size_bytes = 0

        extension_counts[suffix] += 1
        category_counts[category] += 1
        top_level_counts[top_level][category] += 1
        top_level_counts[top_level]["total"] += 1
        top_level_sizes[top_level] += size_bytes
        total_size += size_bytes

        if len(category_samples[category]) < MAX_SAMPLE_PER_CATEGORY:
            category_samples[category].append(
                FileInfo(path=relative_path(path, root), size_bytes=size_bytes)
            )

    return {
        "total_files": len(files),
        "total_size_bytes": total_size,
        "extension_counts": dict(sorted(extension_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "top_level_summary": [
            {
                "folder": folder,
                "total_files": counts.get("total", 0),
                "image_files": counts.get("image", 0),
                "video_files": counts.get("video", 0),
                "label_files": counts.get("label", 0),
                "depth_files": counts.get("depth", 0),
                "other_files": counts.get("other", 0),
                "size_bytes": top_level_sizes[folder],
            }
            for folder, counts in sorted(top_level_counts.items())
        ],
        "samples": {
            category: [
                {"path": item.path, "size_bytes": item.size_bytes}
                for item in samples
            ]
            for category, samples in sorted(category_samples.items())
        },
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def format_mb(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def render_samples(samples: dict[str, list[dict[str, Any]]]) -> str:
    sections: list[str] = []
    for category, records in samples.items():
        sections.append(f"### {category}")
        rows = [
            [record["path"], format_mb(record["size_bytes"])]
            for record in records
        ]
        sections.append(markdown_table(["샘플 파일", "크기"], rows))
    return "\n\n".join(sections) if sections else "샘플 파일을 찾지 못했습니다."


def render_report(summary: dict[str, Any]) -> str:
    counts = summary["counts"]
    top_rows = [
        [
            item["folder"],
            item["total_files"],
            item["image_files"],
            item["video_files"],
            item["label_files"],
            item["depth_files"],
            item["other_files"],
            format_mb(item["size_bytes"]),
        ]
        for item in counts["top_level_summary"]
    ]
    ext_rows = [
        [extension, count]
        for extension, count in counts["extension_counts"].items()
    ]

    metadata = "\n".join(
        [
            f"> **작성일**: {summary['generated_at'][:10]}",
            "> **버전**: v0.1.0",
            f"> **대상 루트**: `{summary['dataset_root']}`",
        ]
    )

    return "\n\n".join(
        [
            "# AI Hub 인도보행 데이터셋 스캔 보고서",
            metadata,
            "---",
            "## 1. 전체 요약",
            markdown_table(
                ["항목", "값"],
                [
                    ["전체 파일 수", counts["total_files"]],
                    ["전체 용량", format_mb(counts["total_size_bytes"])],
                    ["이미지 파일 수", counts["category_counts"].get("image", 0)],
                    ["영상 파일 수", counts["category_counts"].get("video", 0)],
                    ["라벨 후보 파일 수", counts["category_counts"].get("label", 0)],
                    ["뎁스 후보 파일 수", counts["category_counts"].get("depth", 0)],
                ],
            ),
            "---",
            "## 2. 폴더 트리",
            "```text\n" + "\n".join(summary["folder_tree"]) + "\n```",
            "---",
            "## 3. 상위 폴더별 통계",
            markdown_table(
                [
                    "폴더",
                    "전체",
                    "이미지",
                    "영상",
                    "라벨 후보",
                    "뎁스 후보",
                    "기타",
                    "용량",
                ],
                top_rows,
            ),
            "---",
            "## 4. 확장자 통계",
            markdown_table(["확장자", "파일 수"], ext_rows),
            "---",
            "## 5. 샘플 파일",
            render_samples(counts["samples"]),
            "---",
            "## 6. 다음 작업",
            markdown_table(
                ["순서", "작업"],
                [
                    [1, "바운딩박스 폴더의 라벨 확장자와 샘플 JSON/XML 구조를 확인합니다."],
                    [2, "영상 또는 이미지 샘플 1~3개만 데모 입력으로 선별합니다."],
                    [3, "YOLO 추론 입력으로 쓸 샘플 경로를 run_yolo_tts_demo.py에 연결합니다."],
                    [4, "원천데이터 전체는 Git에 올리지 않고 .env 경로로만 참조합니다."],
                ],
            ),
        ]
    ) + "\n"


def write_outputs(summary: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "aihub_walk_dataset_report.md"
    summary_path = output_dir / "aihub_walk_dataset_summary.json"
    report_path.write_text(render_report(summary), encoding="utf-8", newline="\n")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return report_path, summary_path


def main() -> None:
    args = parse_args()
    root = resolve_dataset_root(args.dataset_root)
    files = iter_dataset_files(root)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_root": str(root),
        "folder_tree": build_tree_lines(root, args.max_tree_depth),
        "counts": summarize_files(files, root),
    }
    output_dir = (project_root() / args.output_dir).resolve()
    report_path, summary_path = write_outputs(summary, output_dir)

    print(f"데이터셋 루트: {root}")
    print(f"전체 파일 수: {summary['counts']['total_files']}")
    print(f"Markdown 보고서 저장: {report_path}")
    print(f"JSON 요약 저장: {summary_path}")


if __name__ == "__main__":
    main()
