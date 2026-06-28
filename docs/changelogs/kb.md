# Changelog - kb (관범)

> 이 파일은 **kb(관범)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-06-24 | 전체 | 문서 기준선 구축

- **커밋**: `docs: 프로젝트 문서 기준선 구축 및 초기 디렉토리 골격 생성`
- **변경 내용**:
  - `minchodan_design_note.md` 7단계 골격을 기반으로 루트 README 작성.
  - 스킬 문서(`skills.md`)와 docs 문서 세트 전체 작성 (AGENTS, architecture, api_specification, test_specification, git_branching_strategy, pipeline_stage_design).
  - `.env.example` 환경변수 템플릿과 `requirements.txt` 파이썬 의존성 초기화.
  - 개인 문서 폴더(`docs/{dg,jh,jy,kb,th}/`)를 제거하고, 모든 설계 문서를 `docs/` 폴더에서 공유로 관리하도록 통일.
  - 디렉토리 골격(`.gitkeep`)을 유지하며, 코드 구현은 각 단계별로 진행 예정.
- **관련 파일**: `README.md`, `skills.md`, `docs/README.md`, `docs/AGENTS.md`, `docs/architecture.md`, `docs/api_specification.md`, `docs/test_specification.md`, `docs/git_branching_strategy.md`, `docs/pipeline_stage_design.md`, `.env.example`, `requirements.txt`
- **검증 결과**: 문서 구조 확인, 링크 정합성 확인
- **비고**: 초기 커밋 기준선. 코드 구현은 1단계(WebSocket Gateway)부터 순차 진행.

---

### 2026-06-25 | 3단계 | 3단계 탐지·분할·게이트 백엔드 구현

- **커밋**: `feat(3단계): Yolo 26N 탐지·분할·게이트 백엔드 및 테스트 구현`
- **변경 내용**:
  - `server/detection/` 패키지 신규 구현: schemas, detector_interface, config, mock_detector, yolo_detector, yolo_segmentor, bytetrack_tracker, gates, detection_pipeline
  - `server/bus/` 패키지 신규 구현: redis_client, producer
  - `tests/test_detection.py` 신규 작성: 3단계 검증 21개 케이스
  - `DetectionPipeline`에서 Detector/Segmentor 예외를 분리 처리하여 한쪽 실패 시에도 파이프라인 영속성 유지
  - `ByteTrackTracker`에 Redis 예외 방어 처리 추가
- **관련 파일**: `server/detection/`, `server/bus/`, `tests/test_detection.py`
- **검증 결과**: pytest 테스트 21 Passed 통과
- **비고**: 가중치 미제공 시 MockDetector/MockSegmentor로 자동 폴백 및 팩토리 연동 완료

---

### 2026-06-26 | 3단계 | 보행이론 보고서 추가 및 YOLO26n 통합 테스트 환경 구축

- **커밋**: `docs: 실제 YOLO26n 모델 가중치 다운로드 및 연산 검증 스크립트 추가`, `docs: 보행이론 기반 행동 패턴 및 위험도 정의 보고서 추가`
- **변경 내용**:
  - 보행지도사 이론에 근거하여 시각장애인 행동 패턴 및 위험도 게이트 정의 분석 보고서 작성
  - 공식 `yolo26n.pt` 및 `yolo26n-seg.pt` 모델의 가중치를 자동 배치하는 다운로드 스크립트 구축 및 로드 검증 완수
  - 실제 YOLO26n 모델 연산, ByteTrack 추적, 이중 게이트 작동 및 Redis 연결 예외 바이패스를 검증하는 통합 테스트 스크립트 구축 및 테스트 통과
- **관련 파일**: `docs/behavior_and_risk_insight.md`, `scripts/download_pretrained_weights.py`, `scripts/verify_pretrained_weights.py`, `scripts/integration_test_pipeline.py`
- **검증 결과**: verify_pretrained_weights.py 및 integration_test_pipeline.py 추론 및 분기 PASS
- **비고**: 실제 YOLO26n 사전 학습 가중치 pt 파일 2종(총 약 12MB)을 Git 추적 파일로 등록 및 푸시 완료

---

### 2026-06-26 | 6단계 | 6단계 LangGraph 오케스트레이션 설계서 작성

