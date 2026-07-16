# WebSocket Gateway — 상세 구현 레퍼런스

## 1. 통신 프로토콜 상세

### 1.1 메시지 타입 정의 (JSON 프로토콜)

모든 WebSocket 메시지는 JSON 형식이며, 최상위 `type` 필드로 구분한다.

| type | 방향 | 설명 | 필수 필드 |
|------|------|------|-----------|
| `welcome` | 서버클라이언트 | 연결 수락 직후 전송 | `session_id`, `server_time` |
| `hello` | 클라이언트서버 | 인증 요청 | `device_id`, `token` |
| `auth_ok` | 서버클라이언트 | 인증 성공 응답 | `device_id` |
| `error` | 서버클라이언트 | 오류 알림 | `message`, `code`(선택) |
| `ping` | 양방향 | 하트비트 요청 | `ts` |
| `pong` | 양방향 | 하트비트 응답 | `ts` |
| `detection` | 클라이언트서버 | 카메라 프레임 + 감지 데이터 | `payload` 객체 |
| `ack` | 서버클라이언트 | detection 수신 확인 | `event_id`, `received_at` |
| `alert` | 서버클라이언트 | 위험 알림 (TTS 안내용) | `payload` 객체 |

### 1.2 메시지 시퀀스 다이어그램

```
클라이언트(앱)                              서버(FastAPI)
    │                                          │
    │ ─── TCP Handshake + WS Upgrade ────────► │
    │                                          │ ws.accept()
    │ ◄──────── welcome {session_id} ────────  │
    │                                          │
    │ ─── hello {device_id, token} ──────────► │
    │                                          │ verify_device()
    │ ◄──────── auth_ok {device_id} ──────────│
    │                                          │
    │ ═══════ 양방향 통신 루프 시작 ═══════════ │
    │                                          │
    │ ─── ping {ts} ─────────────────────────► │
    │ ◄──────── pong {ts} ────────────────────│
    │                                          │
    │ ◄──────── ping {ts} ────────────────────│ (서버 측 하트비트)
    │ ─── pong {ts} ─────────────────────────► │
    │                                          │
    │ ─── detection {payload} ───────────────► │
    │                                          │  redis xadd
    │ ◄──────── ack {event_id} ───────────────│
    │                                          │
    │ ◄──────── alert {payload} ──────────────│ (위험 감지 시)
    │                                          │
```

### 1.3 DetectionEvent payload 전체 구조

```json
{
  "type": "detection",
  "payload": {
    "event_id": "evt-1687654321000-042",
    "device_id": "dev-001",
    "timestamp": "2025-06-21T14:30:00.000Z",
    "frame_id": 1234,
    "gps": {
      "lat": 37.5665,
      "lon": 126.9780,
      "accuracy": 5.2
    },
    "thumbnail_jpeg_b64": "/9j/4AAQSkZJRgABAQ...",
    "detections": []
  }
}
```

> **참고**: 2단계(camera-frame-capture)에서 detections 배열은 빈 배열로 전송하며, 3단계(YOLO 감지)에서 서버가 채운다.

## 2. 연결 라이프사이클 상세

### 2.1 연결 수립 플로우

```python
# 연결 URL 형식
# ws://{SERVER_HOST}:{PORT}/ws/detect?device_id={DEVICE_ID}
# 예: ws://192.168.0.10:8000/ws/detect?device_id=dev-001

# Query Parameter:
#   device_id (필수): 디바이스 고유 식별자
```

### 2.2 WebSocket Close 코드 정의

| 코드 | 의미 | 발생 상황 |
|------|------|-----------|
| 1000 | 정상 종료 | 앱 종료, 명시적 disconnect |
| 1001 | Going Away | 하트비트 타임아웃 |
| 1003 | Unsupported Data | JSON 파싱 실패 |
| 1008 | Policy Violation | 인증 실패, 프로토콜 위반 |
| 1011 | Unexpected Condition | 서버 내부 오류 |

### 2.3 재연결 알고리즘 (클라이언트 측)

```typescript
// 지수 백오프 + 최대 재연결 횟수 제한
const INITIAL_DELAY = 1000;     // 1초
const MAX_DELAY = 30000;        // 30초
const MAX_ATTEMPTS = 3;         // 최대 3회
const BACKOFF_FACTOR = 2;       // 지수 백오프 배율

function getReconnectDelay(attempt: number): number {
  const delay = INITIAL_DELAY * Math.pow(BACKOFF_FACTOR, attempt);
  return Math.min(delay, MAX_DELAY);
}

// 재연결 실패 시  로컬 폴백 모드
// 로컬 폴백 모드란:
//   - 카메라 프레임을 로컬 스토리지에 버퍼링
//   - 연결 복구 시 버퍼링된 프레임을 일괄 전송
//   - 사용자에게 "서버 연결 끊김" 음성 알림 (TTS)
```

## 3. 하트비트 메커니즘 상세

