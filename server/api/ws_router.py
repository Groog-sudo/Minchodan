"""
WebSocket /ws/detect 엔드포인트 라우터.
단말(React Native)과 GPU 서버 간 실시간 양방향 통신 채널을 제공합니다.

핸드셰이크: accept -> welcome -> hello -> auth_ok -> heartbeat 루프
detection: decode_frame -> stream_splitter -> ack
"""

import asyncio
import base64
import contextlib
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from server.api.auth import verify_device
from server.api.config import settings
from server.api.heartbeat import HeartbeatManager
from server.api.schemas import now_iso, now_ts
from server.api.session_manager import manager
from server.bus.redis_client import redis_bus
from server.capture.frame_decoder import decode_frame, decode_frame_binary
from server.capture.stream_splitter import get_default_splitter
from server.detection.schemas import DistanceProbeReport
from server.services.detection_guidance_log_service import persist_detection_guidance_log
from server.services.device_registry_service import (
    ensure_device_registered,
    get_cached_device_ids,
)
from server.services.lidar_validation_service import persist_distance_probe_samples
from server.services.pipeline_debug_builder import build_stt_pipeline_debug
from server.services.remote_storage_client import upload_stt_audio
from server.stt.stt_service import SttService
from server.stt.stt_to_llm_bridge import SttToLlmBridge
from server.tts.realtime_tts import realtime_tts

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)
router = APIRouter()

MIN_STT_AUDIO_BYTES = 4096


async def _send_detection_ack(
    ws: WebSocket,
    event_id: str,
    frame_id: int,
    decode_ms: float,
) -> None:
    """탐지 ack를 즉시 보낸다.

    HeartbeatManager가 다른 태스크에서 동시에 타임아웃 close를 걸 수 있어(레이스),
    ack 전송 실패가 세션 전체를 죽이지 않도록 여기서 흡수한다. 소켓이 실제로
    끊겼다면 메인 루프의 다음 ws.receive()가 WebSocketDisconnect로 정상 정리한다.
    """
    with contextlib.suppress(Exception):
        await ws.send_json(
            {
                "type": "ack",
                "event_id": event_id,
                "frame_id": frame_id,
                "decode_ms": round(decode_ms, 2),
            }
        )


async def _route_detection_frame(
    splitter,
    processed,
    event_id: str,
    frame_id: int,
    decode_ms: float,
    b64_len_for_log: int = 0,
) -> None:
    """디코딩 결과를 스트림 스플리터로 라우팅한다 (YOLO/게이트 - 상대적으로 느림)."""
    logger.info(
        f"[WS] detection 수신 - event_id: {event_id}, frame_id: {frame_id}, decode_ms: {decode_ms:.2f}ms"
    )
    print(
        f"[DEBUG_WS] detection 수신 - event_id: {event_id}, frame_id: {frame_id}, decode_ms: {decode_ms:.2f}ms",
        flush=True,
    )

    if processed is not None:
        with contextlib.suppress(Exception):
            await splitter.route_frame(processed)
    else:
        print(
            f"[DEBUG_WS] 디코딩 실패! event_id={event_id}, base64길이={b64_len_for_log}",
            flush=True,
        )


async def _finish_detection(
    ws: WebSocket,
    splitter,
    processed,
    event_id: str,
    frame_id: int,
    decode_ms: float,
    b64_len_for_log: int = 0,
) -> None:
    """디코딩 결과를 스트림 스플리터로 라우팅하고 ack를 응답한다.

    base64 경로(단일 JSON 메시지)와 바이너리 경로(메타 + 바이너리 프레임) 양쪽이
    공유하는 후처리 로직 - route_frame + ack 응답 (guide 17.1 계층 분리 준수).

    2026-07-17 정정: 메인 수신 루프는 현재 이 헬퍼를 호출하지 않고 인라인으로
    처리한다. 인라인 패턴은 ack를 콘솔 중계보다 먼저 보내고(P0) route는
    백그라운드 태스크로 분리한다(최신성 우선). 이 함수는 참조용 계약으로 남겨둔다.
    """
    await _send_detection_ack(ws, event_id, frame_id, decode_ms)
    await _route_detection_frame(
        splitter, processed, event_id, frame_id, decode_ms, b64_len_for_log
    )


async def _broadcast_session_status(
    device_id: str, status: str, rtt_ms: float | None = None
) -> None:
    """콘솔 SessionStatus 패널(단말 접속 상태) 실시간 갱신.

    이전에는 session_status 이벤트를 아무 곳에서도 발행하지 않아 콘솔 패널이 항상 비어
    있었다(2026-07-12 발견). 연결/재확인(heartbeat_ack)/해제 3개 지점에서 호출한다.
    """
    from server.mcp.manager import mcp_manager

    with contextlib.suppress(Exception):
        await mcp_manager.broadcast_event(
            "session_status",
            {
                "device_id": device_id,
                "status": status,
                "rtt_ms": rtt_ms,
                "last_seen": now_iso(),
            },
        )


_stt_bridge = SttToLlmBridge()

# device_id별 STT 처리 직렬화 락. ws_detect 메인 루프는 stt_audio 메시지마다
# asyncio.create_task로 _handle_stt_audio를 fire-and-forget 실행하는데(하트비트/다른
# 메시지 처리를 막지 않기 위함, 2026-07-09 도입), 사용자가 응답을 기다리지 않고 연달아
# 누르면 이전 요청이 처리 중(수 초~10초+)인 동안 새 요청이 동시에 시작돼 nav_manager의
# 공유 대화 상태(awaiting_question/awaiting_intent/status)를 서로 경쟁적으로 읽고 써서
# 응답이 직전 발화와 안 맞는 것처럼 보이는 문제가 실기기에서 확인됐다(2026-07-10).
# STT는 본질적으로 순차 대화이므로 디바이스별로 한 번에 하나씩만 처리하도록 직렬화한다.
_stt_locks: dict[str, asyncio.Lock] = {}


def _get_stt_lock(device_id: str) -> asyncio.Lock:
    if device_id not in _stt_locks:
        _stt_locks[device_id] = asyncio.Lock()
    return _stt_locks[device_id]