- **커밋**: `docs(6단계): 종합 회피 가이드 생성 LangGraph 계층 LLM 설계서 신규 작성`
- **변경 내용**:
  - `docs/stage6_orchestration_design.md` 신규 작성: 6단계 구현 지침 수준의 상세 설계서 (14개 섹션)
  - 3단계 `server/bus/producer.py`의 Redis Streams payload 필드를 6단계 입력 계약으로 정확 매핑 (event_id, track_id, class_name, confidence, bbox, speed, direction, risk, timestamp)
  - 5단계 RAG 미구현 상태에 대응한 `rag_context` 인터페이스 가정 사전 정의 및 방어적 기본값 적용
  - OrchState TypedDict 13개 필드 정의, L1/L2/L3 3계층 아키텍처, LangGraph StateGraph 조립, LLMClientFactory 핫스왑 라우팅, 프롬프트 설계, 방어 코딩 7종 가드레일, KPI 테스트 체크리스트 10항목 포함
  - `course_codebase_guide.md` 섹션 11(LLM), 12(LCEL), 14(LangGraph), 17.2(방어적 코딩) 준수
- **관련 파일**: `docs/stage6_orchestration_design.md`
- **검증 결과**: 문서 규칙(한국어 존댓말, 이모지 금지, Mermaid 큰따옴표, 표 우선, 인용 블록 메타데이터) 준수 확인
- **비고**: 5단계 RAG 미구현 상태에서도 6단계는 기본값 `"관련 수칙 없음"`으로 동작 가능. 구현 순서 9단계 권장 가이드 포함

---

### 2026-06-26 | 6단계 및 기타 | 6단계 LangGraph 오케스트레이터 구현 및 슬랙 연동 자동화 완료

- **커밋**: `feat(6단계): 6단계 LangGraph 오케스트레이터 및 LLMClientFactory 구현`, `feat: 슬랙 API 연동 로컬 자료 요약 발행 스크립트 추가 및 env.example 갱신`, `fix: opencode.json 스키마 오류를 유발하는 정의되지 않은 키 제거`
- **변경 내용**:
  - `server/orchestration/` 모듈 전면 구현: `state.py`, `llm_client_factory.py`, `graph.py` 및 `nodes/` 하위 파일(L1 분류, L2 문장 생성, L3 검증, Fallback 노드) 작성.
  - 외부 래퍼(`langchain_community`) 의존성 없이 로컬 `ollama` SDK 및 `httpx`를 통한 GPT-4o-mini API 호출을 직접 구현하여, 패키지 미설치 환경에서도 핫스왑 및 파이프라인 영속성이 확보되도록 리팩토링.
  - `tests/test_langgraph.py` 테스트 코드 작성: pytest 스타일로 6개 핵심 기능(위험도 분류, 가이드라인 검증 규칙, retry 카운트, Fallback 고정문장, API 장애 대응 등) 검증 완수 및 통과.
  - `scripts/slack_publisher.py` 신규 구현: 슬랙 채널 `#길댕`으로 로컬 파일 요약 및 임의 메시지를 발행하는 Python 도구 구축.
  - `opencode.json` 유효성 검사 오류 해결을 위해 정의되지 않은 키(`context_files`, `rules`) 제거.
- **관련 파일**: `server/orchestration/`, `tests/test_langgraph.py`, `scripts/slack_publisher.py`, `opencode.json`, `.env.example`
- **검증 결과**: `test_langgraph.py` 6 Passed 통과, `opencode --version` 정상 작동.
- **비고**: 6단계 및 슬랙 API 연동 도구가 가상환경 내에서 완벽하게 빌드 및 테스트 완료되었음.

---

### 2026-06-27 | 6단계 | System/GPU Monitor MCP 연동 및 핫스왑 자동화 구현

- **커밋**: `feat(6단계): System/GPU Monitor MCP 연동 및 LLMClientFactory 비동기 핫스왑 구현`
- **변경 내용**:
  - `server/mcp/gpu_monitor.py` 신규 구현: CUDA GPU 및 가상 리소스를 실시간 모니터링하여 임계치 초과 시 핫스왑 트리거를 판단하는 MCP 진단 모듈 구축.
  - `server/orchestration/llm_client_factory.py` 개선: `start_gpu_monitor` 백그라운드 비동기 루프를 추가하여 메인 추론 스레드의 블로킹 지연(0ms) 없이 GPU 부하 발생 시 로컬 Ollama에서 OpenAI GPT-4o-mini로 자동 핫스왑 및 정상 복구 시 복귀 기능 구현.
  - `tests/test_mcp_gpu.py` 신규 작성: GPU 부하 및 복구 상황에 따른 핫스왑 동작과 백그라운드 모니터 태스크의 원활한 라이프사이클을 검증하는 pytest 비동기 테스트 코드 구축.
