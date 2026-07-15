"""Annotation conversion, image validation, and pHash de-duplication utilities."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from config import CLASS_ALIASES, CLASS_TO_ID, SETTINGS
from PIL import Image


@contextmanager
def safe_image_open(path: Path) -> Iterator[Image.Image | None]:
    try:
        image = Image.open(path)
        image.verify()
        image = Image.open(path).convert("RGB")
        yield image
    except Exception:
        yield None
    finally:
        with suppress(Exception):
            image.close()  # type: ignore[name-defined]


def normalize_label(label: str) -> str:
    key = label.strip().lower().replace("-", "_").replace(" ", "_")
    return CLASS_ALIASES.get(key, key)


def xyxy_to_yolo(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    x1 = max(0.0, min(x1, image_width))
    x2 = max(0.0, min(x2, image_width))
    y1 = max(0.0, min(y1, image_height))
    y2 = max(0.0, min(y2, image_height))
    return (
        ((x1 + x2) / 2.0) / image_width,
        ((y1 + y2) / 2.0) / image_height,
        abs(x2 - x1) / image_width,
        abs(y2 - y1) / image_height,
    )


class HashIndex:
    """Persistent perceptual hash index for duplicate image filtering."""

    def __init__(self, index_path: Path, max_distance: int = 4) -> None:
        self.index_path = index_path
        self.max_distance = max_distance
        self.entries: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            self.entries = json.loads(self.index_path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")

    def compute(self, image: Image.Image) -> str:
        try:
            import imagehash
        except ImportError as exc:
            raise RuntimeError("Install ImageHash first: pip install ImageHash") from exc
        return str(imagehash.phash(image))

    def is_duplicate(self, image: Image.Image) -> bool:
        return self.duplicate_source(image) is not None

    def duplicate_source(self, image: Image.Image) -> str | None:
        try:
            import imagehash
        except ImportError as exc:
            raise RuntimeError("Install ImageHash first: pip install ImageHash") from exc

        current = imagehash.hex_to_hash(self.compute(image))
        for known_hash, source in self.entries.items():
            if current - imagehash.hex_to_hash(known_hash) <= self.max_distance:
                return source
        return None

    def add(self, image: Image.Image, source: str) -> None:
        self.entries[self.compute(image)] = source


class FormatConverter:
    """Convert VOC XML and COCO JSON annotations into the local YOLO format."""

    def __init__(self, image_root: Path | None = None, label_root: Path | None = None) -> None:
        self.image_root = image_root or SETTINGS.image_root
        self.label_root = label_root or SETTINGS.label_root
        self.image_root.mkdir(parents=True, exist_ok=True)
        self.label_root.mkdir(parents=True, exist_ok=True)

    def convert_dataset_annotations(self, dataset_dir: Path) -> None:
        for xml_path in dataset_dir.rglob("*.xml"):
            self.convert_voc_file(xml_path)
        for json_path in dataset_dir.rglob("*.json"):
            if self._looks_like_coco(json_path):
                self.convert_coco_file(json_path)

    def convert_voc_file(self, xml_path: Path) -> Path | None:
        root = ET.parse(xml_path).getroot()  # noqa: S314
        filename = root.findtext("filename")
        size = root.find("size")
        if not filename or size is None:
            return None

        width = int(size.findtext("width", "0"))
        height = int(size.findtext("height", "0"))
        lines: list[str] = []

        for obj in root.findall("object"):
            label = normalize_label(obj.findtext("name", ""))
            class_id = CLASS_TO_ID.get(label)
            bndbox = obj.find("bndbox")
            if class_id is None or bndbox is None:
                continue
            x1 = float(bndbox.findtext("xmin", "0"))
            y1 = float(bndbox.findtext("ymin", "0"))
            x2 = float(bndbox.findtext("xmax", "0"))
            y2 = float(bndbox.findtext("ymax", "0"))
            values = xyxy_to_yolo(x1, y1, x2, y2, width, height)
            lines.append(f"{class_id} " + " ".join(f"{value:.6f}" for value in values))

        if not lines:
            return None
        label_path = self.label_root / f"{Path(filename).stem}.txt"
        label_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return label_path

    def convert_coco_file(self, json_path: Path) -> int:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        categories = {
            item["id"]: normalize_label(item["name"]) for item in data.get("categories", [])
        }
        images = {item["id"]: item for item in data.get("images", [])}
        grouped: dict[int, list[str]] = {}

        for annotation in data.get("annotations", []):
            label = categories.get(annotation.get("category_id"), "")
            class_id = CLASS_TO_ID.get(label)
            image_info = images.get(annotation.get("image_id"))
            if class_id is None or image_info is None or "bbox" not in annotation:
                continue
            x, y, width, height = (float(value) for value in annotation["bbox"])
            values = xyxy_to_yolo(
                x,
                y,
                x + width,
                y + height,
                int(image_info["width"]),
                int(image_info["height"]),
            )
            grouped.setdefault(annotation["image_id"], []).append(
                f"{class_id} " + " ".join(f"{value:.6f}" for value in values)
            )

        for image_id, lines in grouped.items():
            stem = Path(images[image_id]["file_name"]).stem
            (self.label_root / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return len(grouped)

    @staticmethod
    def _looks_like_coco(json_path: Path) -> bool:
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return all(key in data for key in ("images", "annotations", "categories"))
        except Exception:
            return False
