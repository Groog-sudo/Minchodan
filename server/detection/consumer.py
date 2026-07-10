"""
3단계 DetectionConsumer.
StreamSplitter의 asyncio.Queue에서 ProcessedFrame을 소비하고
DetectionPipeline을 실행한 뒤, 반사 알림은 WebSocket 고우선 채널로,
인지 이벤트는 Redis Streams로 전송한다 (이중 경로 물리 분리 준수).
"""

import asyncio
import contextlib
import logging
import sys
import time

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

from server.api.schemas import now_ts
from server.api.session_manager import manager
from server.bus.producer import RiskEventProducer
from server.bus.redis_client import redis_bus
from server.capture.stream_splitter import StreamSplitter, get_default_splitter
from server.detection.bytetrack_tracker import ByteTrackTracker
from server.detection.config import get_detector, get_segmentor
from server.detection.detection_pipeline import DetectionPipeline
from server.detection.schemas import DetectionResult, ReflexAlert
from server.orchestration import run_orchestrator
from server.rag.retriever import get_default_retriever
from server.tts.realtime_tts import realtime_tts
from server.tts.suppressor import Alert_suppressor

logger = logging.getLogger(__name__)


class DetectionConsumer:
    """이중 큐(반사/인지)에서 프레임을 소비하고 DetectionPipeline을 실행.

    비협상 원칙:
        반사 알림(ReflexAlert)은 WebSocket 고우선 채널로 즉시 전송.
        인지 결과(DetectionResult mid/low)는 pipeline 내부에서 Redis로 발행.
    """

    def __init__(
        self,
        splitter: StreamSplitter | None = None,
        pipeline: DetectionPipeline | None = None,
    ):
        self.splitter = splitter or get_default_splitter()
        self._pipeline: DetectionPipeline | None = pipeline
        self._reflex_task: asyncio.Task | None = None
        self._cognitive_task: asyncio.Task | None = None
        self._running = False
        # device_id별 마지막 인지 가이드 전송 시각(초)과 그 오디오 재생 길이(초).
        # 이전 안내 음성이 끝나기 전에 다음 안내가 겹쳐 재생을 끊는 문제를 막기 위한
        # 간격 쿨다운. 고정값 하나로는 문장 길이에 따라 달라지는 실제 WAV 재생 시간을
        # 반영하지 못해(짧은 문장엔 과잉 대기, 긴 문장엔 재생 중 짤림) 직전 오디오의
        # 실측 길이 기반으로 동적 산정한다(비협상 아님, 튜닝값).
        self._last_guide_ts: dict[str, float] = {}
        self._last_guide_duration_sec: dict[str, float] = {}
        self._min_guide_cooldown_sec: float = 8.0
        self._guide_cooldown_margin_sec: float = 1.5
        self._last_status: dict[str, str | float | int | None] = {
            "stream": None,
            "event_id": None,
            "device_id": None,
            "result_type": None,
            "risk_hint": None,
            "updated_at": None,
            "error": None,
        }

    def _required_guide_gap_sec(self, device_id: str) -> float:
        """직전 안내 오디오의 실측 재생 길이 + 여유 마진과 최소 쿨다운 중 큰 값을 반환한다."""
        prev_duration_sec = self._last_guide_duration_sec.get(device_id, 0.0)
        return max(
            self._min_guide_cooldown_sec, prev_duration_sec + self._guide_cooldown_margin_sec
        )

    def get_runtime_status(self) -> dict[str, str | float | int | None]:
        """최근 DetectionConsumer 처리 상태를 반환한다."""
        return dict(self._last_status)

    async def _ensure_pipeline(self) -> DetectionPipeline:
        if self._pipeline is None:
            await redis_bus.connect()
            self._pipeline = DetectionPipeline(
                detector=get_detector(),
                segmentor=get_segmentor(),
                tracker=ByteTrackTracker(),
                producer=RiskEventProducer(bus=redis_bus),
                redis_bus=redis_bus,
            )
            logger.info("[DetectionConsumer] pipeline 초기화 완료")
        return self._pipeline

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            await self._ensure_pipeline()
        except Exception as e:
            logger.error(f"[DetectionConsumer] pipeline 초기화 실패: {e}")
            logger.warning("[DetectionConsumer] 폴백 모드로 시작 (pipeline 없이 큐만 소비)")
            self._pipeline = None
        self._reflex_task = asyncio.create_task(self._consume_loop("reflex"))
        self._cognitive_task = asyncio.create_task(self._consume_loop("cognitive"))
        logger.info("[DetectionConsumer] 큐 컨슘 시작: reflex + cognitive")

    async def stop(self) -> None:
        self._running = False
        for task in (self._reflex_task, self._cognitive_task):
            if task and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._reflex_task = None
        self._cognitive_task = None
        logger.info("[DetectionConsumer] 중지")

    async def _consume_loop(self, stream: str) -> None:
        queue = self._select_queue(stream)
        logger.info(f"[DetectionConsumer] {stream} 루프 시작")
        while self._running:
            try:
                processed = await queue.get()
                await self._process_frame(processed, stream)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[DetectionConsumer] {stream} 처리 오류: {e}", exc_info=True)
                continue
        logger.info(f"[DetectionConsumer] {stream} 루프 종료")

    def _select_queue(self, stream: str) -> asyncio.Queue:
        if stream == "reflex":
            return self.splitter.reflex_queue
        return self.splitter.cognitive_queue

    async def _process_frame(self, processed, stream: str) -> None:
        if self._pipeline is None:
            logger.debug(
                f"[DetectionConsumer] pipeline 미초기화, skip: "
                f"event_id={processed.event_id}, stream={stream}"
            )
            self._last_status.update(
                {
                    "stream": stream,
                    "event_id": processed.event_id,
                    "device_id": processed.device_id,
                    "result_type": "pipeline_uninitialized",
                    "risk_hint": None,
                    "updated_at": now_ts(),
                    "error": None,
                }
            )
            return

        frame: np.ndarray = processed.frame
        try:
            result, detections, surfaces = await self._pipeline.run(
                frame=frame,
                stream=stream,
                event_id=processed.event_id,
                device_id=processed.device_id,
            )
        except Exception as e:
            logger.error(
                f"[DetectionConsumer] pipeline.run 실패: event_id={processed.event_id}, {e}"
            )
            self._last_status.update(
                {
                    "stream": stream,
                    "event_id": processed.event_id,
                    "device_id": processed.device_id,
                    "result_type": "pipeline_error",
                    "risk_hint": None,
                    "updated_at": now_ts(),
                    "error": str(e),
                }
            )
            return

        # 서버 YOLO 추론 결과를 BBox 렌더링용으로 단말에 실시간 송신
        await self._send_server_detection(processed.device_id, processed.event_id, detections, surfaces)

        if isinstance(result, ReflexAlert):
            self._last_status.update(
                {
                    "stream": stream,
                    "event_id": result.event_id,
                    "device_id": processed.device_id,
                    "result_type": "reflex_alert",
                    "risk_hint": result.risk_level,
                    "updated_at": now_ts(),
                    "error": None,
                }
            )
            await self._send_reflex_alert(processed.device_id, result)
        elif isinstance(result, DetectionResult):
            self._last_status.update(
                {
                    "stream": stream,
                    "event_id": result.event_id,
                    "device_id": processed.device_id,
                    "result_type": "detection_result",
                    "risk_hint": result.risk_hint,
                    "updated_at": now_ts(),
                    "error": None,
                }
            )
            if result.risk_hint in ("mid", "low"):
                await self._send_cognitive_guide(processed.device_id, result)
            logger.debug(
                f"[DetectionConsumer] 인지 결과: event_id={result.event_id}, "
                f"risk={result.risk_hint}, inference_ms={result.inference_ms:.1f}"
            )
        else:
            logger.warning(f"[DetectionConsumer] 예상치 못한 결과 타입: {type(result)}")
            self._last_status.update(
                {
                    "stream": stream,
                    "event_id": processed.event_id,
                    "device_id": processed.device_id,
                    "result_type": type(result).__name__,
                    "risk_hint": None,
                    "updated_at": now_ts(),
                    "error": "unexpected_result_type",
                }
            )

    async def _send_server_detection(
        self,
        device_id: str,
        event_id: str,
        detections: list,
        surfaces: list,
    ) -> None:
        """YOLO 및 Segmentation 탐지 결과를 BBox 표시용으로 실시간 전송한다."""
        payload_detections = []
        for det in detections:
            payload_detections.append(
                {
                    "model": "object_detection",
                    "className": det.class_name,
                    "confidence": float(det.confidence),
                    "bbox": {
                        "x": float(det.bbox.x),
                        "y": float(det.bbox.y),
                        "w": float(det.bbox.w),
                        "h": float(det.bbox.h),
                    },
                }
            )

        for surf in surfaces:
            # Segmentation centroid 주변에 가상의 80x80 BBox 구성
            if surf.centroid and len(surf.centroid) >= 2:
                cx, cy = surf.centroid[0], surf.centroid[1]
                payload_detections.append(
                    {
                        "model": "segmentation",
                        "className": surf.class_name,
                        "confidence": 1.0,
                        "bbox": {
                            "x": float(cx - 40),
                            "y": float(cy - 40),
                            "w": 80.0,
                            "h": 80.0,
                        },
                    }
                )

        payload = {
            "type": "server_detection",
            "event_id": event_id,
            "detections": payload_detections,
            "ts": time.time(),
        }

        try:
            await manager.send_json(device_id, payload)
        except Exception as e:
            logger.error(
                f"[DetectionConsumer] server_detection 송신 실패: device_id={device_id}, {e}"
            )

    async def _send_reflex_alert(self, device_id: str, alert: ReflexAlert) -> None:
        """반사 알림을 WebSocket 고우선 채널로 즉시 전송 (LLM/RAG 미경유).

        동일 device_id+alert_id 조합이 60초 이내 재발행되면 억제한다(중복 스팸 방지).
        """
        if await Alert_suppressor.should_suppress(device_id, alert.alert_id):
            logger.debug(
                f"[DetectionConsumer] 반사 알림 중복 억제: "
                f"device_id={device_id}, alert_id={alert.alert_id}"
            )
            return

        payload = {
            "type": "reflex_alert",
            "event_id": alert.event_id,
            "alert_id": alert.alert_id,
            "direction": alert.direction,
            "risk_level": alert.risk_level,
            "clip": alert.clip,
            "haptic": alert.haptic,
            "panning": alert.panning,
            "distance": alert.distance,
            "beep_interval_ms": alert.beep_interval_ms,
            "haptic_pattern": alert.haptic_pattern,
            "ts": alert.ts or now_ts(),
        }
        try:
            await manager.send_json(device_id, payload)
            await Alert_suppressor.mark_as_sent(device_id, alert.alert_id)
            logger.info(
                f"[DetectionConsumer] 반사 알림 전송: "
                f"device_id={device_id}, alert_id={alert.alert_id}"
            )
        except Exception as e:
            logger.error(f"[DetectionConsumer] 반사 알림 전송 실패: device_id={device_id}, {e}")

    async def _send_cognitive_guide(self, device_id: str, result: DetectionResult) -> None:
        """인지 결과를 오케스트레이션/TTS와 연결해 guide 메시지로 전송한다."""
        if not result.detections:
            return

        # 쿨다운 사전 검사(빠른 경로): 직전 "전송"으로부터 얼마 지나지 않았다면 굳이
        # 오케스트레이션/TTS(수 초 소요)를 새로 돌리지 않고 조기 반환한다. 실제 간격
        # 보장은 아래 전송 직전 재검사에서 확정하므로 여기서는 슬롯을 갱신하지 않는다.
        if time.monotonic() - self._last_guide_ts.get(
            device_id, 0.0
        ) < self._required_guide_gap_sec(device_id):
            logger.debug(
                f"[DetectionConsumer] 인지 가이드 쿨다운 중 - 전송 생략: device_id={device_id}"
            )
            return

        # NavigationManager에서 융합 길안내 멘트 조회
        navigation_guidance = ""
        try:
            from server.navigation.manager import nav_manager

            guidance_event = nav_manager.get_combined_guidance(device_id)
            if guidance_event:
                navigation_guidance = guidance_event.get("text", "")
        except Exception as e:
            logger.error(f"[DetectionConsumer] NavigationManager 조회 실패: {e}")

        # RAG 검색: 가장 신뢰도 높은 탐지 사물 기준으로 안전 수칙 조회 (실패 시 빈 문자열, fallback 미경유 유지)
        rag_context = ""
        try:
            retriever = get_default_retriever()
            if retriever is not None:
                primary_det = max(result.detections, key=lambda d: d.confidence)
                rag_context = await asyncio.to_thread(
                    retriever.search_guidance,
                    {"class_name": primary_det.class_name, "confidence": primary_det.confidence},
                )
        except Exception as e:
            logger.error(f"[DetectionConsumer] RAG 검색 실패: {e}")

        orch_input = {
            "event": {
                "event_id": result.event_id,
                "risk_hint": result.risk_hint,
                "detections": [
                    {
                        "class_name": det.class_name,
                        "confidence": det.confidence,
                        "direction": det.direction,
                    }
                    for det in result.detections
                ],
            },
            "detected_classes": [det.class_name for det in result.detections],
            "positions": [det.direction or "" for det in result.detections],
            "risk_level": result.risk_hint,
            "navigation_guidance": navigation_guidance,
            "rag_context": rag_context or "관련 수칙 없음",
            "retry_count": 0,
            "verified": False,
            "validation_errors": [],
        }

        try:
            orch_result = await run_orchestrator(orch_input)
            guidance_text = orch_result.get("guidance_text", "")
            if not guidance_text:
                logger.warning(
                    f"[DetectionConsumer] guidance_text 없음: event_id={result.event_id}"
                )
                return

            audio_b64, duration_ms = await realtime_tts.synthesize_from_llm(orch_result)

            # 전송 직전 재검사: 오케스트레이션/TTS 처리 시간이 요청마다 달라(2~10s+),
            # "처리 시작" 시점 쿨다운만으로는 실제 전송(클라이언트 재생 트리거) 간격이
            # 직전 안내 재생 시간보다 가까워질 수 있다. 실제 전송 직전에 한 번 더 슬롯을
            # 확인/갱신해 클라이언트에서 이전 안내 음성이 끝나기 전에 새 안내가 도착하는
            # 것을 막는다(_required_guide_gap_sec가 직전 오디오 실측 길이를 반영).
            send_now = time.monotonic()
            if send_now - self._last_guide_ts.get(device_id, 0.0) < self._required_guide_gap_sec(
                device_id
            ):
                logger.debug(
                    f"[DetectionConsumer] 인지 가이드 전송 직전 쿨다운 재검사 - 생략: "
                    f"device_id={device_id}, event_id={result.event_id}"
                )
                return
            self._last_guide_ts[device_id] = send_now
            self._last_guide_duration_sec[device_id] = duration_ms / 1000.0

            payload = {
                "type": "guide",
                "event_id": result.event_id,
                "risk_level": result.risk_hint,
                "guidance_text": guidance_text,
                "audio_mp3_b64": audio_b64 or "",
                "audio_codec": "wav",
                "duration_ms": duration_ms,
                "ts": now_ts(),
            }
            await manager.send_json(device_id, payload)
            logger.info(
                f"[DetectionConsumer] guide 전송: device_id={device_id}, event_id={result.event_id}"
            )
        except Exception as e:
            logger.error(
                f"[DetectionConsumer] guide 생성/전송 실패: device_id={device_id}, event_id={result.event_id}, {e}"
            )


_default_consumer: DetectionConsumer | None = None


def get_default_consumer() -> DetectionConsumer:
    """모듈 수준 싱글턴. ws_router lifespan에서 시작/중지 제어."""
    global _default_consumer
    if _default_consumer is None:
        _default_consumer = DetectionConsumer()
    return _default_consumer
