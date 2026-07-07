# Minchodan 환경 변수 명세서

> **작성일**: 2026-07-04
> **버전**: v0.4.0 (2026-07-07 Slack 인증 방식 재정정(Bot Token이 실제 사용됨), TTS_ENGINE 실제값(piper), 코드에만 있고 문서 누락됐던 변수 6종 추가, GOOGLE_API_KEY/.env.example 불일치 명시)
> **기준 파일**: [`.env.example`](../.env.example) (단일 기준)
> **설계 기준**: [`docs/architecture.md`](architecture.md) 10절·13.4절, [`docs/pipeline_stage_design.md`](pipeline_stage_design.md)
> **코딩 패턴 기준**: [`docs/course_codebase_guide.md`](course_codebase_guide.md) 3.4(.env 로드)

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
| **`OLLAMA_HOST`** | string | 선택 | (코드 기본값) | 임베딩 팩토리 전용 Ollama 호스트 (2026-07-07 추가 — `OLLAMA_BASE_URL`과 별개로 존재) | `server/rag/embedding_engine_factory.py:46` |
| **`GEMMA_MODEL`** | string | 필수 | `gemma4:e4b` | L2 가이드 생성 모델 (로컬) | [`stage6_orchestration_design.md`](stage6_orchestration_design.md) 9.3절 |
| **`LLAVA_MODEL`** | string | 선택 | `llava` | 4단계 오프라인 캡셔닝 모델 (Ollama 로컬 경로 사용 시). Gemini 캡셔닝 선택 시 미사용 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`GOOGLE_API_KEY`** | string | 선택 | (미설정) | 4단계 캡셔닝 모델 Gemini API(`gemini-2.5-flash-lite`, `server/rag/build/gemini_captioner.py`) 사용 시 필수. 미설정 시 `ValueError` 발생(Llava 폴백 없음 — 2026-07-07 확인: 실제 캡셔너 구현체는 Gemini뿐). **2026-07-07 현재 `.env.example`에 이 변수가 없어 문서와 실제 파일이 불일치** — 값 설정 필요 시 `.env.example`에 직접 추가할 것 | [`stage4_5_rag_design.md`](stage4_5_rag_design.md) 2.1절 |
| **`EMBEDDING_MODEL`** | string | 필수 | `nomic-embed-text` | 임베딩 모델 (768차원) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`OPENAI_API_KEY`** | string | 선택 | (미설정) | OpenAI 핫스왑 시 필요. 미설정 시 OpenAI 클라이언트 초기화에서 `ValueError` 발생 후 Ollama로 폴백 | [`architecture.md`](architecture.md) 13.4절 |

### 2.2 Vector DB (ChromaDB) (4·5단계 RAG)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CHROMA_PATH`** | path | 필수(설계상) | `data/chroma_db` | ChromaDB persist 디렉토리 (로컬 파일 기반). **2026-07-07 현황**: `.env.example`에는 정의돼 있으나 `vector_db_factory.py`/`retriever.py`가 아직 이 변수를 `os.getenv`로 읽지 않는다(명시적 경로/인스턴스 인자로만 동작) — `docs/stage-guides/stage4_5_data_replacement_guide.md` §2.4 참조 | [`architecture.md`](architecture.md) 2절 |
| **`CHROMA_COLLECTION`** | string | 필수(설계상) | `minchodan_kb` | ChromaDB 컬렉션명 (보행 수칙 지식베이스). 위와 동일하게 아직 코드에서 소비되지 않음 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.5절 |

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
| **`HEARTBEAT_TIMEOUT`** | int | 선택 | (코드 기본값) | 하트비트 미수신 타임아웃(초) | `server/api/config.py:31` |
| **`MAX_RECONNECT_ATTEMPTS`** | int | 선택 | (코드 기본값) | 서버 측 재연결 허용 횟수 | `server/api/config.py:32` |
| **`JWT_SECRET_KEY`** | string | 선택 | (코드 기본값) | 관리자/유저 인증 JWT 서명 키 (2026-07-07 추가 — `.env.example`에도 없어 실서비스 배포 전 반드시 별도 설정 필요) | `server/db/security.py:19` |

