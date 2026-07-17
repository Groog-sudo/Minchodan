"""
3단계 DetectionConsumer.
StreamSplitter의 asyncio.Queue에서 ProcessedFrame을 소비하고
DetectionPipeline을 실행한 뒤, 반사 알림은 WebSocket 고우선 채널로,
인지 이벤트는 Redis Streams로 전송한다 (이중 경로 물리 분리 준수).
"""

import asyncio
import base64
import contextlib
import logging
import os
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
from server.detection.direction import estimate_clock_direction, estimate_distance
from server.detection.risk_rules import class_name_to_ko
from server.detection.schemas import DetectionResult, ReflexAlert
from server.orchestration import run_orchestrator
from server.orchestration.llm_client_factory import LLMClientFactory
from server.rag.retriever import get_default_retriever
from server.services.detection_guidance_log_service import persist_detection_guidance_log
from server.services.device_registry_service import get_cached_device_ids
from server.services.event_frame_store import save_event_frame_async
from server.services.pipeline_debug_builder import (
    build_cognitive_pipeline_debug,
    build_reflex_pipeline_debug,
)
from server.tts.realtime_tts import realtime_tts
from server.tts.suppressor import Alert_suppressor

logger = logging.getLogger(__name__)

# 보도 이탈 확정에 필요한 연속 인지 프레임 수 (surface_departure.py의 단일 프레임
# 판정을 히스테리시스로 감싸는 값 - 이 파일 상단 __init__ 주석 참조).
DEPARTURE_CONFIRM_STREAK = 3

