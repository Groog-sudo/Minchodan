import asyncio
import logging
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.bus.redis_client import RedisBus, redis_bus
from server.capture.frame_decoder import ProcessedFrame

logger = logging.getLogger(__name__)

# P0-2 (2026-07-17): 반사 큐는 latest-frame-wins로 얕게 잡아 지연 드리프트 방지.
# 큐가 가득 차면 _push_to_queue가 oldest를 drop하므로 maxsize=2면 매 프레임 latest가 유지됨.
# 인지는 1~2fps 특성상 소량 버퍼(4)로 충분. 환경변수로 오버라이드 가능.
REFLEX_QUEUE_MAXSIZE = int(os.getenv("REFLEX_QUEUE_MAXSIZE", "2"))
COGNITIVE_QUEUE_MAXSIZE = int(os.getenv("COGNITIVE_QUEUE_MAXSIZE", "6"))
# 하위 호환: 기존 QUEUE_MAXSIZE 참조 유지 (두 분리 상수의 최댓값)
QUEUE_MAXSIZE = max(REFLEX_QUEUE_MAXSIZE, COGNITIVE_QUEUE_MAXSIZE)
VALID_STREAMS = {"reflex", "cognitive"}


class StreamSplitter:
    """이중 경로 분기기 (반사/인지).

    이중 경로 물리 분리 원칙 (비협상):
        반사 경로에는 RAG / LLM / 실시간 TTS 모듈을 절대 임포트하지 않습니다.
        본 모듈은 server.bus (Redis 메타데이터 발행) 에만 의존합니다.

    프레임 원본은 asyncio.Queue로 in-process 전달하고,
    Redis에는 추적 메타데이터만 발행합니다 (architecture.md 6.1절 준수).
    """

    def __init__(
        self,
        reflex_queue: asyncio.Queue[ProcessedFrame],
        cognitive_queue: asyncio.Queue[ProcessedFrame],
        bus: RedisBus = redis_bus,
    ):
        self.reflex_queue = reflex_queue
        self.cognitive_queue = cognitive_queue
        self.bus = bus
        # 2026-07-21: 디코드 전 스킵·ack 백프레셔용 적체/드롭 계측
        self.queue_drop_count: dict[str, int] = {"reflex": 0, "cognitive": 0}
        self.ingest_skip_count: dict[str, int] = {"reflex": 0, "cognitive": 0}

    def queue_depth(self, stream: str) -> int:
        queue = self._select_queue(stream if stream in VALID_STREAMS else "cognitive")
        return queue.qsize()

    def is_ingest_busy(self, stream: str) -> bool:
        """소비자가 따라가지 못해 큐가 가득이면 True (디코드 전 스킵 판단용)."""
        queue = self._select_queue(stream if stream in VALID_STREAMS else "cognitive")
        return queue.full()

    def note_ingest_skip(self, stream: str) -> None:
        key = stream if stream in VALID_STREAMS else "cognitive"
        self.ingest_skip_count[key] = self.ingest_skip_count.get(key, 0) + 1

    async def route_frame(self, processed: ProcessedFrame) -> None:
        """스트림 타입에 따라 asyncio.Queue로 분기하고 Redis에 메타데이터 발행.

        알 수 없는 stream 값은 cognitive_queue로 폴백 (안전 폴백).
        Redis 연결 실패 시에도 Queue push는 유지 (파이프라인 영속성).
        """
        queue = self._select_queue(processed.stream)
        await self._push_to_queue(queue, processed)
        await self._publish_metadata(processed)

    def _select_queue(self, stream: str) -> asyncio.Queue[ProcessedFrame]:
        if stream == "reflex":
            return self.reflex_queue
        if stream == "cognitive":
            return self.cognitive_queue
        logger.warning(f"[StreamSplitter] 알 수 없는 stream={stream}, cognitive로 폴백")
        return self.cognitive_queue

    async def _push_to_queue(
        self,
        queue: asyncio.Queue[ProcessedFrame],
        processed: ProcessedFrame,
    ) -> None:
        try:
            queue.put_nowait(processed)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
                queue.put_nowait(processed)
                stream = processed.stream if processed.stream in VALID_STREAMS else "cognitive"
                self.queue_drop_count[stream] = self.queue_drop_count.get(stream, 0) + 1
                logger.warning(
                    f"[StreamSplitter] 큐 가득참, 오래된 프레임 drop: "
                    f"event_id={processed.event_id}, stream={processed.stream}"
                )
            except asyncio.QueueEmpty:
                queue.put_nowait(processed)
            except Exception as e:
                logger.error(
                    f"[StreamSplitter] 큐 push 실패, 프레임 drop: "
                    f"event_id={processed.event_id}, {e}"
                )

    async def _publish_metadata(self, processed: ProcessedFrame) -> None:
        """Redis에 메타데이터만 발행 (프레임 원본 비적재, architecture.md 6.1절)."""
        payload = {
            "event_id": processed.event_id,
            "device_id": processed.device_id,
            "stream": processed.stream,
            "ts": str(processed.ts),
            "size_kb": str(round(processed.size_kb, 2)),
            "decode_ms": str(round(processed.processing_time_ms, 2)),
        }
        try:
            msg_id = await self.bus.publish_event("risk.events", payload)
            if msg_id is None:
                logger.warning(
                    f"[StreamSplitter] Redis 발행 실패 (연결 끊김): event_id={processed.event_id}"
                )
        except Exception as e:
            logger.warning(
                f"[StreamSplitter] Redis 발행 예외, Queue push는 유지: "
                f"event_id={processed.event_id}, {e}"
            )


_default_splitter: StreamSplitter | None = None


def get_default_splitter() -> StreamSplitter:
    """모듈 수준 싱글턴. 1단계 작업자가 호출하여 decode_frame과 연결."""
    global _default_splitter
    if _default_splitter is None:
        _default_splitter = StreamSplitter(
            reflex_queue=asyncio.Queue(maxsize=REFLEX_QUEUE_MAXSIZE),
            cognitive_queue=asyncio.Queue(maxsize=COGNITIVE_QUEUE_MAXSIZE),
        )
    return _default_splitter
