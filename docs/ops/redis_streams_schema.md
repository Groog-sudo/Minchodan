> **작성일**: 2026-07-05
> **버전**: v1.0.0
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
| **최대 크기 제한 (지침)** | `MAXLEN ~1000` | 메모리 과다 적재 방지를 위한 유효 기간 슬라이싱 |

### 1.2 `risk.events` 페이로드 필드 정의

| 필드 키 (Field Key) | 데이터 타입 | 필수 여부 | 설명 및 값 범주 |
| :--- | :--- | :--- | :--- |
| `event_id` | `String` | 필수 | 단말기 생성 고유 식별자 (`evt-timestamp-random`) |
| `device_id` | `String` | 필수 | 디바이스 고유 식별자 (`dev-001` 등) |
| `frame_id` | `Integer` | 필수 | 캡처 단말에서 넘버링된 프레임 고유 번호 |
| `ts` | `Long` | 필수 | 단말기 캡처 시점의 Epoch ms 타임스탬프 |
| `detected_classes` | `JSON String` | 필수 | 탐지된 장애물 목록 (예: `["pothole", "bollard"]`) |
| `surface_state` | `String` | 필수 | 노면 세그멘테이션 상태 (`sidewalk_normal`, `braille_normal` 등) |
| `max_risk_level` | `String` | 필수 | 탐지된 클래스 기준 최고 위험 등급 (`high`, `mid`, `low`) |
| `panning` | `Float` | 옵션 | 경보음 스테레오 밸런스 지표 (`-1.0` 좌측 ~ `1.0` 우측) |
| `beep_interval_ms`| `Integer` | 옵션 | 반사음 주파수 점멸 주기 (ms, `0`은 연속 정지 경보) |

---

## 2. 중복 발화 제어용 TTL 세션 스키마 (Redis Strings)

시각장애인 보행 환경에서 동일 장애물에 대해 피드백이 너무 자주 울리는 피로 현상(중복 노이즈)을 억제하기 위한 휘발성 캐시 영역입니다.

### 2.1 세션 캐시 키 규칙
- **키 네이밍 규칙**: `session:{device_id}:last_alert:{class_name}`
  - 예시: `session:dev-001:last_alert:bollard`

### 2.2 캐시 속성 및 라이프사이클

| 파라미터 | 세팅 기준 및 값 | 설명 |
| :--- | :--- | :--- |
| **데이터 타입** | `String` | 최근 발생한 알림 타임스탬프 (`Epoch ms` 문자열) |
| **기록 명령어** | `SETEX [Key] 30 [Timestamp]` | 알림 발송 시점에 30초의 TTL 만료 기한을 함께 주입 |
| **만료 타임아웃** | **30초** (`TTL=30`) | 30초 이내에 동일 기기에서 동일 장애물이 다시 탐지될 경우 경보 무시 |
| **조회 및 필터링** | `EXISTS [Key]` | 키가 존재하면 가이드 음성 합성(Gemma/TTS) 연산 생략 |