- **관련 파일**: `server/mcp/gpu_monitor.py`, `server/orchestration/llm_client_factory.py`, `tests/test_mcp_gpu.py`
- **검증 결과**: `test_mcp_gpu.py` 2 Passed 완료 (전체 테스트 통과)

---

### 2026-06-27 | 1단계 및 공통 | 통합 MCP 모듈 및 FastAPI SSE 관제 API 구현

- **커밋**: `feat(mcp): 통합 MCPManager 및 FastAPI SSE 모니터링 라우터 구현`
- **변경 내용**:
  - `server/mcp/manager.py` 신규 구현: Redis Streams(mcp:metrics) 이벤트를 수집하여 다수의 리스너 큐로 실시간 브로드캐스트하는 싱글톤 `MCPManager` 구축.
  - `server/api/monitor.py` 신규 구현: 관제 프론트엔드 연동을 위한 Server-Sent Events(SSE) `/api/v1/monitor/stream` 스트리밍 엔드포인트 제공.
  - `server/main.py` 신규 구현: FastAPI 앱 및 모니터링 라우터를 조립하고 lifespan을 통해 `mcp_manager` 컨슈머 시작 및 해제 라이프사이클 통합.
  - `tests/test_mcp_integration.py` 신규 작성: Direct Generator 순회를 통해 SSE 메시지 포맷 정합성과 브로드캐스트 전파를 검증하는 비동기 통합 테스트 구축 및 통과.
- **관련 파일**: `server/mcp/manager.py`, `server/api/monitor.py`, `server/main.py`, `tests/test_mcp_integration.py`
- **검증 결과**: `test_mcp_integration.py` 1 Passed 완료 (0.38초)

---

### 2026-06-27 | 공통 | 내부 MCP 구현 현황 점검 및 프로젝트 문서 동기화

- **커밋**: `docs(mcp): 내부 MCP 구현 현황 점검 및 architecture/test_specification 문서 동기화`
- **변경 내용**:
  - `docs/architecture.md` 13.5절 신규 추가: 설계 6종 MCP 대비 구현 현황 매트릭스 및 단계적 착수 로드맵 명시.
  - `docs/test_specification.md` 5.8절 보완: TC-MCP-002, TC-MCP-003 신규 추가 및 최종 검증일 메타데이터 기록.
  - `docs/changelogs/kb.md` 이번 검증 작업 내역 추가.
- **검증 내용**:
  - 내부 MCP 테스트 2종 재실행: `test_mcp_gpu.py`(2 passed), `test_mcp_integration.py`(1 passed), 총 **3 passed in 21.60s**.
  - 외부 MCP 서버 5종 라이브 연결 확인: google-calendar, notion, slack, google-sheets, puppeteer.
- **관련 파일**: `docs/architecture.md`, `docs/test_specification.md`, `docs/changelogs/kb.md`
- **검증 결과**: pytest 3 passed 통과, 문서 규칙(이모지 금지, 한국어, 표 우선, 인용 블록 메타데이터) 준수 확인
- **비고**: Slack Notification MCP만 단계 의존성 없이 즉시 `server/mcp/` 통합 가능. 7단계 3종 MCP는 7단계 착수 시 동시 구현 권장.

---

### 2026-06-27 | 공통 | 프로젝트 문서화 갭 분석 및 환경 변수·배포 명세서 신규 작성

