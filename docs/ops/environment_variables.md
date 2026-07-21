# Minchodan 환경 변수 명세서

> **작성일**: 2026-06-27
> **수정일**: 2026-07-21
> **버전**: v0.4.36 (2026-07-21 P0/P1 과부하 완화 - SERVER_BUSY_SUGGEST_INTERVAL_MS·REFLEX_SEG_EVERY_N 신규. 기존 v0.4.35 이력 유지: 온디바이스·서버 가중치 기준선 통일. 기존 v0.4.34~v0.4.29 이력 유지)
> **기준 파일**: [`.env.example`](../../.env.example) (단일 기준)
> **설계 기준**: [`docs/design/architecture.md`](../design/architecture.md) 10절·13.4절, [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md)
> **코딩 패턴 기준**: [`docs/dev-guides/course_codebase_guide.md`](../dev-guides/course_codebase_guide.md) 3.4(.env 로드)

---

## 1. 목적

본 문서는 Minchodan 프로젝트의 모든 환경 변수를 단일 명세로 통합하여, 기존 `.env.example`·`architecture.md` 10절·루트 `README.md` 환경변수 표 간의 **3원화 불일치를 해소**합니다. 모든 환경 변수 관련 문서는 본 명세서를 기준으로 참조합니다.

---

## 2. 환경 변수 전체 매트릭스

### 2.1 일반 (서버 로깅)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LOG_LEVEL`** | string | 선택 | `INFO` | **2026-07-19 신규.** 서버 루트 로거 레벨 (`DEBUG`, `INFO`, `WARNING`, `ERROR`). `DEBUG`는 개발 시 상세 추적용, 운영 시 `INFO` 권장(로그 폭주 및 민감정보 노출 방지) | `server/main.py` |

### 2.2 LLM / Ollama (6단계 오케스트레이션)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LLM_PROVIDER`** | string | 필수 | `ollama` | LLM 공급자 (`ollama` 또는 `openai`). GPU 부하 시 `LLMClientFactory`가 자동 핫스왑 | [`stage6_orchestration_design.md`](stage6_orchestration_design.md) 9.3절 |
| **`OLLAMA_BASE_URL`** | string | 필수 | `http://localhost:11434` | Ollama 서버 주소 | [`architecture.md`](architecture.md) 10절 |
| **`COMPOSE_OLLAMA_BASE_URL`** | string | 선택 | `http://host.docker.internal:11434` | Docker Compose의 FastAPI 컨테이너가 호스트 로컬 Ollama로 접속할 때 `OLLAMA_BASE_URL`로 주입할 주소. Linux Compose는 `host.docker.internal`을 고정 게이트웨이 `172.18.0.1`로 매핑하므로 `172.18.0.0/16 -> 172.18.0.1:11434/tcp` UFW 허용이 필요합니다. macOS Colima에서는 `http://host.lima.internal:11434` 사용 권장 | [`docker/docker-compose.macos.yml`](../../docker/docker-compose.macos.yml), [`docker/docker-compose.yml`](../../docker/docker-compose.yml) |
| **`OLLAMA_HOST`** | string | 선택 | (코드 기본값) | 임베딩 팩토리 전용 Ollama 호스트 (2026-07-07 추가 — `OLLAMA_BASE_URL`과 별개로 존재) | `server/rag/embedding_engine_factory.py:46` |
| **`GEMMA_MODEL`** | string | 필수 | `gemma4:e4b` | L2 가이드 생성 모델 (로컬) | [`stage6_orchestration_design.md`](stage6_orchestration_design.md) 9.3절 |
| **`LLAVA_MODEL`** | string | 선택(잔재) | `llava` | **2026-07-07 폐기**: 4단계 캡셔닝을 Llava에서 Gemini API로 전환하면서 코드에서 더 이상 소비되지 않는 잔재 변수. `.env.example`에도 "미사용" 주석 처리됨. 제거 대상이나 하위 호환 표시로 잔존 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`OLLAMA_KEEP_ALIVE`** | string | 선택 | (Ollama 기본 `5m`) | `docker/linux_docker_start.sh`가 `ollama serve` 실행 시 모델 언로드 지연 제어. `.env.example`에 명시됨 | `docker/linux_docker_start.sh` |
| **`OLLAMA_MAX_LOADED_MODELS`** | int | 선택 | (Ollama 기본) | 동시 상주 모델 수 상한. `docker/linux_docker_start.sh`에서 사용 | `docker/linux_docker_start.sh` |
| **`GOOGLE_API_KEY`** | string | 선택 | (미설정) | 4단계 캡셔닝 모델 Gemini API(`gemini-2.5-flash-lite`, `server/rag/build/gemini_captioner.py`) 사용 시 필수. 미설정 시 `ValueError` 발생(Llava 폴백 없음 — 2026-07-07 확인: 실제 캡셔너 구현체는 Gemini뿐). **2026-07-13 해결**: `.env.example`에 추가 완료(정합성 검토 P0) | [`stage4_5_rag_design.md`](stage4_5_rag_design.md) 2.1절 |
| **`EMBEDDING_MODEL`** | string | 필수 | `nomic-embed-text` | 임베딩 모델 (768차원) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`OPENAI_API_KEY`** | string | 선택 | (미설정) | OpenAI 핫스왑 시 필요. 미설정 시 OpenAI 클라이언트 초기화에서 `ValueError` 발생 후 Ollama로 폴백 | [`architecture.md`](architecture.md) 13.4절 |

### 2.3 Vector DB (ChromaDB) (4·5단계 RAG)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CHROMA_PATH`** | path | 필수(설계상) | `data/chroma_db` | ChromaDB persist 디렉토리 (로컬 파일 기반). **2026-07-08 정정**: `server/rag/retriever.py`의 `get_default_retriever()`가 `os.getenv("CHROMA_PATH", "data/chroma_db")`로 읽어 실시간 인지 가이드 파이프라인에 실제 연결됨(이전에는 미소비 상태였음) | [`architecture.md`](architecture.md) 2절 |
| **`CHROMA_COLLECTION`** | string | 필수(설계상) | `safety_guidelines` | ChromaDB 컬렉션명 (보행 수칙 지식베이스). **2026-07-08 정정**: 기존 `.env`/`.env.example` 기본값(`bidding_kb`/`minchodan_kb`)이 실제 저장된 컬렉션명과 달라 RAG 검색이 항상 미적중이었음. 실제 데이터가 적재된 컬렉션명(`safety_guidelines`)으로 정정하고 `get_default_retriever()`에서 소비하도록 연결 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.5절 |
| **`EMBEDDING_PROVIDER`** | string | 선택 | `ollama` | 임베딩 공급자(`ollama`/`mock`/`openai`). `server/rag/retriever.py`가 `get_default_retriever()`에서 소비. **주의**: `.env.example`은 시연용 키워드 매칭을 위해 `mock`을 기본으로 하되, 랩 기본은 `ollama`(`nomic-embed-text`) | `server/rag/retriever.py:143`, `server/rag/embedding_engine_factory.py:41` |

### 2.4 Redis (이벤트 버스·MCP 메트릭)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`REDIS_PASSWORD`** | string | 필수 | 없음 | Redis `requirepass` 비밀값. `scripts/configure_security_secrets.py`로 생성하며 Git에 기록하지 않음 | `docker/docker-compose*.yml` |
| **`REDIS_URL`** | string | 필수 | 없음 | 인증정보를 포함한 Redis 연결 URL. 로컬 예: `redis://:${REDIS_PASSWORD}@localhost:6379` | [`architecture.md`](architecture.md) 2절·13.3절 |
| **`REDIS_STREAM_MAXLEN`** | int | 선택 | `5000` | **2026-07-20 신규.** `risk.events` 등 Redis Stream의 approximate MAXLEN 트리밍 상한. 기존 xadd에 maxlen이 없어 실기기 29시간 테스트에서 236,529건까지 무제한 누적된 것을 확인 후 추가 | `server/bus/redis_client.py` |

