# Minchodan API 명세서

> **작성일**: 2026-06-24
> **버전**: v0.4.27 (2026-07-17 §6.8 distance_probe_sample 신설: LiDAR 실거리 검증 캡처, 검증 전용 스코프로 반사/인지 경로 판단에는 미관여 + 이전 v0.4.26: §8.5 Log 응답에 STT 원본 음성 저장 메타데이터 추가, 이벤트 프레임/사용자 음성 파일 중앙 저장 API 연동 계약 반영 + 이전 v0.4.25: §6.7 dial_action 자동 연결 PhoneDialBridge)
> **설계 기준**: `docs/design/minchodan_design_note.md` 1·2·3·7단계 인터페이스
> **구현 상태**: 1~7단계 전체 구현 완료. `/ws/detect` 핸드셰이크(hello/welcome/auth_ok/heartbeat), detection 페이로드, ack 응답, reflex_alert(사전합성 클립 선점), guide(실시간 TTS WAV), server_detection, realtime_gps, nav_route, distance_probe_sample(LiDAR 검증 전용), network_probe 정합 확인.
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
| `type` | 메시지 타입 (hello, welcome, auth_ok, detection, server_detection, ack, reflex_alert, guide, status, stt_audio, nav_route, realtime_gps, distance_probe_sample, dial_action, heartbeat, heartbeat_ack, network_probe, network_probe_ack, error. 부가: guidance_log_event, latency_event, contact_save, deviation_alert, guidance_audio, route_success, route_error, image_url - 상세는 각 섹션 참조) |
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

### 2.5 network_probe

Tailscale, ngrok, LAN 등 네트워크 경로별 순수 WebSocket RTT를 비교하기 위한 계측 메시지입니다. 카메라 프레임 디코딩, YOLO 추론, RAG, TTS를 거치지 않고 `/ws/detect` 메인 루프에서 즉시 echo 응답합니다.

| 방향 | 메시지 |
| :--- | :--- |
| 단말/스크립트 → 서버 | `{"type":"network_probe","probe_id":"ios-...","client_label":"ios-app","client_sent_ts":1720000000000,"payload":"xxx"}` |
| 서버 → 단말/스크립트 | `{"type":"network_probe_ack","probe_id":"ios-...","client_sent_ts":1720000000000,"client_label":"ios-app","payload_bytes":256,"server_received_ts":1720000000001,"server_sent_ts":1720000000001}` |

| 필드 | 타입 | 설명 |
| :--- | :--- | :--- |
| `probe_id` | string | 클라이언트가 생성한 probe 식별자. 응답 매칭에 사용 |
| `client_label` | string | `ios-app`, `ngrok`, `tailscale` 등 측정 라벨 |
| `client_sent_ts` | number | 클라이언트 송신 시각(epoch ms). 서버는 원문을 그대로 돌려줌 |
| `payload` | string | 네트워크 페이로드 크기 고정용 문자열. 서버는 저장하지 않음 |
| `payload_bytes` | number | 서버가 계산한 UTF-8 페이로드 바이트 수 |
| `server_received_ts` | number | 서버가 응답을 만들 때 기록한 수신 근사 시각(epoch ms) |
| `server_sent_ts` | number | 서버 응답 송신 직전 시각(epoch ms) |

> 실제 개선율 계산은 클라이언트 기준 왕복 시간으로 산정합니다. 서버 시각은 참고용이며 단말과 서버의 시계가 동기화되어 있지 않아 단방향 지연 계산에는 사용하지 않습니다.

### 2.6 error (서버 → 단말)

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
    "transport": "binary",
    "is_outdoor": true
  }
}
```

위 텍스트 메시지 직후, 별도의 WS **바이너리 프레임**으로 raw JPEG 바이트(640x640, JPEG 50% 압축)를 전송한다(JSON 필드 아님, base64 인코딩 없음).

| 필드 | 설명 |
| :--- | :--- |
| `payload.stream` | `reflex` (8~10fps) 또는 `cognitive` (1~2fps) |
| `payload.frame_id` | 프레임 일련 번호 |
| `payload.transport` | `"binary"` 고정 - 서버가 다음 바이너리 프레임을 이 메타와 짝지어야 함을 표시 |
| `payload.is_outdoor` | **선택**. 온디바이스 씬 분류(iOS: `VNClassifyImageRequest`, Android: ML Kit Image Labeling) + 히스테리시스 결과. `true`=실외, `false`=실내, 생략/`null`=미판정(구버전). 서버는 `false`일 때 보도 이탈 판정과 mid/low `risk.events`(인지 TTS) 발행을 억제한다 (`indoor_fp_mitigation_design.md` §4.7~§4.10) |

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
    "thumbnail_jpeg_b64": "/9j/4AAQ...",
    "is_outdoor": true
  }
}
```

