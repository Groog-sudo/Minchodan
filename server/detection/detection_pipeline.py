import logging
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

from server.bus.producer import RiskEventProducer
from server.bus.redis_client import RedisBus
from server.detection.bytetrack_tracker import ByteTrackTracker
from server.detection.detector_interface import DetectorInterface, SegmentorInterface
from server.detection.gates.reflex_gate import reflex_gate
from server.detection.gates.surface_gate import surface_gate
from server.detection.schemas import Detection, DetectionResult, ReflexAlert, SurfaceResult

logger = logging.getLogger(__name__)

RISK_LEVELS = {"high", "mid", "low"}


class DetectionPipeline:
    """3단계 전체 파이프라인: 탐지 → 분할 → 추적 → 게이트 분기."""

    def __init__(
        self,
        detector: DetectorInterface,
        segmentor: SegmentorInterface,
        tracker: ByteTrackTracker,
        producer: RiskEventProducer,
        redis_bus: RedisBus,
    ):
        self.detector = detector
        self.segmentor = segmentor
        self.tracker = tracker
        self.producer = producer
        self.redis_bus = redis_bus

    async def run(
        self,
        frame: np.ndarray | None,
        stream: str,
        event_id: str,
        device_id: str,
    ) -> DetectionResult | ReflexAlert:
        start_ts = time.time()

        if frame is None:
            logger.warning(f"[Pipeline] 프레임 None: event_id={event_id}")
            return DetectionResult(
                event_id=event_id,
                detections=[],
                surface=[],
                risk_hint="none",
                inference_ms=0.0,
            )

        height, width = frame.shape[:2]

        try:
            detections = self.detector.predict(frame)
        except Exception as e:
            logger.error(f"[Pipeline] Detector 추론 실패: {e}")
            detections = []

        try:
            surfaces = self.segmentor.predict(frame)
        except Exception as e:
            logger.error(f"[Pipeline] Segmentor 추론 실패: {e}")
            surfaces = []

        detections = await self.tracker.update(detections, self.redis_bus)

        reflex_alert = self._evaluate_reflex(detections, height, width)
        if reflex_alert is not None:
            reflex_alert.event_id = event_id
            reflex_alert.ts = time.time()
            logger.info(f"[Pipeline] 반사 경로: {reflex_alert.alert_id}")
            return reflex_alert

        surface_alert = self._evaluate_surface(surfaces, height)
        if surface_alert is not None:
            surface_alert.event_id = event_id
            surface_alert.ts = time.time()
            logger.info(f"[Pipeline] 반사 경로: {surface_alert.alert_id}")
            return surface_alert

        risk_hint = self._classify_risk(detections, surfaces)
        inference_ms = (time.time() - start_ts) * 1000

        if risk_hint in ("mid", "low"):
            await self._publish_cognitive(event_id, detections, risk_hint)

        return DetectionResult(
            event_id=event_id,
            detections=detections,
            surface=surfaces,
            risk_hint=risk_hint,
            inference_ms=inference_ms,
        )

    @staticmethod
    def _evaluate_reflex(
        detections: list[Detection],
        frame_height: float,
        frame_width: float,
    ) -> ReflexAlert | None:
        for det in detections:
            alert = reflex_gate(det, frame_height, frame_width)
            if alert is not None:
                return alert
        return None

    @staticmethod
    def _evaluate_surface(
        surfaces: list[SurfaceResult],
        frame_height: float,
    ) -> ReflexAlert | None:
        for surf in surfaces:
            alert = surface_gate(surf, frame_height)
            if alert is not None:
                return alert
        return None

    @staticmethod
    def _classify_risk(detections: list[Detection], surfaces: list[SurfaceResult]) -> str:
        if not detections and not surfaces:
            return "none"
        mid_risk_classes = {
            "bicycle",
            "skateboard",
            "bench",
            "fire hydrant",
            "stop sign",
            "parking meter",
            "backpack",
            "handbag",
            "suitcase",
            "umbrella",
            "person",
        }
        for det in detections:
            if det.class_name in mid_risk_classes:
                return "mid"
        return "low"

    async def _publish_cognitive(
        self,
        event_id: str,
        detections: list[Detection],
        risk_hint: str,
    ):
        for det in detections:
            try:
                await self.producer.publish_detection(event_id, det, risk_hint)
            except Exception as e:
                logger.warning(f"[Pipeline] cognitive 발행 실패: {e}")
