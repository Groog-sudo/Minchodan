# Minchodan API 명세서

> **작성일**: 2026-06-24
> **버전**: v0.4.4 (2026-07-10 §2.4 heartbeat 타임아웃 유예 5→15초 상향 및 서버측 ack/heartbeat 응답 레이스 컨디션 수정 반영 + 이전 v0.4.3 이력 유지)
> **설계 기준**: `docs/design/minchodan_design_note.md` 1·2·3·7단계 인터페이스
> **구현 상태**: 1+2+3단계 구현 완료. `/ws/detect` 핸드셰이크(hello/welcome/auth_ok/heartbeat), detection 페이로드(640x640 압축 이미지), ack 응답, 단말 측 Reflex Gate 4단계 피드백(주차센서식 거리 반비례 햅틱/비프음) 정합 확인. `reflex_alert`/`guide`는 6·7단계 범위로 미구현(설계상 정상).
> **코딩 패턴 기준**: [`docs/dev-guides/course_codebase_guide.md`](../dev-guides/course_codebase_guide.md)

---

## 0. Swagger UI 참조 안내

`http://{host}:8000/docs` 에 접근하면 FastAPI 자동 생성 OpenAPI(OAS 3.1) 문서를 볼 수 있습니다.

| 화면 표시 항목 | 비고 |
| :--- | :--- |
| `GET /api/v1/monitor/stream` | SSE 실시간 모니터링 스트림 |
| `GET /health` | 서버 헬스체크 |
| `WS /ws/detect` | **Swagger UI 자동 렌더링 미지원** (OAS 3.1 한계) — 아래 섹션 전체 명세 참조 |

> WebSocket은 OAS 3.1 규격상 Swagger UI에 자동으로 항목이 생성되지 않습니다. 본 문서의 2·3·4·5섹션을 참고하십시오.

---

## 1. 공통 규격

### 전송 프로토콜

| 항목 | 값 |
| :--- | :--- |
| 프로토콜 | WebSocket (RFC 6455) |
| 엔드포인트 | `ws://{host}:{WS_PORT}/ws/detect?device_id={id}` |
| 인코딩 | JSON (텍스트 프레임) / base64 (이미지) |
| 인증 | `device_token` (hello 핸드셰이크 시 검증) |
| 하트비트 | 5초 ping/pong |
| 이미지 규격 | **640x640 JPEG, compress 50%, base64** (expo-image-manipulator 네이티브 GPU 압축) |
| 이미지 크기 | 장당 약 12~92KB (원본 대비 약 1/40 수준) |

### 공통 메시지 형식

모든 메시지는 JSON 객체이며 `type` 필드로 이벤트 종류를 구분합니다.

| 필드 | 설명 |
| :--- | :--- |
| `type` | 메시지 타입 (hello, welcome, detection, ack, reflex_alert, guide, heartbeat, error) |
| `event_id` | 이벤트 추적 식별자 (UUID) |
| `device_id` | 단말 식별자 |
| `ts` | 타임스탬프 (epoch ms) |
| `payload` | 타입별 페이로드 |

---

## 2. WebSocket 핸드셰이크 (1단계)

### 2.1 hello (단말 → 서버)

```json
{
  "type": "hello",
  "device_id": "dev-001",
  "token": "device_token_value"
}
```

| 필드 | 설명 |
| :--- | :--- |
| `device_id` | 단말 고유 식별자 |
| `token` | 사전 발급된 디바이스 토큰 |

### 2.2 welcome (서버 → 단말)

```json
{
  "type": "welcome",
  "session_id": "dev-001",
  "server_time": "2026-07-05T06:00:00.000Z"
}
```

| 필드 | 설명 |
| :--- | :--- |
| `session_id` | 세션 식별자 (이후 이벤트 추적 기준) |
| `server_time` | 서버 시각 (ISO 8601) |

### 2.3 auth_ok (서버 → 단말)

```json
{
  "type": "auth_ok",
  "device_id": "dev-001"
}
```

### 2.4 heartbeat

서버가 5초 간격(`HEARTBEAT_INTERVAL`)으로 ping을 송신하고 단말은 pong으로 응답합니다. `HEARTBEAT_INTERVAL+HEARTBEAT_TIMEOUT`(기본 5+15=20초) 동안 ack가 없으면 서버가 세션을 종료합니다.

