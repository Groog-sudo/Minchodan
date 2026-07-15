"""Teacher-model auto-labeling into YOLO text files."""

from __future__ import annotations

import shutil
from pathlib import Path

from config import CLASS_ALIASES, CLASS_TO_ID, SETTINGS
from utils.format_converter import HashIndex, safe_image_open, xyxy_to_yolo


class AutoLabeler:
    """Run a pretrained detector and save normalized YOLO labels."""

    def __init__(
        self,
        model_name: str = SETTINGS.default_model,
        confidence: float = 0.35,
        image_root: Path | None = None,
        label_root: Path | None = None,
        allowed_classes: list[str] | None = None,
    ) -> None:
        self.model_name = model_name
        self.confidence = confidence
        self.image_root = image_root or SETTINGS.image_root
        self.label_root = label_root or SETTINGS.label_root
        self.image_root.mkdir(parents=True, exist_ok=True)
        self.label_root.mkdir(parents=True, exist_ok=True)
        self.allowed_classes = set(allowed_classes or [])
        self.hash_index = HashIndex(SETTINGS.hash_index_path)

    def _model(self):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("Install ultralytics first: pip install ultralytics") from exc
        return YOLO(self.model_name)

    def label_directory(self, source_dir: Path) -> int:
        model = self._model()
        image_paths = [
            path
            for path in source_dir.rglob("*")
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        ]

        labeled_count = 0
        for image_path in image_paths:
            try:
                with safe_image_open(image_path) as image:
                    if image is None:
                        continue
                    duplicate_source = self.hash_index.duplicate_source(image)
                    if duplicate_source and self._is_final_output_duplicate(duplicate_source):
                        continue
                    width, height = image.size

                results = model.predict(str(image_path), conf=self.confidence, verbose=False)
                label_lines = self._results_to_yolo_lines(results, width, height)
                if not label_lines:
                    continue

                safe_prefix = self._safe_name(image_path.parent.name)
                output_image = self.image_root / f"{safe_prefix}_{image_path.name}"
                output_label = self.label_root / f"{output_image.stem}.txt"
                if output_image.exists():
                    output_image = self.image_root / f"{image_path.stem}_{labeled_count}{image_path.suffix}"
                    output_label = self.label_root / f"{output_image.stem}.txt"

                shutil.copy2(image_path, output_image)
                output_label.write_text("\n".join(label_lines) + "\n", encoding="utf-8")
                with safe_image_open(output_image) as image:
                    if image is not None:
                        self.hash_index.add(image, str(output_image))
                labeled_count += 1
            except Exception as exc:
                print(f"[WARN] Failed to label {image_path}: {exc}")

        self.hash_index.save()
        print(f"Auto-labeled {labeled_count} images from {source_dir}")
        return labeled_count

    def _is_final_output_duplicate(self, duplicate_source: str) -> bool:
        try:
            return Path(duplicate_source).resolve().is_relative_to(self.image_root.resolve())
        except Exception:
            return False

    @staticmethod
    def _safe_name(text: str) -> str:
        safe = "".join(char if char.isalnum() else "_" for char in text)
        return safe.strip("_")[:80] or "image"

    def _results_to_yolo_lines(self, results, width: int, height: int) -> list[str]:
        lines: list[str] = []
        for result in results:
            names = result.names
            for box in result.boxes:
                source_name = names[int(box.cls.item())].lower().replace(" ", "_")
                target_name = CLASS_ALIASES.get(source_name, source_name)
                target_id = CLASS_TO_ID.get(target_name)
                if target_id is None:
                    continue
                if self.allowed_classes and target_name not in self.allowed_classes:
                    continue
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
                x_center, y_center, box_width, box_height = xyxy_to_yolo(x1, y1, x2, y2, width, height)
                lines.append(f"{target_id} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}")
        return lines