### 2.5 탐지 설정 (3단계 Detection)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`YOLO_CONF`** | float | 필수 | `0.35` | Yolo 26N - Object Detection 신뢰도 임계값 | [`stage3_detection_design.md`](stage3_detection_design.md) 5절 |
| **`DETECTOR_TYPE`** | string | 선택 | `mock` | 탐지 파이프라인 구동 모드 (`mock`: Mock 폴백 / `yolo`: 실제 모델 추론). 개발 환경 및 테스트에서 `mock` 사용 권장 | [`architecture.md`](architecture.md) 10절 |
| **`FRAME_SIZE`** | int | 필수 | `640` | 프레임 리사이즈 크기 (정방형) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`REFLEX_FPS`** | int | 필수 | `10` | 반사 캡처 목표 fps (8~10fps 권장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`COGNITIVE_FPS`** | int | 필수 | `2` | 인지 캡처 목표 fps (1~2fps 권장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.2절 |
| **`YOLO26N_OBJECT_DET`** | path | 선택 | `server/models/yolo26n/object_detection.pt` | Yolo 26N - Object Detection 가중치 경로 (Git 추적) | [`stage3_detection_design.md`](stage3_detection_design.md) 12.3절 |
| **`YOLO26N_SEG`** | path | 선택 | `server/models/yolo26n/segmentation.pt` | Yolo 26N - Segmentation 가중치 경로 (Git 추적) | [`stage3_detection_design.md`](stage3_detection_design.md) 12.3절 |

### 2.6 TTS (7단계 음성 출력)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`TTS_ENGINE`** | string | 필수 | `piper` | TTS 엔진. **2026-07-07 정정**: `piper`만 실제 지원(`kokoro`/`coqui` 미구현, 지정 시 경고 로그 후 piper로 강제 폴백). 인지 경로 실시간 합성에만 사용 (반사 경로는 사전합성 클립) | [`stage7_tts_design.md`](../stage-guides/stage7_tts_design.md) |
| **`PIPER_BINARY_PATH`** | path | 선택 | (코드 기본값) | Piper ONNX 실행 바이너리 경로 (2026-07-07 추가) | `server/tts/tts_service.py:103` |
| **`PIPER_LENGTH_SCALE_MIN`** / **`PIPER_LENGTH_SCALE_MAX`** | float | 선택 | (코드 기본값) | Piper 발화 속도 스케일 범위 (2026-07-07 추가) | `server/tts/tts_service.py:104-105` |

### 2.7 데이터 경로 (4단계 RAG 빌드·7단계 반사 클립)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DATA_RAW`** | path | 필수 | `data/raw` | AI Hub 보행자 데이터셋 원본 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_FRAMES`** | path | 필수 | `data/frames` | 1fps 추출 프레임 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_DEDUPED`** | path | 필수 | `data/deduped` | pHash 중복 제거 후 프레임 | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_CAPTIONS`** | path | 필수 | `data/captions` | 캡셔닝 결과 JSON (Llava 또는 Gemini API 사용에 따라 동일 경로에 저장) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.4절 |
| **`DATA_REFLEX_CLIPS`** | path | 필수 | `data/reflex_clips` | 사전합성 반사 음성 클립 (alert_id별 MP3) | [`pipeline_stage_design.md`](pipeline_stage_design.md) 5.7절 |

### 2.8 Slack Integration (공통 경보)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SLACK_BOT_TOKEN`** | string | 선택 | (미설정) | Slack Bot Token. `scripts/slack_publisher.py:52`에서 실제 사용 중(미설정 시 경고 로그) | `scripts/slack_publisher.py` |
| **`SLACK_CHANNEL_ID`** | string | 선택 | `C0BCZSB5TJS`(코드 내 폴백값) | 경보 발송 대상 채널 ID. `scripts/slack_publisher.py:193`에서 실제 사용 중 | `scripts/slack_publisher.py` |

> **2026-07-07 정정**: 이전 버전은 `SLACK_WEBHOOK_URL`(Incoming Webhook)로 단일화했다고 기술했으나, 실제 코드(`scripts/slack_publisher.py`)를 확인한 결과 `SLACK_WEBHOOK_URL`은 어디에도 쓰이지 않고 `SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID`(Bot Token 방식)만 실제로 사용되고 있다. "폐기"라고 서술했던 방식이 오히려 유일하게 살아있는 구현이었으므로 표를 코드 기준으로 되돌린다.

### 2.9 LangSmith Trace (선택적 관측)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LANGCHAIN_API_KEY`** | string | 선택 | (미설정) | LangSmith Platform API 키. StateGraph 실행 경로 및 지연 추적 활성화 | [`architecture.md`](architecture.md) 13.4절 |
| **`LANGCHAIN_TRACING_V2`** | bool | 선택 | `false` | LangSmith Tracing v2 활성화 여부 (`true` 시 추적 시작) | [`architecture.md`](architecture.md) 13.4절 |

> **선택적 명세**: LangSmith Trace MCP는 `architecture.md` 13.4절에서 "선택적으로 기입"으로 명시되어 있으며, 미설정 시 6단계 LangGraph 동작에는 영향을 주지 않습니다.

### 2.10 GPU 모니터링 Mock (개발·테스트 전용)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MOCK_GPU_USAGE_PCT`** | float | 선택 | `30.0` | Mock GPU 사용률 (%). CUDA 미감지 환경에서 핫스왑 트리거 테스트용 | [`server/mcp/gpu_monitor.py`](../server/mcp/gpu_monitor.py) |
| **`MOCK_GPU_MEM_USED_MB`** | float | 선택 | `2048.0` | Mock GPU 메모리 사용량 (MB). CUDA 미감지 환경에서 핫스왑 트리거 테스트용 | [`server/mcp/gpu_monitor.py`](../server/mcp/gpu_monitor.py) |

> **개발 전용**: 이 변수들은 CUDA GPU가 감지되지 않은 개발·CI 환경에서 `GPUMonitorMCP`의 Mock 폴백 동작을 제어합니다. 프로덕션 환경에서는 무시됩니다.

### 2.11 외부 터널링 (Ngrok) (야외 도로 테스트용)

| 변수명 | 타입 | 필수/선택 | 기본값 | 설명 | 참조 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`NGROK_AUTHTOKEN`** | string | 선택 | (미설정) | 야외 도로 테스트용 ngrok 터널 보안 인증 토큰. 무료 계정 터널 외부 노출 시 필요 | [`docs/changelogs/kb.md`](../changelogs/kb.md) |

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
| 1 | **Slack 인증 방식** | `.env.example`(`SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID`) vs `architecture.md` 13.4절(`SLACK_WEBHOOK_URL`) | 2026-07-07 재정정: 실제 코드(`scripts/slack_publisher.py`)가 `SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID`만 사용하므로 이 방식으로 확정. `SLACK_WEBHOOK_URL`은 코드 어디에도 없는 미사용 변수 |
| 2 | **`WS_HOST` 누락** | `.env.example`에만 존재, `architecture.md`·`README.md`에는 누락 | 본 명세서 2.4절에 통합 |
| 3 | **`DETECTOR_TYPE` 누락** | `.env.example`에만 존재 | 본 명세서 2.5절에 통합 |
| 4 | **`DATA_*` 경로 누락** | `.env.example`에만 존재 (5종) | 본 명세서 2.7절에 통합 |
| 5 | **`MOCK_GPU_*` 누락** | 어디에도 문서화되지 않음 (코드에만 존재) | 본 명세서 2.10절에 신규 명세 |
| 6 | **`LANGCHAIN_*` 누락** | `architecture.md` 13.4절에만 산재 | 본 명세서 2.9절에 통합 |

---

## 5. 보안 주의사항

| 항목 | 지침 |
| :--- | :--- |
| **`.env` 파일** | 절대 Git에 커밋하지 마십시오. `.gitignore`에 `.env` 패턴이 등록되어 있습니다. |
| **`OPENAI_API_KEY`** | OpenAI API Platform에서 발급. 키 유출 시 즉시 회전하십시오. |
| **`SLACK_BOT_TOKEN`** | Slack App 설정에서 Bot Token 발급. 키 유출 시 즉시 회전하십시오. |
| **`LANGCHAIN_API_KEY`** | LangSmith Platform에서 발급. 선택적 변수이므로 미설정해도 동작에 영향 없습니다. |

---

## 6. 검증 체크리스트

환경 변수 설정 완료 후 아래 항목을 점검합니다.

| # | 검증 항목 | 명령 | 기대 결과 |
| :--- | :--- | :--- | :--- |
| 1 | .env 파일 존재 | `Test-Path .env` (Windows) / `test -f .env` (Linux) | `True` |
| 2 | 필수 변수 누락 여부 | `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('LLM_PROVIDER'))"` | `ollama` |
| 3 | Redis 연결 | `redis-cli ping` | `PONG` |
| 4 | Ollama 연결 | `curl $OLLAMA_BASE_URL/api/tags` | 모델 목록 JSON |
| 5 | 가중치 파일 존재 | `Test-Path server/models/yolo26n/object_detection.pt` | `True` |
| 6 | ChromaDB 경로 존재 | `Test-Path data/chroma_db` | `True` (4단계 빌드 후) |
