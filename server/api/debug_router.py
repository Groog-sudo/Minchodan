# -*- coding: utf-8 -*-
"""개발용 디버그 REST API.

문자/안내문 TTS를 연결된 모바일 앱으로 밀어 넣는 실험 엔드포인트를 제공한다.
APP_ENV=production 에서는 비활성화한다.
"""

from __future__ import annotations

import base64
import logging
import os
import sys
import time
from contextlib import suppress

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

if hasattr(sys.stdout, "reconfigure"):
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from server.api.session_manager import manager
from server.tts.realtime_tts import RealtimeTTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/debug", tags=["Debug"])

_DEFAULT_SMS_TEXT = (
    "새 문자가 도착했습니다. 엄마에게서. 오늘 저녁 몇 시에 오실 건가요?"
)


class SpeakToDeviceRequest(BaseModel):
    text: str = Field(default=_DEFAULT_SMS_TEXT, min_length=1)
    device_id: str | None = Field(
        default=None,
        description="대상 device_id. 생략 시 현재 연결된 첫 단말로 전송",
    )
    voice: str = "ko"
    speed: float = 0.85


def _debug_enabled() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() != "production"


@router.post("/speak-to-device")
async def speak_to_device(body: SpeakToDeviceRequest) -> dict:
    """서버 TTS로 합성한 WAV를 연결된 앱에 guide + binary로 전송한다."""
    if not _debug_enabled():
        raise HTTPException(status_code=404, detail="Not found")

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text가 비어 있습니다.")

    connected = manager.list_connected_device_ids()
    device_id = body.device_id or (connected[0] if connected else None)
    if not device_id:
        raise HTTPException(
            status_code=409,
            detail="연결된 단말이 없습니다. 앱 WebSocket 연결을 확인하세요.",
        )
    if not manager.is_connected(device_id):
        raise HTTPException(
            status_code=409,
            detail=f"device_id={device_id} 가 연결되어 있지 않습니다. connected={connected}",
        )

    tts = RealtimeTTS()
    b64_audio, duration_ms = await tts.synthesize(
        text=text, voice=body.voice, speed=body.speed
    )
    audio_bytes = base64.b64decode(b64_audio) if b64_audio else b""
    event_id = f"debug-sms-{int(time.time() * 1000)}"

    sent_json = await manager.send_json(
        device_id,
        {
            "type": "guide",
            "event_id": event_id,
            "stream": "cognitive",
            "guidance_text": text,
            "source": "debug_sms_tts",
            "transport": "binary" if audio_bytes else "none",
            "duration_ms": duration_ms,
        },
    )
    sent_bytes = False
    if audio_bytes:
        sent_bytes = await manager.send_bytes(device_id, audio_bytes)

    if not sent_json:
        raise HTTPException(
            status_code=502,
            detail=f"guide JSON 전송 실패: device_id={device_id}",
        )

    logger.info(
        "[DebugTTS] speak-to-device ok device_id=%s text_len=%s audio_bytes=%s duration_ms=%.0f",
        device_id,
        len(text),
        len(audio_bytes),
        duration_ms,
    )
    return {
        "ok": True,
        "device_id": device_id,
        "event_id": event_id,
        "text": text,
        "audio_bytes": len(audio_bytes),
        "duration_ms": duration_ms,
        "sent_bytes": sent_bytes,
        "connected_devices": connected,
        "fallback_hint": (
            None
            if audio_bytes
            else "서버 TTS 합성 실패 - 단말이 speakFallback으로 텍스트만 읽을 수 있음"
        ),
    }


@router.get("/connected-devices")
async def connected_devices() -> dict:
    if not _debug_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    devices = manager.list_connected_device_ids()
    return {"connected_devices": devices, "count": len(devices)}