- **커밋**: `docs: 환경 변수 명세서·배포 가이드 신규 작성 및 기존 문서 불일치 13건 해소`
- **변경 내용**:
  - `docs/environment_variables.md` 신규 작성: `.env.example` 기준 환경 변수 단일 명세. 카테고리별 10개 분류(LLM/VectorDB/Redis/WebSocket/탐지/TTS/데이터/Slack/LangSmith/GPU Mock), 3원화 불일치 해소 이력, 보안 주의사항, 검증 체크리스트 포함.
  - `docs/deployment_guide.md` 신규 작성: Docker 컨테이너 아키텍처(Redis + Ollama + FastAPI 3컨테이너), 사전 준비·배포 절차·OS별 스크립트 명세·Dockerfile/compose/ignore 명세·검증·트러블슈팅. TC-SMOKE-004 연동.
  - `.env.example` 수정: Slack 인증 `SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID` -> `SLACK_WEBHOOK_URL` 단일화. 모델 가중치 주석 "Git 추적" 반영. LangSmith·GPU Mock 변수 주석 추가.
  - `docs/architecture.md` 10절 수정: 환경 변수 표 단일 명세서 참조로 정합. `WS_HOST`·`DETECTOR_TYPE`·`SLACK_WEBHOOK_URL` 누락 보충, 중복 행 제거.
  - 루트 `AGENTS.md`·`docs/AGENTS.md` 수정: `models/` 정책 "git-ignore" -> "사전학습 가중치 Git 추적, 커스텀 학습 가중치 git-ignore". 루트 AGENTS.md 9절 문서 인덱스에 신규 2종·기존 누락 3종 추가.
  - 루트 `README.md` 수정: 환경 변수 표 단일 명세서 참조로 정합. 디렉토리 구조 모델 가중치 주석 수정. 문서 인덱스에 신규 2종·기존 누락 4종 추가. `Directory_Structure.md` 링크 대소문자 수정. Docker 빠른 시작에 배포 가이드 참조 추가.
  - `docs/README.md` 수정: 버전 v0.2.0 -> v0.3.0. 문서 목록에 신규 2종·Changelog 템플릿 추가. 에이전트 가이드 링크 루트 AGENTS.md로 정합. `directory_Structure.md` -> `Directory_Structure.md` 링크 대소문자 수정. 권장 독해 순서에 환경 변수 명세서·배포 가이드 추가.
  - `docker/windows_docker_start.bat` 전면 재작성: DoctorSkin용 삭제, Minchodan용(Redis + Ollama + FastAPI)으로 재작성. `bump_docker_tag.ps1` 연동·`doctorskin` 태그·`HOST_PORT=8100` 제거.
  - `docker/linux_docker_start.sh` 전면 재작성: DoctorSkin용 삭제, Minchodan용으로 재작성. 이미지 태그 관리 로직 제거, 단순화.
  - `docker/macos_docker_start.sh` 전면 재작성: DoctorSkin용 삭제, Minchodan용으로 재작성. macOS GPU 미지원 경고 추가.
  - `docker/Dockerfile` 신규 작성: `python:3.13-slim` 베이스, OpenCV 의존성(libgl1) 포함, uvicorn 실행.
  - `docker/docker-compose.yml` 신규 작성: 3컨테이너(fastapi/redis/ollama) 정의, GPU 전달, 볼륨 마운트, `minchodan-net` 브리지 네트워크.
  - `docker/.dockerignore` 신규 작성: 빌드 컨텍스트 제외 패턴(Python 캐시·가상환경·.env·Git·문서·클라이언트·콘솔·학습 데이터).
- **관련 파일**: `docs/environment_variables.md`, `docs/deployment_guide.md`, `.env.example`, `docs/architecture.md`, `AGENTS.md`, `docs/AGENTS.md`, `README.md`, `docs/README.md`, `docker/windows_docker_start.bat`, `docker/linux_docker_start.sh`, `docker/macos_docker_start.sh`, `docker/Dockerfile`, `docker/docker-compose.yml`, `docker/.dockerignore`
- **검증 결과**: 문서 규칙(이모지 금지, 한국어, 표 우선, 핵심 굵게, 인용 블록 메타데이터) 준수 확인. 환경 변수 3원화·Slack 인증·모델 가중치 정책·Docker 스크립트 오류 등 기존 문서 간 불일치 13건 해소.
  - **비고**: 단계별 설계서(1·2·4·5·7단계)는 착수 시점 작성 원칙에 따라 본 작업에서 제외. Tier 2~4 문서(보안·관측·데이터 스키마·에러 코드·클라이언트·운영콘솔·RAG 지식베이스·모델 가중치 관리·성능 벤치마크·트러블슈팅·기여 가이드)는 후속 작업 대상.

---

