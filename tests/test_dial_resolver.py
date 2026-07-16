import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pytest

from server.stt.dial_resolver import resolve_dial_action


@pytest.mark.asyncio
async def test_resolve_dial_action_emergency() -> None:
    result = await resolve_dial_action("dev-001", "119로 연결해줘")
    assert result is not None
    assert result["source"] == "stt-dial-emergency"
    assert result["dial_action"]["phone_number"] == "119"


@pytest.mark.asyncio
async def test_resolve_dial_action_not_intent_returns_none() -> None:
    result = await resolve_dial_action("dev-001", "보행훈련은 어디서 받을 수 있나요?")
    assert result is None
