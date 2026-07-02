# Minchodan 온디바이스 모바일 앱 구현 계획서 (1+2단계)

> **작성일**: 2026-06-30
> **버전**: v0.2.0 (플랫폼별 분리 — iOS/Android 담당자용)
> **설계 기준**: [`docs/minchodan_design_note.md`](minchodan_design_note.md) 1·2단계 (v1.1 이중 스트림 반영)
> **API 명세 기준**: [`docs/api_specification.md`](api_specification.md) v0.2.0 (필드 정합 최우선)
> **스킬 참조**: [`.agents/skills/websocket-gateway/SKILL.md`](../.agents/skills/websocket-gateway/SKILL.md), [`.agents/skills/camera-frame-capture/SKILL.md`](../.agents/skills/camera-frame-capture/SKILL.md)
> **코딩 패턴 기준**: [`docs/course_codebase_guide.md`](course_codebase_guide.md)
> **담당 브랜치**: `kb` (iOS 주도 + 서버 Phase A)

> [!IMPORTANT]
> **본 문서는 플랫폼별 분리 이전의 통합 원본입니다.** 실제 구현 시 아래 분리된 설계서를 사용하십시오.
>
> | 플랫폼 | 설계서 | 담당 |
> | --- | --- | --- |
> | **iOS** (서버 Phase A + 공통 TS 코드 주도) | [`docs/mobile_ios_implementation_plan.md`](mobile_ios_implementation_plan.md) | `kb` |
> | **Android** (공통 TS 코드 검토 + Android 빌드/검증) | [`docs/mobile_android_implementation_plan.md`](mobile_android_implementation_plan.md) | Android 담당자 |
>
> 본 통합 문서는 분담 구조 개요와 공통 아키텍처 참조용으로 유지됩니다.

---

## 1. 개요

본 문서는 Minchodan 시각장애인 보행 보조 앱의 **온디바이스 모바일 클라이언트(React Native)** 구현 계획서입니다. **1단계(WebSocket 실시간 통신)** 와 **2단계(카메라 이중 캡처·전송)** 를 한 패스로 구현하여, 단말에서 캡처한 프레임이 서버의 3단계 탐지 파이프라인까지 도달하는 것을 end-to-end로 검증하는 것이 목표입니다.

### 1.1 구현 배경

현재 `client/` 디렉토리는 빈 스캐폴딩(`.gitkeep`만 존재) 상태이며, 서버측 `/ws/detect` WebSocket 라우터가 `server/main.py`에 마운트되지 않아 모바일 앱의 end-to-end 테스트가 불가능한 상태입니다. 따라서 **서버측 WS 라우터 구현(A) → 클라이언트 초기화(B) → WS 훅(C) → 카메라 캡처(D) → 통합 테스트(E)** 순으로 진행합니다.

### 1.2 핵심 원칙 (비협상)

**이중 경로 물리 분리** — 반사 스트림(8~10fps)은 Detection 즉시 경보 용도, 인지 스트림(1~2fps)은 상세 가이드 용도로 단말 단에서부터 분리 캡처합니다.

| 경로 | 위험도 | 단말 캡처 | 서버 처리 | 목표 지연 |
| --- | --- | --- | --- | --- |
| **반사 (reflex)** | high | 10fps `takePhoto({qualityPrioritization:'speed'})` | 3단계 Detection → Reflex Gate → 사전합성 클립 | **캡처수신 < 50ms** (2단계) |
| **인지 (cognitive)** | mid/low | 2fps `takePhoto({qualityPrioritization:'speed'})` | 3단계 Detection+Seg → Redis Streams → LangGraph + RAG → 실시간 TTS | 1~2Hz |

### 1.3 확정된 결정 사항