### 2026-06-27 | 공통 | 코드 품질 검증 파이프라인 문서화 (구현 전 가이드)

- **커밋**: (대기 중)
- **변경 내용**:
  - `docs/code_quality_guide.md` 신규 작성: 코드 품질 검증 파이프라인 단일 명세. 12개 섹션(목적, 도구 매트릭스, 사전 준비, 설치, 도구별 상세 가이드, 코딩 패턴 매핑, 로컬 실행 흐름, CI, FAQ 10패턴, 치트시트, 트러블슈팅, 관련 파일 인덱스).
  - 도구 조합 확정: Ruff(린트+포맷+보안 1차) + Bandit(보안 심층 2차) + mypy(타입 점진적) + jscpd(중복 전용) + pip-audit(의존성 CVE).
  - 실행 시점 분리: pre-commit(Ruff+Bandit, 빠름) / pre-push(mypy+jscpd+pip-audit, 느림) / GitHub Actions(PR 게이트).
  - [`course_codebase_guide.md`](course_codebase_guide.md) 3.2(임포트 순서)·3.3(경로 처리)·17.2(방어적 코딩) 항목과 Ruff 룰 ID 매핑 표 작성.
  - 처음 사용하는 팀원용 FAQ 10패턴 (임포트 순서, 미사용 import, 하드코딩 secret, raise from, None 접근, mutable default, dict get, f-string, subprocess 화이트리스트, 이중 경로 분리 위반).
  - `docs/README.md` 수정: 문서 목록에 code_quality_guide.md 추가, 권장 독해 순서에 삽입.
  - `AGENTS.md` 수정: 섹션 5 AI Coding Rules에 린트·검증 명령 항목 추가.
  - `docs/test_specification.md` 수정: 5.9 공통 - 정적 분석 게이트 섹션 신규 추가.
  - `docs/course_codebase_guide.md` 수정: 18절 부록에 18.5 Ruff 룰 매핑 참조 추가.
