import numpy as np

from server.detection.detector_interface import DetectorInterface, SegmentorInterface
from server.detection.schemas import Detection, SurfaceResult


class MockDetector(DetectorInterface):
    """테스트 및 안전 폴백용 Mock Detector"""
    def load(self) -> bool:
        return True

    def predict(self, frame: np.ndarray) -> list[Detection]:
        return []


class MockSegmentor(SegmentorInterface):
    """테스트 및 안전 폴백용 Mock Segmentor"""
    def load(self) -> bool:
        return True

    def predict(self, frame: np.ndarray) -> list[SurfaceResult]:
        return []
