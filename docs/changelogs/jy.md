# Changelog - jy (준영)

> 이 파일은 **jy(준영)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-07-19 | 보안/클라이언트/문서 | ngrok 제거 및 uuid 취약점 해소

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 외부망 연결을 Tailscale로 단일화한 이후에도 `@expo/ngrok`와 플랫폼별 실행 바이너리, 클라이언트 ngrok 네트워크 모드, 과거 실행 안내가 남아 있었습니다.
  - `@expo/ngrok -> uuid@3.4.0`과 `expo-splash-screen -> xcode -> uuid@7.0.3` 경로에서 `GHSA-w5hq-g745-h8pq` 취약점이 탐지됐습니다.
- **변경 내용**:
  - `@expo/ngrok` 직접 개발 의존성과 관련 바이너리·전이 패키지 34개를 제거하고 `package-lock.json`을 재생성했습니다.
  - `NetworkMode`를 `lan | tailscale`로 축소하고, ngrok 도메인 환경변수·URL 생성·UI 라벨·접근성 분기를 제거했습니다.
  - `xcode@3.0.1`의 미사용 취약 전이 의존성은 npm scoped override로 `uuid@11.1.1`에 고정했습니다.
  - 루트 `.env`의 로컬 ngrok 환경변수 한 줄을 값 출력 없이 제거하고, Windows 시작 스크립트 및 실기기·통합 운영 문서를 Tailscale 기준으로 동기화했습니다.
- **검증 결과**:
  - `npm ls @expo/ngrok @expo/ngrok-bin uuid --all`: ngrok 패키지 없음, `uuid@11.1.1 overridden` 확인
  - `npm audit --json`: 취약점 0건(Moderate/High/Critical 포함 전체 0)
  - `npx tsc --noEmit`: 통과
  - `npx expo config --type public`: 통과, ngrok 환경변수 미노출 확인
  - `git diff --check`: 통과
- **별도 기존 이슈**:
  - `npx expo-doctor`는 21개 중 15개 통과, 6개 실패했습니다. 실패 항목은 이번 보안 변경과 무관한 기존 `app.json` splash 스키마, `expo-asset` peer·중복, 네이티브 폴더와 Prebuild 설정 병존, `react-native-fast-tflite` New Architecture 메타데이터, Expo SDK 56 패키지 버전 불일치입니다.

---

### 2026-07-17 | 문서 보안 | DB·미디어 API 가이드 외부 공개용·내부용 분리

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 통합 가이드에는 실제 Tailscale 주소, DB 식별자, 서버 상태와 내부 경로가 포함되어 팀 내부 운영에는 유용하지만 외부 공개본으로는 과도한 인프라 정보였습니다.
- **변경 내용**:
  - 추적되는 `docs/db_tailscale_guide/README.md`를 외부 공개용 v0.3.0으로 전환하고 실제 호스트·DB·포트·경로·API 식별자를 플레이스홀더로 치환했습니다.
  - 실접속 정보가 포함된 기존 문서는 같은 폴더의 `README.internal.md`로 보존했습니다.
  - 내부 문서는 `.gitignore`에 등록해 공개 저장소나 커밋에 실수로 포함되지 않도록 했습니다.
  - `docs/README.md`에 공개용 문서와 Git 제외 내부 문서의 역할을 구분했습니다.
- **관련 파일**: `.gitignore`, `docs/db_tailscale_guide/README.md`, `docs/db_tailscale_guide/README.internal.md`(Git 제외), `docs/README.md`, `docs/changelogs/jy.md`
- **검증 기준**:
  - 공개본에는 실제 Tailscale IP, DB명·계정명, 서비스 버전, 내부 파일 경로와 실제 비밀번호·토큰이 없어야 합니다.
  - 내부본은 로컬에 존재하되 `git check-ignore`와 `git status`에서 추적 대상이 아니어야 합니다.
- **비고**:
  - 내부 문서는 Git으로 팀에 배포하지 않으며 승인된 비밀관리 도구 또는 팀 내부 보안 채널로 별도 전달합니다.

### 2026-07-17 | 문서·운영 | MariaDB·미디어 저장 API Tailscale 팀 연결 가이드 통합

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 기존 `docs/db_tailscale_guide/README.md`는 공동 MariaDB 접속만 설명해, Raspberry Pi 중앙 미디어 저장 API와 STT 원본 음성 저장 설정을 팀원이 별도 문서에서 찾아야 했습니다.
  - `.vscode/log_Miss_Issue`의 MISS 조사·중앙 저장 진행 문서와 개발 감사 보고서를 팀 표준 문서로 정리하되, AI 에이전트가 비밀값을 노출하거나 운영 DB를 파괴적으로 변경하지 않도록 실행 경계를 명확히 할 필요가 있었습니다.
- **변경 내용**:
  - 기존 DB Tailscale 가이드를 공동 MariaDB와 중앙 미디어 저장 API를 함께 다루는 v0.2.0 통합 가이드로 개정했습니다.
  - 실제 Tailscale 호스트와 서비스 포트, 루트 `.env` 설정, DBeaver·FastAPI·Docker Compose 연결, DB와 미디어 API의 읽기 전용 smoke test를 추가했습니다.
  - 이벤트 프레임 object key와 사용자 STT 원본 음성 경로·전사문·저장 상태 컬럼의 역할, 미디어 API 라우트, 기존 데이터 보존형 마이그레이션 원칙을 문서화했습니다.
  - AI 에이전트 시작 순서, 첫 확인 파일, 비밀값 보호, 금지 명령, 장애 분리표와 팀 전달용 프롬프트 예시를 추가했습니다.
  - `docs/README.md` 인덱스를 갱신하고 실제 파일이 없는 오래된 보고서 링크 1건을 제거했으며, `docs/ops/deployment_guide.md`의 Docker DB 대상 설명을 실제 Compose의 원격 DB 보존 동작과 맞췄습니다.
- **관련 파일**: `docs/db_tailscale_guide/README.md`, `docs/README.md`, `docs/ops/deployment_guide.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - Raspberry Pi에서 Tailscale·MariaDB·미디어 API 서비스 `active`/`enabled`, 포트 `3306`·`8081`, 미디어 `/health` HTTP 200을 읽기 전용 확인했습니다.
  - 공동 MariaDB의 STT·writer 컬럼 존재와 개발 PC 루트 `.env` 기준 `SELECT 1`, 미디어 API Bearer 인증을 확인했습니다.
- **비고**:
  - 실제 DB 비밀번호, 미디어 API 토큰, 개인 SSH 키는 문서와 changelog에 기록하지 않았습니다.

### 2026-07-17 | 환경변수 | Raspberry Pi 중앙 저장소·Ollama 기준 `.env.example` 재작성

- **커밋**: (이번 커밋)
- **변경 배경**:
  - Raspberry Pi MariaDB, 중앙 저장 API, STT 원본 음성 저장, Ollama `gemma4:e4b` 사용 설정이 한 번에 늘어나면서 기존 `.env.example`의 어느 위치에 어떤 값을 넣어야 하는지 파악하기 어려웠습니다.
  - 실제 `.env`에는 DB 비밀번호, 저장 API 토큰, TMAP 키, LLM API 키 등 민감값이 포함되므로, 사용자가 값만 채워 넣을 수 있는 별도 템플릿 정리가 필요했습니다.
- **변경 내용**:
  - 루트 `.env.example`을 새로 생성하여 `0. 실행 환경`부터 `16. 테스트 / 검증 보조`까지 번호가 있는 섹션으로 재구성했습니다.
  - Raspberry Pi MariaDB 설정(`DB_HOST`, `DB_PASSWORD`)과 중앙 저장 API 설정(`EVENT_FRAME_STORAGE_BACKEND`, `IMAGE_SERVER_BASE_URL`, `IMAGE_SERVER_TOKEN`, `WRITER_INSTANCE_ID`)을 별도 섹션으로 분리했습니다.
  - 사용자가 실제 값을 채워야 하는 항목은 `[RASPBERRY_PI_TAILSCALE_IP]`, `[MARIADB_PASSWORD]`, `[IMAGE_SERVER_TOKEN]`, `[TMAP_APP_KEY]`처럼 대괄호 플레이스홀더로 통일했습니다.
  - LLM 기본 사용 의도에 맞춰 Ollama 경로(`OLLAMA_BASE_URL`, `GEMMA_MODEL=gemma4:e4b`)와 RAG 임베딩 경로(`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL=nomic-embed-text`)를 명확히 분리했습니다.
  - 현재 코드 기준 미구현인 `kokoro/coqui`는 TTS 기본값에서 제외하고 `TTS_ENGINE=supertonic`을 기본 예시로 정리했습니다.
  - 기존 임시 백업 템플릿 `01_.env.example`은 삭제하지 않고 보존했습니다.
- **관련 파일**: `.env.example`, `01_.env.example`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `python-dotenv`로 `.env.example` 파싱 성공: 78개 key 인식
  - 중앙 저장 핵심 key(`DB_HOST`, `IMAGE_SERVER_BASE_URL`, `IMAGE_SERVER_TOKEN`, `EVENT_FRAME_STORAGE_BACKEND`) 누락 없음 확인
  - `git diff --check .env.example` 통과
- **비고**:
  - 실제 `.env` 파일은 민감 정보 보호를 위해 열람하지 않았습니다.
  - 운영 반영 시에는 `.env.example`을 복사한 뒤 대괄호 플레이스홀더만 실제 값으로 교체하면 됩니다.

---

### 2026-07-16 | DB/저장소/STT | Raspberry Pi 중앙 저장 API 연동 및 Log STT 원본 음성 메타데이터 기록

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 공유 MariaDB를 여러 FastAPI writer가 함께 쓰는 구조에서 이벤트 프레임 JPEG는 각 writer의 로컬 디스크에 흩어져 `frame_path`는 있으나 콘솔 이미지 조회가 404가 되는 MISS가 발생했습니다.
  - STT 경로는 기존에 사용자가 말한 원본 음성 파일과 전사 문장을 `detection_guidance_logs`에 함께 남기지 않아, 사용자 발화 기반 이력 추적과 재검증이 어려웠습니다.
- **변경 내용**:
  - `server/services/remote_storage_client.py`를 추가해 Raspberry Pi 중앙 저장 API에 이벤트 프레임 JPEG와 STT 원본 음성 bytes를 업로드하도록 했습니다.
  - `server/services/event_frame_store.py`와 `server/detection/consumer.py`를 수정해 원격 저장 사용 시 `frame_path`에 중앙 저장소 object key만 저장하도록 연결했습니다.
  - `server/api/ws_router.py` STT 처리부에서 사용자가 말한 원본 오디오를 업로드하고, `stt_transcript_text`, `stt_audio_path`, `stt_audio_storage_status`, `stt_audio_size_bytes`, `stt_audio_duration_ms`, `stt_audio_sha256` 등을 Log에 저장하도록 했습니다.
  - `server/api/detection_log_router.py`는 로컬 파일이 없으면 중앙 저장소에서 프레임을 조회해 콘솔에 프록시 응답하도록 보강했습니다.
  - `detection_guidance_logs` ORM/DTO/SQLite DDL/마이그레이션에 STT 원본 음성 저장 메타데이터 컬럼과 조회 인덱스를 추가했습니다.
  - 콘솔 타입과 지연 패널에 STT 음성 업로드 시간(`stt_audio_upload_ms`)을 반영했습니다.
  - `.env.example`, `docs/ops/environment_variables.md`, `docs/design/api_specification.md`, `docs/design/architecture.md`, `.vscode/log_Miss_Issue/central_image_storage_latency_progress_share.md`를 새 저장 구조에 맞춰 갱신했습니다.
- **관련 파일**:
  - `server/services/remote_storage_client.py`, `server/services/event_frame_store.py`, `server/detection/consumer.py`, `server/api/ws_router.py`, `server/api/detection_log_router.py`
  - `server/db/models.py`, `server/db/schemas.py`, `server/db/schema.sql`, `server/db/migrations/20260716_002_add_stt_audio_columns_to_detection_guidance_logs.sql`
  - `console/src/types/monitor.ts`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/components/LatencySummaryPanel.tsx`, `console/src/pages/DashboardPage.tsx`
  - `.env.example`, `docs/ops/environment_variables.md`, `docs/design/api_specification.md`, `docs/design/architecture.md`, `.vscode/log_Miss_Issue/central_image_storage_latency_progress_share.md`
