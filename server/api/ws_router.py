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
import sys
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from server.api.auth import verify_device
from server.api.config import settings
from server.api.heartbeat import HeartbeatManager
from server.api.schemas import now_iso, now_ts
from server.api.session_manager import manager
from server.bus.redis_client import redis_bus
from server.capture.frame_decoder import decode_frame, decode_frame_binary
from server.capture.stream_splitter import get_default_splitter
from server.services.detection_guidance_log_service import persist_detection_guidance_log
from server.stt.stt_service import SttService
from server.stt.stt_to_llm_bridge import SttToLlmBridge
from server.tts.realtime_tts import realtime_tts

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)
router = APIRouter()


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
    """
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

    # HeartbeatManager가 다른 태스크에서 동시에 타임아웃 close를 걸 수 있어(레이스),
    # ack 전송 실패가 세션 전체를 죽이지 않도록 여기서 흡수한다. 소켓이 실제로
    # 끊겼다면 메인 루프의 다음 ws.receive()가 WebSocketDisconnect로 정상 정리한다.
    with contextlib.suppress(Exception):
        await ws.send_json(
            {
                "type": "ack",
                "event_id": event_id,
                "frame_id": frame_id,
                "decode_ms": round(decode_ms, 2),
            }
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


async def _handle_stt_audio(ws: WebSocket, device_id: str, data: dict) -> None:
    """STT 음성 명령 메시지를 처리한다: 오디오 저장 -> 전사 -> 네비게이션/LLM 브리지 -> TTS 합성.

    응답은 기존 인지 경로 클라이언트 핸들러가 이미 처리 가능한 "guide" 타입으로 보낸다
    (client/src/hooks/useWebSocket.ts가 audio_mp3_b64 수신 시 자동 재생하므로 클라이언트
    쪽에 별도 신규 메시지 타입 처리를 추가할 필요가 없다).

    2026-07-09: server/stt/*.py(SttService, SttToLlmBridge)는 완성돼 있었으나 어떤
    라우터에서도 호출되지 않아 서버가 STT 요청을 받을 경로 자체가 없었다(main.py에는
    STT 라우팅이 전혀 없고, server/navigation/server.py는 별도 FastAPI 앱이라 클라이언트가
    실제로 붙는 /ws/detect와 무관했다). 이 핸들러가 그 배선을 연결한다.
    """
    audio_b64 = data.get("audio_b64", "")
    if not audio_b64:
        logger.warning(f"[WS] stt_audio 메시지에 audio_b64 없음: device_id={device_id}")
        return

    async with _get_stt_lock(device_id):
        await _process_stt_audio(ws, device_id, data, audio_b64)


async def _process_stt_audio(ws: WebSocket, device_id: str, data: dict, audio_b64: str) -> None:
    model_name = data.get("model_name")

    try:
        audio_bytes = base64.b64decode(audio_b64)
    except (ValueError, TypeError) as e:
        logger.error(f"[WS] stt_audio base64 디코딩 실패: device_id={device_id}, {e}")
        return

    saved_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav.write(audio_bytes)
            saved_path = Path(temp_wav.name)

        stt_result = await asyncio.to_thread(
            SttService.transcribe_file, saved_path=saved_path, model_name=model_name
        )
        bridge_result = await _stt_bridge.invoke_existing_llm(stt_result, device_id)
        guidance_text = bridge_result.get("guidance_text", "")

        audio_mp3_b64, duration_ms = await realtime_tts.synthesize(text=guidance_text)
        stt_event_id = f"stt-{device_id}-{now_ts()}"

        # 2026-07-09에 인지 경로(DetectionConsumer._send_cognitive_guide)가 오디오를
        # audio_mp3_b64(JSON base64)에서 transport:"binary" + 별도 바이너리 프레임으로
        # 옮기면서 클라이언트(useWebSocket.ts)도 transport!=="binary"면 무조건 단말
        # TTS(speakFallback)로 즉시 폴백하도록 바뀌었다. 이 STT 경로가 그 마이그레이션에서
        # 빠져 있어 서버가 합성한 오디오를 클라이언트가 항상 무시하고 있었다(실기기 실측
        # 확인, 2026-07-10) - 인지 경로와 동일한 전송 방식으로 맞춘다.
        audio_bytes_out = base64.b64decode(audio_mp3_b64) if audio_mp3_b64 else b""

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
        logger.info(
            f"[WS] stt_audio 처리 완료: device_id={device_id}, text_len={len(stt_result.text)}, "
            f"source={bridge_result.get('source')}"
        )
        if guidance_text:
            try:
                await persist_detection_guidance_log(
                    event_id=stt_event_id,
                    stream_type="cognitive",
                    detections=[{"source": "stt", "transcript": stt_result.text}],
                    tts_text=guidance_text,
                )
            except Exception as e:
                logger.error(f"[WS] stt_audio DB 로그 저장 실패: device_id={device_id}, {e}")
    except (KeyError, ValueError, RuntimeError) as e:
        logger.error(f"[WS] STT 전사 실패: device_id={device_id}, {e}")
        with contextlib.suppress(Exception):
            await ws.send_json(
                {
                    "type": "guide",
                    "event_id": f"stt-error-{device_id}-{now_ts()}",
                    "risk_level": "low",
                    "guidance_text": "음성 인식에 실패했습니다. 다시 말씀해 주세요.",
                    "audio_codec": "wav",
                    "duration_ms": 0,
                    "transport": "none",
                    "source": "stt-transcribe-error",
                    "ts": now_ts(),
                }
            )
    finally:
        if saved_path is not None:
            saved_path.unlink(missing_ok=True)


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
            logger.warning(f"[WS] 디바이스 토큰 검증 실패 - device_id: {device_id}, token: {token}")
            print(
                f"[DEBUG_WS] 디바이스 토큰 검증 실패 - device_id: {device_id}, token: {token}",
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
        await ws.send_json({"type": "auth_ok", "device_id": device_id})
        await redis_bus.connect()

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

                await _finish_detection(
                    ws, splitter, processed, event_id, frame_id, decode_ms, len(raw_bytes)
                )
                continue

            raw = message.get("text")
            if raw is None:
                continue
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type in ("heartbeat_ack", "pong"):
                if heartbeat:
                    heartbeat.record_ack()

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
                await _finish_detection(
                    ws, splitter, processed, event_id, frame_id, decode_ms, b64_len
                )

            elif msg_type == "stt_audio":
                logger.info(
                    f"[WS] stt_audio 수신: device_id={device_id}, "
                    f"audio_b64_len={len(data.get('audio_b64', ''))}"
                )
                task = asyncio.create_task(_handle_stt_audio(ws, device_id, data))
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)

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
        manager.disconnect(device_id)
        if heartbeat:
            heartbeat.stop()
        if heartbeat_task:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
        for task in list(background_tasks):
            task.cancel()
        logger.info(f"[WS] 세션 종료: device_id={device_id}")