# P0-2 (2026-07-17): 큐 대기로 인한 지연 드리프트 방지.
# 소비 시각 기준 프레임 ts(밀리초 epoch)가 max_age_s를 초과하면 추론 없이 드롭.
# 반사는 즉시성이 생명이므로 0.4초, 인지는 1~2fps 특성상 2.0초 여유.
# ts=0(클라이언트 미전송)이면 신선도 검사를 건너뛴다 (방어적 코딩).
REFLEX_MAX_AGE_S = float(os.getenv("REFLEX_MAX_AGE_S", "0.4"))
COGNITIVE_MAX_AGE_S = float(os.getenv("COGNITIVE_MAX_AGE_S", "2.0"))


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
        # DB 로그 저장은 반사/인지 응답 전송 경로를 막지 않도록 fire-and-forget으로
        # 실행한다 - 참조를 들고 있지 않으면 태스크가 GC되어 조기 취소될 수 있다.
        self._log_tasks: set[asyncio.Task] = set()
        # 반사 경보 후 800ms 지연 인지 가이드도 동일한 이유로 참조를 들고 있어야 한다.
        self._delayed_guide_tasks: set[asyncio.Task] = set()
        # device_id별 마지막 인지 가이드 전송 시각(초)과 그 오디오 재생 길이(초).
        # 이전 안내 음성이 끝나기 전에 다음 안내가 겹쳐 재생을 끊는 문제를 막기 위한
        # 간격 쿨다운. 고정값 하나로는 문장 길이에 따라 달라지는 실제 WAV 재생 시간을
        # 반영하지 못해(짧은 문장엔 과잉 대기, 긴 문장엔 재생 중 짤림) 직전 오디오의
        # 실측 길이 기반으로 동적 산정한다(비협상 아님, 튜닝값).
        self._last_guide_ts: dict[str, float] = {}
        self._last_guide_duration_sec: dict[str, float] = {}
        self._min_guide_cooldown_sec: float = 8.0
        self._guide_cooldown_margin_sec: float = 1.5
        # 2026-07-13 추가: device_id별 보도 이탈(is_departing) 연속 프레임 카운터.
        # 인지 프레임은 1~2fps라 세그멘테이션 경계 노이즈로 단일 프레임이 흔들릴 수 있어,
        # DEPARTURE_CONFIRM_STREAK회 연속으로 이탈이 나와야 실제 안내를 내보낸다
        # (약 1.5~3초 지속 확인 - 너무 짧으면 오탐, 너무 길면 안내가 늦어짐).
        self._departure_streak: dict[str, int] = {}
        # P0-2 (2026-07-17): 스트림별 신선도 초과 드롭 카운터 (콘솔 지연 패널 노출용).
        self._stale_drop_count: dict[str, int] = {"reflex": 0, "cognitive": 0}
        self._last_status: dict[str, str | float | int | None] = {
            "stream": None,
            "event_id": None,
            "device_id": None,
            "result_type": None,
            "risk_hint": None,
            "updated_at": None,
            "error": None,
        }

    def _update_departure_streak(self, device_id: str, is_departing: bool) -> bool:
        """연속 이탈 프레임 수를 device_id별로 갱신하고, 확정 임계값 도달 여부를 반환한다."""
        streak = self._departure_streak.get(device_id, 0) + 1 if is_departing else 0
        self._departure_streak[device_id] = streak
        return streak >= DEPARTURE_CONFIRM_STREAK

    def _required_guide_gap_sec(self, device_id: str) -> float:
        """직전 안내 오디오의 실측 재생 길이 + 여유 마진과 최소 쿨다운 중 큰 값을 반환한다."""
        prev_duration_sec = self._last_guide_duration_sec.get(device_id, 0.0)
        return max(
            self._min_guide_cooldown_sec, prev_duration_sec + self._guide_cooldown_margin_sec
        )

    def get_runtime_status(self) -> dict[str, str | float | int | None]:
        """최근 DetectionConsumer 처리 상태를 반환한다."""
        return dict(self._last_status)

    async def _broadcast_latency_event(
        self, event_id: str | None, stream_type: str, latency_stages: dict[str, float]
    ) -> None:
        """콘솔 "파이프라인 지연 요약" 패널을 실시간 갱신하기 위해 스테이지별 ms를 즉시 푸시한다.

        기존 REST 폴링(30초)만으로는 콘솔이 "실시간"으로 느껴지지 않는다는 피드백에 따라,
        이미 연결돼 있는 콘솔 WS 브로드캐스트 채널(server_detection과 동일 채널)을 재사용한다
        - 신규 연결/엔드포인트 없이 기존에 검증된 경로에 얹는다. db_save_ms는 이 시점에는
        아직 확정 전이라(비동기 백그라운드에서 INSERT 이후 측정) 포함하지 않는다 - REST 폴링된
        detection_guidance_logs 조회 시에는 포함된다.
        """
        try:
            await manager.broadcast_json_to_consoles(
                {
                    "type": "latency_event",
                    "event_id": event_id,
                    "stream_type": stream_type,
                    "latency": latency_stages,
                    "ts": time.time(),
                }
            )
        except Exception as e:
            logger.debug(f"[DetectionConsumer] latency_event 브로드캐스트 실패: {e}")

    async def _broadcast_ai_pipeline_status(self, **fields) -> None:
        """콘솔 "AI Pipeline Monitor" 패널의 LLM/RAG/TTS 필드를 실시간 갱신한다.

        llm_provider/llm_verified/llm_retry_count/rag_query/tts_engine/reflex_bypass는
        콘솔 타입(AiPipelineStatus)에는 정의돼 있었지만 서버 쪽 producer가 전혀 없어
        항상 undefined였다(2026-07-12 발견 - session_status와 같은 문제).
        이 채널은 latency_event/guidance_log_event가 쓰는 콘솔 WS(session_manager)가
        아니라, SystemMetrics/SessionStatus와 같은 SSE 채널(mcp_manager)이다 - 두 브로드캐스트
        경로가 이 프로젝트에 별도로 존재하므로 혼동하지 않도록 주의(§ws_router._broadcast_session_status
        참조). event_type은 콘솔이 llm_status/rag_result/tts_status를 동일하게 처리하므로
        아무거나 써도 무방하지만 가독성을 위해 "llm_status"로 통일한다.
        """
        try:
            from server.mcp.manager import mcp_manager

            await mcp_manager.broadcast_event("llm_status", fields)
        except Exception as e:
            logger.debug(f"[DetectionConsumer] ai_pipeline 상태 브로드캐스트 실패: {e}")

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
        for log_task in list(self._log_tasks):
            log_task.cancel()
        for guide_task in list(self._delayed_guide_tasks):
            guide_task.cancel()
        logger.info("[DetectionConsumer] 중지")

    def _schedule_log_persist(
        self,
        *,
        event_id: str | None,
        stream_type: str,
        detections: list[dict],
        tts_text: str,
        frame: np.ndarray | None = None,
        latency_stages: dict[str, float] | None = None,
        user_id: int | None = None,
        device_id: int | None = None,
        pipeline_debug: dict | None = None,
    ) -> None:
        task = asyncio.create_task(
            self._persist_log_safe(
                event_id=event_id,
                stream_type=stream_type,
                detections=detections,
                tts_text=tts_text,
                frame=frame,
                latency_stages=latency_stages,
                user_id=user_id,
                device_id=device_id,
                pipeline_debug=pipeline_debug,
            )
        )
        self._log_tasks.add(task)
        task.add_done_callback(self._log_tasks.discard)

    async def _persist_log_safe(
        self,
        *,
        event_id: str | None,
        stream_type: str,
        detections: list[dict],
        tts_text: str,
        frame: np.ndarray | None = None,
        latency_stages: dict[str, float] | None = None,
        user_id: int | None = None,
        device_id: int | None = None,
        pipeline_debug: dict | None = None,
    ) -> None:
        # 프레임 저장(JPEG 인코딩+디스크 쓰기)은 백그라운드 로그 태스크 안에서만
        # 수행한다. 반사/인지 실시간 전송이 끝난 뒤 실행되므로 경로 지연에 영향 없다.
        # 저장 실패 시 frame_path=None으로 로그 적재는 계속한다(방어적 코딩).
        frame_path: str | None = None
        if frame is not None and event_id:
            frame_path = await save_event_frame_async(event_id, frame)
        try:
            saved = await persist_detection_guidance_log(
                event_id=event_id,
                stream_type=stream_type,
                detections=detections,
                tts_text=tts_text,
                frame_path=frame_path,
                latency_stages=latency_stages,
                user_id=user_id,
                device_id=device_id,
                pipeline_debug=pipeline_debug,
            )
        except Exception as e:
            logger.error(f"[DetectionConsumer] DB 로그 저장 실패: event_id={event_id}, {e}")
            return
        await self._broadcast_guidance_log_event(saved)

    async def _broadcast_guidance_log_event(self, row) -> None:
        """콘솔 Detection Guidance Log 테이블을 실시간 갱신하기 위해 저장 완료된 로그 행을 푸시한다.

        DB 저장(+프레임 파일 저장)이 모두 끝난 뒤에만 호출되므로, 콘솔이 이 이벤트를 받자마자
        썸네일 URL을 요청해도 404가 나지 않는다(latency_event보다 나중에, 별도로 발생).
        REST 응답(DetectionGuidanceLogResponse)과 동일한 필드 구조를 그대로 실어 보내
        콘솔이 REST로 받은 행과 동일하게 다룰 수 있게 한다.
        """
        try:
            await manager.broadcast_json_to_consoles(
                {"type": "guidance_log_event", "row": row.model_dump(mode="json")}
            )
        except Exception as e:
            logger.debug(f"[DetectionConsumer] guidance_log_event 브로드캐스트 실패: {e}")

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
        # P0-2 (2026-07-17): 큐 대기 시간 계측 + 신선도 검사.
        # processed.ts는 클라이언트 전송 시각(밀리초 epoch). ts=0이면 클라이언트가
        # 전송하지 않은 것으로 간주해 신선도 검사를 건너뛴다 (방어적 코딩).
        queue_wait_ms = 0.0
        if processed.ts > 0:
            now_ms = time.time() * 1000.0
            queue_wait_ms = round(now_ms - processed.ts, 1)
            max_age_s = REFLEX_MAX_AGE_S if stream == "reflex" else COGNITIVE_MAX_AGE_S
            age_s = queue_wait_ms / 1000.0
            if age_s > max_age_s:
                self._stale_drop_count[stream] = self._stale_drop_count.get(stream, 0) + 1
                logger.debug(
                    f"[DetectionConsumer] stale 프레임 드롭: stream={stream}, "
                    f"age={age_s:.2f}s > {max_age_s}s, event_id={processed.event_id}, "
                    f"drop_count={self._stale_drop_count[stream]}"
                )
                return
        # 레이턴시 계측 기준점: 프레임 디코딩 완료(processed.processing_time_ms) 이후부터
        # 반사/인지 전송 완료까지를 측정한다. decode_ms + 이 구간이 WS 수신~단말 전송 총 지연이다.
        pipeline_start = time.perf_counter()
        try:
            result, detections, surfaces = await self._pipeline.run(
                frame=frame,
                stream=stream,
                event_id=processed.event_id,
                device_id=processed.device_id,
                is_outdoor=processed.is_outdoor,
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
        await self._send_server_detection(
            processed.device_id, processed.event_id, detections, surfaces
        )
        # 콘솔 DetectionFeed 패널(탐지 메타데이터 텍스트 피드) 실시간 갱신
        await self._broadcast_detection_event(
            processed.device_id,
            processed.event_id,
            stream,
            detections,
            surfaces,
            getattr(result, "inference_ms", 0.0),
        )

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
            await self._send_reflex_alert(
                processed.device_id,
                result,
                frame=frame,
                decode_ms=processed.processing_time_ms,
                pipeline_start=pipeline_start,
                detections=detections,
                queue_wait_ms=queue_wait_ms,
            )
            # [2026-07-14] 반사 경보(정지) 발동 800ms 후 인지(설명/우회방향) 가이드를 후속 트리거
            delayed_guide_task = asyncio.create_task(
                self._trigger_delayed_cognitive_guide(
                    device_id=processed.device_id,
                    alert=result,
                    detections=detections,
                    surfaces=surfaces,
                    frame=frame,
                    decode_ms=processed.processing_time_ms,
                    pipeline_start=pipeline_start,
                )
            )
            self._delayed_guide_tasks.add(delayed_guide_task)
            delayed_guide_task.add_done_callback(self._delayed_guide_tasks.discard)
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
            departure_confirmed = self._update_departure_streak(
                processed.device_id, result.is_departing
            )
            if result.risk_hint in ("mid", "low") or departure_confirmed:
                await self._send_cognitive_guide(
                    processed.device_id,
                    result,
                    frame=frame,
                    decode_ms=processed.processing_time_ms,
                    pipeline_start=pipeline_start,
                    departure_confirmed=departure_confirmed,
                    queue_wait_ms=queue_wait_ms,
                )
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

    async def _broadcast_detection_event(
        self,
        device_id: str,
        event_id: str,
        stream: str,
        detections: list,
        surfaces: list,
        inference_ms: float,
    ) -> None:
        """콘솔 DetectionFeed 패널(탐지 메타데이터 텍스트 피드)을 실시간 갱신한다.

        이전에는 detection_event가 서버 어디에서도 브로드캐스트되지 않아 패널이 항상
        비어 있었다(2026-07-12 발견, session_status와 동일 문제). DetectionFeedItem은
        프레임당 탐지 1건 요약 구조라, 탐지가 있으면 가장 신뢰도 높은 객체를, 없고
        노면 분류만 있으면 surface만 실어 보낸다. 아무것도 없는 프레임은 보내지 않는다
        (반사 8~10fps 전부를 텍스트 피드에 흘리면 도배되므로).
        """
        if not detections and not surfaces:
            return

        primary_class = "unknown"
        confidence: float | None = None
        if detections:
            primary = max(detections, key=lambda d: d.confidence)
            primary_class = primary.class_name
            confidence = primary.confidence

        try:
            from server.mcp.manager import mcp_manager

            await mcp_manager.broadcast_event(
                "detection_event",
                {
                    "event_id": event_id,
                    "device_id": device_id,
                    "stream": stream,
                    "class_name": primary_class,
                    "confidence": confidence,
                    "inference_ms": round(inference_ms, 1),
                    "surface": surfaces[0].class_name if surfaces else None,
                },
            )
        except Exception as e:
            logger.debug(f"[DetectionConsumer] detection_event 브로드캐스트 실패: {e}")

    @staticmethod
    def _normalize_risk_level(raw: str | None) -> str:
        if raw in ("high", "mid", "low"):
            return raw
        return "low"

    async def _broadcast_risk_event(
        self,
        *,
        event_id: str,
        risk_level: str,
        class_name: str,
        confidence: float | None = None,
        direction: str | None = None,
        guidance_text: str | None = None,
        device_id: str | None = None,
    ) -> None:
        """콘솔 RiskEventLog 패널용 risk_event SSE 브로드캐스트.

        detection_event와 동일하게 mcp_manager 경유. 서버 어디에서도 발행되지 않아
        RiskEventLog가 항상 비어 있던 문제(2026-07-16)를 해소한다.
        """
        payload: dict[str, object] = {
            "event_id": event_id,
            "risk_level": self._normalize_risk_level(risk_level),
            "class_name": class_name or "unknown",
        }
        if confidence is not None:
            payload["confidence"] = round(float(confidence), 4)
        if direction:
            payload["direction"] = direction
        if guidance_text:
            payload["guidance_text"] = guidance_text
        if device_id:
            payload["device_id"] = device_id

        try:
            from server.mcp.manager import mcp_manager

            await mcp_manager.broadcast_event("risk_event", payload)
        except Exception as e:
            logger.debug(f"[DetectionConsumer] risk_event 브로드캐스트 실패: {e}")

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
            await manager.broadcast_json_to_consoles(payload)
        except Exception as e:
            logger.error(
                f"[DetectionConsumer] server_detection 송신 실패: device_id={device_id}, {e}"
            )

    async def _send_reflex_alert(
        self,
        device_id: str,
        alert: ReflexAlert,
        frame: np.ndarray | None = None,
        decode_ms: float = 0.0,
        pipeline_start: float | None = None,
        detections: list | None = None,
        queue_wait_ms: float = 0.0,
    ) -> None:
        """반사 알림을 WebSocket 고우선 채널로 즉시 전송 (LLM/RAG 미경유).

        동일 device_id+alert_id 조합이 60초 이내 재발행되면 억제한다(중복 스팸 방지).
        frame은 전송 성사 후 백그라운드 로그 태스크에서만 저장한다(반사 지연 무영향).
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
            "track_id": alert.track_id,
            "class_name": alert.class_name,
            "hit_count": alert.hit_count,
        }
        try:
            sent = await manager.send_json(device_id, payload)
            if not sent:
                logger.warning(
                    f"[DetectionConsumer] 반사 알림 미전송: "
                    f"device_id={device_id}, alert_id={alert.alert_id}, websocket=disconnected"
                )
                return
            await Alert_suppressor.mark_as_sent(device_id, alert.alert_id)
            logger.info(
                f"[DetectionConsumer] 반사 알림 전송: "
                f"device_id={device_id}, alert_id={alert.alert_id}"
            )
            # 반사 경로 latency_json에는 decode/inference/total만 존재한다(LLM/RAG/TTS 미경유
            # 원칙이 그대로 데이터에 반영됨 - rag_ms/llm_ms/tts_ms 키 자체가 생기지 않는다).
            latency_stages: dict[str, float] = {
                "decode_ms": round(decode_ms, 1),
                "inference_ms": round(alert.inference_ms, 1),
                "queue_wait_ms": round(queue_wait_ms, 1),
            }
            if pipeline_start is not None:
                latency_stages["total_ms"] = round(
                    (time.perf_counter() - pipeline_start) * 1000 + decode_ms, 1
                )
            await self._broadcast_latency_event(alert.event_id, "reflex", latency_stages)
            await self._broadcast_ai_pipeline_status(reflex_bypass=True)
            reflex_confidence: float | None = None
            if detections:
                matched = [d for d in detections if d.class_name == alert.class_name]
                primary = matched[0] if matched else max(detections, key=lambda d: d.confidence)
                reflex_confidence = float(primary.confidence)
            await self._broadcast_risk_event(
                event_id=alert.event_id,
                risk_level=alert.risk_level,
                class_name=alert.class_name or "unknown",
                confidence=reflex_confidence,
                direction=alert.direction,
                guidance_text=f"[반사 클립] {alert.clip}",
                device_id=device_id,
            )
            reg_user_id, reg_device_id = get_cached_device_ids(device_id)
            self._schedule_log_persist(
                event_id=alert.event_id,
                stream_type="reflex",
                detections=[
                    {
                        "track_id": alert.track_id,
                        "class_name": alert.class_name,
                        "hit_count": alert.hit_count,
                        "alert_id": alert.alert_id,
                        "direction": alert.direction,
                        "risk_level": alert.risk_level,
                        "distance": alert.distance,
                    }
                ],
                tts_text=f"[반사 클립] {alert.clip}",
                frame=frame,
                latency_stages=latency_stages,
                user_id=reg_user_id,
                device_id=reg_device_id,
                pipeline_debug=build_reflex_pipeline_debug(
                    alert_id=alert.alert_id,
                    clip=alert.clip,
                    direction=alert.direction,
                    class_name=alert.class_name,
                    distance=str(alert.distance) if alert.distance is not None else None,
                    risk_level=alert.risk_level,
                    hit_count=alert.hit_count,
                    track_id=alert.track_id,
                    inference_ms=alert.inference_ms,
                    detections=detections,
                ),
            )
        except Exception as e:
            logger.error(f"[DetectionConsumer] 반사 알림 전송 실패: device_id={device_id}, {e}")

    async def _trigger_delayed_cognitive_guide(
        self,
        device_id: str,
        alert: ReflexAlert,
        detections: list,
        surfaces: list,
        frame: np.ndarray | None,
        decode_ms: float,
        pipeline_start: float | None,
    ) -> None:
        """반사 경보(비프/햅틱) 발동 800ms 후 인지 가이드(LLM TTS 우회)를 연계 트리거한다."""
        await asyncio.sleep(0.8)  # 반사 진동/비프음 인지용 딜레이

        # 29종 객체 탐지 클래스들을 모아 DetectionResult 스키마로 인지 경로에 피딩
        cognitive_res = DetectionResult(
            event_id=alert.event_id,
            detections=detections,
            surface=surfaces,
            risk_hint="high",  # 반사 경보 직후 상황임을 명시하기 위해 high 위험도 부여
            inference_ms=alert.inference_ms,
            is_departing=False,
            braille_direction="",
        )

        # 인지 경로 전송
        await self._send_cognitive_guide(
            device_id=device_id,
            result=cognitive_res,
            frame=frame,
            decode_ms=decode_ms,
            pipeline_start=pipeline_start,
            departure_confirmed=False,
        )

    async def _send_cognitive_guide(
        self,
        device_id: str,
        result: DetectionResult,
        frame: np.ndarray | None = None,
        decode_ms: float = 0.0,
        pipeline_start: float | None = None,
        departure_confirmed: bool = False,
        queue_wait_ms: float = 0.0,
    ) -> None:
        """인지 결과를 오케스트레이션/TTS와 연결해 guide 메시지로 전송한다."""

        # 💡 [면접 대비 주석]
        # Q. 노면(surface) 정보가 감지되었을 때도 가이드를 생성하는 기준은 무엇인가요?
        # A. 객체 탐지가 없어도 '주의 노면(caution)', '차도(roadway)', '점자블록(braille_normal)' 같은
        #    시각장애인 보행에 유의미한 노면 정보가 감지되었거나, 보도 이탈이 확정된 경우에는
        #    얼리 엑싯하지 않고 LangGraph 오케스트레이션(L1/L2/L3)으로 보내 정밀 가이드를 제공합니다.
        has_significant_surface = any(
            surf.class_name in ("caution", "roadway", "braille_normal") for surf in result.surface
        )
        if not result.detections and not departure_confirmed and not has_significant_surface:
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
        # detections가 비어 있는(순수 보도 이탈) 이벤트는 조회할 사물이 없으므로 건너뛴다.
        rag_context = ""
        clock_direction = ""
        distance_class = ""
        object_ko = ""
        rag_start = time.perf_counter()
        try:
            retriever = get_default_retriever()
            if result.detections:
                primary_det = max(result.detections, key=lambda d: d.confidence)
                if retriever is not None:
                    rag_context = await asyncio.to_thread(
                        retriever.search_guidance,
                        {
                            "class_name": primary_det.class_name,
                            "confidence": primary_det.confidence,
                        },
                    )
                if frame is not None:
                    clock_direction = estimate_clock_direction(primary_det.bbox, frame.shape[1])
                    distance_class = estimate_distance(
                        primary_det.bbox,
                        frame.shape[1],
                        frame.shape[0],
                        primary_det.class_name,
                    )
                object_ko = class_name_to_ko(primary_det.class_name)
        except Exception as e:
            logger.error(f"[DetectionConsumer] RAG 검색 실패: {e}")
        rag_ms = (time.perf_counter() - rag_start) * 1000

        korean_classes = [class_name_to_ko(det.class_name) for det in result.detections]

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
            "detected_classes": korean_classes,
            "positions": [det.direction or "" for det in result.detections],
            "clock_direction": clock_direction,
            "distance": distance_class,
            "object_ko": object_ko,
            "risk_level": result.risk_hint,
            "navigation_guidance": navigation_guidance,
            "rag_context": rag_context or "관련 수칙 없음",
            "is_departing_confirmed": departure_confirmed,
            "braille_direction": result.braille_direction or "",
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

            rag_query = (
                max(result.detections, key=lambda d: d.confidence).class_name
                if result.detections
                else "surface_departure"
            )
            await self._broadcast_ai_pipeline_status(
                llm_provider=LLMClientFactory.get_current_provider(),
                llm_verified=bool(orch_result.get("verified", False)),
                llm_retry_count=int(orch_result.get("retry_count", 0)),
                rag_query=rag_query,
                tts_engine=os.getenv("TTS_ENGINE", "supertonic"),
                reflex_bypass=False,
                # 2026-07-13 발견: guidance_text는 만들어지지만 이 필드가 빠져 있어
                # 콘솔 "TTS GUIDANCE"가 항상 "무발화 대기 중"으로 고정되던 버그.
                last_guidance=guidance_text,
            )

            tts_start = time.perf_counter()
            if orch_result.get("used_fast_lane"):
                audio_b64, duration_ms = await realtime_tts.synthesize_fast_lane(orch_result)
            else:
                audio_b64, duration_ms = await realtime_tts.synthesize_from_llm(orch_result)
            tts_ms = (time.perf_counter() - tts_start) * 1000

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

            # [2026-07-09 도입] guide 오디오(WAV)를 base64 문자열로 JSON에 실어 보내는
            # 대신, 메타데이터(JSON) 전송 직후 원본 바이트를 바이너리 프레임으로 이어
            # 보낸다(카메라 프레임 client->server 전송에 이미 적용된 패턴을 반대
            # 방향에도 적용). 실기기에서 문장 중간 음절이 산발적으로 사라지는 현상의
            # 원인 후보(base64 팽창/RN 구 브릿지 대용량 문자열 처리)를 제거하기 위함.
            audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""

            payload = {
                "type": "guide",
                "event_id": result.event_id,
                "risk_level": result.risk_hint,
                "guidance_text": guidance_text,
                "clock_direction": orch_result.get("clock_direction") or clock_direction,
                "distance_class": orch_result.get("distance") or distance_class,
                "object_ko": orch_result.get("object_ko") or object_ko,
                "audio_codec": "wav",
                "duration_ms": duration_ms,
                "transport": "binary" if audio_bytes else "none",
                "ts": now_ts(),
            }
            await manager.send_json(device_id, payload)
            if audio_bytes:
                await manager.send_bytes(device_id, audio_bytes)
            logger.info(
                f"[DetectionConsumer] guide 전송: device_id={device_id}, event_id={result.event_id}"
            )
            detected_classes_str = ", ".join(orch_input["detected_classes"]) or "(없음)"
            logger.info(
                f'[DetectionConsumer] 탐지 객체: [{detected_classes_str}] -> LLM 응답: "{guidance_text}"'
            )
            # DB 로그에는 콘솔 오탐 검증용 bbox 오버레이를 위해 좌표를 함께 남긴다.
            # (LLM 입력 orch_input에는 bbox를 넣지 않는다 - 프롬프트 오염 방지)
            log_detections = [
                {
                    "track_id": det.track_id,
                    "class_name": det.class_name,
                    "confidence": float(det.confidence),
                    "direction": det.direction,
                    "hit_count": det.hit_count,
                    "bbox": {
                        "x": float(det.bbox.x),
                        "y": float(det.bbox.y),
                        "w": float(det.bbox.w),
                        "h": float(det.bbox.h),
                    },
                }
                for det in result.detections
            ]
            latency_stages: dict[str, float] = {
                "decode_ms": round(decode_ms, 1),
                "inference_ms": round(result.inference_ms, 1),
                "rag_ms": round(rag_ms, 1),
                "llm_ms": round(orch_result.get("total_latency_ms", 0.0), 1),
                "tts_ms": round(tts_ms, 1),
                "queue_wait_ms": round(queue_wait_ms, 1),
            }
            if pipeline_start is not None:
                latency_stages["total_ms"] = round(
                    (time.perf_counter() - pipeline_start) * 1000 + decode_ms, 1
                )
            await self._broadcast_latency_event(result.event_id, "cognitive", latency_stages)
            cognitive_risk = orch_result.get("risk_level") or result.risk_hint
            cognitive_class = (
                max(result.detections, key=lambda d: d.confidence).class_name
                if result.detections
                else (object_ko or "surface")
            )
            cognitive_confidence = (
                float(max(result.detections, key=lambda d: d.confidence).confidence)
                if result.detections
                else None
            )
            cognitive_direction = (
                orch_result.get("clock_direction")
                or clock_direction
                or (
                    max(result.detections, key=lambda d: d.confidence).direction
                    if result.detections
                    else None
                )
            )
            await self._broadcast_risk_event(
                event_id=result.event_id,
                risk_level=str(cognitive_risk),
                class_name=str(cognitive_class),
                confidence=cognitive_confidence,
                direction=str(cognitive_direction) if cognitive_direction else None,
                guidance_text=guidance_text,
                device_id=device_id,
            )
            reg_user_id, reg_device_id = get_cached_device_ids(device_id)
            cognitive_debug = build_cognitive_pipeline_debug(
                guidance_text=guidance_text,
                rag_query=rag_query,
                rag_context=rag_context or "관련 수칙 없음",
                orch_result=orch_result,
                clock_direction=clock_direction,
                distance_class=distance_class,
                object_ko=object_ko,
                llm_provider=LLMClientFactory.get_current_provider(),
                detections=result.detections,
                surfaces=result.surface,
                risk_hint=result.risk_hint,
                inference_ms=result.inference_ms,
                is_departing=result.is_departing,
                departure_confirmed=departure_confirmed,
                braille_direction=result.braille_direction or "",
                navigation_guidance=navigation_guidance,
                detected_classes_ko=korean_classes,
            )
            self._schedule_log_persist(
                event_id=result.event_id,
                stream_type="cognitive",
                detections=log_detections,
                tts_text=guidance_text,
                frame=frame,
                latency_stages=latency_stages,
                user_id=reg_user_id,
                device_id=reg_device_id,
                pipeline_debug=cognitive_debug,
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
