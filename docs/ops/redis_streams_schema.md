> **작성일**: 2026-07-05
> **버전**: v1.1.1 (2026-07-20 억제 키·TTL을 P0-1 실코드 기준 정정: `suppress:{device}:{source}:{track}:{band}`, TTL 5s/surface 15s)
> **설계 기준**: docs/design/architecture.md (v1.1.0)

# Minchodan Redis Streams 데이터 모델 및 TTL 세션 스키마 명세

본 문서는 시각장애인 보행 보조 시스템의 이벤트 버스(Event Bus)로 기능하는 Redis Streams 및 메모리 세션의 엄격한 데이터 규격과 스키마 명세입니다.

---

## 1. Redis Streams 명세 (`risk.events`)

추론 서버(FastAPI)가 탐지한 장애물 메타데이터 및 분석 통계를 중계하는 핵심 데이터 스트림 스트림입니다.

### 1.1 스트림 기본 메타데이터

| 분류 | 내용 | 설명 |
| :--- | :--- | :--- |
| **스트림 키 이름** | `risk.events` | 보행 위협 및 노면 탐지 이벤트 버스 키 |
| **발행 명령어 (Write)** | `XADD risk.events * [필드명] [값] ...` | 서버가 비동기로 프레임별 탐지 이벤트 적재 |
| **구독 명령어 (Read)** | `XREAD COUNT 1 STREAMS risk.events $` | LangGraph 오케스트레이터 및 TTS가 최신 이벤트 수신 |
| **최대 크기 제한 (지침)** | (미설정) | `server/bus/*.py` 어디에도 `MAXLEN`이 적용되어 있지 않다 — 2026-07-07 기준 문서상 지침일 뿐 코드에 강제되지 않음 |

### 1.2 `risk.events` 페이로드 필드 정의 (2026-07-07 실제 코드 기준 전면 정정)

> **주의**: `risk.events` 스트림에는 서로 다른 두 producer가 서로 다른 필드 구조로 발행한다. 최초 설계 문서는 이 둘을 하나로 뭉뚱그린 가상의 필드 목록(`detected_classes`, `surface_state`, `max_risk_level`, `panning`, `beep_interval_ms`)을 제시했으나, 실제로는 아래 두 스키마 중 하나로만 발행되며 이 필드들은 어디에도 존재하지 않는다.

**(A) 2단계 캡처 메타데이터** — `server/capture/stream_splitter.py::_publish_metadata()`가 프레임 수신마다 발행:

| 필드 키 | 타입 | 설명 |
| :--- | :--- | :--- |
| `event_id` | `String` | 이벤트 추적 식별자 |
| `device_id` | `String` | 디바이스 식별자 |
| `stream` | `String` | `reflex` \| `cognitive` |
| `ts` | `String`(숫자 문자열) | 캡처 시점 Epoch ms |
| `size_kb` | `String`(숫자 문자열) | 디코딩된 프레임 크기(KB) |
| `decode_ms` | `String`(숫자 문자열) | 디코딩 소요 시간(ms) |

**(B) 3단계 탐지 이벤트** — `server/bus/producer.py::RiskEventProducer.publish_detection()`가 mid/low 위험 탐지 시 발행:

| 필드 키 | 타입 | 설명 |
| :--- | :--- | :--- |
| `event_id` | `String` | 이벤트 추적 식별자 |
| `track_id` | `String` | ByteTrack ID (`T-0001` 포맷, 없으면 `"unknown"`) |
| `class_name` | `String` | 탐지 클래스명 |
| `confidence` | `String`(숫자 문자열) | 신뢰도 |
| `bbox` | `JSON String` | `{x,y,w,h}` |
| `speed` | `String`(숫자 문자열) | 접근/이탈 속도 |
| `direction` | `String` | `front-left`/`front`/`front-right`/`unknown` |
| `risk` | `String` | 위험 등급 힌트 |
| `timestamp` | `String`(숫자 문자열) | 발행 시점 Unix time |

---

## 2. 중복 발화 제어용 TTL 캐시 스키마 (Redis Strings/Hash, 2026-07-07 실제 코드 기준 전면 정정)

시각장애인 보행 환경에서 동일 경보가 너무 자주 울리는 피로 현상(중복 노이즈)을 억제하고, ByteTrack 컨텍스트를 유지하기 위한 휘발성 캐시 영역입니다.

### 2.1 경보 중복 억제 (`server/tts/suppressor.py`)
- **키 네이밍 규칙**: `suppress:{device_id}:{alert_source}:{track_id}:{distance_band}` (P0-1, 2026-07-17)
  - 예시: `suppress:dev-001:reflex_gate:T-0003:near`
  - `alert_id`는 class-agnostic `"high_obstacle"` 고정이며, 억제 키에는 track/band가 포함된다
- **데이터 타입**: `String` (SETEX 값은 `"1"`)
- **기록 명령어**: `SETEX suppress:{device_id}:{alert_source}:{track_id}:{distance_band} {ttl} 1`
- **만료 타임아웃**: **`REFLEX_SUPPRESS_TTL_S=5`초** (일반 반사). 노면(surface)은 **`REFLEX_SURFACE_SUPPRESS_TTL_S=15`초**. 최초 설계의 60초 무조건 침묵은 폐기(2026-07-17 P0-1)
- **조회/마킹**: `should_suppress` / `mark_sent` — 동일 키 TTL + device 쿨다운 + 거리 밴드 악화 시 재발화

### 2.2 ByteTrack 컨텍스트 (`server/bus/redis_client.py`, 최초 설계 문서에 누락됐던 실제 키)
- **키 네이밍 규칙**: `ctx:{track_id}`
  - 예시: `ctx:T-0003`
- **데이터 타입**: `Hash` (`HSET`)
- **기록 명령어**: `HSET ctx:{track_id} <mapping>` 직후 `EXPIRE ctx:{track_id} 30`
- **만료 타임아웃**: **30초** (`DEFAULT_TRACK_TTL = 30`)
- **조회**: `get_track_context(track_id)` → `HGETALL ctx:{track_id}` (speed/direction 계산용 이전 위치 조회)