| 방향 | 메시지 |
| :--- | :--- |
| 서버 → 단말 | WebSocket ping 프레임 또는 `{"type":"heartbeat", "ts"}` |
| 단말 → 서버 | WebSocket pong 프레임 또는 `{"type":"heartbeat_ack", "ts"}` |

> **2026-07-10 정정**: 기존 타임아웃 유예(5+5=10초)는 ngrok 등 공인망 릴레이 경유 시 왕복 지연으로 정상 연결도 오탐 종료시켰다(`server/api/heartbeat.py`가 타임아웃 시 `ws.close()`를 호출하는 것과, 메인 루프(`server/api/ws_router.py`)가 동시에 ack/heartbeat 응답을 `ws.send_json()`하려는 시점이 겹치면 `Cannot call "send" once a close message has been sent` 예외로 세션 전체가 끊겼다). `HEARTBEAT_TIMEOUT`을 15초로 상향하고, 메인 루프의 ack/pong/heartbeat_ack 전송을 `contextlib.suppress(Exception)`로 감싸 레이스가 발생해도 세션이 죽지 않도록 방어했다(실제로 끊긴 소켓이면 다음 `ws.receive()`가 `WebSocketDisconnect`로 정상 정리한다).

### 2.5 error (서버 → 단말)

```json
{
  "type": "error",
  "code": "auth_failed",
  "message": "디바이스 토큰 검증 실패"
}
```

| `code` | 설명 |
| :--- | :--- |
| `auth_failed` | 디바이스 토큰 검증 실패 |
| `bad_request` | 메시지 형식 오류 |
| `rate_limited` | 프레임 전송 과다 |
| `internal` | 서버 내부 오류 |

---

## 3. 프레임 전송 (2단계)

### 3.1 detection - 바이너리 전송 (기본, 2026-07-07 신설)

실기기 클라이언트는 **base64를 경유하지 않고** JSON 메타데이터 메시지와 raw JPEG 바이트 바이너리 프레임을 순차 전송한다. 단일 WS 연결에서 프레임 전송 순서는 보장되므로, 서버는 `transport: "binary"` 메타를 받은 직후 도착하는 바이너리 프레임을 해당 이벤트로 짝짓는다.

```json
{
  "type": "detection",
  "payload": {
    "event_id": "uuid",
    "device_id": "dev-001",
    "ts": 1719216000000,
    "frame_id": 42,
    "stream": "reflex",
    "transport": "binary"
  }
}
```

위 텍스트 메시지 직후, 별도의 WS **바이너리 프레임**으로 raw JPEG 바이트(640x640, JPEG 50% 압축)를 전송한다(JSON 필드 아님, base64 인코딩 없음).

| 필드 | 설명 |
| :--- | :--- |
| `payload.stream` | `reflex` (8~10fps) 또는 `cognitive` (1~2fps) |
| `payload.frame_id` | 프레임 일련 번호 |
| `payload.transport` | `"binary"` 고정 - 서버가 다음 바이너리 프레임을 이 메타와 짝지어야 함을 표시 |

> **바이너리 전송 도입 사유 (2026-07-07)**: base64 인코딩은 페이로드 크기를 약 33% 증가시키고 JS/서버 양쪽에 인코딩·디코딩 CPU 오버헤드를 유발한다. 클라이언트는 `expo-file-system`의 `File(uri).bytes()`로 raw JPEG `Uint8Array`를 직접 얻어 `WebSocket.send(bytes)`로 전송하고, 서버(`server/api/ws_router.py`)는 `ws.receive()`로 텍스트/바이너리 프레임을 구분해 `decode_frame_binary()`(`server/capture/frame_decoder.py`)로 base64 디코딩 단계 없이 바로 `cv2.imdecode`한다.

### 3.2 detection - base64 전송 (구버전 호환)

바이너리 전송을 지원하지 않는 클라이언트(Mock 모드 등)를 위해 기존 단일 JSON 메시지 방식도 계속 지원한다.