| 항목 | 결정 | 비고 |
| --- | --- | --- |
| RN 워크플로우 | **Expo Dev Client** | `react-native-vision-camera` 네이티브 모듈로 인해 Expo Go 불가, 커스텀 개발 클라이언트 빌드 |
| 빌드 전략 | **로컬 빌드 우선** | macOS: iOS/Android 로컬 빌드, Windows: Android 로컬 빌드 (iOS는 Xcode 필수) |
| 구현 범위 | **1+2단계 (WS + 카메라)** | 음성/햅틱 재생(7단계 클라이언트측)은 다음 패스 |
| 서버 WS 라우터 | **함께 구현** | 스킬 문서 기반, 기존 `decode_frame()`/`get_default_splitter()` 재사용 |
| 디바이스 인증 | **MVP 하드코딩** | `REGISTERED_DEVICES` dict, 추후 `.env`/DB 연동 확장 |
| 필드 정합 기준 | **API 명세서 v0.2.0** | `ts`(epoch ms), `thumbnail_jpeg_b64`, `frame_id`, `heartbeat`/`heartbeat_ack` |

---

## 2. 현재 프로젝트 상태 분석

### 2.1 서버측 구현 현황

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| `server/main.py` | 모니터링 라우터만 마운트 | **`/ws/detect` WebSocket 라우터 미연결** |
| `server/api/monitor.py` | 구현됨 | SSE 모니터링 스트림 (유지) |
| `server/api/ws_router.py` | **미구현** | 스킬 문서에만 존재, 실제 파일 없음 |
| `server/capture/frame_decoder.py` | **구현됨** | `decode_frame(payload)` + `ProcessedFrame` dataclass, None 가드레일 5종 |
| `server/capture/stream_splitter.py` | **구현됨** | `get_default_splitter()` 싱글턴, reflex/cognitive `asyncio.Queue` 분기 |
| `server/bus/redis_client.py` | **구현됨** | `redis_bus` 싱글턴, `publish_event()` |
| `server/detection/` | 3단계 모듈 존재 | WS 라우터가 없어 프레임 수신 불가 |

### 2.2 클라이언트측 구현 현황

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| `client/` | 빈 스캐폴딩 | `src/{hooks,services,components,utils}/.gitkeep`, `assets/reflex_clips/.gitkeep` |
| `package.json` | 없음 | Expo 프로젝트 초기화 필요 |
| `app.json` | 없음 | iOS/Android 권한·번들 설정 필요 |

### 2.3 필드 정합 이슈 (해결)

| 스킬 문서(ws_router) | API 명세서 v0.2.0 (권위) | 채택 |
| --- | --- | --- |
| `timestamp` (ISO 8601) | `ts` (epoch ms) | **API 명세서** |
| `frame_data` | `thumbnail_jpeg_b64` | **API 명세서** |
| (누락) | `frame_id` (증가 번호) | **API 명세서** |
| `ping`/`pong` | `heartbeat`/`heartbeat_ack` | **API 명세서** |

> `frame_decoder.py`는 이미 `ts`/`thumbnail_jpeg_b64`를 사용하므로 API 명세서 기반이 일관성 있게 유지됩니다.

---

## 3. 구현 범위

| 디렉토리 | 구현 여부 | 비고 |
| --- | --- | --- |
| `server/api/` | **구현 (WS 라우터)** | 1단계 서버측, 기존 `monitor.py` 유지 |
| `server/capture/` | **이미 구현됨** | `decode_frame()` / `get_default_splitter()` 재사용 |
| `server/bus/` | **이미 구현됨** | `redis_bus` 싱글턴 재사용 |
| `server/main.py` | **수정** | `ws_router` 마운트 추가 |
| `client/` | **구현 (Expo 프로젝트)** | 1+2단계 클라이언트 전체 |
| `tests/test_ws_echo.py` | **신규** | 1단계 RTT < 100ms 검증 |

---

## 4. 전체 아키텍처