# T3-S (2026-07-18): STT 응답 재생 예상 시간(초) 추정. client/src/hooks/useWebSocket.ts의
# textEstimateMs(글자당 180ms, 최소 2000ms) + estimatedMs(서버 duration_ms와 텍스트 추정치 중
# 큰 값) + 1200ms 마진 계산과 동일한 공식을 서버측 STT 억제 TTL에도 적용해, 응답 전송 직후가
# 아니라 실제 재생이 끝날 것으로 추정되는 시점까지 인지 가이드 발행 억제를 유지한다.
_STT_HOLD_MS_PER_CHAR = 180.0
_STT_HOLD_MIN_TEXT_MS = 2000.0
_STT_HOLD_MARGIN_MS = 1200.0


def _estimate_stt_hold_seconds(guidance_text: str, duration_ms: float = 0.0) -> float:
    if not guidance_text:
        return 0.0
    text_estimate_ms = max(len(guidance_text) * _STT_HOLD_MS_PER_CHAR, _STT_HOLD_MIN_TEXT_MS)
    estimated_ms = max(duration_ms or 0.0, text_estimate_ms)
    return (estimated_ms + _STT_HOLD_MARGIN_MS) / 1000.0


async def _handle_stt_audio(ws: WebSocket, device_id: str, data: dict) -> None:
    """STT 음성 명령 메시지를 처리한다: 오디오 저장 -> 전사 -> 네비게이션/LLM 브리지 -> TTS 합성.

    응답은 기존 인지 경로 클라이언트 핸들러가 이미 처리 가능한 "guide" 타입으로 보낸다.
    JSON 메타데이터 직후 raw WAV 바이너리 프레임을 전송하므로 별도 신규 메시지 타입은 없다.

    2026-07-09: server/stt/*.py(SttService, SttToLlmBridge)는 완성돼 있었으나 어떤
    라우터에서도 호출되지 않아 서버가 STT 요청을 받을 경로 자체가 없었다(main.py에는
    STT 라우팅이 전혀 없고, server/navigation/server.py는 별도 FastAPI 앱이라 클라이언트가
    실제로 붙는 /ws/detect와 무관했다). 이 핸들러가 그 배선을 연결한다.

    T3-S (2026-07-18): STT 처리 구간 동안 해당 device_id의 인지 가이드 발행을 억제한다.
    클라이언트 audioEngine 우선순위 조정자가 1차 방어선이며, 서버 억제는 이중 방어/연산
    낭비 제거용이다. 반사 경로는 이 상태와 무관하게 항상 통과한다.

    _process_stt_audio()는 응답 전송 완료 시점의 예상 재생 시간(초, 없으면 0.0)을
    반환한다 - 억제를 응답 전송 즉시가 아니라 실제 재생이 끝날 것으로 추정되는 시점까지
    유지하기 위함(2026-07-18 정정: 이전에는 전송 직후 즉시 해제해 재생 구간 동안
    인지 경로가 계속 오케스트레이션을 시도하는 경쟁 창이 남아 있었다).
    """
    audio_b64 = data.get("audio_b64", "")
    if not audio_b64:
        logger.warning(f"[WS] stt_audio 메시지에 audio_b64 없음: device_id={device_id}")
        return

    async with _get_stt_lock(device_id):
        manager.set_stt_active(device_id, True)
        hold_seconds = 0.0
        try:
            hold_seconds = await _process_stt_audio(ws, device_id, data, audio_b64)
        finally:
            # 응답 예상 재생시간 + 마진까지 억제를 연장(ttl_seconds=0이면 즉시 해제).
            # 클라이언트 audioEngine이 실제 재생 종료 콜백으로 결정론적 해제를 담당하므로
            # 이 TTL은 이중 방어(연산 낭비 제거)일 뿐 정확성의 1차 책임은 아니다.
            manager.set_stt_active(device_id, False, ttl_seconds=hold_seconds)


async def _handle_distance_probe_sample(device_id: str, data: dict) -> None:
    """LiDAR 실거리 검증 캡처(distance_probe_sample) 메시지를 저장한다.

    거리측정(depthMode) 프로토타입 전용 - 반사/인지 경로의 실시간 판단에는 관여하지
    않는다. CameraView가 depthMode에서 캡처한 정지 프레임을 기존 "detection" 경로로
    보내 server_detection 응답(bbox)을 받은 뒤, 같은 bbox의 LiDAR 실측을 이 메시지로
    보고한다.
    """
    payload = data.get("payload", {})
    try:
        report = DistanceProbeReport.model_validate(payload)
    except ValidationError as e:
        logger.warning(f"[WS] distance_probe_sample payload 검증 실패: device_id={device_id}, {e}")
        return
    if not report.samples:
        return
    _, reg_device_id = get_cached_device_ids(device_id)
    try:
        saved = await persist_distance_probe_samples(report, reg_device_id)
        logger.info(
            f"[WS] distance_probe_sample 저장 완료: device_id={device_id}, "
            f"event_id={report.event_id}, samples={len(saved)}"
        )
    except Exception as e:
        logger.error(f"[WS] distance_probe_sample 저장 실패: device_id={device_id}, {e}")


async def _send_stt_wait_notice(ws: WebSocket, device_id: str) -> None:
    """경로 검색·RAG·LLM 등 장시간 STT 후속 처리 전 즉시 대기 안내를 재생한다.

    에코 감지 메모리(_record_guidance)에는 넣지 않는다 - 본 응답의 일부가 아니므로.
    """
    from server.stt.stt_config import STT_WAIT_GUIDANCE_TEXT

    wait_text = STT_WAIT_GUIDANCE_TEXT
    audio_b64_out, duration_ms = await realtime_tts.synthesize(text=wait_text)
    audio_bytes_out = base64.b64decode(audio_b64_out) if audio_b64_out else b""

    with contextlib.suppress(Exception):
        await ws.send_json(
            {
                "type": "guide",
                "event_id": f"stt-wait-{device_id}-{now_ts()}",
                "risk_level": "low",
                "guidance_text": wait_text,
                "audio_codec": "wav",
                "duration_ms": duration_ms,
                "transport": "binary" if audio_bytes_out else "none",
                "source": "stt-wait-notice",
                "ts": now_ts(),
            }
        )
        if audio_bytes_out:
            await ws.send_bytes(audio_bytes_out)
    logger.info(f"[WS] STT 대기 안내 전송: device_id={device_id}, text={wait_text!r}")