- **검증 결과**:
  - `python -m py_compile` 대상 Python 파일 통과
  - `pytest tests/test_event_frame_store.py tests/test_ws_router_stt.py tests/test_false_positive.py tests/test_tts_prewarm.py` 통과: 20 passed, 3 warnings
  - `cd console && ./node_modules/.bin/tsc --noEmit` 통과
  - `git diff --check` 통과
  - `ruff`는 현재 `.venv`와 PATH에 설치되어 있지 않아 실행하지 못했습니다.
- **비고**:
  - 이번 작업은 서버/DB/콘솔 저장 경로 연동 범위입니다. 작업 전부터 존재하던 iOS 네이티브/Podfile 변경은 이번 범위에서 수정하지 않았습니다.
  - 실제 운영 반영 시 GPU FastAPI `.env`에 `EVENT_FRAME_STORAGE_BACKEND=remote`, `IMAGE_SERVER_BASE_URL`, `IMAGE_SERVER_TOKEN`, `WRITER_INSTANCE_ID`를 설정하고 서버를 재시작해야 합니다.

---

### 2026-07-15 | Docker/Ollama | WSL/Linux 로컬 Ollama 자동 기동 보강

- **커밋**: `infra: WSL/Linux 로컬 Ollama 실행 환경 보강`
- **변경 내용**:
  - `requirements.txt`에서 로컬 Ollama LLM 호출에 필요한 `ollama==0.6.2`를 실제 설치 대상에 포함했습니다.
  - Linux Docker 시작 스크립트가 `systemd`에 의존하지 않고 `ollama serve`를 백그라운드 실행하도록 보강했습니다.
  - 기본 Ollama 바인딩은 `127.0.0.1:11434`로 두고, Docker 컨테이너 접근을 위한 `0.0.0.0:11434` 바인딩은 `MINCHODAN_EXPOSE_OLLAMA=1` 명시 opt-in으로 제한했습니다.
  - Docker 게이트웨이 단독 바인딩 및 브리지 프록시 대안을 검토했으나, 현재 로컬 Docker 네트워크에서는 컨테이너에서 호스트 게이트웨이 요청이 타임아웃되어 최종 반영하지 않았습니다.
  - 시작 스크립트에서 `gemma4:e4b`, `nomic-embed-text` 모델 존재 여부를 확인하고 누락 시 pull하도록 추가했습니다.
  - `.env.example`에 `OLLAMA_HOST`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_MAX_LOADED_MODELS`를 추가해 Docker 컨테이너의 호스트 Ollama 접근 기준을 명시했습니다.
  - 배포 및 하드웨어 구성 문서에 WSL/Linux `systemd` 미사용 환경의 Ollama 실행 기준을 반영했습니다.
- **관련 파일**: `requirements.txt`, `.env.example`, `docker/linux_docker_start.sh`, `docs/ops/deployment_guide.md`, `docs/ops/ai_model_hardware_setup.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `bash -n docker/linux_docker_start.sh docker/macos_docker_start.sh` 통과
  - `docker compose --env-file .env -f docker/docker-compose.yml config --quiet` 통과
  - `git diff --check` 통과
  - `nohup ollama serve`로 로컬 Ollama 서버 기동 후 `curl http://127.0.0.1:11434/api/version` 응답 확인
  - `ollama list`에서 `gemma4:e4b`, `nomic-embed-text` 모델 설치 확인
  - `.venv` 기준 `LLMClientFactory.get_client("ollama")` 실제 호출 성공 확인
  - `EmbeddingEngineFactory.get_embeddings(provider="ollama")`로 `nomic-embed-text` 768차원 임베딩 호출 성공 확인
  - `docker compose --env-file .env -f docker/docker-compose.yml build fastapi` 성공 및 `minchodan-fastapi` 재생성 완료
  - `curl http://127.0.0.1:8008/health` 기준 FastAPI health 정상, `TTS_ENGINE=supertonic`, `CHROMA_COLLECTION=safety_guidelines` 반영 확인
  - 현재 Docker 네트워크에서는 컨테이너에서 호스트 Ollama(`host.docker.internal:11434`) 접근이 타임아웃됩니다. 전체 인터페이스 바인딩(`OLLAMA_HOST=0.0.0.0:11434`)은 보안상 사용자 명시 승인 후 적용 대상으로 남겼습니다.

---

### 2026-06-26 | 공통 | Changelog 관리 체계 전환 및 한국어 안내 자동화 스크립트 수정

- **커밋**: `refactor: changelog per-member append system and localized scripts`
- **변경 내용**:
  - 기존 작업별 개별 파일 방식의 changelog를 팀원별 단일 파일 누적(append) 방식으로 마이그레이션했습니다.
  - 이에 따라 `docs/changelogs/README.md` 및 `TEMPLATE.md`를 신규 누적형 기준에 맞춰 수정했습니다.
  - 팀원별 changelog 파일 5개(`dg.md`, `jh.md`, `jy.md`, `kb.md`, `th.md`)를 신규 생성하고 기존의 baseline 이력을 이관하였습니다.
  - `scripts/prework.sh`, `scripts/postwork.sh` 내의 안내 메시지 및 사용자 질문을 모두 한국어로 지역화(localization)했습니다.
  - Windows cmd 환경에서 발생하는 CP949 한국어 특수 문자 인코딩 에러를 방지하기 위해 `scripts/prework.bat` 및 `scripts/postwork.bat`를 영어로 복원하고 CP949 호환성을 개선했습니다.
  - Windows 환경의 한국어 안내 지원을 위해 UTF-8 BOM 인코딩 기반의 PowerShell 스크립트 `scripts/prework.ps1` 및 `scripts/postwork.ps1`을 새롭게 추가하고, PowerShell 구문 오류를 수정하여 안정성을 확보했습니다.
  - 변경 사항에 맞추어 `README.md`, `skills.md`, `docs/git_branching_strategy.md`, `SCRIPT_GENERATION_PROMPT.md` 문서 내의 관련 레퍼런스를 일관되게 업데이트했습니다.
- **관련 파일**: `docs/changelogs/README.md`, `docs/changelogs/TEMPLATE.md`, `docs/changelogs/jy.md`, `scripts/prework.sh`, `scripts/postwork.sh`, `scripts/prework.bat`, `scripts/postwork.bat`, `scripts/prework.ps1`, `scripts/postwork.ps1`, `README.md`, `skills.md`, `docs/git_branching_strategy.md`, `SCRIPT_GENERATION_PROMPT.md`
- **검증 결과**:
  - `prework.ps1`, `postwork.ps1` 및 `prework.sh`, `postwork.sh` 스크립트 대화형 안내 및 유효성 검사 흐름 터미널 작동 확인 완료
  - 각 문서 내 구 레퍼런스(`2026-06-24_initial_baseline.md`)에 대한 정합성 일괄 교체 및 삭제 검증 완료

---

### 2026-07-03 | DB | DBeaver 세션 SQL 및 DB명 시트 기준 갱신

- **커밋**: 미커밋
- **변경 내용**:
  - Google Sheets `테이블_명세서`, `스키마_설계` 기준으로 `minchodan_db` 초기화 SQL을 재정리했습니다.
  - `admin_accounts`, `admin_login_audits`, `app_users`, `user_devices` 4개 테이블의 컬럼, 인덱스, FK 정책을 시트 기준과 맞췄습니다.
  - 기존 `minchodan_tmp`, 확장 컬럼, `ON DELETE CASCADE` 중심 설명을 제거하고 `ON DELETE RESTRICT` 및 사번 기반 감사 로그 구조를 문서화했습니다.
  - DBeaver 세션 SQL과 환경 변수 예시의 DB명을 `minchodan_db` 기준으로 정리했습니다.
- **관련 파일**: `Minchodan DB.session.sql`, `.env.example`
- **검증 결과**:
  - Google Sheets 메타데이터와 대상 탭 범위 확인 완료
  - SQL 본문에서 이전 DB명 및 제거 대상 컬럼 잔존 여부 검색 완료
  - 대상 SQL/Markdown 파일의 trailing whitespace 검색 완료

---

### 2026-07-03 | DB | SQLAlchemy ORM 모델 및 Pydantic DTO 추가

- **커밋**: 미커밋
- **변경 내용**:
  - 최종 4개 테이블 명세 기준으로 `server/db/models.py`에 SQLAlchemy 2.0 ORM 모델을 추가했습니다.
  - `app_users`와 `user_devices` 간 1:N 관계 및 `ON DELETE RESTRICT` 외래키 정책을 반영했습니다.
  - `server/db/schemas.py`에 생성용 DTO와 ORM 응답용 Pydantic V2 스키마를 분리해 추가했습니다.
  - SQLite 실행용 `server/db/schema.sql` DDL을 추가하고 ORM 핵심 관계 설명 주석을 보강했습니다.
  - 발표 방어 및 직접 하드코딩 학습을 위해 `models.py` 핵심 ORM 매핑 주석을 보강했습니다.
- **관련 파일**: `server/db/models.py`, `server/db/schemas.py`, `server/db/schema.sql`
- **검증 결과**:
  - `compile()` 기반 순수 문법 검사 완료
  - SQLite 메모리 DB에서 `server/db/schema.sql` 실행 및 4개 테이블 생성 확인
  - `app_users` 삭제 시 연결된 `user_devices`가 있으면 `ON DELETE RESTRICT`로 차단되는지 확인
  - 현재 셸에 `ruff`, `sqlalchemy`, `pydantic` 런타임 의존성이 없어 린트 및 import 검증은 미실행

---

### 2026-07-06 | 문서 | DB 반영 내용 교차 검증 및 정합성 업데이트

- **커밋**: a1b2c3d (본인의 실제 커밋 해시 입력)
- **변경 내용**:
  - `server/db/` 신규 DB 계층을 `README.md`, `AGENTS.md`, `docs/AGENTS.md`의 서버 구조 설명에 반영했습니다.
  - `docs/ops/environment_variables.md`에 `.env.example`의 DB 환경 변수 6종을 추가하고 `DB_NAME=minchodan_db` 기준을 명시했습니다.
  - `Minchodan DB.session.sql` 상단 기준 설명에서 존재하지 않는 `back_sql` 참조를 제거하고 현재 기준 파일을 명시했습니다.
  - `.vscode` 로컬 DB 스키마 문서를 현재 4테이블 구조와 `ON DELETE RESTRICT` 기준으로 재정리했습니다.
- **관련 파일**: `README.md`, `AGENTS.md`, `docs/AGENTS.md`, `docs/ops/environment_variables.md`, `Minchodan DB.session.sql`, `.vscode/mariadb_admin_user_schema.md`, `.vscode/PROJECT_TECH_STACK_DATA_WORKFLOW.md`
- **검증 결과**:
  - `minchodan_app`, `ON DELETE CASCADE`, `disability_grade`, `login_id`, `ws_token_hash` 등 과거 초안 키워드 잔존 여부 검색 완료
  - `minchodan_db`, `DB_*`, `server/db`, `ON DELETE RESTRICT` 기준 반영 여부 검색 완료
  - `git diff --check` 통과

---

### 2026-07-08 | DB | MariaDB 연결 정보 환경 변수 로드 전환

- **커밋**: `db: 환경변수 기반 MariaDB 연결 설정`
- **변경 내용**:
  - `server/db/connection.py`의 MariaDB 비동기 접속 문자열 하드코딩을 제거하고 루트 `.env`의 `DB_*` 값을 조합해 사용하도록 변경했습니다.
  - `mysql+aiomysql` 기반 비동기 SQLAlchemy 엔진 설정은 유지하면서 `pool_pre_ping=True`, `pool_recycle=3600`, `expire_on_commit=False` 세션 팩토리 구성을 보존했습니다.
  - DB 연결에 필요한 런타임 의존성 항목을 `requirements.txt`의 고정 버전 목록에 정리했습니다.
