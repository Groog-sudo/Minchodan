# -*- coding: utf-8 -*-
"""Cloudflare R2 (S3 호환) 이벤트 프레임·STT 오디오 저장 클라이언트.

GPU FastAPI는 JPEG/STT 바이너리를 R2에 PutObject 하고, DB에는 object_key만 남긴다.
Pi IMAGE_SERVER HTTP API와 동일한 RemoteStoreResult 계약을 유지한다.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

logger = logging.getLogger(__name__)


def _result_cls():
    """순환 임포트 회피: remote_storage_client.RemoteStoreResult를 지연 로드."""
    from server.services.remote_storage_client import RemoteStoreResult

    return RemoteStoreResult


_DATE_PATTERN = re.compile(r"^\d{8}$")
_EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_FRAME_KEY_PATTERN = re.compile(
    r"^event_frames/(?P<date>\d{8})/(?P<event_id>[A-Za-z0-9][A-Za-z0-9._-]{0,127})\.jpg$"
)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def is_r2_configured() -> bool:
    """R2 필수 환경변수가 모두 있으면 True."""
    return bool(
        _env("R2_ACCESS_KEY_ID")
        and _env("R2_SECRET_ACCESS_KEY")
        and _env("R2_BUCKET")
        and (_env("R2_ENDPOINT") or _env("R2_ACCOUNT_ID"))
    )


def _endpoint_url() -> str:
    explicit = _env("R2_ENDPOINT")
    if explicit:
        return explicit.rstrip("/")
    account_id = _env("R2_ACCOUNT_ID")
    if not account_id:
        return ""
    return f"https://{account_id}.r2.cloudflarestorage.com"


@lru_cache(maxsize=1)
def _sync_client() -> Any:
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=_endpoint_url(),
        aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"),
        region_name=_env("R2_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    return _env("R2_BUCKET")


def _disabled(format_: str | None = None):
    return _result_cls()(
        object_key=None,
        status="not_saved",
        error_code="r2_storage_not_configured",
        format=format_,
    )


def frame_object_key(event_id: str, when: datetime | None = None) -> str:
    stamp = (when or datetime.now(UTC)).strftime("%Y%m%d")
    return f"event_frames/{stamp}/{event_id}.jpg"


def stt_object_key(event_id: str, format_: str) -> str:
    ext = (format_ or "bin").lstrip(".")
    return f"stt/{event_id}.{ext}"


def _put_object_sync(key: str, payload: bytes, content_type: str) -> None:
    _sync_client().put_object(
        Bucket=_bucket(),
        Key=key,
        Body=payload,
        ContentType=content_type,
    )


def _get_object_sync(key: str) -> bytes | None:
    try:
        response = _sync_client().get_object(Bucket=_bucket(), Key=key)
        return bytes(response["Body"].read())
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        logger.error("[R2Storage] GetObject 실패: key=%s error=%s", key, exc)
        return None


def head_bucket_sync() -> bool:
    """사전검사용 HeadBucket. 설정/네트워크 오류 시 False."""
    if not is_r2_configured():
        return False
    try:
        _sync_client().head_bucket(Bucket=_bucket())
        return True
    except Exception as exc:
        logger.warning("[R2Storage] HeadBucket 실패: %s", exc)
        return False


async def upload_event_frame(event_id: str, jpeg_bytes: bytes):
    Result = _result_cls()
    if not is_r2_configured():
        return _disabled(format_="jpg")
    if _EVENT_ID_PATTERN.fullmatch(event_id) is None:
        return Result(None, "upload_failed", "invalid_event_id", format="jpg")

    key = frame_object_key(event_id)
    digest = hashlib.sha256(jpeg_bytes).hexdigest()
    try:
        await asyncio.to_thread(_put_object_sync, key, jpeg_bytes, "image/jpeg")
    except Exception as exc:
        logger.error("[R2Storage] 이벤트 프레임 업로드 실패: event_id=%s error=%s", event_id, exc)
        return Result(
            object_key=None,
            status="upload_failed",
            error_code=exc.__class__.__name__,
            format="jpg",
            size_bytes=len(jpeg_bytes),
            sha256=digest,
        )
    return Result(
        object_key=key,
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
):
    Result = _result_cls()
    if not is_r2_configured():
        return _disabled(format_=format_)
    if _EVENT_ID_PATTERN.fullmatch(event_id) is None:
        return Result(None, "upload_failed", "invalid_event_id", format=format_)

    key = stt_object_key(event_id, format_)
    digest = hashlib.sha256(audio_bytes).hexdigest()
    try:
        await asyncio.to_thread(_put_object_sync, key, audio_bytes, content_type)
    except Exception as exc:
        logger.error("[R2Storage] STT 업로드 실패: event_id=%s error=%s", event_id, exc)
        return Result(
            object_key=None,
            status="upload_failed",
            error_code=exc.__class__.__name__,
            format=format_,
            size_bytes=len(audio_bytes),
            sha256=digest,
        )
    return Result(
        object_key=key,
        status="available",
        format=format_,
        size_bytes=len(audio_bytes),
        sha256=digest,
    )


async def fetch_event_frame(object_key: str) -> bytes | None:
    if not is_r2_configured():
        return None
    if _FRAME_KEY_PATTERN.fullmatch(object_key) is None:
        # 레거시 Pi 키(YYYYMMDD/event.jpg)는 R2에 없음
        return None
    return await asyncio.to_thread(_get_object_sync, object_key)


def generate_presigned_get_url(object_key: str, expires_seconds: int = 300) -> str | None:
    """관리자/콘솔용 단기 GET URL. 실패 시 None."""
    if not is_r2_configured() or not object_key:
        return None
    public_base = _env("R2_PUBLIC_BASE_URL").rstrip("/")
    if public_base:
        return f"{public_base}/{object_key}"
    try:
        return _sync_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": object_key},
            ExpiresIn=expires_seconds,
        )
    except Exception as exc:
        logger.error("[R2Storage] presign 실패: key=%s error=%s", object_key, exc)
        return None


def cleanup_expired_objects_sync(retention_days: int) -> int:
    """event_frames/ 아래 보존 기간 초과 날짜 prefix 객체를 삭제하고 삭제 건수를 반환."""
    if retention_days <= 0 or not is_r2_configured():
        return 0
    cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).strftime("%Y%m%d")
    client = _sync_client()
    bucket = _bucket()
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix="event_frames/"):
        for item in page.get("Contents") or []:
            key = str(item.get("Key") or "")
            match = _FRAME_KEY_PATTERN.fullmatch(key)
            if match is None:
                continue
            if match.group("date") < cutoff:
                try:
                    client.delete_object(Bucket=bucket, Key=key)
                    deleted += 1
                except Exception as exc:
                    logger.error("[R2Storage] 만료 객체 삭제 실패: key=%s error=%s", key, exc)
    if deleted:
        logger.info("[R2Storage] 보존 기간(%s일) 초과 객체 %s개 삭제", retention_days, deleted)
    return deleted


async def cleanup_expired_objects(retention_days: int) -> int:
    return await asyncio.to_thread(cleanup_expired_objects_sync, retention_days)
