import os

import numpy as np

from server.detection.detector_interface import DetectorInterface, SegmentorInterface
from server.detection.schemas import BBox, Detection, SurfaceResult


class MockDetector(DetectorInterface):
    """테스트 및 안전 폴백용 Mock Detector"""

    def load(self) -> bool:
        return True

    def predict(self, frame: np.ndarray) -> list[Detection]:
        if os.getenv("TEST_VERIFY_MODE") == "true":
            return [
                Detection(
                    class_name="bollard",
                    confidence=0.89,
                    bbox=BBox(x=320.0, y=240.0, w=100.0, h=200.0),
                    direction="front",
                )
            ]
        return []


class MockSegmentor(SegmentorInterface):
    """테스트 및 안전 폴백용 Mock Segmentor"""

    def load(self) -> bool:
        return True

    def predict(self, frame: np.ndarray) -> list[SurfaceResult]:
        return []
