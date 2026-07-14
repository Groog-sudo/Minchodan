"""Move likely non-photo web-scraped images into a rejected folder."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import WEB_EXCLUDE_TERMS

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def reject_reason(path: Path) -> str | None:
    lower_path = str(path).lower()
    if any(term in lower_path for term in WEB_EXCLUDE_TERMS):
        return "blocked_term"

    try:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
            if width < 320 or height < 240:
                return "too_small"
            aspect = max(width / height, height / width)
            if aspect > 3.5:
                return "extreme_aspect"
            if image.mode in {"RGBA", "LA", "P"}:
                rgba = image.convert("RGBA")
                alpha = rgba.getchannel("A")
                transparent = sum(1 for value in alpha.getdata() if value < 250)
                if transparent / max(width * height, 1) > 0.05:
                    return "transparent_graphic"
    except Exception:
        return "unreadable"
    return None


def quarantine(
    root: Path,
    rejected_root: Path,
    label_root: Path | None = None,
    rejected_label_root: Path | None = None,
) -> list[tuple[Path, str]]:
    moved: list[tuple[Path, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        reason = reject_reason(path)
        if not reason:
            continue
        relative = path.relative_to(root)
        target = rejected_root / reason / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
        moved.append((target, reason))
        if label_root and rejected_label_root:
            label_path = label_root / f"{path.stem}.txt"
            if label_path.exists():
                label_target = rejected_label_root / reason / f"{path.stem}.txt"
                label_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(label_path), str(label_target))
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="Quarantine likely non-photo scraped images.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--rejected-root", type=Path, default=Path("datasets/rejected"))
    parser.add_argument("--label-root", type=Path)
    parser.add_argument("--rejected-label-root", type=Path)
    args = parser.parse_args()

    moved = quarantine(args.root, args.rejected_root, args.label_root, args.rejected_label_root)
    print(f"Quarantined {len(moved)} suspect images")
    for target, reason in moved[:50]:
        print(f"{reason}: {target}")


if __name__ == "__main__":
    main()