```mermaid
graph TB
    subgraph RN ["React Native 앱 (Expo Dev Client)"]
        CH["CameraView.tsx<br/>후면 카메라"]
        RC["반사 캡처 10fps"]
        CC["인지 캡처 2fps"]
        WSH["useWebSocket.ts<br/>hello/heartbeat/reconnect"]
        FC["frameCapture.ts<br/>base64 인코딩"]
        CH --> RC
        CH --> CC
        RC --> FC
        CC --> FC
        FC --> WSH
    end
    subgraph SV ["FastAPI 서버 (server/api/)"]
        WS["ws_router.py<br/>/ws/detect"]
        AUTH["auth.py<br/>토큰 검증"]
        HB["heartbeat.py<br/>5초 ping/pong"]
        SM["session_manager.py<br/>연결 추적"]
        WS --> AUTH
        WS --> HB
        WS --> SM
    end
    subgraph CAP ["server/capture/ (이미 구현됨)"]
        DF["decode_frame()"]
        SS["get_default_splitter()"]
        RQ["reflex_queue"]
        CQ["cognitive_queue"]
        DF --> SS
        SS -->|"reflex"| RQ
        SS -->|"cognitive"| CQ
    end
    subgraph RD ["Redis Bus"]
        RE["risk.events<br/>메타데이터만"]
    end
    WSH -->|"WebSocket JSON"| WS
    WS -->|"detection payload"| DF
    SS -.->|"event_id/device_id/ts"| RE
    RQ -.->|"3단계 소비"| DET["Yolo 26N Detection"]
    CQ -.->|"3단계 소비"| DET
    WS -->|"ack"| WSH
```

---

## 5. Phase A: 서버측 1단계 WebSocket 라우터 구현

### 5.1 신규 파일 (6개)

#### `server/api/config.py` — 환경 설정

| 항목 | 내용 |
| --- | --- |
| 역할 | WS/Redis/Heartbeat 설정값 중앙화 |
| 핵심 | `__file__` 기반 경로 계산 (guide 3.3), `load_dotenv()` (guide 3.4), `Settings(BaseSettings)` |
| 필드 | `WS_HOST`, `WS_PORT`, `REDIS_HOST/PORT/DB`, `HEARTBEAT_INTERVAL=5`, `HEARTBEAT_TIMEOUT=5`, `MAX_RECONNECT_ATTEMPTS=3`, `CORS_ORIGINS` |

#### `server/api/schemas.py` — Pydantic 메시지 스키마

| 항목 | 내용 |
| --- | --- |
| 역할 | WS 메시지 타입별 스키마 정의 |
| 모델 | `WSMessage`(type/device_id/token/session_id/server_time/ts/payload), `WelcomeMessage`, `AckMessage` |
| type 값 | `hello`, `welcome`, `auth_ok`, `heartbeat`, `heartbeat_ack`, `detection`, `ack`, `alert_reflex`, `guide`, `error` (API 명세서 §1 준수) |

#### `server/api/auth.py` — 디바이스 토큰 검증 (MVP)

| 항목 | 내용 |
| --- | --- |
| 역할 | hello 핸드셰이크 시 디바이스 토큰 검증 |
| MVP 방식 | 하드코딩 `REGISTERED_DEVICES = {"dev-001": "token-abc-001", ...}` |
| 함수 | `async verify_device(device_id, token) -> bool` |
| 확장 | 추후 `.env`/DB 연동 (본 계획 범위 밖) |

#### `server/api/session_manager.py` — 연결 관리자

| 항목 | 내용 |
| --- | --- |
| 역할 | 활성 WebSocket 연결 추적 싱글턴 |
| 클래스 | `SessionManager` (`active_connections: dict[str, WebSocket]`) |
| 메서드 | `connect()`, `disconnect()`, `send_json()`, `is_connected()` |
| 인스턴스 | `manager = SessionManager()` (모듈 수준 싱글턴) |

#### `server/api/heartbeat.py` — 하트비트 관리

| 항목 | 내용 |
| --- | --- |
| 역할 | 서버→단말 5초 `heartbeat` 송신, 타임아웃 시 종료 |
| 클래스 | `HeartbeatManager(ws, device_id, interval, timeout)` |
| 메서드 | `start()` (async 루프), `record_pong()`, `stop()` |
| 타임아웃 | `elapsed > interval + timeout` 시 `ws.close(code=1001)` |
| 메시지 | API 명세서 기준 `{type:"heartbeat", ts}` 송신 |

#### `server/api/ws_router.py` — WebSocket 엔드포인트 (핵심)

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `@router.websocket("/ws/detect")` |
| 쿼리 | `device_id: str = Query(...)` |
| 핸드셰이크 | `manager.connect()` → `welcome` 송신 → `hello` 수신 → `verify_device()` → `auth_ok` |
| detection 처리 | `decode_frame(payload)` → `get_default_splitter().route_frame(processed)` → `ack` 응답 |
| ack 필드 | `{type:"ack", event_id, frame_id, decode_ms}` (API 명세서 §3.2) |
| 가드레일 | `decode_frame` None 반환 시에도 ack 정상 응답 (파이프라인 영속성) |
| 예외 | `WebSocketDisconnect`, `json.JSONDecodeError`, `Exception` → `finally`에서 `manager.disconnect()` + `hb.stop()` + `heartbeat_task.cancel()` |

