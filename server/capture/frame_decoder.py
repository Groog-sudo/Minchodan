import base64
import contextlib
import logging
import os
import sys
import time
from dataclasses import dataclass

import cv2
import numpy as np
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

FRAME_SIZE = int(os.getenv("FRAME_SIZE", "640"))
TARGET_SIZE = (FRAME_SIZE, FRAME_SIZE)
MAX_FRAME_SIZE_KB = 5000
MIN_FRAME_SIZE_KB = 1


@dataclass
class ProcessedFrame:
    """디코딩 완료된 프레임 데이터 (2단계 출력, 3단계 입력)."""

    event_id: str
    device_id: str
    stream: str
    frame: np.ndarray
    original_size: tuple[int, int]
    size_kb: float
    processing_time_ms: float
    ts: int = 0


async def decode_frame(payload: dict) -> ProcessedFrame | None:
    """base64 JPEG 프레임을 디코딩하여 640x640 BGR로 리사이즈.

    가드레일:
        - thumbnail_jpeg_b64 None/빈 문자열 -> None
        - 크기 임계치 이탈 (< 1KB 또는 > 500KB) -> None
        - cv2.imdecode None 반환 -> None
        - cv2.resize 예외 -> None
        - 전체 예외 -> None (파이프라인 영속성)
    """
    start_ts = time.perf_counter()

    event_id = payload.get("event_id", "unknown")
    device_id = payload.get("device_id", "unknown")
    stream = payload.get("stream", "cognitive")
    # 방어적 시간 정보 파싱: ts(밀리초 epoch) 우선, 없을 경우 ISO 8601형식 timestamp 파싱 시도
    raw_ts = payload.get("ts")
    ts = 0
    if raw_ts is not None:
        with contextlib.suppress(ValueError, TypeError):
            ts = int(raw_ts)

    if ts == 0:
        timestamp_str = payload.get("timestamp")
        if timestamp_str:
            with contextlib.suppress(Exception):
                from datetime import datetime

                if timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(timestamp_str)
                ts = int(dt.timestamp() * 1000)

    b64_str = payload.get("thumbnail_jpeg_b64")

    if not b64_str:
        logger.warning(f"[FrameDecoder] base64 데이터 없음: event_id={event_id}")
        return None

    try:
        jpeg_bytes = base64.b64decode(b64_str)
        size_kb = len(jpeg_bytes) / 1024

        if size_kb > MAX_FRAME_SIZE_KB or size_kb < MIN_FRAME_SIZE_KB:
            logger.warning(f"[FrameDecoder] 크기 이상: {size_kb:.1f}KB, event_id={event_id}")
            return None

        np_buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)

        if frame is None:
            logger.error(f"[FrameDecoder] cv2.imdecode 실패: event_id={event_id}")
            return None

        original_size = (frame.shape[0], frame.shape[1])
        frame_resized = cv2.resize(frame, TARGET_SIZE, interpolation=cv2.INTER_LINEAR)

        elapsed_ms = (time.perf_counter() - start_ts) * 1000

        logger.info(
            f"[FrameDecoder] 수신: event_id={event_id}, stream={stream}, "
            f"원본={original_size[1]}x{original_size[0]}, "
            f"크기={size_kb:.1f}KB, 디코딩={elapsed_ms:.2f}ms"
        )

        return ProcessedFrame(
            event_id=event_id,
            device_id=device_id,
            stream=stream,
            frame=frame_resized,
            original_size=original_size,
            size_kb=size_kb,
            processing_time_ms=elapsed_ms,
            ts=ts,
        )

    except Exception as e:
        logger.error(f"[FrameDecoder] 오류: event_id={event_id}, {e}")
        return None