| 필드 | 설명 |
| :--- | :--- |
| `payload.thumbnail_jpeg_b64` | **640x640 JPEG 압축 base64 프레임** (expo-image-manipulator 50% compress). `payload.transport`가 없으면 이 필드가 필수 |
| `payload.is_outdoor` | §3.1과 동일 (선택, 실내/실외 씬 신호) |

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
  "ts": 1719216000000,
  "track_id": 101,
  "class_name": "car",
  "hit_count": 5,
  "distance_band": "medium"
}
```

| 필드 | 설명 |
| :--- | :--- |
| `alert_id` | 알림 식별자(중복 억제 키). **2026-07-09 정정**: `reflex_gate.py`는 클래스명을 포함한 동적 값(`high_{class_name}_{direction}`, 예: `high_car_front`)을 생성한다 — 클립 선택에는 쓰이지 않고 60초 억제 키로만 쓰인다. **2026-07-17 P0-1 정정**: 억제 키는 `high_obstacle:{track_id}:{distance_band}` 조합으로 분리되어 새 객체/거리 악화 시 재발화 |
| `direction` | 방향 (`front`, `front-left`, `front-right`) |
| `risk_level` | `high` (반사 경로 전용) |
| `clip` | 단말 번들 사전합성 클립 경로(`client/assets/sounds/reflex_clips/`, basename 매칭). **2026-07-09 정정**: 클래스와 무관하게 방향/유형 기준으로 고정되며, 확장자는 `.wav`(인코더 제약으로 mp3 대신 채택) |
| `haptic` | 햅틱 동시 출력 여부 |
| `panning` | 스테레오 사운드 좌우 지향 밸런스 값 (-1.0 ~ 1.0). 클라이언트는 5단계 버킷(`-1.0/-0.5/0.0/0.5/1.0`)으로 반올림해 재생한다 |
| `distance` | 역산된 장애물 거리 (0.4m ~ 1.5m) |
| `beep_interval_ms` | 비프음 주기 (ms, 0은 연속 경고음) |
| `haptic_pattern` | 진동 패턴 (`short` \| `double` \| `continuous` \| `light`) |
| `track_id` | ByteTrack 객체 트랙 식별자 (로깅 및 모니터링 추적용, null 가능) |
| `class_name` | 탐지된 장애물의 클래스명 (null 가능) |
| `hit_count` | 해당 트랙 객체의 연속 누적 프레임 탐지 횟수 (null 가능) |
| `distance_band` | **2026-07-17 신규 (P0-1).** 억제 재무장 정책용 거리 밴드 (`near` \| `medium` \| `far`). near(<=0.6m)는 TTL 억제 제외 500ms 스로틀만, non-near는 동일키 5s TTL + device 1.5s 쿨다운 + 밴드 악화 재발화 |

선점 규칙: 반사 음성은 인지 음성을 중단시키고 재생합니다. **2026-07-17 P0-1 정정**: 중복 억제는 `setex(suppress:{device_id}:high_obstacle:{track_id}:{distance_band}, REFLEX_SUPPRESS_TTL_S=5)`로 처리하며, 동일 키 TTL(5s) + device 단위 최소 쿨다운(1.5s) + 거리 밴드 악화 시 재발화를 적용합니다.

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
  "guidance_text": "전동 킥보드 주의하세요",
  "clock_direction": "10시",
  "distance_class": "near",
  "object_ko": "전동 킥보드",
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
| `guidance_text` | L2/L3 생성 **음성 합성용** 텍스트 (한국어 1문장, 20자 내, 객체+행동 중심). 방향·거리는 구조화 필드로 분리(2026-07-16 Phase 2) |
| `clock_direction` | 구조화 시계 방향 (예: `"10시"`, `"12시"`). `estimate_clock_direction()` 산출값. 음성 텍스트와 분리 |
| `distance_class` | 구조화 거리 등급 (`near` / `medium` / `far`). `estimate_distance()` 산출값. **반사 `reflex_alert`의 미터 단위 `distance`와 별개** |
| `object_ko` | 구조화 한국어 주 탐지 객체명 (`CLASS_TEXT` SSoT). 패스트 레인 캐시 키에 사용 |
| `audio_codec` | 오디오 코덱 (현재 `wav` 고정) |
| `duration_ms` | 합성된 오디오 재생 길이(ms). 서버가 다음 guide 전송까지의 쿨다운을 이 값 기반으로 동적 산정(`server/detection/consumer.py`)하는 데 사용, 클라이언트는 참고용 |
| `transport` | `"binary"`(이 메시지 직후 오디오 바이너리 프레임이 이어짐) 또는 `"none"`(서버 TTS 합성 실패, 클라이언트는 `guidance_text`로 단말 내장 TTS 폴백) |
| `sources` | RAG 근거 인용 (선택) |
| `source` | 발화 출처 식별자 (선택). STT 대기 안내는 `"stt-wait-notice"`, 내비게이션은 `"nav-*"`, STT 브릿지는 `bridge_source` 값과 대응. 클라이언트는 `event_id`/`source`로 STT 상호작용 중 뮤트·에코 방어에 활용 |

> **비고 (2026-07-16) - STT 대기 안내**: 경로 검색(TMAP POI)·convenience RAG·LLM 자유 대화 등 Whisper 전사 **이후** 후속 처리가 길어질 때, 서버(`ws_router._send_stt_wait_notice`)가 본 절 `guide` 형식으로 `guidance_text: "잠시만 기다려주세요!"`를 **최대 1회** 선행 전송한다. `event_id`는 `stt-wait-{device_id}-{ts}` 접두, `source`는 `"stt-wait-notice"`. 전사 전에도 `NavigationManager`가 목적지 대기(`WAITING_FOR_DESTINATION`) 또는 질문 답변 대기(`awaiting_free_question`) 상태이면 동일 안내를 보낸다(`stt_to_llm_bridge.should_play_stt_wait_notice`). 본 응답은 STT 에코 감지 메모리(`_record_guidance`)에 넣지 않는다.

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
| 자유 질의(대기 상태에서) | "가까운/근처/주변" + 장소 유형(지하철역·편의점·화장실 등)이 감지되면 TMAP 실거리 검색(`helper_search_nearest_poi`, Haversine 거리순)으로 사실 기반 답변. 그 외는 LLM 자유 대화 / 생활지원 convenience RAG | 위치 사실을 LLM에 맡기지 않고 실제 API 조회 결과로만 답해 환각을 방지. 생활지원 질의는 jh `convenience_rag` 분기 |

> **비고 (2026-07-14)**: th 음성 편의기능 중 SMS 읽어주기와 `contact_save` WS 계약은 제거했다.
> **2026-07-16 복원**: `dial_action` 전화 연결 계약을 STT+convenience RAG/보호자 DB/긴급번호 경로로 재도입했다(§6.7).

> **비고 (2026-07-16) - convenience 코퍼스 음독 정규화**: `data/convenience_guidelines.json`의 STT/TTS 대상 문자열(전화번호·시간·날짜·주소 건물번호 등)은 아라비아 숫자 대신 **한글 음절 숫자**(`공일이…`)로 정규화한다. 시스템 키(`organization_id`)·좌표(`latitude`/`longitude`)는 검색/연동 호환을 위해 유지한다. JSON만 갱신해도 Chroma 임베딩은 자동 반영되지 않으므로 배포 시 `python scripts/build_convenience_db.py`로 `data/chroma_db/convenience_guidelines` 컬렉션을 **재빌드**해야 한다(기본 임베딩: Ollama `nomic-embed-text`).

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

| 발화(예시) | 동작 | 비고 |
| :--- | :--- | :--- |
| `119 연결해줘` / `보호자에게 전화해줘` | `guide` 확인 멘트 + TTS 후 `dial_action`으로 전화 앱 연결 | §6.7 |
| `서울시 장애인 생활지원센터에 전화 걸어줘` | convenience RAG 코퍼스에서 기관명 매칭 후 동일 | 한글 숫자 표기는 서버에서 `tel:`용 숫자로 정규화 |

### 6.7 dial_action (서버 → 단말, 2026-07-16 복원)

STT 경로에서 전화 연결 의도가 감지되면, §6.1 `guide` 확인 멘트·TTS 직후 별도 메시지로 **전화를 자동 연결**한다. 인지/STT 경로 전용이며 반사 경로에는 사용하지 않는다.

```json
{
  "type": "dial_action",
  "event_id": "dial-dev-001-1719216000000",
  "contact_name": "서울시 장애인 생활지원센터",
  "phone_number": "0222223690",
  "source": "stt-dial-convenience",
  "delay_ms": 2000,
  "ts": 1719216000000
}
```

| 필드 | 설명 |
| :--- | :--- |
| `contact_name` | 연결 대상 표시명(기관·보호자·긴급번호 라벨) |
| `phone_number` | `tel:` URL용 숫자만(`0222223690`, `119` 등). convenience 코퍼스 한글 숫자는 서버가 정규화 |
| `source` | `stt-dial-emergency` / `stt-dial-guardian-db` / `stt-dial-convenience` / `stt-dial-not-found`(미발행) |
| `delay_ms` | 확인 TTS 재생 후 전화 앱을 여는 지연(ms). 클라이언트 기본 1500 |

**해석 우선순위** (`server/stt/dial_resolver.py`):

| 순서 | 조건 | 번호 출처 |
| :--- | :--- | :--- |
| 1 | 119/112/1339 긴급 연결 | 고정 단축번호 |
| 2 | `보호자` + 전화 의도 | `app_users.guardian_phone`(device 등록 회원) |
| 3 | 기관·인물·긴급연락망 이름 매칭 | `data/convenience_guidelines.json` |

클라이언트(`phoneDialBridge.ts` + `useWebSocket.ts`)는 확인 TTS 후 `delay_ms`만큼 대기한 뒤 네이티브 `PhoneDialBridge`로 연결한다.

| 플랫폼 | 동작 | 비고 |
| :--- | :--- | :--- |
| **Android** | `Intent.ACTION_CALL`로 **즉시 발신** | `CALL_PHONE` 런타임 권한 필요. 거부 시 `tel:` 폴백 |
| **iOS** | Siri App Intent + Shortcuts(`MinchodanDial`) | `tel:` 전화 앱 열기 미사용. 단축어 1회 설정 필요(아래 참조) |

연결 직전 VoiceOver 안내(`AccessibilityInfo.announceForAccessibility`)와 햅틱(`double`)을 재생한다.

**iOS Siri/Shortcuts 1회 설정** (단축어 앱):

| 단계 | 동작 |
| :--- | :--- |
| 1 | 단축어 이름 `MinchodanDial` 생성 |
| 2 | 동작: **입력 받기**(단축어 입력) → **전화 걸기**(입력값) |
| 3 | 전화 걸기 동작에서 **실행 시 보여주기** 끔 |

앱 내 STT(`119 연결해줘`) 또는 Siri(`길댕아 119 연결해`) 모두 위 경로를 사용한다.

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

`lat`/`lon` 중 하나라도 누락되면 서버는 조용히 무시한다(에러 응답 없음). TMAP 보행자 경로 안내(`server/navigation/server.py`)와 결합되어 실시간 TTS로 안내 문장이 발화된다.

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

### 6.8 distance_probe_sample (단말 → 서버, LiDAR 실거리 검증 전용, 2026-07-17 신설)

**검증 전용 스코프**: 거리측정(depthMode) 프로토타입(`client/ios/DepthProbeBridge.swift`)에서 얻은 LiDAR 실측값을, 서버가 동일 bbox에 재계산한 휴리스틱 거리(near/medium/far)와 나란히 DB(`lidar_distance_validation_samples`)에 남겨 정확도를 사후 검증하기 위한 메시지다. 반사/인지 경로의 실시간 판단에는 관여하지 않는다.

LiDAR 심도 카메라는 vision-camera와 별도의 `AVCaptureSession`을 쓰기 때문에 실시간 탐지와 동시 실행이 불가능하다(카메라 세션 점유 충돌). 따라서 다음 순서로 동작한다.

1. 클라이언트가 depthMode의 `depthResult.previewUri`(depth와 동기화된 정지 프레임)를 기존 §3.2 `detection`(base64) 메시지로 전송하고, `payload.probe_source: "lidar_validation"`로 표시한다.
2. 서버가 정상적으로 YOLO 추론 후 §6.4 `server_detection`으로 bbox 목록을 응답한다(기존 로직 그대로, 신규 필드 없음).
3. 클라이언트는 받은 event_id가 자신이 보낸 검증 캡처와 일치하면, 같은 depth 세션에서 해당 bbox들의 LiDAR 실측을 네이티브 `probeBoxes()`로 샘플링해 아래 메시지로 보고한다.

```json
{
  "type": "distance_probe_sample",
  "payload": {
    "event_id": "probe-dev-001-1721200000000",
    "samples": [
      {
        "class_name": "bollard",
        "confidence": 0.91,
        "bbox": { "x": 120.0, "y": 300.0, "w": 40.0, "h": 80.0 },
        "lidar_meters": 1.42,
        "lidar_sample_count": 31,
        "lidar_accuracy": "absolute",
        "lidar_quality": "high",
        "lidar_calibrated": true
      }
    ]
  }
}
```

| 필드 | 설명 |
| :--- | :--- |
| `event_id` | §3.2에서 보낸 검증 캡처와 동일한 event_id (상관관계 매칭 키) |
| `samples[].bbox` | `server_detection`으로 받은 bbox를 그대로 되돌려 보낸다 (640x640 모델 좌표계) |
| `samples[].lidar_meters` | LiDAR 실측 거리(m). 유효 depth 샘플이 없으면 `null` |
| `samples[].lidar_accuracy` | `absolute`(LiDAR 실측) 또는 `relative`(시차 기반) |

서버(`server/api/ws_router.py`의 `_handle_distance_probe_sample`)는 `estimate_distance()`(`server/detection/direction.py`)로 동일 bbox의 휴리스틱 라벨을 재계산해 LiDAR 실측과 함께 저장한다(휴리스틱 계산의 단일 소스는 서버 유지). 응답 메시지는 없다(fire-and-forget). 담당자는 `scripts/analyze_lidar_validation.py`로 집계를 확인한다.

> **비범위**: vision-camera 세션과 LiDAR 세션의 동시 실행(실시간 라이브 융합)은 포함하지 않는다. 별도의 네이티브 세션 재설계가 필요한 후속 과제로 남긴다.

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
| 인증 | 관리자 JWT 필수 (`Depends(get_current_admin)`, `server/api/monitor.py`). EventSource는 `Authorization` 헤더를 못 붙이므로 `?token=` 쿼리 허용 |
| 서버 소비원 | Redis Stream `mcp:metrics` (`server/mcp/manager.py` MCPManager가 xread 후 리스너 큐로 브로드캐스트, `event_type` 누락 시 `system_status`로 폴백). `session_status`/`detection_event`/`llm_status` 등은 in-process `broadcast_event`로도 전달 |
| 메시지 형식 | `data: {"event_type": "...", "payload": {...}, "timestamp": ...}\n\n` |
| 응답 헤더 | `Content-Type: text/event-stream`, `Cache-Control: no-cache, no-transform`, `Connection: keep-alive`, `X-Accel-Buffering: no` (Docker Desktop 등 중간 프록시가 SSE 청크를 버퍼링해 SystemMetrics 행이 비는 문제 방지, 2026-07-15) |
| keep-alive | 큐 1초 타임아웃 시 SSE 주석 라인(`: keepalive`) + `ping` 이벤트 |

### 8.2 실발행 이벤트 (서버 코드가 직접 생성)

| event_type | payload | 주기 |
| :--- | :--- | :--- |
| `connection_established` | `{status: "ok"}` | 연결 직후 1회 |
| `system_metrics` | §8.3과 동일 필드 | **연결 직후 1회 스냅샷**(GPUMonitorMCP 즉시 조회) + 이후 GPU 모니터 루프(약 2초)가 Redis `mcp:metrics`로 주기 발행 |
| `ping` | 없음 | 큐 1초 타임아웃마다 (keep-alive) |

### 8.3 브리지 이벤트 계약 (Redis `mcp:metrics` 경유, 실구현 완료)

> **중요 (2026-07-13 실구현)**: `mcp:metrics` 스트림에 실시간 메트릭 데이터를 발행(xadd)하는 `MCPManager.publish_metric()` 메서드를 신규 구현하여 메인 모듈들과의 실연동을 완료했습니다. 다중 프로세스(workers > 1) 환경에서도 Redis Streams를 매개로 유실 없이 실시간으로 전송되며, 프론트엔드 모니터 컴포넌트(`McpValidationMonitor.tsx`)에 정상 연동됩니다.

| event_type | payload 필드 (콘솔 파서 기준) | 콘솔 처리 |
| :--- | :--- | :--- |
| `system_metrics` / `gpu_status` / `system_status` / `system_error` | `gpu_usage_pct:number`, `memory_used_mb:number`, `current_provider:string`, `network_rtt_ms:number`, `queue_depth:number`, `dropped_frames:number`, `error_message:string` (전부 선택) | 시스템 상태 덮어쓰기 |
| `risk_event` | `event_id:string`, `risk_level:"high"\|"mid"\|"low"`, `class_name:string`, `confidence:number`, `direction:string`, `guidance_text:string` | 최근 80건 누적 로그 |
| `session_status` | `device_id:string`, `platform:string`, `status:"connected"\|"disconnected"`, `rtt_ms:number` | device_id 기준 upsert |
| `detection_event` | `event_id`, `device_id`, `stream:"reflex"\|"cognitive"`, `class_name`, `confidence`, `inference_ms` | 최근 80건 누적 피드 |
| `llm_status` / `rag_result` / `tts_status` / `stt_status` | `llm_provider`, `rag_query`, `rag_score`, `tts_engine`, `stt_status`, `last_guidance`/`guidance_text`, `inference_ms`, `reflex_bypass`, `surface` | AI 파이프라인 상태 갱신 |
| `audio_validation` | `alert_id:string`, `ttfb_ms:float`, `sample_rate:int`, `channels:int`, `duration_sec:float`, `is_valid:bool`, `errors:list` | McpValidationMonitor 오디오 메트릭 업데이트 |
| `cache_suppression` | `suppressed_keys:list[str]`, `ttl_seconds:int`, `details:list` | McpValidationMonitor 캐시 억제 키 메트릭 업데이트 |
| `accessibility_validation` | `alert_id:string`, `is_valid:bool`, `similarity_score:float`, `warnings:list`, `details:dict` | McpValidationMonitor 접근성 정합 스코어 업데이트 |
| `langsmith_trace` | `alert_id:string`, `from_node:string`, `to_node:string`, `latency_ms:float`, `enabled:bool` | McpValidationMonitor LangSmith 트랙 RTT 업데이트 |

> **발행 위치 보강 (2026-07-16)**: `risk_event`는 Redis `risk.events` 스트림이 아니라 `DetectionConsumer._broadcast_risk_event()`가 반사/인지 경보 전송 성사 직후 `MCPManager.broadcast_event("risk_event", …)`로 in-process 발행한다. `detection_event`·`llm_status` 등과 동일 경로이며, 콘솔 `RiskEventLog`가 SSE로 수신한다.

### 8.4 데모 데이터 분리

콘솔의 데모 데이터는 SSE로 수신되는 것이 아니라, **개발 빌드에서만**(`import.meta.env.DEV && VITE_ENABLE_DEMO_DATA === "true"`) 콘솔 로컬에서 주입됩니다(`console/src/App.tsx`). 운영 빌드에서는 원천 차단되므로 §8.2~8.3의 실이벤트와 혼동하지 않습니다. 단, 사후 이력 로그(§8.5)는 실조회 결과가 있으면 데모 데이터 대신 실데이터를 우선 표시합니다.

### 8.5 사후 이력 조회 REST (2026-07-12 신설)

콘솔의 Detection Guidance Log 테이블은 SSE가 아니라 REST 폴링(기본 30초, `console/src/api/useDetectionLogs.ts`)으로 `detection_guidance_logs`를 조회합니다. 오탐 여부 판별과 안내 발화 당시 상황 확인을 위해 **이벤트 발생 시점 프레임 이미지**를 함께 제공합니다. STT 경로는 사용자 원본 음성 파일 경로와 전사 문장을 같은 로그 행에 보관합니다.

**콘솔 페이지네이션 UX (2026-07-16)**: `DetectionGuidanceLogTable`·`MembersPage` 목록은 서버 `offset`/`limit` + `X-Total-Count` 기반 **서버 페이지네이션**을 사용한다. 기본 `pageSize`는 **10**. 하단 컨트롤은 이전/다음 화살표, 최대 10개 번호 버튼, `...` 페이지 점프 입력, 마지막 페이지 버튼으로 통일한다. `totalCount <= 11`이면 컨트롤을 비활성화한다. 스트림 필터(전체/반사/인지)는 **현재 페이지 rows**에만 클라이언트 필터를 적용하므로, 필터 적용 시 표시 행 수와 `totalCount`가 어긋날 수 있다.

| 항목 | 값 |
| :--- | :--- |
| 로그 목록 | `GET /api/v1/admin/detection-logs?limit=50&offset=0` (limit 1~200) |
| 프레임 이미지 | `GET /api/v1/admin/event-frames/{event_id}` (JPEG 반환) |
| 인증 | 관리자 JWT (`Depends(get_current_admin)`) — 목록은 `Authorization` 헤더, 이미지는 `<img>` 태그 제약상 `?token=` 쿼리 허용(SSE와 동일 우회) |
| 라우터 | `server/api/detection_log_router.py` |

**로그 응답 필드**: `log_id`, `event_id`, `user_id`, `device_id`, `detected_at`, `stream_type`, `detected_objects_json`, `tts_text`, `frame_path`, `false_positive`, `latency_json`, `pipeline_debug_json`, `created_at`, `event_source`, `stt_transcript_text`, `stt_audio_path`, `stt_audio_storage_status`, `stt_audio_format`, `stt_audio_size_bytes`, `stt_audio_duration_ms`, `stt_audio_sha256`, `stt_audio_error_code`, `stt_audio_consent_at`, `stt_audio_expires_at`, `writer_instance_id`

**pipeline_debug_json** (2026-07-16, 관리자 콘솔 전용): `server/services/pipeline_debug_builder.py`가 경로별 중간 텍스트를 직렬화한 JSON 객체. `path`는 `reflex`/`cognitive`/`stt`. MariaDB JSON 컬럼 특성상 REST 응답에서는 객체로 직렬화될 수 있다(콘솔은 string/object 모두 파싱).

| path | 주요 필드 | 설명 |
| :--- | :--- | :--- |
| 공통 | `generation_mode` | 응답 생성 경로 식별 (`reflex_prebaked_clip`, `fast_lane_template`, `langgraph_l2_l3`, `llm_answer`, `echo_skipped` 등) |
| `reflex` | `alert_id`, `clip`, `direction`, `class_name`, `distance`, `risk_level`, `detections_summary` | 반사 사전합성 클립·탐지 요약(최대 8건 bbox/confidence/direction) |
| `cognitive` | `rag_query`, `rag_context`, `clock_direction`, `distance_class`, `object_ko`, `used_fast_lane`, `fast_lane_cache_key`, `l1_risk_level`, `l3_verified`, `l2_drafts`, `detections_summary`, `surfaces_summary`, `llm_text`, `response_text` | 인지 LangGraph/패스트레인·RAG·L2 초안·노면 요약 |
| `stt` | `stt_transcript`, `bridge_source`, `generation_mode`, `response_text`, `rag_query`, `rag_results`, `llm_text`, `template_text`, `response_skipped`, `skip_reason` | STT 전사·브릿지 분기·RAG 미리보기(최대 5건)·에코 스킵 |

**프레임 이미지 저장 계약** (`server/services/event_frame_store.py`):

| 항목 | 값 |
| :--- | :--- |
| 저장 트리거 | 반사 알림/인지 가이드가 **실제 전송 성사**되어 DB 로그가 적재되는 이벤트만 (전 프레임 아님) |
| 저장 위치 | 기본은 `data/event_frames/YYYYMMDD/{event_id}.jpg`. `EVENT_FRAME_STORAGE_BACKEND=remote`이면 Raspberry Pi 중앙 저장 API에 업로드하고 DB에는 object key(`YYYYMMDD/{event_id}.jpg`)만 기록 |
| 실시간 경로 영향 | 없음 — 로컬 JPEG 인코딩·파일 쓰기는 백그라운드 로그 태스크 안에서 `asyncio.to_thread`로 수행. 원격 저장도 로그 태스크 내부에서 수행되어 반사 <300ms 목표를 막지 않음 |
| bbox 표시 | 이미지에 굽지 않음 — `detected_objects_json`의 bbox(좌상단 x,y + w,h, 프레임 픽셀 좌표)를 콘솔이 오버레이 렌더링. 원본 보존으로 임계값/모델 교체 재검증 가능 |
| 보존 정책 | `EVENT_FRAME_RETENTION_DAYS`(기본 7일) 초과 날짜 폴더를 서버 기동 시 삭제. 보행 중 촬영 이미지는 행인 등 개인정보 포함 가능성으로 기간 한정 보존 |
| 실패 처리 | 저장 실패 시 `frame_path=NULL`로 로그는 적재. STT 이벤트 등 프레임 없는 로그도 NULL |
| 경로 방어 | event_id 화이트리스트(`[A-Za-z0-9._-]{1,64}`) + DB 등록 경로만 서빙 + 저장소 밖 경로 해석 차단 이중 검증 |

> 인지 로그의 `detected_objects_json`에는 2026-07-12부터 bbox 좌표가 포함됩니다(콘솔 오버레이용). LLM 오케스트레이터 입력에는 기존대로 bbox를 넣지 않습니다(프롬프트 오염 방지).

**STT 원본 음성 저장 계약** (`server/api/ws_router.py`, `server/services/remote_storage_client.py`):

| 항목 | 값 |
| :--- | :--- |
| 저장 트리거 | `/ws/detect`의 `stt_audio` 처리에서 STT 전사·LLM 브리지·TTS 응답 생성이 완료된 이벤트 |
| 저장 대상 | 사용자가 말한 원본 오디오 bytes. LLM이 출력한 TTS WAV가 아니라 STT 입력 음성 |
| DB 연결 | `stt_audio_path`에 중앙 저장 API object key(`YYYYMMDD/{event_id}.{wav|m4a|ogg|mp3}`), `stt_transcript_text`에 STT 전사 문장, `stt_audio_storage_status`에 `available`/`upload_failed`/`not_saved` 등 상태 저장 |
| 비밀값 경계 | `IMAGE_SERVER_TOKEN`은 서버 `.env` 전용이며 단말 앱/콘솔 공개 변수로 전달하지 않음 |

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
| **v0.4.16** | **2026-07-13** | **§2.5 `network_probe`/`network_probe_ack` 신설 - ngrok/Tailscale/LAN 순수 WebSocket RTT 비교용 echo 메시지 및 iOS 앱 계측 경로 반영** |
| **v0.4.18** | **2026-07-14** | **§4.1 reflex_alert 발화 추적용 신규 필드(track_id/class_name/hit_count) 스펙 추가** |
| **v0.4.19** | **2026-07-14** | **§3.1/§3.2 detection `is_outdoor` 필드 추가(온디바이스 씬 분류). 서버는 실내(`false`)일 때 보도 이탈·인지 TTS(`risk.events`) 억제** |
| **v0.4.27** | **2026-07-17** | **§6.8 `distance_probe_sample` 신설 - LiDAR 실거리 검증 캡처(검증 전용, 반사/인지 경로 판단 미관여), `lidar_distance_validation_samples` DB 테이블 연동** |
| **v0.4.24** | **2026-07-16** | **§6.7 `dial_action` STT 전화 연결 복원(convenience RAG·보호자 DB·긴급번호), §6.3 발화 표 추가** |
| **v0.4.23** | **2026-07-16** | **§6.3 convenience_guidelines 한글 숫자 정규화·Chroma 재빌드(`build_convenience_db.py`) 절차 명시. §8.5 콘솔 서버 페이지네이션 UX(10건·번호창·점프) 보강** |
| **v0.4.22** | **2026-07-16** | **§6.1 `source` 필드·STT 대기 안내(`stt-wait-notice`) 계약 추가. §8.3 `risk_event` 발행 위치(`DetectionConsumer._broadcast_risk_event`) 명시. §8.5 `pipeline_debug_json` 확장 필드 표 보강** |
| **v0.4.21** | **2026-07-16** | **§8.5 `pipeline_debug_json`·`latency_json`·`false_positive` 로그 응답 필드 명세 보강(관리자 콘솔 STT/LLM/패스트레인 디버그)** |
| **v0.4.20** | **2026-07-15** | **§8 SSE: 버퍼 방지 응답 헤더, 연결 직후 `system_metrics` 스냅샷, keep-alive 주석 라인. 콘솔은 SSE 401 프로브·빈 카드 안내 문구 추가** |

### 4.3 latency_event (서버 → 콘솔, 2026-07-17 P2-2 강화)

파이프라인 스테이지별 지연(ms)을 콘솔에 실시간 푸시한다. `server_detection`과 동일 콘솔 WS 브로드캐스트 채널을 재사용한다.

```json
{
  "type": "latency_event",
  "event_id": "uuid",
  "stream_type": "reflex",
  "latency": {
    "decode_ms": 2.1,
    "inference_ms": 45.3,
    "queue_wait_ms": 12.4,
    "total_ms": 59.8
  },
  "latency_alert": false,
  "latency_threshold_ms": 300,
  "ts": 1719216000000
}
```

| 필드 | 설명 |
| :--- | :--- |
| `stream_type` | `reflex` \| `cognitive` |
| `latency` | 스테이지별 지연 (ms). 반사: `decode_ms`/`inference_ms`/`queue_wait_ms`/`total_ms`. 인지: 추가로 `rag_ms`/`llm_ms`/`tts_ms` |
| `latency_alert` | **2026-07-17 신규 (P2-2).** `total_ms`가 임계 초과 시 `true`. 반사 `REFLEX_LATENCY_ALERT_MS=300`, 인지 `COGNITIVE_LATENCY_ALERT_MS=3000` |
| `latency_threshold_ms` | **2026-07-17 신규 (P2-2).** 적용된 지연 임계(ms). 콘솔이 alert 기준 표시용 |
| `queue_wait_ms` | **2026-07-17 신규 (P0-2).** 큐 대기 시간(ms). `processed.ts` 기반 산출, ts=0이면 0 |
