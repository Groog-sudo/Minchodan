import base64
import sys
import time
from unittest.mock import AsyncMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import cv2
import numpy as np
import pytest

from server.bus.redis_client import RedisBus
from server.capture import ProcessedFrame, StreamSplitter, decode_frame, get_default_splitter
from server.capture.stream_splitter import VALID_STREAMS


def make_jpeg_b64(width: int = 640, height: int = 480) -> str:
    """테스트용 JPEG base64 문자열 생성."""
    frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    assert ok, "JPEG 인코딩 실패"
    return base64.b64encode(buf.tobytes()).decode("ascii")


def make_oversized_jpeg_b64() -> str:
    """500KB 초과 JPEG base64 생성."""
    frame = np.random.randint(0, 256, (2000, 2000, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok, "JPEG 인코딩 실패"
    return base64.b64encode(buf.tobytes()).decode("ascii")


def make_undersized_b64() -> str:
    """1KB 미만 base64 생성."""
    return base64.b64encode(b"\x00" * 512).decode("ascii")


def make_payload(
    b64: str,
    stream: str = "cognitive",
    event_id: str = "evt-test",
    device_id: str = "dev-test",
    ts: int = 1719216000000,
) -> dict:
    return {
        "event_id": event_id,
        "device_id": device_id,
        "ts": ts,
        "frame_id": 1,
        "stream": stream,
        "thumbnail_jpeg_b64": b64,
    }


@pytest.fixture
def valid_payload() -> dict:
    return make_payload(make_jpeg_b64())


@pytest.fixture
def mock_redis_bus() -> RedisBus:
    bus = RedisBus(url="redis://localhost:6379")
    bus.publish_event = AsyncMock(return_value="mock-msg-id")  # type: ignore[method-assign]
    return bus


@pytest.fixture
def splitter(mock_redis_bus: RedisBus) -> StreamSplitter:
    import asyncio

    return StreamSplitter(
        reflex_queue=asyncio.Queue(maxsize=100),
        cognitive_queue=asyncio.Queue(maxsize=100),
        bus=mock_redis_bus,
    )


class TestDecodeFrame:
    """TC-CAP-001 ~ TC-CAP-005: 프레임 디코딩 검증."""

    @pytest.mark.asyncio
    async def test_valid_frame(self, valid_payload: dict):
        """TC-CAP-001: 유효 프레임 디코딩."""
        result = await decode_frame(valid_payload)
        assert result is not None
        assert result.frame.shape == (640, 640, 3)
        assert result.processing_time_ms > 0
        assert result.event_id == "evt-test"
        assert result.device_id == "dev-test"
        assert result.stream == "cognitive"
        assert result.ts == 1719216000000
        assert result.original_size == (480, 640)

    @pytest.mark.asyncio
    async def test_timestamp_fallback(self):
        """ts 필드가 없거나 잘못되어 ISO timestamp 필드로 복원되는지 검증."""
        payload = make_payload(make_jpeg_b64(), ts=None)  # type: ignore[arg-type]
        payload["timestamp"] = "2026-06-28T09:00:00.000Z"
        result = await decode_frame(payload)
        assert result is not None
        assert result.ts > 0

    @pytest.mark.asyncio
    async def test_empty_base64(self):
        """TC-CAP-002: 빈 base64 처리."""
        payload = make_payload("")
        result = await decode_frame(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_none_base64(self):
        """TC-CAP-002 변형: None base64 처리."""
        payload = make_payload("cognitive")  # type: ignore[arg-type]
        payload["thumbnail_jpeg_b64"] = None
        result = await decode_frame(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_oversized_frame(self):
        """TC-CAP-003: 과대 프레임 거부 (> 500KB)."""
        payload = make_payload(make_oversized_jpeg_b64())
        result = await decode_frame(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_undersized_frame(self):
        """TC-CAP-004: 과소 프레임 거부 (< 1KB)."""
        payload = make_payload(make_undersized_b64())
        result = await decode_frame(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_decode_latency(self):
        """TC-CAP-005: 캡처수신 지연 평균 < 50ms (100회 반복 측정)."""
        b64 = make_jpeg_b64()
        latencies: list[float] = []
        for i in range(100):
            payload = make_payload(b64, event_id=f"evt-lat-{i}")
            start = time.perf_counter()
            result = await decode_frame(payload)
            elapsed = (time.perf_counter() - start) * 1000
            assert result is not None
            latencies.append(elapsed)
        avg_ms = sum(latencies) / len(latencies)
        assert avg_ms < 50.0, f"평균 디코딩 지연 {avg_ms:.2f}ms >= 50ms"

    @pytest.mark.asyncio
    async def test_reflex_stream_passthrough(self):
        """stream 필드 reflex가 ProcessedFrame에 전달되는지 확인."""
        payload = make_payload(make_jpeg_b64(), stream="reflex")
        result = await decode_frame(payload)
        assert result is not None
        assert result.stream == "reflex"

    @pytest.mark.asyncio
    async def test_unknown_stream_falls_back(self):
        """알 수 없는 stream 값도 디코딩 자체는 정상 수행 (분기는 splitter 책임)."""
        payload = make_payload(make_jpeg_b64(), stream="unknown")
        result = await decode_frame(payload)
        assert result is not None
        assert result.stream == "unknown"


class TestStreamSplitter:
    """TC-CAP-006 ~ TC-CAP-009, TC-PATH-007: 스트림 분기 검증."""

    @pytest.mark.asyncio
    async def test_reflex_routing(self, splitter: StreamSplitter, valid_payload: dict):
        """TC-CAP-006: reflex 스트림 분기."""
        processed = await decode_frame(valid_payload)
        assert processed is not None
        processed.stream = "reflex"

        await splitter.route_frame(processed)

        assert splitter.reflex_queue.qsize() == 1
        assert splitter.cognitive_queue.qsize() == 0
        queued = splitter.reflex_queue.get_nowait()
        assert queued.event_id == processed.event_id

    @pytest.mark.asyncio
    async def test_cognitive_routing(self, splitter: StreamSplitter, valid_payload: dict):
        """TC-CAP-007: cognitive 스트림 분기."""
        processed = await decode_frame(valid_payload)
        assert processed is not None

        await splitter.route_frame(processed)

        assert splitter.cognitive_queue.qsize() == 1
        assert splitter.reflex_queue.qsize() == 0
        queued = splitter.cognitive_queue.get_nowait()
        assert queued.event_id == processed.event_id

    @pytest.mark.asyncio
    async def test_metadata_only_no_frame_in_payload(
        self, splitter: StreamSplitter, valid_payload: dict, mock_redis_bus: RedisBus
    ):
        """TC-CAP-008: Redis 발행 페이로드에 frame/frame_hex 키 없음."""
        processed = await decode_frame(valid_payload)
        assert processed is not None

        await splitter.route_frame(processed)

        mock_redis_bus.publish_event.assert_called_once()  # type: ignore[attr-defined]
        call_args = mock_redis_bus.publish_event.call_args  # type: ignore[attr-defined]
        payload = call_args.kwargs.get("payload") or call_args.args[1]
        assert "frame" not in payload
        assert "frame_hex" not in payload
        assert "event_id" in payload
        assert "device_id" in payload
        assert "stream" in payload
        assert "ts" in payload
        assert "size_kb" in payload
        assert "decode_ms" in payload

    @pytest.mark.asyncio
    async def test_redis_failure_queue_still_pushed(self, valid_payload: dict):
        """TC-CAP-009: Redis 연결 실패 시에도 Queue push는 정상 동작."""
        import asyncio

        failing_bus = RedisBus(url="redis://invalid:9999")
        failing_bus.publish_event = AsyncMock(side_effect=RuntimeError("redis down"))  # type: ignore[method-assign]
        splitter = StreamSplitter(
            reflex_queue=asyncio.Queue(maxsize=100),
            cognitive_queue=asyncio.Queue(maxsize=100),
            bus=failing_bus,
        )

        processed = await decode_frame(valid_payload)
        assert processed is not None

        await splitter.route_frame(processed)

        assert splitter.cognitive_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_reflex_does_not_affect_cognitive(
        self, splitter: StreamSplitter, valid_payload: dict
    ):
        """TC-PATH-007: reflex 분기 시 cognitive Queue 영향 없음."""
        processed = await decode_frame(valid_payload)
        assert processed is not None
        processed.stream = "reflex"

        await splitter.route_frame(processed)

        assert splitter.reflex_queue.qsize() == 1
        assert splitter.cognitive_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_unknown_stream_routes_to_cognitive(
        self, splitter: StreamSplitter, valid_payload: dict
    ):
        """알 수 없는 stream 값은 cognitive_queue로 폴백."""
        processed = await decode_frame(valid_payload)
        assert processed is not None
        processed.stream = "invalid_stream"

        await splitter.route_frame(processed)

        assert splitter.cognitive_queue.qsize() == 1
        assert splitter.reflex_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_queue_full_drops_oldest(self, mock_redis_bus: RedisBus):
        """큐 가득 참 시 오래된 프레임 drop 후 최신 프레임 유지."""
        import asyncio

        small_queue = asyncio.Queue(maxsize=2)
        splitter = StreamSplitter(
            reflex_queue=small_queue,
            cognitive_queue=asyncio.Queue(maxsize=100),
            bus=mock_redis_bus,
        )

        for i in range(3):
            processed = ProcessedFrame(
                event_id=f"evt-full-{i}",
                device_id="dev-test",
                stream="reflex",
                frame=np.zeros((640, 640, 3), dtype=np.uint8),
                original_size=(480, 640),
                size_kb=30.0,
                processing_time_ms=1.0,
                ts=0,
            )
            await splitter.route_frame(processed)

        assert small_queue.qsize() == 2
        first = small_queue.get_nowait()
        second = small_queue.get_nowait()
        assert first.event_id == "evt-full-1"
        assert second.event_id == "evt-full-2"


class TestDualPathDiscipline:
    """TC-PATH-006: 반사 스트림 RAG/LLM/TTS 임포트 금지 검증."""

    def test_no_rag_llm_tts_imports_in_stream_splitter(self):
        """stream_splitter.py에 RAG/LLM/TTS 모듈 import 문이 없어야 함."""
        import server.capture.stream_splitter as ss

        with open(ss.__file__, encoding="utf-8") as f:
            module_source = f.read()

        forbidden_patterns = [
            "from server.rag",
            "from server.orchestration",
            "from server.tts",
            "import server.rag",
            "import server.orchestration",
            "import server.tts",
            "LangGraph",
            "ChromaDB",
            "ChatOllama",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in module_source, (
                f"금지된 모듈 참조 발견: '{pattern}' in stream_splitter.py"
            )

    def test_valid_streams_constant(self):
        """VALID_STREAMS 상수가 reflex/cognitive만 포함하는지 확인."""
        assert {"reflex", "cognitive"} == VALID_STREAMS


class TestGetDefaultSplitter:
    """get_default_splitter 싱글턴 검증."""

    def test_singleton(self):
        """get_default_splitter() 호출 시 동일 인스턴스 반환."""
        s1 = get_default_splitter()
        s2 = get_default_splitter()
        assert s1 is s2

    def test_singleton_queues_exist(self):
        """싱글턴의 reflex/cognitive 큐가 존재하는지 확인."""
        splitter = get_default_splitter()
        assert splitter.reflex_queue is not None
        assert splitter.cognitive_queue is not None

    def test_singleton_queue_maxsize(self):
        """큐 maxsize가 100인지 확인 (백프레셔 정책)."""
        from server.capture.stream_splitter import QUEUE_MAXSIZE

        assert QUEUE_MAXSIZE == 100