### 2.5 WebSocket 서버 (1단계 통신망)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`WS_HOST`** | string | 필수 | `0.0.0.0` | WebSocket 서버 바인드 호스트 | [`api_specification.md`](api_specification.md) 1절 |
| **`WS_BIND_HOST`** | string | 선택(macOS Docker) | `0.0.0.0` | **macOS Docker 변형 전용.** `docker-compose.macos.yml`이 FastAPI 컨테이너 포트를 이 호스트에 바인딩. Tailscale 직접 접속 시 `0.0.0.0`(기본), Linux 변형은 루프백 `127.0.0.1` 고정 | `docker/docker-compose.macos.yml` |
| **`WS_PORT`** | int | 필수 | `8000` | WebSocket 서버 포트 | [`api_specification.md`](api_specification.md) 1절 |
| **`HEARTBEAT_INTERVAL`** | int | 선택 | (코드 기본값) | 하트비트 송신 주기(초). `server/api/config.py` (2026-07-07 추가 — 기존 명세서에 누락돼 있었음) | `server/api/config.py:30` |
| **`HEARTBEAT_TIMEOUT`** | int | 선택 | `15` | 하트비트 미수신 타임아웃(초). 총 유예 시간은 `HEARTBEAT_INTERVAL+HEARTBEAT_TIMEOUT`(기본 20초). **2026-07-10 변경**(기존 5): ngrok 등 공인망 릴레이 경유 시 왕복 지연으로 정상 연결도 오탐 종료되는 문제를 실기기 LTE 테스트로 확인해 상향 | `server/api/config.py:31` |
| **`MAX_RECONNECT_ATTEMPTS`** | int | 선택 | (코드 기본값) | 서버 측 재연결 허용 횟수 | `server/api/config.py:32` |
| **`WS_AUTH_TIMEOUT_SECONDS`** | float | 선택 | `10` | 단말·콘솔 WebSocket 연결 후 인증 메시지를 기다리는 최대 시간. 초과 시 정책 위반 코드로 종료 | `server/api/config.py`, `server/api/ws_router.py` |
| **`CORS_ORIGINS`** | JSON 배열 문자열 | 선택 | `["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]` | 운영자 콘솔 CORS 허용 출처. **2026-07-13 개선**: Pydantic Settings 초기화 시 환경변수 `CORS_ORIGINS`의 JSON 포맷 또는 쉼표 구분값으로부터 동적으로 안전하게 파싱 및 바인딩되도록 개선. | `server/api/config.py`, `server/main.py` |
| **`JWT_SECRET_KEY`** | string | 필수(모든 환경) | 없음 | 관리자·디바이스 JWT 서명 키. 32자 미만 또는 알려진 플레이스홀더면 환경과 무관하게 서버 기동을 거부함 | `server/db/security.py` |
| **`JWT_ISSUER`** | string | 선택 | `minchodan-api` | JWT 발급자 `iss` 검증값 | `server/db/security.py` |
| **`JWT_AUDIENCE`** | string | 선택 | `minchodan-clients` | JWT 대상 `aud` 검증값 | `server/db/security.py` |
| **`ADMIN_BOOTSTRAP_TOKEN`** | string | 최초 구축 시 필수 | 없음 | 관리자 테이블이 비었을 때 `/api/v1/admin/bootstrap`으로 최초 최고관리자를 1회 생성하는 32자 이상 토큰 | `server/api/admin_router.py` |
| **`APP_ENV`** | string | 선택 | `development` | 배포 환경 구분. `production`에서는 API 문서가 비활성화되고 정적 단말 토큰을 사용하지 않음 | `server/main.py`, `server/api/auth.py` |
| **`ALLOW_STATIC_DEVICE_TOKENS`** | bool | 선택 | `false` | 개발용 정적 단말 토큰을 명시적으로 허용. 운영에서는 `false` 유지하고 관리자 발급 단말 JWT 사용 | `server/api/auth.py` |
| **`DEVICE_STATIC_TOKENS`** | string | 선택 | 없음 | 32자 이상 정적 토큰의 `device_id:token` 목록. `ALLOW_STATIC_DEVICE_TOKENS=true`일 때만 로드 | `server/api/auth.py` |
| **`ENABLE_DEBUG_API`** | bool | 선택 | `false` | 비운영 환경에서 최고관리자용 디버그 TTS API를 명시적으로 활성화 | `server/api/debug_router.py` |
| **`ENABLE_NAVIGATION_SIMULATOR`** | bool | 선택 | `false` | `/navigation` 서브앱(콘솔 GPS HUD·OperatorLiveMap iframe) 마운트. **production** 에서는 `true` 일 때만 열고, **development**(`APP_ENV!=production`)에서는 플래그와 무관하게 기본 마운트한다(관제 지도 404 방지, 2026-07-19). | `server/main.py` |
| **`CONSOLE_PORT`** | int | 선택 | `5174` | 운영자 콘솔 컨테이너 호스트 노출 포트. `docker-compose*.yml` `${CONSOLE_PORT:-5174}:5174` | `docker/docker-compose.yml`, `docker/docker-compose.macos.yml` |
| **`CONSOLE_RELAY_MIN_INTERVAL_S`** | float | 선택 | `0.2` | 콘솔 Live Feed 프레임 릴레이 스로틀 간격(초, 기본 5fps). 단말 프레임을 콘솔에 중계할 때 최소 간격 | `server/api/ws_router.py:921` |
| **`SERVER_BUSY_SUGGEST_INTERVAL_MS`** | int | 선택 | `250` | **2026-07-21 신규 (P0).** detection ack `server_busy=true`일 때 단말이 적용할 반사 캡처 간격 힌트(ms, ≈4fps). 디코드 전 스킵·큐 적체 백프레셔와 연동 | `server/api/ws_router.py` |
| **`ACCESS_TOKEN_EXPIRE_HOURS`** | int | 선택 | `8` | 관리자 JWT 액세스 토큰 만료 시간(시간) | `server/db/security.py:27` |
| **`DEVICE_TOKEN_EXPIRE_DAYS`** | int | 선택 | `30` | 단말 JWT 만료 일수(일). §8.8 단말 토큰 발급 계약과 연동 | `server/api/auth.py:58` |

