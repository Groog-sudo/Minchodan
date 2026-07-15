"""Shared configuration for the obstacle data mining pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

TARGET_CLASSES: dict[int, str] = {
    0: "barricade",
    1: "bench",
    2: "bicycle",
    3: "bollard",
    4: "bus",
    5: "car",
    6: "carrier",
    7: "cat",
    8: "chair",
    9: "dog",
    10: "fire_hydrant",
    11: "kiosk",
    12: "motorcycle",
    13: "movable_signage",
    14: "parking_meter",
    15: "person",
    16: "pole",
    17: "potted_plant",
    18: "power_controller",
    19: "scooter",
    20: "stop",
    21: "stroller",
    22: "table",
    23: "traffic_light",
    24: "traffic_light_controller",
    25: "traffic_sign",
    26: "tree_trunk",
    27: "truck",
    28: "wheelchair",
}

CLASS_TO_ID: dict[str, int] = {name: idx for idx, name in TARGET_CLASSES.items()}

# External datasets often use labels that differ slightly from the local taxonomy.
CLASS_ALIASES: dict[str, str] = {
    "bike": "bicycle",
    "motorbike": "motorcycle",
    "motorcycle": "motorcycle",
    "electric scooter": "scooter",
    "kick scooter": "scooter",
    "baby carriage": "stroller",
    "fire hydrant": "fire_hydrant",
    "parking meter": "parking_meter",
    "potted plant": "potted_plant",
    "traffic light": "traffic_light",
    "stoplight": "stop",
    "stop light": "stop",
    "stop": "stop",
    "traffic sign": "traffic_sign",
    "signboard": "movable_signage",
    "a-frame sign": "movable_signage",
    "tree": "tree_trunk",
}

WEB_EXCLUDE_TERMS: tuple[str, ...] = (
    "anime",
    "cartoon",
    "comic",
    "manga",
    "game",
    "gaming",
    "character",
    "avatar",
    "meme",
    "funny",
    "clipart",
    "clip-art",
    "icon",
    "vector",
    "illustration",
    "drawing",
    "render",
    "3d",
    "toy",
    "lego",
    "wallpaper",
    "pngtree",
    "pinterest",
    "shutterstock",
    "istock",
    "freepik",
    "vecteezy",
    "deviantart",
)


@dataclass(frozen=True)
class Settings:
    """Runtime paths and credentials.

    Kaggle also supports the official KAGGLE_USERNAME/KAGGLE_KEY environment
    variables or a user-level kaggle.json file. We intentionally do not store
    credentials in source code.
    """

    project_root: Path = Path(__file__).resolve().parent
    # scripts/obstacle_data_miner 에서 상위 2단계 올라가 training/datasets 폴더에 접근
    dataset_root: Path = project_root.parent.parent / "training" / "datasets"
    object_detection_root: Path = dataset_root / "detection" / "aihub_finetune"
    segmentation_root: Path = dataset_root / "segmentation" / "aihub_finetune"
    raw_root: Path = dataset_root / "object_detection" / "raw"
    image_root: Path = dataset_root / "object_detection" / "images"
    label_root: Path = dataset_root / "object_detection" / "labels"
    hash_index_path: Path = dataset_root / "object_detection" / "hash_index.json"
    kaggle_username: str | None = os.getenv("KAGGLE_USERNAME")
    kaggle_key: str | None = os.getenv("KAGGLE_KEY")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.35"))
    default_model: str = os.getenv("DEFAULT_MODEL", "yolo26n.pt")

    def ensure_directories(self) -> None:
        for path in (self.dataset_root, self.object_detection_root, self.segmentation_root, self.raw_root, self.image_root, self.label_root):
            path.mkdir(parents=True, exist_ok=True)


SETTINGS = Settings()
