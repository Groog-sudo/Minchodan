"""
Raspberry Pi 중앙 저장 API 클라이언트.

GPU FastAPI는 이미지/STT 음성 파일을 직접 DB에 넣지 않고, 이 클라이언트로
Raspberry Pi 저장 API에 업로드한 뒤 응답 object_key만 로그 테이블에 남깁니다.
토큰은 서버 측 환경 변수에서만 읽고 브라우저/앱에는 노출하지 않습니다.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

logger = logging.getLogger(__name__)

_DATE_PATTERN = re.compile(r"^\d{8}$")
_EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class RemoteStoreResult:
    """중앙 저장 API 업로드 결과."""

    object_key: str | None
    status: str
    error_code: str | None = None
    format: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return ""


def _base_url() -> str:
    return _first_env("IMAGE_SERVER_BASE_URL", "EVENT_FRAME_REMOTE_URL").rstrip("/")


def _token() -> str:
    return _first_env("IMAGE_SERVER_TOKEN", "EVENT_FRAME_REMOTE_TOKEN")


def is_remote_storage_enabled() -> bool:
    """중앙 저장소 사용 여부.

    EVENT_FRAME_STORAGE_BACKEND 또는 EVENT_FRAME_BACKEND가 local/disabled이면 끄고,
    remote 계열이거나 base_url/token이 명시돼 있으면 켭니다.
    """
    backend = _first_env("EVENT_FRAME_STORAGE_BACKEND", "EVENT_FRAME_BACKEND").lower()
    if backend in {"local", "local_file", "disabled", "none", "off"}:
        return False
    if backend in {"remote", "remote_http", "image_server", "central"}:
        return bool(_base_url() and _token())
    return bool(_base_url() and _token())


def _timeout_seconds() -> float:
    return float(
        _first_env("IMAGE_UPLOAD_TIMEOUT_SECONDS", "EVENT_FRAME_UPLOAD_TIMEOUT_SEC") or "3"
    )


def _max_retries() -> int:
    return int(_first_env("IMAGE_UPLOAD_MAX_RETRIES", "EVENT_FRAME_UPLOAD_RETRIES") or "1")


def _headers(content_type: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": content_type,
    }


def _disabled_result(format_: str | None = None) -> RemoteStoreResult:
    return RemoteStoreResult(
        object_key=None,
        status="not_saved",
        error_code="remote_storage_disabled",
        format=format_,
    )


async def _put_payload(
    path: str,
    payload: bytes,
    content_type: str,
) -> tuple[dict, str | None]:
    base_url = _base_url()
    token = _token()
    if not base_url or not token:
        return {}, "remote_storage_not_configured"

    attempts = _max_retries() + 1
    last_error: str | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=_timeout_seconds()) as client:
                response = await client.put(path, content=payload, headers=_headers(content_type))
            if response.status_code >= 500 and attempt < attempts:
                last_error = f"remote_http_{response.status_code}"
                await asyncio.sleep(0.2 * attempt)
                continue
            if response.status_code >= 400:
                return {}, f"remote_http_{response.status_code}"
            return response.json(), None
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc.__class__.__name__
            if attempt < attempts:
                await asyncio.sleep(0.2 * attempt)
                continue
            return {}, last_error
        except (httpx.HTTPError, ValueError) as exc:
            return {}, exc.__class__.__name__
    return {}, last_error or "remote_upload_failed"


async def upload_event_frame(event_id: str, jpeg_bytes: bytes) -> RemoteStoreResult:
    if not is_remote_storage_enabled():
        return _disabled_result(format_="jpg")
    if _EVENT_ID_PATTERN.fullmatch(event_id) is None:
        return RemoteStoreResult(None, "upload_failed", "invalid_event_id", format="jpg")

    body, error_code = await _put_payload(
        f"/internal/event-frames/{quote(event_id)}",
        jpeg_bytes,
        "image/jpeg",
    )
    digest = hashlib.sha256(jpeg_bytes).hexdigest()
    if error_code:
        logger.error(
            "[RemoteStorage] 이벤트 프레임 업로드 실패: event_id=%s, error=%s", event_id, error_code
        )
        return RemoteStoreResult(
            object_key=None,
            status="upload_failed",
            error_code=error_code,
            format="jpg",
            size_bytes=len(jpeg_bytes),
            sha256=digest,
        )

    object_key = str(body.get("object_key") or "")
    if not object_key:
        return RemoteStoreResult(None, "upload_failed", "missing_object_key", format="jpg")
    return RemoteStoreResult(
        object_key=object_key,
        status="available",
        format="jpg",
        size_bytes=len(jpeg_bytes),
        sha256=digest,
    )


async def upload_stt_audio(
    event_id: str,
    audio_bytes: bytes,
    content_type: str,
    format_: str,
) -> RemoteStoreResult:
    if not is_remote_storage_enabled():
        return _disabled_result(format_=format_)
    if _EVENT_ID_PATTERN.fullmatch(event_id) is None:
        return RemoteStoreResult(None, "upload_failed", "invalid_event_id", format=format_)

    body, error_code = await _put_payload(
        f"/internal/stt-audio/{quote(event_id)}",
        audio_bytes,
        content_type,
    )
    digest = hashlib.sha256(audio_bytes).hexdigest()
    if error_code:
        logger.error(
            "[RemoteStorage] STT 오디오 업로드 실패: event_id=%s, error=%s", event_id, error_code
        )
        return RemoteStoreResult(
            object_key=None,
            status="upload_failed",
            error_code=error_code,
            format=format_,
            size_bytes=len(audio_bytes),
            sha256=digest,
        )

    object_key = str(body.get("object_key") or "")
    if not object_key:
        return RemoteStoreResult(None, "upload_failed", "missing_object_key", format=format_)
    return RemoteStoreResult(
        object_key=object_key,
        status="available",
        format=str(body.get("format") or format_),
        size_bytes=len(audio_bytes),
        sha256=digest,
    )


def _split_event_frame_key(object_key: str) -> tuple[str, str] | None:
    parts = object_key.split("/", 1)
    if len(parts) != 2:
        return None
    date, filename = parts
    if _DATE_PATTERN.fullmatch(date) is None or not filename.endswith(".jpg"):
        return None
    event_id = filename[:-4]
    if _EVENT_ID_PATTERN.fullmatch(event_id) is None:
        return None
    return date, event_id


async def fetch_event_frame(object_key: str) -> bytes | None:
    """중앙 저장소에서 이벤트 프레임 JPEG bytes를 조회합니다."""
    if not is_remote_storage_enabled():
        return None
    split = _split_event_frame_key(object_key)
    if split is None:
        return None
    date, event_id = split
    try:
        async with httpx.AsyncClient(base_url=_base_url(), timeout=_timeout_seconds()) as client:
            response = await client.get(
                f"/internal/event-frames/{quote(date)}/{quote(event_id)}",
                headers={"Authorization": f"Bearer {_token()}"},
            )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return bytes(response.content)
    except httpx.HTTPError as exc:
        logger.error("[RemoteStorage] 이벤트 프레임 조회 실패: key=%s, error=%s", object_key, exc)
        return None