### 3.1 서버 측 하트비트 구현 (개선 버전)

```python
# server/api/heartbeat.py (개선 버전)

import asyncio
import time
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class HeartbeatManager:
    """
    하트비트 매니저.
    서버클라이언트: 5초마다 ping, 5초 내 pong 없으면 종료
    클라이언트서버: 클라이언트가 보내는 ping에 대해 pong 응답
    """

    def __init__(self, ws: WebSocket, device_id: str, interval: int = 5, timeout: int = 5):
        self.ws = ws
        self.device_id = device_id
        self.interval = interval
        self.timeout = timeout
        self.last_pong_time: float = time.time()
        self._running = True

    async def start(self):
        """하트비트 루프를 시작한다."""
        while self._running:
            await asyncio.sleep(self.interval)

            # 마지막 pong 이후 경과 시간 확인
            elapsed = time.time() - self.last_pong_time
            if elapsed > (self.interval + self.timeout):
                logger.warning(
                    f"[하트비트] 타임아웃: device_id={self.device_id}, "
                    f"마지막 pong으로부터 {elapsed:.1f}초 경과"
                )
                await self.ws.close(code=1001, reason="heartbeat timeout")
                break

            try:
                await self.ws.send_json({
                    "type": "ping",
                    "ts": time.time()
                })
            except Exception as e:
                logger.error(f"[하트비트] ping 전송 실패: {e}")
                break

    def record_pong(self):
        """pong 수신 시 호출하여 시간을 갱신한다."""
        self.last_pong_time = time.time()

    def stop(self):
        """하트비트 루프를 중지한다."""
        self._running = False
```

### 3.2 ws_routes.py와 HeartbeatManager 통합 (개선 버전)

```python
# ws_routes.py에서 HeartbeatManager 사용 시:

from .heartbeat import HeartbeatManager

@router.websocket("/ws/detect")
async def ws_detect(ws: WebSocket, device_id: str = Query(...)):
    await manager.connect(device_id, ws)

    try:
        # ... (welcome, hello, auth 단계는 동일) ...

        # HeartbeatManager 인스턴스 생성
        hb = HeartbeatManager(ws, device_id, settings.HEARTBEAT_INTERVAL, settings.HEARTBEAT_TIMEOUT)
        heartbeat_task = asyncio.create_task(hb.start())

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "pong":
                hb.record_pong()  # 핵심: pong 시간 갱신

            elif msg_type == "ping":
                await ws.send_json({"type": "pong", "ts": time.time()})

            elif msg_type == "detection":
                # ... (detection 처리 로직) ...
                pass

    except WebSocketDisconnect:
        pass
    finally:
        if 'hb' in locals():
            hb.stop()
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
        manager.disconnect(device_id)
```

## 4. Redis Streams 연동 상세

### 4.1 Redis Docker 실행

```bash
# Redis 7 (Alpine 경량 이미지)
docker run -d \
  --name redis-bus \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

# 연결 확인
docker exec -it redis-bus redis-cli ping
#  PONG
```

### 4.2 Redis Streams 핵심 명령 정리

```python
# ── xadd: 이벤트 발행 ──
# 1단계에서 사용. WebSocket 수신 이벤트를 스트림에 저장.
await redis.xadd("risk.events", {
    "event_id": "evt-123",
    "device_id": "dev-001",
    "frame_data": "<base64_string>",
    "timestamp": "2025-06-21T14:30:00"
})
# 반환: "1687654321000-0" (자동 생성 ID)

# ── xread: 이벤트 읽기 (5단계에서 사용) ──
events = await redis.xread(
    {"risk.events": "$"},     # "$" = 새 메시지만
    count=1,
    block=1000                # 1초 대기
)

# ── xgroup create: Consumer Group 생성 (6단계에서 사용) ──
await redis.xgroup_create("risk.events", "llm-consumers", id="0", mkstream=True)

# ── xreadgroup: Consumer Group으로 읽기 ──
events = await redis.xreadgroup(
    groupname="llm-consumers",
    consumername="worker-1",
    streams={"risk.events": ">"},  # ">" = 미소비 메시지
    count=1,
    block=1000
)

# ── xack: 메시지 처리 완료 확인 ──
await redis.xack("risk.events", "llm-consumers", msg_id)
```

### 4.3 스트림 이름 규칙

| 스트림 이름 | 용도 | 발행자 | 소비자 |
|-------------|------|--------|--------|
| `risk.events` | 카메라 프레임 + 감지 이벤트 | WebSocket Gateway (1,2단계) | YOLO Worker (3단계) |
| `risk.detections` | YOLO 감지 결과 | YOLO Worker (3단계) | RAG/LLM (5단계) |
| `risk.alerts` | 최종 위험 알림 | LLM Agent (5단계) | WebSocket Gateway  앱 |
| `tts.requests` | TTS 변환 요청 | LLM Agent (6단계) | TTS Worker (6단계) |

## 5. 에러 처리 및 엣지 케이스