```json
{
  "type": "detection",
  "payload": {
    "event_id": "uuid",
    "device_id": "dev-001",
    "ts": 1719216000000,
    "frame_id": 42,
    "stream": "reflex",
    "thumbnail_jpeg_b64": "/9j/4AAQ..."
  }
}
```

| 필드 | 설명 |
| :--- | :--- |
| `payload.thumbnail_jpeg_b64` | **640x640 JPEG 압축 base64 프레임** (expo-image-manipulator 50% compress). `payload.transport`가 없으면 이 필드가 필수 |

> **이미지 압축 규격 (2026-07-05 신설)**:
> 단말 클라이언트는 `expo-image-manipulator`의 네이티브 GPU 가속을 통해 원본 캡처 이미지를 640x640 픽셀로 크롭하고 JPEG 50% 수준으로 압축하여 전송합니다. 장당 전송 크기는 약 12~92KB이며, 이는 원본(약 3.4MB) 대비 약 1/40 수준입니다. YOLO26n(640x640) 및 Llava(336x336) 추론 품질에 손실 없음이 검증되었습니다. (바이너리 전송 시에는 이 크기에서 base64의 33% 증가분이 추가로 빠진다.)

### 3.2 ack (서버 → 단말)

```json
{
  "type": "ack",
  "event_id": "uuid",
  "frame_id": 42,
  "decode_ms": 12
}
```

| 필드 | 설명 |
| :--- | :--- |
| `decode_ms` | 서버 수신·디코딩 소요 시간 (ms) |

---

## 4. 반사 경로 메시지 (3·7단계, 고우선)

반사 경로는 LLM/RAG/실시간 TTS를 경유하지 않으며, 사전합성 음성 클립을 즉시 재생합니다.

### 4.1 reflex_alert (서버 → 단말, 고우선)

```json
{
  "type": "reflex_alert",
  "event_id": "uuid",
  "alert_id": "high_car_front",
  "direction": "front",
  "risk_level": "high",
  "clip": "reflex_clips/high_front.wav",
  "haptic": true,
  "panning": 0.0,
  "distance": 1.0,
  "beep_interval_ms": 250,
  "haptic_pattern": "double",
  "ts": 1719216000000
}
```

| 필드 | 설명 |
| :--- | :--- |
| `alert_id` | 알림 식별자(중복 억제 키). **2026-07-09 정정**: `reflex_gate.py`는 클래스명을 포함한 동적 값(`high_{class_name}_{direction}`, 예: `high_car_front`)을 생성한다 — 클립 선택에는 쓰이지 않고 60초 억제 키로만 쓰인다 |
| `direction` | 방향 (`front`, `front-left`, `front-right`) |
| `risk_level` | `high` (반사 경로 전용) |
| `clip` | 단말 번들 사전합성 클립 경로(`client/assets/sounds/reflex_clips/`, basename 매칭). **2026-07-09 정정**: 클래스와 무관하게 방향/유형 기준으로 고정되며, 확장자는 `.wav`(인코더 제약으로 mp3 대신 채택) |
| `haptic` | 햅틱 동시 출력 여부 |
| `panning` | 스테레오 사운드 좌우 지향 밸런스 값 (-1.0 ~ 1.0). 클라이언트는 5단계 버킷(`-1.0/-0.5/0.0/0.5/1.0`)으로 반올림해 재생한다 |
| `distance` | 역산된 장애물 거리 (0.4m ~ 1.5m) |
| `beep_interval_ms` | 비프음 주기 (ms, 0은 연속 경고음) |
| `haptic_pattern` | 진동 패턴 (`short` \| `double` \| `continuous` \| `light`) |

선점 규칙: 반사 음성은 인지 음성을 중단시키고 재생합니다. 중복 억제는 서버 `setex(suppress:{alert_id}, 60)`로 처리합니다.

### 4.2 clip 사전 정의

**2026-07-09 정정**: 이전 표는 실제 게이트 3곳(`reflex_gate.py`/`surface_gate.py`/`head_level_gate.py`)이 생성하는 값과 맞지 않는 상상 속 파일명 목록이었다(예: `high_left`/`high_stop`은 존재하지 않음, direction은 `front`/`front-left`/`front-right` 3종뿐). 실제 게이트 출력 기준으로 정정한다.

