# -*- coding: utf-8 -*-
"""Ollama 스트리밍 설정과 응답 청크 병합 동작을 검증합니다."""

import contextlib
import sys
from unittest.mock import AsyncMock

import pytest

from server.orchestration.llm_client_factory import (
    LLMClientFactory,
    SimpleOllamaClient,
    _read_bool_env,
)

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")


async def _stream_parts():
    for content in ("좌측", "으로 ", "피하세요"):
        yield {"message": {"content": content}}


@pytest.mark.asyncio
async def test_ollama_stream_chunks_are_joined_without_sentence_split():
    client = SimpleOllamaClient.__new__(SimpleOllamaClient)
    client.model_name = "gemma4:e4b"
    client.base_url = "http://localhost:11434"
    client.stream = True
    client.split_by_sentence = False
    client.client = AsyncMock()
    client.client.chat.return_value = _stream_parts()

    response = await client.ainvoke([{"role": "user", "content": "안내"}])

    assert response.content == "좌측으로 피하세요"
    client.client.chat.assert_awaited_once_with(
        model="gemma4:e4b",
        messages=[{"role": "user", "content": "안내"}],
        options={"temperature": 0.3, "num_predict": 100},
        think=False,
        stream=True,
    )


def test_ollama_factory_uses_requested_stream_settings(monkeypatch):
    created = {}

    class FakeOllamaClient:
        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setenv("OLLAMA_STREAM", "true")
    monkeypatch.setenv("OLLAMA_SPLIT_BY_SENTENCE", "false")
    monkeypatch.setattr(
        "server.orchestration.llm_client_factory.SimpleOllamaClient",
        FakeOllamaClient,
    )
    monkeypatch.setattr(LLMClientFactory, "_ollama", None)

    LLMClientFactory.get_ollama()

    assert created["stream"] is True
    assert created["split_by_sentence"] is False
    monkeypatch.setattr(LLMClientFactory, "_ollama", None)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("1", True), ("false", False), ("0", False)],
)
def test_read_bool_env(monkeypatch, value, expected):
    monkeypatch.setenv("OLLAMA_STREAM", value)
    assert _read_bool_env("OLLAMA_STREAM", not expected) is expected
