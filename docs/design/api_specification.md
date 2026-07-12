# Minchodan API 명세서

> **작성일**: 2026-06-24
> **버전**: v0.4.15 (2026-07-12 §8.6에 app_users 회원 프로필 확장 필드(birth_date/guardian_phone/address, 전부 선택) 반영 + 이전 v0.4.14 이력 유지: §8.6 회원(시각장애인) 관리 REST 신설 - 관리자 콘솔의 회원 등록/전환/목록 API, 익명 자동등록(anon: 접두사) 레코드를 실명으로 전환하는 분기 로직 명세, §8.5 사후 이력 조회 REST 신설 - detection-logs 목록·event-frames 이미지 서빙, 이벤트 프레임 저장 계약(frame_path·보존 7일·백그라운드 저장), 인지 로그 detected_objects_json에 bbox 포함)
> **설계 기준**: `docs/design/minchodan_design_note.md` 1·2·3·7단계 인터페이스
> **구현 상태**: 1~7단계 전체 구현 완료. `/ws/detect` 핸드셰이크(hello/welcome/auth_ok/heartbeat), detection 페이로드, ack 응답, reflex_alert(사전합성 클립 선점), guide(실시간 TTS WAV), server_detection, realtime_gps, nav_route 정합 확인.
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
| `event_id` | 이벤트 추적 식별자. 단말 detection 프레임은 `event-{device_id}-{stream}-{epoch_ms}` 형식(**2026-07-11 구조화** - 기존 `event-{epoch_ms}`는 반사/인지 타이머가 같은 ms에 발화하면 충돌해 DB UNIQUE 중복 방지 로직이 두 번째 로그를 유실), 서버 발신은 `stt-`/`nav-` 접두 또는 UUID |
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

> **2026-07-11 정정**: 위 메인 루프의 `contextlib.suppress`와 별개로,
> `SessionManager.send_json()`/`send_bytes()`/`is_connected()`(`server/api/session_manager.py`)
> 자체에도 `ws.application_state == WebSocketState.CONNECTED` 가드를 추가했다. WS 연결이
> 끊어진 뒤에도 `active_connections`에서 즉시 제거되지 않는 경쟁 창(consumer 태스크가
> 독립적으로 실행 중)에서 `send`를 시도하면 동일한 `Cannot call send...` 에러가 스팸으로
> 발생했던 문제(13:26:47~52 로그, 17회 반복)를 원천 차단한다.

> **2026-07-11 추가 정정**: `SessionManager.send_json()`/`send_bytes()`는 실제 송신 성공
> 여부를 boolean으로 반환합니다. 반사 경보는 반환값이 `true`인 경우에만 60초 중복 억제를
> 기록하므로, 연결 종료 경쟁 구간에서 전달되지 않은 경보가 전송 완료로 처리되지 않습니다.

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
| `audio_b64` | 녹음된 오디오 파일 전체를 base64 인코딩한 값 (필수). 현재 iOS는 44.1kHz mono 16bit Linear PCM WAV, Android는 MPEG-4/AAC를 사용하며 서버의 `av` 기반 디코더가 처리합니다. |
| `model_name` | 선택. 미지정 시 `server/stt/stt_config.py`의 `DEFAULT_REQUEST_MODEL`(`faster-whisper-small`) 사용. **2026-07-11 기본 모델 medium→small 전환**: macOS Docker CPU 폴백 환경 실측에서 medium은 2초 발화 전사 2.3초·콜드스타트 로딩 8~10초로 STT 왕복 지연의 주 병목이었다. 명령어 위주 짧은 발화 + hotwords 바이어싱 조합 전제이며, 인식 품질 회귀 시 상수 1개만 medium으로 롤백한다. 콜드스타트는 `server/main.py` lifespan에서 백그라운드 스레드 프리로드로 별도 제거 |

응답은 별도 신규 타입이 아니라 기존 **6.1 guide** 메시지로 온다(클라이언트가 이미
guide 수신 시 자동 재생하므로 신규 클라이언트 처리 불필요). 전사 실패 시에도
`guidance_text: "음성 인식에 실패했습니다..."`를 담은 guide 메시지로 응답한다(무응답 방지).

