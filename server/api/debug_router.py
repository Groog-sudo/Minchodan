# -*- coding: utf-8 -*-
"""개발용 디버그 REST API.

문자/안내문 TTS를 연결된 모바일 앱으로 밀어 넣는 실험 엔드포인트를 제공한다.
APP_ENV=production 에서는 비활성화한다.

# 💡 [면접 대비 주석 - 왜 REST로 TTS를 푸시하나]
Q. 인지 경로 guide는 원래 탐지 파이프라인에서만 나오는데, 왜 별도 REST가 있나?
A. 문자 알림·데모처럼 "탐지 없이" 음성만 검증할 때 WS 계약을 재사용하기 위함.
   클라이언트는 기존 guide + binary WAV 재생 경로를 그대로 탄다(신규 프로토콜 없음).
   운영에서는 APP_ENV=production 으로 404 처리해 공격면을 닫는다.
"""

from __future__ import annotations

import base64
import logging
import os
import sys
import time
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

if hasattr(sys.stdout, "reconfigure"):
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from server.api.dependencies import require_super_admin
from server.api.session_manager import manager
from server.tts.realtime_tts import RealtimeTTS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/debug", tags=["Debug"])

# [하드 코딩 부분 - 핵심] 문자 TTS 실험 기본 문구(앱 DEBUG 패널과 동일 계약).
_DEFAULT_SMS_TEXT = "새 문자가 도착했습니다. 엄마에게서. 오늘 저녁 몇 시에 오실 건가요?"


class SpeakToDeviceRequest(BaseModel):
    text: str = Field(default=_DEFAULT_SMS_TEXT, min_length=1)
    device_id: str | None = Field(
        default=None,
        description="대상 device_id. 생략 시 현재 연결된 첫 단말로 전송",
    )
    voice: str = "ko"
    speed: float = 0.85


def _debug_enabled() -> bool:
    # 비운영 환경이어도 명시적으로 허용하지 않으면 디버그 API를 닫는다.
    enabled = os.getenv("ENABLE_DEBUG_API", "false").strip().lower() in {"1", "true", "yes"}
    return enabled and os.getenv("APP_ENV", "development").strip().lower() != "production"


@router.post("/speak-to-device")
async def speak_to_device(
    body: SpeakToDeviceRequest,
    _super_admin: str = Depends(require_super_admin),
) -> dict:
    """서버 TTS로 합성한 WAV를 연결된 앱에 guide + binary로 전송한다.

    # 💡 [면접 대비 주석]
    Q. JSON에 audio를 base64로 안 싣고 binary를 따로 보내는 이유는?
    A. 인지 경로 운영 계약(2026-07-09)과 동일: transport=binary 후 raw WAV.
       base64는 용량·파싱 비용이 커서 실시간 음성에 불리하다.
    """
    if not _debug_enabled():
        raise HTTPException(status_code=404, detail="Not found")

    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text가 비어 있습니다.")

    # [바이브 코딩 부분] 연결 단말 선택·가드레일.
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

    # [바이브 코딩 부분] RealtimeTTS 합성 → guide JSON + WAV bytes 송신.
    tts = RealtimeTTS()
    b64_audio, duration_ms = await tts.synthesize(text=text, voice=body.voice, speed=body.speed)
    audio_bytes = base64.b64decode(b64_audio) if b64_audio else b""
    # [하드 코딩 부분 - 핵심] event_id 접두사 debug-sms- (stt- 가 아니라 인지 priority=1).
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
        # 2026-07-19: 관제 콘솔 미러링. 디버그 TTS도 단말과 동일하게 재생.
        await manager.broadcast_json_to_consoles(
            {
                "type": "console_guide_audio",
                "event_id": event_id,
                "device_id": device_id,
                "audio_codec": "wav",
                "duration_ms": duration_ms,
                "guidance_text": text,
                "source": "debug_sms_tts",
                "ts": int(time.time() * 1000),
            }
        )
        await manager.broadcast_to_consoles(audio_bytes)

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
async def connected_devices(
    _super_admin: str = Depends(require_super_admin),
) -> dict:
    if not _debug_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    devices = manager.list_connected_device_ids()
    return {"connected_devices": devices, "count": len(devices)}