- **관련 파일**: `server/db/connection.py`, `requirements.txt`
- **검증 결과**:
  - `.venv/bin/python -m py_compile server/db/connection.py` 통과
  - `.venv/bin/python -c "import server.db.connection as c; ..."` 기반 import 검증 통과
  - SQLAlchemy 엔진 URL은 비밀번호 마스킹 상태로 `mysql+aiomysql` 형식 확인
  - `git diff --check` 통과

---

### 2026-07-09 | DB | MariaDB Primary-Replica 실습 경로 정리 및 연결 모듈 정리

- **커밋**: `db: connection whitespace cleanup and replica notes`
- **변경 내용**:
  - Raspberry Pi 5B 16GB 단일 장비에서 `3306` Primary와 `3307` Replica를 분리 실행하는 1차 복제 실습 경로를 정리했습니다.
  - 향후 동일 스펙 별도 장비 추가 시 Primary-Replica, 자동 백업/복구 리허설, MaxScale/VIP 자동 페일오버 순서로 고도화하는 운영 방향을 정리했습니다.
  - MariaDB Replica 인스턴스의 AppArmor 프로파일(`mariadbd`)에서 `/var/lib/mysql-replica`, `/var/log/mysql-replica`, `/run/mysqld`, Raspberry Pi block device metadata 접근 허용이 필요한 원인을 확인했습니다.
  - `server/db/connection.py`의 `AsyncSession` 세션 팩토리 옵션 줄에 남아 있던 trailing whitespace를 제거했습니다.
- **관련 파일**: `server/db/connection.py`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `connection.py` import 검증 재실행 완료
  - `.venv/bin/python -m py_compile server/db/connection.py` 통과
  - `.venv/bin/python -c "import server.db.connection as c; ..."` 기반 SQLAlchemy URL 마스킹 출력 확인
  - `git diff --check` 통과

---

### 2026-07-09 | Docker | Compose 경량화, MariaDB 컨테이너 연결, 호스트 로컬 Ollama 전환

- **커밋**: `chore(docker): use host-local ollama with compose`
- **변경 내용**:
  - 프로젝트 루트 `.dockerignore`를 추가하여 실제 Docker build context에서 `.venv/`, `.env`, `.git/`, `client/`, `docs/`, 캐시·빌드 산출물 등이 제외되도록 정리했습니다.
  - `docker/.dockerignore`에는 실제 적용 파일이 루트 `.dockerignore`임을 안내하는 주석을 추가해, `docker/` 하위 ignore 파일만 보고 오해하지 않도록 보완했습니다.
  - `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`에 MariaDB 11.4 서비스를 추가하고, `Minchodan DB.session.sql` 초기화 SQL, `mariadb_data` 볼륨, healthcheck, `COMPOSE_DB_*` 환경 변수를 연결했습니다.
  - FastAPI 컨테이너의 DB 연결값을 compose 내부 기준(`DB_HOST=mariadb`, `DB_PORT=3306`)으로 오버라이드하여 `docker compose up` 시 로컬 MariaDB 컨테이너에 접속하도록 맞췄습니다.
  - 회의 결정에 따라 Ollama는 Docker Compose 서비스에서 제거하고, 호스트 로컬 Ollama(`ollama serve`)를 FastAPI 컨테이너가 `COMPOSE_OLLAMA_BASE_URL`로 호출하는 구조로 전환했습니다.
  - macOS 시작 스크립트는 Colima 실행 시 `host.lima.internal:11434`를 자동 선택하고, Linux/Windows 스크립트는 `host.docker.internal:11434` 기준의 호스트 Ollama 연결 흐름을 안내하도록 수정했습니다.
  - OS별 Docker 시작 스크립트의 시작 메시지, 모델 pull 안내, 로그/중지 명령을 `Redis + MariaDB + FastAPI` 3컨테이너와 호스트 로컬 Ollama 기준으로 정리했습니다.
  - `.env.example`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `SKILLS.md`, `docs/AGENTS.md`, `docs/README.md`, `docs/ops/environment_variables.md`, `docs/ops/deployment_guide.md`, `docs/ops/ai_model_hardware_setup.md`, `docs/ops/test_specification.md`를 새 Docker 실행 구조에 맞게 동기화했습니다.
- **관련 파일**: `.dockerignore`, `.env.example`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `SKILLS.md`, `docker/.dockerignore`, `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `docker/linux_docker_start.sh`, `docker/macos_docker_start.sh`, `docker/windows_docker_start.bat`, `docs/AGENTS.md`, `docs/README.md`, `docs/ops/environment_variables.md`, `docs/ops/deployment_guide.md`, `docs/ops/ai_model_hardware_setup.md`, `docs/ops/test_specification.md`
- **검증 결과**:
  - `docker compose --env-file .env -f docker/docker-compose.macos.yml config --quiet` 통과
  - `docker compose --env-file .env -f docker/docker-compose.yml config --quiet` 통과
  - `bash -n docker/macos_docker_start.sh docker/linux_docker_start.sh` 통과
  - `git diff --check` 통과
  - 실제 `docker compose up`은 이미지 빌드·컨테이너 기동 시간이 길 수 있어 이번 정리 작업에서는 실행하지 않았습니다.

---

### 2026-07-09 | iOS | Xcode MCP 로컬 설정 안내 및 스킬 경로 정리

- **커밋**: `docs(ios): document xcodebuildmcp local config`
- **변경 내용**:
  - `.xcodebuildmcp/config.yaml`에 남아 있던 개인 Mac 절대경로와 시뮬레이터/실기기 UDID를 제거하고, 각 개발자가 로컬에서 입력해야 할 값(`workspacePath`, `deviceId`, `scheme`, `platform`, `bundleId`)을 안내하는 템플릿 주석으로 정리했습니다.
  - `.agents/skills/xcode-build-management/SKILL.md`의 iOS 핵심 자산 링크를 특정 사용자 홈 디렉터리의 `file://` 절대경로에서 프로젝트 기준 상대경로로 변경했습니다.
  - `CoreMLInferenceBridge.swift` 링크를 실제 파일 위치인 `client/ios/CoreMLInferenceBridge.swift` 기준으로 정정했습니다.
- **관련 파일**: `.xcodebuildmcp/config.yaml`, `.agents/skills/xcode-build-management/SKILL.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `rg --files client/ios | rg "CoreMLInferenceBridge|Minchodan\\.xcworkspace|Podfile$"`로 iOS 핵심 파일 실제 위치 확인 완료
  - `git diff --check` 통과

---

### 2026-07-10 | DB | MariaDB Tailscale 외부망 연결 가이드 추가

- **커밋**: `docs(db): add tailscale mariadb guide`
- **변경 내용**:
  - macOS와 Windows 사용자를 분리한 MariaDB Tailscale 연결 절차 문서를 추가했습니다.
  - Tailscale DB Host, DB 이름, DB 사용자명은 플레이스홀더 기준으로 DBeaver 설정값과 `.env` 예시를 정리했습니다.
  - Tailscale 도달성, MariaDB 포트 도달성, DB 인증 실패를 구분하는 점검표와 트러블슈팅 표를 추가했습니다.
  - `docs/README.md` 문서 인덱스에 새 가이드 링크를 반영했습니다.
- **관련 파일**: `docs/db_tailscale_guide/README.md`, `docs/README.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `rg`로 Tailscale 초대 링크, 실제 Host, 실제 DB 사용자명 잔존 여부 확인 완료
  - `git diff --check` 통과

---

### 2026-07-10 | DB | 탐지 및 TTS 안내 로그 테이블 추가

- **커밋**: `db: add detection guidance log table`
- **변경 내용**:
  - 클라이언트 프레임 이벤트 기준의 탐지/안내 이력을 저장하기 위해 `detection_guidance_logs` 테이블 DDL을 추가했습니다.
  - 탐지 시점은 `detected_at`, YOLO 탐지 결과는 `detected_objects_json`, LLM이 사용자에게 출력한 전체 안내 문장은 `tts_text`에 저장하도록 구성했습니다.
  - 서버/클라이언트 이벤트 추적을 위한 `event_id`, 사용자/기기 연결을 위한 `user_id`, `device_id`, 반사/인지 스트림 구분을 위한 `stream_type`, DB 적재 시각 `created_at`을 함께 추가했습니다.
  - 로그성 데이터 보존을 위해 `app_users`, `user_devices` 참조는 `ON DELETE SET NULL` 정책으로 연결했습니다.
  - 기본 확인 설명을 기존 4개 테이블에서 5개 테이블 기준으로 갱신하고, 선택 검증 쿼리에 `SHOW CREATE TABLE detection_guidance_logs;`를 추가했습니다.
- **관련 파일**: `Minchodan DB.session.sql`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `git diff --check -- 'Minchodan DB.session.sql'` 통과
  - SQL 파일 내 신규 테이블 DDL 및 선택 검증 쿼리 위치 확인 완료
  - 실제 MariaDB 실행 검증은 이번 작업 범위에서 수행하지 않았습니다.

---

### 2026-07-10 | DB | 탐지 안내 로그 ORM 및 migration 파일 추가

- **커밋**: `db: add detection guidance ORM migration`
- **변경 내용**:
  - `detection_guidance_logs` 테이블을 SQLAlchemy ORM 기준 정의에 추가하고, `DetectionStreamType` enum과 사용자/기기 역방향 관계를 연결했습니다.
  - 탐지 안내 로그 생성/응답용 Pydantic DTO와 Repository 저장/조회 메서드를 추가했습니다.
  - SQLite 검증용 `server/db/schema.sql`에도 동일한 로그 테이블과 인덱스/FK 구조를 반영했습니다.
  - 운영 변경 이력 폴더 `server/db/migrations/`와 `20260710_001_add_detection_guidance_logs.sql` 증분 SQL 파일을 추가했습니다.
- **관련 파일**: `server/db/models.py`, `server/db/schemas.py`, `server/db/repositories.py`, `server/db/schema.sql`, `server/db/migrations/README.md`, `server/db/migrations/20260710_001_add_detection_guidance_logs.sql`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `.venv/bin/python -m py_compile server/db/models.py server/db/schemas.py server/db/repositories.py` 통과
  - `.venv/bin/python -c "from server.db.models import DetectionGuidanceLog; ..."` 기반 ORM import 검증 통과
  - `sqlite3 :memory: ".read server/db/schema.sql" ".tables"` 기반 SQLite DDL 실행 및 `detection_guidance_logs` 생성 확인
  - `git diff --check` 통과

---

### 2026-07-10 | Git | 최신 dev 브랜치 jy 병합 및 DB 충돌 해결

- **커밋**: `Merge remote-tracking branch 'origin/dev' into jy` (`c050a00`)
- **변경 내용**:
  - 최신 `origin/dev`(`10f2b12`)를 `jy` 브랜치에 병합하고, 병합 결과를 원격 `origin/jy`에 push했습니다.
  - `jy`의 기존 `detection_guidance_logs` ORM/migration 커밋(`0c98670`)과 `dev`의 탐지 안내 로그 서비스 확장 작업이 같은 DB 계층 파일을 수정해 발생한 충돌을 해결했습니다.
  - `server/db/models.py`는 `dev` 기준의 `StreamType`, `detection_guidance_logs` 관계명, MySQL JSON 호환 문자열 저장 구조를 유지하면서 `jy`의 로그 테이블 ORM 정의가 중복되지 않도록 정리했습니다.
  - `server/db/repositories.py`는 `DetectionGuidanceLogRepository`의 `get_by_event_id()` 중복 조회 메서드와 `create()` 저장 메서드가 모두 남도록 충돌 마커를 제거했습니다.
  - `server/db/schemas.py`는 중복 정의된 `DetectionGuidanceLogCreate`, `DetectionGuidanceLogResponse`를 제거하고, 서비스 코드와 맞는 `StreamType` 및 JSON 문자열 DTO 기준으로 통일했습니다.
- **관련 파일**: `server/db/models.py`, `server/db/repositories.py`, `server/db/schemas.py`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `python3 -m py_compile server/db/models.py server/db/repositories.py server/db/schemas.py server/services/detection_guidance_log_service.py` 통과
  - `git diff --check` 통과
  - `git rev-parse HEAD origin/jy origin/dev`로 `HEAD == origin/jy == c050a00`, `origin/dev == 10f2b12` 확인
  - `git log --oneline HEAD..origin/dev` 결과가 비어 있어 `dev`에만 있고 `jy`에 없는 커밋이 없음을 확인