### 2.6 탐지 설정 (3단계 Detection)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`YOLO_CONF`** | float | 필수 | `0.35` | Yolo 26N - **Segmentation** 신뢰도 임계값 (`YoloSegmentor`) | [`stage3_detection_design.md`](../stage-guides/stage3_detection_design.md) 5절 |
| **`YOLO_DET_CONF`** | float | 선택 | `0.50` | Yolo 26N - **Object Detection** 신뢰도 임계값 (`YoloDetector`). `YOLO_CONF`와 별도 | `server/detection/config.py` |
| **`DETECTOR_TYPE`** | string | 선택 | `yolo` | **2026-07-17 정정**: 실측 랩 기본은 `yolo`(가중치 로드). `mock`이면 노트북/데모·CI에서 `MockDetector`/`MockSegmentor`를 강제 사용한다. 미지원 값은 안전 폴백으로 `mock` 처리. `.env.example`과 동일 | `server/detection/config.py` |
| **`FRAME_SIZE`** | int | 필수 | `640` | 프레임 리사이즈 크기 (정방형) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`REFLEX_FPS`** | int | 필수 | `10` | 반사 캡처 목표 fps (8~10fps 권장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`COGNITIVE_FPS`** | int | 필수 | `2` | 인지 캡처 목표 fps (1~2fps 권장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`YOLO_INFERENCE_WORKERS`** | int | 선택 | `3` | **2026-07-20 신규.** YOLO 탐지/분할 추론 전용 `ThreadPoolExecutor` 워커 수. 기존에는 `asyncio.to_thread()`가 기본 스레드풀(워커 18개)을 TTS/STT/RAG/이벤트 프레임 저장과 공유해, 느린 TTS 합성 뒤에 추론이 큐잉되며 CPU 경합·체감 지연이 누적되던 문제를 실기기 장시간 테스트로 확인 후 분리 | `server/detection/detection_pipeline.py` |
| **`REFLEX_SEG_EVERY_N`** | int | 선택 | `3` | **2026-07-21 신규 (P1).** 반사 스트림에서 segmentation을 N프레임마다 1회 수행(1=매 프레임). det는 매 프레임. 노면 게이트는 직전 seg 결과로 평가. 인지 스트림은 항상 seg | `server/detection/detection_pipeline.py` |
| **`REFLEX_QUEUE_MAXSIZE`** | int | 선택 | `2` | **2026-07-17 신규 (P0-2).** 반사 asyncio.Queue 최대 깊이. latest-frame-wins로 얕게 잡아 큐 적체로 인한 지연 드리프트 방지. 큐 가득 시 oldest drop | `server/capture/stream_splitter.py` |
| **`COGNITIVE_QUEUE_MAXSIZE`** | int | 선택 | `4` | **2026-07-17 신규 (P0-2).** 인지 asyncio.Queue 최대 깊이. 1~2fps 특성상 소량 버퍼면 충분 | `server/capture/stream_splitter.py` |
| **`REFLEX_MAX_AGE_S`** | float | 선택 | `0.4` | **2026-07-17 신규 (P0-2).** 반사 프레임 신선도 임계(초). 소비 시각 기준 프레임 ts가 이 값을 초과하면 추론 없이 드롭. ts=0(클라이언트 미전송)이면 검사 건너뜀 | `server/detection/consumer.py` |
| **`COGNITIVE_MAX_AGE_S`** | float | 선택 | `2.0` | **2026-07-17 신규 (P0-2).** 인지 프레임 신선도 임계(초). 인지는 1~2fps 특성상 반사보다 여유 | `server/detection/consumer.py` |
| **`REFLEX_SUPPRESS_TTL_S`** | int | 선택 | `5` | **2026-07-17 신규 (P0-1).** 동일 track_id+distance_band 조합의 반사 억제 TTL(초). 보행 속도(1m/s) 기준 5초면 동일 객체 반복 스팸 방지 충분 | `server/tts/suppressor.py` |
| **`REFLEX_MIN_GAP_S`** | float | 선택 | `1.5` | **2026-07-17 신규 (P0-1).** 서로 다른 객체 경보의 최소 간격(초, device 단위). 알림 폭탄 방지 | `server/tts/suppressor.py` |
| **`REFLEX_NEAR_HAPTIC_THROTTLE_S`** | float | 선택 | `0.5` | **2026-07-17 신규 (P0-1).** near(<=0.6m) 햅틱+비프 스로틀 간격(초). 충돌 임박 촉각 신호는 TTL 억제 제외, 스로틀만 적용 | `server/tts/suppressor.py` |
| **`REFLEX_NEAR_TRACK_MIN_GAP_S`** | float | 선택 | `1.2` | **2026-07-20 신규.** near에서 동일 track_id 재발동 최소 간격(초). 필드 DB 분석 결과 같은 물체가 500ms 스로틀만으로 0.5~1초 간격 재발동해 햅틱이 따닥거리는 사례 확인, 동일 track_id에만 추가 간격을 요구(다른 물체는 기존 500ms만 적용해 반응성 유지) | `server/tts/suppressor.py` |
| **`APPROACH_LOST_WINDOW_S`** | float | 선택 | `1.0` | **2026-07-17 신규 (P0-3).** Approach-Lost 윈도우(초). 동일 track_id가 이 시간 이내 재탐지되고 직전 hit_count가 MIN 이상이면 reacquired=True로 즉시 재발화 | `server/detection/bytetrack_tracker.py` |
| **`APPROACH_LOST_MIN_PREV_HIT`** | int | 선택 | `3` | **2026-07-17 신규 (P0-3).** Approach-Lot 판정에 필요한 직전 hit_count 하한 (reflex_gate MIN_HIT_COUNT와 SSOT) | `server/detection/bytetrack_tracker.py` |
| **`COGNITIVE_UTTERANCE_COOLDOWN_S`** | float | 선택 | `30.0` | **2026-07-17 신규 (P1-2).** 인지 가이드 발화 가치 게이트의 동일 상황 쿨다운(초). 동일 객체+표면 서명이면 이 시간 동안 TTS 합성 생략. 새 객체/표면 변화/보도 이탈/쿨다운 경과 시 발화 | `server/detection/consumer.py` |
| **`SURFACE_CAUTION_CONFIRM_STREAK`** | int | 선택 | `2` | **2026-07-17 신규 (P2-1b).** surface_caution(계단/맨홀 통합) 반사 발동 히스테리시스. 연속 N 프레임 확인 후 반사 발동해 단일 프레임 오탐 완화 | `server/detection/consumer.py` |
| **`REFLEX_LATENCY_ALERT_MS`** | float | 선택 | `300` | **2026-07-17 신규 (P2-2).** 반사 파이프라인 지연 관측 임계(ms). total_ms 초과 시 콘솔 latency_event에 latency_alert=True (비협상 목표 <300ms) | `server/detection/consumer.py` |
| **`COGNITIVE_LATENCY_ALERT_MS`** | float | 선택 | `3000` | **2026-07-17 신규 (P2-2).** 인지 파이프라인 지연 관측 임계(ms). total_ms 초과 시 콘솔 latency_alert=True (가이드 허용 범위 <3000ms) | `server/detection/consumer.py` |
| **`GUIDE_LOW_RISK_NARRATION`** | bool | 선택 | `false` | **2026-07-18 신규 (T2-G).** `true`이면 저위험(low) 순수 내레이션을 발화한다. `false`이면 "측면·원거리·정적 객체" 등 저위험 상황의 단순 안내를 억제해 청각 피로를 줄인다. 보도 이탈, 고위험, 접근 객체, 유의미 노면은 예외로 항상 발화 | `server/detection/consumer.py` |
| **`RAG_ENABLED`** | bool | 선택 | `true` | **2026-07-19 신규.** `GUIDANCE_CONTEXT_MODE=rag`일 때만 의미 있음. `false`면 Chroma 검색을 건너뛰고 `rag_context`를 "관련 수칙 없음"으로 둔다. `hints` 모드에서는 무시 | `server/detection/consumer.py` |
| **`GUIDANCE_CONTEXT_MODE`** | string | 선택 | `hints` | **2026-07-20 신규.** Medium 인지 경로 컨텍스트 소스. `hints`(기본)=인메모리 짧은 회피 힌트(`server/rag/guidance_hints.py`, rag_ms≈0). `rag`=기존 Chroma `search_guidance` 롤백/A/B. 잘못된 값은 `hints`로 폴백 | `server/detection/consumer.py`, [`medium_guidance_hint_dict_implementation_plan.md`](medium_guidance_hint_dict_implementation_plan.md) |
| **`REFLEX_SURFACE_SUPPRESS_TTL_S`** | int | 선택 | `60` | **2026-07-19 신규, 2026-07-20 2차 상향(15→30→60).** 노면(surface) 반사 경보 전용 억제 TTL(초). 세그먼트 흔들림으로 매초 재발화하기 쉬워 일반 반사(5s)보다 길게 설정. 1차 상향(15→30) 후 재검증에서도 같은 캐션 구간을 계속 걸으면 여전히 자주 울린다는 필드 피드백으로 추가 상향 | `server/tts/suppressor.py:27` |
| **`REFLEX_SURFACE_MIN_GAP_S`** | float | 선택 | `45.0` | **2026-07-19 신규, 2026-07-20 2차 상향(8.0→15.0→45.0).** 노면 surface 경보 발화 간 최소 간격(초, device 단위) | `server/tts/suppressor.py:28` |
| **`SURFACE_HAZARD_ABSENT_STREAK`** | int | 선택 | `5` | 노면 위험 소실 히스테리시스. 연속 N 프레임 미탐지 시에만 위험 해제로 판정해 세그먼트 깜빡임 오탐 완화. **2026-07-20**: 기본 3→5 (far flicker 재enter 완화) | `server/detection/consumer.py` |
| **`SURFACE_REENTER_COOLDOWN_S`** | float | 선택 | `20.0` | **2026-07-20 신규.** 노면 인지(surface_hazard) 이탈 후 재진입 enter 최소 간격(초). 쿨다운 안이면 enter를 continue로 강등 | `server/detection/consumer.py` |
| **`BRAILLE_REENTER_COOLDOWN_S`** | float | 선택 | `45.0` | **2026-07-20 신규.** 점자블록-only 인지 재진입 쿨다운(초). 위험 노면보다 길게 잡아 잔소리 완화 | `server/detection/consumer.py` |
| **`BRAILLE_ABSENT_STREAK`** | int | 선택 | `5` | **2026-07-20 신규.** 점자블록 인지 에피소드 이탈 히스테리시스 프레임 수 | `server/detection/consumer.py` |
| **`NEAR_CLEAR_HOLD_OFF_S`** | float | 선택 | `0.4` | **2026-07-20 신규.** Near episode `reflex_clear` 전 hold-off(초). near↔medium 경계 진동으로 비프가 끊기는 채터 완화 | `server/detection/consumer.py` |
| **`SPEECH_FRONT_BAND_NEAR_LO`** / **`SPEECH_FRONT_BAND_NEAR_HI`** | float | 선택 | `0.35` / `0.65` | **2026-07-20 신규.** 안내용 12시 회랑(정규화 x, Near). bbox **중심 x**가 이 구간일 때만 반사 비프/햅틱. 공간 라벨용 `FRONT_BAND`와 분리 | `server/detection/direction.py` |
| **`SPEECH_FRONT_BAND_MEDIUM_LO`** / **`SPEECH_FRONT_BAND_MEDIUM_HI`** | float | 선택 | `0.40` / `0.60` | **2026-07-20 신규.** 안내용 12시 회랑(정규화 x, Medium). 인지 TTS 허용 조건 | `server/detection/direction.py` |
| **`SURFACE_ZONE_NEAR_Y_RATIO`** | float | 선택 | `0.6` | 노면 Y좌표 기반 near 거리 구역 비율. centroid_y > frame_height*이 값이면 near로 판정 | `server/detection/consumer.py:99` |
| **`SURFACE_ZONE_MEDIUM_Y_RATIO`** | float | 선택 | `0.35` | 노면 Y좌표 기반 medium 거리 구역 비율 | `server/detection/consumer.py:100` |
| **`YOLO26N_OBJECT_DET`** | path | 선택 | `server/models/yolo26n/object_detection260714.pt` | Yolo 26N - Object Detection 가중치. **서버·온디바이스 공통 기준선**(CoreML/TFLite는 본 `.pt`에서 export). `object_detection.pt`는 동일 해시 별칭. 레거시: `det_best_20260705.pt` | [`stage3_detection_design.md`](stage3_detection_design.md) 12.3절, `scripts/export_mobile.py` |
| **`YOLO26N_SEG`** | path | 선택 | `server/models/yolo26n/segmentation260714.pt` | Yolo 26N - Segmentation 가중치. **서버·온디바이스 공통 기준선**. `segmentation.pt`는 동일 해시 별칭. 레거시: `segbest.pt`(온디바이스와 불일치) | [`stage3_detection_design.md`](stage3_detection_design.md) 12.3절, `scripts/export_mobile.py` |
| **`YOLO_AUTOINSTALL`** | bool | 선택 | `False` | **2026-07-19 신규.** ultralytics 자체 환경변수(`YOLO_AUTOINSTALL`, Minchodan 접두사 아님). 모델 로드/추론마다 체크포인트 내장 requirements를 현재 설치본과 비교해 불일치 시 런타임 `pip install`을 시도하는 AutoUpdate 기능을 제어. `True`(ultralytics 기본값)면 방금 갱신된 패키지와 이미 임포트된 모듈이 어긋나 `'Conv' object has no attribute 'bn'` 추론 오류가 재발한다(실측 확인). `docker/Dockerfile`에 `ENV`로 기본값 고정, `docker-compose*.yml`에도 명시 | `docker/Dockerfile`, `docker/docker-compose*.yml` |

### 2.7 TTS (7단계 음성 출력)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TTS_ENGINE`** | string | 필수 | `supertonic` | TTS 엔진. **2026-07-13 추가**: `edge`(Microsoft Edge Neural, `edge-tts`, 네트워크 필수·로컬 모델 없음, 한국어 자연도 우선). 기존: `supertonic`(로컬 기본) / `piper` / `pyttsx3`. 인지 경로 실시간 합성에만 사용 (반사 경로는 사전합성 클립) | [`stage7_tts_design.md`](../stage-guides/stage7_tts_design.md) |
| **`EDGE_TTS_VOICE`** | string | 선택 | `ko-KR-SunHiNeural` | **2026-07-13 신규.** `TTS_ENGINE=edge`일 때 화자. 예: `ko-KR-SunHiNeural`(여), `ko-KR-InJoonNeural`(남) | `server/tts/tts_service.py` |
| **`SUPERTONIC_VOICE`** | string | 선택 | `F2` | **2026-07-09 신규.** Supertonic 보이스(`F1`~`F5`/`M1`~`M5`). **2026-07-13 접근성**: 기본 `F1`→`F2`(부드러운 안내톤, 기계음 체감 완화) | `server/tts/tts_service.py` |
| **`SUPERTONIC_MODEL_DIR`** | path | 선택 | (미지정, 라이브러리 기본 `~/.cache/supertonic3`) | **2026-07-09 신규.** 명시적으로 지정하지 않는 것을 권장 - `server/models/` 하위로 지정하면 `docker-compose.yml`의 `../server:/app/server` 볼륨 마운트가 빌드 타임에 받아둔 캐시를 컨테이너 시작 시 호스트 쪽 내용으로 덮어써 버린다(pygoruut와 동일 문제) | `server/tts/tts_service.py` |
| **`SUPERTONIC_TOTAL_STEPS`** | int | 선택 | `12` | **2026-07-09 신규.** 합성 품질/속도 트레이드오프(5=저품질·고속 ~ 16=고품질·저속). **2026-07-13**: 접근성 기본 `8`→`12` | `server/tts/tts_service.py` |
| **`TTS_DEFAULT_SPEED`** | float | 선택 | `0.85` | **2026-07-13 신규.** 인지 경로 기본 발화 속도(Supertonic/Piper/pyttsx3 공통). 미지정 시 `PIPER_DEFAULT_LENGTH_SCALE` → `0.85` 순 | `server/tts/realtime_tts.py` |
| **`PIPER_USE_CUDA`** | bool | 선택 | `false` | Piper ONNX 세션 CUDAExecutionProvider 사용 여부(핫스왑 폴백용, `TTS_ENGINE=piper`일 때만 사용). **2026-07-09 정정**: 상주 프로세스화로 `PIPER_BINARY_PATH`(CLI 바이너리 경로)는 제거됨 | `server/tts/tts_service.py` |
| **`PIPER_LENGTH_SCALE_MIN`** / **`PIPER_LENGTH_SCALE_MAX`** | float | 선택 | `0.5` / `2.0` | Piper 발화 속도(length_scale) 허용 범위(핫스왑 폴백용) | `server/tts/tts_service.py` |
| **`PIPER_DEFAULT_LENGTH_SCALE`** | float | 선택 | `0.85` | Piper 핫스왑·`TTS_DEFAULT_SPEED` 미지정 시 폴백 속도. **2026-07-13**: 접근성 기본 `0.9`→`0.85` | `server/tts/tts_service.py`, `server/tts/realtime_tts.py` |
| **`TTS_PREWARM_LIMIT`** | int | 선택 | `30` | **2026-07-13 신규.** 서버 기동 시 DB(`detection_guidance_logs`) 이력에서 빈도 높은 안내 문장을 뽑아 `RealtimeTTS` 캐시를 미리 채우는 프리워밍 대상 건수. `RealtimeTTS.CACHE_MAX_ENTRIES`(64)를 넘으면 FIFO 축출로 앞쪽이 밀려나므로 이내로 권장 | `server/main.py`(lifespan), `server/tts/realtime_tts.py` |
| **`TTS_PREWARM_MIN_COUNT`** | int | 선택 | `2` | **2026-07-13 신규.** 프리워밍 대상으로 뽑을 문장의 최소 등장 횟수(1회성 문장 제외) | `server/db/repositories.py`(`list_frequent_tts_texts`) |

> **TTS 엔진 선택 이력**: piper → **supertonic(최종 선정, 2026-07-09 코드 반영 완료)**. 현재 코드 런타임(`get_tts_service()`)은 `supertonic`(기본)·`piper`·`pyttsx3` 3종 모두 구현되어 있으며, 미지원 값 입력 시 경고 로그 후 `supertonic`으로 강제 폴백합니다.

### 2.8 데이터 경로 (4단계 RAG 빌드·7단계 반사 클립)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DATA_RAW`** | path | 필수 | `data/raw` | AI Hub 보행자 데이터셋 원본 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_FRAMES`** | path | 필수 | `data/frames` | 1fps 추출 프레임 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_DEDUPED`** | path | 필수 | `data/deduped` | pHash 중복 제거 후 프레임 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_CAPTIONS`** | path | 필수 | `data/captions` | 캡셔닝 결과 JSON (Llava 또는 Gemini API 사용에 따라 동일 경로에 저장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_REFLEX_CLIPS`** | path | 미사용(폐기) | `data/reflex_clips` | **2026-07-09 정정**: 코드 어디서도 소비되지 않는 죽은 변수. 반사 음성 클립은 서버 `data/`가 아니라 단말 번들(`client/assets/sounds/reflex_clips/`, WAV 5종)로 실제 구현됨 | [`reflex_audio_specification.md`](../design/reflex_audio_specification.md) §4 |
| **`EVENT_FRAMES_DIR`** | path | 선택 | `data/event_frames` | 이벤트 프레임 이미지 저장소 루트(2026-07-12 신설). 탐지/안내 로그 적재 이벤트의 발생 시점 프레임 JPEG을 날짜 폴더로 보관 | `server/services/event_frame_store.py`, [`api_specification.md`](../design/api_specification.md) §8.5 |
| **`EVENT_FRAME_RETENTION_DAYS`** | int | 선택 | `7` | 이벤트 프레임 보존 기간(일). 초과 날짜 폴더는 정리 주기마다 삭제(2026-07-20 이전: 서버 기동 시 1회만). `0` 이하는 정리 비활성. 보행 중 촬영 이미지는 개인정보 포함 가능성으로 기간 한정 보존 | `server/services/event_frame_store.py` |
| **`EVENT_FRAME_CLEANUP_INTERVAL_S`** | int | 선택 | `21600` | **2026-07-20 신규.** 이벤트 프레임 보존 정리 반복 주기(초, 기본 6시간). 기존에는 기동 시 1회만 정리해 재시작 없이 장기간 구동하면 보존 기간 초과 폴더가 전혀 정리되지 않았음(실기기 장시간 테스트 피드백) | `server/main.py` |
| **`EVENT_FRAME_JPEG_QUALITY`** | int | 선택 | `80` | 이벤트 프레임 JPEG 품질(용량 통제 우선) | `server/services/event_frame_store.py` |
| **`EVENT_FRAME_STORAGE_BACKEND`** | string | 선택 | `local` | 이벤트 프레임/STT 원본 음성 파일 저장 백엔드. `local`이면 기존 GPU 서버 로컬 디스크, `remote`이면 Raspberry Pi 중앙 저장 API에 업로드. 구 명칭 `EVENT_FRAME_BACKEND`도 코드에서 폴백 지원 | `server/services/event_frame_store.py`, `server/services/remote_storage_client.py` |
| **`IMAGE_SERVER_BASE_URL`** | string | 선택(원격 저장 사용 시 필수) | (미설정) | Raspberry Pi 중앙 저장 API 기본 URL. 예: `http://100.x.x.x:8081`. 구 명칭 `EVENT_FRAME_REMOTE_URL`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`IMAGE_SERVER_TOKEN`** | string | 선택(원격 저장 사용 시 필수) | (미설정) | 중앙 저장 API Bearer 토큰. 서버 `.env`에만 저장하며 클라이언트/콘솔 공개 변수에 넣지 않습니다. 구 명칭 `EVENT_FRAME_REMOTE_TOKEN`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`IMAGE_UPLOAD_TIMEOUT_SECONDS`** | float | 선택 | `3` | 중앙 저장 API 업로드/조회 HTTP 타임아웃(초). 구 명칭 `EVENT_FRAME_UPLOAD_TIMEOUT_SEC`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`IMAGE_UPLOAD_MAX_RETRIES`** | int | 선택 | `1` | 중앙 저장 API 업로드 재시도 횟수. 5xx/네트워크/타임아웃 계열만 짧게 재시도합니다. 구 명칭 `EVENT_FRAME_UPLOAD_RETRIES`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`WRITER_INSTANCE_ID`** | string | 선택 | `HOSTNAME` 폴백 | 다중 FastAPI writer 식별자. `detection_guidance_logs.writer_instance_id`에 저장되어 어떤 서버가 로그를 썼는지 추적합니다 | `server/services/detection_guidance_log_service.py` |

### 2.9 Slack Integration (공통 경보)

Slack 경보는 **2개 독립 구현체**가 존재하며, 각각 다른 인증 방식을 사용합니다.

**구현체 A: `server/mcp/slack_notifier.py` (서버 런타임 MCP)** — Webhook 우선 / Bot Token 폴백 이중 인증:

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SLACK_WEBHOOK_URL`** | string | 선택 | (미설정) | Slack Incoming Webhook URL. **설정 시 최우선 순위**로 사용(`send_notification_sync` L59 `if self.webhook_url:` 분기). 미설정 시 Bot Token 경로로 폴백 | `server/mcp/slack_notifier.py:49,59` |
| **`SLACK_BOT_TOKEN`** | string | 선택 | (미설정) | Slack Web API Bot Token. Webhook 미설정 시 폴백 순위 2로 사용(`elif self.bot_token and self.channel_id:` L80 분기) | `server/mcp/slack_notifier.py:51,80`, `scripts/slack_publisher.py:52` |
| **`SLACK_CHANNEL_ID`** | string | 선택 | `C0BCZSB5TJS`(코드 내 폴백값) | 경보 발송 대상 채널 ID. Bot Token 방식 사용 시 필수 | `server/mcp/slack_notifier.py:52`, `scripts/slack_publisher.py:193` |

> **2026-07-14 정정**: 이전 명세(v0.4.17)는 "2026-07-07 재정정: `SLACK_WEBHOOK_URL`은 코드 어디에도 쓰이지 않는 미사용 변수"라고 단언했으나, **코드 재검증 결과 부정확**함이 확인됨. `server/mcp/slack_notifier.py:49`에서 `os.getenv("SLACK_WEBHOOK_URL")`로 로드하며 L59에서 **최우선 분기**로 활성 사용 중. 두 인증 방식(Webhook/Bot Token)은 `scripts/slack_publisher.py`(Bot Token 전용)와 `server/mcp/slack_notifier.py`(Webhook 우선/Bot Token 폴백)로 구현체가 분리되어 있으며, 본 명세서는 두 구현체 모두를 코드 기준으로 반영함.

### 2.10 LangSmith Trace (선택적 관측)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LANGCHAIN_API_KEY`** | string | 선택 | (미설정) | LangSmith Platform API 키. 실제 API Key 기입 시 Mocking 폴백이 해제되고 실제 SaaS 플랫폼 트레이싱 및 가드레일이 정상 작동합니다. | [`architecture.md`](architecture.md) 13.4절 |
| **`LANGCHAIN_TRACING_V2`** | bool | 선택 | `false` | LangSmith Tracing v2 활성화 여부 (`true` 시 추적 시작) | [`architecture.md`](architecture.md) 13.4절 |

> **선택적 명세**: LangSmith Trace MCP는 `architecture.md` 13.4절에서 "선택적으로 기입"으로 명시되어 있으며, 미설정 시 6단계 LangGraph 동작에는 영향을 주지 않습니다.

### 2.11 GPU 모니터링 Mock (개발·테스트 전용)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MOCK_GPU_USAGE_PCT`** | float | 선택 | `30.0` | Mock GPU 사용률 (%). CUDA 미감지 환경에서 핫스왑 트리거 테스트용 | [`server/mcp/gpu_monitor.py`](../server/mcp/gpu_monitor.py) |
| **`MOCK_GPU_MEM_USED_MB`** | float | 선택 | `2048.0` | Mock GPU 메모리 사용량 (MB). CUDA 미감지 환경에서 핫스왑 트리거 테스트용 | [`server/mcp/gpu_monitor.py`](../server/mcp/gpu_monitor.py) |

> **개발 전용**: 이 변수들은 CUDA GPU가 감지되지 않은 개발·CI 환경에서 `GPUMonitorMCP`의 Mock 폴백 동작을 제어합니다. 프로덕션 환경에서는 무시됩니다.

### 2.12 외부망 연결 (Tailscale, 야외 도로 테스트용)

**2026-07-13 변경**: 기존 공인 프록시를 Tailscale P2P VPN으로 전면 교체하고, 서버 측 인증 토큰 변수와 Docker 터널 서비스를 제거했다. 클라이언트 접속 방식은 `EXPO_PUBLIC_NETWORK_MODE=tailscale` + `EXPO_PUBLIC_TAILSCALE_HOST` 조합을 팀 표준으로 채택했다. 실기기는 `client/.env`에 개발 PC의 MagicDNS 이름을 설정해 WiFi/LTE/핫스팟 어디서든 동일하게 접속한다. 서버 측 별도 터널 환경변수는 필요하지 않다.

**2026-07-19 보안 정리**: 사용하지 않는 외부 터널 클라이언트 패키지와 바이너리 의존성, 클라이언트 네트워크 모드·도메인 환경변수 폴백을 제거했다. 외부망 연결은 Tailscale만 지원한다.

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MINCHODAN_EXPOSE_OLLAMA`** | bool | 선택 | `false` | Linux Docker 스타트업 스크립트가 호스트 로컬 Ollama(11434)를 외부망(Tailscale)에 노출할지 여부. `true`일 때만 Tailscale IP 바인딩 허용 | `docker/linux_docker_start.sh`, [`deployment_guide.md`](deployment_guide.md) |

**2026-07-19 보강 (iOS 네이티브 Metro)**: LTE/Tailscale에서 Expo Dev Launcher가 Bonjour로 Metro를 못 찾을 때 로컬 Xcode 환경의 `METRO_BUNDLER_HOST`에 개인 개발 PC의 MagicDNS 이름 또는 주소를 지정한다. 저장소 소스·공유 스킴·Info.plist에는 개인 주소 폴백을 두지 않는다. 서버 API 호스트(`EXPO_PUBLIC_TAILSCALE_HOST`)와 Metro 호스트는 역할이 다르므로 각각 설정한다.

> **팀 운영 규칙**: 개인 개발 Mac 주소는 Git 추적 파일에 기록하지 않고 로컬 Xcode 환경에서만 설정한다.
>
> | 대상 | 덮어쓰기 방법 |
> | :--- | :--- |
> | Metro JS 번들 (재빌드 최소) | Xcode 스킴 `METRO_BUNDLER_HOST=<본인_Tailscale_IP>:8081` 또는 프로세스 env |
> | Dev Launcher 기본 URL | 저장소에 고정하지 않으며 Expo Dev Launcher에서 로컬 세션을 선택 |
> | FastAPI/WS 서버 | `client/.env`의 `EXPO_PUBLIC_TAILSCALE_HOST=<서버_MagicDNS_이름>`, `EXPO_PUBLIC_SERVER_PORT=443`, `EXPO_PUBLIC_WS_SCHEME=wss` (gitignore, 커밋 금지) |
>
> MagicDNS 이름 확인: `tailscale status --json | jq -r '.Self.DNSName'`. `wss` 인증서 검증을 위해 FastAPI/WS 주소에는 Tailscale IP가 아닌 MagicDNS 이름을 사용한다.

### 2.13 데이터베이스 (MariaDB)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DB_TYPE`** | string | 선택 | `mariadb` | RDB 연결 유형. 현재 세션 SQL은 MariaDB 기준이며, ORM 검증용 DDL은 SQLite 파일로 별도 제공합니다. | [`Minchodan DB.session.sql`](../../Minchodan%20DB.session.sql), [`server/db/schema.sql`](../../server/db/schema.sql) |
| **`DB_HOST`** | string | 필수 | `[IP_ADDRESS]` | MariaDB 서버 호스트 또는 IP 주소 | [`Minchodan DB.session.sql`](../../Minchodan%20DB.session.sql) |
| **`DB_PORT`** | int | 필수 | `3306` | MariaDB 서버 포트 | [`Minchodan DB.session.sql`](../../Minchodan%20DB.session.sql) |
| **`DB_NAME`** | string | 필수 | `minchodan_db` | 현재 확정된 대상 데이터베이스명. 과거 초안의 `minchodan_tmp`, `minchodan_app` 대신 이 값을 사용합니다. | [`Minchodan DB.session.sql`](../../Minchodan%20DB.session.sql) |
| **`DB_USER`** | string | 필수 | `minchodan_team` | 애플리케이션 또는 DBeaver 세션에서 사용할 DB 계정명 | [`.env.example`](../../.env.example) |
| **`DB_PASSWORD`** | string | 필수 | `[your_password]` | DB 계정 비밀번호. 실제 값은 `.env`에만 저장합니다. | [`.env.example`](../../.env.example) |
| **`COMPOSE_DB_NAME`** | string | 선택 | `minchodan_db` | Docker Compose 로컬 MariaDB 컨테이너 전용 DB 이름. 원격 DB용 `DB_NAME`과 분리합니다. | [`docker/docker-compose.macos.yml`](../../docker/docker-compose.macos.yml), [`docker/docker-compose.yml`](../../docker/docker-compose.yml) |
| **`COMPOSE_DB_USER`** | string | 선택 | `minchodan_team` | Docker Compose 로컬 MariaDB 컨테이너 전용 앱 계정명. FastAPI 컨테이너에도 같은 값으로 오버라이드됩니다. | [`docker/docker-compose.macos.yml`](../../docker/docker-compose.macos.yml), [`docker/docker-compose.yml`](../../docker/docker-compose.yml) |
| **`COMPOSE_DB_PASSWORD`** | string | 선택 | `minchodan_password` | Docker Compose 로컬 MariaDB 컨테이너 전용 앱 계정 비밀번호. 실제 배포 값과 분리해 `.env`에서 교체할 수 있습니다. | [`.env.example`](../../.env.example) |
| **`COMPOSE_DB_ROOT_PASSWORD`** | string | 선택 | `minchodan_root_password` | Docker Compose 로컬 MariaDB 컨테이너의 root 계정 비밀번호. 실제 배포 값과 분리해 `.env`에서 교체할 수 있습니다. | [`.env.example`](../../.env.example) |
| **`COMPOSE_DB_HOST`** | string | 선택 | (`DB_HOST`, 미설정 시 `mariadb`) | FastAPI 컨테이너의 DB 호스트만 명시적으로 재정의합니다. 미설정 시 기존 원격 `DB_HOST`를 유지합니다. | [`docker/docker-compose.macos.yml`](../../docker/docker-compose.macos.yml), [`docker/docker-compose.yml`](../../docker/docker-compose.yml) |
| **`DB_HOST_PORT`** | int | 선택 | `3306` | Docker Compose 로컬 MariaDB 컨테이너를 호스트로 노출할 포트. FastAPI의 실제 DB 대상은 `COMPOSE_DB_HOST` 또는 `DB_HOST`가 결정합니다. **2026-07-18 정정**: 공유 GPU 서버의 로컬 3306 포트 충돌을 피하기 위해 `docker/docker-compose.yml`의 `mariadb` 서비스 `ports` 노출을 주석 처리함(원격 DB 기본 연결 유지) — 이 변수는 현재 `docker-compose.macos.yml`에만 적용됨. | [`docker/docker-compose.macos.yml`](../../docker/docker-compose.macos.yml) |
| **`NETWORK_ENV_FILE`** | path | 선택 | `../.env` | FastAPI 컨테이너에 추가로 주입할 Raspberry Pi 네트워크 프로필 경로입니다. `demo`는 내부망, `test`는 Tailscale 경로이며 `scripts/switch_rpi_network.sh`가 OS별 Compose와 macOS DB 프록시를 함께 전환합니다. Compose 파일 기준 상대경로를 사용합니다. | `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `scripts/switch_rpi_network.sh` |

네트워크 프로필 파일은 Git에서 제외되는 로컬 설정입니다. 공통 비밀번호와 토큰은 루트 `.env`에 한 번만 보관하고, 프로필에는 아래 비밀이 아닌 대상값만 둡니다.

| 프로필 | 로컬 파일 | 필수 키 | 용도 |
| :--- | :--- | :--- | :--- |
| **시연** | `.env.network.demo` | `NETWORK_ENV_FILE`, `DB_HOST`, `DB_PORT`, `IMAGE_SERVER_BASE_URL` | Raspberry Pi 내부망 경로 |
| **테스트** | `.env.network.test` | `NETWORK_ENV_FILE`, `DB_HOST`, `DB_PORT`, `IMAGE_SERVER_BASE_URL` | Raspberry Pi Tailscale 경로 |

### 2.14 내비게이션 (GPS 경로 안내, 2026-07-10 신설)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TMAP_APP_KEY`** | string | 필수(내비게이션 사용 시) | `YOUR_TMAP_APP_KEY_HERE`(코드 내 플레이스홀더) | TMAP POI 검색·보행자 경로 안내 API 키. 미설정 또는 플레이스홀더 그대로일 경우 콘솔 경고와 함께 기능 비활성화. **2026-07-11 용도 확장**: 단말 하단 T맵 지도 패널(WebView + TMap JS API)용으로 `nav_route` WS 메시지의 `app_key` 필드에 실어 전달. 클라이언트 하드코딩을 피해 저장소에 키가 남지 않으나 앱 런타임에는 노출되므로 **TMap 콘솔에서 키 사용 제한 설정 권장**. **2026-07-13 해결**: `.env.example`에 추가 완료(정합성 검토 P0). **2026-07-18 정정**: 프로토타입 `pedestrian_navigation.py`가 삭제되어 TMAP 연동은 `server/navigation/server.py`에서 담당 | `server/navigation/server.py:38`, `server/api/ws_router.py` |

### 2.15 클라이언트·콘솔 공개 변수 (빌드 시 인라인, 2026-07-11 신설)

> **주의**: `EXPO_PUBLIC_*`(단말 앱)과 `VITE_*`(운영 콘솔)는 빌드 산출물에 **평문 포함**되는 공개 변수입니다. 비밀키를 넣지 않습니다. 서버 `.env`가 아니라 각 앱 디렉토리의 환경 파일(`client/.env`, `console/.env`)에서 관리합니다.

| 변수명 | 타입 | 필수/선택 | 기본값(코드 폴백) | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`EXPO_PUBLIC_NETWORK_MODE`** | string | 선택 | `tailscale` | 단말 접속 모드(`lan`/`tailscale`). `tailscale`이면 WiFi/USB 토글보다 외부망 주소 우선 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_WIFI_HOST`** | string | LAN 사용 시 필수 | 없음 | **평상시 WiFi 모드** PC 호스트. 소스 코드에는 개인·공용 IP 폴백을 두지 않음 | `client/src/config/index.ts`, [android_wifi_usb_transport.md](android_wifi_usb_transport.md) |
| **`EXPO_PUBLIC_LAN_IP`** | string | 선택 | (WIFI_HOST 폴백) | 구 명칭. 설정 시 `WIFI_HOST`가 없으면 이 값을 WiFi 호스트로 사용 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_USB_HOST`** | string | 선택 | `127.0.0.1` | **개발 USB 모드** + `adb reverse` 호스트 | `client/src/config/index.ts`, [android_wifi_usb_transport.md](android_wifi_usb_transport.md) |
| **`METRO_BUNDLER_HOST`** | string | 선택 | 없음 | **iOS 네이티브 전용** Debug Metro 호스트. 개인 MagicDNS/주소는 로컬 Xcode 환경에만 설정하고 공유 스킴에 저장하지 않음 | `client/ios/Minchodan/AppDelegate.swift` |
| **`EXPO_PUBLIC_TAILSCALE_HOST`** | string | Tailscale 사용 시 필수 | 없음 | **외부망 Tailscale 모드** FastAPI/WS MagicDNS 호스트. `wss` 인증서 검증을 위해 Tailscale IP를 사용하지 않음 | `client/src/config/index.ts`, `client/.env.example` |
| **`EXPO_PUBLIC_SERVER_PORT`** | string | 선택 | `8000` | 단말이 접속할 FastAPI/WebSocket 포트. Tailscale Serve의 `wss` 종단은 `443`, 로컬 직접 연결은 기본 `8000` 사용 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_WS_SCHEME`** | string | 선택 | `wss` | WebSocket 스킴. iOS ATS를 전역 허용하지 않으므로 Tailscale Serve 등 TLS 종단을 사용. USB 루프백만 `ws` 허용 | `client/src/config/index.ts`, `client/ios/Minchodan/Info.plist` |
| **`EXPO_PUBLIC_DEFAULT_TRANSPORT`** | string | 선택 | `wifi` | 앱 최초 기동 기본 수송(`wifi`/`usb`). 이후 선택은 단말에 영속 | `client/src/config/index.ts`, `client/src/services/serverTransport.ts` |
| **`EXPO_PUBLIC_NETWORK_BENCHMARK`** | string | 선택 | `false` | `true`이면 iOS/Android 앱이 `network_probe`를 주기적으로 보내 최신 RTT와 최근 30개 평균을 디버그 정보에 표시 | `client/src/config/index.ts`, `client/src/hooks/useWebSocket.ts` |
| **`EXPO_PUBLIC_NETWORK_BENCHMARK_INTERVAL_MS`** | int | 선택 | `1000` | 앱 내 `network_probe` 전송 간격(ms) | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_NETWORK_BENCHMARK_PAYLOAD_BYTES`** | int | 선택 | `256` | 앱 내 `network_probe` 페이로드 크기(bytes). 작은 고정값으로 순수 WS 왕복 지연을 비교 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_DEVICE_ID`** | string | 필수 | 없음 | 단말 식별자. 소스 기본값 없음 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_DEVICE_TOKEN`** | string | 필수 | 없음 | 단말 JWT 또는 명시 허용된 개발 정적 토큰. 공개 빌드 변수이므로 운영 장기 토큰 저장소로 사용하지 않음 | `client/src/config/index.ts`, `server/api/auth.py` |
| **`VITE_MONITOR_STREAM_URL`** | string | 선택 | `http://localhost:8000/api/v1/monitor/stream` | 콘솔 SSE 스트림 주소 | `console/src/api/useMonitorStream.ts`, `console/.env.example` |
| **`VITE_ENABLE_DEMO_DATA`** | string | 선택 | `false` | 콘솔 데모 데이터 주입(개발 빌드 전용, api_specification §8.4) | `console/src/App.tsx` |
| **`VITE_NAV_MAP_URL`** | string | 선택 | `http://localhost:8000/navigation/?embed=true` | 관제 지도 iframe 주소(2026-07-11 신설) | `console/src/components/OperatorLiveMap.tsx` |
| **`VITE_API_BASE_URL`** | string | 선택 | `http://localhost:8000` | 콘솔 REST API 기본 주소(2026-07-12 신설). 사후 이력 로그 조회·이벤트 프레임 이미지 서빙에 사용 | `console/src/api/useDetectionLogs.ts`, api_specification §8.5 |

### 2.16 코드 실사용 미등재 변수 (2026-07-14 일괄 명세)

> **2026-07-14 정합성 검토**: 코드(`os.getenv`)에서 활성 사용 중이나 기존 명세(§2.1~2.14)에 누락되어 있던 변수들을 일괄 등재합니다. 대부분은 고급 튜닝·내부 분기용 선택 변수이므로 기본값 미설정 시 안전 폴백합니다.

| 변수명 | 타입 | 필수/선택 | 기본값(코드) | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CONVENIENCE_CHROMA_COLLECTION`** | string | 선택 | `convenience_guide` | 생활지원 RAG 전용 ChromaDB 컬렉션명. 안전 수칙(`safety_guidelines`)과 분리된 생활 정보 검색용 | `server/rag/retriever.py`, `scripts/` |
| **`CONVENIENCE_CHROMA_PATH`** | path | 선택 | `data/chroma_db/convenience_guidelines` | 생활지원 RAG 전용 ChromaDB persist 디렉토리. `.env.example`에 명시됨 | `server/rag/convenience_rag.py:397,597`, `scripts/build_convenience_db.py:33` |
| **`CONVENIENCE_EMBEDDING_MODEL`** | string | 선택 | (`EMBEDDING_MODEL` 폴백) | 생활지원 RAG 전용 임베딩 모델 | `server/rag/embedding_engine_factory.py` |
| **`CONVENIENCE_EMBEDDING_PROVIDER`** | string | 선택 | (`LLM_PROVIDER` 폴백) | 생활지원 RAG 임베딩 공급자(`ollama`/`openai`) | `server/rag/embedding_engine_factory.py` |
| **`CONVENIENCE_LLM_PROVIDER`** | string | 선택 | `ollama` | 생활지원 RAG **답변** LLM. `ollama`(기본, 실패 시 Gemini 폴백) / `gemini`(API 우선) / `ollama_only` / `gemini_only` | `server/rag/convenience_rag.py` |
| **`GEMINI_MODEL`** | string | 선택 | `gemini-2.5-flash-lite` | Gemini 캡셔닝/LLM 모델명. 4단계 RAG 빌드 및 L2 가이드 생성(gemini provider) 시 사용 | `server/rag/build/gemini_captioner.py`, `server/orchestration/llm_client_factory.py` |
| **`GEMINI_MAX_OUTPUT_TOKENS`** | int | 선택 | `180` | Gemini `maxOutputTokens`(생성 길이 상한, 입력 컨텍스트 아님). 음성 안내가 중간에 끊기지 않도록 짧게 유지 | `server/orchestration/llm_client_factory.py` |
| **`EDGE_TTS_SAMPLE_RATE`** | int | 선택 | `22050` | **2026-07-20 정정**(기존 24000): `server/tts/tts_service.py:481` 코드 기본값은 `22050`Hz. edge-tts 출력 샘플레이트 | `server/tts/tts_service.py:481` |
| **`SUPERTONIC_SPEED_MIN`** / **`SUPERTONIC_SPEED_MAX`** | float | 선택 | (코드 기본값) | Supertonic 발화 속도 허용 범위 | `server/tts/tts_service.py` |
| **`DATABASE_URL`** | string | 선택 | (미설정) | SQLAlchemy 통합 DB 연결 URL. 설정 시 개별 `DB_HOST`/`DB_PORT`/... 조합보다 우선 | `server/db/connection.py` |
| **`LANGCHAIN_PROJECT`** | string | 선택 | `minchodan` | LangSmith 트레이스 프로젝트명 | `server/mcp/langsmith_tracer.py` |
| **`STT_MAX_CONCURRENT_REQUESTS`** | int | 선택 | `2` | STT 동시 처리 요청 상한. 메모리 보호용 세마포어 | `server/api/ws_router.py:65`, `server/api/stt_router.py:26` |
| **`STT_UPLOAD_MAX_BYTES`** | int | 선택 | `10485760` | STT 오디오 업로드 최대 바이트(10MB). §8.5 STT 음성 저장 계약과 연관 | `server/api/ws_router.py:63`, `server/api/stt_router.py:84` |
| **`STT_CONFIG_SOURCE`** | string | 선택 | (코드 기본값) | STT 설정 소스 분기 | `server/stt/stt_config.py` |
| **`TEST_VERIFY_MODE`** | bool | 선택 | `false` | 검증 테스트 모드 활성화(오프라인 검증 스크립트용) | `server/` |
| **`DEVICE_TOKEN`** | string | 선택 | (미설정) | 디바이스 토큰(`scripts/` 유틸리티 스크립트 전용) | `scripts/` |
| **`AIHUB_WALK_DATASET_ROOT`** | path | 선택 | (미설정) | AIHub 인도보행 영상 데이터셋 루트 경로(RAG 빌드 스크립트용) | `scripts/` |
| **`SEG_COMPARE_DIR`** | path | 선택(디버그) | `/app/data/seg_compare` | 세그멘테이션 비교 디버그 덤프 디렉토리 | `server/api/ws_router.py:988` |
| **`SEG_COMPARE_DUMP`** | int | 선택(디버그) | `40` | 세그멘테이션 비교 덤프 잔여 프레임 수. `0`이면 덤프 비활성. 양수면 해당 프레임 수만큼 JPEG를 `SEG_COMPARE_DIR`에 저장 후 자동 종료 | `server/api/ws_router.py:998` |
| **`SEG_COMPARE_MIN_BYTES`** | int | 선택(디버그) | `20000` | 세그멘테이션 비교 덤프 최소 바이트 | `server/api/ws_router.py:998` |

> **참고**: 이 변수들은 `.env.example`에 주석 처리 또는 미기재 상태일 수 있으며, 고급 사용자만 설정하는 튜닝 포인트입니다. 프로젝트 기동에는 영향을 주지 않습니다.

---

## 3. 환경 변수 로드 패턴

모든 Python 모듈은 [`docs/dev-guides/course_codebase_guide.md`](dev-guides/course_codebase_guide.md) 3.4절의 표준 패턴을 준수합니다.

```python
from dotenv import load_dotenv
import os

# __file__ 기반 경로 계산 (guide 3.3)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(root_dir, ".env")

# .env 로드 (guide 3.4)
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# 환경 변수 읽기 (기본값 포함, 방어적 코딩 guide 17.2)
llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
```

---

## 4. 불일치 해소 이력

본 명세서 작성 전 다음 3곳에서 환경 변수가 중복 관리되고 있었습니다. 2026-06-27 기준으로 본 명세서가 단일 기준이 됩니다.

| 이전 출처 | 상태 | 비고 |
| :--- | :--- | :--- |
| [`.env.example`](../.env.example) | **본 명세서 기준** | 가장 풍부한 변수 집합. Slack 인증은 실제 코드(`scripts/slack_publisher.py`) 기준 `SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID` 유지(2026-07-07 정정, §2.8 참조) |
| [`architecture.md`](architecture.md) 10절 | 본 명세서 참조로 정합 | `OPENAI_API_KEY` 누락 보충, 중복 행 제거 |
| 루트 [`README.md`](../README.md) 환경변수 표 | 본 명세서 참조로 정합 | `WS_HOST`, `DETECTOR_TYPE`, `YOLO26N_*`, `DATA_*`, `SLACK_*` 누락 보충 |

### 4.1 해소된 주요 불일치

| # | 항목 | 이전 상태 | 해소 후 |
| :--- | :--- | :--- | :--- |
| 1 | **Slack 인증 방식** | `.env.example`(`SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID`) vs `architecture.md` 13.4절(`SLACK_WEBHOOK_URL`) | 2026-07-14 코드 기준 확정: `server/mcp/slack_notifier.py`는 `SLACK_WEBHOOK_URL`(우선)+`SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID`(폴백) 이중 인증 구조. `scripts/slack_publisher.py`는 `SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID` 전용. 두 구현체를 §2.8에 통합 명세 |
| 2 | **`WS_HOST` 누락** | `.env.example`에만 존재, `architecture.md`·`README.md`에는 누락 | 본 명세서 2.4절에 통합 |
| 3 | **`DETECTOR_TYPE` 누락** | `.env.example`에만 존재 | 본 명세서 2.5절에 통합 |
| 4 | **`DATA_*` 경로 누락** | `.env.example`에만 존재 (5종) | 본 명세서 2.7절에 통합 |
| 5 | **`MOCK_GPU_*` 누락** | 어디에도 문서화되지 않음 (코드에만 존재) | 본 명세서 2.10절에 신규 명세 |
| 6 | **`LANGCHAIN_*` 누락** | `architecture.md` 13.4절에만 산재 | 본 명세서 2.9절에 통합 |
| 7 | **외부 터널 인증 변수 제거** | 사용하지 않는 외부 터널 인증 설정이 과거 문서에 잔존 | 2026-07-19 Tailscale 단일 경로로 정리 |
| 8 | **DB 환경 변수 누락** | `.env.example`에는 `DB_*` 6종이 있으나 본 명세서에는 누락 | 본 명세서 2.12절에 통합하고 `DB_NAME=minchodan_db` 기준으로 정합 |
| 9 | **`TMAP_APP_KEY` 누락** | 코드(`server/navigation/`)에서 실사용되나 본 명세서·`.env.example` 모두 누락 | 본 명세서 2.13절에 신규 명세. **2026-07-13**: `.env.example` 반영 완료 |

---

## 5. 보안 주의사항

| 항목 | 지침 |
| :--- | :--- |
| **`.env` 파일** | 절대 Git에 커밋하지 마십시오. `.gitignore`에 `.env` 패턴이 등록되어 있습니다. |
| **`OPENAI_API_KEY`** | OpenAI API Platform에서 발급. 키 유출 시 즉시 회전하십시오. |
| **`SLACK_BOT_TOKEN`** | Slack App 설정에서 Bot Token 발급. 키 유출 시 즉시 회전하십시오. |
| **`LANGCHAIN_API_KEY`** | LangSmith Platform에서 발급. 선택적 변수이므로 미설정해도 동작에 영향 없습니다. |
| **`DB_PASSWORD`** | 실제 DB 비밀번호는 `.env`에만 저장하고 문서, 커밋, 채팅 로그에 노출하지 않습니다. |

---

## 6. 검증 체크리스트

환경 변수 설정 완료 후 아래 항목을 점검합니다.

| # | 검증 항목 | 명령 | 기대 결과 |
| :--- | :--- | :--- | :--- |
| 1 | .env 파일 존재 | `Test-Path .env` (Windows) / `test -f .env` (Linux) | `True` |
| 2 | 필수 변수 누락 여부 | `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('LLM_PROVIDER'))"` | `ollama` |
| 3 | Redis 연결 | `redis-cli ping` | `PONG` |
| 4 | Ollama 연결 | `curl $OLLAMA_BASE_URL/api/tags` | 모델 목록 JSON |
| 5 | Docker 컨테이너의 호스트 Ollama 연결 | `docker exec minchodan-fastapi curl -fsS http://host.docker.internal:11434/api/tags` | 모델 목록 JSON |
| 6 | 가중치 파일 존재 | `Test-Path server/models/yolo26n/det_best_20260705.pt` | `True` |
| 7 | ChromaDB 경로 존재 | `Test-Path data/chroma_db` | `True` (4단계 빌드 후) |
| 8 | DB 대상명 확인 | `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('DB_NAME'))"` | `minchodan_db` |
