# -*- coding: utf-8 -*-
import sys
from typing import Any

from server.detection.schemas import (
    BBox,
    Detection,
    DetectionResult,
    ReflexAlert,
    SurfaceResult,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


__all__ = [
    "BBox",
    "ByteTrackTracker",
    "Detection",
    "DetectionPipeline",
    "DetectionResult",
    "DetectorInterface",
    "MockDetector",
    "MockSegmentor",
    "ReflexAlert",
    "SegmentorInterface",
    "SurfaceResult",
    "YoloDetector",
    "YoloSegmentor",
]


def __getattr__(name: str) -> Any:
    """무거운 선택 의존성은 실제 접근 시점에만 로드한다."""
    if name == "ByteTrackTracker":
        from server.detection.bytetrack_tracker import ByteTrackTracker

        return ByteTrackTracker
    if name == "DetectionPipeline":
        from server.detection.detection_pipeline import DetectionPipeline

        return DetectionPipeline
    if name in {"DetectorInterface", "SegmentorInterface"}:
        from server.detection.detector_interface import DetectorInterface, SegmentorInterface

        return {
            "DetectorInterface": DetectorInterface,
            "SegmentorInterface": SegmentorInterface,
        }[name]
    if name in {"MockDetector", "MockSegmentor"}:
        from server.detection.mock_detector import MockDetector, MockSegmentor

        return {
            "MockDetector": MockDetector,
            "MockSegmentor": MockSegmentor,
        }[name]
    if name == "YoloDetector":
        from server.detection.yolo_detector import YoloDetector

        return YoloDetector
    if name == "YoloSegmentor":
        from server.detection.yolo_segmentor import YoloSegmentor

        return YoloSegmentor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