---

### 2026-07-10 | Git | 개인 설정 파일 제외 규칙 문서화

- **커밋**: `docs(git): document local private config ignores`
- **변경 내용**:
  - `.gitignore` 하단의 `**/Copy_*` 규칙을 팀원이 이해할 수 있도록 개인 설정 파일 제외 가이드를 추가했습니다.
  - 이미 Git이 추적 중인 원본 파일은 `.gitignore`만으로 수정 제외되지 않는다는 주의사항을 명시했습니다.
  - `.xcodebuildmcp/config.yaml`은 공유 템플릿으로 유지하고, `.xcodebuildmcp/Copy_config.yaml`은 개인 설정 복사본으로 사용하는 운영 기준을 정리했습니다.
  - 커밋 전 `git check-ignore`, `git status`, `git status --ignored` 기반 점검 명령을 문서화했습니다.
- **관련 파일**: `.gitignore`, `docs/ops/local_private_config_guide.md`, `docs/README.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `git check-ignore -v .xcodebuildmcp/Copy_config.yaml`로 `**/Copy_*` 규칙 적용 확인
  - `git status --short --ignored .xcodebuildmcp ...`로 `Copy_config.yaml`이 ignored 상태(`!!`)임을 확인
  - `git diff --check` 통과

---

### 2026-07-11 | iOS/서버 | 실기기 빌드 의존성 및 FastAPI 루트 응답 정리

- **커밋**: `15cb978` (`iOS: 실기기 빌드 의존성 및 루트 응답 정리`)
- **변경 내용**:
  - 실기기 빌드 과정에서 미사용 `react-native-tts`, CocoaPods 1.17 잠금 결과, Xcode 26 프로젝트 자동 재작성, 개인 `DEVELOPMENT_TEAM` 값이 함께 반영되었습니다.
  - 후속 dev 병합 전 정합성 검토에서 `react-native-worklets-core`는 이미 기준선에 존재했고 `react-native-tts`는 런타임 import가 없음을 확인했습니다.
  - Xcode 26이 `shellScript`를 배열로 저장한 프로젝트 파일은 CocoaPods 1.17.0/xcodeproj 1.28.1의 깨끗한 `pod install`과 호환되지 않는 것도 확인했습니다.
  - FastAPI 서버 기본 경로(`/`)에 서비스 상태, 헬스체크 경로, Swagger 문서 경로, WebSocket 경로를 반환하는 루트 응답을 추가했습니다.
  - 실기기 확인과 세션 로그를 바탕으로 안전 판단 공백, 음성 상호작용 지연, 연결 신뢰성, 안내 품질 검증, 제품화 과제를 정리한 Mitos 보완점 문서를 추가했습니다.
- **관련 파일**: `client/package.json`, `client/package-lock.json`, `client/ios/Podfile.lock`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `server/main.py`, `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `client/ios/build-device-debug.log` 기준 `xcodebuild -workspace client/ios/Minchodan.xcworkspace -scheme Minchodan -configuration Debug -destination platform=iOS,id=... build` 실기기 Debug 빌드 성공 확인
  - 기존 Pods가 남아 있던 로컬 빌드 로그에서는 `BUILD SUCCEEDED`를 확인했으나, 후속 깨끗한 `pod install` 검증에서 Xcode 프로젝트 저장 형식 호환 실패를 확인
  - 빌드 로그 마지막 결과 `BUILD SUCCEEDED` 확인
  - `python3 -m py_compile server/main.py` 통과
  - `git diff --check` 통과
  - `server/main.py` 루트 응답은 정적 코드 diff 기준으로 확인했으며, 서버 기동 후 HTTP 요청 검증은 이번 작업 범위에서 아직 수행하지 않았습니다.
- **비고**:
  - `client/ios/build-device-debug.log`는 빌드 성공 근거로 확인했지만 현재 미추적 파일 상태이므로, 커밋 포함 여부는 커밋 직전에 별도 판단이 필요합니다.

---

### 2026-07-11 | 문서 | macOS Xcode 빌드 공유 가이드 문서화

- **커밋**: `6d38ae3` (`docs: macOS Xcode 빌드 공유 가이드 추가`)
- **변경 내용**:
  - `.vscode/xcode_mcp_setup_guide.md`의 Xcode MCP 설정 절차를 팀 공유 문서로 복사하여 `docs/macOS_xcode_build/xcode_mcp_setup_guide.md`를 추가했습니다.
  - `.vscode/ios_device_build_iteration_guide.md`의 iOS 실기기 빌드 및 수정 반복 절차를 공유 문서로 복사하여 `docs/macOS_xcode_build/ios_device_build_iteration_guide.md`를 추가했습니다.
  - 원본 `.vscode` 문서는 로컬 작업 노트로 보존하고, `docs/` 하위 복사본에는 팀원이 그대로 참고할 수 있도록 목적, 사전 준비, MCP 설정, 실기기 빌드, 설치/실행, 커밋 전 점검 절차를 정리했습니다.
  - 개인 Mac 절대경로, `file://` 링크, 실제 단말명, 실제 UDID/CoreDevice ID, 실제 bundle id, Apple 계정/Team 관련 값이 공유 문서에 노출되지 않도록 `<PROJECT_ROOT>`, `<XCODEBUILD_DEVICE_UDID>`, `<COREDEVICE_IDENTIFIER>`, `<IOS_BUNDLE_ID>` 등 안내 문구로 치환했습니다.
  - Xcode MCP 설정 문서에는 `xcodebuildmcp` 개요, `.xcodebuildmcp/config.yaml` 필드 설명, MCP 클라이언트 등록 예시, 오동작 대처 기준, 개인값 점검 명령을 정리했습니다.
  - iOS 단말 빌드 반복 문서에는 환경 확인, 단말 연결 확인, Signing Team 설정, Metro 실행, CLI 빌드, `devicectl` 설치/실행, 앱 확인 체크리스트, 재빌드 판단 기준을 정리했습니다.
- **관련 파일**: `docs/macOS_xcode_build/xcode_mcp_setup_guide.md`, `docs/macOS_xcode_build/ios_device_build_iteration_guide.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `rg`로 `file:///`, `/Users/<LOCAL_USER>`, 실제 단말명, 실제 bundle id, Apple 개발자 계정/Team 식별자 잔존 여부 확인 완료
  - `git diff --check -- docs/macOS_xcode_build docs/changelogs/jy.md` 통과
  - 기존 미추적 빌드 로그 `client/ios/build-device-debug.log`는 이번 문서 커밋 대상에서 제외했습니다.

---

### 2026-07-11 | iOS/문서 | dev 병합 전 정합성 차단 사항 정리

- **커밋**: (이번 커밋)
- **변경 내용**:
  - `client/ios/Minchodan.xcodeproj/project.pbxproj`, `Podfile.lock`, `package.json`, `package-lock.json`을 `origin/dev` 기준으로 복구하여 Xcode 26 자동 재작성, 개인 Signing Team, 미사용 `react-native-tts`와 잠금 파일 노이즈를 제거했습니다.
  - 루트 `PROJECT_IMPROVEMENTS_MITOS.md`를 v0.2.0으로 갱신하여 `3e7ab52`에서 해결된 STT 위험 문구와 전사문 저장 문제를 완료 상태로 분리했습니다.
  - 중복된 `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md`를 제거하고 `docs/README.md`가 루트 정본을 가리키도록 수정했습니다.
  - 과거 iOS 작업과 macOS 가이드 changelog를 실제 diff와 커밋 해시에 맞게 정정했습니다.
- **관련 파일**: `client/package.json`, `client/package-lock.json`, `client/ios/Podfile.lock`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `PROJECT_IMPROVEMENTS_MITOS.md`, `docs/README.md`, `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md`, `docs/changelogs/jy.md`
- **검증 결과**: `npm ci`, `tsc --noEmit`, `server/main.py`·`server/db/models.py` `py_compile`, `git diff --check` 통과. CocoaPods 1.17.0은 복구된 Xcode 프로젝트를 정상 파싱하고 autolinking까지 완료했으며, `pod install --deployment`는 저장소 기준 1.16.2와 로컬 1.17.0의 4개 Pod 체크섬·도구 버전 차이만 보고했습니다.
- **비고**: `client/ios/build-device-debug.log`는 기존 미추적 상태로 유지하며 커밋에 포함하지 않습니다.

---

### 2026-07-11 | Git | 최신 dev 병합 및 정합성 충돌 해소

- **커밋**: (이번 병합 커밋)
- **변경 내용**:
  - `origin/dev`(`3e7ab52`)를 `jy`에 일반 병합하여 STT·반사 경보 안전 패치와 CoreML FP16+ANE 변경을 통합했습니다.
  - 유일한 명시적 충돌인 `.gitignore`는 `dev`의 LF 버전과 `.zcode/`, `.claude/`, 에이전트 스크립트 제외 규칙을 유지하고 `jy`의 `**/Copy_*` 규칙을 추가하는 방식으로 해소했습니다.
  - CocoaPods 1.17.0으로 네이티브 의존성을 재생성하여 미사용 `TextToSpeech` Pod 제거와 96개 Pod 설치를 확인한 뒤, 추적 `Podfile.lock`은 저장소 기준 1.16.2 체크섬으로 유지했습니다.
- **관련 파일**: `.gitignore`, `docs/changelogs/jy.md` 및 `origin/dev`의 신규 커밋 전체
- **검증 결과**: 서버 테스트 130건 통과·2건 건너뜀(`test_ws_echo.py`, 기존 비결정적 RAG E2E 제외), `tsc --noEmit`, SQLite 5개 테이블 생성, 변경 Python 파일 `py_compile`, CocoaPods 설치, iOS 기기용 Debug 무서명 빌드, `git diff --check` 통과.
- **비고**: `dev` 브랜치와 `origin/dev`에는 아직 `jy`를 병합하지 않았습니다. 본 커밋과 `origin/jy` push 이후 별도 승인 단계로 진행합니다.

---

### 2026-07-13 | iOS/서버/문서 | ngrok 외부 터널에서 Tailscale 외부망 접속 및 RTT 계측 경로 전환

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 기존 외부망 테스트는 `ngrok` 공개 터널 도메인을 통해 FastAPI WebSocket 서버에 접속하는 방식이었으나, 데모·실기기 테스트에서는 터널 중계 구간의 지연과 도메인 변경 가능성이 병목이 될 수 있었습니다.
  - iPhone이 Wi-Fi가 아닌 셀룰러 데이터 환경에 있어도 서버와 같은 tailnet에만 들어오면 접속할 수 있도록, 클라이언트 외부망 모드를 `ngrok` 단일 경로에서 `tailscale` 선택 경로로 확장했습니다.
  - 속도 개선 여부를 감으로 판단하지 않도록, 카메라 인코딩·프레임 디코딩·YOLO 추론·TTS 지연을 제외한 순수 WebSocket RTT만 별도 측정하는 `network_probe` 계약을 추가했습니다.
