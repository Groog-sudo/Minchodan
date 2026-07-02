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
            return

        frame: np.ndarray = processed.frame
        try:
            result = await self._pipeline.run(
                frame=frame,
                stream=stream,
                event_id=processed.event_id,
                device_id=processed.device_id,
            )
        except Exception as e:
            logger.error(
                f"[DetectionConsumer] pipeline.run 실패: event_id={processed.event_id}, {e}"
            )
            return

        if isinstance(result, ReflexAlert):
            await self._send_reflex_alert(processed.device_id, result)
        elif isinstance(result, DetectionResult):
            logger.debug(
                f"[DetectionConsumer] 인지 결과: event_id={result.event_id}, "
                f"risk={result.risk_hint}, inference_ms={result.inference_ms:.1f}"
            )
        else:
            logger.warning(f"[DetectionConsumer] 예상치 못한 결과 타입: {type(result)}")

    async def _send_reflex_alert(self, device_id: str, alert: ReflexAlert) -> None:
        """반사 알림을 WebSocket 고우선 채널로 즉시 전송 (LLM/RAG 미경유)."""
        payload = {
            "type": "reflex_alert",
            "event_id": alert.event_id,
            "alert_id": alert.alert_id,
            "direction": alert.direction,
            "risk_level": alert.risk_level,
            "clip": alert.clip,
            "haptic": alert.haptic,
            "ts": alert.ts or now_ts(),
        }
        try:
            await manager.send_json(device_id, payload)
            logger.info(
                f"[DetectionConsumer] 반사 알림 전송: "
                f"device_id={device_id}, alert_id={alert.alert_id}"
            )
        except Exception as e:
            logger.error(f"[DetectionConsumer] 반사 알림 전송 실패: device_id={device_id}, {e}")


_default_consumer: DetectionConsumer | None = None


def get_default_consumer() -> DetectionConsumer:
    """모듈 수준 싱글턴. ws_router lifespan에서 시작/중지 제어."""
    global _default_consumer
    if _default_consumer is None:
        _default_consumer = DetectionConsumer()
    return _default_consumer
