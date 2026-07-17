# Minchodan 환경 변수 명세서

> **작성일**: 2026-06-27
> **수정일**: 2026-07-16
> **버전**: v0.4.19 (2026-07-16 §2.7 중앙 저장 API 환경 변수 6종 추가 — 이벤트 프레임과 STT 원본 음성 파일을 Raspberry Pi 저장 API로 업로드하고 Log 테이블에는 object key만 남기는 구조 반영. 기존 v0.4.18 이력 유지: §2.8 `SLACK_WEBHOOK_URL` 코드 재검증 기반 재등재, §2.15 미등재 변수 13종 일괄 명세)
> **기준 파일**: [`.env.example`](../../.env.example) (단일 기준)
> **설계 기준**: [`docs/design/architecture.md`](../design/architecture.md) 10절·13.4절, [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md)
> **코딩 패턴 기준**: [`docs/dev-guides/course_codebase_guide.md`](../dev-guides/course_codebase_guide.md) 3.4(.env 로드)

---

## 1. 목적

본 문서는 Minchodan 프로젝트의 모든 환경 변수를 단일 명세로 통합하여, 기존 `.env.example`·`architecture.md` 10절·루트 `README.md` 환경변수 표 간의 **3원화 불일치를 해소**합니다. 모든 환경 변수 관련 문서는 본 명세서를 기준으로 참조합니다.

---

## 2. 환경 변수 전체 매트릭스

### 2.1 LLM / Ollama (6단계 오케스트레이션)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LLM_PROVIDER`** | string | 필수 | `ollama` | LLM 공급자 (`ollama` 또는 `openai`). GPU 부하 시 `LLMClientFactory`가 자동 핫스왑 | [`stage6_orchestration_design.md`](stage6_orchestration_design.md) 9.3절 |
| **`OLLAMA_BASE_URL`** | string | 필수 | `http://localhost:11434` | Ollama 서버 주소 | [`architecture.md`](architecture.md) 10절 |
| **`COMPOSE_OLLAMA_BASE_URL`** | string | 선택 | `http://host.docker.internal:11434` | Docker Compose의 FastAPI 컨테이너가 호스트 로컬 Ollama로 접속할 때 `OLLAMA_BASE_URL`로 주입할 주소. macOS Colima에서는 `http://host.lima.internal:11434` 사용 권장 | [`docker/docker-compose.macos.yml`](../../docker/docker-compose.macos.yml), [`docker/docker-compose.yml`](../../docker/docker-compose.yml) |
| **`OLLAMA_HOST`** | string | 선택 | (코드 기본값) | 임베딩 팩토리 전용 Ollama 호스트 (2026-07-07 추가 — `OLLAMA_BASE_URL`과 별개로 존재) | `server/rag/embedding_engine_factory.py:46` |
| **`GEMMA_MODEL`** | string | 필수 | `gemma4:e4b` | L2 가이드 생성 모델 (로컬) | [`stage6_orchestration_design.md`](stage6_orchestration_design.md) 9.3절 |
| **`LLAVA_MODEL`** | string | 선택 | `llava` | 4단계 오프라인 캡셔닝 모델 (Ollama 로컬 경로 사용 시). Gemini 캡셔닝 선택 시 미사용 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`GOOGLE_API_KEY`** | string | 선택 | (미설정) | 4단계 캡셔닝 모델 Gemini API(`gemini-2.5-flash-lite`, `server/rag/build/gemini_captioner.py`) 사용 시 필수. 미설정 시 `ValueError` 발생(Llava 폴백 없음 — 2026-07-07 확인: 실제 캡셔너 구현체는 Gemini뿐). **2026-07-13 해결**: `.env.example`에 추가 완료(정합성 검토 P0) | [`stage4_5_rag_design.md`](stage4_5_rag_design.md) 2.1절 |
| **`EMBEDDING_MODEL`** | string | 필수 | `nomic-embed-text` | 임베딩 모델 (768차원) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`OPENAI_API_KEY`** | string | 선택 | (미설정) | OpenAI 핫스왑 시 필요. 미설정 시 OpenAI 클라이언트 초기화에서 `ValueError` 발생 후 Ollama로 폴백 | [`architecture.md`](architecture.md) 13.4절 |