- **클라이언트 변경 내용**:
  - `client/src/config/index.ts`에 `NetworkMode = "lan" | "ngrok" | "tailscale"` 타입과 `EXPO_PUBLIC_NETWORK_MODE`, `EXPO_PUBLIC_TAILSCALE_HOST`, `EXPO_PUBLIC_SERVER_PORT` 기반 URL 생성 규칙을 추가했습니다.
  - `EXPO_PUBLIC_NETWORK_MODE=tailscale`일 때 앱이 `ws://{EXPO_PUBLIC_TAILSCALE_HOST}:{EXPO_PUBLIC_SERVER_PORT}/ws/detect`로 접속하도록 하여, Wi-Fi/LAN 주소와 ngrok 도메인을 거치지 않는 Tailscale 직접 경로를 만들었습니다.
  - `client/src/services/serverTransport.ts`에서 외부망 모드일 때 버튼 라벨을 `연결: Tailscale` 또는 `연결: ngrok`으로 표시하고, Tailscale/ngrok 모드에서는 Wi-Fi/USB 토글이 실제 접속 주소를 바꾸지 않도록 정리했습니다.
  - `client/src/hooks/useWebSocket.ts`에 `EXPO_PUBLIC_NETWORK_BENCHMARK=true`일 때 주기적으로 `network_probe`를 전송하는 로직을 추가하고, `network_probe_ack` 수신 시 최신 RTT와 최근 30개 평균 RTT를 계산하도록 했습니다.
  - `client/src/components/CameraView.tsx` 디버그 오버레이에 `망RTT: ...ms (평균 ...ms)` 줄을 추가하여, iOS 실기기에서 셀룰러 데이터 + Tailscale 연결 품질을 앱 화면에서 바로 확인할 수 있게 했습니다.
  - `client/src/types/detection.ts`에 `network_probe_ack` 메시지 타입과 `probe_id`, `payload_bytes`, `server_received_ts`, `server_sent_ts` 필드를 추가해 서버 응답 계약을 타입에 반영했습니다.
  - `client/.env.example`을 추가하여 Tailscale 실기기 테스트에 필요한 `EXPO_PUBLIC_NETWORK_MODE=tailscale`, `EXPO_PUBLIC_TAILSCALE_HOST`, `EXPO_PUBLIC_NETWORK_BENCHMARK=true` 예시를 별도 템플릿으로 제공했습니다.
- **서버 변경 내용**:
  - `server/api/ws_router.py`의 `/ws/detect` 메인 수신 루프에 `network_probe` 분기를 추가했습니다.
  - 서버는 `network_probe`를 받으면 탐지 파이프라인, Redis Streams, RAG, LLM, TTS를 거치지 않고 즉시 `network_probe_ack`를 반환합니다.
  - 응답에는 `probe_id`, `client_sent_ts`, `client_label`, `payload_bytes`, `server_received_ts`, `server_sent_ts`를 담아, 앱과 CLI 스크립트가 동일한 계약으로 RTT를 계산할 수 있게 했습니다.
  - `server/api/ws_router.py` 상단에 UTF-8 선언을 추가하여 프로젝트 Python 파일 헤더 규칙과 맞췄습니다.
- **벤치마크 도구 변경 내용**:
  - `scripts/benchmark_ws_network.py`를 추가하여 `ngrok`, `tailscale`, `lan` 등 여러 WebSocket target을 같은 방식으로 측정할 수 있게 했습니다.
  - 스크립트는 `welcome` 수신 후 `hello` 인증과 `auth_ok`까지의 handshake 시간을 따로 측정하고, `network_probe` 왕복 RTT에 대해 평균, p50, p95, max, 실패 수를 출력합니다.
  - `--json-out`, `--csv-out` 옵션을 제공하여 반복 측정 결과를 파일로 보존할 수 있게 했습니다.
  - `websockets` 패키지는 실제 측정 시점에 lazy import하도록 구성하여, 의존성이 없는 환경에서도 `--help` 출력은 정상 동작하도록 했습니다.
- **문서 동기화 내용**:
  - `docs/ops/environment_variables.md`에 `EXPO_PUBLIC_NETWORK_MODE`, `EXPO_PUBLIC_TAILSCALE_HOST`, `EXPO_PUBLIC_SERVER_PORT`, `EXPO_PUBLIC_NETWORK_BENCHMARK`, `EXPO_PUBLIC_NETWORK_BENCHMARK_INTERVAL_MS`, `EXPO_PUBLIC_NETWORK_BENCHMARK_PAYLOAD_BYTES`를 추가했습니다.
  - `docs/ops/android_wifi_usb_transport.md`를 Wi-Fi/USB뿐 아니라 Tailscale 외부망까지 포함하는 모바일 접속 운영 가이드로 확장했습니다.
  - `docs/mobile/ios_android_bifurcation_contract.md`에 iOS 앱의 Tailscale 외부망 URL 생성 규칙과 앱 내 `network_probe` RTT 표시 계약을 반영했습니다.
  - `docs/design/api_specification.md`에 `network_probe`/`network_probe_ack` 메시지 계약을 추가하여 `/ws/detect` API 명세와 실제 서버 구현을 맞췄습니다.
  - `docs/ops/network_latency_benchmark.md`를 새로 추가하여 iOS 셀룰러 + Tailscale 전제, Metro 재번들 절차, CLI 비교 측정 명령, 결과 해석 기준을 정리했습니다.
- **운영 및 테스트 기준 정리**:
  - iOS 앱 실측은 `client/.env`에 `EXPO_PUBLIC_NETWORK_MODE=tailscale`, `EXPO_PUBLIC_TAILSCALE_HOST=<SERVER_TAILSCALE_IP_OR_MAGICDNS>`, `EXPO_PUBLIC_NETWORK_BENCHMARK=true`를 설정한 뒤 `cd client && npx expo start -c`로 Metro 캐시를 초기화해 진행하는 기준으로 정리했습니다.
  - CLI 비교 측정은 앱과 같은 `device_id`를 동시에 쓰면 서버 세션이 교체될 수 있으므로, 순수 네트워크 비교 시에는 앱을 종료하고 실행하거나 별도 벤치마크용 `device_id`/토큰을 쓰는 기준으로 정리했습니다.
  - `improve` 열은 첫 번째 `--target`의 평균 RTT를 기준으로 뒤 target의 개선율을 계산하므로, ngrok 대비 Tailscale 개선률을 보고 싶을 때는 `--target ngrok=...`을 첫 번째, `--target tailscale=...`을 두 번째로 두는 방식으로 안내했습니다.
  - Tailscale 단일 target 실측에서 `samples=50`, `fail=0`, `avg=5.30ms`, `p50=3.75ms`, `p95=11.94ms`, `max=13.94ms`가 확인되어, 현재 환경 기준 순수 WebSocket RTT는 안정적으로 낮은 편임을 확인했습니다. 실제 Tailscale IP와 토큰은 문서에 기록하지 않았습니다.
  - Docker Compose는 `server/`, `scripts/`를 볼륨 마운트하므로 로컬 컨테이너 테스트에서는 FastAPI 컨테이너 재시작만으로 코드 변경이 반영될 수 있고, 이미지 자체를 배포 레지스트리에 push하려면 Dockerfile의 코드 내장 전략을 별도 검토해야 함을 정리했습니다.
- **관련 파일**: `client/src/config/index.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `client/src/services/serverTransport.ts`, `client/src/types/detection.ts`, `client/.env.example`, `server/api/ws_router.py`, `scripts/benchmark_ws_network.py`, `docs/design/api_specification.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/ops/android_wifi_usb_transport.md`, `docs/ops/environment_variables.md`, `docs/ops/network_latency_benchmark.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `python3 -m py_compile scripts/benchmark_ws_network.py server/api/ws_router.py server/api/session_manager.py` 통과
  - `git diff --check` 통과
  - `cd client && npx tsc --noEmit` 통과
  - `python3 scripts/benchmark_ws_network.py --help` 정상 출력 확인
  - Tailscale 단일 target 기준 `network_probe` 50개 샘플 수집, 실패 0건, 평균 RTT 5.30ms 확인
- **비고**:
  - `client/.env`와 루트 `.env`의 실제 Tailscale Host, device token, ngrok domain 값은 로컬 비밀/환경값으로 취급하며 changelog에 남기지 않습니다.
  - ngrok 컨테이너나 ngrok 도메인 지원을 제거한 것이 아니라, `lan`/`ngrok`/`tailscale`을 선택 가능한 네트워크 모드로 확장한 작업입니다.

---

### 2026-07-13 | iOS/클라이언트/문서 | LiDAR 거리 필드 우선 표시 및 반사 게이트 fallback 구조 적용

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 단말 "거리측정" 토글은 `DepthProbeBridge` 자체 캡처 세션 기반 계측용 프로토타입이라, 기존 객체 탐지 bbox와 동기화된 실거리로 직접 쓰기 어려웠습니다.
  - 객체별 실거리 융합으로 가기 위한 선행 단계로, 클라이언트 탐지 결과 타입과 화면/반사 게이트가 `distanceMeters`를 우선 소비하고, 값이 없으면 기존 bbox 휴리스틱으로 fallback하는 구조를 먼저 적용했습니다.
- **변경 내용**:
  - `DetectionResult`와 `ServerDetectionResult`에 `distanceMeters`, `distanceSource`, `depthSampleCount`, `depthAccuracy` optional 필드를 추가했습니다.
  - `CameraView.tsx`에 거리 해석 helper를 추가하여 BBox 라벨과 탐지 요약을 `LiDAR` 또는 `추정`으로 구분 표시하도록 바꿨습니다.
  - 단말 반사 게이트는 LiDAR 값이 있는 경우 0.5m/1.0m/1.5m/3.0m 기준으로 우선 판단하고, LiDAR 값이 없을 때만 기존 면적 ratio 기반 주차센서식 판정을 유지합니다.
  - `DepthProbeBridge.swift`와 `depthProbe.ts`에 bbox 중앙 50% 영역 7x7 grid 샘플링, 최소 8개 유효 샘플, 25퍼센타일 거리 계산 helper(`probeBoxes`)를 추가했습니다.
  - `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`를 LiDAR 우선/fallback 구현 상태와 실기기 video+depth 동기화 검증 잔여 상태로 갱신했습니다.
- **관련 파일**: `client/src/inference/types.ts`, `client/src/types/detection.ts`, `client/src/components/CameraView.tsx`, `client/src/services/depthProbe.ts`, `client/ios/DepthProbeBridge.swift`, `client/ios/DepthProbeBridge.mm`, `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `cd client && npx tsc --noEmit` 통과
  - `xcodebuild -workspace Minchodan.xcworkspace ...`는 현재 실행 환경에서 `.xcworkspace` 인식 오류와 CoreSimulator 로그 권한 오류로 완료하지 못했습니다.
  - 대체로 `xcodebuild -project Minchodan.xcodeproj ...`를 실행했으나, 서명 설정에서는 provisioning profile 부재로 실패했고, `CODE_SIGNING_ALLOWED=NO`에서는 `sandbox-exec: sandbox_apply: Operation not permitted`로 CoreML 모델 컴파일 단계가 차단되어 최종 iOS 빌드 완료까지는 확인하지 못했습니다.
- **비고**:
  - 이번 작업은 `distanceMeters` 소비 경로와 bbox depth 샘플링 helper까지의 부분 해소입니다. 정식 객체별 실거리 경보로 승격하려면 VisionCamera video frame과 LiDAR depth map이 같은 세션·같은 타임스탬프·같은 640x640 crop 좌표계임을 실기기에서 검증해야 합니다.

---

### 2026-07-13 | iOS/클라이언트/문서 | `거리측정` 계측용 LiDAR 프로브 동기화 프리뷰 적용

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 기존 `거리측정` 버튼은 `DepthProbeBridge`의 별도 depth 세션에서 고정 3점 값만 읽고, 같은 세션의 실제 카메라 프리뷰를 화면에 보여주지 않았습니다.
  - 그 결과 사용자가 보고 있다고 생각한 벽/물체 위치와 LiDAR depth 샘플 좌표가 정합된다고 보장할 수 없어, 줄자 실측과 앱 표시값이 크게 어긋날 수 있었습니다.
  - 이번 작업의 우선순위는 일반 객체 bbox별 `distanceMeters` 융합이 아니라, 앱 하단 `거리측정` 버튼으로 켜지는 운영자/계측용 프로토타입 자체를 줄자 검증 가능한 상태로 만드는 것입니다.
- **변경 내용**:
  - `DepthProbeBridge.swift`에 `AVCaptureVideoDataOutput`을 추가하고, `AVCaptureDepthDataOutput`과 `AVCaptureDataOutputSynchronizer`로 묶어 video+depth를 같은 네이티브 세션에서 동기화했습니다.
  - `probe()` 결과에 같은 세션에서 생성한 1:1 정사각형 프리뷰 JPEG(`previewUri`)와 `synchronizedAt`, 샘플별 `sampleCount`를 함께 반환하도록 확장했습니다.
  - depth 샘플 좌표를 전체 depth map 기준이 아니라 화면에 보이는 1:1 center square crop 기준으로 변환하도록 수정했습니다.
  - 점 샘플은 기존 3x3 이웃에서 5x5 이웃 미디언으로 넓혀 단일 픽셀 노이즈 영향을 줄였습니다.
  - `CameraView.tsx`의 `거리측정` 모드에서 VisionCamera가 꺼진 동안에도 네이티브 LiDAR 세션 프리뷰를 표시하고, 중앙/전방 하단/발밑 샘플 마커와 거리값을 프리뷰 위에 같이 표시하도록 변경했습니다.
  - `거리측정` 모드가 켜져 있을 때는 단말 캡처 루프와 서버 `detection_control`을 OFF로 보내 stale bbox와 반사 경보가 계측 화면에 섞이지 않도록 했습니다.
  - `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`에 계측용 버튼 개선 상태와 객체별 정식 fusion 잔여 조건을 분리해 기록했습니다.
- **구현 상세**:
  - 네이티브 세션 구성은 `builtInLiDARDepthCamera` 입력 1개에 `AVCaptureVideoDataOutput`과 `AVCaptureDepthDataOutput`을 동시에 붙이는 방식입니다.
  - video/depth 연결은 모두 portrait 기준으로 맞추고, video mirroring은 끈 상태로 유지합니다.
  - JS 화면의 카메라 프레임은 1:1 정사각형이므로, depth map도 전체 map 좌표가 아니라 center square crop 좌표로 변환해 `중앙`, `전방 하단`, `발밑` 샘플을 읽습니다.
  - `previewUri`는 같은 동기화 세션의 video buffer를 640x640 JPEG data URI로 변환한 값이며, `CameraView.tsx`는 이 이미지를 계측 화면의 실제 프리뷰로 사용합니다.
  - 각 샘플 행의 괄호 숫자는 해당 지점 주변 5x5 이웃에서 유효한 depth 픽셀 수입니다. 값이 낮으면 표면 반사, 저조도, 유리/검정 표면 등으로 샘플 신뢰도가 낮을 수 있습니다.
- **관련 파일**: `client/ios/DepthProbeBridge.swift`, `client/src/services/depthProbe.ts`, `client/src/components/CameraView.tsx`, `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `cd client && npx tsc --noEmit` 통과
  - `git diff --check` 통과
  - `xcodebuild -project client/ios/Minchodan.xcodeproj -scheme Minchodan -configuration Debug -destination generic/platform=iOS -derivedDataPath client/ios/build-lidar-probe-check CODE_SIGNING_ALLOWED=NO build` 실행 시 Swift 산출물은 생성됐으나, 기존과 같은 CoreML 모델 컴파일 sandbox 오류(`sandbox-exec: sandbox_apply: Operation not permitted`) 및 `__preview.dylib` 링크 오류로 최종 iOS 빌드는 완료하지 못했습니다.