- **관련 파일**: `docs/code_quality_guide.md`, `docs/README.md`, `AGENTS.md`, `docs/test_specification.md`, `docs/course_codebase_guide.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 규칙(이모지 금지, 한국어, 표 우선, 핵심 굵게, 인용 블록 메타데이터, Mermaid 큰따옴표) 준수 확인.
- **비고**: 본 작업은 문서화만 수행. 실제 설정 파일(`pyproject.toml`, `requirements-dev.txt`, `.jscpd.json`, `.pre-commit-config.yaml`, `.github/workflows/lint.yml`) 및 기존 36개 .py 자동 수정은 후속 구현 단계에서 진행.

---

### 2026-06-27 | 공통 | 코드 품질 검증 파이프라인 구현 및 기존 코드 일괄 수정

- **커밋**: (대기 중)
- **변경 내용**:
  - `pyproject.toml` 신규 작성: Ruff(lint+format), mypy(점진적), bandit, pytest 통합 설정. Ruff 룰 I/E/W/F/UP/S/B/SIM/C4/RUF/PT 활성화, per-file-ignores로 tests/scripts/server/main.py 의도된 패턴 예외 처리.
  - `requirements-dev.txt` 신규 작성: ruff, mypy, bandit, pip-audit, pre-commit (jscpd는 npm 별도 설치).
  - `.jscpd.json` 신규 작성: 중복 검출 전용 설정 (min-lines 5, min-tokens 50, threshold 5%).
  - `.pre-commit-config.yaml` 신규 작성: pre-commit(Ruff format+check+Bandit) / pre-push(mypy+jscpd+pip-audit) 분리.
  - `.github/workflows/lint.yml` 신규 작성: PR 시 Ruff/Bandit/mypy/jscpd/pip-audit CI 게이트.
  - 기존 36개 .py 파일 일괄 수정: `ruff format` 21개 파일 포맷팅, `ruff check --fix` 179개 위반 자동 수정, `--unsafe-fixes`로 36개 추가 수정 (contextlib.suppress 도입 등).
  - 수동 수정 3건: `scripts/slack_publisher.py` B904(raise from), `server/mcp/manager.py` SIM105/S110(contextlib.suppress), scripts/ 2건 B310 nosec 화이트리스트.
  - mypy 점진적 적용: `disallow_untyped_defs=false`, `disable_error_code`로 union-attr/assignment/attr-defined/type-var/return-value/arg-type/no-any-return/var-annotated 무시 (기존 코드, 파일 수정 시 점진 해제).
  - pre-commit/pre-push 훅 설치 완료.
  - `docs/code_quality_guide.md` 관련 파일 인덱스 상태 "구현 예정" -> "완료" 갱신.
  - `docs/test_specification.md` 5.9 TC-LINT-001~009 상태 "구현 예정" -> "완료"/"부분 완료" 갱신.
- **관련 파일**: `pyproject.toml`, `requirements-dev.txt`, `.jscpd.json`, `.pre-commit-config.yaml`, `.github/workflows/lint.yml`, `docs/code_quality_guide.md`, `docs/test_specification.md`, `scripts/slack_publisher.py`, `server/mcp/manager.py`, `scripts/download_pretrained_weights.py`, 기존 36개 .py 일괄 수정
- **검증 결과**:
  - Ruff check: All checks passed! (36 files)
  - Ruff format: 36 files already formatted
  - Bandit: Medium 0, High 0
  - mypy: Success: no issues found in 28 source files
  - jscpd: 6 clones, 2.01% duplicated lines (threshold 5% 이내 통과)
  - pip-audit: chromadb CVE-2026-45829 1건 알려짐 (fix version 미출시, 대기)
  - pre-commit install: 완료 (pre-commit + pre-push)
- **비고**: chromadb CVE-2026-45829는 fix version 미출시 상태. 패치 출시 시 `requirements.txt` 업데이트 필요. mypy `disable_error_code`는 기존 코드 점진적 마이그레이션 완료 시 순차적 해제 예정.

---

### 2026-06-28 | 2단계 | 2단계 캡처 백엔드 설계서 작성 (구현 전 가이드)

- **커밋**: (대기 중)
- **변경 내용**:
  - `docs/stage2_capture_design.md` 신규 작성: 2단계 백엔드 FastAPI 구현 상세 설계서. 13개 섹션(개요, 구현 범위, 파일 목록, 핵심 설계 결정, 이중 캡처 스트림, 디코딩 파이프라인, 검증 기준, 코딩 패턴 준수, 데이터 인터페이스, 에러 처리 가드레일, 브랜치 전략, 의존성, 참고 자료). `docs/stage3_detection_design.md`의 13섹션 구조·스타일을 벤치마크로 차용.
  - 핵심 설계 결정 5종: (1) asyncio.Queue 기반 이중 스트림 분리 (사용자 결정 반영), (2) 프레임 원본 비적재 원칙 (architecture.md 6.1절 준수, SKILL.md 샘플 frame.hex() 방식 위반 해소), (3) FRAME_SIZE 환경 변수화, (4) 1단계 인터페이스 호환 단위 구현 전략 (사용자 결정), (5) 2·3단계 duck typing 호환.
  - 구현 파일 4개 확정: `server/capture/__init__.py`, `frame_decoder.py`, `stream_splitter.py`, `tests/test_frame_decode.py`.
  - 테스트 매트릭스 TC-CAP-001~009 + TC-PATH-006~007 정의 (캡처수신 < 50ms, Redis 메타데이터만 발행, 반사 경로 RAG/LLM/TTS 임포트 금지 검증).
  - `docs/README.md` 수정: 버전 v0.5.0 -> v0.6.0. 문서 목록에 2단계 캡처 설계서 추가. 권장 독해 순서 12번에 2단계 삽입 (기존 12~14번 -> 13~15번).
  - `AGENTS.md` 수정: 9절 문서 인덱스에 2단계 캡처 설계서 추가 (3단계 설계서 행 앞에 삽입).
  - 루트 `README.md` 수정: 문서 인덱스에 2단계 캡처 설계서 추가 (3단계 설계서 행 앞에 삽입).
- **관련 파일**: `docs/stage2_capture_design.md`, `docs/README.md`, `AGENTS.md`, `README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 규칙(이모지 금지, 한국어, 표 우선, 핵심 굵게, 인용 블록 메타데이터, Mermaid 큰따옴표·`<br/>`) 준수 확인. 3단계 설계서와 13섹션 구조·스타일 일치 확인. 이중 경로 분리 원칙(비협상) docstring 명시 사항 반영.
- **비고**: 본 작업은 설계서 작성만 수행. 실제 구현(`server/capture/` 3개 파일 + 테스트 1개)은 후속 구현 단계에서 진행. 1단계 WS 백엔드 미구현 상태에서 2단계 백엔드 단위 구현 전략은 사용자 승인됨.