> **비고 (2026-07-10)**: `_handle_stt_audio`(`server/api/ws_router.py`)가 응답 오디오를
> §6.1의 `transport: "binary"` 규격이 아니라 구버전 `audio_mp3_b64`(JSON base64 필드)로
> 보내고 있어, 클라이언트(`useWebSocket.ts`)가 `transport !== "binary"` 조건으로 서버
> TTS 오디오를 항상 무시하고 단말 내장 TTS로만 폴백하던 결함을 실기기 실측으로 발견해
> 수정했다(§6.1 규격과 동일하게 통일). 자세한 경위는 `docs/changelogs/kb.md` 2026-07-10
> 항목 참조.

`stt_audio`로 전달되는 발화는 `server/stt/stt_to_llm_bridge.py`가 다음 명령 어휘로
분기한다(디바이스별 상태는 `NavigationManager`가 `status`/`awaiting_free_question`/
`awaiting_intent` 3개 독립 플래그로 관리).

| 발화(예시) | 동작 | 비고 |
| :--- | :--- | :--- |
| `길댕아` (또는 유사 발음) | 2단계 진입 대기 상태로 전환, "길 찾아드릴까요, 질문 받을까요?" 응답 | 정확 문자열 매칭이 아니라 **편집거리(Levenshtein) ≤1 퍼지 매칭**("길댕"과 비교) - "길대가"/"결댕아"/"길땡아" 등 STT 오인식 변형까지 흡수 |
| `길찾아줘` (대기 중) | 목적지 대기 상태(`WAITING_FOR_DESTINATION`)로 전환 | 이어지는 발화를 목적지명으로 파싱해 TMAP POI 검색 + 경로 계산 수행 |
| `물어볼게` (대기 중) | 자유 질의응답 대기 상태로 전환 | 이어지는 발화를 장애물 회피 오케스트레이터가 아닌 순수 LLM 대화로 처리(§ 아래 참조) |
| `네비게이션 켜줘` / `질문할게` 등 | 위 2단계 웨이크워드 없이 바로 진입하는 기존 단일 트리거(하위 호환 유지) | "네비게이션"/"내비게이션" 표기는 매칭 전 정규화 |
| 자유 질의(대기 상태에서) | "가까운/근처/주변" + 장소 유형(지하철역·편의점·화장실 등)이 감지되면 TMAP 실거리 검색(`helper_search_nearest_poi`, Haversine 거리순)으로 사실 기반 답변. 그 외는 LLM 자유 대화 | 위치 사실을 LLM에 맡기지 않고 실제 API 조회 결과로만 답해 환각을 방지 |

> **비고 (2026-07-10)**: 목적지 설정 시 `NavigationManager` 세션 키를 `"default_device"`로
> 하드코딩해뒀던 결함이 있었다 - GPS 갱신(`realtime_gps`)과 턴바이턴 안내 조회
> (`get_combined_guidance`)는 실제 `device_id`의 세션을 보는데, 목적지만 별도의 가짜
> 세션에 저장되어 **목적지 설정은 성공해도 실제 길안내 음성이 영구히 나올 수 없는
> 구조**였다. `invoke_existing_llm(stt_result, device_id)`로 실제 device_id를 그대로
> 전달하도록 수정.

> **비고 (2026-07-11) - 자기-에코 감지**: TTS 안내문이 스피커로 재생되는 도중 사용자가
> 녹음 버튼을 누르면 마이크가 안내문을 주워듣고 Whisper가 전사한다. 이 전사에 웨이크업
> 키워드가 포함되면 메아리 루프(안내문 -> 재녹음 -> 전사 -> 웨이크업 재발동 -> 동일
> 안내문)가 발생한다(실기기 13:24:07 로그로 확인). 서버(`stt_to_llm_bridge.py`)는
> device_id별 최근 안내문을 10초간 보관(`_recent_guidance`)하고, 전사 결과가 이 안내문과
> 유사하면 `source: "stt-echo-detected"`로 빈 응답을 반환해 클라이언트에 응답을 보내지
> 않는다(`ws_router._process_stt_audio`에서 스킵). 클라이언트(`CameraView.tsx`)는 TTS
> 재생 중 녹음 시작 시 `stopGuideAudio()` 후 150ms 대기해 스피커 잔향이 멈춘 뒤 마이크를
> 활성화하는 이중 방어를 적용한다.