### 2.2 Vector DB (ChromaDB) (4·5단계 RAG)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CHROMA_PATH`** | path | 필수(설계상) | `data/chroma_db` | ChromaDB persist 디렉토리 (로컬 파일 기반). **2026-07-08 정정**: `server/rag/retriever.py`의 `get_default_retriever()`가 `os.getenv("CHROMA_PATH", "data/chroma_db")`로 읽어 실시간 인지 가이드 파이프라인에 실제 연결됨(이전에는 미소비 상태였음) | [`architecture.md`](architecture.md) 2절 |
| **`CHROMA_COLLECTION`** | string | 필수(설계상) | `safety_guidelines` | ChromaDB 컬렉션명 (보행 수칙 지식베이스). **2026-07-08 정정**: 기존 `.env`/`.env.example` 기본값(`bidding_kb`/`minchodan_kb`)이 실제 저장된 컬렉션명과 달라 RAG 검색이 항상 미적중이었음. 실제 데이터가 적재된 컬렉션명(`safety_guidelines`)으로 정정하고 `get_default_retriever()`에서 소비하도록 연결 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.5절 |

### 2.3 Redis (이벤트 버스·MCP 메트릭)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`REDIS_URL`** | string | 필수 | `redis://localhost:6379` | Redis 연결 URL. Streams(`risk.events`, `mcp:metrics`) 및 컨텍스트 TTL(30초)에 사용 | [`architecture.md`](architecture.md) 2절·13.3절 |

### 2.4 WebSocket 서버 (1단계 통신망)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`WS_HOST`** | string | 필수 | `0.0.0.0` | WebSocket 서버 바인드 호스트 | [`api_specification.md`](api_specification.md) 1절 |
| **`WS_PORT`** | int | 필수 | `8000` | WebSocket 서버 포트 | [`api_specification.md`](api_specification.md) 1절 |
| **`HEARTBEAT_INTERVAL`** | int | 선택 | (코드 기본값) | 하트비트 송신 주기(초). `server/api/config.py` (2026-07-07 추가 — 기존 명세서에 누락돼 있었음) | `server/api/config.py:30` |
| **`HEARTBEAT_TIMEOUT`** | int | 선택 | `15` | 하트비트 미수신 타임아웃(초). 총 유예 시간은 `HEARTBEAT_INTERVAL+HEARTBEAT_TIMEOUT`(기본 20초). **2026-07-10 변경**(기존 5): ngrok 등 공인망 릴레이 경유 시 왕복 지연으로 정상 연결도 오탐 종료되는 문제를 실기기 LTE 테스트로 확인해 상향 | `server/api/config.py:31` |
| **`MAX_RECONNECT_ATTEMPTS`** | int | 선택 | (코드 기본값) | 서버 측 재연결 허용 횟수 | `server/api/config.py:32` |
| **`CORS_ORIGINS`** | JSON 배열 문자열 | 선택 | `["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]` | 운영자 콘솔 CORS 허용 출처. **2026-07-13 개선**: Pydantic Settings 초기화 시 환경변수 `CORS_ORIGINS`의 JSON 포맷 또는 쉼표 구분값으로부터 동적으로 안전하게 파싱 및 바인딩되도록 개선. | `server/api/config.py`, `server/main.py` |
| **`JWT_SECRET_KEY`** | string | 필수(운영) / 선택(개발) | (개발 전용 임시 키) | 관리자/유저·디바이스 JWT 서명 키. **2026-07-11 강화**: `APP_ENV=production`에서 미설정 시 `RuntimeError`로 서버 기동 거부(fail-closed). 개발 환경에서만 임시 키 폴백. `.env.example`에 등재됨 | `server/db/security.py` |
| **`APP_ENV`** | string | 선택 | `development` | 배포 환경 구분(`development`/`production`). **2026-07-11 신설**: `production`이면 (1) `JWT_SECRET_KEY` 필수(기동 거부), (2) `DEVICE_STATIC_TOKENS` 미설정 시 정적 디바이스 토큰 경로 비활성화(JWT만 인정) | `server/db/security.py`, `server/api/auth.py` |
| **`DEVICE_STATIC_TOKENS`** | string | 선택 | (개발 기본 2식) | 정적 디바이스 토큰 목록, `device_id:token` 쉼표 구분(예: `dev-001:token-abc-001,dev-002:token-abc-002`). **2026-07-11 신설**: 코드 하드코딩 딕셔너리를 환경 변수로 분리. 미설정 시 개발 환경은 개발 기본값 폴백(경고 로그), 운영 환경은 빈 목록 | `server/api/auth.py` |

