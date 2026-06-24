---
name: websocket-gateway
description: |
  FastAPI WebSocket 기반 실시간 양방향 통신 게이트웨이 구현.
  시각장애인 보행보조 앱(React Native)과 GPU 서버 간 끊김 없는 실시간 데이터 교환 채널을 구축한다.
  Redis Streams를 통한 내부 모듈 간 메시지 버스 연동을 포함한다.
---

# WebSocket Gateway (1단계: 서버와 실시간 통신망 연결)

> **작성일**: 2026-06-24
> **버전**: v0.1.0
> **설계 기준**: `docs/minchodan_design_note.md` 1단계

## 개요

시각장애인의 눈(스마트폰 카메라)과 브레인 서버(AI)가 **지연 시간 없이** 통신하는 상태를 유지하는 것이 핵심 목표이다. HTTP 요청/응답 방식은 매번 연결을 새로 맺으므로 실시간성이 떨어진다. WebSocket은 한 번 연결하면 양방향 영구 연결(Full-Duplex)을 유지하므로, 카메라 프레임·위험 알림 등을 수십 ms 이내에 교환할 수 있다.

## 목표 아키텍처

```
┌─────────────────┐         WebSocket (ws://)         ┌──────────────────────┐
│  React Native   │ ◄──────────────────────────────► │  FastAPI + Uvicorn   │
│  시각장애인 앱    │    JSON 메시지 (양방향)            │  server/api/         │
└─────────────────┘                                   └──────────┬───────────┘
                                                                  │ xadd / xread
                                                       ┌──────────▼───────────┐
                                                       │   Redis Streams      │
                                                       │   (메시지 버스)        │
                                                       └──────────────────────┘
```

## 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| 서버 프레임워크 | FastAPI + Uvicorn | 비동기 WebSocket 서버 |
| 메시지 버스 | Redis 7 (Streams) | 내부 모듈 간 이벤트 전달 |
| 프로토콜 | WebSocket (RFC 6455) | 양방향 실시간 통신 |
| 앱 클라이언트 | React Native WebSocket API | 모바일 앱 통신 |
| 컨테이너 | Docker (redis:7-alpine) | Redis 실행 환경 |

## 디렉토리 구조 (Minchodan 기준)

```
server/api/
├── __init__.py
├── main.py              # FastAPI 앱 인스턴스 + CORS + 라우터 등록
├── ws_router.py          # WebSocket 엔드포인트 (/ws/detect)
├── session_manager.py    # 연결 관리 (접속자 추적, 브로드캐스트)
├── heartbeat.py          # 하트비트 루프 (ping/pong)
├── auth.py               # 디바이스 토큰 검증
├── config.py             # 환경 변수 및 설정 값
└── schemas.py            # Pydantic 메시지 스키마
```

> `server/bus/redis_client.py`, `server/bus/producer.py`, `server/bus/consumer.py`는 Redis Streams 인터페이스를 담당한다.

## 핵심 구현 절차 (서버 측)

### 단계 1-1. 프로젝트 디렉토리 및 의존성 설정

```bash
# server/api/ 패키지 생성
```

**requirements.txt** (프로젝트 루트):

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
redis>=5.0.0
pydantic>=2.9.0
python-dotenv>=1.0.0
websockets>=12.0
```

### 단계 1-2. config.py — 환경 설정

```python
# server/api/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    WS_HOST: str = "0.0.0.0"
    WS_PORT: int = 8000
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    HEARTBEAT_INTERVAL: int = 5      # 초 단위
    HEARTBEAT_TIMEOUT: int = 5       # pong 응답 대기 시간
    MAX_RECONNECT_ATTEMPTS: int = 3  # 클라이언트 재접속 최대 횟수
    CORS_ORIGINS: list[str] = ["*"]  # 개발 시 전체 허용, 운영 시 제한

    class Config:
        env_file = ".env"

settings = Settings()
```

### 단계 1-3. main.py — FastAPI 앱 인스턴스

```python
# server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.api.ws_router import router as ws_router
from server.api.config import settings

app = FastAPI(
    title="Minchodan 시각장애인 보행보조 AI - WebSocket Gateway",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router, prefix="")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ws-gateway"}
```

### 단계 1-4. schemas.py — 메시지 스키마

```python
# server/api/schemas.py
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class WSMessage(BaseModel):
    type: str                        # "hello" | "ping" | "pong" | "detection" | "welcome" | "ack" | "alert_reflex" | "guide"
    device_id: Optional[str] = None
    token: Optional[str] = None
    session_id: Optional[str] = None
    server_time: Optional[str] = None
    ts: Optional[float] = None
    payload: Optional[dict[str, Any]] = None

class WelcomeMessage(BaseModel):
    type: str = "welcome"
    session_id: str
    server_time: str

