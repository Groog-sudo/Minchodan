"""
원격 이벤트 프레임/STT 저장 파사드.

- `EVENT_FRAME_STORAGE_BACKEND=remote`: Raspberry Pi 중앙 저장 HTTP API
- `EVENT_FRAME_STORAGE_BACKEND=r2`: Cloudflare R2 (S3 API, r2_storage_client)
GPU FastAPI는 바이너리를 DB에 넣지 않고 object_key만 로그 테이블에 남깁니다.
비밀값(토큰/R2 키)은 서버 `.env`에만 둡니다.
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


def storage_backend() -> str:
    """이벤트 프레임 저장 백엔드 식별자: local | remote | r2."""
    return _first_env("EVENT_FRAME_STORAGE_BACKEND", "EVENT_FRAME_BACKEND").lower() or "local"


def is_r2_backend() -> bool:
    return storage_backend() in {"r2", "s3", "cloudflare_r2"}


def is_pi_remote_backend() -> bool:
    backend = storage_backend()
    if backend in {"remote", "remote_http", "image_server", "central"}:
        return bool(_base_url() and _token())
    if backend in {"local", "local_file", "disabled", "none", "off", "r2", "s3", "cloudflare_r2"}:
        return False
    return bool(_base_url() and _token())


def is_remote_storage_enabled() -> bool:
    """원격 저장소(Pi IMAGE_SERVER 또는 Cloudflare R2) 사용 여부.

    EVENT_FRAME_STORAGE_BACKEND가 local/disabled이면 끄고,
    r2/s3이거나 remote 계열(또는 base_url/token)이면 켠다.
    """
    backend = storage_backend()
    if backend in {"local", "local_file", "disabled", "none", "off"}:
        return False
    if is_r2_backend():
        from server.services.r2_storage_client import is_r2_configured

        return is_r2_configured()
    return is_pi_remote_backend()


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


# 💡 [면접 대비 주석] 공유 httpx.AsyncClient 연결 풀 (2026-07-17, P1).
# 기존에는 매 요청마다 async with httpx.AsyncClient(...)를 새로 생성해 TCP/TLS 핸드셰이크
# 비용이 반복됐다. 모듈 수준에서 1개의 클라이언트를 생성해 keep-alive와 커넥션 풀을 재사용한다.
# FastAPI lifespan(main.py)이 startup에서 create_shared_client(), shutdown에서
# close_shared_client()를 호출한다. 클라이언트 미초기 시에는 요청마다 폴백 생성한다(방어적).
_shared_client: httpx.AsyncClient | None = None


async def create_shared_client() -> None:
    """FastAPI lifespan startup에서 호출. Pi remote일 때만 공유 httpx 클라이언트를 생성한다."""
    global _shared_client
    if _shared_client is not None:
        return
    if is_r2_backend() or not is_pi_remote_backend():
        logger.info("[RemoteStorage] Pi httpx 클라이언트 생략 (backend=%s)", storage_backend())
        return
    _shared_client = httpx.AsyncClient(
        base_url=_base_url(),
        timeout=_timeout_seconds(),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    logger.info("[RemoteStorage] 공유 httpx.AsyncClient 생성 완료")


async def close_shared_client() -> None:
    """FastAPI lifespan shutdown에서 호출. 공유 클라이언트를 종료한다."""
    global _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None
        logger.info("[RemoteStorage] 공유 httpx.AsyncClient 종료 완료")


async def _get_client() -> httpx.AsyncClient:
    """공유 클라이언트를 반환. 미초기 시 임시 클라이언트를 생성한다(방어적 폴백)."""
    global _shared_client
    if _shared_client is not None:
        return _shared_client
    # lifespan이 아직 실행되지 않았거나 이미 종료된 경우의 방어적 폴백.
    return httpx.AsyncClient(base_url=_base_url(), timeout=_timeout_seconds())


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
        client = await _get_client()
        owns_client = _shared_client is None
        try:
            if owns_client:
                async with client:
                    response = await client.put(
                        path, content=payload, headers=_headers(content_type)
                    )
            else:
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
    if is_r2_backend():
        from server.services.r2_storage_client import upload_event_frame as r2_upload

        return await r2_upload(event_id, jpeg_bytes)
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
    if is_r2_backend():
        from server.services.r2_storage_client import upload_stt_audio as r2_upload_stt

        return await r2_upload_stt(event_id, audio_bytes, content_type, format_)
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


def resolve_event_frame_url(object_key: str, expires_seconds: int = 300) -> str | None:
    """R2 백엔드일 때 단기 GET URL(presigned 또는 공개 base). Pi remote는 None."""
    if not object_key or not is_r2_backend() or not is_remote_storage_enabled():
        return None
    from server.services.r2_storage_client import generate_presigned_get_url

    return generate_presigned_get_url(object_key, expires_seconds=expires_seconds)


async def fetch_event_frame(object_key: str) -> bytes | None:
    """중앙 저장소에서 이벤트 프레임 JPEG bytes를 조회합니다."""
    if not is_remote_storage_enabled():
        return None
    if is_r2_backend():
        from server.services.r2_storage_client import fetch_event_frame as r2_fetch

        return await r2_fetch(object_key)
    split = _split_event_frame_key(object_key)
    if split is None:
        return None
    date, event_id = split
    client = await _get_client()
    owns_client = _shared_client is None
    try:
        if owns_client:
            async with client:
                response = await client.get(
                    f"/internal/event-frames/{quote(date)}/{quote(event_id)}",
                    headers={"Authorization": f"Bearer {_token()}"},
                )
        else:
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