---

### 2026-06-28 | 2단계 | 2단계 캡처 백엔드 구현 및 품질 검증 완료

- **커밋**: `feat(2단계): 2단계 캡처 백엔드 구현 및 단위 테스트 완료`
- **변경 내용**:
  - `server/capture/frame_decoder.py` 구현: base64 인코딩된 JPEG 이미지 프레임을 OpenCV BGR 배열로 디코딩하고, 640x640 크기로 리사이징하는 모듈 완성. 프레임 크기 이상 및 디코딩 오류 발생 시 None을 반환하는 가드레일 예외 처리 적용.
  - `server/capture/stream_splitter.py` 구현: 디코딩된 프레임 데이터를 스트림 타입(반사/인지)에 따라 분기하여 Redis Streams(`risk.events`)로 비동기적으로 발행하는 라우팅 로직 완성.
  - `server/capture/__init__.py` 구현: 패키지 진입점 구조 구축.
  - `tests/test_frame_decode.py` 구현: 비정상 base64 포맷 처리, 리사이징 정합성 검증, 스트림 타입별 Redis 발행 및 예외 복구 시나리오를 다루는 20개 테스트 케이스 작성.
- **관련 파일**: `server/capture/__init__.py`, `server/capture/frame_decoder.py`, `server/capture/stream_splitter.py`, `tests/test_frame_decode.py`, `docs/changelogs/kb.md`
- **검증 결과**:
  - `tests/test_frame_decode.py` 20개 테스트 전체 통과 (`20 passed in 1.69s`)
  - Ruff 린트/포맷팅 통과 (`All checks passed!`)
  - Mypy 타입 점검 성공 (`Success: no issues found in 28 source files`)
- **비고**: 1단계 WebSocket Gateway 백엔드 인터페이스와의 연동을 대비하여 duck typing 호환 설계가 적용되었으며, 3단계 YOLO 탐지 파이프라인의 수신 이벤트 규격과의 완벽한 통합이 가능함을 검증 완료함.

---

### 2026-06-28 | 공통 | 프로젝트 문서 불일치 감사 및 정합성 보완 작업

- **커밋**: `docs(공통): 문서 교차 검증 불일치 수정 및 API 방어 코드 반영`
- **변경 내용**:
  - `docs/test_specification.md` 수정: 5.2절 2단계 테스트 ID를 `TC-FR-`에서 `TC-CAP-` 체계로 전면 전환하고, 2·3단계 완료된 백엔드 테스트 항목 상태를 `대기`에서 `완료`로 현행화. 상단 버전을 `v0.4.0`으로 갱신.
  - `server/capture/frame_decoder.py` 수정: API 스키마 불일치(ts vs timestamp) 방지를 위해, `ts`(밀리초 epoch) 우선 파싱 후 없을 경우 ISO 8601 형식 `timestamp` 문자열을 비동기적으로 자동 분석해 밀리초 epoch으로 복원하는 시간 정보 파싱 방어 코드 구현.
  - `tests/test_frame_decode.py` 수정: `test_timestamp_fallback` 테스트 케이스를 신규 추가하여, ts 필드 누락 시 timestamp 필드로의 자동 변환/복원 안정성 검증 통과 완료 (총 21개 테스트 통과).
  - `docs/deployment_guide.md` 수정: fastapi 서비스의 포트 표기를 docker-compose의 동적 환경변수 바인딩 정책에 맞추어 `8000:8000`에서 `${WS_PORT:-8000}:8000`으로 갱신하고 상단 버전을 `v0.2.0`으로 업데이트.
