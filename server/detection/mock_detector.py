import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.detector_interface import DetectorInterface, SegmentorInterface
from server.detection.schemas import BBox, Detection, SurfaceResult


class MockDetector(DetectorInterface):
    """가중치 없을 때 사용하는 Mock 탐지기."""

    def __init__(self, mock_detections: list[Detection] | None = None):
        self._detections = mock_detections

    def load(self) -> bool:
        return True

    def predict(self, frame) -> list[Detection]:
        if self._detections is not None:
            return self._detections
        height, width = frame.shape[:2]
        return [
            Detection(
                class_name="unknown",
                confidence=0.87,
                bbox=BBox(
                    x=width * 0.3,
                    y=height * 0.5,
                    w=width * 0.2,
                    h=height * 0.2,
                ),
                track_id=None,
                speed=0.0,
                direction="unknown",
                risk=None,
            )
        ]


class MockSegmentor(SegmentorInterface):
    """가중치 없을 때 사용하는 Mock 분할기."""

    def __init__(self, mock_surfaces: list[SurfaceResult] | None = None):
        self._surfaces = mock_surfaces

    def load(self) -> bool:
        return True

    def predict(self, frame) -> list[SurfaceResult]:
        if self._surfaces is not None:
            return self._surfaces
        height, width = frame.shape[:2]
        return [
            SurfaceResult(
                class_name="unknown",
                mask=None,
                centroid=[width * 0.5, height * 0.8],
            )
        ]