| `clip` (basename) | 방향 | 트리거 | 발생 게이트 |
| :--- | :--- | :--- | :--- |
| `high_front.wav` | front | 고위험 객체(차량류 5종) 발밑 근접, 정면 회랑 | `reflex_gate.py` |
| `high_front-left.wav` | front-left | 고위험 객체 발밑 근접, 좌측 회랑 | `reflex_gate.py` |
| `high_front-right.wav` | front-right | 고위험 객체 발밑 근접, 우측 회랑 | `reflex_gate.py` |
| `surface_caution.wav` | front | 노면 P0 클래스(`caution`, 계단/맨홀/그레이팅 통합) 하단 검출 | `surface_gate.py` |
| `head_level_warning.wav` | 탐지 방향 | 중위험 클래스가 화면 상단 40%(머리 높이)에서 검출돼 고위험으로 격상. **2026-07-09 신규** | `head_level_gate.py` |

---

## 5. 단말 측 Reflex Gate 피드백 규격 (2단계 클라이언트 확장, 2026-07-05 신설)

서버 `reflex_alert` 페이로드와 별개로, 단말 클라이언트(`CameraView.tsx`)는 온디바이스 CoreML 추론 결과(`allDetections`)를 실시간으로 분석하여 **주차센서식 거리 반비례 4단계 즉각 피드백**을 자체적으로 구동합니다.

> 이 피드백은 서버 왕복 지연 없이 단말 온디바이스에서 즉시 발화되는 Reflex Gate 구현체입니다.

### 5.1 거리 추정 공식

```
areaRatio = (bbox.w * bbox.h) / (640 * 640)
```

단일 2D 카메라 피드 상에서 탐지 박스 면적의 전체 프레임 대비 점유율을 거리 팩터로 사용합니다.

### 5.2 4단계 피드백 캘리브레이션

| 단계 | 조건 | 햅틱 패턴 | 비프음 주기 | 설명 |
| :---: | :--- | :--- | :--- | :--- |
| **1단계** | `ratio > 0.32` 또는 긴급 클래스 `ratio > 0.20` | `continuous` | 0ms (연속음) | 초접근 — 코앞 충돌 위기 |
| **2단계** | `ratio > 0.12` 또는 긴급 클래스 `ratio > 0.08` | `double` | 200ms | 근접 — 충돌 방어 제동 필요 |
| **3단계** | `ratio > 0.03` | `short` | 600ms | 중거리 — 방향 전환 권고 |
| **4단계** | `ratio <= 0.03` | 없음 | 1200ms | 원거리 — 존재 인지만 |
| **안전** | 탐지 없음 | 없음 | 없음 | 햅틱/비프음 완전 정지 |

### 5.3 긴급 위험 클래스 목록 (가중치 적용)

아래 클래스는 일반 사물 대비 격상 문턱값(Threshold)을 약 40% 낮춰 더 민감하게 발화합니다.

```
person, bicycle, car, motorcycle, bus, truck, skateboard, pothole, caution
```

### 5.4 BBox 오버레이 색상 규격

| 클래스 그룹 | 색상 | 예시 |
| :--- | :--- | :--- |
| 긴급 충돌 위험군 | `#EF4444` (빨강 고정) | `person`, `car`, `bicycle` |
| 지면/도로 위험군 | `#F59E0B` (주황 고정) | `roadway` |
| 일반 사물 | `hsl(hash, 85%, 55%)` (해시 기반 고유 컬러) | `keyboard`, `cup` 등 |

---

## 6. 인지 경로 메시지 (6·7단계)

인지 경로는 Redis Streams(`risk.events`) → LangGraph L1/L2/L3 + RAG → 실시간 TTS 흐름을 거칩니다.

### 6.1 guide (서버 → 단말)

**2026-07-09 변경**: guide 오디오는 더 이상 `audio_mp3_b64`(base64 JSON 필드)로 전송되지
않는다. §3의 client→server 바이너리 프레임 프로토콜과 동일한 방식을 반대 방향(server→client)에
적용해, JSON 메타데이터 메시지 직후 raw WAV 바이트를 별도 WS **바이너리 프레임**으로 전송한다.
실기기 실측 결과 base64 인코딩/디코딩 경로 자체가 원인은 아니었으나(§ 아래 비고 참조), 카메라
프레임 전송과 동일한 아키텍처로 통일해 페이로드 크기와 처리 오버헤드를 줄인다.

