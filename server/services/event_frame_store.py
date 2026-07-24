"""
이벤트 프레임 이미지 파일 저장소.

탐지/안내 로그(detection_guidance_logs)가 적재되는 이벤트의 발생 시점 프레임을
JPEG 파일로 보관하고, DB에는 상대 경로(frame_path)만 남깁니다.

설계 원칙:
- 저장 위치: data/event_frames/YYYYMMDD/{event_id}.jpg (날짜 폴더로 보존 정리 용이)
- 원본 프레임만 저장 (bbox는 detected_objects_json에 있으므로 콘솔에서 오버레이 렌더링)
- 인코딩/파일 쓰기는 동기 함수로 두고 호출부(백그라운드 로그 태스크)에서
  asyncio.to_thread로 감쌉니다. 반사/인지 실시간 경로를 절대 막지 않습니다.
- 보존 기간 초과 날짜 폴더는 서버 기동 시 정리합니다 (개인정보 기간 한정 보존).
"""

import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
import logging
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv

from server.services.remote_storage_client import is_remote_storage_enabled, upload_event_frame

load_dotenv()

logger = logging.getLogger(__name__)

# 프로젝트 루트 기준 절대 경로 (server/services/ -> server/ -> 루트)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVENT_FRAMES_DIR = Path(
    os.getenv("EVENT_FRAMES_DIR", os.path.join(_PROJECT_ROOT, "data", "event_frames"))
)

# JPEG 품질: 오탐 검증용이므로 원본 화질 유지보다 용량 통제를 우선합니다.
JPEG_QUALITY = int(os.getenv("EVENT_FRAME_JPEG_QUALITY", "80"))

# 보존 기간(일). 보행 중 촬영 이미지는 행인 등 개인정보를 포함할 수 있어
# 오탐 검증 목적의 기간 한정 보존만 허용합니다.
RETENTION_DAYS = int(os.getenv("EVENT_FRAME_RETENTION_DAYS", "7"))

# event_id 화이트리스트: 파일명으로 쓰이므로 경로 탈출 문자를 차단합니다.
_EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# 날짜 폴더명 형식 (보존 정리 시 이 형식 외 디렉토리는 건드리지 않습니다)
_DATE_DIR_PATTERN = re.compile(r"^\d{8}$")


def is_valid_event_id(event_id: str | None) -> bool:
    """event_id가 파일명으로 안전한 형식인지 검사합니다."""
    return bool(event_id) and bool(_EVENT_ID_PATTERN.match(event_id))


def save_event_frame(event_id: str, frame: np.ndarray) -> str | None:
    """프레임을 JPEG으로 저장하고 EVENT_FRAMES_DIR 기준 상대 경로를 반환합니다.

    동기 함수이므로 실시간 경로에서 직접 호출하지 말고 asyncio.to_thread로 감쌉니다.
    실패 시 None을 반환하며 예외를 전파하지 않습니다 (로그 적재는 계속 진행).
    """
    if frame is None or not is_valid_event_id(event_id):
        return None
    try:
        date_dir = datetime.now(UTC).strftime("%Y%m%d")
        target_dir = EVENT_FRAMES_DIR / date_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        rel_path = f"{date_dir}/{event_id}.jpg"
        abs_path = target_dir / f"{event_id}.jpg"

        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not ok:
            logger.warning(f"[EventFrameStore] JPEG 인코딩 실패: event_id={event_id}")
            return None
        abs_path.write_bytes(encoded.tobytes())
        return rel_path
    except Exception as e:
        logger.error(f"[EventFrameStore] 프레임 저장 실패: event_id={event_id}, {e}")
        return None


def encode_event_frame_jpeg(event_id: str, frame: np.ndarray) -> bytes | None:
    """프레임을 JPEG bytes로 인코딩합니다."""
    if frame is None or not is_valid_event_id(event_id):
        return None
    try:
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not ok:
            logger.warning(f"[EventFrameStore] JPEG 인코딩 실패: event_id={event_id}")
            return None
        return encoded.tobytes()
    except Exception as e:
        logger.error(f"[EventFrameStore] JPEG 인코딩 예외: event_id={event_id}, {e}")
        return None


async def save_event_frame_async(event_id: str, frame: np.ndarray) -> str | None:
    """이벤트 프레임을 저장하고 DB에 남길 object key 또는 상대 경로를 반환합니다.

    원격 저장소가 켜져 있으면 Raspberry Pi 저장 API에 업로드하고, 성공한 object_key만
    반환합니다. 원격 업로드 실패 시 로컬에 몰래 저장하지 않고 None을 반환해
    다중 FastAPI writer 환경에서 MISS를 다시 만들지 않습니다.
    """
    if is_remote_storage_enabled():
        jpeg_bytes = await asyncio.to_thread(encode_event_frame_jpeg, event_id, frame)
        if jpeg_bytes is None:
            return None
        result = await upload_event_frame(event_id, jpeg_bytes)
        if result.status == "available":
            return result.object_key
        logger.error(
            "[EventFrameStore] 원격 프레임 저장 실패: event_id=%s, status=%s, error=%s",
            event_id,
            result.status,
            result.error_code,
        )
        return None
    return await asyncio.to_thread(save_event_frame, event_id, frame)


def resolve_frame_path(frame_path: str | None) -> Path | None:
    """DB의 frame_path를 실제 파일 경로로 변환합니다.

    EVENT_FRAMES_DIR 밖을 가리키는 경로(경로 탈출)나 미존재 파일은 None을 반환합니다.
    """
    if not frame_path:
        return None
    try:
        candidate = (EVENT_FRAMES_DIR / frame_path).resolve()
        base = EVENT_FRAMES_DIR.resolve()
        if not candidate.is_relative_to(base):
            logger.warning(f"[EventFrameStore] 경로 탈출 시도 차단: {frame_path}")
            return None
        if not candidate.is_file():
            return None
        return candidate
    except (OSError, ValueError) as e:
        logger.warning(f"[EventFrameStore] 경로 해석 실패: {frame_path}, {e}")
        return None


def cleanup_expired_frames(retention_days: int | None = None) -> int:
    """보존 기간을 초과한 로컬 날짜 폴더 또는 R2 객체를 삭제하고 건수를 반환합니다.

    2026-07-20: 서버 기동 시 1회 + EVENT_FRAME_CLEANUP_INTERVAL_S 주기로 반복
    호출합니다(`server/main.py`). YYYYMMDD 형식 폴더만 대상으로 하며, 형식이
    다른 항목은 안전을 위해 건드리지 않습니다.
    """
    days = RETENTION_DAYS if retention_days is None else retention_days
    if days <= 0:
        return 0

    from server.services.remote_storage_client import is_r2_backend

    if is_r2_backend():
        from server.services.r2_storage_client import cleanup_expired_objects_sync

        return cleanup_expired_objects_sync(days)

    if not EVENT_FRAMES_DIR.is_dir():
        return 0
    cutoff = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y%m%d")
    removed = 0
    for entry in EVENT_FRAMES_DIR.iterdir():
        if not entry.is_dir() or not _DATE_DIR_PATTERN.match(entry.name):
            continue
        if entry.name < cutoff:
            try:
                shutil.rmtree(entry)
                removed += 1
            except OSError as e:
                logger.error(f"[EventFrameStore] 만료 폴더 삭제 실패: {entry}, {e}")
    if removed:
        logger.info(f"[EventFrameStore] 보존 기간({days}일) 초과 폴더 {removed}개 삭제")
    return removed