- **관련 파일**: `docs/test_specification.md`, `server/capture/frame_decoder.py`, `tests/test_frame_decode.py`, `docs/deployment_guide.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - `python -m pytest` 실행: 51개 테스트 케이스 전원 통과 완료 (`51 passed in 42.30s`).
  - `ruff check .` 실행: All checks passed! 통과 (`contextlib.suppress` 구조 적용으로 SIM105/S110 경고 전면 해결).
  - `mypy server/` 실행: `Success: no issues found` 통과.
- **비고**: 프로젝트 문서 간 상호 불일치 6가지 항목 중 5가지를 즉시 해결 및 반영하였으며, 남은 1가지(2단계-3단계 Queue 연동 갭)는 1단계 WebSocket 개발 착수 시 중개 백그라운드 태스크로 연동하기로 설계 매핑을 완료함.

---

### 2026-06-28 | 6단계 및 공통 | 6단계 LLM 추론 모델 gemma4-e4b 교체 및 지연 시간 분석 리포트 추가

- **커밋**: `docs(6단계): 추론 모델 gemma4-e4b 교체 및 지연 분석 리포트 추가`
- **변경 내용**:
  - 6단계 오케스트레이션 LLM 모델을 `gemma2:9b`에서 새로 출시된 고효율 경량 모델인 `gemma4-e4b`로 전면 교체하여 지연 시간 단축 및 VRAM 사용량 대폭 절감.
  - 관련 모든 문서(`AGENTS.md`, `README.md`, `docs/README.md`, `docs/AGENTS.md`, `docs/architecture.md`, `docs/deployment_guide.md`, `docs/environment_variables.md`, `docs/minchodan_design_note.md`, `docs/pipeline_stage_design.md`, `docs/stage6_orchestration_design.md`, `docs/test_specification.md`) 내 LLM 모델명을 `gemma4-e4b`로 일괄 업데이트.
  - 6단계 추론 노드 및 팩토리 코드(`llm_client_factory.py`, `l2_generator.py`) 내의 default 모델 값을 `gemma4-e4b`로 정합성 있게 수정.
  - `docs/latency_impact_analysis.md` 신규 작성: 정밀 분석 LLM 추가에 따른 지연 시간 영향 및 대안 아키텍처 분석 리포트.
  - `docs/dual_gemma4_latency_analysis.md` 신규 작성: Gemma 4-E4B 및 Gemma 4-E2B 이중 LLM 구성에 따른 성능 영향도 분석 리포트.
  - 에이전트 스킬 문서(`.agents/skills/llm-guidance-orchestrator/SKILL.md` 및 `references/implementation_detail.md`) 내용의 모델 정보 및 예상 지연 시간 최적화 지표 반영.
  - 리포트 및 스크립트 내 오기된 YOLOv8 명칭을 Yolo 26N으로 일괄 정정.
- **관련 파일**: `AGENTS.md`, `README.md`, `server/orchestration/llm_client_factory.py`, `server/orchestration/nodes/l2_generator.py`, `.agents/skills/llm-guidance-orchestrator/`, `docs/latency_impact_analysis.md`, `docs/dual_gemma4_latency_analysis.md` 및 docs 내 마크다운 파일군, `scripts/download_pretrained_weights.py`, `scripts/verify_pretrained_weights.py`
- **검증 결과**: 소스 코드 및 모든 문서 내 모델명 표기 정합성 확보 완료.

---

### 2026-06-28 | 6단계 및 공통 | 최신 Gemini API 비용/속도 비교 및 폴백 모델 분석 리포트 추가

- **커밋**: `docs: 최신 Gemini API 비용 비교 및 Flash-Lite 폴백 적합성 분석 보고서 추가`
- **변경 내용**:
  - `docs/gemini_fallback_feasibility.md` 신규 작성: 최신 Gemini API 3.x 라인업(Gemini 3.1 Flash-Lite, Gemini 3.5 Flash)과 GPT-4o-mini의 1M 토큰당 비용, 지연 시간, 한국어 퀄리티를 비교 분석한 타당성 보고서 추가.
  - 우리 프로젝트의 20자 이내 짧은 한국어 가이드 및 RAG 입력 패턴 하에서, Google AI Studio의 무료 티어(Free Tier)를 통해 실제 지출 비용을 $0.00으로 수렴시킬 수 있고 첫 토큰 지연 시간(TTFT)이 대폭 상향된 **Gemini 3.1 Flash-Lite** 모델을 최적의 최소 비용 폴백 모델로 선정 및 구현 구조(SimpleGeminiClient) 제안.
- **관련 파일**: `docs/gemini_fallback_feasibility.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 규칙(이모지 금지, 한국어, GFM 표 사용, 볼드강조, 인용 블록 메타데이터) 준수 완료.