async def _send_nav_guidance(ws: WebSocket, device_id: str, nav_event: dict) -> None:
    """GPS 갱신 시점에 평가된 길안내 멘트를 TTS 합성해 guide 메시지로 전송한다.

    2026-07-11 도입: 길안내를 카메라 탐지 여부와 분리하기 위한 전용 전송 경로.
    메시지 형식은 STT/인지 경로 guide와 동일해 클라이언트 수정이 필요 없다
    (event_id가 "stt-"로 시작하지 않으므로 STT 상호작용 중에는 뮤트 대상 - 의도된 동작).
    """
    text = nav_event.get("text", "")
    if not text:
        return

    audio_b64_out, duration_ms = await realtime_tts.synthesize(text=text)
    audio_bytes_out = base64.b64decode(audio_b64_out) if audio_b64_out else b""

    with contextlib.suppress(Exception):
        await ws.send_json(
            {
                "type": "guide",
                "event_id": f"nav-{device_id}-{now_ts()}",
                "risk_level": "mid" if nav_event.get("is_danger") else "low",
                "guidance_text": text,
                "audio_codec": "wav",
                "duration_ms": duration_ms,
                "transport": "binary" if audio_bytes_out else "none",
                "source": nav_event.get("type", "nav-guidance"),
                "ts": now_ts(),
            }
        )
        if audio_bytes_out:
            await ws.send_bytes(audio_bytes_out)
    logger.info(
        f"[WS] 길안내 전송: device_id={device_id}, text={text!r}, "
        f"type={nav_event.get('type')}, waypoint_idx={nav_event.get('active_waypoint_idx')}"
    )


def _detect_audio_suffix(audio_bytes: bytes) -> str:
    """magic bytes로 오디오 포맷을 감지하여 임시 파일 확장자를 결정한다.

    Android는 MPEG-4/AAC(.m4a) 포맷으로 전송하는데 .wav로 저장하면
    ffmpeg 디코딩이 실패하는 케이스가 있다. iOS는 .wav(RIFF) 또는 .m4a.
    """
    if len(audio_bytes) < 12:
        return ".wav"
    # MPEG-4 계열(m4a/mp4/aac): offset 4-8이 'ftyp' box 시그니처
    if audio_bytes[4:8] == b"ftyp":
        return ".m4a"
    # RIFF/WAV
    if audio_bytes[:4] == b"RIFF":
        return ".wav"
    # OGG
    if audio_bytes[:4] == b"OggS":
        return ".ogg"
    # MP3 (ID3 tag or sync word)
    if audio_bytes[:3] == b"ID3" or (
        len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0
    ):
        return ".mp3"
    # 감지 실패 시 .wav 폴백 (ffmpeg이 내용 기반으로 재시도)
    return ".wav"


def _audio_content_type_for_suffix(audio_suffix: str) -> str:
    """오디오 확장자에 맞는 Content-Type을 반환합니다."""
    if audio_suffix == ".wav":
        return "audio/wav"
    if audio_suffix == ".m4a":
        return "audio/mp4"
    if audio_suffix == ".ogg":
        return "audio/ogg"
    if audio_suffix == ".mp3":
        return "audio/mpeg"
    return "application/octet-stream"