### 5.2 수정 파일 (1개)

| 파일 | 변경 내용 |
| --- | --- |
| `server/main.py` | `from server.api.ws_router import router as ws_router` 추가, `app.include_router(ws_router, prefix="")` 마운트. 기존 `monitor_router` 및 `lifespan` 유지 |

### 5.3 detection 처리 흐름 상세

```mermaid
sequenceDiagram
    participant APP as React Native 앱
    participant WS as ws_router.py
    participant DF as decode_frame()
    participant SS as get_default_splitter()
    participant RD as Redis risk.events
    APP->>WS: type=detection, payload{event_id, ts, frame_id, stream, thumbnail_jpeg_b64}
    WS->>DF: decode_frame(payload)
    DF-->>WS: ProcessedFrame 또는 None (가드레일)
    alt ProcessedFrame not None
        WS->>SS: route_frame(processed)
        SS->>RD: xadd risk.events (메타데이터)
        SS-->>WS: 분기 완료 (reflex/cognitive queue)
    end
    WS-->>APP: type=ack, event_id, frame_id, decode_ms
```

### 5.4 신규 테스트 (1개)

| 파일 | 내용 |
| --- | --- |
| `tests/test_ws_echo.py` | 1단계 검증: 연결 수립, hello/welcome, echo 왕복 **RTT < 100ms**, 하트비트, 재연결, `WebSocketDisconnect` 정리. `pytest` + `websockets` 클라이언트 사용 |

---

## 6. Phase B: 클라이언트측 Expo Dev Client 프로젝트 초기화

### 6.1 프로젝트 생성

| 순번 | 내용 | 비고 |
| --- | --- | --- |
| B1 | 기존 `client/` 빈 스캐폴딩 정리 | `.gitkeep` 제거 후 Expo 템플릿 적용 |
| B2 | `npx create-expo-app` (blank TypeScript) | `client/` 하위에 생성 |
| B3 | `app.json` / `app.config.js` 설정 | 이름, 번들 ID, iOS/Android 카메라·오디오 권한 |
| B4 | 의존성 설치 | `react-native-vision-camera`, `expo-dev-client`, `expo-haptics` |
| B5 | 디렉토리 구조 정리 | 스킬 기준 구조로 재배치 |

### 6.2 디렉토리 구조 (클라이언트)

```
client/
├── app.json                      # Expo 설정 (권한, 번들 ID)
├── package.json                  # 의존성
├── tsconfig.json                 # TypeScript 설정
├── src/
│   ├── config/
│   │   └── index.ts              # WS_URL, DEVICE_ID, TOKEN, FPS 설정
│   ├── types/
│   │   └── detection.ts          # WSMessage, DetectionEvent, AckMessage 타입
│   ├── hooks/
│   │   ├── useWebSocket.ts       # 1단계 WS 연결/하트비트/재연결
│   │   └── useCamera.ts          # 2단계 이중 캡처 타이머
│   ├── services/
│   │   └── frameCapture.ts       # takePhoto → base64 → send
│   ├── components/
│   │   ├── CameraView.tsx        # 카메라 + WS 연동
│   │   └── ConnectionStatus.tsx  # 접속 상태 표시 (접근성)
│   └── utils/
│       └── haptics.ts            # 햅틱 + announceForAccessibility (7단계 준비 stub)
├── assets/
│   └── reflex_clips/             # 사전합성 반사 음성 클립 (7단계)
└── App.tsx                       # 엔트리 포인트
```

### 6.3 설정 파일

| 파일 | 핵심 내용 |
| --- | --- |
| `src/config/index.ts` | `WS_URL`(서버 LAN IP), `DEVICE_ID`, `TOKEN`, `REFLEX_FPS=10`, `COGNITIVE_FPS=2`, `HEARTBEAT_INTERVAL=5000`, `MAX_RECONNECT=3` |
| `app.json` | `expo-dev-client` 플러그인, iOS `NSCameraUsageDescription`, Android `CAMERA` 권한 |

