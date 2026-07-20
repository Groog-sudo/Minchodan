import asyncio
import logging
import sys
import time
from typing import ClassVar

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

from server.bus.producer import RiskEventProducer
from server.bus.redis_client import RedisBus
from server.detection.bytetrack_tracker import ByteTrackTracker
from server.detection.detector_interface import DetectorInterface, SegmentorInterface
from server.detection.direction import is_speech_front
from server.detection.gates.head_level_gate import head_level_gate
from server.detection.gates.reflex_gate import reflex_gate
from server.detection.gates.surface_gate import surface_gate
from server.detection.path_risk import classify_path_risk, compute_path_risk_ratio
from server.detection.schemas import Detection, DetectionResult, ReflexAlert, SurfaceResult
from server.detection.surface_departure import (
    braille_follow_direction,
    check_sidewalk_departure,
    point_in_polygon,
)

logger = logging.getLogger(__name__)

RISK_LEVELS = {"high", "mid", "low"}

# =========================================================================
# 👨‍💻 HARD CODE 영역 시작: 인지 경로 mid risk 객체·노면·머리높이 격상 분리 👨‍💻
# 💡 [면접 대비 주석]
# 질문: 2026-07-14 이후 객체 mid 목록은 왜 비었나요?
# 답변: stage3 v0.3.1·class-agnostic reflex(Option A) 채택 후, 근접 객체는 reflex_gate/
# head_level_gate가 반사 경로를 담당하고 consumer의 800ms 지연 인지·패스트 레인이 설명을 맡습니다.
# LangGraph L1의 인지 mid는 노면 이탈(is_departing_confirmed) 전용이므로 객체 클래스는 mid로
# 올리지 않습니다. server/orchestration/nodes/l1_classifier.py의 MID_RISK_CLASSES와
# 동일하게 유지할 것(tests/test_langgraph.py::TestRiskClassifierConsistency 참조).
#
# HEAD_LEVEL_ESCALATION_CLASSES는 인지 mid와 별도입니다. 상체 높이(화면 상단 40%) 돌출물은
# LLM 지연 전에 head_level_gate가 반사 경로로 격상해야 하므로 18종 정적 장애물 목록을 유지합니다.
MID_RISK_CLASSES: set[str] = set()