class AckMessage(BaseModel):
    type: str = "ack"
    event_id: str
    received_at: str
```

### 단계 1-5. session_manager.py — 연결 관리자

```python
# server/api/session_manager.py
from fastapi import WebSocket
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """활성 WebSocket 연결을 추적하고 관리하는 싱글턴 클래스"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(f"[연결] device_id={device_id}, 현재 접속: {len(self.active_connections)}명")

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"[해제] device_id={device_id}, 현재 접속: {len(self.active_connections)}명")

    async def send_json(self, device_id: str, data: dict):
        ws = self.active_connections.get(device_id)
        if ws:
            await ws.send_json(data)

    def is_connected(self, device_id: str) -> bool:
        return device_id in self.active_connections

manager = SessionManager()
```

### 단계 1-6. auth.py — 디바이스 토큰 검증

```python
# server/api/auth.py
import logging

logger = logging.getLogger(__name__)

REGISTERED_DEVICES = {
    "dev-001": "token-abc-001",
    "dev-002": "token-abc-002",
}

async def verify_device(device_id: str, token: str) -> bool:
    expected_token = REGISTERED_DEVICES.get(device_id)
    if expected_token is None:
        logger.warning(f"[인증 실패] 미등록 디바이스: {device_id}")
        return False
    if expected_token != token:
        logger.warning(f"[인증 실패] 토큰 불일치: device_id={device_id}")
        return False
    logger.info(f"[인증 성공] device_id={device_id}")
    return True
```

### 단계 1-7. heartbeat.py — 하트비트 관리

```python
# server/api/heartbeat.py
import asyncio
import time
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class HeartbeatManager:
    """서버->클라이언트: 5초마다 ping, 5초 내 pong 없으면 종료"""

    def __init__(self, ws: WebSocket, device_id: str, interval: int = 5, timeout: int = 5):
        self.ws = ws
        self.device_id = device_id
        self.interval = interval
        self.timeout = timeout
        self.last_pong_time: float = time.time()
        self._running = True

    async def start(self):
        while self._running:
            await asyncio.sleep(self.interval)
            elapsed = time.time() - self.last_pong_time
            if elapsed > (self.interval + self.timeout):
                logger.warning(f"[하트비트] 타임아웃: device_id={self.device_id}")
                await self.ws.close(code=1001, reason="heartbeat timeout")
                break
            try:
                await self.ws.send_json({"type": "ping", "ts": time.time()})
            except Exception as e:
                logger.error(f"[하트비트] ping 전송 실패: {e}")
                break

    def record_pong(self):
        self.last_pong_time = time.time()

    def stop(self):
        self._running = False
```

### 단계 1-8. ws_router.py — WebSocket 엔드포인트

```python
# server/api/ws_router.py
import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from server.api.session_manager import manager
from server.api.auth import verify_device
from server.api.heartbeat import HeartbeatManager
from server.bus.redis_client import redis_bus
from server.api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/detect")
async def ws_detect(ws: WebSocket, device_id: str = Query(...)):
    await manager.connect(device_id, ws)

    try:
        welcome = {
            "type": "welcome",
            "session_id": device_id,
            "server_time": datetime.now().isoformat()
        }
        await ws.send_json(welcome)

        raw_hello = await ws.receive_text()
        hello_data = json.loads(raw_hello)

        if hello_data.get("type") != "hello":
            await ws.close(code=1008, reason="expected hello message")
            return

        token = hello_data.get("token", "")
        is_valid = await verify_device(device_id, token)
        if not is_valid:
            await ws.send_json({"type": "error", "message": "인증 실패"})
            await ws.close(code=1008, reason="authentication failed")
            return

        await ws.send_json({"type": "auth_ok", "device_id": device_id})
        await redis_bus.connect()

        hb = HeartbeatManager(ws, device_id, settings.HEARTBEAT_INTERVAL, settings.HEARTBEAT_TIMEOUT)
        heartbeat_task = asyncio.create_task(hb.start())

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "pong":
                hb.record_pong()

            elif msg_type == "ping":
                await ws.send_json({"type": "pong", "ts": time.time()})

            elif msg_type == "detection":
                payload = data.get("payload", {})
                event_id = payload.get("event_id", "unknown")

                await redis_bus.publish_event("risk.events", {
                    "event_id": event_id,
                    "device_id": device_id,
                    "timestamp": payload.get("timestamp", datetime.now().isoformat()),
                    "stream": payload.get("stream", "cognitive"),
                    "frame_data": payload.get("thumbnail_jpeg_b64", ""),
                })

                await ws.send_json({
                    "type": "ack",
                    "event_id": event_id,
                    "received_at": datetime.now().isoformat()
                })

            else:
                logger.warning(f"[WS] 알 수 없는 메시지 타입: {msg_type}")

    except WebSocketDisconnect as e:
        logger.info(f"[WS] 연결 끊김: device_id={device_id}, code={e.code}")
    except json.JSONDecodeError as e:
        logger.error(f"[WS] JSON 파싱 오류: {e}")
        await ws.close(code=1003, reason="invalid JSON")
    except Exception as e:
        logger.error(f"[WS] 예기치 않은 오류: device_id={device_id}, error={e}")
    finally:
        manager.disconnect(device_id)
        if 'hb' in locals():
            hb.stop()
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
        logger.info(f"[WS] 세션 종료: device_id={device_id}")
```

### 단계 1-9. 서버 실행

```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

## 핵심 구현 절차 (React Native 앱 측)

### useWebSocket.ts

```typescript
// client/src/hooks/useWebSocket.ts
import { useRef, useCallback, useEffect, useState } from 'react';

const WS_URL = 'ws://서버IP:8000/ws/detect';
const MAX_RECONNECT = 3;
const RECONNECT_DELAY = 1000;
const HEARTBEAT_INTERVAL = 5000;

type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'fallback';

export function useWebSocket(deviceId: string, token: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const heartbeatTimer = useRef<NodeJS.Timeout | null>(null);
  const [status, setStatus] = useState<WSStatus>('disconnected');

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_URL}?device_id=${deviceId}`);
    wsRef.current = ws;
    setStatus('connecting');

    ws.onopen = () => {
      reconnectCount.current = 0;
      ws.send(JSON.stringify({ type: 'hello', device_id: deviceId, token: token }));
      heartbeatTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
        }
      }, HEARTBEAT_INTERVAL);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'welcome': setStatus('connected'); break;
        case 'auth_ok': break;
        case 'pong': break;
        case 'ping': ws.send(JSON.stringify({ type: 'pong', ts: Date.now() })); break;
        case 'ack': break;
        case 'alert_reflex': handleAlertReflex(data); break;
        case 'guide': handleGuide(data); break;
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      if (heartbeatTimer.current) clearInterval(heartbeatTimer.current);
      if (reconnectCount.current < MAX_RECONNECT) {
        reconnectCount.current += 1;
        setTimeout(connect, RECONNECT_DELAY);
      } else {
        setStatus('fallback');
      }
    };

    ws.onerror = (error) => { console.error('[WS] 오류:', error); };
  }, [deviceId, token]);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (heartbeatTimer.current) clearInterval(heartbeatTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status, send, ws: wsRef };
}
```

## 데이터 인터페이스

| 방향 | 페이로드 |
| --- | --- |
| In (hello) | `{type:"hello", device_id, token}` |
| Out (welcome) | `{type:"welcome", session_id, server_time}` |
| Out (auth_ok) | `{type:"auth_ok", device_id}` |
| In (detection) | `{type:"detection", payload:{event_id, device_id, ts, frame_id, stream, thumbnail_jpeg_b64}}` |
| Out (ack) | `{type:"ack", event_id, received_at}` |
| Out (alert_reflex) | `{type:"alert_reflex", event_id, alert_id, direction, risk_level, clip, haptic, ts}` |
| Out (guide) | `{type:"guide", event_id, risk_level, guidance_text, audio_mp3_b64, ts}` |

## 테스트 체크리스트

| 항목 | 기대 결과 | 합격 기준 |
|------|-----------|-----------|
| 연결 수립 | welcome 메시지 수신 | 3초 이내 |
| hello/인증 | auth_ok 응답 | 토큰 일치 시 성공 |
| 하트비트 | pingpong 왕복 | 5초 간격, RTT < 100ms |
| 메시지 echo | 앱서버앱 왕복 | **RTT < 100ms** |
| 연결 끊김 복구 | 자동 재연결 | 3회 이내 성공 |
| Redis 발행 | xadd 성공 | 메시지 ID 반환 |
| WebSocketDisconnect | 소켓 close + 리소스 해제 | 예외 없이 정리 |

## Redis Streams 활용 로드맵

| 단계 | 용도 | 핵심 명령 |
|------|------|-----------|
| 1단계 (본 스킬) | 이벤트 발행 | `xadd risk.events {...}` |
| 3단계 | 컨텍스트 캐싱 (TTL=30초) | `hset ctx:{track_id} ...` + `expire 30` |
| 3단계 | mid/low 발행 | `xadd risk.events {...}` |
| 6단계 | Consumer Group 재처리 | `xgroup create`, `xreadgroup` |
| 7단계 | 중복 알림 억제 | `setex suppress:{alert_id} 60 ""` |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- API 명세서: [`docs/api_specification.md`](../../../docs/api_specification.md)
- FastAPI WebSocket 공식 문서: https://fastapi.tiangolo.com/advanced/websockets/
- Redis Streams 공식 문서: https://redis.io/docs/data-types/streams/