async def _process_stt_audio(ws: WebSocket, device_id: str, data: dict, audio_b64: str) -> float:
    """STT 응답 처리 후, 예상 재생 시간(초)을 반환한다(호출부의 STT 억제 TTL 연장용)."""
    stt_event_id = f"stt-{device_id}-{now_ts()}"
    model_name = data.get("model_name")
    # 레이턴시 계측: 실기기 -> STT -> LLM -> TTS -> DB저장 스테이지별 ms를 모아
    # persist_detection_guidance_log에 넘긴다(콘솔 레이턴시 패널에서 확인).
    stt_stage_start = time.perf_counter()
    latency_stages: dict[str, float] = {}

    try:
        from server.mcp.manager import mcp_manager

        await mcp_manager.broadcast_event(
            "stt_status", {"stt_status": "transcribing", "device_id": device_id}
        )
    except Exception as e:
        logger.error(f"[WS] stt_status broadcast failed: {e}")

    try:
        audio_bytes = base64.b64decode(audio_b64)
    except (ValueError, TypeError) as e:
        logger.error(f"[WS] stt_audio base64 디코딩 실패: device_id={device_id}, {e}")
        return 0.0

    if len(audio_bytes) < MIN_STT_AUDIO_BYTES:
        logger.warning(
            f"[WS] stt_audio 길이 부족 - 전사 생략: device_id={device_id}, "
            f"bytes={len(audio_bytes)}, min={MIN_STT_AUDIO_BYTES}"
        )
        too_short_text = "음성이 너무 짧습니다. 버튼을 누른 채로 다시 말씀해 주세요."
        with contextlib.suppress(Exception):
            await ws.send_json(
                {
                    "type": "guide",
                    "event_id": f"stt-short-{device_id}-{now_ts()}",
                    "risk_level": "low",
                    "guidance_text": too_short_text,
                    "audio_codec": "wav",
                    "duration_ms": 0,
                    "transport": "none",
                    "source": "stt-audio-too-short",
                    "ts": now_ts(),
                }
            )
        return _estimate_stt_hold_seconds(too_short_text)

    saved_path: Path | None = None
    try:
        # magic bytes로 포맷 감지: Android = .m4a(MPEG-4/AAC), iOS = .wav(RIFF)
        audio_suffix = _detect_audio_suffix(audio_bytes)
        logger.info(
            f"[WS] STT 오디오 포맷 감지: device_id={device_id}, suffix={audio_suffix}, size={len(audio_bytes)}"
        )

        # 0바이트 오디오 즉시 차단 - Whisper 예외 전에 안내 반환
        if len(audio_bytes) == 0:
            logger.warning(f"[WS] STT 오디오 0바이트: device_id={device_id}")
            empty_audio_text = "음성이 녹음되지 않았습니다. 다시 시도해 주세요."
            with contextlib.suppress(Exception):
                await ws.send_json(
                    {
                        "type": "guide",
                        "event_id": f"stt-empty-{device_id}-{now_ts()}",
                        "risk_level": "low",
                        "guidance_text": empty_audio_text,
                        "audio_codec": "wav",
                        "duration_ms": 0,
                        "transport": "none",
                        "source": "stt-empty-audio",
                        "ts": now_ts(),
                    }
                )
            return _estimate_stt_hold_seconds(empty_audio_text)

        with tempfile.NamedTemporaryFile(suffix=audio_suffix, delete=False) as temp_wav:
            temp_wav.write(audio_bytes)
            saved_path = Path(temp_wav.name)

        wait_notice_sent = False
        if _stt_bridge.should_play_stt_wait_notice(device_id):
            await _send_stt_wait_notice(ws, device_id)
            wait_notice_sent = True

        stt_result = await asyncio.to_thread(
            SttService.transcribe_file, saved_path=saved_path, model_name=model_name
        )
        latency_stages["stt_ms"] = round((time.perf_counter() - stt_stage_start) * 1000, 1)
        logger.info(f"[WS] STT 전사 완료: device_id={device_id}, text_len={len(stt_result.text)}")

        if not wait_notice_sent and _stt_bridge.should_play_stt_wait_notice(
            device_id, stt_result.text
        ):
            await _send_stt_wait_notice(ws, device_id)
            wait_notice_sent = True

        llm_start = time.perf_counter()
        bridge_result = await _stt_bridge.invoke_existing_llm(stt_result, device_id)
        latency_stages["llm_ms"] = round((time.perf_counter() - llm_start) * 1000, 1)
        guidance_text = bridge_result.get("guidance_text", "")
        bridge_source = bridge_result.get("source", "")

        # 2026-07-11: 자기-에코 감지(안내문이 마이크로 재녹음된 경우)면 클라이언트에
        # 응답을 보내지 않고 조용히 종료한다 (메아리 루프 방지).
        # 관리자 콘솔 디버그용으로는 전사문과 스킵 사유를 DB에 남긴다.
        if bridge_source == "stt-echo-detected":
            logger.info(f"[WS] STT 에코 감지 - 응답 스킵: device_id={device_id}")
            stt_event_id = f"stt-echo-{device_id}-{now_ts()}"
            latency_stages["total_ms"] = round((time.perf_counter() - stt_stage_start) * 1000, 1)
            try:
                reg_user_id, reg_device_id = get_cached_device_ids(device_id)
                saved_log = await persist_detection_guidance_log(
                    event_id=stt_event_id,
                    stream_type="cognitive",
                    detections=[
                        {
                            "source": "stt",
                            "text_length": len(stt_result.text or ""),
                            "stt_transcript": (stt_result.text or "").strip(),
                            "skipped": True,
                            "skip_reason": "stt_echo_detected",
                        }
                    ],
                    tts_text="[에코 스킵] 응답 미전송",
                    latency_stages=latency_stages,
                    user_id=reg_user_id,
                    device_id=reg_device_id,
                    pipeline_debug=build_stt_pipeline_debug(
                        stt_transcript=stt_result.text or "",
                        bridge_result=bridge_result,
                        response_skipped=True,
                    ),
                )
                with contextlib.suppress(Exception):
                    await manager.broadcast_json_to_consoles(
                        {"type": "guidance_log_event", "row": saved_log.model_dump(mode="json")}
                    )
            except Exception as e:
                logger.error(f"[WS] stt_echo DB 로그 저장 실패: device_id={device_id}, {e}")
            return 0.0

        logger.info(
            f"[WS] STT 안내 생성: device_id={device_id}, "
            f"guidance_len={len(guidance_text)}, source={bridge_source}"
        )

        # 콘솔 AI Pipeline Monitor 실시간 갱신 (consumer.py._broadcast_ai_pipeline_status와 동일 목적).
        with contextlib.suppress(Exception):
            from server.mcp.manager import mcp_manager
            from server.orchestration.llm_client_factory import LLMClientFactory

            await mcp_manager.broadcast_event(
                "llm_status",
                {
                    "llm_provider": LLMClientFactory.get_current_provider(),
                    "tts_engine": os.getenv("TTS_ENGINE", "supertonic"),
                    "reflex_bypass": False,
                },
            )

        # 2026-07-11: 클라이언트에 전송할 안내문을 에코 감지용 메모리에 기록한다
        # (다음 STT 입력이 이 안내문의 에코인지 판정하기 위함).
        if guidance_text:
            _stt_bridge._record_guidance(device_id, guidance_text)

        tts_start = time.perf_counter()
        audio_wav_b64, duration_ms = await realtime_tts.synthesize(text=guidance_text)
        latency_stages["tts_ms"] = round((time.perf_counter() - tts_start) * 1000, 1)

        # 2026-07-09에 인지 경로(DetectionConsumer._send_cognitive_guide)가 오디오를
        # JSON base64 오디오에서 transport:"binary" + 별도 바이너리 프레임으로
        # 옮기면서 클라이언트(useWebSocket.ts)도 transport!=="binary"면 무조건 단말
        # TTS(speakFallback)로 즉시 폴백하도록 바뀌었다. 이 STT 경로가 그 마이그레이션에서
        # 빠져 있어 서버가 합성한 오디오를 클라이언트가 항상 무시하고 있었다(실기기 실측
        # 확인, 2026-07-10) - 인지 경로와 동일한 전송 방식으로 맞춘다.
        audio_bytes_out = base64.b64decode(audio_wav_b64) if audio_wav_b64 else b""

        # 백그라운드 태스크로 분리돼(2026-07-09) 처리 도중 클라이언트가 이미 끊어졌을 수
        # 있다 - 전송 실패는 결과를 못 받는 것 이상의 문제가 아니므로 조용히 무시한다.
        with contextlib.suppress(Exception):
            await ws.send_json(
                {
                    "type": "guide",
                    "event_id": stt_event_id,
                    "risk_level": "low",
                    "guidance_text": guidance_text,
                    "audio_codec": "wav",
                    "duration_ms": duration_ms,
                    "transport": "binary" if audio_bytes_out else "none",
                    "source": bridge_result.get("source", "stt-bridge"),
                    "ts": now_ts(),
                }
            )
            if audio_bytes_out:
                await ws.send_bytes(audio_bytes_out)

        dial_action = bridge_result.get("dial_action")
        if isinstance(dial_action, dict):
            phone_number = dial_action.get("phone_number")
            if phone_number:
                delay_ms = int(duration_ms or 0) + 800
                with contextlib.suppress(Exception):
                    await ws.send_json(
                        {
                            "type": "dial_action",
                            "event_id": f"dial-{device_id}-{now_ts()}",
                            "contact_name": dial_action.get("contact_name", ""),
                            "phone_number": str(phone_number),
                            "source": bridge_result.get("source", "stt-dial"),
                            "delay_ms": delay_ms,
                            "ts": now_ts(),
                        }
                    )
                logger.info(
                    f"[WS] dial_action 전송: device_id={device_id}, "
                    f"contact={dial_action.get('contact_name')}, phone={phone_number}"
                )

        # 2026-07-11 지도 패널용: 경로 설정/해제 시 좌표 목록을 nav_route 메시지로
        # 전달한다. TMap appKey는 클라이언트 하드코딩 대신 서버 환경변수를 재사용해
        # 저장소에 키가 남지 않게 한다(키 노출 범위는 동일하므로 TMap 콘솔에서
        # 키 사용 제한을 걸어둘 것).
        if "nav_waypoints" in bridge_result:
            with contextlib.suppress(Exception):
                await ws.send_json(
                    {
                        "type": "nav_route",
                        "waypoints": bridge_result["nav_waypoints"],
                        "app_key": os.getenv("TMAP_APP_KEY", ""),
                        "ts": now_ts(),
                    }
                )
            logger.info(
                f"[WS] nav_route 전송: device_id={device_id}, "
                f"waypoints={len(bridge_result['nav_waypoints'])}"
            )

        logger.info(
            f"[WS] stt_audio 처리 완료: device_id={device_id}, text_len={len(stt_result.text)}, "
            f"source={bridge_result.get('source')}"
        )
        if guidance_text:
            latency_stages["total_ms"] = round((time.perf_counter() - stt_stage_start) * 1000, 1)
            upload_start = time.perf_counter()
            audio_upload_result = await upload_stt_audio(
                stt_event_id,
                audio_bytes,
                _audio_content_type_for_suffix(audio_suffix),
                audio_suffix.lstrip("."),
            )
            latency_stages["stt_audio_upload_ms"] = round(
                (time.perf_counter() - upload_start) * 1000,
                1,
            )
            # 콘솔 "파이프라인 지연 요약" 패널 실시간 갱신 (consumer.py._broadcast_latency_event와
            # 동일 목적/채널 - STT 경로는 DetectionConsumer 밖이라 여기서 직접 브로드캐스트한다).
            with contextlib.suppress(Exception):
                await manager.broadcast_json_to_consoles(
                    {
                        "type": "latency_event",
                        "event_id": stt_event_id,
                        "stream_type": "cognitive",
                        "latency": latency_stages,
                        "ts": now_ts(),
                    }
                )
            try:
                reg_user_id, reg_device_id = get_cached_device_ids(device_id)
                saved_log = await persist_detection_guidance_log(
                    event_id=stt_event_id,
                    stream_type="cognitive",
                    detections=[
                        {
                            "source": "stt",
                            "text_length": len(stt_result.text),
                            "stt_transcript": (stt_result.text or "").strip(),
                        }
                    ],
                    tts_text=guidance_text,
                    latency_stages=latency_stages,
                    user_id=reg_user_id,
                    device_id=reg_device_id,
                    pipeline_debug=build_stt_pipeline_debug(
                        stt_transcript=stt_result.text or "",
                        bridge_result=bridge_result,
                    ),
                    event_source="stt",
                    stt_transcript_text=(stt_result.text or "").strip() or None,
                    stt_audio_path=audio_upload_result.object_key,
                    stt_audio_storage_status=audio_upload_result.status,
                    stt_audio_format=audio_upload_result.format,
                    stt_audio_size_bytes=audio_upload_result.size_bytes,
                    stt_audio_duration_ms=(
                        int(stt_result.duration * 1000) if stt_result.duration is not None else None
                    ),
                    stt_audio_sha256=audio_upload_result.sha256,
                    stt_audio_error_code=audio_upload_result.error_code,
                )
                # 콘솔 Detection Guidance Log 테이블 실시간 갱신 (consumer.py._broadcast_guidance_log_event와
                # 동일 목적/채널 - DB 저장 완료 후에만 보내 콘솔이 즉시 썸네일을 요청해도 안전하다).
                with contextlib.suppress(Exception):
                    await manager.broadcast_json_to_consoles(
                        {"type": "guidance_log_event", "row": saved_log.model_dump(mode="json")}
                    )
            except Exception as e:
                logger.error(f"[WS] stt_audio DB 로그 저장 실패: device_id={device_id}, {e}")
        return _estimate_stt_hold_seconds(guidance_text, duration_ms)
    except (KeyError, ValueError, RuntimeError) as e:
        logger.error(f"[WS] STT 전사 실패: device_id={device_id}, {e}")
        error_text = "음성 인식에 실패했습니다. 다시 말씀해 주세요."
        with contextlib.suppress(Exception):
            await ws.send_json(
                {
                    "type": "guide",
                    "event_id": f"stt-error-{device_id}-{now_ts()}",
                    "risk_level": "low",
                    "guidance_text": error_text,
                    "audio_codec": "wav",
                    "duration_ms": 0,
                    "transport": "none",
                    "source": "stt-transcribe-error",
                    "ts": now_ts(),
                }
            )
        return _estimate_stt_hold_seconds(error_text)
    finally:
        if saved_path is not None:
            saved_path.unlink(missing_ok=True)
        with contextlib.suppress(Exception):
            from server.mcp.manager import mcp_manager

            await mcp_manager.broadcast_event(
                "stt_status", {"stt_status": "idle", "device_id": device_id}
            )