### 2.5 탐지 설정 (3단계 Detection)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`YOLO_CONF`** | float | 필수 | `0.35` | Yolo 26N - **Segmentation** 신뢰도 임계값 (`YoloSegmentor`) | [`stage3_detection_design.md`](../stage-guides/stage3_detection_design.md) 5절 |
| **`YOLO_DET_CONF`** | float | 선택 | `0.50` | Yolo 26N - **Object Detection** 신뢰도 임계값 (`YoloDetector`). `YOLO_CONF`와 별도 | `server/detection/config.py` |
| **`DETECTOR_TYPE`** | string | 선택 | `yolo` | **2026-07-17 정정**: 실측 랩 기본은 `yolo`(가중치 로드). `mock`이면 노트북/데모·CI에서 `MockDetector`/`MockSegmentor`를 강제 사용한다. 미지원 값은 안전 폴백으로 `mock` 처리. `.env.example`과 동일 | `server/detection/config.py` |
| **`FRAME_SIZE`** | int | 필수 | `640` | 프레임 리사이즈 크기 (정방형) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`REFLEX_FPS`** | int | 필수 | `10` | 반사 캡처 목표 fps (8~10fps 권장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`COGNITIVE_FPS`** | int | 필수 | `2` | 인지 캡처 목표 fps (1~2fps 권장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`YOLO26N_OBJECT_DET`** | path | 선택 | `server/models/yolo26n/det_best_20260705.pt` | Yolo 26N - Object Detection 가중치 경로 (Git 추적). **2026-07-08 정정**: `.env` 미설정 시 코드 기본값이 커스텀 학습이 안 된 COCO 스톡 모델(`object_detection.pt`)을 가리키던 결함을 실제 학습 가중치 경로로 수정 | [`stage3_detection_design.md`](stage3_detection_design.md) 12.3절 |
| **`YOLO26N_SEG`** | path | 선택 | `server/models/yolo26n/segbest.pt` | Yolo 26N - Segmentation 가중치 경로 (Git 추적). **2026-07-08 정정**: 위와 동일한 사유로 `segmentation.pt`(스톡) → `segbest.pt`(학습 완료, 4클래스)로 수정 | [`stage3_detection_design.md`](stage3_detection_design.md) 12.3절 |

### 2.6 TTS (7단계 음성 출력)

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

### 2.7 데이터 경로 (4단계 RAG 빌드·7단계 반사 클립)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DATA_RAW`** | path | 필수 | `data/raw` | AI Hub 보행자 데이터셋 원본 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_FRAMES`** | path | 필수 | `data/frames` | 1fps 추출 프레임 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_DEDUPED`** | path | 필수 | `data/deduped` | pHash 중복 제거 후 프레임 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_CAPTIONS`** | path | 필수 | `data/captions` | 캡셔닝 결과 JSON (Llava 또는 Gemini API 사용에 따라 동일 경로에 저장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_REFLEX_CLIPS`** | path | 미사용(폐기) | `data/reflex_clips` | **2026-07-09 정정**: 코드 어디서도 소비되지 않는 죽은 변수. 반사 음성 클립은 서버 `data/`가 아니라 단말 번들(`client/assets/sounds/reflex_clips/`, WAV 5종)로 실제 구현됨 | [`reflex_audio_specification.md`](../design/reflex_audio_specification.md) §4 |
| **`EVENT_FRAMES_DIR`** | path | 선택 | `data/event_frames` | 이벤트 프레임 이미지 저장소 루트(2026-07-12 신설). 탐지/안내 로그 적재 이벤트의 발생 시점 프레임 JPEG을 날짜 폴더로 보관 | `server/services/event_frame_store.py`, [`api_specification.md`](../design/api_specification.md) §8.5 |
| **`EVENT_FRAME_RETENTION_DAYS`** | int | 선택 | `7` | 이벤트 프레임 보존 기간(일). 초과 날짜 폴더는 서버 기동 시 삭제. `0` 이하는 정리 비활성. 보행 중 촬영 이미지는 개인정보 포함 가능성으로 기간 한정 보존 | `server/services/event_frame_store.py` |
| **`EVENT_FRAME_JPEG_QUALITY`** | int | 선택 | `80` | 이벤트 프레임 JPEG 품질(용량 통제 우선) | `server/services/event_frame_store.py` |
| **`EVENT_FRAME_STORAGE_BACKEND`** | string | 선택 | `local` | 이벤트 프레임/STT 원본 음성 파일 저장 백엔드. `local`이면 기존 GPU 서버 로컬 디스크, `remote`이면 Raspberry Pi 중앙 저장 API에 업로드. 구 명칭 `EVENT_FRAME_BACKEND`도 코드에서 폴백 지원 | `server/services/event_frame_store.py`, `server/services/remote_storage_client.py` |
| **`IMAGE_SERVER_BASE_URL`** | string | 선택(원격 저장 사용 시 필수) | (미설정) | Raspberry Pi 중앙 저장 API 기본 URL. 예: `http://100.x.x.x:8081`. 구 명칭 `EVENT_FRAME_REMOTE_URL`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`IMAGE_SERVER_TOKEN`** | string | 선택(원격 저장 사용 시 필수) | (미설정) | 중앙 저장 API Bearer 토큰. 서버 `.env`에만 저장하며 클라이언트/콘솔 공개 변수에 넣지 않습니다. 구 명칭 `EVENT_FRAME_REMOTE_TOKEN`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`IMAGE_UPLOAD_TIMEOUT_SECONDS`** | float | 선택 | `3` | 중앙 저장 API 업로드/조회 HTTP 타임아웃(초). 구 명칭 `EVENT_FRAME_UPLOAD_TIMEOUT_SEC`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`IMAGE_UPLOAD_MAX_RETRIES`** | int | 선택 | `1` | 중앙 저장 API 업로드 재시도 횟수. 5xx/네트워크/타임아웃 계열만 짧게 재시도합니다. 구 명칭 `EVENT_FRAME_UPLOAD_RETRIES`도 코드에서 폴백 지원 | `server/services/remote_storage_client.py` |
| **`WRITER_INSTANCE_ID`** | string | 선택 | `HOSTNAME` 폴백 | 다중 FastAPI writer 식별자. `detection_guidance_logs.writer_instance_id`에 저장되어 어떤 서버가 로그를 썼는지 추적합니다 | `server/services/detection_guidance_log_service.py` |

### 2.8 Slack Integration (공통 경보)

Slack 경보는 **2개 독립 구현체**가 존재하며, 각각 다른 인증 방식을 사용합니다.

**구현체 A: `server/mcp/slack_notifier.py` (서버 런타임 MCP)** — Webhook 우선 / Bot Token 폴백 이중 인증:

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SLACK_WEBHOOK_URL`** | string | 선택 | (미설정) | Slack Incoming Webhook URL. **설정 시 최우선 순위**로 사용(`send_notification_sync` L59 `if self.webhook_url:` 분기). 미설정 시 Bot Token 경로로 폴백 | `server/mcp/slack_notifier.py:49,59` |
| **`SLACK_BOT_TOKEN`** | string | 선택 | (미설정) | Slack Web API Bot Token. Webhook 미설정 시 폴백 순위 2로 사용(`elif self.bot_token and self.channel_id:` L80 분기) | `server/mcp/slack_notifier.py:51,80`, `scripts/slack_publisher.py:52` |
| **`SLACK_CHANNEL_ID`** | string | 선택 | `C0BCZSB5TJS`(코드 내 폴백값) | 경보 발송 대상 채널 ID. Bot Token 방식 사용 시 필수 | `server/mcp/slack_notifier.py:52`, `scripts/slack_publisher.py:193` |

> **2026-07-14 정정**: 이전 명세(v0.4.17)는 "2026-07-07 재정정: `SLACK_WEBHOOK_URL`은 코드 어디에도 쓰이지 않는 미사용 변수"라고 단언했으나, **코드 재검증 결과 부정확**함이 확인됨. `server/mcp/slack_notifier.py:49`에서 `os.getenv("SLACK_WEBHOOK_URL")`로 로드하며 L59에서 **최우선 분기**로 활성 사용 중. 두 인증 방식(Webhook/Bot Token)은 `scripts/slack_publisher.py`(Bot Token 전용)와 `server/mcp/slack_notifier.py`(Webhook 우선/Bot Token 폴백)로 구현체가 분리되어 있으며, 본 명세서는 두 구현체 모두를 코드 기준으로 반영함.

### 2.9 LangSmith Trace (선택적 관측)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LANGCHAIN_API_KEY`** | string | 선택 | (미설정) | LangSmith Platform API 키. 실제 API Key 기입 시 Mocking 폴백이 해제되고 실제 SaaS 플랫폼 트레이싱 및 가드레일이 정상 작동합니다. | [`architecture.md`](architecture.md) 13.4절 |
| **`LANGCHAIN_TRACING_V2`** | bool | 선택 | `false` | LangSmith Tracing v2 활성화 여부 (`true` 시 추적 시작) | [`architecture.md`](architecture.md) 13.4절 |

> **선택적 명세**: LangSmith Trace MCP는 `architecture.md` 13.4절에서 "선택적으로 기입"으로 명시되어 있으며, 미설정 시 6단계 LangGraph 동작에는 영향을 주지 않습니다.

### 2.10 GPU 모니터링 Mock (개발·테스트 전용)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MOCK_GPU_USAGE_PCT`** | float | 선택 | `30.0` | Mock GPU 사용률 (%). CUDA 미감지 환경에서 핫스왑 트리거 테스트용 | [`server/mcp/gpu_monitor.py`](../server/mcp/gpu_monitor.py) |
| **`MOCK_GPU_MEM_USED_MB`** | float | 선택 | `2048.0` | Mock GPU 메모리 사용량 (MB). CUDA 미감지 환경에서 핫스왑 트리거 테스트용 | [`server/mcp/gpu_monitor.py`](../server/mcp/gpu_monitor.py) |

> **개발 전용**: 이 변수들은 CUDA GPU가 감지되지 않은 개발·CI 환경에서 `GPUMonitorMCP`의 Mock 폴백 동작을 제어합니다. 프로덕션 환경에서는 무시됩니다.

### 2.11 외부망 연결 (Tailscale, 야외 도로 테스트용)

**2026-07-13 변경**: ngrok 프록시(클라우드 경유 지연)를 Tailscale P2P VPN으로 전면 교체. `NGROK_AUTHTOKEN` 변수 및 `docker-compose.yml`/`docker-compose.macos.yml`의 `ngrok` 서비스를 완전히 제거했다(서버 인프라 결정 - kb). 클라이언트 접속 방식은 처음엔 기존 `lan` 모드(`EXPO_PUBLIC_LAN_IP`)를 재사용해 구현했으나, jy 브랜치 병합 시 §2.14의 전용 `EXPO_PUBLIC_NETWORK_MODE=tailscale` + `EXPO_PUBLIC_TAILSCALE_HOST` 조합을 팀 표준으로 채택했다(jy가 같은 세션에서 독립적으로 구현, `network_probe` RTT 계측과도 통합됨). 실기기는 `client/.env`에 `EXPO_PUBLIC_NETWORK_MODE=tailscale`, `EXPO_PUBLIC_TAILSCALE_HOST=<개발 PC의 Tailscale IP 또는 MagicDNS 이름>`을 설정해 WiFi/LTE/핫스팟 어디서든 동일하게 접속한다(서버 측 환경변수는 불요 - Tailscale 자체가 OS 레벨 네트워크 인터페이스). 클라이언트 쪽 `NETWORK_MODE=ngrok` 분기와 `@expo/ngrok` 의존성은 폴백으로 코드에 보존되어 있으나, ngrok 도커 인프라 자체는 없으므로 실제로 그 경로를 쓰려면 컨테이너를 별도로 다시 구성해야 한다. 상세: [`docs/changelogs/kb.md`](../changelogs/kb.md), [`docs/changelogs/jy.md`](../changelogs/jy.md) 2026-07-13 항목.

### 2.12 데이터베이스 (MariaDB)

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
| **`DB_HOST_PORT`** | int | 선택 | `3306` | Docker Compose 로컬 MariaDB 컨테이너를 호스트로 노출할 포트. FastAPI 컨테이너 내부 연결은 항상 `mariadb:3306`을 사용합니다. | [`docker/docker-compose.macos.yml`](../../docker/docker-compose.macos.yml), [`docker/docker-compose.yml`](../../docker/docker-compose.yml) |

### 2.13 내비게이션 (GPS 경로 안내, 2026-07-10 신설)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TMAP_APP_KEY`** | string | 필수(내비게이션 사용 시) | `YOUR_TMAP_APP_KEY_HERE`(코드 내 플레이스홀더) | TMAP POI 검색·보행자 경로 안내 API 키. 미설정 또는 플레이스홀더 그대로일 경우 콘솔 경고와 함께 기능 비활성화. **2026-07-11 용도 확장**: 단말 하단 T맵 지도 패널(WebView + TMap JS API)용으로 `nav_route` WS 메시지의 `app_key` 필드에 실어 전달. 클라이언트 하드코딩을 피해 저장소에 키가 남지 않으나 앱 런타임에는 노출되므로 **TMap 콘솔에서 키 사용 제한 설정 권장**. **2026-07-13 해결**: `.env.example`에 추가 완료(정합성 검토 P0) | `server/navigation/pedestrian_navigation.py:269`, `server/navigation/server.py:38`, `server/api/ws_router.py` |

### 2.14 클라이언트·콘솔 공개 변수 (빌드 시 인라인, 2026-07-11 신설)

> **주의**: `EXPO_PUBLIC_*`(단말 앱)과 `VITE_*`(운영 콘솔)는 빌드 산출물에 **평문 포함**되는 공개 변수입니다. 비밀키를 넣지 않습니다. 서버 `.env`가 아니라 각 앱 디렉토리의 환경 파일(`client/.env`, `console/.env`)에서 관리합니다.

| 변수명 | 타입 | 필수/선택 | 기본값(코드 폴백) | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`EXPO_PUBLIC_NETWORK_MODE`** | string | 선택 | `lan` | 단말 접속 모드(`lan`/`ngrok`/`tailscale`). `ngrok` 또는 `tailscale`이면 WiFi/USB 토글보다 외부망 주소 우선 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_WIFI_HOST`** | string | 선택 | `192.168.137.1` | **평상시 WiFi 모드** PC 호스트. Windows 노트북 모바일 핫스팟 게이트웨이 기본값(2026-07-13) | `client/src/config/index.ts`, [android_wifi_usb_transport.md](android_wifi_usb_transport.md) |
| **`EXPO_PUBLIC_LAN_IP`** | string | 선택 | (WIFI_HOST 폴백) | 구 명칭. 설정 시 `WIFI_HOST`가 없으면 이 값을 WiFi 호스트로 사용 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_USB_HOST`** | string | 선택 | `127.0.0.1` | **개발 USB 모드** + `adb reverse` 호스트 | `client/src/config/index.ts`, [android_wifi_usb_transport.md](android_wifi_usb_transport.md) |
| **`EXPO_PUBLIC_TAILSCALE_HOST`** | string | 선택 | (`WIFI_HOST` 폴백) | **외부망 Tailscale 모드** 서버 호스트. iOS/Android 단말의 Tailscale VPN이 켜진 상태에서 서버의 `100.x` 주소 또는 MagicDNS 이름을 사용 | `client/src/config/index.ts`, `client/.env.example` |
| **`EXPO_PUBLIC_SERVER_PORT`** | string | 선택 | `8000` | 단말이 접속할 FastAPI/WebSocket 포트. 기본 `/ws/detect` 포트와 동일 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_DEFAULT_TRANSPORT`** | string | 선택 | `wifi` | 앱 최초 기동 기본 수송(`wifi`/`usb`). 이후 선택은 단말에 영속 | `client/src/config/index.ts`, `client/src/services/serverTransport.ts` |
| **`EXPO_PUBLIC_NGROK_DOMAIN`** | string | 선택 | `partake-primer-surround.ngrok-free.dev` | 외부망 터널 도메인 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_NETWORK_BENCHMARK`** | string | 선택 | `false` | `true`이면 iOS/Android 앱이 `network_probe`를 주기적으로 보내 최신 RTT와 최근 30개 평균을 디버그 정보에 표시 | `client/src/config/index.ts`, `client/src/hooks/useWebSocket.ts` |
| **`EXPO_PUBLIC_NETWORK_BENCHMARK_INTERVAL_MS`** | int | 선택 | `1000` | 앱 내 `network_probe` 전송 간격(ms) | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_NETWORK_BENCHMARK_PAYLOAD_BYTES`** | int | 선택 | `256` | 앱 내 `network_probe` 페이로드 크기(bytes). 작은 고정값으로 순수 WS 왕복 지연을 비교 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_DEVICE_ID`** | string | 선택 | `dev-001` | 단말 식별자 | `client/src/config/index.ts` |
| **`EXPO_PUBLIC_DEVICE_TOKEN`** | string | 선택 | `token-abc-001`(개발 전용) | 디바이스 토큰. **2026-07-11 분리**: 코드 하드코딩에서 환경 변수 우선으로 전환. 실질 보안은 서버 JWT 발급 체계(`issue_device_token`)로 이관 예정 | `client/src/config/index.ts`, `server/api/auth.py` |
| **`VITE_MONITOR_STREAM_URL`** | string | 선택 | `http://localhost:8000/api/v1/monitor/stream` | 콘솔 SSE 스트림 주소 | `console/src/api/useMonitorStream.ts`, `console/.env.example` |
| **`VITE_ENABLE_DEMO_DATA`** | string | 선택 | `false` | 콘솔 데모 데이터 주입(개발 빌드 전용, api_specification §8.4) | `console/src/App.tsx` |
| **`VITE_NAV_MAP_URL`** | string | 선택 | `http://localhost:8000/navigation/?embed=true` | 관제 지도 iframe 주소(2026-07-11 신설) | `console/src/components/OperatorLiveMap.tsx` |
| **`VITE_API_BASE_URL`** | string | 선택 | `http://localhost:8000` | 콘솔 REST API 기본 주소(2026-07-12 신설). 사후 이력 로그 조회·이벤트 프레임 이미지 서빙에 사용 | `console/src/api/useDetectionLogs.ts`, api_specification §8.5 |

### 2.15 코드 실사용 미등재 변수 (2026-07-14 일괄 명세)

> **2026-07-14 정합성 검토**: 코드(`os.getenv`)에서 활성 사용 중이나 기존 명세(§2.1~2.14)에 누락되어 있던 변수들을 일괄 등재합니다. 대부분은 고급 튜닝·내부 분기용 선택 변수이므로 기본값 미설정 시 안전 폴백합니다.

| 변수명 | 타입 | 필수/선택 | 기본값(코드) | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CONVENIENCE_CHROMA_COLLECTION`** | string | 선택 | `convenience_guide` | 생활지원 RAG 전용 ChromaDB 컬렉션명. 안전 수칙(`safety_guidelines`)과 분리된 생활 정보 검색용 | `server/rag/retriever.py`, `scripts/` |
| **`CONVENIENCE_EMBEDDING_MODEL`** | string | 선택 | (`EMBEDDING_MODEL` 폴백) | 생활지원 RAG 전용 임베딩 모델 | `server/rag/embedding_engine_factory.py` |
| **`CONVENIENCE_EMBEDDING_PROVIDER`** | string | 선택 | (`LLM_PROVIDER` 폴백) | 생활지원 RAG 임베딩 공급자(`ollama`/`openai`) | `server/rag/embedding_engine_factory.py` |
| **`GEMINI_MODEL`** | string | 선택 | `gemini-2.5-flash-lite` | Gemini 캡셔닝/LLM 모델명. 4단계 RAG 빌드 및 L2 가이드 생성(gemini provider) 시 사용 | `server/rag/build/gemini_captioner.py`, `server/orchestration/llm_client_factory.py` |
| **`EDGE_TTS_SAMPLE_RATE`** | int | 선택 | `24000` | edge-tts 출력 샘플레이트(Hz) | `server/tts/tts_service.py` |
| **`SUPERTONIC_SPEED_MIN`** / **`SUPERTONIC_SPEED_MAX`** | float | 선택 | (코드 기본값) | Supertonic 발화 속도 허용 범위 | `server/tts/tts_service.py` |
| **`DATABASE_URL`** | string | 선택 | (미설정) | SQLAlchemy 통합 DB 연결 URL. 설정 시 개별 `DB_HOST`/`DB_PORT`/... 조합보다 우선 | `server/db/connection.py` |
| **`LANGCHAIN_PROJECT`** | string | 선택 | `minchodan` | LangSmith 트레이스 프로젝트명 | `server/mcp/langsmith_tracer.py` |
| **`STT_CONFIG_SOURCE`** | string | 선택 | (코드 기본값) | STT 설정 소스 분기 | `server/stt/stt_config.py` |
| **`TEST_VERIFY_MODE`** | bool | 선택 | `false` | 검증 테스트 모드 활성화(오프라인 검증 스크립트용) | `server/` |
| **`DEVICE_TOKEN`** | string | 선택 | (미설정) | 디바이스 토큰(`scripts/` 유틸리티 스크립트 전용) | `scripts/` |
| **`AIHUB_WALK_DATASET_ROOT`** | path | 선택 | (미설정) | AIHub 인도보행 영상 데이터셋 루트 경로(RAG 빌드 스크립트용) | `scripts/` |

> **참고**: 이 변수들은 `.env.example`에 주석 처리 또는 미기재 상태일 수 있으며, 고급 사용자만 설정하는 튜닝 포인트입니다. 프로젝트 기동에는 영향을 주지 않습니다.

---

## 3. 환경 변수 로드 패턴

모든 Python 모듈은 [`docs/course_codebase_guide.md`](course_codebase_guide.md) 3.4절의 표준 패턴을 준수합니다.

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
| 7 | **`NGROK_AUTHTOKEN` 누락** | 야외 도로 테스트용 터널 인증 변수가 `.env.example`에만 존재 | 본 명세서 2.11절에 통합 |
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
| 5 | Docker 컨테이너의 호스트 Ollama 연결 | `docker exec minchodan-fastapi python -c "import os; print(os.getenv('OLLAMA_BASE_URL'))"` | `COMPOSE_OLLAMA_BASE_URL` 값 |
| 6 | 가중치 파일 존재 | `Test-Path server/models/yolo26n/det_best_20260705.pt` | `True` |
| 7 | ChromaDB 경로 존재 | `Test-Path data/chroma_db` | `True` (4단계 빌드 후) |
| 8 | DB 대상명 확인 | `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('DB_NAME'))"` | `minchodan_db` |
