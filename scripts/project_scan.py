# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
    "node_modules",
    "outputs",
    "runs",
    "venv",
}

DOC_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".hwp"}
PYTHON_EXTENSIONS = {".py"}
TEXT_SCAN_EXTENSIONS = {
    ".bat",
    ".env",
    ".example",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_SCAN_NAMES = {
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "requirements-dev.txt",
    "requirements.txt",
}

MAX_TEXT_BYTES = 2_000_000
MAX_LIST_ITEMS = 120
MAX_KEYWORD_FILES_PER_CATEGORY = 80
OUTPUT_FILE_NAMES = {
    "project_scan_report.md",
    "project_scan_summary.json",
}

KEYWORDS = {
    "yolo": [
        "yolo",
        "ultralytics",
        "detect",
        "predict",
        "train",
        "bbox",
        "class_id",
        "confidence",
    ],
    "langchain": [
        "langchain",
        "langgraph",
        "agent",
        "tool",
        "chain",
        "Runnable",
        "ChatOpenAI",
    ],
    "fastapi": [
        "fastapi",
        "APIRouter",
        "uvicorn",
        "BaseModel",
        "HTTPException",
    ],
    "openai": [
        "OpenAI",
        "AsyncOpenAI",
        "OPENAI_API_KEY",
        "chat.completions",
        "responses",
    ],
    "dataset": [
        "dataset",
        "data.yaml",
        "images",
        "labels",
        "json",
        "annotation",
        "frame",
    ],
}


@dataclass
class FileRecord:
    path: str
    size_bytes: int


def resolve_default_root() -> Path:
    current_dir = Path(__file__).resolve().parent
    return current_dir.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minchodan 프로젝트 코드와 문서를 스캔하여 Markdown/JSON 보고서를 생성합니다."
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=str(resolve_default_root()),
        help="스캔할 프로젝트 루트 경로입니다. 생략하면 현재 Minchodan 루트를 사용합니다.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="산출물 저장 폴더입니다. 생략하면 프로젝트 루트에 저장합니다.",
    )
    parser.add_argument(
        "--max-tree-depth",
        type=int,
        default=3,
        help="보고서에 표시할 폴더 트리 깊이입니다.",
    )
    return parser.parse_args()


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def should_skip_dir(path: Path) -> bool:
    return path.name in EXCLUDED_DIR_NAMES


def iter_project_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)
        dir_names[:] = [
            dir_name
            for dir_name in sorted(dir_names)
            if not should_skip_dir(current_path / dir_name)
        ]
        for file_name in sorted(file_names):
            if file_name in OUTPUT_FILE_NAMES:
                continue
            files.append(current_path / file_name)
    return files


def is_doc_file(path: Path) -> bool:
    return path.suffix.lower() in DOC_EXTENSIONS


def is_python_file(path: Path) -> bool:
    return path.suffix.lower() in PYTHON_EXTENSIONS


def is_text_scan_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SCAN_EXTENSIONS or path.name in TEXT_SCAN_NAMES


