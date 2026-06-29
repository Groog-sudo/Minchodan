import sys
from abc import ABC, abstractmethod

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.detection.schemas import Detection, SurfaceResult


class DetectorInterface(ABC):
    """탐지 모델 추상 인터페이스."""

    @abstractmethod
    def load(self) -> bool:
        """모델 가중치를 로드하고 성공 여부를 반환한다."""

    @abstractmethod
    def predict(self, frame) -> list[Detection]:
        """프레임에서 객체를 탐지해 Detection 리스트를 반환한다."""


class SegmentorInterface(ABC):
    """분할 모델 추상 인터페이스."""

    @abstractmethod
    def load(self) -> bool:
        """모델 가중치를 로드하고 성공 여부를 반환한다."""

    @abstractmethod
    def predict(self, frame) -> list[SurfaceResult]:
        """프레임에서 노면을 분할해 SurfaceResult 리스트를 반환한다."""