@router.websocket("/ws/console/live-feed")
async def ws_console_live_feed(ws: WebSocket) -> None:
    """관제 콘솔의 실시간 프레임 스트리밍 수신용 웹소켓 엔드포인트.

    receive_text()만 쓰면 클라이언트의 binary/disconnect 프레임에서 예외로
    끊기거나, uvicorn 재기동 후 반쯤 열린(half-open) 소켓을 감지하기 어렵다.
    receive()로 모든 메시지 타입을 흡수하고 disconnect만 정리한다.
    """
    await manager.connect_console(ws)
    try:
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000), message.get("reason"))
    except WebSocketDisconnect:
        manager.disconnect_console(ws)
    except Exception as e:
        logger.error(f"[ConsoleWS] 예외: {e}")
        manager.disconnect_console(ws)


@router.websocket("/ws/detect")
async def ws_detect(
    ws: WebSocket,
    device_id: str = Query(..., description="단말 식별자"),
) -> None:
    """WebSocket /ws/detect 엔드포인트.

    핸드셰이크 절차:
        1. accept -> welcome 송신
        2. hello 수신 -> 디바이스 토큰 검증 -> auth_ok 송신
        3. heartbeat 루프 시작
        4. detection 메시지 수신 시 프레임 디코딩 -> 스트림 분기 -> ack 응답

    가드레일:
        - WebSocketDisconnect: 소켓 close + 리소스 해제
        - JSONDecodeError: 1003 종료
        - decode_frame None 반환: ack 정상 응답 (파이프라인 영속성)
    """
    await manager.connect(device_id, ws)

    heartbeat: HeartbeatManager | None = None
    heartbeat_task: asyncio.Task[None] | None = None
    background_tasks: set[asyncio.Task] = set()

    try:
        await ws.send_json(
            {
                "type": "welcome",
                "session_id": device_id,
                "server_time": now_iso(),
            }
        )
        logger.info(f"[WS] welcome 송신 완료 - device_id: {device_id}")
        print(f"[DEBUG_WS] welcome 송신 완료 - device_id: {device_id}", flush=True)

        raw_hello = await ws.receive_text()
        logger.info(f"[WS] hello 수신 - raw: {raw_hello}")
        print(f"[DEBUG_WS] hello 수신 - raw: {raw_hello}", flush=True)
        hello_data = json.loads(raw_hello)

        if hello_data.get("type") != "hello":
            logger.warning(f"[WS] expected hello, but got: {hello_data.get('type')}")
            print(f"[DEBUG_WS] expected hello, but got: {hello_data.get('type')}", flush=True)
            await ws.send_json(
                {
                    "type": "error",
                    "code": "bad_request",
                    "message": "expected hello message",
                }
            )
            await ws.close(code=1008, reason="expected hello message")
            return

        token = hello_data.get("token", "")
        is_valid = await verify_device(device_id, token)
        if not is_valid:
            # 토큰 원문은 로그에 남기지 않는다(2026-07-11, dev 개선 계획서 §2 보안 기준).
            logger.warning(
                f"[WS] 디바이스 토큰 검증 실패 - device_id: {device_id}, token_len: {len(token)}"
            )
            print(
                f"[DEBUG_WS] 디바이스 토큰 검증 실패 - device_id: {device_id}, token_len: {len(token)}",
                flush=True,
            )
            await ws.send_json(
                {
                    "type": "error",
                    "code": "auth_failed",
                    "message": "디바이스 토큰 검증 실패",
                }
            )
            await ws.close(code=1008, reason="authentication failed")
            return

        logger.info(f"[WS] 토큰 검증 성공 - auth_ok 송신 - device_id: {device_id}")
        print(f"[DEBUG_WS] 토큰 검증 성공 - auth_ok 송신 - device_id: {device_id}", flush=True)
        # auth_ok 송신 "전"에 등록을 끝낸다: 클라이언트는 auth_ok를 받는 즉시 프레임을
        # 보내기 시작할 수 있어, 먼저 보내버리면 DetectionConsumer가 등록 완료 전에
        # 로그를 저장해 user_id/device_id가 NULL로 새는 레이스가 있었다(2026-07-12 실측 확인).
        try:
            await ensure_device_registered(device_id)
        except Exception as e:
            logger.error(f"[WS] 단말 자동 등록 실패: device_id={device_id}, {e}")
        await ws.send_json({"type": "auth_ok", "device_id": device_id})
        await _broadcast_session_status(device_id, "connected")
        await redis_bus.connect()

        # 2026-07-11: 재접속 시 지도 경로 복원. nav_route는 원래 경로 설정 순간에만
        # 전송되는데, 앱을 재시작하면 클라이언트 메모리의 경로가 사라져 서버 세션이
        # NAVIGATING인데도 지도 패널이 비어 있었다(실기기 확인). 서버 세션에 살아
        # 있는 웨이포인트를 인증 직후 재전송해 단말 재시작에도 지도를 복원한다.
        try:
            from server.navigation.manager import nav_manager

            if nav_manager.get_status(device_id) == "NAVIGATING":
                nav_session = nav_manager._get_or_create_session(device_id)
                if nav_session.waypoints:
                    await ws.send_json(
                        {
                            "type": "nav_route",
                            "waypoints": [
                                {"lat": wp["lat"], "lon": wp["lon"]} for wp in nav_session.waypoints
                            ],
                            "app_key": os.getenv("TMAP_APP_KEY", ""),
                            "ts": now_ts(),
                        }
                    )
                    logger.info(
                        f"[WS] nav_route 재전송(재접속 복원): device_id={device_id}, "
                        f"waypoints={len(nav_session.waypoints)}"
                    )
        except Exception as e:
            logger.error(f"[WS] nav_route 재전송 실패: device_id={device_id}, {e}")

        heartbeat = HeartbeatManager(
            ws,
            device_id,
            settings.HEARTBEAT_INTERVAL,
            settings.HEARTBEAT_TIMEOUT,
        )
        heartbeat_task = asyncio.create_task(heartbeat.start())

        splitter = get_default_splitter()

        # 바이너리 전송 프로토콜: 클라이언트가 detection 메타(JSON, transport="binary")를
        # 먼저 보내고 곧바로 raw JPEG 바이트를 바이너리 WS 프레임으로 전송한다. 단일 WS
        # 연결에서는 프레임 전송 순서가 보장되므로, 직전에 받은 메타를 여기에 잠시 보관해뒀다가
        # 바로 뒤이어 오는 바이너리 프레임과 짝지어 처리한다.
        pending_binary_meta: dict | None = None

        # YOLO/게이트(route_frame)는 Mac CPU에서 수백 ms~수 초가 걸릴 수 있다.
        # 메인 수신 루프에서 await하면 다음 프레임 receive가 막혀 콘솔 Live Feed가
        # 탐지 FPS(~1fps)로 끊긴다. ack+콘솔 중계는 즉시 하고, route만 백그라운드로
        # 넘긴다. 동시 추론은 1개로 제한하고 바쁠 때는 해당 프레임 탐지만 드롭한다
        # (최신성 우선, Live Feed 중계는 이미 끝난 상태).
        route_sem = asyncio.Semaphore(1)

        # 💡 [면접 대비 주석] 콘솔 Live Feed 전용 FPS 분리 (2026-07-17, P0).
        # 단말은 반사 경로 품질을 위해 5~8fps로 송신하지만, 운영자 모니터링 화면은
        # 3~5fps로 충분하다. 단말 송신률을 그대로 relay하면 대역폭·브라우저 디코드
        # 부하가 가중되고, 여러 콘솔 탭이 열린 환경에서 버퍼링이 누적된다.
        # ACK/YOLO 라우팅은 기존 단말 FPS를 그대로 유지하고, 콘솔 relay만 별도 쓰로틀.
        console_relay_interval_s = max(
            0.001,
            float(os.getenv("CONSOLE_RELAY_MIN_INTERVAL_S", "0.2")),  # 0.2s = 5fps
        )
        last_console_relay_ts: float = 0.0

        async def _route_detection_bg(
            processed_frame,
            route_event_id: str,
            route_frame_id: int,
            route_decode_ms: float,
            route_b64_len: int = 0,
        ) -> None:
            if route_sem.locked():
                logger.debug(
                    "[WS] detection route busy - drop event_id=%s frame_id=%s",
                    route_event_id,
                    route_frame_id,
                )
                return
            async with route_sem:
                await _route_detection_frame(
                    splitter,
                    processed_frame,
                    route_event_id,
                    route_frame_id,
                    route_decode_ms,
                    route_b64_len,
                )

        # stt_audio 처리(STT+LLM+TTS)는 수 초~수십 초가 걸릴 수 있어(2026-07-09 실측:
        # 로컬 tiny 모델+gemma4:e4b만으로도 약 10초), 메인 수신 루프에서 inline await로
        # 처리하면 그동안 ws.receive()가 멈춰 클라이언트의 heartbeat_ack를 못 받아
        # HeartbeatManager가 타임아웃으로 연결을 강제 종료해버린다(응답을 다 만들어놓고도
        # 전송 직전에 끊기는 것을 실측으로 확인). 다른 메시지 타입과 달리 백그라운드
        # asyncio.Task(background_tasks)로 분리해 메인 루프가 계속 heartbeat/다른
        # 메시지를 처리하게 한다.

        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(message.get("code", 1000), message.get("reason"))

            raw_bytes = message.get("bytes")
            if raw_bytes is not None:
                if pending_binary_meta is None:
                    logger.warning("[WS] 대기 중인 메타데이터 없이 바이너리 프레임 수신 - 무시")
                    continue

                meta = pending_binary_meta
                pending_binary_meta = None
                event_id = meta.get("event_id", "unknown")
                frame_id = meta.get("frame_id", 0)

                decode_start = time.perf_counter()
                processed = await decode_frame_binary(raw_bytes, meta)
                decode_ms = (time.perf_counter() - decode_start) * 1000

                # 💡 [면접 대비 주석] ACK를 콘솔 중계보다 먼저 보낸다 (2026-07-17, P0).
                # 기존 순서(broadcast -> ack)에서는 느린 콘솔 send가 단말 ACK를 지연시켜
                # 단말의 in-flight 프레임 제한(A2)이 동작하지 못하고 버퍼링이 누적됐다.
                # ACK는 단말과의 계약이므로 콘솔 relay 상태와 독립되어야 한다.
                # 콘솔 중계는 이제 session_manager의 latest-only 큐로 분리되어 논블로킹이다.
                await _send_detection_ack(ws, event_id, frame_id, decode_ms)

                # 콘솔 relay FPS 분리(A5): 설정 주기 이내면 relay 건너뛰기(최신 프레임만 유지 목적).
                relay_now = time.perf_counter()
                if relay_now - last_console_relay_ts >= console_relay_interval_s:
                    last_console_relay_ts = relay_now
                    await manager.broadcast_to_consoles(raw_bytes)

                task = asyncio.create_task(
                    _route_detection_bg(processed, event_id, frame_id, decode_ms, len(raw_bytes))
                )
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)
                continue

            raw = message.get("text")
            if raw is None:
                continue
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type in ("heartbeat_ack", "pong"):
                if heartbeat:
                    heartbeat.record_ack()
                    await _broadcast_session_status(
                        device_id, "connected", rtt_ms=heartbeat.last_rtt_ms
                    )

            elif msg_type == "ping":
                # HeartbeatManager와의 동시 close 레이스 방지 (ack 전송과 동일 사유)
                with contextlib.suppress(Exception):
                    await ws.send_json(
                        {
                            "type": "pong",
                            "ts": now_ts(),
                        }
                    )

            elif msg_type == "heartbeat":
                with contextlib.suppress(Exception):
                    await ws.send_json(
                        {
                            "type": "heartbeat_ack",
                            "ts": now_ts(),
                        }
                    )

            elif msg_type == "network_probe":
                payload = data.get("payload", "")
                payload_bytes = len(payload.encode("utf-8")) if isinstance(payload, str) else 0
                with contextlib.suppress(Exception):
                    await ws.send_json(
                        {
                            "type": "network_probe_ack",
                            "probe_id": data.get("probe_id", ""),
                            "client_sent_ts": data.get("client_sent_ts"),
                            "client_label": data.get("client_label", ""),
                            "payload_bytes": payload_bytes,
                            "server_received_ts": now_ts(),
                            "server_sent_ts": now_ts(),
                        }
                    )

            elif msg_type == "detection":
                payload = data.get("payload", {})
                event_id = payload.get("event_id", "unknown")
                frame_id = payload.get("frame_id", 0)

                # GPS 데이터 수신 시 NavigationManager로 위치 정보 업데이트 전파
                gps_data = payload.get("gps")
                if gps_data and isinstance(gps_data, dict):
                    lat = gps_data.get("lat")
                    lon = gps_data.get("lon")
                    heading = gps_data.get("heading")
                    if lat is not None and lon is not None:
                        from server.navigation.manager import nav_manager

                        nav_manager.update_gps(
                            device_id,
                            float(lat),
                            float(lon),
                            float(heading) if heading is not None else None,
                        )

                if payload.get("transport") == "binary":
                    # 뒤이어 도착할 바이너리 프레임을 대기 (ack는 그때 응답)
                    pending_binary_meta = payload
                    continue

                # 구버전 호환 경로: base64 JPEG가 payload에 직접 포함된 단일 메시지
                decode_start = time.perf_counter()
                processed = await decode_frame(payload)
                decode_ms = (time.perf_counter() - decode_start) * 1000

                b64_val = payload.get("thumbnail_jpeg_b64")
                b64_len = len(b64_val) if b64_val else 0
                if b64_val:
                    with contextlib.suppress(Exception):
                        b64_for_decode = b64_val
                        if isinstance(b64_for_decode, str) and b64_for_decode.startswith("data:"):
                            parts = b64_for_decode.split(",", 1)
                            if len(parts) == 2:
                                b64_for_decode = parts[1]
                        raw_bytes = base64.b64decode(b64_for_decode)
                # 2026-07-17: ACK를 콘솔 중계보다 먼저 (P0). 바이너리 경로와 동일한 순서.
                await _send_detection_ack(ws, event_id, frame_id, decode_ms)
                if raw_bytes is not None:
                    await manager.broadcast_to_consoles(raw_bytes)
                task = asyncio.create_task(
                    _route_detection_bg(processed, event_id, frame_id, decode_ms, b64_len)
                )
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)

            elif msg_type == "stt_audio":
                logger.info(
                    f"[WS] stt_audio 수신: device_id={device_id}, "
                    f"audio_b64_len={len(data.get('audio_b64', ''))}"
                )
                task = asyncio.create_task(_handle_stt_audio(ws, device_id, data))
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)

            elif msg_type == "detection_control":
                # 클라이언트 "탐지 시작/중지" 토글. OFF면 목적지/인텐트 대기를 풀고
                # STT 일반 발화를 자유 질문으로 라우팅한다(탐지 끄고 질문 무응답 실측).
                enabled = bool(data.get("enabled", False))
                from server.navigation.manager import nav_manager

                nav_manager.set_detection_enabled(device_id, enabled)
                logger.info(f"[WS] detection_control: device_id={device_id}, enabled={enabled}")

            elif msg_type == "realtime_gps":
                lat = data.get("lat")
                lon = data.get("lon")
                heading = data.get("heading")
                if lat is not None and lon is not None:
                    from server.navigation.manager import nav_manager

                    nav_manager.update_gps(
                        device_id,
                        float(lat),
                        float(lon),
                        float(heading) if heading is not None else None,
                    )
                    logger.debug(
                        f"[WS] realtime_gps 수신: device_id={device_id}, "
                        f"lat={lat}, lon={lon}, heading={heading}"
                    )
                    # 콘솔 HUD 미니맵 실시간 갱신: 앱 실기기 GPS 좌표를 콘솔로 브로드캐스트.
                    # useLiveFeed가 이 메시지를 받아 lastGps 상태를 갱신하고,
                    # LiveCameraFeed가 HUD 미니맵 iframe에 postMessage로 주입한다.
                    with contextlib.suppress(Exception):
                        await manager.broadcast_json_to_consoles(
                            {
                                "type": "realtime_gps",
                                "lat": float(lat),
                                "lon": float(lon),
                                "heading": float(heading) if heading is not None else 0,
                                "device_id": device_id,
                                "ts": now_ts(),
                            }
                        )
                    # 2026-07-11 길안내 무음 수정: 기존에는 길안내 멘트 조회가
                    # DetectionConsumer._send_cognitive_guide 안에만 있어 카메라 탐지가
                    # 없으면(빈 장면) NAVIGATING 상태여도 안내가 전혀 나가지 않았다
                    # (실기기 실측: 경로 113 웨이포인트 설정 후 무음). 길안내는 위치
                    # 이벤트가 본질이므로 GPS 갱신 시점에 직접 평가한다. 중복 발화는
                    # nav_filter의 announced_cache/silence_interval이 양쪽 경로 공용으로
                    # 차단한다. 조회는 동기(중복 판정 원자성 보장), 합성·전송만 태스크로
                    # 분리해 수신 루프를 막지 않는다.
                    if nav_manager.get_status(device_id) == "NAVIGATING":
                        try:
                            nav_event = nav_manager.get_combined_guidance(device_id)
                        except Exception as e:
                            logger.error(f"[WS] 길안내 조회 실패: device_id={device_id}, {e}")
                            nav_event = None
                        if nav_event and nav_event.get("text"):
                            task = asyncio.create_task(_send_nav_guidance(ws, device_id, nav_event))
                            background_tasks.add(task)
                            task.add_done_callback(background_tasks.discard)

            elif msg_type == "distance_probe_sample":
                task = asyncio.create_task(_handle_distance_probe_sample(device_id, data))
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)

            else:
                logger.warning(f"[WS] 알 수 없는 메시지 타입: {msg_type}")

    except WebSocketDisconnect as e:
        logger.info(f"[WS] 연결 끊김: device_id={device_id}, code={e.code}")
    except json.JSONDecodeError as e:
        logger.error(f"[WS] JSON 파싱 오류: {e}")
        with contextlib.suppress(Exception):
            await ws.close(code=1003, reason="invalid JSON")
    except Exception as e:
        logger.error(f"[WS] 예기치 않은 오류: device_id={device_id}, error={e}")
    finally:
        manager.disconnect(device_id, ws)
        await _broadcast_session_status(device_id, "disconnected")
        if heartbeat:
            heartbeat.stop()
        if heartbeat_task:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
        for task in list(background_tasks):
            task.cancel()
        logger.info(f"[WS] 세션 종료: device_id={device_id}")
