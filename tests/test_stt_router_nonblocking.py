import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
import io
import time

import pytest
from fastapi import UploadFile

import server.api.stt_router as stt_router_module
from server.stt.stt_schema import SttTranscribeResult

# ============================================================
# 테스트 파일 역할
# ============================================================
# server/api/stt_router.py의 /transcribe, /transcribe-and-guide가 동기 블로킹 함수
# SttService.transcribe_file()을 asyncio.to_thread 없이 직접 호출해, 처리 중 이벤트
# 루프 전체(다른 모든 WS 연결 포함)가 멈추던 결함(2026-07-09 실서버 구동으로 발견)의
# 회귀를 방지한다. 진짜 blocking 여부를 증명하기 위해 time.sleep으로 느린 전사를
# 흉내내고, 그동안 별도 asyncio 태스크(하트비트 카운터)가 계속 진행되는지로 검증한다.


def _slow_transcribe_file(cls, saved_path, model_name):
    time.sleep(0.3)  # 실제 whisper 추론처럼 동기적으로 블로킹
    return SttTranscribeResult(
        model_name="faster-whisper-medium",
        text="느린 전사 완료",
        language="ko",
        duration=0.3,
        segments=[],
        has_input=True,
        saved_file="dummy.wav",
    )


async def _make_upload_file() -> UploadFile:
    return UploadFile(filename="dummy.wav", file=io.BytesIO(b"RIFF....WAVEfmt "))


@pytest.mark.asyncio
async def test_transcribe_does_not_block_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        stt_router_module.SttService, "transcribe_file", classmethod(_slow_transcribe_file)
    )

    heartbeat_ticks = 0

    async def _heartbeat_counter() -> None:
        nonlocal heartbeat_ticks
        while True:
            await asyncio.sleep(0.02)
            heartbeat_ticks += 1

    heartbeat_task = asyncio.create_task(_heartbeat_counter())
    try:
        upload = await _make_upload_file()
        result = await stt_router_module.transcribe_audio(audio=upload, model_name=None)
    finally:
        heartbeat_task.cancel()

    assert result.text == "느린 전사 완료"
    # 0.3초짜리 블로킹 구간 동안 0.02초 간격 하트비트가 여러 번 돌았어야
    # 이벤트 루프가 멈추지 않았다고 볼 수 있다(블로킹이었다면 0에 가까웠을 것).
    assert heartbeat_ticks >= 5, f"이벤트 루프가 블로킹된 것으로 보임 (ticks={heartbeat_ticks})"


@pytest.mark.asyncio
async def test_transcribe_and_guide_does_not_block_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        stt_router_module.SttService, "transcribe_file", classmethod(_slow_transcribe_file)
    )

    async def _fake_invoke(self, stt_result):
        return {"guidance_text": "안내문", "used_fallback_llm": True, "source": "stt-bridge"}

    monkeypatch.setattr(stt_router_module.SttToLlmBridge, "invoke_existing_llm", _fake_invoke)

    heartbeat_ticks = 0

    async def _heartbeat_counter() -> None:
        nonlocal heartbeat_ticks
        while True:
            await asyncio.sleep(0.02)
            heartbeat_ticks += 1

    heartbeat_task = asyncio.create_task(_heartbeat_counter())
    try:
        upload = await _make_upload_file()
        result = await stt_router_module.transcribe_and_guide(audio=upload, model_name=None)
    finally:
        heartbeat_task.cancel()

    assert result.guidance_text == "안내문"
    assert heartbeat_ticks >= 5, f"이벤트 루프가 블로킹된 것으로 보임 (ticks={heartbeat_ticks})"