> 환경변수는 `expo-constants` 또는 `react-native-dotenv`로 관리 (`.env` 직접 참조 불가)

### 6.4 개발 클라이언트 빌드

| 플랫폼 | 명령 | 비고 |
| --- | --- | --- |
| iOS (macOS) | `npx expo run:ios --device` | 실기기 필수 (시뮬레이터 카메라 미지원) |
| Android (macOS/Windows) | `npx expo run:android --device` | 실기기 또는 에뮬레이터 (가상 카메라) |

---

## 7. Phase C: 클라이언트측 1단계 WebSocket 훅

### 7.1 신규 파일 (3개)

#### `src/types/detection.ts` — 타입 정의

| 타입 | 필드 |
| --- | --- |
| `WSStatus` | `'connecting' \| 'connected' \| 'disconnected' \| 'fallback'` |
| `WSMessage` | `type`, `device_id?`, `token?`, `session_id?`, `server_time?`, `ts?`, `payload?` |
| `DetectionPayload` | `event_id`, `device_id`, `ts`(number), `frame_id`(number), `stream`('reflex'\|'cognitive'), `thumbnail_jpeg_b64` |
| `AckPayload` | `event_id`, `frame_id`, `decode_ms` |

#### `src/hooks/useWebSocket.ts` — WS 연결 훅

| 항목 | 내용 |
| --- | --- |
| 역할 | WebSocket 연결 생명주기 관리 |
| 입력 | `deviceId: string, token: string` |
| 반환 | `{ status, send, ws }` |
| 연결 흐름 | `new WebSocket(WS_URL?device_id=)` → `onopen`: hello 송신 → `onmessage`: welcome 수신 시 `connected` |
| 하트비트 | 5초 간격 `{type:"heartbeat", ts: Date.now()}` 송신, `heartbeat_ack` 수신 |
| 재연결 | `onclose` 시 `MAX_RECONNECT=3`회까지 `RECONNECT_DELAY=1000ms` 후 재시도, 초과 시 `fallback` |
| 가드레일 | 소켓 유실 시 `heartbeatTimer` 즉시 `clearInterval` (메모리 고갈 방지) |
| 정리 | `useEffect` cleanup에서 `ws.close()` + 타이머 해제 |

#### `src/components/ConnectionStatus.tsx` — 접속 상태 표시

| 항목 | 내용 |
| --- | --- |
| 역할 | WS 연결 상태 시각화 + 접근성 |
| 접근성 | `accessibilityLabel={`연결: ${status}`}` (시각장애인 운영자용) |
| 상태 | connecting(황), connected(녹), disconnected(적), fallback(회) |

### 7.2 메시지 처리 흐름

```mermaid
sequenceDiagram
    participant UI as CameraView
    participant HOOK as useWebSocket
    participant WS as FastAPI 서버
    UI->>HOOK: useWebSocket(deviceId, token)
    HOOK->>WS: WebSocket 연결 (ws://...?device_id=)
    WS-->>HOOK: onopen
    HOOK->>WS: {type:"hello", device_id, token}
    WS-->>HOOK: {type:"welcome", session_id, server_time}
    HOOK->>HOOK: status = "connected"
    WS-->>HOOK: {type:"auth_ok"}
    loop 5초 간격
        HOOK->>WS: {type:"heartbeat", ts}
        WS-->>HOOK: {type:"heartbeat_ack", ts}
    end
    UI->>HOOK: send(detectionEvent)
    HOOK->>WS: {type:"detection", payload:{...}}
    WS-->>HOOK: {type:"ack", event_id, frame_id, decode_ms}
```

---

## 8. Phase D: 클라이언트측 2단계 이중 카메라 캡처

### 8.1 신규 파일 (4개)

#### `src/hooks/useCamera.ts` — 이중 캡처 타이머

