# -*- coding: utf-8 -*-
import asyncio
import sys
from unittest.mock import AsyncMock

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import numpy as np
import pytest

from server.bus.producer import RiskEventProducer
from server.bus.redis_client import RedisBus
from server.detection import (
    BBox,
    ByteTrackTracker,
    Detection,
    DetectionPipeline,
    DetectionResult,
    MockDetector,
    MockSegmentor,
    ReflexAlert,
    YoloDetector,
)
from server.detection.gates import reflex_gate, surface_gate
from server.detection.schemas import SurfaceResult


@pytest.fixture
def frame() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_redis_bus() -> RedisBus:
    bus = RedisBus(url="redis://localhost:6379")
    bus._client = AsyncMock()
    bus.publish_event = AsyncMock(return_value="mock-id")
    bus.set_track_context = AsyncMock(return_value=True)
    bus.get_track_context = AsyncMock(return_value={})
    return bus


class TestSchemas:
    def test_bbox(self):
        b = BBox(x=10.0, y=20.0, w=30.0, h=40.0)
        assert b.model_dump() == {"x": 10.0, "y": 20.0, "w": 30.0, "h": 40.0}

    def test_detection(self):
        d = Detection(
            class_name="kickboard",
            confidence=0.9,
            bbox=BBox(x=0.0, y=0.0, w=10.0, h=10.0),
        )
        assert d.class_name == "kickboard"
        assert d.track_id is None


class TestMockDetector:
    def test_mock_detector(self, frame):
        det = MockDetector()
        assert det.load() is True
        results = det.predict(frame)
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].class_name == "unknown"

    def test_mock_segmentor(self, frame):
        seg = MockSegmentor()
        assert seg.load() is True
        results = seg.predict(frame)
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].class_name == "unknown"


