"""FiftyOne Open Images/COCO miner."""

from __future__ import annotations

import shutil
from pathlib import Path

from config import CLASS_TO_ID, SETTINGS
from utils.format_converter import HashIndex, safe_image_open


SOURCE_CLASS_MAPS: dict[str, dict[str, str]] = {
    "coco-2017": {
        "person": "person",
        "bicycle": "bicycle",
        "car": "car",
        "motorcycle": "motorcycle",
        "bus": "bus",
        "truck": "truck",
        "traffic light": "traffic_light",
        "fire hydrant": "fire_hydrant",
        "parking meter": "parking_meter",
        "bench": "bench",
        "cat": "cat",
        "dog": "dog",
        "chair": "chair",
        "suitcase": "carrier",
        "potted plant": "potted_plant",
        "dining table": "table",
        "stop sign": "traffic_sign",
    },
    "open-images-v7": {
        "Person": "person",
        "Bicycle": "bicycle",
        "Car": "car",
        "Motorcycle": "motorcycle",
        "Bus": "bus",
        "Truck": "truck",
        "Traffic light": "traffic_light",
        "Fire hydrant": "fire_hydrant",
        "Parking meter": "parking_meter",
        "Bench": "bench",
        "Cat": "cat",
        "Dog": "dog",
        "Chair": "chair",
        "Suitcase": "carrier",
        "Potted plant": "potted_plant",
        "Table": "table",
        "Wheelchair": "wheelchair",
        "Traffic sign": "traffic_sign",
        "Tree": "tree_trunk",
    },
}


class FiftyOneMiner:
    """Download target classes from FiftyOne Zoo datasets and export YOLO labels."""

    def __init__(self, export_root: Path | None = None) -> None:
        self.export_root = export_root or SETTINGS.object_detection_root / "fiftyone_exports"
        self.export_root.mkdir(parents=True, exist_ok=True)
        self.hash_index = HashIndex(SETTINGS.hash_index_path)

    def download_and_export(
        self,
        dataset_name: str = "open-images-v7",
        split: str = "train",
        max_samples: int = 500,
        target_classes: list[str] | None = None,
    ) -> Path:
        try:
            import fiftyone.zoo as foz
        except ImportError as exc:
            raise RuntimeError("Install fiftyone first: pip install fiftyone") from exc

        source_map = SOURCE_CLASS_MAPS[dataset_name]
        normalized_source_map = {source_label.lower(): target_label for source_label, target_label in source_map.items()}
        source_classes = self._source_classes_for_targets(source_map, target_classes)
        if target_classes and not source_classes:
            available_targets = sorted(set(source_map.values()))
            raise ValueError(
                f"{dataset_name} has no mapped source classes for {target_classes}. "
                f"Available mapped targets: {available_targets}"
            )
        dataset = foz.load_zoo_dataset(
            dataset_name,
            split=split,
            label_types=["detections"],
            classes=source_classes,
            max_samples=max_samples,
            only_matching=True,
        )

        suffix = "all" if not target_classes else "_".join(target_classes)
        export_dir = self.export_root / f"{dataset_name}_{split}_{max_samples}_{suffix}_aihub_order"
        image_dir = export_dir / "images"
        label_dir = export_dir / "labels"
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        label_field = self._detect_label_field(dataset)
        exported = 0
        for sample in dataset:
            detections = getattr(sample, label_field, None)
            if detections is None:
                continue
            lines = self._detections_to_yolo_lines(detections.detections, normalized_source_map)
            if not lines:
                continue
            image_path = Path(sample.filepath)
            with safe_image_open(image_path) as image:
                if image is None:
                    continue
                duplicate_source = self.hash_index.duplicate_source(image)
                if duplicate_source:
                    print(f"[SKIP] duplicate image {image_path.name} ~= {duplicate_source}")
                    continue
                self.hash_index.add(image, str(image_path))
            output_name = f"{dataset_name.replace('-', '_')}_{split}_{exported:06d}{image_path.suffix.lower()}"
            shutil.copy2(image_path, image_dir / output_name)
            (label_dir / f"{Path(output_name).stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
            exported += 1

        self.hash_index.save()
        print(f"Exported {exported} remapped samples to {export_dir}")
        return export_dir

    @staticmethod
    def _source_classes_for_targets(source_map: dict[str, str], target_classes: list[str] | None) -> list[str]:
        if not target_classes:
            return list(source_map)
        targets = {item.strip().lower().replace("-", "_").replace(" ", "_") for item in target_classes}
        return [source_label for source_label, target_label in source_map.items() if target_label in targets]

    @staticmethod
    def _detect_label_field(dataset) -> str:
        sample = dataset.first()
        if sample is None:
            raise RuntimeError("FiftyOne dataset is empty")
        for field_name in ("ground_truth", "detections"):
            if field_name in sample.field_names:
                return field_name
        raise RuntimeError(f"Cannot find detection label field in sample fields: {sample.field_names}")

    @staticmethod
    def _detections_to_yolo_lines(detections, source_map: dict[str, str]) -> list[str]:
        lines: list[str] = []
        for detection in detections:
            source_label = detection.label.strip().lower()
            target_label = source_map.get(source_label)
            if target_label is None:
                continue
            target_id = CLASS_TO_ID[target_label]
            x, y, width, height = [float(value) for value in detection.bounding_box]
            x_center = x + width / 2
            y_center = y + height / 2
            lines.append(f"{target_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
        return lines