> **비고 (2026-07-11) - 인텐트 대기 상태 체크 순서**: `awaiting_intent` 대기 상태에서
> 발화 분기 우선순위를 `nav intent -> question intent -> wake 재호출 -> else(재질문)`로
> 변경했다(이전: wake 재호출이 최우선). "길댕아 길찾아줘"라고 말하면 wake 매칭이 먼저
> True가 되어 인텐트 매칭 전에 리턴해버려, 목적지 대기 상태로 진입하지 못하고 같은
> 안내만 반복하던 문제(5회 반복 로그 확인)를 해결.

> **비고 (2026-07-11) - 민감정보와 플랫폼별 검증**: 서버는 STT 원본 오디오와 전사문을
> 영구 파일, INFO 로그, DB에 저장하지 않습니다. 요청 단위 임시 파일은 전사 후 즉시
> 삭제하며 DB에는 `text_length` 같은 비식별 메타만 남깁니다. 클라이언트의 캡처 길이
> 검사는 비압축 PCM인 iOS에만 적용하고, Android MPEG-4/AAC에는 PCM 바이트 공식을
> 적용하지 않습니다.

### 6.4 server_detection (서버 → 단말, 실시간 BBox 업데이트)

서버에서 실시간 YOLO 및 노면 분할(Segmentation) 추론을 완료할 때마다, 탐지된 모든 사물 및 노면의 BBox/Centroid 정보를 모바일 화면 렌더링용으로 브로드캐스트합니다.

```json
{
  "type": "server_detection",
  "event_id": "uuid",
  "detections": [
    {
      "model": "object_detection",
      "className": "scooter",
      "confidence": 0.87,
      "bbox": {
        "x": 120,
        "y": 200,
        "w": 160,
        "h": 160
      }
    },
    {
      "model": "segmentation",
      "className": "caution",
      "confidence": 0.92,
      "bbox": {
        "x": 280,
        "y": 540,
        "w": 80,
        "h": 80
      }
    }
  ],
  "ts": 1719216000000
}
```

| 필드 | 설명 |
| :--- | :--- |
| `detections` | 모바일 화면 렌더링용 BBox 정보 배열. 노면 분할(`segmentation`) 결과의 centroid 좌표는 서버 단에서 80x80 크기의 가상 BBox로 변환하여 동일 포맷으로 전달 |

> **비고 (2026-07-11) - 폴백 모드 BBox 표시**: WS 연속 3회 재연결 실패로 폴백 모드
> (`status === "fallback"`)에 진입하면 `server_detection`이 수신되지 않는다. 이때 단말은
> 온디바이스 CoreML 추론 결과(det + seg)를 `CameraView.tsx`에서 직접 `detections`
> 상태에 반영해 BBox를 표시한다(`isMockModeRef.current || wsStatusRef.current ===
> "fallback"` 조건). 정상 연결 시에는 서버 결과를 온디바이스 결과가 덮어쓰지 않도록
> 폴백 모드에서만 온디바이스 결과를 사용한다. **2026-07-11 정책 변경**: 폴백 진입
> 후에도 재연결을 포기하지 않고 지수 백오프(1s~30s)로 무한 재시도하며, 폴백 전환과
> 복구를 각각 음성으로 고지한다. 폴백 상태는 백그라운드 재시도 중에도 유지되고
> welcome 수신 시에만 해제된다(`useWebSocket.ts`).

---

### 6.5 realtime_gps (단말 → 서버, GPS 내비게이션, 2026-07-10 신설)

단말이 `expo-location`의 `watchPositionAsync`로 수신한 좌표를 실시간 전송하면, 서버는 `NavigationManager`(`server/navigation/manager.py`)의 디바이스별 세션에 현재 위치를 갱신합니다. 응답 메시지는 없다(fire-and-forget).

```json
{
  "type": "realtime_gps",
  "lat": 37.5665,
  "lon": 126.9780,
  "heading": 45.0
}
```

| 필드 | 설명 |
| :--- | :--- |
| `lat` | 위도 (필수) |
| `lon` | 경도 (필수) |
| `heading` | 방위각(도, 0~360). 선택, 미제공 시 `None`으로 처리 |