class TestGates:
    def test_reflex_gate_high_risk_bottom(self):
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is not None
        assert alert.alert_id == "high_front"

    def test_reflex_gate_low_position(self):
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=0.0, y=0.0, w=10.0, h=10.0),
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_low_risk_class(self):
        det = Detection(
            class_name="kickboard",
            confidence=0.9,
            bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_surface_gate_p0(self):
        surf = SurfaceResult(class_name="stair", centroid=[320.0, 400.0])
        alert = surface_gate(surf, 480.0)
        assert alert is not None
        assert alert.alert_id == "surface_stair"

    def test_surface_gate_none(self):
        surf = SurfaceResult(class_name="sidewalk_damaged", centroid=[320.0, 400.0])
        alert = surface_gate(surf, 480.0)
        assert alert is None


class TestByteTrackTracker:
    @pytest.mark.asyncio
    async def test_update_without_track_id(self, mock_redis_bus):
        tracker = ByteTrackTracker()
        dets = [Detection(class_name="kickboard", confidence=0.8, bbox=BBox(x=0, y=0, w=10, h=10))]
        updated = await tracker.update(dets, mock_redis_bus)
        assert updated[0].track_id is None
        assert updated[0].speed == 0.0

    @pytest.mark.asyncio
    async def test_update_with_track_id(self, mock_redis_bus):
        tracker = ByteTrackTracker()
        dets = [
            Detection(
                class_name="kickboard",
                confidence=0.8,
                bbox=BBox(x=0, y=100, w=10, h=10),
                track_id="T-0001",
            )
        ]
        updated = await tracker.update(dets, mock_redis_bus)
        assert updated[0].track_id == "T-0001"
        mock_redis_bus.set_track_context.assert_called_once()


class TestPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_none_frame(self, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=MockDetector(),
            segmentor=MockSegmentor(),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(None, "test", "evt-1", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "none"

    @pytest.mark.asyncio
    async def test_pipeline_mock(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=MockDetector(),
            segmentor=MockSegmentor(),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-2", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint in ("none", "low")
        assert result.inference_ms >= 0


class FailingDetector(MockDetector):
    """predict()에서 예외를 발생시키는 목업 Detector."""

    def predict(self, frame):
        raise RuntimeError("detector failure")


class FailingSegmentor(MockSegmentor):
    """predict()에서 예외를 발생시키는 목업 Segmentor."""

    def predict(self, frame):
        raise RuntimeError("segmentor failure")


class TestPipelineRobustness:
    @pytest.mark.asyncio
    async def test_detector_exception_continues_with_segmentor(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=FailingDetector(),
            segmentor=MockSegmentor(),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-det-fail", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.detections == []
        assert len(result.surface) == 1
        assert result.risk_hint == "low"

    @pytest.mark.asyncio
    async def test_segmentor_exception_returns_detections_only(self, frame, mock_redis_bus):
        detector = MockDetector(
            mock_detections=[
                Detection(
                    class_name="kickboard",
                    confidence=0.8,
                    bbox=BBox(x=10.0, y=10.0, w=20.0, h=20.0),
                )
            ]
        )
        pipeline = DetectionPipeline(
            detector=detector,
            segmentor=FailingSegmentor(),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-seg-fail", "dev-1")
        assert isinstance(result, DetectionResult)
        assert len(result.detections) == 1
        assert result.surface == []
        assert result.risk_hint == "mid"

    @pytest.mark.asyncio
    async def test_reflex_gate_triggers(self, frame, mock_redis_bus):
        detector = MockDetector(
            mock_detections=[
                Detection(
                    class_name="car",
                    confidence=0.9,
                    bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
                )
            ]
        )
        pipeline = DetectionPipeline(
            detector=detector,
            segmentor=MockSegmentor(mock_surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-reflex", "dev-1")
        assert isinstance(result, ReflexAlert)
        assert result.alert_id == "high_front"
        assert result.direction == "front"

    @pytest.mark.asyncio
    async def test_surface_gate_triggers(self, frame, mock_redis_bus):
        segmentor = MockSegmentor(
            mock_surfaces=[SurfaceResult(class_name="stair", centroid=[320.0, 400.0])]
        )
        pipeline = DetectionPipeline(
            detector=MockDetector(mock_detections=[]),
            segmentor=segmentor,
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-surface", "dev-1")
        assert isinstance(result, ReflexAlert)
        assert result.alert_id == "surface_stair"
        assert result.direction == "front"

    @pytest.mark.asyncio
    async def test_empty_inputs_return_none_risk(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=MockDetector(mock_detections=[]),
            segmentor=MockSegmentor(mock_surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-empty", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.detections == []
        assert result.surface == []
        assert result.risk_hint == "none"

    @pytest.mark.asyncio
    async def test_mid_risk_publishes_to_redis(self, frame, mock_redis_bus):
        detector = MockDetector(
            mock_detections=[
                Detection(
                    class_name="kickboard",
                    confidence=0.8,
                    bbox=BBox(x=10.0, y=10.0, w=20.0, h=20.0),
                )
            ]
        )
        pipeline = DetectionPipeline(
            detector=detector,
            segmentor=MockSegmentor(mock_surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-mid", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "mid"
        mock_redis_bus.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_tracker_exception_still_returns_result(self, frame, mock_redis_bus):
        mock_redis_bus.get_track_context = AsyncMock(side_effect=RuntimeError("redis down"))
        detector = MockDetector(
            mock_detections=[
                Detection(
                    class_name="kickboard",
                    confidence=0.8,
                    bbox=BBox(x=10.0, y=10.0, w=20.0, h=20.0),
                    track_id="T-0001",
                )
            ]
        )
        pipeline = DetectionPipeline(
            detector=detector,
            segmentor=MockSegmentor(mock_surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-track-fail", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "mid"


class TestYoloDetectorLoad:
    def test_unloadable_weights_returns_false(self):
        det = YoloDetector(weights_path="server/models/yolo26n/not_exist.pt")
        assert det.load() is False
        assert det.model is None
