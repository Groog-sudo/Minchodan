# -*- coding: utf-8 -*-
import contextlib
import logging
import os
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from server.stt import DEFAULT_REQUEST_MODEL, SttService, SttToLlmBridge
from server.stt.stt_schema import SttTranscribeResult

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stt", tags=["STT"])


class SttGuideResponse(BaseModel):
    stt: SttTranscribeResult
    guidance_text: str
    used_fallback_llm: bool
    source: str


async def _save_upload_to_temp(upload_file: UploadFile) -> Path:
    suffix = Path(upload_file.filename or "input.wav").suffix or ".wav"
    data = await upload_file.read()

    if not data:
        raise HTTPException(status_code=400, detail="오디오 파일이 비어 있습니다.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(data)
        temp_path = Path(temp_file.name)

    return temp_path


@router.post("/transcribe", response_model=SttTranscribeResult)
async def transcribe_audio(
    audio: UploadFile = File(..., description="음성 파일 (wav/mp3 등)"),
    model_name: str | None = Form(default=DEFAULT_REQUEST_MODEL),
) -> SttTranscribeResult:
    temp_path: Path | None = None

    try:
        temp_path = await _save_upload_to_temp(audio)
        return SttService.transcribe_file(saved_path=temp_path, model_name=model_name)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("STT transcribe 처리 실패: %s", exc)
        raise HTTPException(status_code=500, detail="STT 처리 중 오류가 발생했습니다.") from exc
    finally:
        if temp_path and temp_path.exists():
            with contextlib.suppress(Exception):
                os.unlink(temp_path)


@router.post("/transcribe-and-guide", response_model=SttGuideResponse)
async def transcribe_and_guide(
    audio: UploadFile = File(..., description="음성 파일 (wav/mp3 등)"),
    model_name: str | None = Form(default=DEFAULT_REQUEST_MODEL),
) -> SttGuideResponse:
    temp_path: Path | None = None

    try:
        temp_path = await _save_upload_to_temp(audio)
        stt_result = SttService.transcribe_file(saved_path=temp_path, model_name=model_name)
        bridge = SttToLlmBridge()
        bridge_result = await bridge.invoke_existing_llm(stt_result)
        return SttGuideResponse(
            stt=stt_result,
            guidance_text=bridge_result.get("guidance_text", ""),
            used_fallback_llm=bridge_result.get("used_fallback_llm", True),
            source=bridge_result.get("source", "stt-bridge"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("STT transcribe-and-guide 처리 실패: %s", exc)
        raise HTTPException(status_code=500, detail="STT 가이드 처리 중 오류가 발생했습니다.") from exc
    finally:
        if temp_path and temp_path.exists():
            with contextlib.suppress(Exception):
                os.unlink(temp_path)