- **실기기 확인 절차**:
  - Swift 네이티브 코드 변경이므로 Metro reload만으로는 반영되지 않습니다. `npx expo start -c --dev-client --host lan` 실행 후 Xcode에서 실제 iPhone 대상으로 재빌드해야 합니다.
  - 앱 본화면 진입 후 `탐지 시작`을 누르지 않아도 `거리측정` 버튼만으로 계측 모드를 시작할 수 있습니다.
  - 정상 화면은 `LiDAR 프리뷰 준비 중...`이 잠깐 보인 뒤, 네이티브 LiDAR 세션 프리뷰 위에 `중앙`, `전방 하단`, `발밑` 마커와 거리값이 표시되는 상태입니다.
  - 줄자 검증은 카메라 렌즈면 기준으로 0.5m, 1.0m, 2.0m 지점을 맞추고, 폰을 벽과 최대한 수직으로 둔 상태에서 우선 `중앙` 값을 비교합니다.
  - 벽면, 박스, 의자처럼 난반사가 적고 평평한 표면부터 확인하고, 유리, 거울, 검정 유광 물체, 강한 역광 표면은 별도 실패 표면으로 분리 기록합니다.
- **비고**:
  - 이번 수정은 `거리측정` 버튼 자체를 줄자 검증 가능한 계측 화면으로 개선하는 작업입니다.
  - 일반 객체 탐지 bbox에 `LiDAR` 거리 라벨을 붙이는 정식 경로는 여전히 별도 과제이며, VisionCamera 탐지 프레임과 depth map을 같은 세션·같은 타임스탬프·같은 640x640 crop 좌표계로 묶는 후속 구현이 필요합니다.
  - 실기기에서 여전히 큰 오차가 나면 다음 우선 확인 대상은 프리뷰 방향 180도 보정 필요 여부, depth orientation, 렌즈 기준 줄자 위치, 기기와 벽의 수직 정렬입니다.

---

### 2026-07-14 | 운영 환경 | OS·아키텍처별 PyTorch 휠 분리 및 콘솔 favicon 갱신

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 병합 후 macOS Python 3.13 가상환경에서 `pip install -r requirements.txt`를 실행하면 공식 휠이 없는 `torch==2.12.1+cu128`을 요청하여 설치가 중단됐습니다.
- **변경 내용**:
  - macOS와 Apple Silicon 기반 Linux 컨테이너는 PyPI의 `torch==2.12.1`/`torchvision==0.27.1`을 사용하도록 환경 마커를 추가했습니다.
  - Linux x86_64와 Windows GPU 환경은 공식 cu128 인덱스에 존재하는 `torch==2.11.0+cu128`/`torchvision==0.26.0+cu128` 호환 조합을 선택하도록 정정했습니다.
  - `docs/ops/ai_model_hardware_setup.md`의 설치 기준을 실제 `requirements.txt`와 동기화했습니다.
  - 운영 콘솔의 브라우저·Apple 디바이스 favicon 링크와 16x16·32x32·180x180 자산을 추가했습니다.
- **관련 파일**: `requirements.txt`, `console/index.html`, `console/public/favicon.ico`, `console/public/favicon-16x16.png`, `console/public/favicon-32x32.png`, `console/public/apple-touch-icon.png`, `.gitignore`, `docs/ops/ai_model_hardware_setup.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - macOS arm64, Python 3.13.14 가상환경에서 `python -m pip install -r requirements.txt` 재실행 성공
  - `python -m pip check` 및 `git diff --check` 통과
  - `console` 운영 빌드(`tsc --noEmit`, `vite build`) 통과

---

### 2026-07-14 | iOS/클라이언트/문서 | LiDAR 동기화 데이터의 렌즈·광선 거리 보정 적용

- **커밋**: (이번 커밋)
- **변경 배경**:
  - `dev` 업데이트 후 새 iOS 앱 빌드에서 `거리측정` 기능이 실제 줄자 거리와 크게 어긋나는 현상이 확인됐습니다. 특히 0.5m 이하에서는 앱 표시가 1m 근방으로 튀고, 0.6m 이상에서는 실제 거리보다 짧아졌다가 멀어지는 값 흔들림이 간헐적으로 나타났습니다.
  - 직전 개선으로 `DepthProbeBridge`는 같은 `AVCaptureSession` 안에서 video+depth를 동기화하고 1:1 crop 좌표를 맞추는 단계까지 적용됐지만, `AVDepthData`가 가질 수 있는 렌즈 왜곡과 픽셀별 카메라 광선 방향은 아직 거리 산식에 반영하지 않았습니다.
  - Apple AVFoundation의 LiDAR depth 캡처 흐름은 RGB/depth 동기화와 `AVCameraCalibrationData` 활용을 전제로 하므로, 프레임 쌍이 같은 시각에 도착했는지뿐 아니라 해당 depth frame에 보정 데이터가 붙어 있는지도 계측 신뢰 조건으로 올렸습니다.
  - 단, 렌즈·광선 보정은 특히 화면 가장자리와 비스듬한 표면에서 의미가 크며, 화면 중앙에서 0.5m가 1m로 두 배 튀는 현상을 단독으로 설명하기는 어렵습니다. 따라서 이번 수정은 왜곡·광선 산식 누락을 제거하는 1차 확정 조치이고, 실기기 줄자 검증으로 남은 원인 후보를 좁히는 구조까지 같이 마련했습니다.
- **네이티브 동기화 변경 내용**:
  - `AVCaptureDataOutputSynchronizer` delegate에서 `AVCaptureSynchronizedDepthData`와 `AVCaptureSynchronizedSampleBufferData`가 모두 존재하고 drop되지 않았을 때만 최신 depth/video frame을 갱신하도록 조건을 강화했습니다.
  - `syncedDepth.depthData.cameraCalibrationData`가 없는 프레임은 계측 입력에서 제외하여, 보정 산식을 적용할 수 없는 depth map이 `probe()` 또는 `probeBoxes()` 결과에 섞이지 않게 했습니다.
  - `depthOutput.alwaysDiscardsLateDepthData = true`를 설정해 늦게 도착한 depth frame이 최신 video frame과 섞일 가능성을 낮췄습니다.
  - serial `queue` 안에서 `latestDepth`, `latestVideoBuffer`, `latestSynchronizedAt`을 함께 갱신하여 JS가 읽는 프리뷰와 depth 샘플의 시점 불일치를 줄였습니다.
- **거리 보정 산식 변경 내용**:
  - `DepthSampleValue`를 추가해 보정 전 z축 depth(`axialMeters`)와 보정 후 카메라-표면 거리(`calibratedMeters`)를 한 쌍으로 보관합니다.
  - `lensDistortionLookupTable`, `lensDistortionCenter`, `intrinsicMatrixReferenceDimensions`를 사용해 샘플 좌표의 방사형 렌즈 왜곡을 보간 보정하는 `rectifiedPoint` helper를 추가했습니다.
  - `intrinsicMatrix`의 `fx`, `fy`, `cx`, `cy`로 정규화 카메라 광선 벡터를 복원하고, `sqrt(1 + x^2 + y^2)` 광선 스케일을 원본 z축 depth에 곱해 카메라-표면 거리를 계산하는 `calibratedDistance` helper를 추가했습니다.
  - `probe()`의 단일 지점 5x5 미디언과 `probeBoxes()`의 bbox 중앙 50% 영역 7x7 grid 25퍼센타일 모두 보정 거리 기준으로 반환하도록 바꿨습니다.
  - 보정에 실패한 샘플은 유효 샘플에서 제외하여, 일부 픽셀만 보정 가능한 상태에서 무리하게 원본 z값을 섞지 않도록 했습니다.
- **클라이언트 표시 및 디버깅 변경 내용**:
  - `client/src/services/depthProbe.ts` 타입에 `axialMeters`, `quality`, `calibrated` 필드를 추가했습니다.
  - `CameraView.tsx`의 거리측정 오버레이에 보정 적용 여부, depth 정확도, depth 품질을 표시하도록 했습니다.
  - 화면 표시와 개발 로그에 보정 거리(`meters`)와 원본 z축 depth(`axialMeters`)를 함께 노출해, 실기기 A/B 측정 시 보정 산식이 실제로 값을 얼마나 바꾸는지 바로 비교할 수 있게 했습니다.
- **문서 동기화 내용**:
  - `docs/mobile/ios_android_bifurcation_contract.md`에 iOS 전용 `DepthProbeBridge`가 video/depth 동기화뿐 아니라 `cameraCalibrationData` 기반 렌즈·광선 거리 보정을 수행한다는 계약을 추가했습니다.
  - `docs/design/risk_ssot_contract.md`에 단말 LiDAR 거리값은 보정 적용 상태까지 실기기 줄자 검증이 필요하며, 정식 객체별 반사 거리와 서버 bbox 휴리스틱은 아직 완전 동등하지 않다는 기술 부채를 명시했습니다.
  - `docs/research/mitos_improvement_roadmap.md`의 거리 추정 항목을 `부분 해소` 상태로 갱신하고, 남은 과제를 계측용 버튼 줄자 실측과 객체 탐지 프레임-depth map 정식 fusion 검증으로 분리했습니다.
- **관련 파일**: `client/ios/DepthProbeBridge.swift`, `client/src/services/depthProbe.ts`, `client/src/components/CameraView.tsx`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/design/risk_ssot_contract.md`, `docs/research/mitos_improvement_roadmap.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `cd client && npx tsc --noEmit` 통과
  - `git diff --check` 통과
  - `xcodebuild -workspace client/ios/Minchodan.xcworkspace -scheme Minchodan -configuration Debug -destination 'generic/platform=iOS' -derivedDataPath /tmp/minchodan-lidar-calibration-workspace-build CODE_SIGNING_ALLOWED=NO build` 통과
  - 무서명 Debug iOS 앱 산출물 생성 확인: `/tmp/minchodan-lidar-calibration-workspace-build/Build/Products/Debug-iphoneos/Minchodan.app`
- **잔여 실기기 검증**:
  - 렌즈면 기준 0.3m, 0.5m, 1.0m, 2.0m의 평평한 무광 표면을 중앙·좌측·우측 지점에서 각각 측정해 보정 거리(`meters`)와 원본 z축 depth(`axialMeters`)를 함께 기록합니다.
  - 같은 거리에서 단말을 벽과 수직으로 둔 경우와 10~20도 기울인 경우를 나눠 측정해, 렌즈·광선 보정이 가장자리와 기울어진 표면에서 기대한 방향으로 작동하는지 확인합니다.
  - 0.5m 이하에서 여전히 1m 근방으로 표시되면 이번 보정 산식보다 orientation/crop 매핑, depth map 해상도 좌표 변환, 렌즈면이 아닌 화면/케이스 기준 줄자 측정, 유리·검정 유광 표면 같은 LiDAR 취약 표면을 우선 재점검합니다.
  - 정식 객체별 거리 경보로 승격하려면 VisionCamera 탐지 프레임과 LiDAR depth의 동일 세션·동일 타임스탬프·동일 640x640 crop 좌표계 fusion 검증이 별도로 필요합니다.
- **비고**:
  - 이번 변경은 `거리측정` 계측 버튼 경로의 신뢰 조건과 보정 산식을 강화한 작업입니다. 일반 객체 탐지 bbox에 들어오는 `distanceMeters` 계약은 유지되지만, 모든 탐지 객체가 보정된 LiDAR 실거리를 받는 정식 fusion 단계까지 완료된 것은 아닙니다.
  - 보정 후 값이 원본 z축 depth와 거의 같게 보이는 중앙 지점도 정상일 수 있습니다. 광선 스케일은 중심부에서 1에 가깝고, 차이는 보통 가장자리나 기기 각도 변화에서 더 잘 드러납니다.

---

### 2026-07-17 | 배포 | Docker 외부 DB 보존 및 iOS Pod 정합화

- **커밋**: (이번 커밋)
- **변경 배경**:
  - DB와 중앙 이미지 저장 API는 기존 외부 서비스를 그대로 사용해야 하므로, Linux Compose가 `DB_HOST=mariadb`로 강제 전환하던 동작을 제거할 필요가 있었습니다.
  - iOS 의존성 설치 결과와 Xcode 프로젝트의 Expo Dev Client 리소스 목록을 현재 `client/package.json` 기준으로 맞출 필요가 있었습니다.
- **변경 내용**:
  - `docker/docker-compose.yml`의 FastAPI `DB_HOST`가 `.env`의 기존 원격 DB 값을 우선 유지하고, 필요할 때만 `COMPOSE_DB_HOST`로 재정의되도록 변경했습니다.
  - 중앙 이미지 저장 API 관련 환경 변수는 Compose에서 재정의하지 않고 기존 `.env` 값을 그대로 전달합니다.
  - `pod install` 결과에 맞춰 `Podfile.lock`과 Xcode 프로젝트의 Expo Dev Client 리소스 참조를 동기화했습니다.
  - `docs/ops/environment_variables.md`와 `docs/ops/deployment_guide.md`의 DB 대상 선택 규칙을 실제 Compose 동작과 동기화했습니다.
- **검증 결과**:
  - `docker compose --env-file .env -f docker/docker-compose.yml config --quiet` 통과
  - `Podfile.lock` YAML 파싱 및 Xcode 프로젝트 plist 파싱 통과
  - `git diff --check` 통과
- **비고**:
  - 실제 호스트/IP가 포함된 `client/ios/Minchodan/AppDelegate.swift`, `client/src/config/index.ts`와 로컬 `.env` 파일은 이번 커밋에서 제외했습니다.

---

### 2026-07-18 | 설계 | 휴리스틱 거리 구역 기반 알림 라우팅 구현 계획 수립

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 현장 테스트에서 객체 탐지 알림이 과도하게 반복되어 비프·햅틱·TTS 알림 피로를 유발하는 문제가 확인됐습니다.
  - 서버 면적비 구역, 서버 bbox 하단 의사 거리, 단말 면적비 휴리스틱, 수동 LiDAR 거리 기준이 서로 다른 의미로 사용되어 Near/Medium/Far 경로를 단일 규칙으로 적용하기 어려웠습니다.
- **변경 내용**:
  - 현행 서버·클라이언트·WebSocket·억제기·Fast Lane·LiDAR 검증 경로와 관련 설계 문서를 교차 감사했습니다.
  - 일반 객체는 유효 Near에서 비프·햅틱 반사 경로, Medium/Far에서 발화 가치 필터를 거친 짧은 인지 TTS 경로를 사용하도록 목표 정책을 정의했습니다.
  - 거리 정책 SSOT, 구역 히스테리시스, Near enter/update/clear 상태, 서버·단말 알림 소유권, API 호환, 테스트·KPI·문서 동기화 계획을 모바일 구현 계획서로 정리했습니다.
  - 루트 경로의 구현 계획서를 `docs/mobile/` 하위로 이동해 모바일 관련 설계 문서 위치와 정합화했습니다.
- **관련 파일**: `docs/mobile/HEURISTIC_DISTANCE_ALERT_ROUTING_IMPLEMENTATION_PLAN.md`, `docs/README.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `tests/test_cognitive_fields.py`, `tests/test_fast_lane.py`, `tests/test_suppressor_rearm.py`: 27개 통과
  - `tests/test_detection.py`, `tests/test_risk_ssot.py`, `tests/test_langgraph.py`: 91개 통과
  - 계획서 UTF-8 확인 및 `git diff --check` 통과
