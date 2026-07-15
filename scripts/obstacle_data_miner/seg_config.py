"""Segmentation configuration for road-surface data mining."""

from __future__ import annotations

from pathlib import Path

from config import SETTINGS


SEG_TARGET_CLASSES: dict[int, str] = {
    0: "sidewalk_normal",
    1: "caution",
    2: "roadway",
    3: "braille_normal",
}

SEG_CLASS_TO_ID: dict[str, int] = {name: idx for idx, name in SEG_TARGET_CLASSES.items()}

SEG_CLASS_ALIASES: dict[str, str] = {
    "sidewalk": "sidewalk_normal",
    "normal_sidewalk": "sidewalk_normal",
    "road": "roadway",
    "roadway": "roadway",
    "car_road": "roadway",
    "braille_block": "braille_normal",
    "tactile_paving": "braille_normal",
    "tactile_block": "braille_normal",
    "damaged_sidewalk": "caution",
    "puddle": "caution",
    "slope": "caution",
    "curb": "caution",
}

SEG_DATASET_ROOT: Path = SETTINGS.segmentation_root
SEG_RAW_ROOT: Path = SEG_DATASET_ROOT / "raw"
SEG_IMAGE_ROOT: Path = SEG_DATASET_ROOT / "images"
SEG_LABEL_ROOT: Path = SEG_DATASET_ROOT / "labels"
SEG_MASK_ROOT: Path = SEG_DATASET_ROOT / "masks"