`lat`/`lon` 중 하나라도 누락되면 서버는 조용히 무시한다(에러 응답 없음). TMAP 보행자 경로 안내(`server/navigation/pedestrian_navigation.py`)와 결합되어 실시간 TTS로 안내 문장이 발화된다.

> **비고 (2026-07-11) - 길안내 무음 결함 수정**: 기존에는 턴바이턴 멘트 조회
> (`get_combined_guidance`)가 `DetectionConsumer._send_cognitive_guide` 내부에만 있어
> 카메라 탐지가 없는 빈 장면에서는 NAVIGATING 상태여도 안내가 전혀 발화되지 않았다
> (실기기 실측: 경로 113 웨이포인트 설정 후 무음). 길안내는 위치 이벤트가 본질이므로
> `realtime_gps` 수신 시점에 서버가 직접 안내를 평가하고 `_send_nav_guidance()`
> (`server/api/ws_router.py`)로 TTS 합성·전송하도록 분리했다. 응답 형식은 §6.1 guide와
> 동일하다(`event_id`는 `nav-` 접두, `source`는 nav_filter 이벤트 타입). 중복 발화는
> nav_filter의 announced_cache/silence_interval이 탐지 경로와 공용으로 차단하며, 조회는
> 수신 루프에서 동기로 수행(중복 판정 원자성)하고 합성·전송만 백그라운드 태스크로
> 분리한다.

---

### 6.6 nav_route (서버 → 단말, 지도 경로 표시, 2026-07-11 신설)

목적지 설정으로 보행 경로가 수립되거나 해제될 때, 서버가 경로 좌표 목록을 단말 하단 T맵 지도 패널(`client/src/components/NavMapPanel.tsx`, 운영자/데모용)에 전달합니다.

```json
{
  "type": "nav_route",
  "waypoints": [
    { "lat": 37.5665, "lon": 126.9780 },
    { "lat": 37.5670, "lon": 126.9791 }
  ],
  "app_key": "TMAP JS API appKey",
  "ts": 1720574000000
}
```

| 필드 | 설명 |
| :--- | :--- |
| `waypoints` | 경로 폴리라인용 좌표 목록. **빈 배열이면 경로 해제**(지도 패널의 폴리라인 제거). 좌표 외 상세 정보(설명 문구 등)는 전송하지 않는다 |
| `app_key` | TMap JS API appKey. 클라이언트 하드코딩 대신 서버 환경변수 `TMAP_APP_KEY`를 재사용해 저장소에 키가 남지 않도록 한다(앱 런타임에는 노출되므로 TMap 콘솔에서 키 사용 제한 권장) |

전송 시점은 3곳이다.

| 시점 | 발생 위치 | 비고 |
| :--- | :--- | :--- |
| 경로 수립 성공 | `stt_to_llm_bridge.py` `navigation-setup-success` → `ws_router._process_stt_audio` | `nav_waypoints` 좌표 목록 포함 |
| 네비게이션 종료 | `navigation-setup-shutdown` | `waypoints: []`로 경로 해제 |
| WS 재접속(인증 직후) | `ws_router.ws_detect` | 서버 세션이 NAVIGATING이고 웨이포인트가 살아 있으면 재전송. 앱 재시작으로 단말 메모리의 경로가 사라져도 지도를 복원한다(실기기 확인 결함 수정) |

클라이언트는 `nav_route`를 `lastMessage` 경유가 아닌 **전용 상태(`navRoute`)** 로 보존한다(고빈도 ack/탐지 메시지의 React 배칭에 저빈도 이벤트가 덮여 유실되는 문제 - guide 오디오와 동일한 이유). 지도 패널은 토글 켜짐일 때만 WebView를 마운트하고, 현재 위치 마커 갱신은 2초 스로틀을 적용한다.

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

운영자 모니터링 콘솔은 별도 SSE 스트리밍 채널을 사용합니다. **2026-07-11 계약 고정**(dev 개선 계획서 §5): 실발행 이벤트와 예약(확장) 이벤트를 분리하고, payload 필드를 콘솔 파서(`console/src/api/useMonitorStream.ts`) 기준으로 고정합니다.

### 8.1 전송 규격

