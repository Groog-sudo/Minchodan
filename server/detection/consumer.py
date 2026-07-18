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
from server.detection.direction import (
    estimate_clock_direction,
    estimate_direction,
    estimate_distance,
)
from server.detection.risk_rules import class_name_to_ko
from server.detection.schemas import Detection, DetectionResult, ReflexAlert, ReflexClear
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

# P1-2 (2026-07-17): 인지 가이드 발화 가치(Utterance Value) 게이트.
# 동일 상황(객체+표면 서명 동일) 반복 안내는 COGNITIVE_UTTERANCE_COOLDOWN_S 동안 TTS 합성 생략.
# 새 객체/표면 변화/보도 이탈/쿨다운 경과 중 하나라도 true면 발화.
COGNITIVE_UTTERANCE_COOLDOWN_S = float(os.getenv("COGNITIVE_UTTERANCE_COOLDOWN_S", "30.0"))

# P2-1(b) (2026-07-17): surface_caution(계단/맨홀 통합 클래스) 단일 프레임 오탐 완화 히스테리시스.
# 세그멘테이션 경계 노이즈로 단일 프레임 caution이 흔들릴 수 있어, 연속 N 프레임 확인 후 반사 발동.
SURFACE_CAUTION_CONFIRM_STREAK = int(os.getenv("SURFACE_CAUTION_CONFIRM_STREAK", "2"))

# P2-2 (2026-07-17): 파이프라인 지연 관측 임계. total_ms가 임계 초과 시 콘솔 latency_event에
# latency_alert=True 필드를 추가해 운영자가 지연 드리프트를 실시간 인지한다.
# 반사 <300ms(비협상 목표), 인지 <3000ms(가이드 허용 범위) 기준.
REFLEX_LATENCY_ALERT_MS = float(os.getenv("REFLEX_LATENCY_ALERT_MS", "300"))
COGNITIVE_LATENCY_ALERT_MS = float(os.getenv("COGNITIVE_LATENCY_ALERT_MS", "3000"))

