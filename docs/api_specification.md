# Minchodan API 명세서

> **작성일**: 2026-06-24
> **버전**: v0.1.0
> **설계 기준**: `docs/minchodan_design_note.md` 1·2·7단계 인터페이스

---

## 1. 공통 규격

### 전송 프로토콜

| 항목       | 값                                        |
| ---------- | ----------------------------------------- |
| 프로토콜   | WebSocket (RFC 6455)                      |
| 엔드포인트 | `ws://{host}:{WS_PORT}/ws/detect`         |
| 인코딩     | JSON (텍스트 프레임) / base64 (이미지)    |
| 인증       | `device_token` (hello 핸드셰이크 시 검증) |
| 하트비트   | 5초 ping/pong                             |

### 공통 메시지 형식

모든 메시지는 JSON 객체이며 `type` 필드로 이벤트 종류를 구분합니다.

| 필드        | 설명                                                                                |
| ----------- | ----------------------------------------------------------------------------------- |
| `type`      | 메시지 타입 (hello, welcome, detection, ack, alert_reflex, guide, heartbeat, error) |
| `event_id`  | 이벤트 추적 식별자 (UUID)                                                           |
| `device_id` | 단말 식별자                                                                         |
| `ts`        | 타임스탬프 (epoch ms)                                                               |
| `payload`   | 타입별 페이로드                                                                     |

---

## 2. WebSocket 핸드셰이크 (1단계)

### 2.1 hello (단말 서버)

```json
{
  "type": "hello",
  "device_id": "android-xxxx",
  "token": "device_token_value"
}
```

| 필드        | 설명                      |
| ----------- | ------------------------- |
| `device_id` | 단말 고유 식별자          |
| `token`     | 사전 발급된 디바이스 토큰 |

### 2.2 welcome (서버 단말)

```json
{
  "type": "welcome",
  "session_id": "uuid-session",
  "server_time": 1719216000000
}
```

| 필드          | 설명                                |
| ------------- | ----------------------------------- |
| `session_id`  | 세션 식별자 (이후 이벤트 추적 기준) |
| `server_time` | 서버 시각 (epoch ms)                |

### 2.3 heartbeat

서버가 5초 간격으로 ping을 송신하고 단말은 pong으로 응답합니다. ping/pong은 WebSocket 제어 프레임 또는 JSON `{type:"heartbeat"}` 메시지를 사용합니다.

| 방향      | 메시지                                                  |
| --------- | ------------------------------------------------------- |
| 서버 단말 | WebSocket ping 프레임 또는 `{type:"heartbeat", ts}`     |
| 단말 서버 | WebSocket pong 프레임 또는 `{type:"heartbeat_ack", ts}` |

### 2.4 error (서버 단말)

```json
{
  "type": "error",
  "event_id": "uuid",
  "code": "auth_failed",
  "message": "디바이스 토큰 검증 실패"
}
```

| `code`         | 설명                    |
| -------------- | ----------------------- |
| `auth_failed`  | 디바이스 토큰 검증 실패 |
| `bad_request`  | 메시지 형식 오류        |
| `rate_limited` | 프레임 전송 과다        |
| `internal`     | 서버 내부 오류          |

---

## 3. 프레임 전송 (2단계)

### 3.1 detection (단말 서버)

```json
{
  "type": "detection",
  "payload": {
    "event_id": "uuid",
    "device_id": "android-xxxx",
    "ts": 1719216000000,
    "frame_id": 42,
    "stream": "reflex",
    "thumbnail_jpeg_b64": "/9j/4AAQ..."
  }
}
```

| 필드                         | 설명                                         |
| ---------------------------- | -------------------------------------------- |
| `payload.stream`             | `reflex` (8~10fps) 또는 `cognitive` (1~2fps) |
| `payload.frame_id`           | 프레임 일련 번호                             |
| `payload.thumbnail_jpeg_b64` | JPEG 압축 base64 프레임                      |

### 3.2 ack (서버 단말)

```json
{
  "type": "ack",
  "event_id": "uuid",
  "frame_id": 42,
  "decode_ms": 12
}
```

| 필드        | 설명                            |
| ----------- | ------------------------------- |
| `decode_ms` | 서버 수신·디코딩 소요 시간 (ms) |

---

## 4. 반사 경로 메시지 (3·7단계, 고우선)

반사 경로는 LLM/RAG/실시간 TTS를 경유하지 않으며, 사전합성 음성 클립을 즉시 재생합니다.

### 4.1 alert_reflex (서버 단말, 고우선)

```json
{
  "type": "alert_reflex",
  "event_id": "uuid",
  "alert_id": "high_front",
  "direction": "front",
  "risk_level": "high",
  "clip": "reflex_clips/high_front.mp3",
  "haptic": true,
  "ts": 1719216000000
}
```

