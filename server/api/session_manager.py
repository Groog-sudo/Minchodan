"""
WebSocket 세션 관리자.
활성 WebSocket 연결을 추적하고 관리하는 싱글턴 클래스.
"""

import asyncio
import contextlib
import logging
import sys
import time
from dataclasses import dataclass, field

from fastapi import WebSocket
from starlette.websockets import WebSocketState

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


@dataclass
class _ConsoleSession:
    # 💡 [면접 대비 주석] 콘솔 연결별 송신 세션.
    # 느린 콘솔 하나가 send 버퍼가 찰 때까지 await 블록되면, 기존 순차 루프 구조에서는
    # 다음 단말 ACK 수신·다른 콘솔 중계까지 줄줄이 밀리는 글로벌 직렬화 지점이 된다.
    # 이를 분리하기 위해 (1) 콘솔마다 전용 송신 worker 코루틴, (2) maxsize=1 latest-only 큐를 둔다.
    # 큐가 꽉 찬 상태에서 새 프레임이 오면 대기 중인 이전 프레임을 버리고 최신으로 교체한다.
    # 실시간 모니터링에서는 "모든 프레임 처리"보다 "최신 프레임 우선"이 안전 기준에 부합한다.
    ws: WebSocket
    queue: asyncio.Queue[tuple[str, bytes | dict]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=1)
    )
    worker: asyncio.Task | None = None