```json
{
  "type": "guide",
  "event_id": "uuid",
  "risk_level": "mid",
  "guidance_text": "전방 킥보드, 우측으로 한 발 물러서세요",
  "audio_codec": "wav",
  "duration_ms": 4820.5,
  "transport": "binary",
  "sources": [{ "citation_number": 1, "label": "VEC_0", "role": "vector" }],
  "ts": 1719216000000
}
```

위 텍스트 메시지 직후, 별도의 WS **바이너리 프레임**으로 raw WAV 바이트(합성 실패 시 프레임
없이 `transport: "none"`)를 전송한다(JSON 필드 아님, base64 인코딩 없음). 클라이언트
(`client/src/hooks/useWebSocket.ts`)는 `ws.binaryType = "arraybuffer"`로 수신해
`audioEngine.playGuideAudioBytes(Uint8Array)`에 그대로 전달한다.

| 필드 | 설명 |
| :--- | :--- |
| `guidance_text` | L2/L3 생성 가이드 문장 (한국어 1문장, 20자 내, 방향 포함) |
| `audio_codec` | 오디오 코덱 (현재 `wav` 고정) |
| `duration_ms` | 합성된 오디오 재생 길이(ms). 서버가 다음 guide 전송까지의 쿨다운을 이 값 기반으로 동적 산정(`server/detection/consumer.py`)하는 데 사용, 클라이언트는 참고용 |
| `transport` | `"binary"`(이 메시지 직후 오디오 바이너리 프레임이 이어짐) 또는 `"none"`(서버 TTS 합성 실패, 클라이언트는 `guidance_text`로 단말 내장 TTS 폴백) |
| `sources` | RAG 근거 인용 (선택) |

> **비고 (2026-07-09)**: 실기기에서 안내 음성이 문장 중간에 끊기던 근본 원인은 base64
> 전송 방식이 아니라 (1) 서버 TTS 엔진(Piper) 자체의 발음 품질 한계와 (2) 반사 캡처가
> `takePhoto()`(정지사진 반복 촬영)를 써서 촬영마다 iOS 오디오 세션을 인터럽트하던
> 문제였다. 자세한 경위는 `docs/stage-guides/stage7_tts_design.md` §TTS 엔진, `docs/changelogs/kb.md`
> 참조. 바이너리 전송 전환 자체는 페이로드 최적화 목적으로 유지한다.

### 6.2 status (서버 → 단말, 진행 알림)

```json
{
  "type": "status",
  "event_id": "uuid",
  "stage": "l2_generating",
  "ts": 1719216000000
}
```

| `stage` | 설명 |
| :--- | :--- |
| `detecting` | 탐지 수행 중 |
| `rag_searching` | RAG 검색 중 |
| `l1_classifying` | L1 위험도 분류 중 |
| `l2_generating` | L2 가이드 생성 중 |
| `l3_validating` | L3 검증 중 |
| `tts_synthesizing` | 실시간 TTS 합성 중 |

### 6.3 stt_audio (단말 → 서버, 2026-07-09 신설)

음성 명령(네비게이션 켜기/끄기, 목적지 설정 등) 캡처 결과를 서버로 전달합니다. 단말은
녹음만 담당하고("서버가 모든 추론 수행" 원칙), 실제 음성 인식(faster-whisper)은
서버(`server/api/ws_router.py`의 `_handle_stt_audio`)가 수행합니다.

```json
{
  "type": "stt_audio",
  "audio_b64": "UklGRi...",
  "model_name": "faster-whisper-medium"
}
```

| 필드 | 설명 |
| :--- | :--- |
| `audio_b64` | 녹음된 오디오 파일 전체를 base64 인코딩한 값 (필수). 컨테이너 포맷은 서버의 `av` 기반 디코더가 처리하므로 특정 포맷에 종속되지 않음(iOS `RecordingPresets.HIGH_QUALITY` 기준 m4a) |
| `model_name` | 선택. 미지정 시 `server/stt/stt_config.py`의 `DEFAULT_REQUEST_MODEL`(`faster-whisper-medium`) 사용 |

