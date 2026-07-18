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
MAX_FRAME_SIZE_KB = 500
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
    # 클라이언트 온디바이스 씬 분류(scene.isLikelyIndoor) 기반 실외 추정치.
    # None: 클라이언트가 판정 불가(구버전/Android 등)로 미전송 - 기존처럼 신뢰.
    # True/False: 클라이언트가 보낸 최근 판정값(1프레임 지연 허용, CameraView.tsx 참조).
    is_outdoor: bool | None = None
    # 2026-07-19: "거리측정" 모드의 단발 검증 캡처 프레임 식별용("lidar_validation").
    # None이면 일반 연속 스트림 프레임(반사/인지). CameraView.tsx의
    # handleDistanceProbeCapture()가 채운다.
    probe_source: str | None = None


def _parse_frame_meta(payload: dict) -> tuple[str, str, str, int, bool | None, str | None]:
    """detection 메시지 payload/메타데이터에서 event_id/device_id/stream/ts/is_outdoor/probe_source를 추출.

    base64 방식(단일 JSON 메시지)과 바이너리 방식(메타 JSON + 바이너리 프레임 2단계)
    양쪽 모두 동일한 키 이름(event_id, device_id, stream, ts, timestamp, is_outdoor,
    probe_source)을 사용하므로 공통 파싱 로직으로 공유한다.
    """
    event_id = payload.get("event_id", "unknown")
    device_id = payload.get("device_id", "unknown")
    stream = payload.get("stream", "cognitive")
    is_outdoor = payload.get("is_outdoor")
    if is_outdoor is not None:
        is_outdoor = bool(is_outdoor)
    probe_source = payload.get("probe_source")

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

    return event_id, device_id, stream, ts, is_outdoor, probe_source


def _build_processed_frame(
    jpeg_bytes: bytes,
    event_id: str,
    device_id: str,
    stream: str,
    ts: int,
    start_ts: float,
    is_outdoor: bool | None = None,
    probe_source: str | None = None,
) -> ProcessedFrame | None:
    """raw JPEG 바이트를 디코딩하여 640x640 BGR ProcessedFrame으로 변환.

    base64 경로(decode_frame)와 바이너리 경로(decode_frame_binary)가 공유하는 핵심 로직.

    가드레일:
        - 크기 임계치 이탈 (< 1KB 또는 > 500KB) -> None
        - cv2.imdecode None 반환 -> None
        - 전체 예외 -> None (파이프라인 영속성)
    """
    try:
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
            is_outdoor=is_outdoor,
            probe_source=probe_source,
        )

    except Exception as e:
        logger.error(f"[FrameDecoder] 오류: event_id={event_id}, {e}")
        return None


async def decode_frame(payload: dict) -> ProcessedFrame | None:
    """base64 JPEG 프레임(단일 JSON 메시지, 구버전 호환)을 디코딩하여 640x640 BGR로 리사이즈.

    가드레일:
        - thumbnail_jpeg_b64 None/빈 문자열 -> None
        - 그 외는 _build_processed_frame과 동일
    """
    start_ts = time.perf_counter()
    event_id, device_id, stream, ts, is_outdoor, probe_source = _parse_frame_meta(payload)

    b64_str = payload.get("thumbnail_jpeg_b64")
    if not b64_str:
        logger.warning(f"[FrameDecoder] base64 데이터 없음: event_id={event_id}")
        return None

    # data URI 형식("data:image/jpeg;base64,...")도 허용한다.
    if isinstance(b64_str, str) and b64_str.startswith("data:"):
        parts = b64_str.split(",", 1)
        if len(parts) == 2:
            b64_str = parts[1]

    try:
        jpeg_bytes = base64.b64decode(b64_str)
    except Exception as e:
        logger.error(f"[FrameDecoder] base64 디코딩 오류: event_id={event_id}, {e}")
        return None

    return _build_processed_frame(
        jpeg_bytes, event_id, device_id, stream, ts, start_ts, is_outdoor, probe_source
    )


async def decode_frame_binary(jpeg_bytes: bytes, meta: dict) -> ProcessedFrame | None:
    """바이너리 WS 프레임으로 수신한 raw JPEG 바이트를 디코딩 (base64 미경유).

    클라이언트가 먼저 보낸 JSON 메타데이터 메시지(meta)와 뒤이어 도착한 바이너리
    프레임(jpeg_bytes)을 ws_router에서 짝지어 전달받는다. base64 인코딩/디코딩 단계가
    없어 페이로드 크기(약 33%)와 CPU 오버헤드를 절감한다.
    """
    start_ts = time.perf_counter()
    event_id, device_id, stream, ts, is_outdoor, probe_source = _parse_frame_meta(meta)

    if not jpeg_bytes:
        logger.warning(f"[FrameDecoder] 바이너리 데이터 없음: event_id={event_id}")
        return None

    return _build_processed_frame(
        jpeg_bytes, event_id, device_id, stream, ts, start_ts, is_outdoor, probe_source
    )