### 5.1 에러 처리 체크리스트

| 상황 | 처리 방법 | 코드 위치 |
|------|-----------|-----------|
| JSON 파싱 실패 | close(1003), 로그 경고 | ws_routes.py |
| 미등록 device_id | close(1008), 인증 실패 응답 | auth.py |
| 토큰 불일치 | close(1008), 인증 실패 응답 | auth.py |
| 하트비트 타임아웃 | close(1001), 리소스 정리 | heartbeat.py |
| Redis 연결 실패 | 재연결 시도 3회, 실패 시 로그 에러 | redis_bus.py |
| 서버 메모리 부족 | Redis maxmemory-policy로 자동 정리 | Docker 설정 |
| 동시 접속 폭증 | ConnectionManager에서 최대 접속 수 제한 | connection_manager.py |
| 네트워크 지연 | RTT 모니터링, 100ms 초과 시 경고 로그 | ws_routes.py |

### 5.2 ConnectionManager 최대 접속 수 제한 (선택 구현)

```python
MAX_CONNECTIONS = 100

async def connect(self, device_id: str, websocket: WebSocket):
    if len(self.active_connections) >= MAX_CONNECTIONS:
        await websocket.close(code=1013, reason="서버 과부하: 최대 접속 수 초과")
        logger.warning(f"[연결 거부] 최대 접속 수 초과: {MAX_CONNECTIONS}")
        return
    await websocket.accept()
    self.active_connections[device_id] = websocket
```

### 5.3 Graceful Shutdown

```python
# main.py에 추가
from contextlib import asynccontextmanager
from .redis_bus import redis_bus
from .connection_manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    await redis_bus.connect()
    yield
    # 종료 시
    for device_id in list(manager.active_connections.keys()):
        ws = manager.active_connections[device_id]
        await ws.close(code=1001, reason="server shutdown")
    manager.active_connections.clear()
    await redis_bus.disconnect()

app = FastAPI(lifespan=lifespan)
```

## 6. 성능 기준 및 모니터링

### 6.1 핵심 성능 지표

| 지표 | 목표 값 | 측정 방법 |
|------|---------|-----------|
| 연결 수립 시간 | < 3초 | welcome 메시지 수신까지 |
| 메시지 왕복 시간 (RTT) | < 100ms | pingpong 왕복 |
| 프레임 전송 지연 | < 50ms | detection 전송ack 수신 |
| 동시 접속 수 | 100+ | 부하 테스트 |
| Redis xadd 지연 | < 5ms | 단일 이벤트 발행 |

### 6.2 로깅 설정

```python
# server/api/main.py에 추가
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("gateway.log", encoding="utf-8")
    ]
)
```

## 7. 테스트 코드 예시

### 7.1 WebSocket 통합 테스트 (pytest)

```python
# tests/test_ws_gateway.py
import pytest
from httpx import AsyncClient, ASGITransport
from httpx_ws import aconnect_ws
from backend.gateway.main import app

@pytest.mark.asyncio
async def test_websocket_connection():
    """WebSocket 연결  환영 메시지  hello 인증 흐름 테스트"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        async with aconnect_ws("/ws/detect?device_id=dev-001", client) as ws:
            # 1) 환영 메시지 수신
            welcome = await ws.receive_json()
            assert welcome["type"] == "welcome"
            assert welcome["session_id"] == "dev-001"

            # 2) hello 전송
            await ws.send_json({
                "type": "hello",
                "device_id": "dev-001",
                "token": "token-abc-001"
            })

            # 3) auth_ok 수신
            auth_resp = await ws.receive_json()
            assert auth_resp["type"] == "auth_ok"

@pytest.mark.asyncio
async def test_invalid_token():
    """잘못된 토큰으로 인증 시 연결 종료 확인"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        async with aconnect_ws("/ws/detect?device_id=dev-001", client) as ws:
            welcome = await ws.receive_json()
            await ws.send_json({
                "type": "hello",
                "device_id": "dev-001",
                "token": "WRONG-TOKEN"
            })
            error_resp = await ws.receive_json()
            assert error_resp["type"] == "error"
```

### 7.2 수동 테스트 (wscat)

```bash
# wscat 설치
npm install -g wscat

# 연결 테스트
wscat -c "ws://localhost:8000/ws/detect?device_id=dev-001"

# 연결 후 입력:
{"type": "hello", "device_id": "dev-001", "token": "token-abc-001"}
#  응답: {"type": "auth_ok", "device_id": "dev-001"}

# ping 테스트:
{"type": "ping", "ts": 1687654321000}
#  응답: {"type": "pong", "ts": ...}
```

## 8. 환경 변수 (.env 예시)

```env
# server/api/.env
WS_HOST=0.0.0.0
WS_PORT=8000
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
HEARTBEAT_INTERVAL=5
HEARTBEAT_TIMEOUT=5
MAX_RECONNECT_ATTEMPTS=3
CORS_ORIGINS=["*"]
```