응답은 별도 신규 타입이 아니라 기존 **6.1 guide** 메시지로 온다(클라이언트가 이미
guide 수신 시 자동 재생하므로 신규 클라이언트 처리 불필요). 전사 실패 시에도
`guidance_text: "음성 인식에 실패했습니다..."`를 담은 guide 메시지로 응답한다(무응답 방지).

---

## 7. 탐지 결과 상세 (3단계, 내부/콘솔용)

탐지 결과는 서버 내부 `DetectionResult` 스키마이며 운영자 콘솔에 SSE/WS로 전달될 수 있습니다.

```json
{
  "event_id": "uuid",
  "detections": [
    {
      "class_name": "kickboard",
      "confidence": 0.87,
      "bbox": [120, 200, 280, 360],
      "track_id": 3
    }
  ],
  "surface": [
    {
      "class_name": "crosswalk",
      "mask": "...",
      "centroid": [320, 580]
    }
  ],
  "risk_hint": "mid",
  "inference_ms": 72
}
```

---

## 8. 운영자 콘솔 구독 SSE (`/api/v1/monitor/stream`)

운영자 모니터링 콘솔은 별도 SSE 스트리밍 채널을 사용합니다.

| 이벤트 타입 | 설명 |
| :--- | :--- |
| `connection_established` | 최초 연결 수립 확인 |
| `ping` | Keep-Alive 하트비트 (1초 간격) |
| MCP 메트릭 이벤트 | Redis Streams `risk.events` 실시간 뷰 |

---

## 9. 예외 처리 가드레일

| 단계 | 예외 | 처리 |
| :--- | :--- | :--- |
| 1 | `WebSocketDisconnect` | 소켓 close + 리소스 해제 |
| 2 | 카메라 권한 거부 (`NotAllowedError`) | 단말에서 안내 후 종료 |
| 2 | 소켓 유실 | `clearInterval` 타이머 자원 즉시 해제 |
| 2 | 이미지 압축 실패 | `FileSystem.deleteAsync` 임시파일 강제 소멸 후 재시도 |
| 3 | 빈 버퍼/디코딩 실패 (`None`) | 에러 없이 빈 리스트 반환 |
| 5 | DB 손상/경로 부재 (`FileNotFoundError`) | 디폴트 안내 문자열 반환 |
| 6 | API 장애/Rate Limit | 디폴트 수칙 문장 즉시 반환 |
| 7 | TTS 호출 실패/타임아웃 | 기기 내장 TTS로 우회 |

상세 예외 처리는 `docs/design/minchodan_design_note.md` 각 단계의 **의존성·예외** 필드를 참조합니다.

---

## 10. 변경 이력

| 버전 | 날짜 | 변경 내용 |
| :--- | :--- | :--- |
| v0.1.0 | 2026-06-24 | 초안 작성 (1단계 WebSocket 핸드셰이크 설계) |
| v0.2.0 | 2026-06-29 | 2단계 프레임 전송(detection/ack) 규격 추가 |
| v0.2.1 | 2026-06-30 | 1+2단계 Phase A~D 구현 완료 반영 |
| **v0.3.0** | **2026-07-05** | **640x640 JPEG 이미지 압축 규격 신설 / 단말 Reflex Gate 4단계 피드백 규격 신설 / BBox 오버레이 색상 규격 신설 / Swagger UI openapi_tags 안내 섹션 추가 / 운영자 콘솔 SSE 명세 구체화** |
| v0.4.0 | 2026-07-07 | detection 프레임 바이너리 전송 프로토콜 추가, base64는 구버전 호환 경로로 격하 |
| v0.4.1 | 2026-07-09 | guide 메시지에 `audio_codec`, `duration_ms` 필드 추가 |
| **v0.4.2** | **2026-07-09** | **stt_audio(6.3) 신설 / reflex_alert clip·alert_id 사전 정의(4.2)를 실제 게이트 3곳 출력값으로 정정 / head_level_warning.wav 클립 추가** |