HEAD_LEVEL_ESCALATION_CLASSES = {
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
        is_outdoor: bool | None = None,
        probe_source: str | None = None,
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

        detections = await self.tracker.update(
            detections, self.redis_bus, frame_width=width, frame_height=height
        )

        # 1. 진단 및 2. 완화 조치 (교차검증 게이트 + 시간적 지속성)
        filtered_detections = []
        hallucination_count = 0
        total_detections = len(detections)

        # 1회성 진단 로깅을 위한 멤버 변수 설정
        if not hasattr(self, "_has_logged_diagnostic"):
            self._has_logged_diagnostic = False
            self._hallucination_total = 0
            self._detections_total = 0

        for det in detections:
            # 시간적 지속성 강화 (최소 4프레임 이상 유지된 경우만 승격, Mock/테스트 등은 예외)
            # T1-a (2026-07-18): 접근 중인 객체는 hit_count 선필터를 완화해 빠른 안내가
            # 가능하도록 한다. 정적 객체는 4프레임, 접근 객체는 2프레임을 요구한다.
            # [면접 대비 주석] 먼 객체는 누적으로 안전 확보, 근접 신규 객체는 접근성으로
            # 조기 통과하는 비대칭 설계. 정적 오탐은 여전히 4프레임으로 필터링 유지.
            # 2026-07-19: "거리측정" 모드의 단발 검증 캡처(probe_source="lidar_validation")는
            # 연속 스트림이 아니라 사용자가 명시적으로 트리거한 1회성 정지 프레임이므로,
            # 연속 프레임 누적을 전제로 하는 이 필터를 적용할 수 없다(항상 hit_count=1로
            # 걸러져 탐지 0건이 되는 결함이었음). 검증 캡처는 이 필터를 건너뛴다.
            if det.track_id is not None and probe_source != "lidar_validation":
                min_hit_count = 2 if det.direction == "approaching" else 4
                if det.hit_count < min_hit_count:
                    continue

            # 세그멘테이션이 없으면 교차검증을 건너뛴다(seg 실패 시 반사까지 전량 드롭 방지).
            if surfaces:
                sample_points = []
                for rx in [0.25, 0.5, 0.75]:
                    for ry in [0.25, 0.5, 0.75]:
                        px = det.bbox.x + det.bbox.w * rx
                        py = det.bbox.y + det.bbox.h * ry
                        sample_points.append((px, py))

                hits = 0
                for point in sample_points:
                    for surf in surfaces:
                        if not surf.polygon:
                            continue
                        if point_in_polygon(point, surf.polygon):
                            hits += 1
                            break
                overlap = hits / len(sample_points)

                # Detection-Segmentation 교차검증 (겹침 비율 30% 미만 무시)
                if overlap < 0.30:
                    hallucination_count += 1
                    continue

            filtered_detections.append(det)

        if total_detections > 0 and not self._has_logged_diagnostic:
            self._hallucination_total += hallucination_count
            self._detections_total += total_detections
            if self._detections_total >= 30:
                ratio = self._hallucination_total / self._detections_total
                logger.info(
                    f"[OOD DIAGNOSTIC] 겹치지 않는 탐지 (허공/환각 탐지) 비율: {ratio * 100:.1f}%"
                )
                self._has_logged_diagnostic = True

        detections = filtered_detections

        # 2026-07-18 거리 정책 SSOT: stream 불변식 강제.
        # [면접 대비 주석] stream 인자를 받고도 실제 분기에 쓰지 않던 것이 기존 결함이었다
        # (반사 프레임에서도 인지 후보가 만들어지고, 인지 프레임에서도 반사 경보가 나올 수
        # 있었음). 반사(8~10fps)는 안전 게이트(Near 반사·머리높이·노면)만 평가하고,
        # 인지(1~2fps)는 mid/low 분류와 보도 이탈만 평가해 서로의 출력 종류를 침범하지 않는다.
        if stream == "reflex":
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

            surface_alert = self._evaluate_surface(surfaces, height, width)
            if surface_alert is not None:
                surface_alert.event_id = event_id
                surface_alert.ts = time.time()
                surface_alert.inference_ms = (time.time() - start_ts) * 1000
                logger.info(f"[Pipeline] 반사 경로: {surface_alert.alert_id}")
                return surface_alert, detections, surfaces

            # 반사 스트림에서 안전 게이트가 하나도 발동하지 않으면 인지 후보를 만들지
            # 않고(risk_hint="none") BBox 오버레이용 원시 탐지 정보만 반환한다.
            res = DetectionResult(
                event_id=event_id,
                detections=detections,
                surface=surfaces,
                risk_hint="none",
                inference_ms=(time.time() - start_ts) * 1000,
            )
            return res, detections, surfaces

        risk_hint = self._classify_risk(detections, surfaces)
        inference_ms = (time.time() - start_ts) * 1000

        # is_outdoor=False(클라이언트 온디바이스 씬 분류가 실내로 확정)면 세그멘테이션
        # 결과와 무관하게 이탈 판정을 걸지 않는다. 실내 바닥이 roadway/caution으로
        # 오분류되는 도메인쉬프트(2026-07-13 실기기 실측으로 확인)를 게이팅하기 위함.
        # None(클라이언트 미판정, 구버전 등)은 기존처럼 세그멘테이션 결과를 신뢰한다.
        is_departing = (
            check_sidewalk_departure(surfaces, width, height) if is_outdoor is not False else False
        )
        braille_direction = braille_follow_direction(surfaces, width, height)
        if is_departing:
            logger.info(
                f"[Pipeline] 보도 이탈 판정(단일 프레임): event_id={event_id}, "
                f"braille_direction={braille_direction}"
            )

        # 2026-07-13 실험: 강사님 추천(Depth Map + 주행 ROI + 위험 픽셀 비율) 알고리즘의
        # 저비용 근사. 아직 risk_hint/안내문에는 연결하지 않고 관측(로그)만 한다 -
        # is_outdoor=False일 때는 이탈 판정과 동일한 이유로 계산 자체를 건너뛴다.
        if is_outdoor is not False:
            path_risk_ratio = compute_path_risk_ratio(surfaces, width, height)
            if path_risk_ratio > 0:
                logger.info(
                    f"[Pipeline] 주행통로 위험 비율(실험): event_id={event_id}, "
                    f"ratio={path_risk_ratio:.2f}, level={classify_path_risk(path_risk_ratio)}"
                )

        # 2026-07-14 정책: 클라이언트가 실내(is_outdoor=False)로 확정하면 인지 경로
        # (Redis risk.events → LLM → TTS)도 발행하지 않는다. 실외 전용 det/seg 모델의
        # 실내 오탐이 TTS로 새는 것을 막기 위함. None(구버전/미판정)은 기존처럼 발행.
        if risk_hint in ("mid", "low") and is_outdoor is not False:
            await self._publish_cognitive(event_id, detections, surfaces, risk_hint)

        res = DetectionResult(
            event_id=event_id,
            detections=detections,
            surface=surfaces,
            risk_hint=risk_hint,
            inference_ms=inference_ms,
            is_departing=is_departing,
            braille_direction=braille_direction,
        )
        return res, detections, surfaces

    _REFLEX_BAND_PRIORITY: ClassVar[dict[str, int]] = {"near": 0, "medium": 1, "far": 2}

    @classmethod
    def _evaluate_reflex(
        cls,
        detections: list[Detection],
        frame_height: float,
        frame_width: float,
    ) -> ReflexAlert | None:
        """프레임 내 모든 탐지를 게이트 통과 여부와 무관하게 전부 평가한 뒤,
        통과한 후보 중 가장 위험한 1건만 반사 알림으로 반환한다.

        2026-07-20: 기존에는 detections 리스트 순서상 첫 통과 항목을 즉시 반환했다.
        YOLO 출력 순서는 confidence/거리 정렬을 보장하지 않으므로, 여러 객체가 동시에
        잡히는 프레임(자동차+사람+트럭 등)에서 진짜 근접 위험 객체가 리스트 뒤쪽에
        있으면 앞쪽 객체의 게이트 통과 여부와 무관하게 스킵될 수 있었다(프레임당 1건
        상한 자체는 유지하되, 그 1건을 뽑는 기준을 리스트 순서에서 거리/밴드 우선순위로
        교체 - reflex_gate가 반환하는 모든 후보를 먼저 모은다).
        """
        candidates = [
            alert
            for det in detections
            if (alert := reflex_gate(det, frame_height, frame_width)) is not None
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda a: (
                cls._REFLEX_BAND_PRIORITY.get(a.distance_band, 2),
                a.distance,
            ),
        )

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

        2026-07-20: far head_level 스팸이 Near 비프 UX를 잠식하는 DB 실측을 반영해
        near/medium 모두 안내용 12시 회랑(is_speech_front)만 허용한다(far는 화면/인지만).
        """
        escalation_classes = frozenset(HEAD_LEVEL_ESCALATION_CLASSES)
        for det in detections:
            zone = getattr(det, "effective_distance_zone", "") or ""
            if zone == "far":
                continue
            if zone in ("near", "medium"):
                if not is_speech_front(det.bbox, frame_width, zone):
                    continue
            elif getattr(det, "route", "") != "reflex":
                # zone 미부착: route=reflex(near) + speech_front만 허용
                continue
            else:
                if not is_speech_front(det.bbox, frame_width, "near"):
                    continue
            alert = head_level_gate(det, frame_height, frame_width, escalation_classes)
            if alert is not None:
                return alert
        return None

    @staticmethod
    def _evaluate_surface(
        surfaces: list[SurfaceResult],
        frame_height: float,
        frame_width: float = 0.0,
    ) -> ReflexAlert | None:
        for surf in surfaces:
            alert = surface_gate(surf, frame_height, frame_width)
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
        # best_20260705.pt 객체 탐지가 있더라도 best.pt 노면 분할 결과가 생략되지 않고
        # Redis Streams를 통해 오케스트레이션 단계로 온전히 전달되도록 if detections: return 가드레일을 제거합니다.
        for surf in surfaces:
            try:
                await self.producer.publish_surface(event_id, surf, risk_hint)
            except Exception as e:
                logger.warning(f"[Pipeline] surface cognitive 발행 실패: {e}")