| 항목 | 내용 |
| --- | --- |
| 역할 | 후면 카메라 이중 타이머 캡처 |
| 입력 | `reflexFps=10`, `cognitiveFps=2` |
| 반환 | `{ cameraRef, device, hasPermission, isCapturing, startCapture, stopCapture, captureFrame }` |
| 권한 | `useCameraPermission()`, 거부 시 안내 |
| 디바이스 | `useCameraDevice('back')` |
| 캡처 | `cameraRef.current.takePhoto({qualityPrioritization:'speed', flash:'off', enableShutterSound:false})` → `photo.toBase64()` |
| 타이머 | `setInterval(1000/reflexFps)`, `setInterval(1000/cognitiveFps)` 별도 관리 |
| 가드레일 | `cameraRef.current` null 체크, `takePhoto` 예외 시 `null` 반환 (에러 없이 스킵) |
| 정리 | 언마운트 시 `clearInterval` 즉시 해제 (자원 누수 방지) |

#### `src/services/frameCapture.ts` — 프레임 전송 서비스

| 항목 | 내용 |
| --- | --- |
| 역할 | 캡처 프레임 → detection 이벤트 조립 → WS 전송 |
| 함수 | `generateEventId()`, `buildDetectionEvent(base64, deviceId, stream)`, `sendFrame(base64, stream, deviceId, send)` |
| event_id | `evt-{Date.now()}-{random 3자리}` |
| 페이로드 | API 명세서 §3.1 준수: `{type:"detection", payload:{event_id, device_id, ts:Number, frame_id, stream, thumbnail_jpeg_b64}}` |
| frame_id | 모듈 수준 증가 카운터 |
| ts | `Date.now()` (epoch ms) |

#### `src/components/CameraView.tsx` — 카메라 + WS 연동

| 항목 | 내용 |
| --- | --- |
| 역할 | 카메라 컴포넌트 + WS 상태 연동 게이트 |
| 연동 | `status === 'connected' && !isCapturing` → `startCapture()`, `status !== 'connected' && isCapturing` → `stopCapture()` |
| 권한 거부 | "카메라 권한이 필요합니다." 안내 |
| 디바이스 없음 | "카메라를 찾을 수 없습니다." 안내 |
| 접근성 | `accessibilityLabel`로 연결·캡처 상태 전달 |

#### `src/utils/haptics.ts` — 햅틱/접근성 (7단계 준비 stub)

| 항목 | 내용 |
| --- | --- |
| 역할 | 햅틱 + `announceForAccessibility` 래퍼 (본 패스에서는 stub) |
| 함수 | `triggerHaptic()`, `announce(message)` |
| 구현 | `expo-haptics` 호출 래퍼, 7단계 반사/인지 음성 재생 시 본격 활용 |

### 8.2 detection 페이로드 (API 명세서 v0.2.0 준수)

```typescript
{
  type: "detection",
  payload: {
    event_id: "evt-1719216000000-001",
    device_id: "dev-001",
    ts: 1719216000000,           // epoch ms (number)
    frame_id: 42,                // 증가 번호
    stream: "reflex",            // "reflex" | "cognitive"
    thumbnail_jpeg_b64: "/9j/4AAQ..."
  }
}
```

### 8.3 가드레일 (설계 의존성·예외 준수)

| 예외 | 처리 |
| --- | --- |
| 카메라 권한 거부 (`NotAllowedError`) | 안내 메시지 표시, 종료 |
| 소켓 유실 | `clearInterval`로 타이머 자원 즉시 해제 (메모리 고갈 방지) |
| `takePhoto` 실패 | `null` 반환, 에러 없이 스킵 (파이프라인 영속성) |
| `cameraRef.current` null | `null` 반환, 캡처 시도 안 함 |

---

## 9. Phase E: 통합 실기기 테스트 및 검증

### 9.1 검증 매트릭스

