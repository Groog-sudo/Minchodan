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
from server.detection.gates.head_level_gate import head_level_gate
from server.detection.gates.reflex_gate import reflex_gate
from server.detection.gates.surface_gate import surface_gate
from server.detection.schemas import Detection, DetectionResult, ReflexAlert, SurfaceResult

logger = logging.getLogger(__name__)

RISK_LEVELS = {"high", "mid", "low"}

# 2026-07-07 정정: 이전 목록은 COCO 80클래스 잔재(skateboard/backpack/handbag/suitcase/
# umbrella/"fire hydrant" 등)였고 실제 파인튜닝 완료 29클래스 모델과 대부분 일치하지 않았다.
# 반사 게이트가 이미 처리하는 5종(car/truck/bus/motorcycle/scooter)과 정보성/비장애물
# 클래스(person/cat/dog/traffic_light/traffic_sign/stop)를 제외한 정적 장애물 전부를 채택했다.
# server/orchestration/nodes/l1_classifier.py의 MID_RISK_CLASSES와 동일하게 유지할 것
# (두 분류기가 서로 다른 목록으로 어긋났던 것이 이번에 고친 버그였다. tests/test_langgraph.py의
# 일관성 회귀 테스트 참조).
MID_RISK_CLASSES = {
    "barricade",
    "bench",
    "bicycle",
    "bollard",
    "carrier",
    "chair",
    "fire_hydrant",
    "kiosk",
    "movable_signage",
    "parking_meter",
    "pole",
    "potted_plant",
    "power_controller",
    "stroller",
    "table",
    "traffic_light_controller",
    "tree_trunk",
    "wheelchair",
}
MID_RISK_SURFACE_CLASSES = {"caution", "roadway"}


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

        head_level_alert = self._evaluate_head_level(detections, height, width)
        if head_level_alert is not None:
            head_level_alert.event_id = event_id
            head_level_alert.ts = time.time()
            logger.info(f"[Pipeline] 반사 경로(머리 높이 격상): {head_level_alert.alert_id}")
            return head_level_alert

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
    def _evaluate_head_level(
        detections: list[Detection],
        frame_height: float,
        frame_width: float,
    ) -> ReflexAlert | None:
        """중위험(mid) 클래스가 화면 상단 40%(머리 높이)에 있으면 고위험으로 격상한다.

        docs/design/behavior_and_risk_insight.md 제안 반영(2026-07-09 구현):
        발밑 근접만 보는 reflex_gate와 달리, 흰지팡이로 감지 불가능한 상체 높이
        돌출 장애물(나뭇가지, 개방된 적재함 등)을 조기에 반사 경로로 격상한다.
        """
        escalation_classes = frozenset(MID_RISK_CLASSES)
        for det in detections:
            alert = head_level_gate(det, frame_height, frame_width, escalation_classes)
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
        """탐지/분할 결과를 mid/low로 1차 분류한다 (high는 이미 반사 게이트가 처리 완료).

        MID_RISK_CLASSES/MID_RISK_SURFACE_CLASSES(모듈 상수) 기준. 2026-07-07 정정 이력은
        해당 상수 정의부 주석 참조.
        """
        if not detections and not surfaces:
            return "none"

        for det in detections:
            if det.class_name in MID_RISK_CLASSES:
                return "mid"
        for surf in surfaces:
            if surf.class_name in MID_RISK_SURFACE_CLASSES:
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
