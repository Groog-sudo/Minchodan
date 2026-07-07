import sys
from unittest.mock import AsyncMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
    DetectorInterface,
    ReflexAlert,
    SegmentorInterface,
    YoloDetector,
)
from server.detection.gates import reflex_gate, surface_gate
from server.detection.schemas import SurfaceResult


class StubDetector(DetectorInterface):
    """테스트용 가벼운 Detector stub (실제 모델 로드 없이 결정론적 결과 반환)."""

    def __init__(self, detections: list[Detection] | None = None):
        self._detections = detections

    def load(self) -> bool:
        return True

    def predict(self, frame) -> list[Detection]:
        return list(self._detections) if self._detections is not None else []


class StubSegmentor(SegmentorInterface):
    """테스트용 가벼운 Segmentor stub."""

    def __init__(self, surfaces: list[SurfaceResult] | None = None):
        self._surfaces = surfaces

    def load(self) -> bool:
        return True

    def predict(self, frame) -> list[SurfaceResult]:
        return list(self._surfaces) if self._surfaces is not None else []


class FailingDetector(StubDetector):
    def predict(self, frame):
        raise RuntimeError("detector failure")


class FailingSegmentor(StubSegmentor):
    def predict(self, frame):
        raise RuntimeError("segmentor failure")


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
            class_name="bicycle",
            confidence=0.9,
            bbox=BBox(x=0.0, y=0.0, w=10.0, h=10.0),
        )
        assert d.class_name == "bicycle"
        assert d.track_id is None