| 항목 | 기대 결과 | 합격 기준 | 단계 |
| --- | --- | --- | --- |
| WS 연결 수립 | welcome 메시지 수신 | 3초 이내 | 1 |
| hello/인증 | auth_ok 응답 | 토큰 일치 시 성공 | 1 |
| echo 왕복 | 앱→서버→앱 | **RTT < 100ms** | 1 |
| 하트비트 | heartbeat/heartbeat_ack 5초 간격 | 타임아웃 없음 | 1 |
| 재연결 | 의도적 단절 후 복구 | 3회 이내 성공 | 1 |
| WebSocketDisconnect | 소켓 close + 리소스 해제 | 예외 없이 정리 | 1 |
| 카메라 권한 요청 | 승인 다이얼로그 | iOS/Android 모두 | 2 |
| 후면 카메라 활성화 | `isActive=true` | `device !== null` | 2 |
| 반사 캡처 10fps | setInterval 주기 | ±100ms 오차 | 2 |
| 인지 캡처 2fps | setInterval 주기 | ±100ms 오차 | 2 |
| base64 변환 | JPEG base64 문자열 | 30~50KB 범위 | 2 |
| 서버 프레임 수신 | 디코딩 성공 | 640×640, 30~50KB | 2 |
| **캡처수신 지연** | 전체 파이프라인 | **< 50ms** | 2 |
| ack 응답 | event_id 일치 | decode_ms 포함 | 2 |
| 소켓 유실 타이머 해제 | clearInterval | 자원 해제 확인 | 2 |

### 9.2 테스트 환경

| 항목 | 설정 |
| --- | --- |
| 서버 실행 | macOS/Windows 로컬 `uvicorn server.main:app --host 0.0.0.0 --port 8000` |
| 단말 네트워크 | 서버와 **동일 WiFi망**, `WS_URL` = 서버 LAN IP |
| 디바이스 등록 | `auth.py`에 `dev-001`/`token-abc-001` 사전 등록 |
| iOS 테스트 | 실기기 필수 (시뮬레이터 카메라 미지원) |
| Android 테스트 | 실기기 또는 에뮬레이터 (가상 카메라) |

### 9.3 테스트 시나리오

```mermaid
graph LR
    T1["서버 기동<br/>uvicorn"] --> T2["앱 시작<br/>WS 연결"]
    T2 --> T3{"welcome<br/>수신?"}
    T3 -->|"실패"| T4["WS 디버그<br/>RTT/재연결"]
    T3 -->|"성공"| T5["카메라 권한<br/>승인"]
    T5 --> T6{"캡처<br/>시작?"}
    T6 -->|"실패"| T7["권한/디바이스<br/>가드레일"]
    T6 -->|"성공"| T8["서버 로그<br/>프레임 수신 확인"]
    T8 --> T9{"캡처수신<br/>< 50ms?"}
    T9 -->|"실패"| T10["FPS/압축<br/>튜닝"]
    T9 -->|"성공"| T11["합격<br/>1+2단계 완료"]
```

---

## 10. 작업 순서 및 의존성

### 10.1 순차 의존성

```mermaid
graph LR
    A["Phase A<br/>서버 WS 라우터"] --> B["Phase B<br/>Expo 초기화"]
    B --> C["Phase C<br/>WS 훅"]
    C --> D["Phase D<br/>카메라 캡처"]
    D --> E["Phase E<br/>통합 테스트"]
    A -.->|"end-to-end<br/>테스트 위해"| E
```

> 서버(A)를 먼저 구축해야 클라이언트(C/D)의 end-to-end 테스트가 가능합니다.

### 10.2 브랜치 전략

| 항목 | 내용 |
| --- | --- |
| 작업 브랜치 | `kb` (현재) |
| 병합 대상 | `dev` (PR 기반, `master`/`main` 직접 push 금지) |
| PR 단위 | Phase A 완료 후 1차 PR, Phase B+D 완료 후 2차 PR (또는 전체 완료 후 단일 PR) |

---

## 11. 산출물 목록

### 11.1 서버측 (Phase A)

| 파일 | 유형 | 역할 |
| --- | --- | --- |
| `server/api/config.py` | 신규 | 환경 설정 |
| `server/api/schemas.py` | 신규 | Pydantic 스키마 |
| `server/api/auth.py` | 신규 | 디바이스 토큰 검증 (MVP 하드코딩) |
| `server/api/session_manager.py` | 신규 | 연결 추적 싱글턴 |
| `server/api/heartbeat.py` | 신규 | 5초 ping/pong 하트비트 |
| `server/api/ws_router.py` | 신규 | `/ws/detect` 엔드포인트 (핵심) |
| `server/main.py` | 수정 | `ws_router` 마운트 추가 |
| `tests/test_ws_echo.py` | 신규 | RTT < 100ms echo 검증 |