| 항목 | 값 |
| :--- | :--- |
| 엔드포인트 | `GET /api/v1/monitor/stream` |
| 인증 | 관리자 JWT 필수 (`Depends(get_current_admin)`, `server/api/monitor.py`) |
| 서버 소비원 | Redis Stream `mcp:metrics` (`server/mcp/manager.py` MCPManager가 xread 후 리스너 큐로 브로드캐스트, `event_type` 누락 시 `system_status`로 폴백) |
| 메시지 형식 | `data: {"event_type": "...", "payload": {...}, "ts": ...}\n\n` |

### 8.2 실발행 이벤트 (서버 코드가 직접 생성)

| event_type | payload | 주기 |
| :--- | :--- | :--- |
| `connection_established` | `{status: "ok"}` | 연결 직후 1회 |
| `ping` | 없음 | 큐 1초 타임아웃마다 (keep-alive) |

### 8.3 브리지 이벤트 계약 (Redis `mcp:metrics` 경유, 예약)

> **중요 (2026-07-11 실측)**: 현재 저장소에는 `mcp:metrics` 스트림에 실데이터를
> 발행(xadd)하는 producer가 **없습니다**(스트림 생성용 init dummy 제외). 탐지
> 파이프라인의 실발행 스트림은 `risk.events`이며 `mcp:metrics`와 연결되어 있지
> 않습니다. 따라서 아래 이벤트는 **콘솔이 소비 준비를 마친 예약 계약**이고,
> producer 구현(`risk.events`→`mcp:metrics` 브리지 또는 직접 발행)이 후속
> 과제입니다(dev 개선 계획서 §5 "SSE 계약 정리"). producer 구현 시 반드시 아래
> 필드명을 그대로 사용해야 콘솔 수정 없이 표시됩니다.

| event_type | payload 필드 (콘솔 파서 기준) | 콘솔 처리 |
| :--- | :--- | :--- |
| `system_metrics` / `gpu_status` / `system_status` / `system_error` | `gpu_usage_pct:number`, `memory_used_mb:number`, `current_provider:string`, `network_rtt_ms:number`, `queue_depth:number`, `dropped_frames:number`, `error_message:string` (전부 선택) | 시스템 상태 덮어쓰기 |
| `risk_event` | `event_id:string`, `risk_level:"high"\|"mid"\|"low"`, `class_name:string`, `confidence:number`, `direction:string`, `guidance_text:string` | 최근 80건 누적 로그 |
| `session_status` | `device_id:string`, `platform:string`, `status:"connected"\|"disconnected"`, `rtt_ms:number` | device_id 기준 upsert |
| `detection_event` | `event_id`, `device_id`, `stream:"reflex"\|"cognitive"`, `class_name`, `confidence`, `inference_ms` | 최근 80건 누적 피드 |
| `llm_status` / `rag_result` / `tts_status` / `stt_status` | `llm_provider`, `rag_query`, `rag_score`, `tts_engine`, `stt_status`, `last_guidance`/`guidance_text`, `inference_ms`, `reflex_bypass`, `surface` | AI 파이프라인 상태 갱신 |

### 8.4 데모 데이터 분리

콘솔의 데모 데이터는 SSE로 수신되는 것이 아니라, **개발 빌드에서만**(`import.meta.env.DEV && VITE_ENABLE_DEMO_DATA === "true"`) 콘솔 로컬에서 주입됩니다(`console/src/App.tsx`). 운영 빌드에서는 원천 차단되므로 §8.2~8.3의 실이벤트와 혼동하지 않습니다. 단, 사후 이력 로그(§8.5)는 실조회 결과가 있으면 데모 데이터 대신 실데이터를 우선 표시합니다.

### 8.5 사후 이력 조회 REST (2026-07-12 신설)

콘솔의 Detection Guidance Log 테이블은 SSE가 아니라 REST 폴링(기본 30초, `console/src/api/useDetectionLogs.ts`)으로 `detection_guidance_logs`를 조회합니다. 오탐 여부 판별과 안내 발화 당시 상황 확인을 위해 **이벤트 발생 시점 프레임 이미지**를 함께 제공합니다.

