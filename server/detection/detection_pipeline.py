import asyncio
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

# =========================================================================
# 👨‍💻 HARD CODE 영역 시작: cognitive 경로로 넘길 mid risk 클래스 확정 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 왜 모든 탐지 객체를 reflex(즉시 경보)로 보내지 않았나요?
# 답변: 시각장애인 보행 보조에서 가장 위험한 것은 "경보 과다"로 인한 피로 누적입니다.
# 따라서 즉시 충돌 가능성이 큰 5종(car/truck/bus/motorcycle/scooter)만 reflex로 고정하고,
# 나머지 정적 장애물/보행 방해물은 mid risk로 분류해 cognitive 경로에서 방향성과 회피
# 문장을 포함한 상세 안내로 처리하도록 설계했습니다.
#
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

# =========================================================================
# 👨‍💻 HARD CODE 영역 시작: segmentation 기반 mid risk 노면 기준 👨‍💻
# 💡 [면접 대비 주석]
# 질문: segmentation 결과는 왜 `caution`, `roadway`만 mid로 봤나요?
# 답변: 현재 실제 4클래스 segmentation 모델에서 보행 판단에 직접 영향을 주는 노면 위험은
# caution(계단/맨홀/그레이팅 통합)과 roadway(차도) 두 가지입니다.
# sidewalk_normal / braille_normal은 상태 정보로는 의미가 있지만 즉시 회피 문장을 만들
# 필요가 적기 때문에 mid 경로에 올리지 않고 low 쪽으로 남겨두었습니다.
# 노면은 현재 실제 segmentation 4클래스 기준으로 본다.
# caution : 계단/맨홀/그레이팅 통합 위험 구간
# roadway : 차도 침범 / 이탈 위험
MID_RISK_SURFACE_CLASSES = {"caution", "roadway"}
# =========================================================================


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
    ) -> tuple[DetectionResult | ReflexAlert, list[Detection], list[SurfaceResult]]:
        start_ts = time.time()

        if frame is None:
            logger.warning(f"[Pipeline] 프레임 None: event_id={event_id}")
            res = DetectionResult(
                event_id=event_id,
                detections=[],
                surface=[],
                risk_hint="none",
                inference_ms=0.0,
            )
            return res, [], []

        height, width = frame.shape[:2]

        # to_thread로 워커 스레드에 위임: predict()는 동기 블로킹 호출이라 그대로 await하면
        # 추론 중(150~300ms) WS 수신 루프/하트비트/Redis 통신까지 이벤트 루프 전체가 멈춘다
        # (2026-07-10 실기기 테스트에서 반사 큐 드랍 + Redis xadd 타임아웃으로 실측 확인).
        try:
            detections = await asyncio.to_thread(self.detector.predict, frame)
        except Exception as e:
            logger.error(f"[Pipeline] Detector 추론 실패: {e}")
            detections = []

        try:
            surfaces = await asyncio.to_thread(self.segmentor.predict, frame)
        except Exception as e:
            logger.error(f"[Pipeline] Segmentor 추론 실패: {e}")
            surfaces = []

        detections = await self.tracker.update(detections, self.redis_bus)

        reflex_alert = self._evaluate_reflex(detections, height, width)
        if reflex_alert is not None:
            reflex_alert.event_id = event_id
            reflex_alert.ts = time.time()
            reflex_alert.inference_ms = (time.time() - start_ts) * 1000
            logger.info(f"[Pipeline] 반사 경로: {reflex_alert.alert_id}")
            return reflex_alert, detections, surfaces

        head_level_alert = self._evaluate_head_level(detections, height, width)
        if head_level_alert is not None:
            head_level_alert.event_id = event_id
            head_level_alert.ts = time.time()
            head_level_alert.inference_ms = (time.time() - start_ts) * 1000
            logger.info(f"[Pipeline] 반사 경로(머리 높이 격상): {head_level_alert.alert_id}")
            return head_level_alert, detections, surfaces

        surface_alert = self._evaluate_surface(surfaces, height)
        if surface_alert is not None:
            surface_alert.event_id = event_id
            surface_alert.ts = time.time()
            surface_alert.inference_ms = (time.time() - start_ts) * 1000
            logger.info(f"[Pipeline] 반사 경로: {surface_alert.alert_id}")
            return surface_alert, detections, surfaces

        risk_hint = self._classify_risk(detections, surfaces)
        inference_ms = (time.time() - start_ts) * 1000

        if risk_hint in ("mid", "low"):
            await self._publish_cognitive(event_id, detections, surfaces, risk_hint)

        res = DetectionResult(
            event_id=event_id,
            detections=detections,
            surface=surfaces,
            risk_hint=risk_hint,
            inference_ms=inference_ms,
        )
        return res, detections, surfaces

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
        # 💡 [면접 대비 주석]
        # 3단계 DetectionPipeline은 "최종 문장 생성"이 아니라 "반사와 인지의 경계 분리"까지만 맡는다.
        # high는 reflex/surface gate에서 이미 잘라냈고, 여기서는 남은 후보를 mid/low/none으로만
        # 정리해 후속 RAG/LangGraph로 넘긴다. 즉 3단계는 과판단을 피하고 경로 분리 책임에 집중한다.
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
        surfaces: list[SurfaceResult],
        risk_hint: str,
    ):
        for det in detections:
            try:
                await self.producer.publish_detection(event_id, det, risk_hint)
            except Exception as e:
                logger.warning(f"[Pipeline] cognitive 발행 실패: {e}")
        if detections:
            return
        for surf in surfaces:
            try:
                await self.producer.publish_surface(event_id, surf, risk_hint)
            except Exception as e:
                logger.warning(f"[Pipeline] surface cognitive 발행 실패: {e}")