- **비고**:
  - 초기 Near 진입 면적비 0.10, 이탈 0.08, Medium 진입 0.03, Far 이탈 0.025는 LiDAR 클래스별 검증 전 잠정 권장값입니다.
  - 기존 사용자 로컬 변경 파일은 수정하지 않았습니다.

---

### 2026-07-19 | 보안 | 인증·전송·컨테이너·의존성 전면 보강

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 개발 기본 JWT·단말 토큰, 공개 관리자 생성, URL 쿼리 토큰, 인증 전 WebSocket 세션 교체, 무제한 STT 업로드와 공개 개발 API가 계정 탈취·서비스 고갈 경로가 될 수 있었습니다.
  - Redis/MariaDB 약한 기본 비밀번호와 전체 인터페이스 포트, iOS ATS 전역 허용, 취약 버전 의존성 및 표준 XML 파서가 남아 있었습니다.
- **변경 내용**:
  - JWT를 모든 환경에서 fail-closed로 전환하고 표준 클레임 검증, 최초 최고관리자 1회 부트스트랩, 관리자 RBAC, 로그인 제한, 만료형 단말 JWT 발급을 적용했습니다.
  - 콘솔 SSE·프레임·WebSocket의 URL 토큰을 제거하고 Authorization 헤더·최초 인증 메시지, Origin 검증, 인증 제한시간을 적용했습니다.
  - STT 파일 형식·용량·동시성 제한, 디버그/내비게이션 시뮬레이터 명시 허용, 사용자 등록 운영자 권한을 적용했습니다.
  - 공개 단말 토큰/IP 폴백과 iOS ATS 전역 허용을 제거하고 기본 WSS로 전환했습니다.
  - 로컬 전용 비밀값 생성 스크립트, `.env` 권한 600, Redis 인증, Compose 필수 DB 비밀번호, 루프백 포트, 비루트 컨테이너와 `no-new-privileges`를 적용했습니다.
  - Pillow·setuptools와 PyTorch 계열을 보안 수정 버전으로 올리고 XML 파서를 `defusedxml`로 교체했습니다. 팀 최대 RTX 5090 기준으로 Ubuntu x86_64/Windows amd64는 `torch==2.13.0+cu130`/`torchvision==0.28.0+cu130`, macOS는 PyPI 2.13.0/0.28.0 MPS·CPU 경로로 분리했습니다.
- **검증 결과**:
  - Python Ruff·Bandit, 콘솔 운영 빌드, 클라이언트 TypeScript, 양쪽 npm audit, Docker Compose 2종 구성 검증을 통과했습니다.
  - 인증·JWT·단말 바인딩·요청 제한 회귀 테스트를 추가하고 비통합 테스트 361건 통과를 확인했습니다.
  - macOS 로컬 `.venv`를 PyTorch 2.13/torchvision 0.28로 갱신하고 CPU 폴백 1 step 연산을 확인했습니다. 현재 호스트에서는 MPS가 비활성 상태였습니다.
- **잔여 검증**:
  - Tailscale Serve TLS 종단 구성 후 iOS 실기기 WSS 연결을 검증해야 합니다. RTX 5090 실장 Ubuntu·Windows 서버에서는 NVIDIA R580 이상 드라이버와 cu130 빌드의 실제 추론을 각각 검증해야 합니다.
  - 패치가 없는 ChromaDB 임베디드 모드 취약점(`CVE-2026-45829`/`PYSEC-2026-311`)과 데이터베이스 개인정보 컬럼의 애플리케이션 계층 암호화는 별도 마이그레이션 과제로 유지합니다.

---

### 2026-07-19 | 배포/인프라/클라이언트/문서 | 로컬 GPU 서버 Docker 재배포 및 Mac·iOS Tailscale WSS 연결 구성

- **커밋**: (이번 커밋)
- **작업 목표**:
  - 현재 프로젝트 소스 변경분을 Docker 이미지에 다시 반영하고 FastAPI·Redis·MariaDB·운영 콘솔을 로컬 GPU 서버에서 실행합니다.
  - Ollama는 Docker 컨테이너로 중복 기동하지 않고 호스트 로컬 프로세스로 유지하며, FastAPI 컨테이너가 `gemma4:e4b`와 `nomic-embed-text`를 호출하도록 연결합니다.
  - MariaDB와 중앙 미디어 저장 API는 기존 Raspberry Pi Tailscale 서비스를 유지하고, Mac에서 빌드한 iOS 앱은 Tailscale Serve의 유효한 TLS 인증서를 통해 `wss`로 GPU FastAPI에 연결하도록 구성합니다.
  - 비밀값은 루트 `.env`와 `client/.env`에만 보관하고, Git 추적 문서·Compose 출력·애플리케이션 로그에는 원문을 남기지 않습니다.

- **로컬 환경 변수 정합화**:
  - 루트 `.env`에서 LLM 공급자를 Ollama, L2 모델을 `gemma4:e4b`, 임베딩 모델을 `nomic-embed-text`로 유지하고 Compose 전용 Ollama 주소를 `http://host.docker.internal:11434`로 설정했습니다.
  - Docker 브리지에서 호스트 Ollama에 접근할 수 있도록 로컬 실행 환경의 `OLLAMA_HOST=0.0.0.0:11434`, `MINCHODAN_EXPOSE_OLLAMA=1` 구성을 사용하되, 전체 로컬망에 무제한 공개하지 않고 별도 UFW 최소 허용 규칙을 적용했습니다.
  - 미구현 `kokoro` 값으로 인해 서버 기동마다 Supertonic으로 폴백하던 경고를 제거하기 위해 `TTS_ENGINE=supertonic`으로 정정했습니다.
  - 루트 `.env` 권한은 `600`으로 유지하고 Git 제외 상태를 재확인했습니다.
  - 클라이언트 로컬 `client/.env`는 `EXPO_PUBLIC_NETWORK_MODE=tailscale`, 서버 MagicDNS 이름, `EXPO_PUBLIC_SERVER_PORT=443`, `EXPO_PUBLIC_WS_SCHEME=wss` 조합으로 변경했습니다.
  - 단말 ID와 단말 토큰은 서버 등록값과 일치하는 로컬 값으로 유지했으며, 본 변경 이력에는 실제 값을 기록하지 않았습니다.