| 항목 | 값 |
| :--- | :--- |
| 로그 목록 | `GET /api/v1/admin/detection-logs?limit=50&offset=0` (limit 1~200) |
| 프레임 이미지 | `GET /api/v1/admin/event-frames/{event_id}` (JPEG 반환) |
| 인증 | 관리자 JWT (`Depends(get_current_admin)`) — 목록은 `Authorization` 헤더, 이미지는 `<img>` 태그 제약상 `?token=` 쿼리 허용(SSE와 동일 우회) |
| 라우터 | `server/api/detection_log_router.py` |

**로그 응답 필드**: `log_id`, `event_id`, `user_id`, `device_id`, `detected_at`, `stream_type`, `detected_objects_json`, `tts_text`, `frame_path`, `created_at`

**프레임 이미지 저장 계약** (`server/services/event_frame_store.py`):

| 항목 | 값 |
| :--- | :--- |
| 저장 트리거 | 반사 알림/인지 가이드가 **실제 전송 성사**되어 DB 로그가 적재되는 이벤트만 (전 프레임 아님) |
| 저장 위치 | `data/event_frames/YYYYMMDD/{event_id}.jpg`, DB에는 상대 경로(`frame_path`)만 기록 |
| 실시간 경로 영향 | 없음 — JPEG 인코딩·파일 쓰기는 백그라운드 로그 태스크 안에서 `asyncio.to_thread`로 수행 (반사 <300ms 목표 무영향) |
| bbox 표시 | 이미지에 굽지 않음 — `detected_objects_json`의 bbox(좌상단 x,y + w,h, 프레임 픽셀 좌표)를 콘솔이 오버레이 렌더링. 원본 보존으로 임계값/모델 교체 재검증 가능 |
| 보존 정책 | `EVENT_FRAME_RETENTION_DAYS`(기본 7일) 초과 날짜 폴더를 서버 기동 시 삭제. 보행 중 촬영 이미지는 행인 등 개인정보 포함 가능성으로 기간 한정 보존 |
| 실패 처리 | 저장 실패 시 `frame_path=NULL`로 로그는 적재. STT 이벤트 등 프레임 없는 로그도 NULL |
| 경로 방어 | event_id 화이트리스트(`[A-Za-z0-9._-]{1,64}`) + DB 등록 경로만 서빙 + 저장소 밖 경로 해석 차단 이중 검증 |

> 인지 로그의 `detected_objects_json`에는 2026-07-12부터 bbox 좌표가 포함됩니다(콘솔 오버레이용). LLM 오케스트레이터 입력에는 기존대로 bbox를 넣지 않습니다(프롬프트 오염 방지).

### 8.6 회원(시각장애인) 관리 REST (2026-07-12 신설)

콘솔의 "회원 관리" 화면(`console/src/pages/MembersPage.tsx`)이 사용합니다. `app_users`/`user_devices`를 다루며, 기존에 인증 없이 열려 있던 `POST /api/v1/users/register`(어디서도 호출되지 않는 죽은 엔드포인트)와 별개로 관리자 인증이 필요한 신규 API입니다.

| 항목 | 값 |
| :--- | :--- |
| 회원 목록 | `GET /api/v1/admin/members?limit=20&offset=0` (limit 1~100) |
| 회원 등록/전환 | `POST /api/v1/admin/members` |
| 인증 | 관리자 JWT (`Depends(get_current_admin)`), 다른 admin API와 동일 수준(역할별 세분화 권한 체크는 없음) |
| 라우터 | `server/api/admin_member_router.py` |

**목록 응답 필드**: `user_id`, `name`, `phone`, `disability_severity`, `birth_date`, `guardian_phone`, `address`, `status`, `devices`(`device_id`/`device_uuid`/`platform`/`is_active` 배열), `is_anonymous`(phone이 `anon:` 접두사면 true). `X-Total-Count` 응답 헤더로 전체 건수를 함께 내려준다(detection-logs와 동일 패턴).

**등록 요청 필드**: `device_uuid`, `name`, `phone`, `disability_severity`(필수) + `birth_date`, `guardian_phone`, `address`(선택, 2026-07-12 추가 - 익명 자동등록 레코드는 채우지 않으므로 NULL 허용), platform 생략 시 unknown.