### 11.2 클라이언트측 (Phase B+D)

| 파일 | 유형 | 역할 |
| --- | --- | --- |
| `client/app.json` | 신규 | Expo 설정, 권한 |
| `client/package.json` | 신규 | 의존성 |
| `client/tsconfig.json` | 신규 | TypeScript 설정 |
| `client/App.tsx` | 신규 | 엔트리 포인트 |
| `client/src/config/index.ts` | 신규 | WS_URL, 디바이스, FPS 설정 |
| `client/src/types/detection.ts` | 신규 | 타입 정의 |
| `client/src/hooks/useWebSocket.ts` | 신규 | WS 연결/하트비트/재연결 |
| `client/src/hooks/useCamera.ts` | 신규 | 이중 캡처 타이머 |
| `client/src/services/frameCapture.ts` | 신규 | 프레임 전송 서비스 |
| `client/src/components/CameraView.tsx` | 신규 | 카메라 + WS 연동 |
| `client/src/components/ConnectionStatus.tsx` | 신규 | 접속 상태 표시 |
| `client/src/utils/haptics.ts` | 신규 | 햅틱/접근성 stub |

---

## 12. 위험 및 완화

| 위험 | 영향 | 완화 |
| --- | --- | --- |
| iOS 시뮬레이터 카메라 미지원 | iOS 테스트 불가 | 실기기 필수, macOS 환경 확보 |
| Windows에서 iOS 빌드 불가 | 교차 빌드 제약 | iOS 빌드는 macOS에서만, Windows는 Android 한정 |
| WiFi망 지연 변동 | RTT/캡처수신 KPI 달성 불확실 | 동일 LAN망 사용, 반복 측정 |
| `react-native-vision-camera` 버전 호환 | 네이티브 빌드 실패 | v4 안정 버전 고정, `expo-dev-client` 호환 매트릭스 확인 |
| 프레임 크기 초과 | 서버 디코딩 거부 | 640×640 JPEG 품질 조정, 30~50KB 범위 유지 |
| Redis 미기동 시 메타데이터 발행 실패 | risk.events 누락 | `redis_bus` 연결 실패 시에도 Queue push는 유지 (이중 가드레일) |

---

## 13. 다음 패스 예정 (범위 밖)

| 항목 | 단계 | 비고 |
| --- | --- | --- |
| 음성/햡틱 재생 (반사 클립 선점 + 인지 TTS 수신) | 7단계 클라이언트측 | `haptics.ts` 본격 구현, `reflexClipPlayer`, `audioPlayer` |
| 반사 클립 사전합성 | 7단계 서버측 | `data/reflex_clips/` MP3 번들 |
| 서버 디바이스 인증 DB 연동 | 1단계 확장 | `REGISTERED_DEVICES` → `.env`/DB |
| EAS Build 도입 | 인프라 | 클라우드 iOS 빌드 (Windows 지원) |
| 운영자 콘솔 연동 | 별도 | `console/` React 앱, SSE 구독 |

---

## 14. 참고 자료

| 자료 | 경로 |
| --- | --- |
| 설계 노트 (원본) | [`docs/minchodan_design_note.md`](minchodan_design_note.md) |
| API 명세서 | [`docs/api_specification.md`](api_specification.md) |
| 시스템 아키텍처 | [`docs/architecture.md`](architecture.md) |
| 2단계 캡처 설계서 | [`docs/stage2_capture_design.md`](stage2_capture_design.md) |
| WebSocket 게이트웨이 스킬 | [`.agents/skills/websocket-gateway/SKILL.md`](../.agents/skills/websocket-gateway/SKILL.md) |
| 카메라 프레임 캡처 스킬 | [`.agents/skills/camera-frame-capture/SKILL.md`](../.agents/skills/camera-frame-capture/SKILL.md) |
| 코딩 패턴 기준 | [`docs/course_codebase_guide.md`](course_codebase_guide.md) |
| 테스트 명세서 | [`docs/test_specification.md`](test_specification.md) |
| 환경 변수 명세서 | [`docs/environment_variables.md`](environment_variables.md) |
| react-native-vision-camera | https://react-native-vision-camera.com/ |
| Expo Dev Client | https://docs.expo.dev/develop/development-builds/introduction/ |