- **Docker 빌드·Compose 구성 변경**:
  - 루트 `.dockerignore`와 `docker/.dockerignore`에 가상환경, 도구 캐시, 대용량 `data/` 경로를 제외해 Docker 빌드 컨텍스트를 약 `13.35MB`로 축소했습니다.
  - FastAPI 이미지 빌드에서 Python 3.13, PyTorch `2.13.0+cu130`, CUDA 13.0 경로와 NVIDIA GPU 인식을 확인했습니다.
  - Supertonic 모델 자산과 한국어 음소 변환 바이너리가 이미지 빌드 단계에 캐시된 상태로 FastAPI 이미지를 다시 생성했습니다.
  - 루트 `.env`가 모드 `600`인 상태에서 비루트 FastAPI 사용자가 `/app/.env` 바인드 마운트를 읽지 못해 발생한 `PermissionError`를 해소하기 위해 `.env` 파일 마운트를 제거했습니다. 환경 변수는 Compose `env_file`로만 런타임에 주입합니다.
  - FastAPI·Redis·운영 콘솔의 호스트 포트는 각각 `127.0.0.1:8000`, `127.0.0.1:6379`, `127.0.0.1:5174`로 제한하고 MariaDB 호스트 포트는 노출하지 않았습니다.
  - Linux Compose의 `minchodan-net`을 `172.18.0.0/16`, 게이트웨이 `172.18.0.1`로 고정하고 `host.docker.internal`을 해당 게이트웨이에 명시적으로 매핑했습니다. Docker 네트워크가 재생성돼도 UFW 규칙과 목적지 주소가 바뀌지 않도록 하기 위한 조치입니다.
  - macOS Compose는 Docker Desktop·Colima의 호스트 별칭 동작을 유지하기 위해 Linux 고정 IPAM을 적용하지 않았습니다.
  - 운영 콘솔은 `VITE_PROXY_TARGET=http://fastapi:8000`을 사용하도록 하고, Linux inotify 한도 초과(`ENOSPC`)를 회피하기 위해 Chokidar polling과 1초 간격을 적용했습니다.
  - 콘솔의 익명 `node_modules` 볼륨 권한 문제를 새 볼륨으로 해소하고 Vite 개발 서버가 정상 기동되는 것을 확인했습니다.
  - Redis URL 전체를 출력하던 MCP 관리자와 내비게이션 Redis 초기화 로그를 일반 연결 성공 메시지로 교체했습니다.
  - 기존 로그에 Redis 인증 URL이 노출된 이력이 있어 Redis 비밀번호를 로컬에서 재생성하고 관련 컨테이너를 재생성했습니다. 실제 비밀번호는 기록하지 않았습니다.

- **호스트 Ollama 연결 및 방화벽 구성**:
  - 호스트 Ollama가 `11434` 포트에서 실행되고 `gemma4:e4b`, `nomic-embed-text:latest` 모델이 설치된 것을 확인했습니다.
  - FastAPI 컨테이너에서 `host.docker.internal`이 Docker 기본 브리지 주소로 해석되어 초기 UFW 규칙의 대상과 일치하지 않던 문제를 확인했습니다.
  - Linux Compose 게이트웨이를 `172.18.0.1`로 고정한 후 `sudo ufw allow from 172.18.0.0/16 to 172.18.0.1 port 11434 proto tcp` 규칙을 적용했습니다.
  - FastAPI 컨테이너 내부에서 호스트 Ollama `/api/tags`를 조회해 두 모델을 확인했습니다.
  - 컨테이너에서 `gemma4:e4b` 실제 생성 요청을 보내 `연결 확인` 응답과 `done=true`를 확인했습니다.
  - `nomic-embed-text` 실제 임베딩 요청으로 벡터 1개, 차원 768을 확인했습니다.

- **Tailscale Serve 및 Mac·iOS 클라이언트 경로 구성**:
  - tailnet 관리 콘솔에서 Serve 기능을 1회 활성화하고, Linux 호스트에서 `sudo tailscale set --operator="$USER"`로 현재 사용자에게 Serve 구성 권한을 부여했습니다.
  - `tailscale serve --bg http://127.0.0.1:8000`을 적용해 서버 MagicDNS의 tailnet 전용 HTTPS/WSS 443 종단을 FastAPI 루프백 8000으로 프록시했습니다.
  - 실제 MagicDNS 주소와 Tailscale IPv4는 로컬 설정에만 유지하고 본 변경 이력에서는 공개하지 않았습니다.
  - MagicDNS `/`와 `/health` 요청에서 HTTP 200을 확인했습니다.
  - 클라이언트 로컬 `.env`의 단말 ID·토큰을 읽되 값은 출력하지 않는 Node WebSocket 스모크를 실행해 `welcome -> hello -> auth_ok` 인증 핸드셰이크를 확인했습니다.
  - Expo Metro를 `--host lan`으로 독립 백그라운드 세션에서 실행하고 로컬 루프백과 GPU 서버 Tailscale IPv4의 `8081/status`에서 모두 `packager-status:running`을 확인했습니다.
  - Mac에서 만든 개발 빌드는 동일 tailnet에서 GPU 서버의 Tailscale IPv4 8081을 Metro 주소로 사용할 수 있고, FastAPI는 MagicDNS 443 WSS를 사용하도록 역할을 분리했습니다.
  - 기존 Mac 빌드에 IP 기반 `wss://...:8000` 값이 번들돼 있다면 최신 `client/.env`를 Mac에 동기화한 뒤 Metro 재번들 또는 iOS 앱 재빌드가 필요함을 명시했습니다.
  - Release·TestFlight 빌드는 JS 번들이 앱에 포함되므로 Mac의 최신 환경 변수를 반영해 재빌드해야 하며, 실행 시 Metro는 필요하지 않습니다.

- **Raspberry Pi 외부 서비스 재검증**:
  - FastAPI 컨테이너의 DB 환경 변수가 기존 Raspberry Pi MariaDB를 계속 가리키는 상태에서 읽기 전용 `SELECT 1`을 실행해 결과 `1`을 확인했습니다.
  - 중앙 미디어 저장 백엔드가 활성 상태임을 확인하고 Raspberry Pi 미디어 API `/health`에서 HTTP 200을 확인했습니다.
  - 인증이 필요한 미디어 객체 조회 경로는 토큰 원문을 출력하지 않은 상태에서 인증 실패가 아닌 미존재 객체 응답을 확인해 Bearer 인증 경로가 유지됨을 검증했습니다.

- **실행 결과**:

  | 검증 대상 | 결과 |
  | :--- | :--- |
  | FastAPI | `127.0.0.1:8000` HTTP 200, Tailscale Serve `/health` HTTP 200 |
  | Redis | 컨테이너 `healthy`, FastAPI Redis 연결 성공 |
  | MariaDB 컨테이너 | 컨테이너 `healthy`, 호스트 포트 미노출 |
  | Raspberry Pi MariaDB | FastAPI 컨테이너에서 `SELECT 1` 성공 |
  | Raspberry Pi 미디어 API | 원격 저장 활성, `/health` HTTP 200 |
  | 운영 콘솔 | `127.0.0.1:5174` HTTP 200 |
  | 호스트 Ollama | `/api/tags` HTTP 200, Gemma 생성 성공, nomic 임베딩 768차원 |
  | Tailscale Serve | tailnet 전용 HTTPS/WSS 443 활성 |
  | 클라이언트 WebSocket | 실제 `welcome -> hello -> auth_ok` 성공 |
  | Expo Metro | 로컬 및 Tailscale IPv4 `8081/status` 응답 정상 |
  | TTS | `TTS_ENGINE=supertonic`, 모델 로드와 30개 캐시 프리워밍 완료 |
  | GPU 런타임 | 컨테이너에서 PyTorch cu130 및 CUDA GPU 인식 |

- **검증 명령 및 품질 확인**:
  - `docker compose --env-file ../.env -f docker-compose.yml config --quiet`: Linux 구성 통과
  - `docker compose --env-file ../.env -f docker-compose.macos.yml config --quiet`: macOS 구성 통과
  - `bash -n docker/linux_docker_start.sh`: 통과
  - `docker ps --filter name=minchodan`: FastAPI·Redis·MariaDB·콘솔 모두 실행 상태 확인
  - FastAPI 현재 컨테이너 전체 로그에서 `Traceback`, `ERROR`, 지원하지 않는 TTS 엔진 경고가 없음을 확인
  - `git diff --check`: 통과

- **문서 정합화**:
  - `docs/ops/deployment_guide.md`와 `docs/ops/environment_variables.md`에 Linux 고정 Docker 서브넷, UFW 최소 허용 범위, `.env`의 `env_file` 주입, Tailscale Serve 초기 권한 설정, MagicDNS/443/WSS 클라이언트 구성을 반영했습니다.
  - `client/.env.example`을 Tailscale IP·8000 예시에서 MagicDNS·443·`wss` 예시로 변경했습니다.
  - 무선 테스트, 네트워크 지연 측정, Android 통합·빌드·온디바이스 실행, iOS/Android 분기 계약, 온디바이스 추론 격리 계획, 내비게이션 관제·서버 통합 지침을 같은 MagicDNS/443/WSS 기준으로 교차 갱신했습니다.
  - 운영 가이드에 남아 있던 `minchodan-ollama` 컨테이너와 `llava` 다운로드 절차를 호스트 Ollama의 `gemma4:e4b`·`nomic-embed-text` 준비 절차로 정정했습니다. 이미지 캡셔닝은 Gemini 경로를 유지합니다.
  - 과거 changelog와 연구·계획 문서의 역사적 기술 표현은 작업 당시 기록 보존을 위해 일괄 수정하지 않았습니다.

- **관련 추적 파일**:
  - Docker·환경 예시: `.dockerignore`, `.env.example`, `docker/.dockerignore`, `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `docker/linux_docker_start.sh`, `client/.env.example`
  - 로그 보안: `server/mcp/manager.py`, `server/navigation/server.py`
  - 운영 문서: `docs/ops/deployment_guide.md`, `docs/ops/environment_variables.md`, `docs/ops/wireless_test_guide.md`, `docs/ops/network_latency_benchmark.md`, `docs/ops/tailscale_connection_guide.md`, Android 실행·통합 가이드 5종
  - 모바일·통합 계약: `docs/mobile/ios_android_bifurcation_contract.md`, `docs/mobile/ondevice_inference_engine_isolation_plan.md`, `docs/dev-guides/integration/관제_UI_및_시나리오_연동_지침서.md`, `docs/dev-guides/integration/서버_및_시스템_통합_기술_지침서.md`
  - 변경 이력: `docs/changelogs/jy.md`

- **로컬 전용 변경 및 외부 런타임 상태**:
  - 루트 `.env`, `client/.env`, 실제 단말 토큰, Redis·DB·미디어 API 비밀번호와 토큰, 실제 Tailscale IPv4·MagicDNS는 Git 추적 대상에서 제외했습니다.
  - UFW 규칙, Tailscale Serve 활성화와 operator 지정, 호스트 Ollama 프로세스, 실행 중인 Metro는 호스트 런타임 상태이므로 저장소 checkout만으로 자동 복원되지 않습니다. 배포 가이드의 절차에 따라 새 호스트에서 별도로 적용해야 합니다.

- **잔여 기능 상태**:
  - 서버 연결과 인증은 완료됐지만 루트 `.env`의 `DETECTOR_TYPE=mock`이므로 서버 YOLO 실제 탐지는 아직 활성화하지 않았습니다.
  - `data/chroma_db`가 존재하지 않아 RAG 검색 데이터베이스는 아직 구축되지 않았습니다.
  - Mac에서 빌드한 실제 iOS 앱의 카메라 프레임 전송·TTS 수신까지의 실기기 종단 검증은 Mac 소스와 로컬 환경 변수 동기화 후 별도로 수행해야 합니다.
  - 현재 Tailscale 피어 연결은 환경에 따라 DERP 릴레이를 사용할 수 있으므로 야외 실측 전 직접 연결 여부와 RTT를 다시 확인해야 합니다.

---