# T2-G (2026-07-18): 저위험(low) 순수 내레이션 발화 여부.
# false이면 "측면·원거리·정적 객체" 등 저위험 상황의 단순 내레이션을 억제한다.
GUIDE_LOW_RISK_NARRATION = os.getenv("GUIDE_LOW_RISK_NARRATION", "false").lower() == "true"


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
        # P1-2 (2026-07-17): device_id별 직전 인지 안내의 상황 서명(객체+표면).
        # 동일 서명 + 쿨다운 이내 재발화를 TTS 합성 생략으로 차단.
        self._last_guide_signature: dict[str, str] = {}
        # P2-1(b) (2026-07-17): device_id별 surface_caution 연속 프레임 카운터 (히스테리시스).
        self._surface_caution_streak: dict[str, int] = {}
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

    def _required_guide_gap_sec(
        self,
        device_id: str,
        primary_det: Detection | None = None,
        frame: np.ndarray | None = None,
        distance_class: str = "",
    ) -> float:
        """직전 안내 오디오의 실측 재생 길이 + 여유 마진과 최소 쿨다운 중 큰 값을 반환한다.

        T1-b (2026-07-18): 12시 회랑 접근 객체가 근접/중거리면 쿨다운을 단축해 신규 위험에
        빠르게 반응한다. 단, 이전 안내가 아직 재생 중이면 그 길이만큼은 기다려야 한다.
        """
        prev_duration_sec = self._last_guide_duration_sec.get(device_id, 0.0)
        base_gap = max(
            self._min_guide_cooldown_sec, prev_duration_sec + self._guide_cooldown_margin_sec
        )

        # T1-b: 12시 회랑 + approaching + near/medium이면 쿨다운을 3초로 단축
        if (
            primary_det is not None
            and frame is not None
            and distance_class in ("near", "medium")
            and primary_det.direction == "approaching"
        ):
            _h, w = frame.shape[:2]
            spatial_dir = estimate_direction(primary_det.bbox, w, distance_class)
            if spatial_dir == "front":
                return max(3.0, prev_duration_sec + self._guide_cooldown_margin_sec)

        return base_gap

    @staticmethod
    def _compute_cognitive_signature(result: DetectionResult, departure_confirmed: bool) -> str:
        """P1-2: 인지 가이드 상황 서명(객체+표면+이탈) 산출.

        # [면접 대비 주석]
        # 발화 가치 게이트의 핵심: "같은 상황의 반복 안내는 억제, 상황이 바뀌면 즉시 안내".
        # 서명 = 정렬된 객체 클래스 목록 + 정렬된 표면 클래스 목록 + 이탈 여부.
        # 동일 서명이면 같은 상황으로 간주해 쿨다운 내 TTS 합성을 생략해 CPU/중복 안내를 줄인다.
        # 객체/표면이 하나라도 바뀌면 서명이 달라져 즉시 발화한다.
        """
        objects_key = ",".join(sorted({d.class_name for d in result.detections}))
        surface_key = ",".join(sorted({s.class_name for s in result.surface}))
        departure_key = "departure" if departure_confirmed else ""
        return f"obj:{objects_key}|surf:{surface_key}|dep:{departure_key}"

    def _has_utterance_value(
        self, device_id: str, result: DetectionResult, departure_confirmed: bool
    ) -> bool:
        """P1-2: 인지 가이드 발화 가치 판정.

        발화 조건(OR):
            1. 보도 이탈 확정 (departure_confirmed) - 안전상 항상 가치.
            2. 상황 서명 변화 (새 객체/표면 변화) - 직전과 다른 상황.
            3. 직전 안내로부터 COGNITIVE_UTTERANCE_COOLDOWN_S 경과 - 동일 상황도 주기적 갱신.
        위 모두 거짓이면 동일 상황 반복이므로 TTS 합성 생략.
        """
        if departure_confirmed:
            return True
        current_sig = self._compute_cognitive_signature(result, departure_confirmed)
        prev_sig = self._last_guide_signature.get(device_id)
        if prev_sig != current_sig:
            return True
        # 동일 서명이면 쿨다운 경과 여부가 발화 가치를 결정
        return (
            time.monotonic() - self._last_guide_ts.get(device_id, 0.0)
            >= COGNITIVE_UTTERANCE_COOLDOWN_S
        )

    def _is_speech_worthy(
        self,
        primary_det: Detection | None,
        frame: np.ndarray | None,
        distance_class: str,
        risk_hint: str,
        departure_confirmed: bool,
    ) -> bool:
        """T2-G (2026-07-18): 인지 발화 회랑/접근 필터.

        발화 가치 게이트(_has_utterance_value) 앞단에서 "처음부터 발화할 가치가 있는가"를
        먼저 판정한다. 측면·원거리·정적 저위험 객체는 흰지팡이·주변 소리로 인지 가능하므로
        음성 안내 가치가 낮다. 반면 12시 회랑 접근 객체, 보도 이탈, 노면 위험은 절대
        침묵하지 않는다.

        # [면접 대비 주석]
        # 이 필터는 안전 관련 경로(보도 이탈, 고위험, 접근 객체, 유의미 노면)를 보수적으로
        # 예외 처리하고, 오직 "측면·원거리·정적 저위험"만 무발화한다.
        """
        # 안전 예외: 보도 이탈, 고위험/중위험, 저위험 내레이션 설정 시
        if departure_confirmed:
            return True
        if risk_hint in ("high", "medium"):
            return True
        if GUIDE_LOW_RISK_NARRATION:
            return True

        if primary_det is None or frame is None:
            return False

        # 원거리 정적 객체는 무발화
        if distance_class == "far" and primary_det.direction != "approaching":
            return False

        # 12시 회랑 밖 정적 객체는 무발화
        _h, w = frame.shape[:2]
        spatial_dir = estimate_direction(primary_det.bbox, w, distance_class)
        return spatial_dir == "front" or primary_det.direction == "approaching"

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
            # P2-2 (2026-07-17): 지연 임계 초과 시 latency_alert 필드 추가 (콘솔 실시간 인지).
            total_ms = latency_stages.get("total_ms", 0.0)
            threshold = (
                REFLEX_LATENCY_ALERT_MS if stream_type == "reflex" else COGNITIVE_LATENCY_ALERT_MS
            )
            latency_alert = bool(total_ms and total_ms > threshold)
            await manager.broadcast_json_to_consoles(
                {
                    "type": "latency_event",
                    "event_id": event_id,
                    "stream_type": stream_type,
                    "latency": latency_stages,
                    "latency_alert": latency_alert,
                    "latency_threshold_ms": threshold,
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

        if stream == "reflex":
            # 2026-07-18: Near episode 이탈/track 소실 감지. reflex_gate가 이번 프레임에
            # 아무것도 발동하지 않았거나(DetectionResult) 다른 track이 발동했더라도,
            # 직전에 열려 있던 Near episode의 track이 이번 프레임 detections에 더 이상
            # near로 존재하지 않으면 reflex_clear를 보낸다.
            await self._reconcile_near_episode(processed.device_id, detections)

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
            # P2-1(b) (2026-07-17): surface_caution 단일 프레임 오탐 완화 히스테리시스.
            # [면접 대비 주석] 세그멘테이션 경계 노이즈로 단일 프레임 caution이 흔들려 과경보가 되므로,
            # 연속 SURFACE_CAUTION_CONFIRM_STREAK 프레임 확인 후에만 반사 발동. 미달 시 반사 스킵
            # (caution은 인지 경로에서도 설명되므로 안전 마진 유지). high_obstacle 등 비-surface 반사는
            # 히스테리시스 없이 즉시 발동(이미 reflex_gate MIN_HIT_COUNT로 오탐 완화됨).
            if result.alert_id == "surface_caution":
                streak = self._surface_caution_streak.get(processed.device_id, 0) + 1
                self._surface_caution_streak[processed.device_id] = streak
                if streak < SURFACE_CAUTION_CONFIRM_STREAK:
                    logger.debug(
                        f"[DetectionConsumer] surface_caution 히스테리시스 대기: "
                        f"streak={streak}/{SURFACE_CAUTION_CONFIRM_STREAK}, "
                        f"device_id={processed.device_id}"
                    )
                    return
            else:
                # 비-surface 반사일 때 surface_caution streak 리셋 (독립 상태 유지)
                self._surface_caution_streak[processed.device_id] = 0
            sent_ok = await self._send_reflex_alert(
                processed.device_id,
                result,
                frame=frame,
                decode_ms=processed.processing_time_ms,
                pipeline_start=pipeline_start,
                detections=detections,
                queue_wait_ms=queue_wait_ms,
            )
            # 11.1 결함 수정 (2026-07-18): 반사가 억제되었거나 전송 실패(연결 끊김 등)면
            # 후속 인지 태스크를 예약하지 않는다. 이전에는 성공 여부와 무관하게 항상
            # 800ms 후 인지 가이드를 예약해, 억제된 반사에도 불필요한 RAG/LLM/TTS 부하가
            # 발생했다(C-05).
            if sent_ok:
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

    async def _reconcile_near_episode(self, device_id: str, detections: list[Detection]) -> None:
        """직전에 열려 있던 Near episode의 track이 이번 프레임에서 이탈/소실됐는지 확인한다.

        2026-07-18 거리 정책 SSOT: Near episode는 enter 이후 명시적 reflex_clear로만
        종료된다(프레임마다 반복되는 독립 이벤트가 아니다). 이 메서드는 reflex 스트림의
        모든 프레임(반사가 발동하지 않은 프레임 포함)에서 호출되어, 활성 track이 더 이상
        near 구역에 없으면 즉시 clear를 내보낸다.
        """
        active_track = Alert_suppressor.peek_active_near_track(device_id)
        if active_track is None:
            return
        near_track_ids = {
            (det.track_id or "unknown")
            for det in detections
            if det.effective_distance_zone == "near"
        }
        if active_track in near_track_ids:
            return
        Alert_suppressor.end_near_episode(device_id)
        await self._send_reflex_clear(device_id, active_track, reason="zone_exit")

    async def _send_reflex_clear(self, device_id: str, track_id: str, reason: str) -> None:
        """Near episode 종료를 단말에 알린다. 단말은 해당 track의 반사 출력을 즉시 정지한다."""
        clear = ReflexClear(
            event_id="",
            alert_id="high_obstacle",
            track_id=None if track_id == "unknown" else track_id,
            alert_source="object",
            reason=reason,
            ts=now_ts(),
        )
        payload = {
            "type": "reflex_clear",
            "event_id": clear.event_id,
            "alert_id": clear.alert_id,
            "track_id": clear.track_id,
            "alert_source": clear.alert_source,
            "reason": clear.reason,
            "policy_version": clear.policy_version,
            "ts": clear.ts,
        }
        try:
            await manager.send_json(device_id, payload)
            logger.info(
                f"[DetectionConsumer] reflex_clear 전송: "
                f"device_id={device_id}, track_id={track_id}, reason={reason}"
            )
        except Exception as e:
            logger.error(f"[DetectionConsumer] reflex_clear 전송 실패: device_id={device_id}, {e}")

    async def _send_reflex_alert(
        self,
        device_id: str,
        alert: ReflexAlert,
        frame: np.ndarray | None = None,
        decode_ms: float = 0.0,
        pipeline_start: float | None = None,
        detections: list | None = None,
        queue_wait_ms: float = 0.0,
    ) -> bool:
        """반사 알림을 WebSocket 고우선 채널로 즉시 전송 (LLM/RAG 미경유).

        P0-1 (2026-07-17): 재무장 정책 적용.
        - 억제 키: {alert_source}:{track_id}:{distance_band}
        - 동일 키 TTL(5s) + device 단위 최소 쿨다운(1.5s) + 밴드 악화 재발화
        - near(<=0.6m) 햅틱+비프는 TTL 억제 제외, 500ms 스로틀만
        frame은 전송 성사 후 백그라운드 로그 태스크에서만 저장한다(반사 지연 무영향).

        반환값: 실제로 전송(억제되지 않고 WebSocket send 성공)했으면 True. 호출부는
        이 값이 True일 때만 800ms 후속 인지 태스크를 예약한다(11.1 결함 수정).
        """
        is_near = alert.distance <= 0.6
        if not await Alert_suppressor.should_emit_reflex(
            device_id=device_id,
            track_id=alert.track_id,
            distance_band=alert.distance_band,
            is_near=is_near,
            alert_source=alert.alert_source,
        ):
            logger.debug(
                f"[DetectionConsumer] 반사 알림 억제(재무장 정책): "
                f"device_id={device_id}, track_id={alert.track_id}, "
                f"band={alert.distance_band}, near={is_near}"
            )
            return False

        # 2026-07-18: 일반 객체(Near) 반사만 episode enter/update 상태를 갖는다.
        # head_level/surface는 순간 이벤트이므로 episode 상태를 갱신하지 않는다.
        if alert.alert_source == "object":
            alert.event_state = Alert_suppressor.begin_or_continue_near_episode(
                device_id, alert.track_id
            )

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
            "distance_band": alert.distance_band,
            "alert_source": alert.alert_source,
            "event_state": alert.event_state,
            "estimated_distance_m": alert.estimated_distance_m,
            "policy_version": alert.policy_version,
        }
        try:
            sent = await manager.send_json(device_id, payload)
            if not sent:
                logger.warning(
                    f"[DetectionConsumer] 반사 알림 미전송: "
                    f"device_id={device_id}, alert_id={alert.alert_id}, websocket=disconnected"
                )
                return False
            await Alert_suppressor.mark_reflex_sent(
                device_id=device_id,
                track_id=alert.track_id,
                distance_band=alert.distance_band,
                alert_source=alert.alert_source,
            )
            logger.info(
                f"[DetectionConsumer] 반사 알림 전송: "
                f"device_id={device_id}, alert_id={alert.alert_id}, "
                f"track_id={alert.track_id}, band={alert.distance_band}"
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
            return True
        except Exception as e:
            logger.error(f"[DetectionConsumer] 반사 알림 전송 실패: device_id={device_id}, {e}")
            return False

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
        """반사 경보(비프/햅틱) 발동 800ms 후 인지 가이드(LLM TTS 우회)를 연계 트리거한다.

        P1-1 (2026-07-17): 단일 객체 + 방향 확정 시 avoidance 템플릿으로 즉시 우회 방향 안내.
        LangGraph 전체(L1/L2/L3)를 돌리는 수 초 소요를 없애 반사 후속 안내 지연(S7)을 해소한다.
        다중 객체/방향 불확정 시 기존 LangGraph 경로로 폴백한다(안전 측면).
        """
        await asyncio.sleep(0.8)  # 반사 진동/비프음 인지용 딜레이

        # P1-1: avoidance fast lane 우선 시도 (단일 객체 + 방향 확정)
        from server.orchestration.avoidance import (
            build_avoidance_guidance,
            can_use_avoidance_fast_lane,
        )

        preset_guidance: str | None = None
        if can_use_avoidance_fast_lane(alert, detections):
            preset_guidance = build_avoidance_guidance(alert)
            logger.info(
                f"[DetectionConsumer] avoidance fast lane: device_id={device_id}, "
                f"direction={alert.direction}, guidance='{preset_guidance}'"
            )

        # 7.4 목표 정책 (2026-07-18): 일반 Near 존재 안내("반사와 같은 사실을 TTS로 반복")는
        # 금지한다. 회피 방향이 명확한 post_reflex 안내(avoidance fast lane)만 허용하고,
        # 그마저 불가능하면(다중 객체·방향 불확정) 후속 인지 안내 자체를 생략한다.
        if preset_guidance is None:
            logger.debug(
                f"[DetectionConsumer] avoidance 불가 - post_reflex 인지 안내 생략: "
                f"device_id={device_id}, alert_id={alert.alert_id}"
            )
            return

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

        # 인지 경로 전송 (preset_guidance가 있으면 LangGraph 우회)
        await self._send_cognitive_guide(
            device_id=device_id,
            result=cognitive_res,
            frame=frame,
            decode_ms=decode_ms,
            pipeline_start=pipeline_start,
            departure_confirmed=False,
            preset_guidance_text=preset_guidance,
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
        preset_guidance_text: str | None = None,
    ) -> None:
        """인지 결과를 오케스트레이션/TTS와 연결해 guide 메시지로 전송한다.

        P1-1 (2026-07-17): preset_guidance_text가 주어지면 LangGraph(run_orchestrator)를
        우회하고 그 텍스트로 즉시 TTS 합성 후 전송한다 (반사 후속 avoidance fast lane).
        """

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

        # T3-S (2026-07-18): 서버 차원에서 STT 상호작용 중이면 인지 가이드 발행을 억제한다.
        # 반사 경로는 이 게이트를 거치지 않는다(비협상). 클라이언트 audioEngine 우선순위
        # 조정자가 1차 방어선이며, 서버 억제는 연산 낭비 제거용 이중 방어.
        if manager.is_stt_active(device_id):
            logger.debug(
                f"[DetectionConsumer] STT 상호작용 중 - 인지 가이드 발행 억제: "
                f"device_id={device_id}"
            )
            return

        # T2-G (2026-07-18): 회랑/접근 필터. 발화 가치 게이트 앞단에서 "처음부터 발화할
        # 가치가 있는가"를 먼저 판정한다. 안전 예외(보도 이탈, 고위험, 접근 객체,
        # 유의미 노면)는 통과시키고 측면·원거리·정적 저위험만 무발화한다.
        primary_det = (
            max(result.detections, key=lambda d: d.confidence) if result.detections else None
        )
        distance_class = ""
        if primary_det is not None and frame is not None:
            distance_class = estimate_distance(
                primary_det.bbox,
                frame.shape[1],
                frame.shape[0],
                primary_det.class_name,
            )
        if not self._is_speech_worthy(
            primary_det,
            frame,
            distance_class,
            result.risk_hint,
            departure_confirmed,
        ):
            logger.debug(
                f"[DetectionConsumer] 회랑/접근 필터 탈락 - 인지 가이드 무발화: "
                f"device_id={device_id}, risk_hint={result.risk_hint}, distance={distance_class}"
            )
            return

        # P1-2 (2026-07-17): 발화 가치(Utterance Value) 게이트.
        # 동일 상황(객체+표면 서명 동일) 반복 안내는 COGNITIVE_UTTERANCE_COOLDOWN_S 동안
        # TTS 합성 생략. 새 객체/표면 변화/보도 이탈/쿨다운 경과 시에만 발화.
        # [면접 대비 주석] 인지 가이드는 LangGraph+RAG+TTS로 수 초 소요되므로, 동일 상황 반복을
        # 사전 차단해 CPU 점유와 중복 안내를 동시에 줄인다(S5/S6).
        if not self._has_utterance_value(device_id, result, departure_confirmed):
            logger.debug(
                f"[DetectionConsumer] 인지 가이드 발화 가치 없음(동일 상황 반복) - "
                f"TTS 합성 생략: device_id={device_id}"
            )
            return

        # 쿨다운 사전 검사(빠른 경로): 직전 "전송"으로부터 얼마 지나지 않았다면 굳이
        # 오케스트레이션/TTS(수 초 소요)를 새로 돌리지 않고 조기 반환한다. 실제 간격
        # 보장은 아래 전송 직전 재검사에서 확정하므로 여기서는 슬롯을 갱신하지 않는다.
        if time.monotonic() - self._last_guide_ts.get(
            device_id, 0.0
        ) < self._required_guide_gap_sec(device_id, primary_det, frame, distance_class):
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
        # T2-G: 위 회랑/접근 필터에서 이미 primary_det/distance_class를 계산했으므로 재사용.
        rag_context = ""
        clock_direction = ""
        object_ko = ""
        rag_start = time.perf_counter()
        try:
            retriever = get_default_retriever()
            if primary_det is not None:
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
                    if not distance_class:
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
            if preset_guidance_text is not None:
                # P1-1 (2026-07-17): avoidance fast lane - LangGraph 우회, preset 텍스트로 즉시 합성.
                orch_result = {
                    "guidance_text": preset_guidance_text,
                    "verified": True,
                    "used_fast_lane": False,
                    "retry_count": 0,
                    "total_latency_ms": 0.0,
                    "risk_level": "high",
                    "direction": preset_guidance_text,
                }
            else:
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
            # P1-2: 발화 가치 게이트용 상황 서명 갱신 (다음 동일 상황 판정 기준).
            self._last_guide_signature[device_id] = self._compute_cognitive_signature(
                result, departure_confirmed
            )

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
