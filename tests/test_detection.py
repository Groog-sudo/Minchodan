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
        # class-agnostic: 중앙 + 면적>=10% + hit_count>=3
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=210.0, y=280.0, w=220.0, h=160.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is not None
        assert alert.alert_id == "high_obstacle"
        assert alert.class_name == "obstacle"
        assert alert.direction == "front"

    def test_reflex_gate_off_center_rejected(self):
        """중앙 존 밖이면 면적이 커도 반사 미발동 (측면은 인지/로컬 폴백 영역)."""
        det = Detection(
            class_name="truck",
            confidence=0.9,
            bbox=BBox(x=10.0, y=280.0, w=100.0, h=160.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_low_position(self):
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=0.0, y=0.0, w=10.0, h=10.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_any_class_near_center(self):
        """class-agnostic: bicycle 등도 지오메트리만 충족하면 obstacle 경보."""
        det = Detection(
            class_name="bicycle",
            confidence=0.9,
            bbox=BBox(x=210.0, y=280.0, w=220.0, h=160.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is not None
        assert alert.alert_id == "high_obstacle"

    def test_reflex_gate_low_confidence_rejected(self):
        """존재 confidence 0.35 미달 시 발동하지 않는다."""
        det = Detection(
            class_name="car",
            confidence=0.30,
            bbox=BBox(x=210.0, y=280.0, w=220.0, h=160.0),
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_insufficient_hit_count_rejected(self):
        """연속 프레임 수(hit_count)가 MIN_HIT_COUNT 미만이면 발동하지 않는다."""
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=210.0, y=280.0, w=220.0, h=160.0),
            hit_count=1,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_small_area_rejected(self):
        """면적 비율이 MIN_AREA_RATIO 미만이면 미발동."""
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=250.0, y=420.0, w=140.0, h=60.0),  # ~2.7% < 10%
            hit_count=3,
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

    def test_reflex_gate_small_bottom_near_emits(self):
        """P0-3: 발밑(화면 하단 80% 이하) 소형 객체(면적 4~10%)는 근접으로 발동."""
        # frame 480x640. area 5% 목표: w*h = 0.05*307200 = 15360. 160*96=15360. bottom=430+96=526>=384.
        det = Detection(
            class_name="bollard",
            confidence=0.9,
            bbox=BBox(x=270.0, y=430.0, w=160.0, h=96.0),  # ~5%, bottom=526
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is not None
        assert alert.distance_band in ("near", "medium")

    def test_reflex_gate_small_bottom_below_lower_bound_rejected(self):
        """P0-3: 발밑이어도 면적이 SMALL_OBJECT_MIN_AREA_RATIO(4%) 미만이면 미발동."""
        # area = 100*100/(480*640) = 0.0326 = 3.26% < 4%. bottom=380+100=480>=384.
        det = Detection(
            class_name="bollard",
            confidence=0.9,
            bbox=BBox(x=270.0, y=380.0, w=100.0, h=100.0),  # 3.26%, bottom=480
            hit_count=3,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is None

    def test_reflex_gate_reacquired_bypasses_min_hit_count(self):
        """P0-3: reacquired=True면 hit_count<MIN_HIT_COUNT여도 즉시 발동."""
        # 중앙 + 근접(면적 ~11.5%)이지만 hit_count=1. reacquired=True면 발동.
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=210.0, y=280.0, w=220.0, h=160.0),  # ~11.5%, centered
            hit_count=1,
            reacquired=True,
        )
        alert = reflex_gate(det, 480.0, 640.0)
        assert alert is not None


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

    @pytest.mark.asyncio
    async def test_reacquired_within_window(self, mock_redis_bus):
        """P0-3: 직전 hit_count>=3이고 1초 이내 재탐지 시 reacquired=True."""
        import time as _time

        tracker = ByteTrackTracker()
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=0, y=100, w=10, h=10),
            track_id="T-0001",
        )
        # 직전 hit_count=3, 0.5초 전 관측
        recent_ts = _time.time() - 0.5
        mock_redis_bus.get_track_context = AsyncMock(
            return_value={
                "hit_count": "3",
                "last_pos": '{"x":0,"y":100,"w":10,"h":10}',
                "updated_at": str(recent_ts),
            }
        )
        updated = await tracker.update([det], mock_redis_bus)
        assert updated[0].reacquired is True
        assert updated[0].hit_count == 4  # 정상 누적 유지

    @pytest.mark.asyncio
    async def test_not_reacquired_after_window(self, mock_redis_bus):
        """P0-3: 1초 초과 후 재탐지 시 reacquired=False (윈도우 밖)."""
        import time as _time

        tracker = ByteTrackTracker()
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=0, y=100, w=10, h=10),
            track_id="T-0001",
        )
        # 직전 hit_count=3, 2초 전 관측 (윈도우 1초 초과)
        old_ts = _time.time() - 2.0
        mock_redis_bus.get_track_context = AsyncMock(
            return_value={
                "hit_count": "3",
                "last_pos": '{"x":0,"y":100,"w":10,"h":10}',
                "updated_at": str(old_ts),
            }
        )
        updated = await tracker.update([det], mock_redis_bus)
        assert updated[0].reacquired is False

    @pytest.mark.asyncio
    async def test_not_reacquired_with_low_prev_hit(self, mock_redis_bus):
        """P0-3: 직전 hit_count<3이면 윈도우 내 재탐지여도 reacquired=False."""
        import time as _time

        tracker = ByteTrackTracker()
        det = Detection(
            class_name="car",
            confidence=0.9,
            bbox=BBox(x=0, y=100, w=10, h=10),
            track_id="T-0001",
        )
        recent_ts = _time.time() - 0.5
        mock_redis_bus.get_track_context = AsyncMock(
            return_value={
                "hit_count": "2",  # MIN(3) 미만
                "last_pos": '{"x":0,"y":100,"w":10,"h":10}',
                "updated_at": str(recent_ts),
            }
        )
        updated = await tracker.update([det], mock_redis_bus)
        assert updated[0].reacquired is False


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
        result, _, _ = await pipeline.run(None, "test", "evt-1", "dev-1")
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
        result, _, _ = await pipeline.run(frame, "test", "evt-2", "dev-1")
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
        result, _, _ = await pipeline.run(frame, "test", "evt-det-fail", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.detections == []
        assert len(result.surface) == 1
        assert result.risk_hint == "low"

    @pytest.mark.asyncio
    async def test_segmentor_exception_returns_detections_only(self, frame, mock_redis_bus):
        # 2026-07-17 MID_RISK Option A: bicycle는 인지 mid가 아닌 low로 분류된다
        # (MID_RISK_CLASSES 공집합 전환). segmentor 예외 시에도 분류 규칙은 동일.
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
        result, _, _ = await pipeline.run(frame, "test", "evt-seg-fail", "dev-1")
        assert isinstance(result, DetectionResult)
        assert len(result.detections) == 1
        assert result.surface == []
        assert result.risk_hint == "low"

    @pytest.mark.asyncio
    async def test_reflex_gate_triggers(self, frame, mock_redis_bus):
        # 파이프라인이 hit_count < 4 탐지를 필터하므로, 직전 컨텍스트 hit_count=3 → 이번 프레임 4.
        # reflex_gate 자체는 MIN_HIT_COUNT=3.
        mock_redis_bus.get_track_context = AsyncMock(return_value={"hit_count": "3"})
        detector = StubDetector(
            detections=[
                Detection(
                    class_name="car",
                    confidence=0.9,
                    bbox=BBox(x=210.0, y=280.0, w=220.0, h=160.0),
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
        result, _, _ = await pipeline.run(frame, "test", "evt-reflex", "dev-1")
        assert isinstance(result, ReflexAlert)
        assert result.alert_id == "high_obstacle"
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
        result, _, _ = await pipeline.run(frame, "test", "evt-surface", "dev-1")
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
        result, _, _ = await pipeline.run(frame, "test", "evt-roadway", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "mid"

    @pytest.mark.asyncio
    async def test_is_departing_true_by_default_when_polygon_covers_reference_point(
        self, frame, mock_redis_bus
    ):
        """is_outdoor 미전달(None, 구버전 클라이언트 등)이면 기존처럼 세그멘테이션 결과를
        그대로 신뢰해 이탈 판정이 나가야 한다(회귀 방지)."""
        # frame은 480x640(H x W) - 기준점(0.5, 0.9) => (320, 432)를 덮는 폴리곤.
        polygon = [[100.0, 300.0], [540.0, 300.0], [540.0, 480.0], [100.0, 480.0]]
        segmentor = StubSegmentor(
            surfaces=[SurfaceResult(class_name="roadway", centroid=[320.0, 400.0], polygon=polygon)]
        )
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=segmentor,
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result, _, _ = await pipeline.run(frame, "test", "evt-departing-default", "dev-1")
        assert result.is_departing is True

    @pytest.mark.asyncio
    async def test_is_departing_suppressed_when_client_reports_indoor(self, frame, mock_redis_bus):
        """2026-07-13 실기기 실측: 실내 바닥이 roadway/caution으로 오분류돼 이탈 판정이
        계속 발생하는 것을 확인. 클라이언트 온디바이스 씬 분류가 실내(is_outdoor=False)로
        확정한 경우 세그멘테이션 결과와 무관하게 이탈 판정을 걸지 않아야 한다."""
        polygon = [[100.0, 300.0], [540.0, 300.0], [540.0, 480.0], [100.0, 480.0]]
        segmentor = StubSegmentor(
            surfaces=[SurfaceResult(class_name="roadway", centroid=[320.0, 400.0], polygon=polygon)]
        )
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=segmentor,
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result, _, _ = await pipeline.run(
            frame, "test", "evt-departing-indoor", "dev-1", is_outdoor=False
        )
        assert result.is_departing is False

    @pytest.mark.asyncio
    async def test_cognitive_publish_suppressed_when_client_reports_indoor(
        self, frame, mock_redis_bus
    ):
        """2026-07-14 정책: 실내(is_outdoor=False)면 mid/low라도 risk.events(인지 TTS)를
        발행하지 않는다. 실외 전용 모델의 실내 오탐이 음성 안내로 새는 것을 막기 위함.
        2026-07-17 MID_RISK Option A: bicycle는 low로 분류되나, 발행 억제 정책은 동일."""
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
        result, _, _ = await pipeline.run(
            frame, "test", "evt-mid-indoor", "dev-1", is_outdoor=False
        )
        assert result.risk_hint == "low"
        mock_redis_bus.publish_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_inputs_return_none_risk(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=StubSegmentor(surfaces=[]),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result, _, _ = await pipeline.run(frame, "test", "evt-empty", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "none"

    @pytest.mark.asyncio
    async def test_mid_risk_publishes_to_redis(self, frame, mock_redis_bus):
        # 2026-07-17 MID_RISK Option A: 객체 클래스(bicycle)는 더 이상 mid가 아니므로,
        # mid risk 발행 검증은 노면 roadway 클래스로 유발한다(MID_RISK_SURFACE_CLASSES).
        # 테스트 의도("mid → Redis 발행")는 유지하되 분류 SSOT 변경을 반영.
        segmentor = StubSegmentor(
            surfaces=[SurfaceResult(class_name="roadway", centroid=[320.0, 120.0])]
        )
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=segmentor,
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result, _, _ = await pipeline.run(frame, "test", "evt-mid", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "mid"
        mock_redis_bus.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_surface_only_mid_risk_publishes_to_redis(self, frame, mock_redis_bus):
        pipeline = DetectionPipeline(
            detector=StubDetector(detections=[]),
            segmentor=StubSegmentor(
                surfaces=[SurfaceResult(class_name="roadway", centroid=[320.0, 120.0])]
            ),
            tracker=ByteTrackTracker(),
            producer=RiskEventProducer(bus=mock_redis_bus),
            redis_bus=mock_redis_bus,
        )
        result, _, _ = await pipeline.run(frame, "test", "evt-surface-mid", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "mid"
        mock_redis_bus.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_tracker_exception_still_returns_result(self, frame, mock_redis_bus):
        # 테스트 의도: tracker 예외 시에도 DetectionResult를 반환(파이프라인 영속성).
        # 2026-07-17 MID_RISK Option A: bollard의 track_id="T-0001"이나 hit_count 기본값이
        # 최소 유지 프레임(4) 미만이라 시간적 지속성 필터(detection_pipeline.py:150)에서
        # 제외되고, tracker 예외(redis down)로 hit_count가 증가하지 않아 detections가
        # 빈 리스트가 된다. 결과적으로 _classify_risk([], []) == "none"이 올바른 기대값.
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
        result, _, _ = await pipeline.run(frame, "test", "evt-track-fail", "dev-1")
        assert isinstance(result, DetectionResult)
        assert result.risk_hint == "none"


class TestYoloDetectorLoad:
    def test_unloadable_weights_returns_false(self):
        det = YoloDetector(weights_path="server/models/yolo26n/not_exist.pt")
        assert det.load() is False
        assert det.model is None


class TestReflexAlertSuppression:
    """2026-07-08: 중복 억제(Alert_suppressor)가 실제 반사 전송 경로(_send_reflex_alert)에
    연결됐는지 검증. 이전에는 suppressor 구현은 있었으나 consumer.py가 호출하지 않아
    60초 이내 동일 alert_id가 억제 없이 계속 전송되는 결함이 있었다.

    2026-07-17 P0-1: 재무장 정책으로 API가 should_emit_reflex/mark_reflex_sent로 변경.
    """

    @pytest.mark.asyncio
    async def test_suppressed_alert_is_not_sent(self, monkeypatch):
        import server.detection.consumer as consumer_module

        send_mock = AsyncMock(return_value=True)
        should_emit_mock = AsyncMock(return_value=False)
        mark_reflex_mock = AsyncMock()
        monkeypatch.setattr(consumer_module.manager, "send_json", send_mock)
        monkeypatch.setattr(
            consumer_module.Alert_suppressor, "should_emit_reflex", should_emit_mock
        )
        monkeypatch.setattr(consumer_module.Alert_suppressor, "mark_reflex_sent", mark_reflex_mock)

        consumer = consumer_module.DetectionConsumer()
        alert = ReflexAlert(
            event_id="evt-1",
            alert_id="high_front",
            direction="front",
            clip="reflex_clips/high_front.mp3",
            ts=0.0,
            track_id="t1",
            distance_band="medium",
        )
        await consumer._send_reflex_alert("device-1", alert)

        should_emit_mock.assert_awaited_once()
        # near 여부는 alert.distance<=0.6 기준. distance 기본 1.0 -> is_near=False
        assert should_emit_mock.call_args.kwargs["device_id"] == "device-1"
        assert should_emit_mock.call_args.kwargs["track_id"] == "t1"
        assert should_emit_mock.call_args.kwargs["distance_band"] == "medium"
        assert should_emit_mock.call_args.kwargs["is_near"] is False
        send_mock.assert_not_awaited()
        mark_reflex_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unsuppressed_alert_is_sent_and_marked(self, monkeypatch):
        import server.detection.consumer as consumer_module

        send_mock = AsyncMock()
        should_emit_mock = AsyncMock(return_value=True)
        mark_reflex_mock = AsyncMock()
        monkeypatch.setattr(consumer_module.manager, "send_json", send_mock)
        monkeypatch.setattr(
            consumer_module.Alert_suppressor, "should_emit_reflex", should_emit_mock
        )
        monkeypatch.setattr(consumer_module.Alert_suppressor, "mark_reflex_sent", mark_reflex_mock)

        consumer = consumer_module.DetectionConsumer()
        alert = ReflexAlert(
            event_id="evt-2",
            alert_id="high_front",
            direction="front",
            clip="reflex_clips/high_front.mp3",
            ts=0.0,
            track_id="t2",
            distance_band="medium",
        )
        await consumer._send_reflex_alert("device-1", alert)

        send_mock.assert_awaited_once()
        mark_reflex_mock.assert_awaited_once()
        assert mark_reflex_mock.call_args.kwargs["device_id"] == "device-1"
        assert mark_reflex_mock.call_args.kwargs["track_id"] == "t2"
        assert mark_reflex_mock.call_args.kwargs["distance_band"] == "medium"

    @pytest.mark.asyncio
    async def test_disconnected_alert_is_not_marked_as_sent(self, monkeypatch):
        import server.detection.consumer as consumer_module

        send_mock = AsyncMock(return_value=False)
        should_emit_mock = AsyncMock(return_value=True)
        mark_reflex_mock = AsyncMock()
        monkeypatch.setattr(consumer_module.manager, "send_json", send_mock)
        monkeypatch.setattr(
            consumer_module.Alert_suppressor, "should_emit_reflex", should_emit_mock
        )
        monkeypatch.setattr(consumer_module.Alert_suppressor, "mark_reflex_sent", mark_reflex_mock)

        consumer = consumer_module.DetectionConsumer()
        alert = ReflexAlert(
            event_id="evt-disconnected",
            alert_id="high_front",
            direction="front",
            clip="reflex_clips/high_front.mp3",
            ts=0.0,
            track_id="t3",
            distance_band="medium",
        )
        await consumer._send_reflex_alert("device-1", alert)

        send_mock.assert_awaited_once()
        mark_reflex_mock.assert_not_awaited()