class TestGates:
    def test_reflex_gate_high_risk_bottom(self):
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is not None
        assert alert.alert_id == "high_car_front"
        assert alert.direction == "front"

    def test_reflex_gate_left_direction(self):
        det = Detection(
            class_name="truck",
            confidence=0.9,
            bbox=BBox(x=10.0, y=420.0, w=50.0, h=60.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is not None
        assert alert.direction == "front-left"
        assert alert.alert_id == "high_truck_front-left"

    def test_reflex_gate_low_position(self):
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=0.0, y=0.0, w=10.0, h=10.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_low_risk_class(self):
        det = Detection(
            class_name="bicycle",
            confidence=0.9,
            bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_low_confidence_rejected(self):
        """실내 오탐 완화: 클래스별 최소 confidence 미달 시 발동하지 않는다."""
        det = Detection(
            class_name="car",
            confidence=0.4,  # HIGH_RISK_CLASSES["car"] = 0.6 미달
            bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_insufficient_hit_count_rejected(self):
        """실내 오탐 완화: 연속 프레임 수(hit_count)가 MIN_HIT_COUNT 미만이면 발동하지 않는다."""
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
            hit_count=1,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_surface_gate_p0(self):
        """실제 4클래스 Segmentation 모델 기준 (2026-07-07 정정, caution=stairs/manhole/grating 통합 클래스)."""
        surf = SurfaceResult(class_name="caution", centroid=[320.0, 400.0])
        alert = surface_gate(surf, 480.0)
        assert alert is not None
        assert alert.alert_id == "surface_caution"

    def test_surface_gate_non_p0_class_returns_none(self):
        surf = SurfaceResult(class_name="sidewalk_normal", centroid=[320.0, 400.0])
        alert = surface_gate(surf, 480.0)
        assert alert is None

    def test_surface_gate_top_position_returns_none(self):
        surf = SurfaceResult(class_name="caution", centroid=[320.0, 100.0])
        alert = surface_gate(surf, 480.0)
        assert alert is None


class TestByteTrackTracker:
    @pytest.mark.asyncio
    async def test_update_without_track_id(self, mock_redis_bus):
        tracker = ByteTrackTracker()
        dets = [
            Detection(
                class_name="bicycle",
                confidence=0.8,
                bbox=BBox(x=0, y=0, w=10, h=10),
            )
        ]
        updated = await tracker.update(dets, mock_redis_bus)
        assert updated[0].track_id is None
        assert updated[0].speed == 0.0

    @pytest.mark.asyncio
    async def test_update_with_track_id(self, mock_redis_bus):
        tracker = ByteTrackTracker()
        dets = [
            Detection(
                class_name="bicycle",
                confidence=0.8,
                bbox=BBox(x=0, y=100, w=10, h=10),
                track_id="T-0001",
            )
        ]
        updated = await tracker.update(dets, mock_redis_bus)
        assert updated[0].track_id == "T-0001"
        mock_redis_bus.set_track_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_track_hit_count_starts_at_one(self, mock_redis_bus):
        """2026-07-07 추가: 신규 track(이전 컨텍스트 없음)은 hit_count=1로 시작한다."""
        tracker = ByteTrackTracker()
        dets = [
            Detection(
                class_name="car",
                confidence=0.9,
                bbox=BBox(x=0, y=100, w=10, h=10),
                track_id="T-0001",
            )
        ]
        updated = await tracker.update(dets, mock_redis_bus)
        assert updated[0].hit_count == 1

    @pytest.mark.asyncio
    async def test_hit_count_increments_across_consecutive_frames(self, mock_redis_bus):
        """2026-07-07 추가: 동일 track_id가 연속 프레임에 걸쳐 갱신되면 hit_count가 누적된다
        (실내 오탐 완화용 reflex_gate MIN_HIT_COUNT 조건의 근간)."""
        tracker = ByteTrackTracker()
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=0, y=100, w=10, h=10),
            track_id="T-0001",
        )

        # 1프레임째: 컨텍스트 없음 -> hit_count=1
        mock_redis_bus.get_track_context = AsyncMock(return_value={})
        updated = await tracker.update([det], mock_redis_bus)
        assert updated[0].hit_count == 1

        # 2프레임째: 직전 컨텍스트에 hit_count=1이 있었다고 가정 -> hit_count=2
        mock_redis_bus.get_track_context = AsyncMock(
            return_value={"hit_count": "1", "last_pos": '{"x":0,"y":100,"w":10,"h":10}'}
        )
        updated = await tracker.update([det], mock_redis_bus)
        assert updated[0].hit_count == 2

        # 3프레임째: 직전 컨텍스트에 hit_count=2 -> hit_count=3 (MIN_HIT_COUNT 도달)
        mock_redis_bus.get_track_context = AsyncMock(
            return_value={"hit_count": "2", "last_pos": '{"x":0,"y":100,"w":10,"h":10}'}
        )
        updated = await tracker.update([det], mock_redis_bus)
        assert updated[0].hit_count == 3


class TestPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_none_frame(self, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=StubDetector(),
            segmentor=StubSegmentor(),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(None, "test", "evt-1", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "none"

    @pytest.mark.asyncio
    async def test_pipeline_empty_inputs(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=StubSegmentor(surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-2", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "none"
        assert result.inference_ms >= 0


class TestPipelineRobustness:
    @pytest.mark.asyncio
    async def test_detector_exception_continues_with_segmentor(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=FailingDetector(),
            segmentor=StubSegmentor(
                surfaces=[SurfaceResult(class_name="person", centroid=[320.0, 400.0])]
            ),
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
        detector = StubDetector(
            detections=[
                Detection(
                    class_name="bicycle",
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
        # 2026-07-07: 실내 오탐 완화를 위해 MIN_HIT_COUNT(3) 조건이 추가됨에 따라,
        # track_id를 부여하고 직전 컨텍스트에 hit_count=2가 있었던 것으로 모킹하여
        # 이번 프레임에서 hit_count=3(조건 충족)이 되도록 구성한다.
        mock_redis_bus.get_track_context = AsyncMock(return_value={"hit_count": "2"})
        detector = StubDetector(
            detections=[
                Detection(
                    class_name="car",
                    confidence=0.9,
                    bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),
                    track_id="T-0001",
                )
            ]
        )
        pipeline = DetectionPipeline(
            detector=detector,
            segmentor=StubSegmentor(surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-reflex", "dev-1")
        assert isinstance(result, ReflexAlert)
        assert result.alert_id == "high_car_front"
        assert result.direction == "front"

    @pytest.mark.asyncio
    async def test_surface_gate_triggers(self, frame, mock_redis_bus):
        segmentor = StubSegmentor(
            surfaces=[SurfaceResult(class_name="caution", centroid=[320.0, 400.0])]
        )
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=segmentor,
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-surface", "dev-1")
        assert isinstance(result, ReflexAlert)
        assert result.alert_id == "surface_caution"
        assert result.direction == "front"

    @pytest.mark.asyncio
    async def test_surface_only_roadway_classifies_mid(self, frame, mock_redis_bus):
        """2026-07-07 회귀 테스트: 노면 클래스(roadway)만 있어도 mid로 분류되어야 한다
        (surface_gate의 P0 임계치에는 못 미치는 낮은 위치의 caution/roadway도 인지 경로에서
        완전히 무시되지 않도록 _classify_risk가 surfaces를 함께 고려하는지 검증)."""
        segmentor = StubSegmentor(
            surfaces=[SurfaceResult(class_name="roadway", centroid=[320.0, 100.0])]
        )
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=segmentor,
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-roadway", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "mid"

    @pytest.mark.asyncio
    async def test_empty_inputs_return_none_risk(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=StubSegmentor(surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result = await pipeline.run(frame, "test", "evt-empty", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "none"

    @pytest.mark.asyncio
    async def test_mid_risk_publishes_to_redis(self, frame, mock_redis_bus):
        detector = StubDetector(
            detections=[
                Detection(
                    class_name="bicycle",
                    confidence=0.8,
                    bbox=BBox(x=10.0, y=10.0, w=20.0, h=20.0),
                )
            ]
        )
        pipeline = DetectionPipeline(
            detector=detector,
            segmentor=StubSegmentor(surfaces=[]),
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
        detector = StubDetector(
            detections=[
                Detection(
                    class_name="bollard",
                    confidence=0.8,
                    bbox=BBox(x=10.0, y=10.0, w=20.0, h=20.0),
                    track_id="T-0001",
                )
            ]
        )
        pipeline = DetectionPipeline(
            detector=detector,
            segmentor=StubSegmentor(surfaces=[]),
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