def read_text_safely(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return ""
    except OSError:
        return ""

    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""


def make_file_record(path: Path, root: Path) -> FileRecord:
    try:
        size_bytes = path.stat().st_size
    except OSError:
        size_bytes = 0
    return FileRecord(path=relative_path(path, root), size_bytes=size_bytes)


def find_named_files(files: list[Path], root: Path, names: set[str]) -> dict[str, list[FileRecord]]:
    found: dict[str, list[FileRecord]] = {name: [] for name in sorted(names)}
    for path in files:
        if path.name in found:
            found[path.name].append(make_file_record(path, root))
    return found


def summarize_extensions(files: list[Path]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter(path.suffix.lower() or "(no extension)" for path in files)
    return [
        {"extension": extension, "count": count}
        for extension, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def scan_keywords(files: list[Path], root: Path) -> dict[str, list[dict[str, Any]]]:
    keyword_report: dict[str, list[dict[str, Any]]] = {category: [] for category in KEYWORDS}

    for path in files:
        if not is_text_scan_file(path):
            continue
        text = read_text_safely(path)
        if not text:
            continue
        lowered_text = text.lower()

        for category, keywords in KEYWORDS.items():
            matched = [
                keyword
                for keyword in keywords
                if keyword.lower() in lowered_text
            ]
            if not matched:
                continue
            keyword_report[category].append(
                {
                    "path": relative_path(path, root),
                    "matched_keywords": matched,
                    "line_count": text.count("\n") + 1,
                }
            )

    for category, records in keyword_report.items():
        records.sort(key=lambda item: (item["path"].count("/"), item["path"]))
        keyword_report[category] = records[:MAX_KEYWORD_FILES_PER_CATEGORY]
    return keyword_report


def build_tree_lines(root: Path, max_depth: int) -> list[str]:
    lines = [root.name + "/"]

    def add_children(directory: Path, depth: int, prefix: str) -> None:
        if depth > max_depth:
            return
        try:
            children = [
                child
                for child in directory.iterdir()
                if not should_skip_dir(child) and child.name not in OUTPUT_FILE_NAMES
            ]
        except OSError:
            return

        children.sort(key=lambda child: (child.is_file(), child.name.lower()))
        visible_children = children[:MAX_LIST_ITEMS]
        for index, child in enumerate(visible_children):
            connector = "└── " if index == len(visible_children) - 1 else "├── "
            suffix = "/" if child.is_dir() else ""
            lines.append(f"{prefix}{connector}{child.name}{suffix}")
            if child.is_dir():
                child_prefix = prefix + ("    " if index == len(visible_children) - 1 else "│   ")
                add_children(child, depth + 1, child_prefix)
        if len(children) > len(visible_children):
            lines.append(f"{prefix}└── ... ({len(children) - len(visible_children)}개 생략)")

    add_children(root, 1, "")
    return lines


def records_to_json(records: list[FileRecord]) -> list[dict[str, Any]]:
    return [{"path": record.path, "size_bytes": record.size_bytes} for record in records]


def top_records(records: list[FileRecord], limit: int = MAX_LIST_ITEMS) -> list[dict[str, Any]]:
    return records_to_json(records[:limit])


def collect_summary(root: Path, max_tree_depth: int) -> dict[str, Any]:
    files = iter_project_files(root)
    doc_records = [make_file_record(path, root) for path in files if is_doc_file(path)]
    python_records = [make_file_record(path, root) for path in files if is_python_file(path)]
    key_files = find_named_files(
        files,
        root,
        {
            ".env.example",
            "package.json",
            "pyproject.toml",
            "README.md",
            "requirements.txt",
        },
    )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(root),
        "counts": {
            "total_files": len(files),
            "document_files": len(doc_records),
            "python_files": len(python_records),
        },
        "folder_tree": build_tree_lines(root, max_tree_depth),
        "extension_counts": summarize_extensions(files),
        "key_files": {
            name: records_to_json(records)
            for name, records in key_files.items()
        },
        "document_files": top_records(doc_records),
        "python_files": top_records(python_records),
        "keyword_hits": scan_keywords(files, root),
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def render_record_table(records: list[dict[str, Any]], empty_message: str) -> str:
    if not records:
        return empty_message
    rows = [[record["path"], record["size_bytes"]] for record in records]
    return markdown_table(["파일", "크기(bytes)"], rows)


def render_keyword_section(summary: dict[str, Any]) -> str:
    sections: list[str] = []
    keyword_hits: dict[str, list[dict[str, Any]]] = summary["keyword_hits"]

    for category, records in keyword_hits.items():
        sections.append(f"### {category}")
        if not records:
            sections.append("해당 키워드가 포함된 파일을 찾지 못했습니다.")
            continue
        rows = [
            [
                record["path"],
                ", ".join(record["matched_keywords"]),
                record["line_count"],
            ]
            for record in records
        ]
        sections.append(markdown_table(["파일", "매칭 키워드", "라인 수"], rows))
    return "\n\n".join(sections)


def render_report(summary: dict[str, Any]) -> str:
    extension_rows = [
        [item["extension"], item["count"]]
        for item in summary["extension_counts"][:30]
    ]
    key_file_rows = [
        [name, ", ".join(record["path"] for record in records) or "없음"]
        for name, records in summary["key_files"].items()
    ]
    metadata = "\n".join(
        [
            f"> **작성일**: {summary['generated_at'][:10]}",
            "> **버전**: v0.1.0",
            f"> **대상 루트**: `{summary['project_root']}`",
        ]
    )

    return "\n\n".join(
        [
            "# 프로젝트 스캔 보고서",
            metadata,
            "---",
            "## 1. 요약",
            markdown_table(
                ["항목", "값"],
                [
                    ["전체 파일 수", summary["counts"]["total_files"]],
                    ["문서 파일 수", summary["counts"]["document_files"]],
                    ["Python 파일 수", summary["counts"]["python_files"]],
                ],
            ),
            "---",
            "## 2. 폴더 트리",
            "```text\n" + "\n".join(summary["folder_tree"]) + "\n```",
            "---",
            "## 3. 핵심 파일",
            markdown_table(["파일명", "발견 경로"], key_file_rows),
            "---",
            "## 4. 확장자 통계",
            markdown_table(["확장자", "파일 수"], extension_rows),
            "---",
            "## 5. 문서 파일",
            render_record_table(summary["document_files"], "문서 파일을 찾지 못했습니다."),
            "---",
            "## 6. Python 파일",
            render_record_table(summary["python_files"], "Python 파일을 찾지 못했습니다."),
            "---",
            "## 7. 키워드 기반 관련 파일",
            render_keyword_section(summary),
            "---",
            "## 8. 다음 작업 제안",
            markdown_table(
                ["순서", "작업"],
                [
                    [1, "YOLO 관련 파일을 열어 실제 탐지/추론 구조와 모델 경로를 확인합니다."],
                    [2, "LangChain/LangGraph 관련 파일을 열어 탐지 JSON이 연결될 입력 스키마를 확인합니다."],
                    [3, "데이터셋 원본 폴더를 별도 스캔하여 라벨 형식과 YOLO 변환 가능성을 판단합니다."],
                    [4, "확인된 라벨 형식 기준으로 class_mapping.json과 변환 계획을 작성합니다."],
                ],
            ),
        ]
    ) + "\n"


def write_outputs(summary: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "project_scan_report.md"
    summary_path = output_dir / "project_scan_summary.json"

    report_path.write_text(render_report(summary), encoding="utf-8", newline="\n")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    return report_path, summary_path


def main() -> None:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"프로젝트 루트 폴더를 찾을 수 없습니다: {root}")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else root
    summary = collect_summary(root, args.max_tree_depth)
    report_path, summary_path = write_outputs(summary, output_dir)

    print(f"Markdown 보고서 저장: {report_path}")
    print(f"JSON 요약 저장: {summary_path}")


if __name__ == "__main__":
    main()