| 필드         | 설명                                                                      |
| ------------ | ------------------------------------------------------------------------- |
| `alert_id`   | 사전합성 클립 식별자 (예: `high_front`, `high_left`, `surface_crosswalk`) |
| `direction`  | 방향 (`front`, `left`, `right`, `stop`)                                   |
| `risk_level` | `high` (반사 경로 전용)                                                   |
| `clip`       | 단말 번들 사전합성 클립 경로                                              |
| `haptic`     | 햅틱 동시 출력 여부                                                       |

선점 규칙: 반사 음성은 인지 음성을 중단시키고 재생합니다. 중복 억제는 서버 `setex(suppress:{alert_id}, 60)`로 처리합니다.

### 4.2 alert_id 사전 정의

| `alert_id`                | 방향  | 트리거                  |
| ------------------------- | ----- | ----------------------- |
| `high_front`              | front | 고위험 객체 근접 (전방) |
| `high_left`               | left  | 고위험 객체 근접 (좌측) |
| `high_right`              | right | 고위험 객체 근접 (우측) |
| `high_stop`               | stop  | 고위험 객체 근접 (정지) |
| `surface_crosswalk`       | front | 횡단보도 하단 검출      |
| `surface_manhole`         | front | 맨홀 하단 검출          |
| `surface_stairs`          | front | 계단 하단 검출          |
| `surface_grating`         | front | 그레이팅 하단 검출      |
| `surface_braille_damaged` | front | 점자블록 파손 하단 검출 |

---

## 5. 인지 경로 메시지 (6·7단계)

인지 경로는 Redis Streams(`risk.events`) LangGraph L1/L2/L3 + RAG 실시간 TTS 흐름을 거칩니다.

### 5.1 guide (서버 단말)

```json
{
  "type": "guide",
  "event_id": "uuid",
  "risk_level": "mid",
  "guidance_text": "전방 킥보드, 우측으로 한 발 물러서세요",
  "audio_mp3_b64": "SUQzBAAAA...",
  "sources": [{ "citation_number": 1, "label": "VEC_0", "role": "vector" }],
  "ts": 1719216000000
}
```

| 필드            | 설명                                                      |
| --------------- | --------------------------------------------------------- |
| `guidance_text` | L2/L3 생성 가이드 문장 (한국어 1문장, 20자 내, 방향 포함) |
| `audio_mp3_b64` | 실시간 TTS 합성 base64 MP3                                |
| `sources`       | RAG 근거 인용 (선택)                                      |

### 5.2 status (서버 단말, 진행 알림)

```json
{
  "type": "status",
  "event_id": "uuid",
  "stage": "l2_generating",
  "ts": 1719216000000
}
```

| `stage`            | 설명               |
| ------------------ | ------------------ |
| `detecting`        | 탐지 수행 중       |
| `rag_searching`    | RAG 검색 중        |
| `l1_classifying`   | L1 위험도 분류 중  |
| `l2_generating`    | L2 가이드 생성 중  |
| `l3_validating`    | L3 검증 중         |
| `tts_synthesizing` | 실시간 TTS 합성 중 |

---

## 6. 탐지 결과 상세 (3단계, 내부/콘솔용)

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

## 7. 운영자 콘솔 구독 (별도)

운영자 모니터링 콘솔은 별도 SSE 또는 WebSocket 구독 채널을 사용합니다.

| 채널           | 설명                          |
| -------------- | ----------------------------- |
| 탐지 피드      | 실시간 DetectionResult 스트림 |
| RiskEvent 로그 | Redis `risk.events` 스트림 뷰 |
| 세션 상태      | WS 세션 연결/해제 상태        |

---

## 8. 예외 처리 가드레일

| 단계 | 예외                                    | 처리                                  |
| ---- | --------------------------------------- | ------------------------------------- |
| 1    | `WebSocketDisconnect`                   | 소켓 close + 리소스 해제              |
| 2    | 카메라 권한 거부 (`NotAllowedError`)    | 단말에서 안내 후 종료                 |
| 2    | 소켓 유실                               | `clearInterval` 타이머 자원 즉시 해제 |
| 3    | 빈 버퍼/디코딩 실패 (`None`)            | 에러 없이 빈 리스트 반환              |
| 5    | DB 손상/경로 부재 (`FileNotFoundError`) | 디폴트 안내 문자열 반환               |
| 6    | API 장애/Rate Limit                     | 디폴트 수칙 문장 즉시 반환            |
| 7    | TTS 호출 실패/타임아웃                  | 기기 내장 TTS로 우회                  |

상세 예외 처리는 `docs/minchodan_design_note.md` 각 단계의 **의존성·예외** 필드를 참조합니다.