**등록/전환 분기 로직** (`UserService.register_or_convert_member`):

| device_uuid 상태 | 동작 |
| :--- | :--- |
| 이미 등록됨(주로 익명 자동등록) | 소유 회원의 `name`/`phone`/`disability_severity`를 요청 값으로 UPDATE(전환). 신규 행 생성 안 함 |
| 미등록 | 같은 phone의 기존 회원이 있으면 그 회원에 기기만 추가, 없으면 회원+기기 신규 생성 |
| phone이 다른 회원 소유 | `409 Conflict` |

> "익명 자동등록"은 `server/services/device_registry_service.py`가 WS 최초 접속 시 `detection_guidance_logs.user_id`/`device_id` FK를 채우기 위해 만드는 `phone="anon:{device_uuid}"` 형태의 임시 계정입니다(2026-07-12 도입). 회원 관리 화면은 이 임시 계정을 실명으로 전환하는 용도로 설계되었습니다.

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
| v0.4.4 | 2026-07-10 | heartbeat 타임아웃 유예 5→15초 상향, 서버측 ack/heartbeat 응답 레이스 컨디션 수정(WS 세션 조기 종료 방지) |
| v0.4.5 | 2026-07-10 | server_detection(6.4) 신설, dg2 브랜치 병합 반영 |
| v0.4.6 | 2026-07-10 | realtime_gps(6.5) 신설, 구현 상태를 1~7단계 전체 완료로 갱신 |
| **v0.4.7** | **2026-07-10** | **stt_audio(6.3) 응답 전송을 audio_mp3_b64→binary transport로 통일(§6.1 규격과 일치), 명령 어휘 표(길댕아 2단계 웨이크워드·질문 모드·POI 실거리 검색) 추가, device_id 세션 불일치 결함(목적지는 설정돼도 길안내 음성이 안 나오던 원인) 수정 반영** |
| **v0.4.8** | **2026-07-11** | **§6.3 자기-에코 감지(TTS 안내문 재녹음 무시, 서버+클라이언트 이중 방어)·인텐트 체크 순서 변경(nav/question > wake 재호출) 비고 추가, §6.4 폴백 모드 온디바이스 BBox 표시 비고 추가, §2.4 SessionManager WebSocketState 가드(WS 종료 후 송신 실패 스팸 방지) 비고 추가** |
| **v0.4.9** | **2026-07-11** | **STT 원본·전사문 비보존, iOS PCM·Android AAC 플랫폼별 캡처 검증, SessionManager 송신 성공 boolean 및 반사 경보 억제 조건 정합화** |
| **v0.4.10** | **2026-07-11** | **nav_route(6.6) 신설(경로 좌표 전송·해제·재접속 복원, TMap appKey 서버 환경변수 전달), §6.5 realtime_gps 수신 시점 길안내 직접 평가 비고 추가(카메라 무탐지 시 무음 결함 수정), §6.3 STT 기본 모델 `faster-whisper-small` 전환·프리로드 반영** |
| **v0.4.11** | **2026-07-11** | **§6.4 폴백 모드 비고 갱신 - 클라이언트 재연결 정책 변경(무한 지수 백오프, 폴백 전환/복구 음성 고지, 폴백 상태 welcome 수신 시 해제) 반영** |
| **v0.4.12** | **2026-07-11** | **§8 SSE 계약 고정 - 실발행(8.2)/예약 브리지(8.3) 이벤트 분리, payload 필드를 콘솔 파서 기준으로 고정, `mcp:metrics` producer 부재 사실 명시(기존 "risk.events 실시간 뷰" 오기 정정), 데모 데이터 분리(8.4). §1 공통 필드 event_id 형식 구조화 반영** |
| **v0.4.13** | **2026-07-12** | **§8.5 사후 이력 조회 REST 신설 - `GET /api/v1/admin/detection-logs` 목록, `GET /api/v1/admin/event-frames/{event_id}` 프레임 JPEG 서빙, 이벤트 프레임 저장 계약(frame_path 컬럼, data/event_frames/ 날짜 폴더, 보존 기본 7일, 백그라운드 저장으로 반사 경로 무영향), 인지 로그 detected_objects_json에 bbox 좌표 포함(콘솔 오탐 검증 오버레이용)** |