class SessionManager:
    """활성 WebSocket 연결을 추적하고 관리하는 싱글턴 클래스."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self.console_connections: set[WebSocket] = set()
        self._console_sessions: dict[WebSocket, _ConsoleSession] = {}
        # T3-S (2026-07-18): 디바이스별 STT 상호작용 활성 상태. consumer가 인지 가이드
        # 발행을 억제할 때 참조한다. 값은 monotonic 시간 기준 만료 시각.
        self._stt_activity: dict[str, float] = {}
        # guide 오디오 미러 송신 태스크 참조 유지(RUF006: dangling create_task 방지).
        self._guide_audio_tasks: set[asyncio.Task[None]] = set()

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        """새 연결 수락 및 등록.

        동일 device_id의 잔류 세션이 있으면 강제 종료 후 교체한다.
        망 전환(Wi-Fi <-> 핫스팟) 또는 앱 강제 종료 시 기존 TCP 연결이 FIN 없이
        사라져 서버에 세션이 잔류하는 문제를 방지한다.
        """
        await websocket.accept()
        await self.register_authenticated(device_id, websocket)

    async def register_authenticated(self, device_id: str, websocket: WebSocket) -> None:
        """인증이 끝난 소켓만 활성 세션으로 등록한다."""
        old_ws = self.active_connections.get(device_id)
        if old_ws is not None:
            with contextlib.suppress(Exception):
                await old_ws.close(code=1001, reason="replaced by new connection")
            self.active_connections.pop(device_id, None)
            logger.info(f"[Session] 잔류 세션 강제 종료: device_id={device_id}")

        self.active_connections[device_id] = websocket
        logger.info(
            f"[Session] 연결: device_id={device_id}, 현재 접속: {len(self.active_connections)}명"
        )

    async def connect_console(self, websocket: WebSocket, accept: bool = True) -> None:
        """새 관제 콘솔 연결 수락 및 등록.

        연결별 전용 송신 worker를 함께 띄운다(2026-07-17, 역압력 분리).
        2026-07-19: accept=False 옵션 추가 - WebSocket 수락 전 인증을 먼저
        수행한 뒤 등록만 하고 싶은 경우(connect_console 이전에 JWT 검증).
        """
        if accept:
            await websocket.accept()
        self.console_connections.add(websocket)
        session = _ConsoleSession(ws=websocket)
        session.worker = asyncio.create_task(
            self._console_sender_loop(session),
            name=f"console-sender-{id(websocket)}",
        )
        self._console_sessions[websocket] = session
        logger.info(f"[Session] 콘솔 연결됨. 현재 콘솔 수: {len(self.console_connections)}")

    def disconnect_console(self, websocket: WebSocket) -> None:
        """관제 콘솔 연결 해제 및 등록 삭제. 송신 worker도 함께 취소한다."""
        if websocket in self.console_connections:
            self.console_connections.remove(websocket)
        session = self._console_sessions.pop(websocket, None)
        if session is not None and session.worker is not None:
            session.worker.cancel()
        logger.info(f"[Session] 콘솔 해제됨. 남은 콘솔 수: {len(self.console_connections)}")

    async def _console_sender_loop(self, session: _ConsoleSession) -> None:
        """콘솔 전용 송신 worker. latest-only 큐에서 꺼내 전송.

        이 코루틴이 콘솔별로 독립 실행되므로, 한 콘솔의 send 지연이
        다른 콘솔이나 단말 수신 루프로 전파되지 않는다.
        """
        ws = session.ws
        try:
            while True:
                kind, payload = await session.queue.get()
                try:
                    if ws.application_state != WebSocketState.CONNECTED:
                        break
                    if kind == "bytes":
                        await ws.send_bytes(payload)
                    else:
                        await ws.send_json(payload)
                except Exception as e:
                    logger.error(f"[Session] 콘솔 송신 예외: {e}")
                    self.disconnect_console(ws)
                    break
        except asyncio.CancelledError:
            raise

    def _enqueue_console(self, kind: str, data: bytes | dict) -> None:
        """모든 콘솔 큐에 latest-only 인큐.

        큐가 꽉 찬 경우 대기 중이던 이전 프레임을 버리고 최신으로 교체한다.
        인큐 자체는 논블로킹이므로 호출부(단말 수신 루프 등)를 블록하지 않는다.
        """
        stale_consoles: list[WebSocket] = []
        for ws in list(self.console_connections):
            if ws.application_state != WebSocketState.CONNECTED:
                stale_consoles.append(ws)
                continue
            session = self._console_sessions.get(ws)
            if session is None:
                continue
            try:
                session.queue.put_nowait((kind, data))
            except asyncio.QueueFull:
                # latest-only: 대기 중이던 이전 프레임 폐기 후 최신으로 교체
                with contextlib.suppress(asyncio.QueueEmpty):
                    session.queue.get_nowait()
                with contextlib.suppress(asyncio.QueueFull):
                    session.queue.put_nowait((kind, data))
        for ws in stale_consoles:
            self.disconnect_console(ws)

    async def broadcast_to_consoles(self, data: bytes) -> None:
        """모든 활성 관제 콘솔 웹소켓에 raw bytes (이미지 프레임) 전송.

        2026-07-17: 직렬 await 대신 콘솔별 latest-only 큐에 인큐한다.
        실시간성 복구(P0) - 느린 콘솔이 단말 ACK·다른 콘솔 중계를 지연시키지 않는다.
        """
        self._enqueue_console("bytes", data)

    async def broadcast_json_to_consoles(self, data: dict) -> None:
        """모든 활성 관제 콘솔 웹소켓에 JSON 데이터(BBox 등) 전송.

        2026-07-17: 직렬 await 대신 콘솔별 latest-only 큐에 인큐한다.
        """
        self._enqueue_console("json", data)

    async def broadcast_guide_audio_to_consoles(
        self,
        meta: dict,
        audio_bytes: bytes,
    ) -> None:
        """인지 가이드 오디오를 콘솔에 JSON+WAV 쌍으로 전달한다.

        latest-only 큐(maxsize=1)를 쓰면 JSON 직후 WAV를 넣을 때 앞선 JSON이
        드롭되어 콘솔이 영원히 '대기 중'에 머문다(2026-07-19 실측).
        이 경로만 큐를 우회해 쌍을 원자적으로 보낸다. 느린 콘솔은 태스크로 분리.
        """
        if not self.console_connections:
            return

        async def _send_pair(ws: WebSocket) -> None:
            try:
                if ws.application_state != WebSocketState.CONNECTED:
                    self.disconnect_console(ws)
                    return
                await ws.send_json(meta)
                if audio_bytes:
                    await ws.send_bytes(audio_bytes)
            except Exception as e:
                logger.error(f"[Session] 콘솔 guide 오디오 송신 예외: {e}")
                self.disconnect_console(ws)

        for ws in list(self.console_connections):
            task = asyncio.create_task(
                _send_pair(ws),
                name=f"console-guide-audio-{id(ws)}",
            )
            self._guide_audio_tasks.add(task)
            task.add_done_callback(self._guide_audio_tasks.discard)

    def disconnect(self, device_id: str, websocket: WebSocket | None = None) -> None:
        """연결 해제 및 등록 삭제."""
        current = self.active_connections.get(device_id)
        if current is None or (websocket is not None and current is not websocket):
            return

        self.active_connections.pop(device_id, None)
        if current is not None:
            logger.info(
                f"[Session] 해제: device_id={device_id}, "
                f"현재 접속: {len(self.active_connections)}명"
            )

    async def send_json(self, device_id: str, data: dict) -> bool:
        """특정 디바이스에 JSON 메시지 송신.

        2026-07-11: WebSocket application_state가 CONNECTED인 경우에만 송신한다.
        WS 연결이 끊어진 뒤에도 active_connections에서 즉시 제거되지 않는 경쟁
        창(consumer 태스크가 독립적으로 실행 중)에서 send를 시도하면
        "Cannot call send once a close message has been sent" 에러가 스팸으로
        발생했던 문제(13:26:47~52 로그, 17회 반복)를 방지한다.
        """
        ws = self.active_connections.get(device_id)
        if not ws or ws.application_state != WebSocketState.CONNECTED:
            return False
        await ws.send_json(data)
        return True

    async def send_bytes(self, device_id: str, data: bytes) -> bool:
        """특정 디바이스에 바이너리(raw bytes) 프레임 송신.

        인지 경로 guide 오디오(WAV)를 base64 문자열로 JSON에 실어 보내는 대신
        원본 바이트를 그대로 전송한다(2026-07-09 도입). base64는 페이로드를
        33% 부풀리고, RN 구 브릿지에서 대용량 문자열을 다루는 경로를 추가로
        거치게 한다 - 실기기에서 문장 중간 음절이 산발적으로 사라지는 현상의
        원인 후보를 좁히기 위해, 카메라 프레임 전송(client->server)에 이미
        적용된 바이너리 프레임 패턴을 반대 방향(server->client)에도 적용한다.
        """
        ws = self.active_connections.get(device_id)
        if not ws or ws.application_state != WebSocketState.CONNECTED:
            return False
        await ws.send_bytes(data)
        return True

    def is_connected(self, device_id: str) -> bool:
        """디바이스 연결 여부 확인. application_state도 함께 검증한다."""
        ws = self.active_connections.get(device_id)
        return ws is not None and ws.application_state == WebSocketState.CONNECTED

    def list_connected_device_ids(self) -> list[str]:
        """현재 CONNECTED 상태인 device_id 목록을 반환한다.

        # 💡 [면접 대비 주석]
        Q. 왜 dict 키만 안 보고 application_state까지 보나?
        A. 끊긴 소켓이 맵에 남을 수 있다. debug TTS 푸시 대상은 실제 CONNECTED만.
        """
        # [바이브 코딩 부분] CONNECTED 필터 목록 생성.
        return [
            device_id
            for device_id, ws in self.active_connections.items()
            if ws.application_state == WebSocketState.CONNECTED
        ]

    def set_stt_active(self, device_id: str, active: bool, ttl_seconds: float = 0.0) -> None:
        """디바이스별 STT 상호작용 활성 상태를 설정한다.

        T3-S (2026-07-18): STT 처리 중 인지 경로 발행을 억제하기 위한 레지스트리.
        active=False이고 ttl_seconds>0이면 ttl_seconds 후에 자동 만료된다.
        """
        if active:
            expire_at = time.monotonic() + ttl_seconds if ttl_seconds > 0 else float("inf")
            self._stt_activity[device_id] = expire_at
            logger.debug(f"[Session] STT 활성: device_id={device_id}")
        else:
            if ttl_seconds > 0:
                self._stt_activity[device_id] = time.monotonic() + ttl_seconds
                logger.debug(
                    f"[Session] STT 활성 TTL 연장: device_id={device_id}, ttl={ttl_seconds:.1f}s"
                )
            else:
                self._stt_activity.pop(device_id, None)
                logger.debug(f"[Session] STT 비활성: device_id={device_id}")

    def is_stt_active(self, device_id: str) -> bool:
        """디바이스가 STT 상호작용 중인지 확인한다. TTL이 만료된 항목은 정리한다."""
        expire_at = self._stt_activity.get(device_id)
        if expire_at is None:
            return False
        if time.monotonic() > expire_at:
            self._stt_activity.pop(device_id, None)
            return False
        return True


manager = SessionManager()
