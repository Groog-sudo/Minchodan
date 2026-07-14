import io
import os
import sys
import wave
from contextlib import asynccontextmanager
from datetime import UTC, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.db.models import Base, DetectionGuidanceLog, StreamType
from server.db.repositories import DetectionGuidanceLogRepository
from server.tts.realtime_tts import DEFAULT_SPEED, RealtimeTTS

# ============================================================
# 테스트 파일 역할
# ============================================================
# TTS 캐시 프리워밍(DB 이력 기반) 기능을 검증한다.
# 1) DetectionGuidanceLogRepository.list_frequent_tts_texts: 빈도 집계/필터/정렬
# 2) list_frequent_tts_texts(서비스 함수): 세션 팩토리 배선
# 3) RealtimeTTS.prewarm: 합성 캐시 채우기, 개별 실패 격리


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _seed(session: AsyncSession, tts_text: str, stream_type: StreamType, count: int) -> None:
    for _ in range(count):
        session.add(
            DetectionGuidanceLog(
                detected_at=datetime.now(UTC),
                stream_type=stream_type,
                detected_objects_json="[]",
                tts_text=tts_text,
            )
        )
    await session.commit()


@pytest.mark.asyncio
async def test_list_frequent_tts_texts_orders_by_count_and_filters_cognitive(
    db_session: AsyncSession,
) -> None:
    await _seed(db_session, "왼쪽에 자전거 주의", StreamType.COGNITIVE, 5)
    await _seed(db_session, "전방 보행자 주의", StreamType.COGNITIVE, 3)
    await _seed(db_session, "한 번만 나온 문장", StreamType.COGNITIVE, 1)
    # 반사 경로 로그는 실제 합성 문장이 아닌 클립 플레이스홀더라 결과에서 제외돼야 한다.
    await _seed(db_session, "[반사 클립] high_front.wav", StreamType.REFLEX, 10)

    repo = DetectionGuidanceLogRepository(db_session)
    texts = await repo.list_frequent_tts_texts(min_count=2, limit=10)

    assert texts == ["왼쪽에 자전거 주의", "전방 보행자 주의"]


@pytest.mark.asyncio
async def test_list_frequent_tts_texts_respects_limit(db_session: AsyncSession) -> None:
    await _seed(db_session, "문장 A", StreamType.COGNITIVE, 5)
    await _seed(db_session, "문장 B", StreamType.COGNITIVE, 4)
    await _seed(db_session, "문장 C", StreamType.COGNITIVE, 3)

    repo = DetectionGuidanceLogRepository(db_session)
    texts = await repo.list_frequent_tts_texts(min_count=1, limit=2)

    assert texts == ["문장 A", "문장 B"]


@pytest.mark.asyncio
async def test_service_list_frequent_tts_texts_uses_sessionmaker_factory(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed(db_session, "문장 A", StreamType.COGNITIVE, 3)

    from server.services import detection_guidance_log_service as service_module

    @asynccontextmanager
    async def _fake_sessionmaker():
        yield db_session

    monkeypatch.setattr(service_module, "async_sessionmaker_factory", _fake_sessionmaker)

    texts = await service_module.list_frequent_tts_texts(min_count=1, limit=10)
    assert texts == ["문장 A"]


class _FakeTTSService:
    """합성 없이 고정 WAV 바이트를 반환하는 테스트용 더블. 특정 텍스트만 실패를 흉내낸다."""

    FAIL_TEXT = "합성실패문장"

    async def generate(self, text: str, voice: str, speed: float = 1.0) -> bytes | None:
        if text == self.FAIL_TEXT:
            raise RuntimeError("synthetic failure")
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 100)
        return buf.getvalue()


@pytest.mark.asyncio
async def test_prewarm_fills_cache_and_skips_failures() -> None:
    tts = RealtimeTTS(tts_service=_FakeTTSService())

    warmed = await tts.prewarm(["안내문장1", "안내문장2", _FakeTTSService.FAIL_TEXT, "  ", ""])

    assert warmed == 2
    assert len(tts._cache) == 2
    assert ("안내문장1", "ko", DEFAULT_SPEED) in tts._cache
    assert ("안내문장2", "ko", DEFAULT_SPEED) in tts._cache


@pytest.mark.asyncio
async def test_prewarm_warns_when_exceeding_cache_limit(caplog: pytest.LogCaptureFixture) -> None:
    tts = RealtimeTTS(tts_service=_FakeTTSService())
    texts = [f"문장{i}" for i in range(tts.CACHE_MAX_ENTRIES + 1)]

    with caplog.at_level("WARNING"):
        warmed = await tts.prewarm(texts)

    # 전부 합성엔 성공하지만(warmed == 요청 건수), FIFO 축출로 캐시엔 상한만큼만 남는다.
    assert warmed == len(texts)
    assert len(tts._cache) == tts.CACHE_MAX_ENTRIES
    assert any("캐시 상한" in r.message for r in caplog.records)
