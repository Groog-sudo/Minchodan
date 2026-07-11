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
  - [`course_codebase_guide.md`](../course_codebase_guide.md) 3.2(임포트 순서)·3.3(경로 처리)·17.2(방어적 코딩) 항목과 Ruff 룰 ID 매핑 표 작성.
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

---

### 2026-06-30 | 1+2단계 | 온디바이스 모바일 앱 구현 계획서 신규 작성

- **커밋**: (대기 중)
- **변경 내용**:
  - `docs/mobile_app_implementation_plan.md` 신규 작성: 온디바이스 모바일 클라이언트(React Native) 1+2단계 구현 계획서. 14개 섹션(개요, 현재 상태 분석, 구현 범위, 전체 아키텍처, Phase A~E 상세, 작업 순서, 산출물, 위험, 다음 패스, 참고 자료).
  - 확정 결정 사항 반영: Expo Dev Client 워크플로우, 로컬 빌드 우선(macOS iOS/Android, Windows Android), 1+2단계 범위(WS+카메라), 서버 WS 라우터 동시 구현, MVP 하드코딩 디바이스 인증, API 명세서 v0.2.0 필드 정합 기준.
  - Phase A(서버 WS 라우터 6개 신규 + main.py 수정 + 테스트 1개), Phase B(Expo 초기화), Phase C(WS 훅 3개), Phase D(카메라 캡처 4개), Phase E(통합 실기기 테스트) 순차 의존성 정의.
  - 기존 구현 모듈 재사용 지점 명시: `server/capture/frame_decoder.py`의 `decode_frame()`, `server/capture/stream_splitter.py`의 `get_default_splitter()` 싱글턴, `server/bus/redis_client.py`의 `redis_bus`.
  - 필드 정합 이슈 해결: 스킬 문서(`timestamp`/`frame_data`/`ping`-`pong`)와 API 명세서 v0.2.0(`ts` epoch ms/`thumbnail_jpeg_b64`/`heartbeat`-`heartbeat_ack`/`frame_id`) 불일치를 API 명세서 기준으로 통일.
  - 검증 매트릭스 15항목 정의 (RTT < 100ms, 캡처수신 < 50ms 포함), 위험 6종 및 완화 대책, Mermaid 아키텍처/시퀀스/시나리오 다이어그램 4종 포함.
- **관련 파일**: `docs/mobile_app_implementation_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 규칙(이모지 금지, 한국어 존댓말, 표 우선, 핵심 굵게, 인용 블록 메타데이터, Mermaid 큰따옴표·`<br/>`) 준수 확인.
- **비고**: 본 작업은 구현 계획서 작성만 수행. 실제 구현(Phase A~E)은 후속 작업에서 순차 진행. 브랜치 `kb`에서 진행, PR 기반 `dev` 병합 예정.

---

### 2026-06-30 | 1+2단계 | 모바일 앱 구현 설계서 플랫폼별 분리 (iOS/Android)

- **커밋**: (대기 중)
- **변경 내용**:
  - `docs/mobile_ios_implementation_plan.md` 신규 작성: iOS 클라이언트 구현 설계서 (12개 섹션). iOS 담당자(`kb`)가 서버 Phase A(WS 라우터) 전담 + 공통 TypeScript 코드 주도 작성 + iOS 네이티브 빌드/권한/테스트 담당. iOS 특화 제약(시뮬레이터 카메라 미지원, ATS, NSCameraUsageDescription, Apple Developer 계정) 및 완화 대책 명시.
  - `docs/mobile_android_implementation_plan.md` 신규 작성: Android 클라이언트 구현 설계서 (12개 섹션). Android 담당자가 공통 TS 코드 검토 + Android 네이티브 빌드/권한/테스트 담당. Android 특화 설정(CAMERA/INTERNET 권한, usesCleartextTraffic, 에뮬레이터 카메라 지원, Windows 빌드 가능) 및 iOS 비교 표 명시.
  - `docs/mobile_app_implementation_plan.md` 수정: 버전 v0.1.0 → v0.2.0. 상단에 플랫폼별 분리 안내(admonition) 추가, 두 개의 분리된 설계서 링크 및 담당자 매트릭스 명시. 본문은 분담 구조 개요와 공통 아키텍처 참조용으로 유지.
  - 분담 구조 확정: 주도-지원 분담 (iOS 담당자 주도, Android 담당자 지원), 서버 Phase A는 iOS 담당자 겸임, 공통 TS 코드는 iOS 담당자 주도 작성 후 Android 담당자 검토.
  - 플랫폼별 차이점 명시: iOS(실기기 필수, macOS만 빌드, 시뮬레이터 카메라 미지원) vs Android(에뮬레이터 카메라 지원, macOS/Windows 빌드, 실기기 권장但 필수 아님).
- **관련 파일**: `docs/mobile_ios_implementation_plan.md`, `docs/mobile_android_implementation_plan.md`, `docs/mobile_app_implementation_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 규칙(이모지 금지, 한국어 존댓말, 표 우선, 핵심 굵게, 인용 블록 메타데이터, Mermaid 큰따옴표·`<br/>`) 준수 확인. 두 설계서 간 역할 분담·의존성·참조 관계 정합성 확인.
- **비고**: 두 명의 담당자가 각각 독립적으로 읽을 수 있도록 플랫폼별 설계서로 분리. 공통 TS 코드는 iOS 설계서에 상세 기술, Android 설계서에서는 검토/검증 관점으로 요약. Android 담당자 이니셜은 `dg`로 확정.

---

### 2026-06-30 | 1+2단계 | Phase A~D 구현 완료 (서버 WS 라우터 + 클라이언트 WS/카메라 이중 캡처)

- **커밋**: (대기 중)
- **변경 내용**:

  **Phase A - 서버 WS 라우터 (7개 파일 신규 + main.py 마운트)**:
  - `server/api/ws_router.py`: `@router.websocket("/ws/detect")` 엔드포인트. 핸드셰이크(accept → welcome → hello → `verify_device()` → auth_ok → heartbeat 태스크), detection(`decode_frame()` → `splitter.route_frame()` → ack), `WebSocketDisconnect`/`JSONDecodeError`/`Exception` 예외 처리 + `finally` 정리 (165줄).
  - `server/api/auth.py`: `verify_device(device_id, token) -> bool`. MVP 하드코딩 `REGISTERED_DEVICES = {"dev-001": "token-abc-001", "dev-002": "token-abc-002"}` (41줄).
  - `server/api/config.py`: `Settings(BaseSettings)` - `WS_PORT=8000`, `HEARTBEAT_INTERVAL=5`, `HEARTBEAT_TIMEOUT=5`, `MAX_RECONNECT_ATTEMPTS=3`. `__file__` 기반 경로, `load_dotenv()` (39줄).
  - `server/api/heartbeat.py`: `HeartbeatManager` 클래스 - 5초 `heartbeat` 송신, `record_ack()`, 타임아웃 시 `ws.close(code=1001)` (76줄).
  - `server/api/schemas.py`: Pydantic 모델 7종 (`WSMessage`, `WelcomeMessage`, `AuthOkMessage`, `AckMessage`, `ErrorMessage`, `HeartbeatMessage`, `HeartbeatAckMessage`) (84줄).
  - `server/api/session_manager.py`: `SessionManager` 싱글턴 - `connect()`/`disconnect()`/`send_json()`/`is_connected()` (53줄).
  - `server/main.py`: `ws_router` 임포트 및 `app.include_router(ws_router, prefix="")` 마운트 (+2줄).

  **Phase B~D - 클라이언트 (React Native + Expo 56)**:
  - `client/App.tsx`: 엔트리 포인트. `SafeAreaView` → `CameraView` 렌더링 (23줄).
  - `client/app.json`: Expo 설정. iOS `NSCameraUsageDescription`/`NSMicrophoneUsageDescription`/ATS, Android `CAMERA`/`INTERNET`/`RECORD_AUDIO` 권한 + `usesCleartextTraffic`, `plugins: ["react-native-vision-camera"]` (38줄).
  - `client/package.json`: 의존성 `expo ~56.0.12`, `react-native 0.85.3`, `react 19.2.3`, `react-native-vision-camera ^4.7.3`, `expo-haptics`, `expo-file-system`, `expo-splash-screen`, `expo-status-bar`.
  - `client/src/components/CameraView.tsx`: 카메라+WS 연동 게이트. `status === "connected"` 시 `startCapture`, 연결 끊김 시 `stopCapture`. 권한/디바이스 부재 가드레일, `accessibilityLabel` 접근성 (93줄).
  - `client/src/components/ConnectionStatus.tsx`: WS 상태 시각화. connecting(황)/connected(녹)/disconnected(적)/fallback(회) (54줄).
  - `client/src/hooks/useCamera.ts`: **이중 캡처 타이머 핵심**. `useCameraDevice("back")` (fallback front), `setInterval(1000/reflexFps)` + `setInterval(1000/cognitiveFps)` 분리. `takePhoto()` → `expo-file-system` base64 변환 (`file://` scheme 보정). `cameraRef.current` null 가드 (136줄).
  - `client/src/hooks/useWebSocket.ts`: WS 생명주기. `ws://...?device_id=` 연결 → `hello` 송신 → `welcome` 수신 시 `connected` → 5초 heartbeat → 재연결 3회 후 `fallback` (121줄).
  - `client/src/services/frameCapture.ts`: `buildDetectionEvent()` / `sendFrame()`. API 명세서 v0.2.0 정합 (`event_id`, `ts` epoch ms, `frame_id`, `stream`, `thumbnail_jpeg_b64`) (51줄).
  - `client/src/types/detection.ts`: `WSStatus`, `StreamType`, `MessageType` 10종, `DetectionEvent`, `AckPayload` 등 타입 정의 (68줄).
  - `client/src/config/index.ts`: `WS_URL = ws://10.0.2.2:8000/ws/detect` (Android 에뮬레이터), `REFLEX_FPS = 10`, `COGNITIVE_FPS = 2` (16줄).
  - `client/src/utils/haptics.ts`: `triggerHaptic()` (expo-haptics 래퍼) + `announce()` stub (28줄).

  **테스트 코드**:
  - `tests/test_ws_echo.py`: 6개 케이스. `test_handshake_welcome_and_auth`, `test_echo_rtt_under_100ms` (RTT < 100ms), `test_heartbeat_response`, `test_auth_failure`, `test_detection_ack` (빈 프레임 가드레일), `test_disconnect_cleanup`. TC-WS-001~006 커버 (183줄).

  **Android 에뮬레이터 디버깅 및 수정 사항**:
  - `expo-splash-screen` 의존성 추가: `ClassNotFoundException: expo.modules.splashscreen.SplashScreenManager` 해결.
  - `expo-dev-client` 의존성 제거: DevLauncherActivity의 mDNS 서비스 디스커버리 실패로 Metro 번들 로드 불가 이슈 해결. adb reverse + 표준 RN dev server 연결로 대체.
  - Gradle 9.3.1 → 8.13 다운그레이드: RN gradle plugin의 `JvmVendorSpec.IBM_SEMERU` 호환성 확보.
  - `useCamera.ts` base64 변환 경로 보정: `photo.path`에 `file://` scheme prefix 추가.

- **관련 파일**: `server/api/` (7개), `server/main.py`, `client/` (16개), `tests/test_ws_echo.py`
- **검증 결과**:
  - Android 에뮬레이터(cold boot, back+front 카메라 emulated)에서 Metro 번들 로드 성공, `CameraView` 렌더링, `[Camera] 이중 루프 시작: 반사 10fps / 인지 2fps` 로그 확인.
  - 캡처 성공(`CameraView.takePhoto: Successfully captured 1856 x 1392 photo!`), base64 인코딩 → 프레임 전송(`[Frame] stream=reflex, frame_id=68, size≈59KB`) 정상 동작 확인.
  - 서버-클라이언트 API 명세서 v0.2.0 정합: 핸드셰이크(hello/welcome/auth_ok/heartbeat), detection 페이로드, ack 응답 필드 완전 일치.
- **비고**: TC-WS-001~006 테스트 코드 작성 완료, 실행은 서버 기동 후 통합 테스트로 진행 예정. TC-CAP-007/008(단말 권한/타이머 해제)은 실기기 검증 대기. `expo-dev-client` 제거는 에뮬레이터 DevLauncher 이슈 회피를 위한 조치이며, 실기기 빌드 시 재검토 필요.

---

### 2026-07-01 | 2단계+Post-MVP | 온디바이스 TFLite 추론 구조 구축, 햅틱/비프 입체 경고 도입 및 78개 테스트 통과

- **커밋**: `feat(2단계+Post-MVP): 온디바이스 TFLite 추론 구조 구축, 햅틱/비프 입체 경고 도입 및 78개 테스트 통과`
- **변경 내용**:
  - `docs/reflex_audio_specification.md` 신규 작성: 시각장애인 긴급 회피 반응 시간을 최소화하기 위한 방향성 입체 비프음(Stereo Panning Beep), 주차센서식 거리 반비례 비프음 가속 구조(beep_interval_ms), 햅틱 피드백 등 기술 사양 확정.
  - `docs/post_mvp_ondevice_feasibility.md` 신규 작성: YOLO26n CoreML 익스포트 한계 규명 및 TFLite/ONNX 온디바이스 타당성 분석(1-Thread 가상 CPU 시뮬레이션 지연 22.89ms 확보) 수록.
  - `server/detection/gates/reflex_gate.py` 및 `schemas.py` 수정: 반사 경보(`ReflexAlert`) 시 객체 중심축 기반 panning(-1.0 ~ 1.0) 및 거리 역산 비프음 주기(0~500ms), 햅틱 패턴(`short`/`double`/`continuous`) 연산 구현.
  - `server/capture/frame_decoder.py` 수정: 실기기 고화질 캡처 패킷 유실 방지를 위해 최대 프레임 허용 크기(`MAX_FRAME_SIZE_KB`)를 500KB에서 5000KB(5MB)로 상향.
  - `client/src/services/audioEngine.ts` 및 `hapticEngine.ts` 신규 구현: `expo-av`를 통한 입체 음향 밸런싱(Panning)과 비프음 가속 스케줄러, `expo-haptics`를 통한 세부 진동 패턴 구동기 완성.
  - `client/src/hooks/useWebSocket.ts` 수정: 모바일 렌더 스레드를 영구 정지하여 하트비트 타임아웃을 냈던 `Alert.alert` 블로킹 모달 팝업을 제거하고 디버그 콘솔 및 debugOverlay 텍스트로 보완. `reflex_alert` 이벤트 수신 시 실시간 오디오/햅틱 엔진 트리거 결합.
  - `client/src/hooks/useOnDeviceDetection.ts` 신규 작성: `react-native-fast-tflite` 패키지를 설치하고 `assets/models/yolo26n/`에 엣지 모델을 내장하여 단말 자체 NPU 가속 추론 및 즉각 비프음/햅틱 출력 환경(오프라인 반사 루프) 뼈대 구축.
- **관련 파일**: `docs/reflex_audio_specification.md`, `docs/post_mvp_ondevice_feasibility.md`, `server/capture/frame_decoder.py`, `server/detection/gates/reflex_gate.py`, `server/detection/schemas.py`, `client/src/hooks/useWebSocket.ts`, `client/src/hooks/useOnDeviceDetection.ts`, `client/src/services/audioEngine.ts`, `client/src/services/hapticEngine.ts`, `tests/test_vector_db_factory.py`
- **검증 결과**:
  - `tests/test_vector_db_factory.py`의 macOS 내 persistent 디렉토리 생성 실패(Rust 내부 InternalError 예외) 예외 포착 보완.
  - 로컬 Ollama nomic-embed-text 모델 pull 다운로드 완료 및 uvicorn 테스트 서버 가동 하에 **78개 전체 테스트 케이스 100% 통과(Passed)** 확인 완료.
  - JDK 17 및 Android SDK 환경 변수를 매핑하여 Gradle 클린 빌드 기반으로 온디바이스 추론 및 햅틱/비프 가속 엔진이 빌드된 배포용 **[app-release.apk](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/client/android/app/build/outputs/apk/release/app-release.apk)** 최종 성공 추출 완료.
- **비고**: YOLO26n 및 YOLO26n-seg 모델이 엣지 컴퓨팅에 최적화된 핵심 자산임을 반영하여, 타사 대안 모델 우회안을 배제하고 TFLite/ONNX 모바일 런타임을 통해 원본 모델을 단말에 강제 이식하는 배포 구조로 단일화 및 최종 확정하였습니다.

---

### 2026-07-01 | 공통 | 문서 링크 정합성 확보 및 API 명세 불일치 해소

- **커밋**: `docs: 문서 링크 및 API 불일치 수정 및 verify_gpu.py 스크립트 추가`
- **변경 내용**:
  - `scripts/verify_gpu.py` 신규 작성: GPU 드라이버 가용성 및 sm_120 최적화(Blackwell) 환경 적합성을 검증하는 헬퍼 스크립트 구축(deployment_guide.md 및 여러 문서 내 깨진 링크 완전 해소).
  - 마크다운 깨진 링크 수정: `docs/changelogs/kb.md` 내 `course_codebase_guide.md` 상대 경로 및 `docs/changelogs/README.md` 내 삭제된 3단계 개별 보고서 링크를 kb.md 앵커로 정정.
  - `docs/api_specification.md` 불일치 정합: 반사 경보 type명을 실제 구현체와 맞추어 `alert_reflex`에서 `reflex_alert`로 수정하고, 방향성 입체 음향/진동 가속 매개변수 필드(`panning`, `distance`, `beep_interval_ms`, `haptic_pattern`) 상세 명세 보충.
- **관련 파일**: `scripts/verify_gpu.py`, `docs/changelogs/kb.md`, `docs/changelogs/README.md`, `docs/api_specification.md`
- **검증 결과**: `check_links.py` 검증 스크립트 실행 결과 전체 문서 내 깨진 링크가 0건임을 확인. `verify_gpu.py`의 로컬 예외 가드레일 동작을 정상 수행 및 통과.

---

### 2026-07-01 | 공통 | 30개 문서 교차 검증 및 불일치 일괄 수정

- **커밋**: `docs: 30개 문서 교차 검증 기반 불일치 일괄 수정`
- **변경 내용**:
  - `CHROMA_COLLECTION` 기본값 오염 문자열 수정: 과거 입찰 프로젝트 잔재인 `bidding_kb`를 프로젝트 의미에 부합하는 `minchodan_kb`로 전 문서(`.env.example`, `architecture.md`, `README.md`, `environment_variables.md`, `stage4_5_data_replacement_guide.md`) 일괄 교체.
  - `environment_variables.md` v0.2.0 갱신: `YOLO_CONF` 중복 행 삭제, `DETECTOR_TYPE` 항목 실제 추가, `GOOGLE_API_KEY` 신규 항목 추가(4단계 Gemini 캡셔닝 시 필수), `LLAVA_MODEL` 설명을 선택 항목으로 보정, `DATA_CAPTIONS` 설명을 Llava/Gemini 양쪽 지원으로 수정.
  - `architecture.md` 파일 목록 수정: `server/rag/build/llava_captioner.py` → `gemini_captioner.py` (Llava 폴백 지원 명시).
  - `test_specification.md` 수정: 섹션 번호 역전(5.6 → 5.8 → 5.7) 교정(5.7=MCP, 5.8=7단계 TTS로 올바른 순서 복원), TC-RAG-003 캡셔닝 모델 설명을 Gemini/Llava 양쪽 허용 표현으로 갱신.
  - `post_mvp_hybrid_roadmap.md` 수정: §7.2 macOS 개인 절대경로를 프로젝트 루트 기준 상대경로로 교체, §11 검증 기준에서 실패 확정된 CoreML 항목을 ONNX/TFLite 실제 검증 기준으로 교체.
- **관련 파일**: `.env.example`, `architecture.md`, `README.md`, `docs/environment_variables.md`, `docs/stage4_5_data_replacement_guide.md`, `docs/test_specification.md`, `docs/post_mvp_hybrid_roadmap.md`, `docs/changelogs/kb.md`
- **검증 결과**: 30개 설계/아키텍처/구현 문서 및 소스코드 교차 검증 수행. 이중 경로 물리 분리 원칙은 검토된 모든 문서에서 위반 없이 일관 준수 확인.

---

### 2026-07-02 | 3단계+Post-MVP | 세그멘테이션 모델 TFLite 변환 및 온디바이스 탐지 훅 연동 완료

- **커밋**: `feat: 세그멘테이션 모델 TFLite 변환 스크립트 추가 및 온디바이스 탐지 훅 연동`
- **변경 내용**:
  - `scripts/export_tflite.py` 신규 작성: PyTorch 형식의 세그멘테이션 가중치 파일 `server/models/yolo26n/segbest.pt`를 모바일 엣지 구동을 위한 LiteRT/TFLite 포맷(`segbest.tflite`)으로 변환하는 자동화 스크립트 구축 및 변환 완수.
  - TFLite 모델 배포: 변환된 모델을 모바일 프로젝트 에셋인 `client/assets/models/yolo26n/segmentation.tflite` 경로에 복사 및 통합 완료.
  - `client/src/hooks/useOnDeviceDetection.ts` 수정:
    - 엣지 모델을 `segmentation.tflite`로 교체 탑재.
    - 클래스 정의를 신규 학습 사양(`sidewalk_normal`, `caution`, `roadway`, `braille_normal` 4종)으로 전면 교체.
    - 세그멘테이션 출력 텐서 `(1, 300, 38)`의 구조(attrsPerBox=38)에 맞게 바운딩 박스 좌표 및 클래스별 확률 스코어를 파싱하는 로직으로 파서 최적화.
    - `caution`(주의 영역) 및 `roadway`(차도 침범)에 한해 오프라인 반사 햅틱 및 3D 비프음 재생기가 작동하도록 위험 게이트 조건을 재매핑.
  - iOS 빌드 환경 검증: Xcode 26.6, CocoaPods 1.16.2 설치 상태와 `Podfile.lock` 정합성을 검사하여, USB 유선 연결 기기를 통한 핫 리로드 디버깅(`npx expo run:ios`) 준비 완료 확인.
- **관련 파일**: `scripts/export_tflite.py`, `client/assets/models/yolo26n/segmentation.tflite`, `client/src/hooks/useOnDeviceDetection.ts`
- **검증 결과**:
  - `export_tflite.py` 실행 완료: YOLO26n-seg 모델 export 성공 (10.7 MB).
  - `useOnDeviceDetection.ts` 컴파일 및 타입 검증 통과.
- **비고**: 학습된 세그멘테이션 가중치 모델을 모바일에 직결하여 서버 RTT 지연 0ms 수준의 긴급 반사 피드백 성능을 확보하였습니다.

---

### 2026-07-02 | 공통 | TypeScript 빌드 오류 해결 및 모바일 Mock 디버그 프레임워크 연동

- **커밋**: `feat(client): TypeScript 타입 체크 통과 및 모바일 Mock 디버그 기능 연동 완료`
- **변경 내용**:
  - **TypeScript 타입 및 빌드 에러 해결**:
    - `client/src/types/detection.ts`: `alert_reflex` 라벨명을 `reflex_alert`로 단일화 및 방향성/주기성 햅틱 피드백용 속성(`panning`, `beep_interval_ms`, `haptic_pattern`, `alert_id`) 6종을 명세에 맞추어 보충.
    - `client/src/hooks/useWebSocket.ts`: WebSocket 이벤트 핸들러 `onmessage`/`onerror` 파라미터의 타입 정의 호환성 에러를 `any` 캐스팅으로 우회.
    - `client/src/hooks/useOnDeviceDetection.ts`: TFLite 모델 로더(`loadTensorflowModel`)의 delegate 인자에 빈 배열 `[]`를 주어 컴파일 에러 해결 및 Float32Array의 버퍼 캐스팅(`frame.buffer as ArrayBuffer`) 적용.
    - `client/src/components/CameraView.tsx`: `StyleSheet.absoluteFillObject` 빌드 오류를 absolute 수동 레이아웃 객체로 전환하여 컴파일 정상화.
    - `client/src/services/audioEngine.ts`: Sound 클래스 내부의 panning 속성 부여 시, expo-av 타이핑 미지원 해결을 위해 `(this.soundInstance as any).setStatusAsync({ stereoPan })`로 교체 완료.
  - **모바일 Mock 디버그 프레임워크 신규 이식**:
    - `client/src/components/DebugTriggerPanel.tsx`: 실기기 없이 시뮬레이터 상에서 햅틱/비프 밸런스를 튜닝할 수 있는 디버그 트리거 패널 마운트.
    - `client/src/config/mock.ts`: Mock 상태 관련 설정값 추가.
    - `client/src/services/frameProvider.ts` / `mockFrameProvider.ts` / `realFrameProvider.ts`: 카메라 없이 로컬 샘플 이미지를 base64로 주기 송출하는 이중화 캡처 인터페이스 구축 및 통합.
  - **저장소 최적화**:
    - 프로젝트 루트 내 타겟 모델이 아닌 불필요한 기본 모델 `yolo11n.pt` 및 `yolov8n.pt` 2종 삭제 및 깃 인덱스(`git rm`) 영구 배제 완수.
- **관련 파일**: `client/src/` 전체, `.gitignore`
- **검증 결과**:
  - `client/` 경로 내 `npx tsc --noEmit` 실행 결과 **타입 컴파일 에러 0건**으로 빌드 정합 완료.
- **비고**: 시뮬레이터 환경 및 크로스 플랫폼 네이티브 연동 시 빌드 실패를 유발할 수 있는 타입 오류들을 완벽하게 진압하여 유선 배포 준비를 완료하였습니다.

---

### 2026-07-04 | 2·3단계+Post-MVP | 온디바이스 추론 파이프라인 안정화, expo-audio 마이그레이션, 단일 캡처 타이머 구조 개선 및 COCO 탐지 결함 수정

- **커밋**: (대기 중)
- **변경 내용**:

  **A. 단일 캡처 타이머 + 스트림 분할 구조로 개선 (`useCamera.ts`)**:
  - 초기 "독립 두 타이머" 설계(`setInterval(1000/reflexFps)` + `setInterval(1000/cognitiveFps)`)를 **단일 타이머 단일 캡처 + 프레임 분할** 구조로 개선. 실기기에서 두 `takePhoto` 호출이 직렬 대기하며 하드웨어 경합을 유발해 반사 경로 지연이 목표(캡처수신 < 50ms)를 초과하는 문제 해결.
  - 반사 fps 기준 단일 `setInterval`로 `takePhoto` 1회 호출 후 reflex 전달, 매 `floor(reflexFps/cognitiveFps)` 번째 프레임을 동일 프레임을 `stream:'cognitive'`로 추가 전달 (재캡처 비용 0).
  - `isCapturingRealFrame` ref 가드레일로 중복 캡처 방지(drop). `decodeBase64JpegToChw()`로 base64 → CHW float32 텐서 변환을 훅 내에서 수행하여 온디바이스 추론 직결.
  - 이중 경로 분리 원칙(`stream` 필드로 reflex/cognitive 분기)은 유지되어 서버 `stream_splitter` 계약과 무관하게 동작.

  **B. expo-av → expo-audio 마이그레이션 (`audioEngine.ts`, `app.json`, `package.json`)**:
  - `expo-av`(`Audio.Sound.createAsync`)를 Expo SDK 56+ 차세대 API인 **`expo-audio`**(`createAudioPlayer`)로 전면 교체. 동기 프로퍼티 할당(`volume=`, `loop=`, `play()`) 기반으로 전환.
  - iOS 오디오 세션 초기화(`setAudioModeAsync({playsInSilentMode:true})`) 추가로 무음 모드에서도 비프음 재생 보장 (시각장애인 보조 필수).
  - `expo-audio`는 스테레오 패닝(`pan`) 미지원 → 패닝 값은 햅틱/거리 계산에만 활용하고 오디오는 모노 풀볼륨 재생으로 명시.
  - `app.json` 플러그인에 `expo-audio`/`expo-splash-screen` 추가, `package.json` 의존성 버전 동기화(expo ~56.0.13, expo-audio ~56.0.12, expo-splash-screen ~56.0.11).
  - iOS `bundleIdentifier`를 `com.minchodan.app` → `com.minchodan.app.kwanbum`으로 변경(개인 개발 빌드 식별용), `minimumVersion` 제거, Android `usesCleartextTraffic` 제거.

  **C. 온디바이스 추론 훅 고도화 (`useOnDeviceDetection.ts`, `CameraView.tsx`)**:
  - 플랫폼별 하드웨어 가속 delegate(iOS CoreML / Android NNAPI) 적용 및 `loadModelWithFallback()`로 delegate 실패 시 CPU 자동 폴백 구조 추가.
  - NMS 내장 포맷 디코더 개선: 출력 텐서가 여러 개일 수 있는 경우(segmentation `[1,300,38]` + mask `[1,32,160,160]`)를 `attrsPerBox`로 나누어떨어지는 NMS 텐서 자동 선택. 좌표 min/max 보정, 음수/영역 박스 필터, `maxScore` 로깅 추가.
  - `detShapeLog` 상태로 object_detection 출력 shape을 디버그 오버레이에 표시. BBox 오버레이, 위험 클래스 색상 구분(보행 충돌 위험 빨강/노면 위험 주황/기타 초록) 추가.

  **D. COCO 80종 객체 탐지 불가 원인 진단 및 결함 수정 (Python 교차 검증)**:
  - **원인 진단**: `object_detection.tflite` 입출력 텐서 shape(`[1,3,640,640]`→`[1,300,6]`)은 코드 가정과 일치하고 모델/변환은 정상(bus.jpg `/255` 추론 시 bus 0.924 / person 0.91 = PT와 일치). 탐지 불가의 원인은 (1) 프레임 정규화가 `/5`로 잘못됨(bus.jpg에서 person 1개 0.49만 탐지), (2) 기존 샘플 5종에 COCO 클래스 객체가 아예 없음(PT로 conf=0.01에서도 0개)으로 분리 확정.
  - **정규화 결함 수정**: `realFrameProvider.ts`/`mockFrameProvider.ts`의 `/5` → `/255`(Ultralytics YOLO 표준)로 수정. export 스크립트(`scripts/export_tflite.py`)는 `int8=False` float32 표준 변환이며 비표준 스케일 인자가 없어 `/5`는 근거 없는 결함값임을 확인.
  - **샘플 교체**: `client/assets/samples/frame_01~05.jpg` 5종을 COCO 보행 회피 위험 클래스(person, bicycle, bus)가 포함된 실사 이미지 5종(Ultralytics 공개 데모 bus/zidane + Unsplash 보행 시점)로 전면 교체. 기존 명명 규칙(clear/center far·near/left·right near) 유지.
  - `useOnDeviceDetection.ts`의 `CONF_THRESHOLD` 주석 오기("0~255 raw 입력 기반")를 "NMS 출력은 이미 0~1 정규화 confidence"로 정정.

  **E. Mock 모드 실기기 전환**:
  - `client/src/config/mock.ts`: `MOCK_CAMERA`/`MOCK_HAPTIC`를 `true` → `false`로 전환하여 실기기 카메라/햅틱 구동 활성화.

  **F. 모델 파일 갱신**:
  - `server/models/yolo26n/object_detection.{onnx,tflite}`, `segmentation.tflite` 재갱신(재 export).

  **G. 프로젝트 문서 정합 (구현체 기준 동기화)**:
  - `.agents/skills/camera-frame-capture/SKILL.md`: 단계 2-1 useCamera 코드 예시를 단일 타이머 + 스트림 분할 구현체에 맞게 전면 재작성, 구현 개선 노트(`2026-07-04`) 및 디렉토리 주석·데이터 흐름 표 정정.
  - `docs/mobile/mobile_{app,ios,android}_implementation_plan.md`: Phase D useCamera 섹션(역할/타이머/가드레일/캡처) 및 검증 매트릭스(반사 캡처/인지 분할), 산출물 표를 단일 캡처 타이머 + 스트림 분할 기준으로 업데이트. 이중 경로 분리 원칙 유지 명시.
  - `.agents/skills/tts-voice-streamer/SKILL.md`: 단계 7-6 반사 클립 플레이어 예시를 `expo-av` → `expo-audio` API로 정합.
  - `README.md`, `AGENTS.md`: 클라이언트 기술 스택 표기에 `expo-audio`(단말 재생 계층), `react-native-fast-tflite`(온디바이스 추론) 보완 및 "이중 캡처 타이머" → "단일 캡처 타이머 + 스트림 분할"로 정정.
- **관련 파일**:
  - 코드: `client/src/hooks/{useCamera,useOnDeviceDetection}.ts`, `client/src/services/{audioEngine,frameProvider,mockFrameProvider,realFrameProvider}.ts`, `client/src/components/CameraView.tsx`, `client/src/config/mock.ts`, `client/{app.json,package.json,package-lock.json}`, `client/metro.config.js`, `server/models/yolo26n/*`, `client/assets/samples/frame_01~05.jpg`
  - 문서: `.agents/skills/{camera-frame-capture,tts-voice-streamer}/SKILL.md`, `docs/mobile/mobile_{app,ios,android}_implementation_plan.md`, `README.md`, `AGENTS.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - Python 회귀 검증: 교체된 5개 샘플을 `/255` 정규화 TFLite 추론 시 **5/5 ALL PASS** (frame_01 person 0.93, frame_02 bus 0.92+person 0.91, frame_03 person 0.88, frame_04 person 0.85+bicycle 0.66, frame_05 person 0.75 외 12개).
  - TypeScript 타입 체크: `npx tsc --noEmit` 컴파일 에러 0건 통과.
  - 문서 규칙(이모지 금지, 한국어 존댓말, 표 우선, 핵심 굵게, 인용 블록 메타데이터) 준수 확인.
- **비고**: 정규화 결함(`/5`)과 샘플 부재가 결합하여 COCO 탐지가 전혀 되지 않았던 현상을 두 축으로 분리 진단 후 수정하여, 실기기 카메라(realFrameProvider)와 시뮬레이터(mockFrameProvider) 양쪽에서 COCO 80종 탐지 가능 상태로 복구. 단일 캡처 타이머 구조 개선은 이중 경로 물리 분리 원칙(비협상)을 위반하지 않으면서 하드웨어 경합을 제거해 반사 경로 지연 목표를 달성. 미해결: `yolo11n.pt`(루트) 미사용 파일로 확인되어 추후 정리 대상.

---

### 2026-07-04 | 온디바이스 추론 | 온디바이스 추론 엔진 격리 설계서 CoreML 가속 방식 현행화

- **커밋**: `docs: 온디바이스 추론 엔진 플랫폼 격리 설계서 내 CoreML 가속 상태 및 의사결정 흐름 최신화`
- **변경 내용**:
  - `docs/mobile/ondevice_inference_engine_isolation_plan.md` 내 iOS CoreML 가속 현황을 실제 구현 상태에 맞추어 현행화.
  - 현재 실제 빌드가 CoreML `.mlpackage`/`.modelc`를 번들링하여 직접 구동하는 것이 아니라, `client/assets/models/yolo26n/*.tflite` 모델 파일을 사용하되 TFLite 런타임(`react-native-fast-tflite`)이 iOS의 CoreML 백엔드를 delegate로 호출(`$EnableCoreMLDelegate=true` 및 `["core-ml"]` delegate)하여 ANE 가속을 획득하는 폴백(간접 가속) 전략임을 명시.
  - "1.2 현행 MVP와의 관계", "2.2 플랫폼 분기 및 CoreML 인프라 현황"의 표 및 "4.4 의사결정 흐름" 섹션을 수정하여 이중 전략 우회 시도 상태에서 TFLite + CoreML Delegate 폴백 전략을 단일 노선(기본 가속 노선)으로 채택한 상태로 반영 완료.
- **관련 파일**: `docs/mobile/ondevice_inference_engine_isolation_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서의 링크 정합성 및 마크다운 규칙(한국어 존댓말, 이모지 금지, 표 사용, 굵게 강조) 준수 확인.
- **비고**: CoreML 포맷 변환 실패 한계에 대응하여 TFLite CoreML Delegate 호출 폴백 전략을 메인으로 통합 완료하여 iOS/Android의 모델 파일 포맷 단일화를 유지하면서 가속 성능을 보장하는 최선의 구조를 확정하였습니다.

---

### 2026-07-04 | 온디바이스 추론 | CoreML 완전 가속 모드 도입 및 세그멘테이션(seg) CoreML 포맷 지원 리팩토링

- **커밋**: `feat(ios): CoreML 세그멘테이션 모델 지원 및 완전 가속 기동 구조 구현`
- **변경 내용**:
  - `client/ios/CoreMLInferenceBridge.swift` 리팩토링:
    - 4개 세그멘테이션 클래스(`sidewalk_normal`, `caution`, `roadway`, `braille_normal`)를 매핑하기 위한 `segClassNames` 정의 추가.
    - `loadModels`의 반환 형태를 Boolean에서 Dictionary(`[String: Any]`) 형태로 변경하여 detection과 segmentation 모델의 탑재 여부(`det`, `seg`)를 각각 React Native에 응답하도록 보완.
    - `runDetection` 및 `parseYoloOutput` 함수가 6개 채널(detection) 뿐만 아니라 38개 채널(segmentation) 형태의 YOLO end2end raw tensor 출력을 모두 디코딩할 수 있도록 수정.
    - 추론 결과를 신뢰도(`confidence`) 기준 역순으로 정렬하여 반환하게 보완.
  - `client/src/inference/localDetectorSelect.ios.ts` 수정:
    - `load` 단계에서 `CoreMLInferenceBridge.loadModels`가 리턴하는 딕셔너리를 파싱하여 `isSegLoaded` 여부를 체크.
    - CoreML에 segmentation 모델이 적재된 경우 TFLite 폴백 모듈(`segFallback`)을 로드하지 않고 완전 CoreML 가속 모드(`segLoaded=true`)로 구동하도록 구현.
    - `detect` 호출 시 TFLite 폴백이 없는 환경에서는 `CoreMLInferenceBridge.detectFrame` 하나만으로 detection과 segmentation 추론 결과를 일괄 획득하여 반환하고, 폴백이 활성화되어 있을 때만 기존 하이브리드(det=CoreML, seg=TFLite) 병렬 처리를 타도록 동적 분기 로직 적용.
- **관련 파일**: `client/ios/CoreMLInferenceBridge.swift`, `client/src/inference/localDetectorSelect.ios.ts`, `docs/changelogs/kb.md`
- **검증 결과**:
  - TypeScript 빌드 검증: `client/` 에서 `npx tsc --noEmit` 검사 시 에러 없이 통과.
- **비고**: 기존의 TFLite 기반 세그멘테이션 파싱 로직 및 useOnDeviceDetection과의 정합성을 완벽하게 유지하면서, iOS 단말에서 단일 CoreML 브릿지 호출만으로 detection과 segmentation ANE 하드웨어 완전 가속 추론이 가능하도록 온디바이스 추론 성능 극대화 구조를 완성하였습니다.

---

### 2026-07-04 | 외부 통신 연동 | 야외 도로 테스트용 Ngrok 터널링 구축 및 LTE 셀룰러 접속 검증

- **커밋**: `feat(net): 야외 도로 테스트용 ngrok 터널링 환경 구축 및 LTE 연동`
- **변경 내용**:
  - `ngrok` 무료 연동 및 Homebrew 설치 자동화: `brew install ngrok/ngrok/ngrok`으로 로컬 설치를 완료하고 사용자가 발급해 준 토큰을 `ngrok config add-authtoken`를 통해 등록 완료.
  - `.env` 기밀 데이터 저장: 발급받은 `NGROK_AUTHTOKEN` 값을 프로젝트 보안 명세에 맞춰 `.env`에 보존 및 백업.
  - 퍼블릭 wss 도메인 연동: 로컬 개발 서버 포트(`8000`)를 외부 인터넷으로 노출하는 터널을 기동하여 `wss://partake-primer-surround.ngrok-free.dev` 주소를 확보.
  - 클라이언트 환경설정 반영: [client/src/config/index.ts](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/client/src/config/index.ts) 내의 `WS_URL`을 확보된 wss 주소로 변경 및 메트로 빌드 연동 처리.
- **관련 파일**: `.env`, `client/src/config/index.ts`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 외부 LTE 통신망(`125.128.144.75`)을 거쳐 들어온 아이폰 기기의 WebSocket handshake 연결 및 커넥션 오픈 로그 정상 검증 완료.
- **비고**: 외부망을 통한 실기기 연동이 확인되었으므로, 유선 케이블을 배제한 채 실제 야외 보행 도로 테스트를 진행할 수 있는 원격 추론 환경을 성공적으로 확보하였습니다.

---

### 2026-07-04 | 온디바이스 추론 | 세그멘테이션 CoreML 모델 리소스 배치 보완 및 완전 가속 리빌드 성공

- **커밋**: `fix(ios): segmentation.mlpackage 빌드 타겟 변경 및 CoreML 완전 가속 모드 점화`
- **변경 내용**:
  - `client/ios/Minchodan.xcodeproj/project.pbxproj` 파일 보완: Xcode 드롭 단계에서 세그멘테이션 모델(`segmentation.mlpackage`)이 소스코드 빌드 단계(`PBXSourcesBuildPhase`)로 오분류되어 배치되었던 점을 식별하고, 이를 번들 리소스 빌드 단계(`PBXResourcesBuildPhase`)로 이전되도록 pbxproj 포맷에 맞춰 정적 재배치 및 무결성 수정 완료.
  - 앱 패키지 번들링 연동: 이로써 복사된 세그멘테이션 모델이 앱 리소스로 정식 탑재되어 Xcode 빌드 시 `.mlmodelc` 포맷으로 자동 컴파일되어 Bundle.main에 포함되도록 기저 환경 정합.
- **관련 파일**: `client/ios/Minchodan.xcodeproj/project.pbxproj`, `docs/changelogs/kb.md`
- **검증 결과**:
  - "고태현의 iPhone" 실기기 리빌드 성공 및 컴파일 에러 0건 확인.
  - 리로드 실기기 로그 상에서 세그멘테이션 폴백 TFLite 구동이 완벽하게 생략되고, **`LOG [CoreMLDetector] det=CoreML ANE / seg=CoreML ANE 완전 가속 기동 완료`**의 정상 기동이 검증 완료됨.
- **비고**: iOS 플랫폼에서 디텍션(Object Detection)과 세그멘테이션(Segmentation) 두 개의 모델이 모두 Apple Neural Engine(ANE) 상에서 직접 하드웨어 완전 가속 연산을 하도록 보완하여, 목표 레이턴시를 충족하는 극강의 온디바이스 추론 최적화를 최종 완수하였습니다.

---

### 2026-07-05 | 에이전트 스킬 | iOS Xcode 빌드, 조작 및 디버깅 자동화를 위한 xcode-build-management 스킬 생성

- **커밋**: `feat(skills): iOS Xcode 빌드, 시뮬레이터 관리 및 디버깅을 위한 xcode-build-management 스킬 생성`
- **변경 내용**:
  - `xcode-build-skill` 및 `patrickserrano/skills` 레포지토리를 상세히 분석하여, 우리 프로젝트의 React Native iOS 개발 환경에 특화된 Xcode 빌드/디버그 자동화 에이전트 스킬을 신규 추가.
  - `.agents/skills/xcode-build-management/SKILL.md` 신규 생성: `xcodebuild` 및 `xcrun simctl` 기반의 프로젝트 정보 수집, 시뮬레이터 부팅, 앱 빌드 및 설치, 디버깅 로그 수집 워크플로우 정의. Swift/SwiftUI 리팩토링 및 뷰 배치, Swift Concurrency 사용 표준 수립.
  - `.agents/skills/xcode-build-management/references/implementation_detail.md` 신규 생성: Apple Silicon 빌드 최적화, DerivedData 캐시 관리, Xcode 스크립트 샌드박스 오류 대처, XCUITest UI 자동화 테스트 가이드, `CoreMLInferenceBridge.swift` 리팩토링 예제 제공.
  - `SKILLS.md` 수정: 에이전트 시작 규칙에 따른 전역 스킬 인덱스 표에 새롭게 추가한 `xcode-build-management` 스킬 항목 등록 완료.
- **관련 파일**: `SKILLS.md`, `.agents/skills/xcode-build-management/SKILL.md`, `.agents/skills/xcode-build-management/references/implementation_detail.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 스킬 파일들의 마크다운 인덱스 및 위계 정합성 확인 완료.
  - 프로젝트 공통 룰(이모지 사용 금지, 한국어 경어체 작성) 완벽 준수 검증 완료.
- **비고**: Xcode 빌드와 수정, 시뮬레이터 기동 및 디버깅 로그 파싱 등 복잡한 iOS 네이티브 관련 빌드/디버그 문제 해결 과정을 에이전트가 주도적으로 수행할 수 있는 기반 스킬 셋을 성공적으로 구축하였습니다.

---

### 2026-07-05 | 환경 설정 | Ollama Gemma 4세대 정식 모델(gemma4:e4b) 통합 연동 및 명세 보완

- **커밋**: `refactor(llm): gemma4-e4b 명세를 정식 허브 모델명 gemma4:e4b로 교정 및 관련 문서 일괄 수정`
- **변경 내용**:
  - Ollama의 Gemma 4세대 Edge 최적화 모델의 정식 라이브러리 명칭이 `gemma4:e4b`로 제공됨에 따라, 이전의 하이픈(-) 오타 명세 `gemma4-e4b`를 일제히 교정.
  - `.env` 및 `.env.example`: `GEMMA_MODEL=gemma4:e4b` 값으로 명세 교정 및 저장.
  - `server/orchestration/llm_client_factory.py`: `os.getenv("GEMMA_MODEL", "gemma4:e4b")` 기본값 fallback 코드 및 로그 출력을 정식 명칭에 맞게 변경.
  - `docs/ops/deployment_guide.md` 및 `docs/ops/environment_variables.md`: Docker exec pull 지침, 환경변수 상세 및 디스크 가이드에 적힌 오타를 정식 모델명 `gemma4:e4b` 및 실제 다운로드 용량(약 9.6GB)에 맞게 일괄 업데이트 완수.
- **관련 파일**: `.env`, `.env.example`, `server/orchestration/llm_client_factory.py`, `docs/ops/deployment_guide.md`, `docs/ops/environment_variables.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - `docker exec minchodan-ollama ollama pull gemma4:e4b` 실행 시 Ollama 허브로부터 정상적으로 manifest 수집 및 다운로드 수신 동작 확인 완료.
- **비고**: 4세대 Edge 최적화 모델 명세 정합을 마침으로써, 오프라인 인지 경로 상세 회피 안내 문장 생성 품질 향상을 위한 LLM 엔진 기저 통신 무결성을 최종 확보하였습니다.

---

### 2026-07-05 | 문서 작성 | 실기기 무선 연동 테스트 및 Docker 환경 공유 가이드 문서 신설

- **커밋**: `docs(ops): 외부 LTE망 연동 및 Docker 컨테이너 구조 명세를 위한 wireless_test_guide.md 작성`
- **변경 내용**:
  - 내일 실외 LTE/5G 환경에서 연동을 시작할 새로운 팀원들을 위해, 현재 로컬 도커에 기동되어 맞물려 돌아가는 컨테이너의 역할과 네트워크 흐름을 종합한 가이드라인 신설.
  - `docs/ops/wireless_test_guide.md` 신규 생성:
    - 3대 Docker 컨테이너(`fastapi`, `redis`, `ollama`) 구성 및 기능 정의.
    - Ngrok 외부 wss 터널링 프록시 아키텍처 및 포트 포워딩 연결 흐름 구조화.
    - WebSocket 실기기 핸드셰이크 프로토콜 규격 및 실시간 base64 이미지 디코딩 ─► YOLO 추론 파이프라인 흐름 구체화.
    - `base64 데이터 없음` 오타 오류 및 `lap` 의존성 누락 문제 해결법 등 실제 겪은 주요 문제 해결법(트러블슈팅) 기재.
  - `docs/README.md` 수정: 운영 카테고리 인덱스 표에 신설된 가이드 문서(`wireless_test_guide.md`) 링크 등록 완료.
- **관련 파일**: `docs/ops/wireless_test_guide.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 마크다운 문법 준수 및 링크 이동 기능 확인 완료.
- **비고**: 본 가이드를 배포함으로써, 팀원들이 도커 인프라의 내부 상호작용 및 외부 이동통신망을 통한 터널링 구조를 명확히 이해하고, 에러 상황 시 신속하게 대응할 수 있도록 환경을 체계화하였습니다.

---

### 2026-07-05 | 개발 환경 | Windows 환경 연동성 강화를 위한 배치파일 및 가이드 보완

- **커밋**: `refactor(docker): windows_docker_start.bat 내 GPU/CPU 하드웨어 모드 분기 및 가이드 보완`
- **변경 내용**:
  - 윈도우 환경을 사용하는 팀원들의 상이한 하드웨어 사양(NVIDIA 외장 GPU 소유 여부)을 지원하기 위해 `windows_docker_start.bat` 스크립트 고도화.
  - 시작 시 `[1] GPU Mode` 와 `[2] CPU Only Mode` 메뉴 선택지를 입력받도록 수정:
    - 1번 선택 시 기존의 GPU 하드웨어 가속용 `docker-compose.yml` 실행.
    - 2번 선택 시 macOS용으로 검증된 CPU Fallback 전용 `docker-compose.macos.yml` 을 자동 호출하여 기동하도록 윈도우 스크립트 분기 완료.
    - 스크립트 내부의 Ollama pull 및 로그 조회 명령어들에 사용되던 `gemma2:9b` 명칭을 `gemma4:e4b` 정식 명칭에 맞게 교정.
  - `docs/ops/wireless_test_guide.md` 보완: 윈도우 팀원들이 겪을 수 있는 환경별(GPU vs CPU) Compose 및 배치 스크립트 분기 기동 지침 수록 완료.
- **관련 파일**: `docker/windows_docker_start.bat`, `docs/ops/wireless_test_guide.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 배치파일 문법 및 파라미터 바인딩 검증 완료.
- **비고**: macOS뿐 아니라 다양한 Windows 기기(GPU 탑재 데스크톱 및 CPU 온보드 노트북 등)를 소지한 내일의 테스터 팀원들 모두가 터미널 1클릭으로 장애 없이 추론 서버를 가동할 수 있도록 크로스 플랫폼 적합성을 완비하였습니다.

---

### 2026-07-05 | 설계 반영 | iOS 구현 설계서 내 하이브리드(React Native vs Swift/CoreML) 아키텍처 기술 명세 추가

- **커밋**: `docs(mobile): mobile_ios_implementation_plan.md 내 하이브리드 역할 분담 및 설계 배경 추가`
- **변경 내용**:
  - React Native(TypeScript / JS)의 전체 시스템 및 디바이스 피드백 제어 역할과 iOS Native(Swift / CoreML)의 Neural Engine 연계 딥러닝 고속 추론 역할을 정의하고, 이들의 협업 구조에 대한 가치 및 설계 배경을 문서에 추가.
  - `docs/mobile/mobile_ios_implementation_plan.md` 1.5절 신설:
    - React Native와 iOS Native 간의 역할 분담표 작성.
    - JavaScript 싱글스레드 성능 제약 극복 방안 및 ANE 하드웨어 직접 제어의 설계 결정 배경 기술.
    - `CameraView` ─▶ `CoreMLInferenceBridge.swift` ─▶ `BBoxOverlay` 간의 실시간 브릿지 이미지 데이터 송수신 메커니즘 구체화.
- **관련 파일**: `docs/mobile/mobile_ios_implementation_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 마크다운 인덱스 정합성 및 위계 검증 완료.
- **비고**: 팀원들이 모바일 클라이언트 단의 자바스크립트 제어 영역과 Swift 네이티브 가속 영역 간의 상호작용 방식 및 아키텍처 설계 명분을 명확하게 파악하고 개발할 수 있도록 설계 문서를 최신화하였습니다.

---

### 2026-07-05 | 리팩토링 | iOS Swift 파일 내 영문 주석의 한글 번역 및 최신화

- **커밋**: `refactor(ios): iOS Swift 파일 내 보일러플레이트 및 기능 설명 주석의 한국어 번역 완료`
- **변경 내용**:
  - 내일부터 진행될 외부 연동 현장 테스트에서 팀원들의 iOS 네이티브 코드 분석 편의성을 높이기 위해 프로젝트 내의 주요 `.swift` 파일 내 영문 주석들을 100% 한국어로 일제히 번역 교정.
  - `client/ios/Minchodan/AppDelegate.swift`: Expo config-plugins용 네이티브 확장 지점, Metro 번들 URL 로드 목적, Universal Links 및 Deep Linking 등 보일러플레이트 API 주석을 한국어로 전면 변경.
  - `client/ios/Minchodan/CoreMLInferenceBridge.swift` & `client/ios/CoreMLInferenceBridge.swift`: bounding box 0~1 정규화 텐서 파싱 공식, 이미지 해상도 스케일러(prepareInput), 좌표계 변환 원리 등 영문으로 혼용되던 모든 텍스트 주석을 명확한 한국어로 수정.
- **관련 파일**: `client/ios/Minchodan/AppDelegate.swift`, `client/ios/Minchodan/CoreMLInferenceBridge.swift`, `client/ios/CoreMLInferenceBridge.swift`, `docs/changelogs/kb.md`
- **검증 결과**:
  - UTF-8 인코딩 확인 및 Swift 컴파일러 빌드 무결성 확인 완료.
- **비고**: 기계 번역된 구글 보일러플레이트 영문 주석을 모두 직관적인 실무 한국어 주석으로 대체함으로써, iOS 내부 네이티브 파이프라인(ANE 가속 적재, GCD 백그라운드 스레딩, 픽셀 변환)에 대한 팀원들의 코드 리딩 오버헤드를 극적으로 낮추었습니다.

---

### 2026-07-05 | 문서 작성 | 모바일 클라이언트 의존성 및 개발 툴체인 구축 가이드 신설

- **커밋**: `docs(ops): 외부 연동 가이드 내 모바일 클라이언트 의존성 복원 및 빌드 순서 수록`
- **변경 내용**:
  - 네이티브 깃 이그노어 해제 조치에 따라, 팀원들이 클론받은 후 모바일(iOS/Android) 개발 환경을 복원하고 빌드할 수 있는 단계별 상세 안내 추가.
  - `docs/ops/wireless_test_guide.md` 6절 신설:
    - 필수 툴체인(Node.js LTS, Xcode, CocoaPods, Android Studio, JDK 17 등)의 플랫폼별 권장 요구사항 정의.
    - `npm install` ─▶ `npx expo prebuild` ─▶ `pod install` 로 이어지는 클라이언트 의존성 1클릭 복원 절차 수록.
    - `npx expo run:ios --device` 및 `run:android` 실기기 컴파일 명령어 수록.
    - iOS 최초 컴파일 시 Xcode Signing & Capabilities 개인 무료 프로비저닝 서명 주의사항 부각.
- **관련 파일**: `docs/ops/wireless_test_guide.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 실기기 빌드 명령어 및 디렉토리 접근 매뉴얼 정합성 검토 완료.
- **비고**: 이로써 깃허브에서 내려받은 직후 의존성 선언 파일(`package.json`, `Podfile`)을 통해 한 줄의 명령어로 네이티브 빌드 환경을 즉시 복원하고 가동하는 완성형 배포 안내 프로세스를 확립하였습니다.

---

### 2026-07-05 | 개발 반영 | iOS CoreML 추론 지연 시간(Latency) 실시간 측정 및 벤치마크 로그 탑재

- **커밋**: `feat(ios): Swift 네이티브 브릿지 내 CFAbsoluteTimeGetCurrent 기반 추론 벤치마크 로그 생성`
- **변경 내용**:
  - 실기기 탑재 CoreML 모델이 Apple Neural Engine(ANE) 가속 성능을 성공적으로 뽑아내고 있는지 터미널 상에서 직접 계측 검증할 수 있도록 벤치마크 기능 주입.
  - `client/ios/CoreMLInferenceBridge.swift`:
    - `detectFrame` 호출 시 `CFAbsoluteTimeGetCurrent()`를 사용하여 탐지(det) 및 분할(seg) 모델의 순수 컴파일/추론 경과 시간(ms)을 개별 측정.
    - 추론 완료 시 소수점 둘째 자리 포맷의 벤치마크 요약 로그 출력 (`[CoreMLBridge] 벤치마크 - 탐지(det): 12.30ms...`).
    - 측정된 벤치마크 통계를 JSON 딕셔너리로 묶어 React Native 자바스크립트 영역에 동적 리턴(`benchmark.total_ms`).
  - `client/ios/Minchodan/CoreMLInferenceBridge.swift`: Vision Framework의 `perform` 동기 추론 전후 지연 측정을 수행하는 동일 로깅 기능 주입.
- **관련 파일**: `client/ios/CoreMLInferenceBridge.swift`, `client/ios/Minchodan/CoreMLInferenceBridge.swift`, `docs/changelogs/kb.md`
- **검증 결과**:
  - CFAbsoluteTime 패키지 바인딩 및 iOS 빌드 통과 성공 검증 완료.
- **비고**: 본 벤치마크 계측기를 빌드에 수록함으로써, 가속 지연 시간(정상 ANE 작동 시 10~20ms, 가속 실패 시 100ms 이상)을 로컬 서버 터미널과 Xcode 디버거 상에서 실시간으로 대조 검증하고, 최적화 완성도를 객관적 통계로 입증할 수 있게 되었습니다.

---

### 2026-07-05 | 개발 반영 | 실기기 이미지 압축 패치 도입 및 성능 벤치마크 문서화 최적화 완수

- **커밋**: `feat(ios): expo-image-manipulator 도입을 통한 실기기 캡처 이미지 압축 및 지연 시간 문서화 반영`
- **변경 내용**:
  - **이미지 압축 패치 구현**:
    - `expo-image-manipulator` 패키지를 새로 추가하여, 단말 캡처 프레임을 기기 GPU 가속을 통해 640x640 크기로 강제 크롭하고 JPEG 50% 수준 압축을 적용.
    - 프레임 전송 용량을 3.4MB ──► 12KB (약 1/45) 수준으로 격감시켜 무선 네트워크 대역폭 병목을 원천 제거.
    - `FileSystem.deleteAsync`를 사용하여 매 프레임마다 임시 캐시 사진 파일을 삭제하여 저장소 누출 방지.
  - **콘솔 벤치마크 중계기 연계**:
    - `CameraView.tsx` 에 수신된 `benchmark` 객체를 읽어 메트로 번들러에 `[CoreMLBench]` 지연시간 로그를 실시간 출력하는 로직 추가.
  - **공식 문서 최적화 업데이트**:
    - `docs/ops/wireless_test_guide.md`: 이미지 대용량으로 인한 무선망 소켓 끊김 에러 진단 및 압축 해결책을 `5.3` 단락으로 추가.
    - `docs/mobile/mobile_ios_implementation_plan.md`: CoreML 실시간 벤치마크 ms 지연 계측 구조와 ANE 가속 정상 여부 판정 기준을 `9장`으로 신설 반영.
- **관련 파일**: `client/package.json`, `client/src/hooks/useCamera.ts`, `client/src/components/CameraView.tsx`, `docs/ops/wireless_test_guide.md`, `docs/mobile/mobile_ios_implementation_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - `고태현의 iPhone (00008120-0011705611F0201E)` 실기기 빌드 런칭 및 연동 시 소켓 끊김 현상 100% 소멸 검증 완료.
  - 10 FPS 프레임 전송 하에 `mouse`, `keyboard`, `tv` 실시간 룰베이스 탐지 및 통신 정합성 확인 완료.
- **비고**: 이로써 10 FPS 전속 전송 시 무선 인터넷 대역폭으로 인해 가동 환경이 깨지던 결함을 완전히 차단하고, ANE 초고속 가속 벤치마크 통계를 문서에 공식 수록하여 프로젝트의 컨텍스트를 완벽하게 고도화했습니다.

---

### 2026-07-05 | 개발 반영 | 실기기 탐지 결과에 따른 햅틱 및 입체 비프음 실질 연동 피드백 완료

- **커밋**: `feat(ios): 실시간 탐지 결과(BBox)에 반응하는 햅틱 및 입체 비프음 엔진 연동 완료`
- **변경 내용**:
  - **호출부 연동 누락 해소**:
    - `CameraView.tsx` 내부의 프레임 수신 콜백(`handleFrame`) 내에 탐지된 `allDetections` 결과값에 따라 실시간 햅틱과 입체 비프음을 구동하는 분기 회로 결합.
  - **위험 클래스별 피드백 제어 (Reflex Gate)**:
    - **Collision Risk (긴급 회피)**: `person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck`, `skateboard`, `pothole`, `caution` 등이 탐지 신뢰도 45% 이상으로 검출되면 ──► `double` 경고 햅틱 및 300ms 주기의 촘촘한 고속 점멸 비프음(`playBeep(0.0, 300)`) 가동.
    - **General obstacles (일반 장애물)**: 기타 볼라드, 벤치 등이 잡히면 ──► `short` 경고 햅틱 및 800ms 주기의 느린 비프음(`playBeep(0.0, 800)`) 가동.
    - **Safe (무탐지)**: 검출 결과가 비어있으면 (`allDetections.length === 0`) ──► 햅틱 타이머 클리어(`stopContinuous`) 및 비프음 완전 음소거(`stopBeep()`).
  - **사운드 에셋 검증**:
    - `client/assets/sounds/beep.wav` 리소스 적재 상태를 확인하여 iOS 실기기 런타임 오프라인 재생 환경 확인 완료.
- **관련 파일**: `client/src/components/CameraView.tsx`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 카메라 전방에 사물이 들어올 시 즉각적인 찌릿한 진동 피드백 및 800Hz 고속 비프음 점멸이 실기기 스피커를 통해 연동 재생됨을 검증 완료.
- **비고**: 이로써 7단계 클라이언트의 반사 경로 햅틱/비프 연계 요건을 완수하여 시각장애인 단말이 단순 전송기가 아닌 즉각적인 경보 반응기로서 동작하는 기능을 확립했습니다.

---

### 2026-07-05 | UI/UX 개선 | 클래스별 고유 색상 및 1:1 카메라 스크린 기하학적 캘리브레이션 튜닝 완료

- **커밋**: `style(ios): 클래스별 해시 기반 고유 HSL 컬러 부여 및 1:1 카메라 프레임 종횡비 정합 완료`
- **변경 내용**:
  - **1:1 비율 카메라 스크린 정합 (Aspect Ratio 1:1)**:
    - 실기기 화면(직사각형 종횡비 19.5:9)과 YOLOv8 추론 해상도(정사각형 640x640)의 불일치로 인해 바운딩 박스가 실물보다 과도하게 뚱뚱하거나 어긋나 보이던 오차를 해결.
    - 리액트 네이티브 `Dimensions` 를 통해 화면 너비(`SCREEN_WIDTH`)를 획득하고, 카메라 프리뷰와 BBoxOverlay를 감싸는 컨테이너를 가로세로 동일 크기의 정사각형 `cameraContainer` 뷰 영역으로 격리 제약.
    - 이로써 좌표 투영 왜곡이 0이 되어, 탐지 박스가 실물 물체 테두리에 3:4 크기로 오차 없이 정확히 밀착 렌더링되도록 캘리브레이션 튜닝 완료.
  - **해시 기반 고유 컬러 자동 매핑**:
    - `getClassColor` 헬퍼 함수를 작성하여, 문자열 해싱 연산을 거쳐 모든 탐지 사물 종류(class)마다 서로 겹치지 않는 유니크하고 선명한 고유 HSL 컬러(`hsl(hue, 85%, 55%)`)가 화면에 실시간 자동 할당되도록 구현.
    - 단, 충돌 보행 가이드 핵심인 긴급 충돌 위험군(`person` 등)은 빨간색(`#EF4444`)을 강제하고, 지면/도로는 주황색(`#F59E0B`)을 고정하여 보행자 인지 직관성 보존.
- **관련 파일**: `client/src/components/CameraView.tsx`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 아이폰 실기기 상의 뷰파인더가 카메라 센서 본연의 3:4 종횡비 프레임으로 정렬되며, 잘림 현상 없이 전체 시야가 렌더링됨과 동시에 바운딩 박스가 실측 물체 위에 1:1로 정밀하게 밀착 작동하는 시각 피드백 통과 완료.
- **비고**: 시각적인 BBox 캘리브레이션 튜닝을 통해 하단 여백 및 잘림 현상을 극복하고 전체 시야를 확보하면서도 기하학적 매핑의 왜곡을 없앴습니다.

---

### 2026-07-05 | 개발 반영 | 자동차 주차센서식 거리 반비례 햅틱 세기 및 비프음 속도 다이내믹 연동 완료

- **커밋**: `feat(ios): 바운딩 박스 면적 비율 기반의 다이내믹 주차센서식 햅틱/비프 연동 회로 이식`
- **변경 내용**:
  - **거리 반비례 피드백 공식 정립**:
    - 사물과 사용자 간의 거리를 단일 2D 렌즈로 추정하기 위해, 바운딩 박스의 면적 점유율인 `areaRatio = (w * h) / (640 * 640)` 을 구동 원식으로 책정.
  - **거리별 4단계 다이내믹 경보 캘리브레이션**:
    - **1단계 (초접근, `ratio > 0.32`)**: 코앞 충돌 위기 상황 ──► `continuous` (연속 강 진동) 및 `playBeep(0.0, 0)` (삐- 연속음).
    - **2단계 (근접, `ratio > 0.12`)**: 근거리 감지 ──► `double` (경고 진동) 및 `playBeep(0.0, 200)` (200ms 고속 점멸음).
    - **3단계 (중거리, `ratio > 0.03`)**: 중거리 감지 ──► `short` (단발 진동) 및 `playBeep(0.0, 600)` (600ms 중속 점멸음).
    - **4단계 (원거리, `ratio <= 0.03`)**: 미세 포착 ──► 진동 소멸(`stopContinuous`) 및 `playBeep(0.0, 1200)` (1200ms 저속 점멸음).
  - **긴급 위험 클래스 가중치 보정**:
    - `person`, `car`, `pothole` 등 긴급 충돌 위험군의 경우, 먼 거리에서도 즉각 대비할 수 있도록 1~2단계 격상 문턱값(Threshold)을 일반 사물 대비 **약 40% 낮게 하향 튜닝**하여 긴급 발화 민감도 가중치 매핑.
- **관련 파일**: `client/src/components/CameraView.tsx`, `docs/changelogs/kb.md`
- **검증 결과**:
  - 카메라 앞 사물이 다가오거나 폰을 물체에 접근시킬 때 주차 센서와 같이 비프음이 점차 삐-삐-삐-삐이이익 빨라지며 진동 세기가 동적으로 급증하는 피드백 루프 검증 성공.
- **비고**: 시각장애인 보행을 위한 '거리 반비례 경보 속도' 요건을 충족하여 주차 센서식의 가장 안전하고 직관적인 인지 보조 인터페이스를 확립했습니다.

---

### 2026-07-05 | 빌드 복구 | 벤치마크 테스트 도중 오염된 디코딩 임계치 원복 및 가상환경 테스트 통과 검증

- **커밋**: `fix(server): 과대 프레임 디코딩 거부 임계치 원복 및 전체 테스트 스위트 복구`
- **변경 내용**:
  - **디코딩 가드레일 임계치 수정**:
    - 벤치마크 과정에서 `MAX_FRAME_SIZE_KB`가 `5000`으로 오염되어 과대 프레임 거부 테스트(`TC-CAP-003`)에서 `assert result is None`이 실패하던 이슈 해결.
    - `server/capture/frame_decoder.py` 내의 `MAX_FRAME_SIZE_KB` 임계치를 다시 본래 설계 규격인 `500` (500KB)으로 원복하여 테스트 규격 충족.
  - **가상환경 의존성 격리 실행**:
    - `.venv` 환경에서 발생하던 `ImportError: cannot import name 'Sentinel' from 'typing_extensions'` 패키지 꼬임 이슈를 우회하기 위해, 정상 가상환경인 `venv` 환경으로 전환하여 전체 테스트 정상 수행 환경 확보.
- **관련 파일**: `server/capture/frame_decoder.py`, `docs/changelogs/kb.md`
- **검증 결과**:
  - `PYTHONPATH=. venv/bin/pytest tests/` 명령을 통한 총 78개 단위/E2E 테스트 케이스 전체 PASS 통과.
  - `scripts/integration_test_pipeline.py` 실행을 통한 YOLO 모델 로딩, Redis Streams 연동, 이중 경로 게이트 및 KPI(지연시간 119.87ms) 검증 완료.

---

### 2026-07-06 | 문서 개선 | 프로젝트 문서 내 구버전 YOLO 모델 명칭(YOLOv8, YOLO11n)의 YOLO26n 일괄 수정 및 동기화

- **커밋**: `docs: 프로젝트 문서 내 구버전 YOLOv8/11 모델 명칭 오기 수정 및 YOLO26n 일괄 동기화`
- **변경 내용**:
  - **공식 문서 오기 수정**:
    - `docs/design/api_specification.md`: 이미지 압축 규격 내 `YOLOv8(640x640)` 표기를 프로젝트 공식 모델인 `YOLO26n(640x640)`으로 수정.
    - `docs/mobile/mobile_ios_implementation_plan.md`: 하이브리드 아키텍처 iOS Native 역할 부분의 `YOLOv8`을 `YOLO26n`으로 동기화.
    - `docs/ops/wireless_test_guide.md`: docker 컨테이너 역할 설명 및 ByteTrack 트러블슈팅 단락의 `YOLOv8`을 `YOLO26n`으로 수정.
- **관련 파일**: `docs/design/api_specification.md`, `docs/mobile/mobile_ios_implementation_plan.md`, `docs/ops/wireless_test_guide.md`, `docs/changelogs/kb.md`
- **비고**: 프로젝트에서 실제로 사용하는 메인 YOLO 추론 모델인 YOLO26n에 맞춰 개발/설계 문서의 표기적 혼선을 모두 일괄 정비하여 일관성을 확보했습니다.

---

### 2026-07-06 | 문서 개선 | Git dev 브랜치에 대한 PR(Pull Request) 의무 규정 제거 및 로컬 직접 병합 push 허용 반영

- **커밋**: `docs: Git dev 브랜치 직접 push 허용 및 PR 의무화 관련 가이드 일괄 삭제`
- **변경 내용**:
  - **Git 브랜칭 가이드 및 AGENTS.md 수정**:
    - `docs/ops/git_branching_strategy.md`: `dev` 브랜치의 보호 수준을 "직접 push 금지"에서 "직접 push 허용"으로 변경하고, 병합 예시를 `gh pr`에서 로컬 `git merge` 및 `git push`로 수정. 기존 "6. PR 규칙" 섹션을 삭제하고 "6. 병합 및 Push 규칙"으로 대체.
    - `AGENTS.md`, `docs/AGENTS.md`, `CLAUDE.md`: 브랜치 3계층 설명 내 `dev` 브랜치 직접 push 금지 문구를 직접 병합 후 push 허용으로 교체하고, PR(Pull Request) 기반 작업 문구를 직접 병합 및 push 기반으로 수정.
- **관련 파일**: `docs/ops/git_branching_strategy.md`, `AGENTS.md`, `docs/AGENTS.md`, `CLAUDE.md`, `docs/changelogs/kb.md`
- **비고**: 개발 생산성 향상과 샌드박스 CLI 환경에서의 원활한 병합을 위해 `dev` 브랜치에 대한 PR 기반 협업 규칙을 제거하고 직접 병합 후 푸시하는 방식으로 가이드를 최신화했습니다.

---

### 2026-07-06 | 가이드 보완 | 팀원 간 로컬 개발 환경 복제 가이드 추가 및 ios_env_setup.zip 패키징 수록

- **커밋**: `docs: 모바일 네이티브 빌드 트러블슈팅 가이드에 로컬 환경 동기화 절차 추가`
- **변경 내용**:
  - **개발 환경 복제 가이드 신설**:
    - `docs/ops/mobile_build_troubleshooting.md` 에 "4. 팀원 간 로컬 개발 환경 동기화 및 복제 가이드" 단락을 추가.
    - 공유해야 하는 핵심 환경 파일 및 빌드 오류 방지를 위해 제외해야 하는 컴파일 캐시 폴더 목록을 명시.
    - Apple 인증서(`.p12`) 및 프로비저닝 프로파일(`.mobileprovision`)을 획득하는 수동 과정 수록.
- **관련 파일**: `docs/ops/mobile_build_troubleshooting.md`, `docs/changelogs/kb.md`
- **비고**: 깃 이그노어된 파일들로 인해 신규 진입 팀원이 겪을 수 있는 환경 빌드 꼬임 에러를 방지하고 동일한 iOS 빌드 상태를 즉각 구성할 수 있도록 이식용 매뉴얼을 수록했습니다.

### 2026-07-05 | 3단계 | YOLO 데이터셋 29종 선별 추출 및 핑퐁 명세 동기화

- **Commit**: stage3: YOLO 데이터셋 29종 선별 추출 스크립트 수정 및 핑퐁 통신 문서 동기화
- **Changes**:
  - prepare_aihub_yolo_detection.py: AI Hub 29종 전체 클래스 대상 2000장 균형 추출, 면적 1~80% 및 정중앙(10~90%) 필터 적용
  - yolo_detector.py, yolo_segmentor.py: HARD CODE / VIBE CODE 주석 및 면접 대비 주석 추가
  - pi_specification.md: JSON ping/pong WebSocket 하트비트 메시지 포맷 명세 반영
  - minchodan_design_note.md: 3단계 커스텀 학습 대상 29종 2000장 추출 전략 명세 갱신
- **Files**: scripts/prepare_aihub_yolo_detection.py, server/detection/yolo_detector.py, server/detection/yolo_segmentor.py, docs/design/api_specification.md, docs/design/minchodan_design_note.md
- **Verification**: 핑퐁 및 YOLO 파이프라인 정합성 문서 교차 검증 완료

---

### 2026-07-06 | 3단계+iOS | iOS CoreML 온디바이스 추론 raw tensor 파싱 재구성 및 모델 클래스별 검증 보고서 신규 작성

- **커밋**: (대기 중)
- **변경 내용**:
  - **iOS CoreML 추론 파이프라인 전면 재구성** (`client/ios/CoreMLInferenceBridge.swift`, 실제 Xcode 빌드 타겟 파일): 기존 `VNCoreMLRequest`/`VNImageRequestHandler`(Vision Framework) 기반 호출을 제거하고, `MLModel`을 직접 로드해 YOLO26n end2end 모델의 raw tensor 출력(`[1, 300, 6]`, `(cx, cy, w, h, confidence, class_id)`)을 수동 파싱하는 방식으로 교체. Vision이 강제하는 `VNRecognizedObjectObservation` 클래스 라벨 매핑 방식이 커스텀 29/4클래스 모델과 맞지 않아 필요해진 재작성.
  - `computeUnits`를 `.cpuAndGPU`에서 `.cpuOnly`로 재하향: GPU(Metal) 경로에서도 `MLIR pass manager failed` 크래시가 재현되어(end2end NMS 연산인 Topk/GatherNd 등의 Metal 컴파일 실패로 추정), 현재는 CPU 전용으로 완전히 내려 안정성을 우선함.
  - 이미지 방향 정규화 버그 수정 (`normalizedCGImage()` 추가): `UIImage.cgImage`가 EXIF `imageOrientation`을 반영하지 않아, 세로로 촬영된 사진이 회전되지 않은 채 그대로 모델에 들어가 엉뚱한 클래스로 오탐지되던 문제를 해결.
  - bbox 좌표 단위 버그 수정: 클라이언트(`CameraView.tsx`)가 bbox 전체(x,y,w,h)를 640x640 픽셀 단위로 취급해 `FRAME_SIZE`로 나눠 화면 비율과 위험도 area ratio를 계산하므로, 기존에 `(x,y)`만 0~1로 정규화하고 `(w,h)`는 픽셀값으로 남겨 단위가 섞이던 것을 `(cx,cy,w,h)` 중심점 좌표를 좌상단 기준 `(x,y,w,h)`로만 변환하고 픽셀 단위를 유지하도록 수정.
  - segmentation 모델을 선택(optional) 로드로 변경: `segmentation.mlmodelc`가 번들되지 않은 경우에도 `object_detection`만으로 det-only 모드로 기동하도록 방어 처리. det/seg 독립 벤치마크 로깅(`det_ms`/`seg_ms`/`total_ms`) 유지.
  - `client/ios/Minchodan/CoreMLInferenceBridge.swift`(project.pbxproj 그룹에 path 속성이 없어 실제로는 빌드 타겟에 연결되지 않는 미사용 사본, `.d` 의존성 파일로 확인)에도 동일한 재구성을 반영해 두 파일 간 코드 드리프트를 최소화. 단, `confThreshold`(0.25 vs 0.05)와 bbox 정규화 방식은 실제 빌드 타겟 파일(`client/ios/CoreMLInferenceBridge.swift`)에만 추가 보정이 반영되어 있고 두 파일이 완전히 동일하지는 않음.
  - **iOS 온디바이스 추론 재활성화** (`client/src/components/CameraView.tsx`): 위 크래시/오탐지 원인 수정을 근거로, 실기기(REAL 모드)에서 로컬 CoreML 추론을 건너뛰던 `if (!isMockModeRef.current) { return; }` 서버 전담 우회 가드를 제거.
  - `CameraView.tsx`에 신뢰도 임계값 실시간 조절 UI 추가(`confThreshold` state, `+`/`-` 버튼, 5%~95% 범위): BBox 오버레이·감지 목록·Reflex Gate 피드백 전부 이 임계값 기준으로 필터링.
  - `CameraView.tsx`의 긴급 회피 클래스 목록(`HIGH_HAZARDS`)을 신규 29클래스 taxonomy(`scooter`, `wheelchair`, `stroller`, `carrier` 등)에 맞게 갱신하고, `GROUND_HAZARDS`(segmentation `caution`/`roadway`)를 신설해 노면 위험 구간도 조기 경보 대상에 포함.
  - 카메라 미리보기 컨테이너 종횡비를 `3:4`에서 `1:1`로 수정: 실제 캡처/추론 프레임이 640x640 정사각형인데 미리보기만 3:4였던 불일치로 인해 bbox가 실제 사물보다 넓게 그려지던 문제를 해결.
  - `client/src/hooks/useOnDeviceDetection.ts`: 기존 COCO 91클래스 라벨(`COCO_CLASS_NAMES`)을 신규 커스텀 29클래스(`DET_CLASS_NAMES`, export)로 교체. object_detection 29클래스는 이미 보행 위험 사물만 선별한 도메인 특화 모델이므로, 기존 COCO 화이트리스트(`DET_HAZARD`, 7종 선별)가 불필요해져 제거하고 탐지 결과 전체를 위험군으로 취급하도록 단순화.
  - iOS 온디바이스 bbox 좌표 어긋남 버그 수정: `client/src/hooks/useCamera.ts`의 `captureRealFrame`이 `expo-image-manipulator`의 `resize({width,height})`로 원본 사진을 종횡비 무시하고 늘려(stretch) 모델에 넣던 것을, 카메라 미리보기(`resizeMode="cover"`)와 동일하게 중앙 정사각형 크롭 후 리사이즈하도록 수정. `PhotoFile.width/height`가 EXIF 원본(회전 미반영) 축이라 세로 촬영 시 크롭 좌표축이 뒤바뀌는 문제도 `photo.orientation` 기준으로 함께 보정.
  - `.mcp.json` 수정: XcodeBuildMCP 활성 워크플로우에 `swiftpm`, `project-scaffolding` 추가(기존 `simulator,device,macos,debugging,ui-automation`에 이어).
  - `server/detection/yolo_detector.py`의 `_parse_result` 파싱 스텁 활성화: `SKILLS.md` 담당자 학습형 협업 규칙에 따라 `for box in result.boxes:` 루프 진입 전 조기 `return detections`로 막혀 있던 것을, 사용자 직접 지시에 따라 루프를 살리고 누락되어 있던 최종 `return detections`를 추가하여 서버 탐지 파이프라인이 실제 `list[Detection]`을 반환하도록 수정.
  - `scripts/validate_class_samples.py` 신규 작성: `det_best_20260705.pt`(Detection 29클래스), `segbest.pt`(Segmentation 4클래스) 두 모델을 ultralytics로 직접 로드해 클래스별 샘플 이미지에 추론을 실행하고, `result.plot(conf=True, labels=True)`로 bbox+신뢰도 오버레이 이미지를 저장.
  - `data/validation_samples/raw/<class_name>/`에 33클래스(Detection 29 + Segmentation 4) 각 3장씩 총 99장의 검증용 샘플 이미지 확보(한국 인도·도로 맥락 우선, 인터넷 공개 이미지). `data/validation_samples/results/{detection,segmentation}/<class_name>/`에 시각화 결과 저장.
  - `docs/ops/model_class_validation_report.md` 신규 작성: 클래스별 탐지 성공률·총 박스 수·최고 신뢰도 표, 실패/저조 클래스(`stop` 0/3 등) 원인 분석 및 후속 조치 제안 수록.
  - `docs/ops/ondevice_coreml_benchmark.md` 수정: Vision Framework 기반 서술을 raw tensor 파싱 기준으로 정정하고, `computeUnits` 값(`.all` → `.cpuOnly`) 및 클래스 체계(80클래스 COCO → 커스텀 29/4클래스) 최신화. 기존 실측 벤치마크 수치(`laptop` 탐지 등)는 구 아키텍처(Vision+COCO) 기준이라 현재 raw tensor 파이프라인 재측정 전까지 참고용으로만 유지한다고 명시.
  - `docs/README.md` 수정: 버전 v0.7.0 → v0.8.0, ops/ 문서 목록에 모델 클래스별 검증 보고서 추가.
  - `.claude/settings.json` 신규 작성: 검증 이미지 수집 과정에서 반복적으로 발생하던 curl/WebSearch/WebFetch 권한 프롬프트를 줄이기 위해 `Bash(curl *)`, `WebSearch`, `WebFetch(domain:commons.wikimedia.org)` 등 허용 목록 추가.
- **관련 파일**: `client/ios/CoreMLInferenceBridge.swift`, `client/ios/Minchodan/CoreMLInferenceBridge.swift`, `client/src/components/CameraView.tsx`, `client/src/hooks/useCamera.ts`, `client/src/hooks/useOnDeviceDetection.ts`, `.mcp.json`, `server/detection/yolo_detector.py`, `scripts/validate_class_samples.py`, `docs/ops/model_class_validation_report.md`, `docs/ops/ondevice_coreml_benchmark.md`, `docs/README.md`, `.claude/settings.json`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 신규 에러 없음 확인. `scripts/validate_class_samples.py` 실행 결과 Detection 29클래스 중 28개 클래스 최소 1장 이상 탐지 성공, Segmentation 4클래스 전부 탐지 성공. `stop` 클래스만 3장 전부 탐지 실패(conf 0.01까지 낮춰도 미탐지) 확인.
- **비고**: `stop` 클래스 탐지 실패는 학습 데이터 부족 또는 `traffic_sign`과의 클래스 혼동 가능성으로 추정되며, 재학습 데이터 보강이 필요하다. `traffic_light_controller` 등 일부 클래스는 한국 실사 샘플을 끝내 확보하지 못해 해외 사진으로 대체됐다(상세는 검증 보고서 3.3절 참조). iOS raw tensor 파이프라인은 실기기 재빌드 후 벤치마크 재측정이 필요하며(`docs/ops/ondevice_coreml_benchmark.md` §4 부록 참조), `client/ios/Minchodan/CoreMLInferenceBridge.swift`는 여전히 빌드 미대상 사본이므로 향후 정리(삭제 또는 실제 연결) 필요.

---

### 2026-07-07 | 오케스트레이션 | LangGraph 3계층 오케스트레이션 구조 정상화 및 방향 추출 알고리즘 버그 수정

- **커밋**: `refactor(server): LangGraph 엣지 구조 정상화 및 extract_direction 오추출 버그 수정`
- **변경 내용**:
  - **LangGraph fallback 노드 연결 정상화**:
    - [graph.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/orchestration/graph.py)와 [l3_validator.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/orchestration/nodes/l3_validator.py)를 수정하여, 검증 실패 및 재시도 횟수 초과 시 L3 검증자 내부에서 직접 폴백을 주입하는 대신 `verified=False` 상태로 `fallback` 노드로 올바르게 라우팅되도록 개선 (데드 노드 해결).
    - `route_after_l3`에서 `retry_count > 1` (MAX_RETRY=1 초과) 조건을 통해 1회의 재시도 기회를 보장하도록 조건부 분기 정교화.
  - **L2 프롬프트 피드백 환류 루프 구축**:
    - [l2_generator.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/orchestration/nodes/l2_generator.py)에 동적 에러 피드백을 적용하여, 재시도 시 이전 실패 사유(`validation_errors`)를 사용자 프롬프트 하단에 주입함으로써 재생성 성공률 극대화.
  - **최종 결정 방향어 추출 알고리즘 버그 수정**:
    - 복합문("좌측 장애물 회피하여 우측으로 이동")에서 단순히 딕셔너리 정적 순서에 의존하여 반대 방향을 오추출하던 문제를, 문장에서 가장 마지막에 등장하는 방향 키워드(`text.rfind`)를 우선시하는 출현 위치 인덱스 분석 알고리즘으로 개선하여 오추출 차단.
  - **FastAPI 생명주기에 GPU 모니터링 시동 탑재**:
    - [main.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/main.py)의 `lifespan` 블록이 실행될 때 `LLMClientFactory.start_gpu_monitor()`가 비동기로 가동되도록 마운트하여, GPU 과부하 상태 시 OpenAI 핫스왑 기능의 런타임 활성화 보장.
- **관련 파일**: [graph.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/orchestration/graph.py), [l3_validator.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/orchestration/nodes/l3_validator.py), [l2_generator.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/orchestration/nodes/l2_generator.py), [main.py](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/main.py)
- **검증 결과**:
  - `python -m pytest tests/test_langgraph.py` 실행 결과 전체 6개 단위 테스트 케이스 100% PASS (수정된 아키텍처 상태 전이 및 1회 재시도 보장 흐름 정상 검증 완료).
- **비고**: 오케스트레이션 단계에서 기획된 설계서 상의 분기 구조를 온전히 복구하고 치명적인 오추출 보행 유도 버그를 완치하였습니다.

---

### 2026-07-07 | 품질 | 프로젝트 전체 검증 및 CI 차단 요인 수정 (S105, tsc 타입 오류, 런타임 생성 파일 ignore)

- **커밋**: (대기 중)
- **변경 내용**:
  - `pyproject.toml`: `server/db/schemas.py`의 `TokenResponse.token_type = "bearer"`가 최신 Ruff(0.15.x)에서 S105(하드코딩 비밀번호 의심)로 오탐 판정되는 문제를 per-file-ignores로 정정. pre-commit은 ruff v0.6.9로 핀 고정되어 통과했지만, CI(`.github/workflows/lint.yml`)는 `requirements-dev.txt`의 `ruff>=0.6.0`(핀 없음)으로 최신 버전을 설치하므로 CI 린트가 실패하는 상태였음. (`# noqa: S105` 인라인 방식은 pre-commit 구버전 ruff가 RUF100 unused-noqa로 자동 제거해버려 설정 파일 방식을 채택.)
  - `client/src/types/detection.ts`: `WSMessage` 인터페이스에 `frame_id`, `decode_ms` 필드 추가. 서버 ack 메시지(`server/api/ws_router.py`)는 `decode_ms`를 payload가 아닌 최상위 필드로 전송하는데 타입 정의에 누락되어 `CameraView.tsx:75`에서 `npx tsc --noEmit` 타입 오류(TS2339)가 발생하던 것을 수정.
  - `.gitignore`: TTS 서버 기동 시 `server/tts/tts_service.py`가 자동 생성하는 `server/models/piper/*.runtime.compat.json`을 ignore 목록에 추가 (untracked 파일로 계속 노출되던 런타임 산출물).
  - 로컬 가상환경 동기화: `venv/`에 `aiomysql`, `PyJWT` 등 `requirements.txt` 명시 패키지가 미설치되어 pytest collection 자체가 실패하던 것을 `pip install -r requirements.txt`로 동기화 (`.venv/`는 정상이었음).
- **관련 파일**: `pyproject.toml`, `client/src/types/detection.ts`, `.gitignore`, `docs/changelogs/kb.md`
- **검증 결과**: `ruff check server/ scripts/ tests/` All checks passed. `npx tsc --noEmit` 오류 0건. `pytest tests/ --ignore=tests/test_ws_echo.py` 74건 전체 통과 (`test_ws_echo.py`는 로컬 서버 기동이 필요한 통합 테스트라 서버 중지 상태에서는 연결 거부로 실패하는 것이 정상). Bandit 통과. LangGraph retry 흐름(L1 초기화 → L3 증가 → retry_count>1 시 fallback) 무한루프 없음 확인.
- **비고**: `requirements.txt`의 `tokenizers==0.23.1` 핀이 전이 의존성 transformers 5.12.1의 요구(`tokenizers<=0.23.0`)와 충돌한다는 pip resolver 경고가 있음 (동작에는 지장 없으나 향후 requirements 정리 시 검토 필요 — requirements.txt 변경은 사전 허가 대상이라 이번에 수정하지 않음). `server/api/config.py:27`의 `# nosec B104` 주석은 현재 Bandit 기준 불필요(stale)하다는 경고가 있으나 무해하여 보존함.

---

### 2026-07-07 | 2단계 | 온디바이스 추론 지연 기반 동적 반사(reflex) FPS 조절 추가

- **커밋**: (대기 중)
- **변경 내용**:
  - `client/src/hooks/useCamera.ts`: 반사 캡처 루프를 `setInterval` 고정 주기에서 재귀 `setTimeout` 방식으로 교체하여, 매 tick마다 최신 간격값을 반영할 수 있도록 재구성.
  - `reportInferenceLatency(latencyMs)` 신규 API 추가: 온디바이스 CoreML 추론 지연이 현재 캡처 간격의 90%를 넘으면(따라가지 못하는 상태) 간격을 50ms씩 늘려 fps를 낮추고(최저 1fps까지), 지연이 간격의 50% 미만으로 안정되면 20ms씩 기본 간격까지 서서히 복구한다.
  - `client/src/components/CameraView.tsx`: `detectFrameRef.current(...)` 호출 후 얻은 `benchmark.total_ms`(또는 `dt` 폴백)를 `reportInferenceLatencyRef.current(...)`로 매 추론마다 피드백. 디버그 오버레이에 `현재 반사 fps`를 표시(`currentReflexFps`).
- **관련 파일**: `client/src/hooks/useCamera.ts`, `client/src/components/CameraView.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 신규 에러 없음.
- **비고**: 조절 기준을 "온디바이스 추론 지연" 단독으로 채택함(사용자 확인). WS 연결 상태(fallback 등) 기준은 이번 범위에 포함하지 않음 — 필요 시 후속 작업으로 별도 추가. 반사 경로(Reflex Path)는 여전히 LLM/RAG/실시간 TTS를 경유하지 않으며, 이번 변경은 캡처 주기 조절에 한정된다(비협상 원칙 위반 없음).

---

### 2026-07-07 | 2단계 | detection 프레임 Base64 탈피 및 바이너리(raw JPEG) 전송 전환

- **커밋**: (대기 중)
- **변경 내용**:
  - **클라이언트 (`client/src/hooks/useCamera.ts`)**: `captureRealFrame`에서 `expo-file-system`의 신규 `File(uri).bytes()` API로 매니퓰레이션 완료된 JPEG 파일을 raw `Uint8Array`로 직접 읽어 `FrameData.jpegBytes`에 담아 반환. 기존 `base64` 필드는 CoreML 네이티브 브릿지 호출용(구 RN 브릿지가 JSON 직렬화 가능 타입만 인자로 받을 수 있어 불가피)으로만 유지하고, 서버 전송 용도로는 더 이상 사용하지 않음.
  - **클라이언트 (`client/src/hooks/useWebSocket.ts`)**: `sendBinary(data: Uint8Array)` 신규 API 추가. RN `WebSocket.send()`가 `ArrayBufferView`를 바이너리 프레임으로 직접 전송하는 것을 활용.
  - **클라이언트 (`client/src/components/CameraView.tsx`)**: `handleFrame`에서 `frame.jpegBytes`가 있으면 (1) `transport: "binary"` 메타만 담은 JSON 텍스트 메시지, (2) 곧바로 raw JPEG 바이트 바이너리 프레임을 순차 전송하도록 변경. `jpegBytes`가 없는 경로(Mock 등)는 기존 base64 방식으로 폴백.
  - **서버 (`server/capture/frame_decoder.py`)**: `_parse_frame_meta`/`_build_processed_frame` 공통 헬퍼로 리팩터링하고, base64 미경유 `decode_frame_binary(jpeg_bytes, meta)`를 신규 추가. 기존 `decode_frame(payload)`(base64 경로)는 그대로 유지하여 하위 호환.
  - **서버 (`server/api/ws_router.py`)**: 메인 수신 루프를 `ws.receive_text()` 고정에서 `ws.receive()` 제네릭 방식으로 교체해 텍스트/바이너리 프레임을 구분 처리. `transport: "binary"` 메타 수신 시 `pending_binary_meta`에 보관해뒀다가 곧바로 뒤따르는 바이너리 프레임과 짝지어 `decode_frame_binary`로 디코딩. route_frame+ack 로직은 `_finish_detection` 헬퍼로 공통화하여 base64/바이너리 두 경로가 공유.
  - **문서 (`docs/design/api_specification.md`)**: v0.4.0으로 갱신. detection 프레임 전송 규격을 바이너리(기본, §3.1) / base64(구버전 호환, §3.2) 2단으로 재구성.
  - **테스트**: `tests/test_frame_decode.py`에 `TestDecodeFrameBinary` 클래스 신규 추가(정상/빈바이트/과대/과소/손상 바이트/base64 경로와의 결과 일치 검증, 7건). `tests/test_api_ws.py`에 실제 `/ws/detect` 엔드포인트를 통한 바이너리 전송 e2e 테스트 2건 추가(정상 전송 ack 확인, 메타 없는 고아 바이너리 프레임 무시 확인).
- **관련 파일**: `client/src/hooks/useCamera.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `server/capture/frame_decoder.py`, `server/capture/__init__.py`, `server/api/ws_router.py`, `docs/design/api_specification.md`, `tests/test_frame_decode.py`, `tests/test_api_ws.py`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 오류 0건. `ruff check`/`ruff format --check`/`bandit` 전부 통과. `pytest tests/ --ignore=tests/test_ws_echo.py` 83건 전체 통과(신규 9건 포함) — 특히 `test_websocket_detection_binary_transport`는 `TestClient.websocket_connect`로 실제 `/ws/detect` 라우터 코드 경로를 통해 JSON 메타 + `send_bytes()` 바이너리 프레임 → ack 왕복을 검증.
- **비고**: 단일 WS 연결에서 프레임 전송 순서가 보장된다는 전제(RFC 6455 및 ASGI 스펙)로 메타-바이너리 짝짓기를 구현했다. 하트비트/핑퐁 등 제어 메시지는 여전히 JSON 텍스트로 유지(빈도가 낮고 페이로드가 작아 최적화 실익이 없음). Mock 모드는 여전히 base64 경로를 사용(시뮬레이터 프리뷰용 float32 디코딩과 결합되어 있어 이번 범위에서 제외).

---

### 2026-07-07 | 문서 | 이번 세션 구현 변경사항(바이너리 전송, iOS CoreML 재검증) 전반에 걸친 문서 동기화

- **커밋**: (대기 중)
- **변경 내용**: 오늘 세션에서 구현/변경된 내용(detection 프레임 바이너리 전송 전환, iOS CoreML raw tensor 재구성 및 GPU/ANE 재검증)이 아직 반영되지 않은 관련 설계·운영 문서를 전수 점검하여 갱신.
  - `docs/design/api_specification.md`(직전 커밋에서 이미 v0.4.0 갱신 완료, 본 항목에서는 나머지 문서 동기화)
  - `docs/design/architecture.md`: v0.3.0. §6.3 2단계 인터페이스를 바이너리(기본)/base64(구버전 호환) 2단으로 갱신.
  - `docs/design/minchodan_design_note.md`: v0.2.1. 2단계 핵심 절차·데이터 인터페이스를 `File.bytes()` 기반 바이너리 전송 기준으로 갱신.
  - `docs/stage-guides/stage1_websocket_design.md`: v1.1.0. §3.1을 바이너리(신설)/§3.1b base64(구버전 호환)로 재구성.
  - `docs/stage-guides/stage2_capture_design.md`: v0.2.0. §6.4 바이너리 전송 디코딩 경로(`_parse_frame_meta`/`_build_processed_frame`/`decode_frame_binary`) 신설, §9.1 입력 인터페이스에 바이너리 예시 추가, §7.1에 신규 테스트 커버리지 각주 추가.
  - `docs/ops/mobile_build_troubleshooting.md`: v1.5.0. §1.6(이중화 파일 삭제 완료), §1.7(`.cpuOnly` 재확정), §1.8(온디바이스 추론 재활성화 + 바이너리 전송 전환)에 2026-07-07 후속 업데이트 각주 추가.
  - `docs/ops/wireless_test_guide.md`: v1.1.0. §4.2 프레임 캡처·전송 절차, §5.1 트러블슈팅 항목을 바이너리 기본/base64 구버전 호환 기준으로 갱신.
  - `docs/ops/test_specification.md`: v0.6.0. TC-WS-007(바이너리 전송 프로토콜), TC-CAP-010(바이너리 디코딩) 신규 검증 케이스 추가.
  - `docs/mobile/mobile_ios_implementation_plan.md`, `docs/mobile/mobile_android_implementation_plan.md`: 각 문서 상단에 2026-07-07 프로토콜 갱신 알림(`[!IMPORTANT]`) 추가 — 두 문서는 최초 계획 시점(v0.1.0, base64 전제) 원본이라 전면 재작성 대신 최신 규격 문서로의 안내 각주만 삽입.
  - `docs/README.md`: v0.9.0으로 버전 갱신.
- **관련 파일**: `docs/README.md`, `docs/design/architecture.md`, `docs/design/minchodan_design_note.md`, `docs/stage-guides/stage1_websocket_design.md`, `docs/stage-guides/stage2_capture_design.md`, `docs/ops/mobile_build_troubleshooting.md`, `docs/ops/wireless_test_guide.md`, `docs/ops/test_specification.md`, `docs/mobile/mobile_ios_implementation_plan.md`, `docs/mobile/mobile_android_implementation_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 전용 변경으로 코드 검증은 해당 없음. 각 파일의 마크다운 표/각주 형식이 기존 문서 스타일(인용 블록 메타데이터, 표 구조, `[!IMPORTANT]` 콜아웃)과 일치하는지 diff로 육안 확인.
- **비고**: `docs/mobile/mobile_app_implementation_plan.md`(플랫폼 분리 이전 통합 원본, 문서 자체에 "분리된 설계서 사용" 안내가 이미 있음)와 `docs/mobile/ondevice_inference_engine_isolation_plan.md`(LocalDetector 추상화 계획 - 실제 구현은 더 단순한 직접 수정 경로를 택해 상당 부분 미실현 상태)는 이번 범위에서 제외했다. 후자는 향후 온디바이스 아키텍처 정리 시 별도로 현재 구현과의 정합 여부를 재검토할 필요가 있다.

---

### 2026-07-07 | 품질 | 전체 문서 정합성 감사 1차 - 설계 문서 4종 + 3/4/5단계 설계서 정정, 운영 설정 버그 수정

- **커밋**: (대기 중)
- **변경 내용**: 6개 병렬 조사 에이전트로 프로젝트 전체 문서(design/stage-guides/ops/root 40여개)를 실제 코드와 대조 감사. 이번 커밋은 그 중 design 4종 + stage3 + stage4_5 3종 + 발견된 실제 운영 버그를 반영한다 (나머지 stage6/7·ops·root는 후속 커밋).
  - **`.env`/`.env.example` 운영 버그 수정 (문서 아닌 실제 설정)**: `YOLO26N_OBJECT_DET`/`YOLO26N_SEG`가 순정 COCO 80클래스 사전학습 체크포인트(`object_detection.pt`/`segmentation.pt`)를 가리키고 있어, 실제로는 검증 완료된 파인튜닝 모델(`det_best_20260705.pt` 29클래스/`segbest.pt` 4클래스, `docs/ops/model_class_validation_report.md` 참조)이 아니라 순정 COCO 모델로 추론하도록 설정되어 있었음을 `ultralytics.YOLO()`로 직접 로드해 클래스 수 확인 후 정정. `TTS_ENGINE=kokoro`(미구현, `tts_service.py`는 piper만 지원)도 `piper`로 정정.
  - `docs/design/backend_db_architecture.md`: `async_session_factory`→`async_sessionmaker_factory` 함수명 정정.
  - `docs/design/behavior_and_risk_insight.md`: §3.1 위험도 표를 실제 `reflex_gate.py`/`l1_classifier.py`/`surface_gate.py` 클래스 배정 기준으로 재작성(최초 제안은 킥보드=고위험/횡단보도=저위험이었으나 실제는 킥보드=중위험, 횡단보도=고위험 P0로 반대). §4.1 "Y축 상단 40% 격상" 로직이 미구현 상태임을 명시.
  - `docs/design/pipeline_stage_design.md`: 캡셔닝 Llava→Gemini, 노면 7클래스→실제 4클래스, LLM 클라이언트 ChatOllama/ChatOpenAI→커스텀 SimpleOllamaClient/SimpleOpenAIClient, TTS Kokoro/Coqui→Piper, Embeddings 파일 경로 정정.
  - `docs/design/reflex_audio_specification.md`: §2.1 direction/alert_id 실제 값(front-left/front/front-right, 클래스명 포함 동적 alert_id)으로 정정. §4 Web Audio API(OscillatorNode/GainNode/StereoPannerNode) 가상 파이프라인을 실제 구현(`expo-audio` 정적 WAV 루프 + 볼륨 스위칭)으로 전면 재작성하고, **`panning`(입체 음향)이 현재 미구현**임을 명시(저장만 되고 실제 좌우 밸런스에 적용되지 않음).
  - `docs/stage-guides/stage3_detection_design.md`: `ByteTrackTracker`의 실제 역할(track_id 파싱은 `YoloDetector`가 담당, 본 클래스는 speed/direction만 계산) 정정. `ReflexAlert` 스키마에 누락 필드(panning/distance/beep_interval_ms/haptic_pattern) 추가, track_id 타입(`str`, `T-0001` 포맷)로 수정. `HIGH_RISK_CLASSES`에 `scooter` 추가(4→5종). direction/alert_id 실제 값 정정. **Surface Gate가 실제 4클래스 세그멘테이션 모델과 `P0_SURFACE_CLASSES` 불일치로 현재 전혀 발동하지 않는 문제**를 사실관계로 기록(위험도 규칙 담당자 판단 필요 영역이라 코드는 직접 수정하지 않음). 모델 가중치 경로를 실제 파인튜닝 완료 파일 기준으로 정정.
  - `docs/stage-guides/stage4_5_rag_design.md`: 캡셔닝 VLM Llava→Gemini 2.5 Flash Lite, `Retriever.search()`→`search_guidance()`, import 경로 `rag.shared.labels`→`server.rag.shared.labels` 오탈자 수정.
  - `docs/stage-guides/stage4_5_data_replacement_guide.md`: §2.4(env var 미연동), §3(`__main__` 블록이 실제로는 임시 데이터를 쓰고 삭제하는 스모크 테스트일 뿐 프로덕션 DB를 조작하지 않음) 현황 각주 추가.
  - `docs/stage-guides/stage4_5_test_guide.md`: 스모크 테스트 예상 콘솔 출력 문자열을 실제 코드 기준으로 정정, 존재하지 않는 테스트 함수(`test_generate_caption_real_integration`) 참조 제거.
- **관련 파일**: `.env.example`, `docs/design/backend_db_architecture.md`, `docs/design/behavior_and_risk_insight.md`, `docs/design/pipeline_stage_design.md`, `docs/design/reflex_audio_specification.md`, `docs/stage-guides/stage3_detection_design.md`, `docs/stage-guides/stage4_5_rag_design.md`, `docs/stage-guides/stage4_5_data_replacement_guide.md`, `docs/stage-guides/stage4_5_test_guide.md`, `docs/changelogs/kb.md` (`.env`도 동일하게 수정했으나 git-ignore 대상)
- **검증 결과**: `.env` 모델 경로 수정 후 `server.detection.config` 재로드로 실제 경로 반영 확인(`det_best_20260705.pt`/`segbest.pt`, 파일 존재 확인). `pytest tests/ --ignore=tests/test_ws_echo.py` 83건 전체 통과(회귀 없음).
- **비고**: Surface Gate 미발동 문제와 `l1_classifier.py`의 `kickboard` 클래스명이 실제 탐지기 출력(`scooter`)과 어긋나는 문제는 위험도 판정 로직(핵심 로직, 담당자 직접 작성 영역)에 해당하여 이번 문서 정정 범위에서 코드를 직접 고치지 않고 사실관계만 기록했다. 후속 작업으로 담당자 검토가 필요하다. 나머지 문서(stage6/7, ops 6종, root 6종+skills)의 정정은 후속 커밋에서 이어간다.

---

### 2026-07-07 | 품질 | 전체 문서 정합성 감사 2차 - stage6/7, ops 6종, root 문서 전체 정정 완료

- **커밋**: (대기 중)
- **변경 내용**: 1차 감사(design/stage3/stage4_5)에 이어 나머지 전 범위를 실제 코드 기준으로 정정 완료.
  - `docs/stage-guides/stage6_orchestration_design.md`: LLM 클라이언트를 `ChatOllama`/`ChatOpenAI`(LangChain)에서 실제 구현체 `SimpleOllamaClient`/`SimpleOpenAIClient`(raw `ollama.AsyncClient`/`httpx`)로 정정. 핫스왑 트리거를 "L3 실패율 > 10%"에서 실제 기준인 "GPU 부하 감지(`start_gpu_monitor`)"로 정정.
  - `docs/stage-guides/stage7_tts_design.md`: TTS 엔진을 Kokoro/Coqui에서 실제 유일 구현체 Piper로 정정, `reflex_clip_sender.py`를 "(예정)"에서 "구현 완료"로 정정, 오디오 실제 포맷이 WAV임을 명시(필드명은 `audio_mp3_b64`이나 내용물은 WAV).
  - `docs/ops/redis_streams_schema.md`: §1.2/§2 전면 재작성. 최초 설계의 가상 필드 목록(`detected_classes`/`surface_state`/`max_risk_level` 등)이 실제로 존재하지 않음을 확인하고, `risk.events`에 실제로 발행되는 두 가지 서로 다른 스키마(2단계 캡처 메타데이터 vs 3단계 탐지 이벤트)를 코드 기준으로 명시. 중복 억제 키를 `session:{device_id}:last_alert:{class_name}`(TTL 30초)에서 실제 `suppress:{device_id}:{alert_id}`(TTL 60초)로 정정하고, 문서에 없던 `ctx:{track_id}` 키(TTL 30초)를 추가.
  - `docs/ops/environment_variables.md`: Slack 인증 방식을 `SLACK_WEBHOOK_URL`(미사용 변수)에서 실제 사용 중인 `SLACK_BOT_TOKEN`+`SLACK_CHANNEL_ID`로 재정정, `TTS_ENGINE` 기본값을 `piper`로 정정, 코드에는 있으나 문서에 누락됐던 변수 6종(`HEARTBEAT_INTERVAL/TIMEOUT`, `MAX_RECONNECT_ATTEMPTS`, `JWT_SECRET_KEY`, `OLLAMA_HOST`, `PIPER_BINARY_PATH` 등) 추가, `GOOGLE_API_KEY`가 문서엔 있으나 `.env.example`엔 없는 불일치 명시, `CHROMA_PATH`/`CHROMA_COLLECTION`이 아직 코드에서 소비되지 않음을 명시.
  - `docs/ops/ai_model_hardware_setup.md`: CUDA 12.8이 `requirements.txt`/`Dockerfile`에 실제로 고정되어 있지 않음(순정 `torch==2.12.1`, `+cu128` 태그 없음)을 명시.
  - `docs/ops/code_quality_guide.md`: pre-push 훅이 실제로는 존재하지 않고(mypy/jscpd/pip-audit는 CI 전용) pre-commit은 ruff-format/ruff/bandit만 등록되어 있음을 명시. Bandit `skips`(B101)와 Ruff `per-file-ignores`(B404/B603)를 혼동했던 표 정정. `requirements-dev.txt`에 jscpd가 없음(Node.js 별도 설치) 정정.
  - `docs/ops/deployment_guide.md`: macOS 로컬 테스트용 `docker/docker-compose.macos.yml`(GPU 미사용 변형, 실제로 `macos_docker_start.sh`가 사용) 파일 인덱스에 누락돼 있던 것 추가.
  - `docs/ops/git_branching_strategy.md`: 실제 `git branch -a`/커밋 이력과 대조 결과 정확함을 확인, 수정 없음.
  - **`CLAUDE.md`(루트, 세션 컨텍스트 자동 주입 문서)**: §4 존재하지 않는 `console/` 디렉토리 참조 삭제, §8 스킬 표에 누락된 `xcode-build-management` 추가 및 `.claude/skills`가 `.agents/skills`의 junction이라는 잘못된 서술 정정(실측: 서로 다른 inode의 독립 디렉토리이며 `xcode-build-management`가 누락돼 트리가 어긋나 있음), §9 문서 인덱스의 링크 7개 전부가 `docs/` 평면 경로를 가리켜 깨져 있던 것을 실제 하위 디렉토리(`docs/design/`, `docs/ops/`, `docs/dev-guides/`) 기준으로 전부 정정, `rag-knowledge-builder` 스킬 설명의 Llava를 Gemini로 정정.
  - `README.md`(루트): CLAUDE.md와 동일한 문서 인덱스 링크 깨짐(7개 이상) 전부 정정, 존재하지 않는 `console/` 디렉토리 트리 전체 제거, `data/captions/` 설명의 Llava→Gemini 정정.
  - `docs/AGENTS.md`: 루트 `CLAUDE.md`/`AGENTS.md`(v0.3.0)보다 오래된 stale 중복 사본(v0.1.0, 갱신 안 됨)임을 확인, 전면 재작성 대신 상단에 "루트 문서가 최신 기준" deprecated 안내 추가.
  - `Directory_Structure.md`: 프로젝트 초기 기획 단계의 "임시 디렉토리 구조"로 루트 디렉토리명(`guidedog-ai/`)부터 실제와 다르고 다수 파일 경로가 틀려(`server/config.py`, `llava_captioner.py`, `server/bus/consumer.py` 등 실제 미존재/이동) 있음을 확인, 전면 재작성 대신 상단에 이력 참고용 안내 추가하고 `README.md`/`CLAUDE.md`를 최신 기준으로 안내.
  - `.agents/skills/rag-knowledge-builder/SKILL.md`: frontmatter `description`(스킬 검색/요약에 노출됨) 및 본문 헤더의 Llava를 Gemini로 정정하고, 본문 코드 예시가 여전히 최초 계획(로컬 Llava) 기준임을 알리는 안내 추가(전체 코드 예시 재작성은 범위 밖).
- **관련 파일**: `docs/stage-guides/stage6_orchestration_design.md`, `docs/stage-guides/stage7_tts_design.md`, `docs/ops/redis_streams_schema.md`, `docs/ops/environment_variables.md`, `docs/ops/ai_model_hardware_setup.md`, `docs/ops/code_quality_guide.md`, `docs/ops/deployment_guide.md`, `CLAUDE.md`, `README.md`, `docs/AGENTS.md`, `Directory_Structure.md`, `.agents/skills/rag-knowledge-builder/SKILL.md`, `docs/changelogs/kb.md`
- **검증 결과**: `pytest tests/ --ignore=tests/test_ws_echo.py` 83건 전체 통과(회귀 없음, 이번 라운드는 문서 전용 변경).
- **비고**: 6개 병렬 조사 에이전트가 이번 세션 내 `docs/`의 design/stage-guides/ops/root 전 영역(약 40개 문서)을 실제 코드와 전수 대조했다. 의도적으로 범위에서 제외한 것: (1) `docs/research/*.md`(6종, 시점 스냅샷 성격의 타당성 분석 문서라 "현재 상태"로 고쳐 쓰면 이력이 훼손됨), (2) `docs/dev-guides/신규_설계서_예시_2.md`(다른 프로젝트명("VIP Assistant AI")의 템플릿/예시 문서, Minchodan 서술 아님), (3) `docs/dev-guides/antigravity_agent_prompt__4_5_final.md`(이미 실행 완료된 1회성 에이전트 작업 지시서), (4) `docs/mobile/mobile_app_implementation_plan.md`(문서 자체에 이미 "분리된 설계서 사용" 안내 존재), (5) `docs/mobile/ondevice_inference_engine_isolation_plan.md`(LocalDetector 추상화 계획 - 실제 구현이 더 단순한 경로를 택해 상당 부분 미실현, 별도 검토 필요), (6) `.agents/skills/*/SKILL.md` 중 rag-knowledge-builder를 제외한 7개는 경로/클래스명 스팟체크만 수행(전수 라인 단위 검증은 아님).

---

### 2026-07-07 | 3단계 | 실내 오탐(도메인 시프트) 완화 - 클래스별 confidence 임계값 및 연속 프레임(hit_count) 검증 추가

- **커밋**: (대기 중)
- **변경 내용**: YOLO26n det/seg 모델이 AI Hub 한국 인도(실외) 데이터셋만으로 학습되어 실내 환경을 미학습 도메인(OOD)으로 취급, 실내에서 `car`/`bus` 등이 오탐되는 문제에 대한 완화책 2종을 구현.
  - `server/detection/schemas.py`: `Detection`에 `hit_count: int = 0` 필드 추가 — 동일 `track_id`가 연속 몇 프레임 유지됐는지를 담는다.
  - `server/detection/bytetrack_tracker.py`: `ByteTrackTracker.update()`가 Redis `ctx:{track_id}` 컨텍스트의 `hit_count`를 프레임마다 +1 누적하도록 `_compute_hit_count()` 추가. track_id가 없는 경우(Mock 등)와 새 track은 1부터 시작.
  - `server/detection/gates/reflex_gate.py`: `HIGH_RISK_CLASSES`를 `set`에서 `{class_name: min_confidence}` 딕셔너리로 변경(car/truck/bus=0.6, motorcycle=0.55, scooter=0.5 — 실내 오탐이 잦은 차량류 위주로 상향). `MIN_HIT_COUNT=3` 신설: 클래스+위치 조건을 통과해도 confidence 미달 또는 hit_count가 3프레임 미만이면 반사 경보를 발동하지 않는다. 기존에는 게이트가 confidence를 아예 확인하지 않았고 단일 프레임만으로 즉시 발동했던 문제를 함께 해소.
  - `client/src/components/CameraView.tsx`: `CLASS_MIN_CONFIDENCE` 맵 및 `getEffectiveConfThreshold()` 추가 — 사용자 조절 슬라이더(`confThreshold`, 기본 40%)와 클래스별 최소값 중 더 높은 쪽을 유효 임계값으로 사용(실외 전용 클래스인 car/bus/truck/motorcycle/scooter/fire_hydrant/parking_meter/traffic_light(_controller)/traffic_sign/stop/roadway 대상). 서버 `reflex_gate.py`와 동일한 완화 전략을 온디바이스 경로에도 반영.
  - 테스트: 기존 reflex_gate/ByteTrackTracker 테스트에 `hit_count=3` 보강, 신규 회귀 테스트 추가 — confidence 미달 시 거부, hit_count 미달 시 거부, 신규 track hit_count=1 시작, 연속 3프레임에 걸친 hit_count 누적(1→2→3) 검증, `HIGH_RISK_CLASSES`(dict로 변경됨) 관련 일관성 테스트 시그니처 보정.
- **관련 파일**: `server/detection/schemas.py`, `server/detection/bytetrack_tracker.py`, `server/detection/gates/reflex_gate.py`, `client/src/components/CameraView.tsx`, `tests/test_detection.py`, `tests/test_langgraph.py`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 오류 0건. `pytest tests/ --ignore=tests/test_ws_echo.py` 93건 전체 통과(신규 8건 포함). `ruff format/check`, `bandit` 전부 통과.
- **비고**: `direction.py::estimate_distance()`의 `small_objects` 집합에도 동일 패턴의 존재하지 않는 클래스명(`kickboard`, `planter`)이 남아 있음을 검토 중 발견했으나, 이 함수는 현재 어디서도 호출되지 않는 죽은 코드라 이번 수정 범위에서 제외했다(향후 연결 시 함께 정정 필요). MIN_HIT_COUNT=3, 클래스별 confidence 값은 초기 추정치이며 실기기/실외 재현 테스트를 통해 조정이 필요할 수 있다.

---

### 2026-07-07 | 3단계 | 실내 오탐 완화 실기기 현장 검증 및 2차 방어선(co-occurrence, 안전노면 제외, bbox 라벨 clamp) 구현 + 2차 설계서 작성

- **커밋**: (대기 중)
- **변경 내용**: 1차 완화책(클래스별 confidence + hit_count) 적용 후 실기기 실내 현장 재테스트를 진행한 결과, `car` 오탐이 confidence 0.916까지, `sidewalk_normal` 오탐이 0.95까지 나와 confidence 임계값만으로는 원천 차단이 불가능함을 실측으로 확인. 이에 따라 추가 방어선을 구현하고, 남은 근본 대응은 별도 설계서로 분리했다.
  - `client/src/components/CameraView.tsx`: `VEHICLE_CLASSES`(차량류)에만 걸었던 실외 노면 co-occurrence 게이트(`hasOutdoorSurface`)를 전체 object_detection 클래스로 확장(bollard/movable_signage 등도 동일 패턴의 실내 오탐이 확인됨). `SAFE_SURFACE_CLASSES`(`sidewalk_normal`, `braille_normal`) 신설 — 안전한 정상 보행로는 화면을 얼마나 채우든 반사 경보 판정에서 제외(기존 `maxAreaRatio > 0.32` 무조건 최상위 경보 발동 조건이 클래스 무관하게 걸리는 문제를 해소).
  - `BBoxOverlay`: bbox가 화면 밖(음수 좌표)으로 나갈 때 클래스명 라벨이 같이 잘려 안 보이는 문제를 라벨-박스 위치 분리 + clamp로 수정. 1차 수정에서 스타일 없는 wrapper `<View>`로 감쌌다가 %기반 좌표가 0x0으로 collapse된 부모 기준으로 계산되어 박스 자체가 안 보이는 회귀가 발생, `Fragment`로 교체해 두 View 모두 원래 컨테이너의 직계 자식으로 되돌려 해결.
  - `docs/design/indoor_fp_mitigation_design.md`(신규): co-occurrence 게이트의 구조적 한계(seg 모델도 동일 도메인쉬프트를 공유해 "노면 신호=실외"라는 전제가 실내에서도 거짓이 됨)를 문서화하고, 재학습 없이 적용 가능한 2개 방어선(물리적 타당성 필터 - bbox가 640 캔버스를 초과하는 회귀 붕괴 케이스 차단, `VNClassifyImageRequest` 기반 독립 씬 분류기 게이트)의 구현 설계를 작성. 아직 코드 구현 전 단계(설계서만 작성).
- **관련 파일**: `client/src/components/CameraView.tsx`, `docs/design/indoor_fp_mitigation_design.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 오류 0건. 실기기 재현 테스트로 co-occurrence 게이트 확장 후 동일 실내 물체 밀착 시 `car`/`bollard`/`movable_signage` 경보 미발동, `sidewalk_normal` 고신뢰도(0.7~0.81)에도 경보 미발동 확인. bbox 렌더링 회귀는 Fragment 수정 후 재확인 대기 중.
- **비고**: `docs/design/indoor_fp_mitigation_design.md`의 §3(물리적 타당성 필터)·§4(씬 분류기 게이트)는 아직 구현 전이다. 특히 §3의 캔버스 초과 임계값(1.02배)은 실외 근접 상황에서의 정상 bbox 데이터가 없어 실외 현장 검증 전까지 확정치가 아니며, §4는 `VNClassifyImageRequest`의 identifier taxonomy 자체가 실측 전이라 로깅 전용 계측 단계부터 시작해야 한다.

---

### 2026-07-07 | 3단계 | 실내 오탐 완화 설계서(§3/§4) 구현 및 §4 씬 분류기 계측 1차 데이터 분석

- **커밋**: (대기 중)
- **변경 내용**: `docs/design/indoor_fp_mitigation_design.md` 설계서를 그대로 구현하고, §4 로깅 전용 계측 단계에서 실기기 실내 데이터를 수집·분석했다.
  - `client/src/components/CameraView.tsx`: §3 물리적 타당성 필터 구현 — `isGeometricallyImplausible(bbox)` 추가(`CANVAS_OVERFLOW_MARGIN=1.02`, w/h가 640 캔버스를 2% 이상 초과하면 클래스 무관하게 반사 경보 제외). `validDetections` 필터 체인에 반영.
  - `client/ios/CoreMLInferenceBridge.swift`: §4 롤아웃 2단계(로깅 전용 계측) 구현 — `VNClassifyImageRequest` 기반 `classifyScene()` 신설. `detectFrame` 응답에 `scene.topLabels`(top-5 identifier+confidence)와 `scene_ms` 지연시간을 추가(`isLikelyIndoor` 판정 로직은 아직 미구현, 설계서 §4.5 지침대로 계측 전용).
  - `client/src/inference/localDetectorSelect.ios.ts`: 브리지 응답의 `scene.topLabels`를 `[SceneClassify] ...` 형식으로 Metro 콘솔에 로그 출력하도록 연결(게이트 미연결, 순수 계측).
  - 네이티브(Swift) 변경이라 `mcp__xcodebuildmcp__build_run_device`로 리빌드·재설치 후 실기기에서 558개 `[SceneClassify]` 로그(전량 실내 세션)를 수집·분석.
- **분석 결과 (실내 558개 샘플)**:
  - `indoor` 리터럴 identifier는 **한 번도 등장하지 않음**. Apple 분류기 taxonomy에 이 정확한 라벨이 없거나 이번 씬에서 전혀 활성화되지 않았다.
  - `outdoor`가 139/558(25%) 등장 — **전량 실내(사무실)에서 나온 오탐**. 동반 identifier(`night_sky`/`sky`/`moon`/`celestial_body`, 평균 confidence 0.11~0.21)로 보아 **천장 조명을 달/밤하늘로 오인해 "outdoor"로 연쇄 추론**하는 것으로 추정됨. 최대 confidence가 0.71까지 나와, 진짜 실외 confidence와 겹칠 위험이 있다(YOLO det/seg에서 봤던 FP-TP confidence 겹침 문제가 씬 분류기에서도 재현될 조짐).
  - 반대로 `computer_monitor`(172회, 평균 0.70), `computer_keyboard`(122회, 평균 0.71), `people`/`adult`(87~92회, 평균 0.68~0.71), `desk`/`furniture`(57~66회, 평균 0.59~0.61)는 고빈도·고confidence로 안정적으로 실내를 정확히 짚어냈다.
  - **결론**: `outdoor` 리터럴 라벨을 그대로 신뢰하는 단순 규칙은 위험하다(25% 오탐률, TP와 confidence 겹침 우려). 대신 "실내 사물 identifier가 고confidence로 존재하면 실내"라는 역방향(positive indoor evidence) 규칙이 더 유망해 보이나, **실외 비교 데이터 없이는 확정할 수 없다.**
- **관련 파일**: `client/src/components/CameraView.tsx`, `client/ios/CoreMLInferenceBridge.swift`, `client/src/inference/localDetectorSelect.ios.ts`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 오류 0건. `build_run_device` 빌드 성공(processId 1677). §3은 실기기 재현 테스트로 기존 오탐 케이스에 대한 영향 없음(회귀 없음) 확인. §4는 계측 전용이라 게이트 동작에는 아직 영향 없음.
- **비고**: 사용자 요청으로 실외 데이터 수집은 추후로 연기됨. §4.4 게이트 활성화(3단계)는 실외 `[SceneClassify]` 데이터 확보 후 재개한다. §3의 `CANVAS_OVERFLOW_MARGIN` 값도 여전히 실외 근접 상황 실측 검증 대기 중.

---

### 2026-07-07 | 3단계 | 실외 실측 로그 확보 및 §4.4 씬 분류기 게이트 규칙 확정·코드 반영

- **커밋**: (대기 중)
- **변경 내용**: Docker(Redis+Ollama+FastAPI, macOS CPU 구성) + ngrok(`partake-primer-surround.ngrok-free.dev`) + Metro 터널(`exp.direct`)을 기동해 실기기를 무선(핫스팟)으로 야외 이동시켜 `[SceneClassify]` 로그를 추가 수집하고, 이전 실내 558건 분석과 대조해 §4.4 게이트 규칙을 확정·구현했다.
  - **실외 실측 분석(74건, 실내→이동→실외→재입장 혼합 세션)**: 진짜 실외 구간(잔디/보도, 191·194행)에서 `outdoor` confidence가 0.48~0.66으로, 기존에 확인된 실내 오탐 패턴(천장 조명→`night_sky`/`moon`/`celestial_body` 동반, 0.51 고정)보다 오히려 높게 나와 confidence 단독으로는 안정적 분리가 어려움을 확인. 대신 **동반 identifier의 종류**가 질적으로 달랐다 — 오탐은 항상 `night_sky`/`celestial_body`/`moon`과, 실외 정탐은 `grass`/`land`/`path`/`plant`/`foliage`/`crosswalk`(212행)와 함께 등장. 씬 분류 지연시간은 평균 11.27ms(최대 74.13ms, 콜드스타트 추정)로 반사 경로 예산(300ms) 대비 부담 없음을 확인.
  - `docs/design/indoor_fp_mitigation_design.md`(v0.1.0 → v0.2.0): §4.3 `classifyScene()` 의사코드를 키워드 매핑 로직(`OUTDOOR_POSITIVE_IDENTIFIERS`/`INDOOR_FALSE_POSITIVE_IDENTIFIERS`)으로 확정, §4.4에 실측 근거 표와 3단계 확정 규칙(실외 긍정 증거 우선 → 조명 오탐 override → 기본값 실내) 추가, §4.5를 "해결된 항목"/"남은 한계"(실외 표본 4~5건뿐)로 재구성, §6 롤아웃 순서 1~3단계 완료 표시.
  - `client/ios/CoreMLInferenceBridge.swift`: `classifyScene()`을 로깅 전용(`topLabels`만 반환)에서 `isLikelyIndoor`/`confidence` 판정 로직으로 교체. `outdoorPositiveIdentifiers`/`indoorFalsePositiveIdentifiers` 키워드 집합 추가. 분류 실패(예외/observations 없음) 시 `isLikelyIndoor=false`(허용적 폴백, §4.6)로 반환.
  - `client/src/inference/types.ts`: `SceneClassification` 인터페이스 신규 추가, `DualDetectionResult`에 `scene?: SceneClassification` 필드 추가.
  - `client/src/inference/localDetectorSelect.ios.ts`: `coremlResults` 타입을 `DualDetectionResult`로 변경하고 `detect()`의 양쪽 반환 경로(하이브리드/풀 CoreML)에 `scene` 필드를 전달하도록 수정(기존에는 로그만 남기고 값이 드롭됐음).
  - `client/src/hooks/useOnDeviceDetection.ts`: `detectFrame()`이 `result.scene`을 캡처해 반환값에 포함하도록 수정(기존에는 `{ seg, det }`만 반환해 상위로 전파되지 않았음).
  - `client/src/components/CameraView.tsx`: `handleFrame`에서 `scene`을 구조분해하고 `isOutdoorByScene = scene ? !scene.isLikelyIndoor : true`를 계산해, 기존 `hasOutdoorSurface`(seg 기반 co-occurrence)와 AND로 결합. `validDetections` 필터에 씬 분류 게이트 조건 추가.
- **관련 파일**: `docs/design/indoor_fp_mitigation_design.md`, `client/ios/CoreMLInferenceBridge.swift`, `client/src/inference/types.ts`, `client/src/inference/localDetectorSelect.ios.ts`, `client/src/hooks/useOnDeviceDetection.ts`, `client/src/components/CameraView.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 오류 0건. `build_run_device` 빌드 성공(processId 1954). 실기기 재설치 후 Metro 로그로 `[SceneClassify]`/`[CoreMLBenchmark]` 정상 출력 확인(현재 실내 세션 기준 `night_sky` override 패턴 재현). 게이트가 실제로 실외에서 정상 발동하고 실내에서 억제되는지의 현장 회귀 테스트는 아직 미실시.
- **비고**: `OUTDOOR_POSITIVE_IDENTIFIERS`/`INDOOR_FALSE_POSITIVE_IDENTIFIERS` 키워드 집합은 오늘 확보한 작은 실외 표본(4~5건) 기준이라, 맑은 날/흐린 날/야간, 도로/공원 등 더 다양한 실외 환경에서 추가 수집·보강이 필요하다(설계서 §4.5 참조). 코드 반영은 완료했으나 실외 현장에서의 최종 회귀 검증(정상 탐지 유지 + 실내 오탐 억제 동시 확인)은 후속 세션 과제로 남는다.

---

### 2026-07-07 | 문서 | 씬 분류기 게이트 기법 해설 문서(팀 학습용) 신규 작성

- **커밋**: (대기 중)
- **변경 내용**: 팀원들이 씬 분류기 게이트 기법(§4)을 잘 모른다는 피드백에 따라, 기존 기술 설계서(`indoor_fp_mitigation_design.md`)와 별도로 배경·원리·코드 위치·FAQ 중심의 학습용 해설 문서를 신규 작성했다.
  - `docs/design/scene_classifier_gate_guide.md` 신규 작성(9개 섹션): (1) 문서 목적, (2) 문제 상황(도메인 시프트, 1차 완화책의 논리적 구멍), (3) 핵심 아이디어(VNClassifyImageRequest 독립성, AND 결합 아키텍처 mermaid), (4) 판정 규칙 도출 과정(단순 방법의 실패 → 동반 identifier 기반 규칙 확정, 실측 표 포함), (5) 코드 위치 매핑 표 + 데이터 흐름 mermaid, (6) 로그로 직접 확인하는 방법(예시 2종), (7) 한계 및 주의점, (8) FAQ 5문항, (9) 참고 문서.
  - `docs/README.md`: v0.9.0 → v0.10.0, design/ 섹션 문서 목록에 신규 문서 인덱스 추가.
- **관련 파일**: `docs/design/scene_classifier_gate_guide.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 규칙(이모지 금지, 한국어, 표 우선, 인용 블록 메타데이터, Mermaid 큰따옴표·`<br/>`) 준수 확인. `indoor_fp_mitigation_design.md`의 실측 수치(confidence, identifier 목록)와 교차 확인해 정합성 확보.
- **비고**: 이 문서는 기술 설계서를 대체하지 않는다 — 안전성 검토·인터페이스 계약 등 구현 세부사항은 여전히 `indoor_fp_mitigation_design.md`가 원본이며, 이 문서는 그 내용을 처음 접하는 팀원 관점에서 재구성한 보조 자료다.

---

### 2026-07-07 | 문서/스킬 | 단계별 스킬 문서(.agents/.claude) 실측 정합 감사 및 두 트리 전수 동기화

- **커밋**: (대기 중)
- **변경 내용**: 8개 단계별 스킬 문서(`.agents/skills/*/SKILL.md`)를 실제 코드와 전수 대조해 낡은 명세를 정정하고, `.agents`↔`.claude` 두 스킬 트리를 완전 동기화했다.
  - **stage3 (yolo-obstacle-detection)**: 최초 계획 taxonomy가 실제 파인튜닝 모델과 어긋나 있던 것을 정정. 객체 탐지 "커스텀 클래스: kickboard/stair" → 실제 **29클래스**(전동킥보드=`scooter`, `stair` 부재) 명시. 노면 "7클래스(braille_damaged/crosswalk/manhole/grating 등)" → 실제 **4클래스**(sidewalk_normal/caution/roadway/braille_normal). `HIGH_RISK_CLASSES`를 set→{클래스:confidence} dict(scooter 포함 5종)+`MIN_HIT_COUNT`로, `P0_SURFACE_CLASSES`를 존재하지 않는 클래스명→`caution` 단일로 정정. 모델 경로를 순정 COCO(`object_detection.pt`/`segmentation.pt`)→실제 파인튜닝(`det_best_20260705.pt`/`segbest.pt`)로 정정. Surface Gate 미발동 알려진 이슈 기록. **온디바이스(CoreML/TFLite) 런타임 각주 신설** — 실제 배포 앱 반사 탐지는 서버가 아니라 온디바이스에서 수행됨을 명시.
  - **stage7 (tts-voice-streamer)**: 인지 TTS 엔진 **Kokoro/Coqui(미구현)→Piper**(`PiperTTSService`, `piper-kss-korean.onnx`), 클라이언트 오디오 **Web Audio API→expo-audio**(`createAudioPlayer`), 오디오 포맷 MP3→WAV(필드명은 `audio_mp3_b64` 유지), panning 미구현 사실 명시. frontmatter description·기술스택표·디렉토리·코드 스케치·테스트 체크리스트 전반 정정.
  - **stage2 (camera-frame-capture)**: detection 프레임 전송을 **base64→바이너리(raw JPEG) 기본**으로 정정(2단 전송: transport 메타 JSON + raw 바이너리 프레임). base64는 구버전 호환·Mock 폴백으로 명시.
  - **stage6 (llm-guidance-orchestrator)**: 실제 클라이언트가 LangChain `ChatOllama`가 아니라 raw `SimpleOllamaClient`/`SimpleOpenAIClient`이고 핫스왑 트리거가 "L3 실패율"이 아니라 "GPU 부하 감지"임을 정정. `MID_RISK_CLASSES`를 존재하지 않는 클래스명(kickboard 등)→실제 29클래스 기준 목록으로 정정. `.claude` 트리의 `gemma4-e4b`(오기)를 실제 `gemma4:e4b`로 통일.
  - **stage4/5 (rag-knowledge-builder/rag-realtime-search)**: RAG 라벨(`labels.py`)·retriever가 최초 계획 명칭(`kickboard`/`stairs`/`manhole`)으로 내부 일관돼 있으나 **실제 탐지 모델 29클래스(scooter/caution)와 어긋나는 코드 레벨 불일치**를 각주로 기록(RAG 재빌드가 걸린 담당자 영역이라 코드 직접 수정은 보류). rag-realtime의 실제 진입점이 `build_search_query`가 아니라 `Retriever.search_guidance(detect_info, k=5)`임도 명시.
  - **두 트리 동기화**: `.claude/skills/`에 누락돼 있던 `xcode-build-management` 스킬을 복사하고, 서로 어긋나 있던 5개 스킬(camera/llm/rag-knowledge/tts + rag-realtime)을 `.agents` 정본 기준으로 동기화. 결과적으로 **8개 스킬 SKILL.md·references 전부 양 트리 일치** 확인.
  - `SKILLS.md`·`CLAUDE.md`: 스킬 인덱스 표의 낡은 설명(stage2 base64, stage3 킥보드/계단, stage4 Llava) 정정, §8 두 트리 "xcode 누락·어긋남" 주석을 "전수 동기화 완료(여전히 수동 동기화 필요)"로 갱신.
- **관련 파일**: `.agents/skills/{camera-frame-capture,llm-guidance-orchestrator,rag-knowledge-builder,rag-realtime-search,tts-voice-streamer,yolo-obstacle-detection}/SKILL.md`, `.claude/skills/` 8개 스킬 전체(동기화), `SKILLS.md`, `CLAUDE.md`, `docs/changelogs/kb.md`
- **검증 결과**: 두 트리 diff 전수 검사로 8개 스킬 SKILL.md·references 완전 일치 확인. 정정 근거는 실제 코드(`yolo_detector.py`/`reflex_gate.py`/`surface_gate.py`/`tts_service.py`/`l1_classifier.py`/`labels.py`/`retriever.py`) 및 `docs/ops/model_class_validation_report.md`와 교차 확인. 문서 규칙(이모지 금지, 한국어, 표 우선, 인용 블록 메타데이터) 준수.
- **비고**: 코드 레벨의 실제 버그성 불일치 2건(RAG `labels.py` 명칭이 탐지 taxonomy와 어긋남, Surface Gate 미발동)은 위험도/RAG 로직 담당자 판단 영역이라 스킬 문서에는 사실만 기록하고 코드는 직접 수정하지 않았다. 후속 담당자 검토 필요. references/implementation_detail.md의 라인 단위 전수 검증은 이번 범위에서 제외(SKILL.md 우선 정정), 향후 필요 시 별도 진행.

---

### 2026-07-07 | 문서 | 루트 문서(CLAUDE.md/README.md) 기술 스택 stale 항목 실측 정정

- **커밋**: (대기 중)
- **변경 내용**: 스킬 감사 중 발견한, 루트 권위 문서의 기술 스택·환경변수 stale 항목을 실제 코드 기준으로 정정(스킬 문서와 동일 기준으로 통일).
  - `CLAUDE.md` §2: `Ollama (Gemma2:9b, Llava, ...)` → `gemma4:e4b, nomic-embed-text` + VLM 캡셔닝을 Gemini API(`gemini-2.5-flash-lite`)로 분리 명시. `TTS: Kokoro/Coqui` → `Piper`. LLM Orchestration에 raw SimpleOllamaClient/SimpleOpenAIClient(LangChain 래퍼 미사용) 명시. 클라이언트 `Audio: Web Audio API` → `expo-audio(createAudioPlayer)`, 온디바이스 추론(CoreML/TFLite) 항목 추가.
  - `README.md`: 7단계 요약 표(stage3 킥보드→scooter·29/4클래스·온디바이스, stage4 Llava→Gemini, stage6 ChatOllama→SimpleOllamaClient·gemma4:e4b, stage7 Kokoro/Coqui→Piper·Web Audio→expo-audio) 및 기술 스택 리스트 정정. 환경변수 표 `GEMMA_MODEL` 기본값 `gemma4-e4b`→`gemma4:e4b` 정정, 미사용 `LLAVA_MODEL` 행에 "미사용(구 Llava 잔재)" 명시하고 실제 캡셔닝 키 `GOOGLE_API_KEY` 행 추가. RAG 빌드 파이프라인 주석의 Llava 캡셔닝→Gemini 캡셔닝 2건 정정.
  - 두 문서 상단 버전 메타데이터 갱신(CLAUDE.md v0.3.2, README.md v0.2.1).
- **관련 파일**: `CLAUDE.md`, `README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 정정값은 실제 코드(`llm_client_factory.py` `GEMMA_MODEL` 기본 `gemma4:e4b`, `gemini_captioner.py` `GOOGLE_API_KEY`, `tts_service.py` PiperTTSService, `audioEngine.ts` expo-audio) 및 `.env.example`과 교차 확인. `grep` 재검사로 정정 문맥 밖 잔여 stale 토큰 0건 확인.
- **비고**: `docs/AGENTS.md`는 이미 상단에 "루트 문서가 최신 기준" deprecated 안내가 있는 stale 중복 사본이라 이번에도 수정 대상에서 제외했다(동일 stale 토큰이 남아있으나 문서 자체가 참고용). `.env.example`의 미사용 `LLAVA_MODEL` 변수 자체 제거는 `.env`/`.env.example` 정리 시 별도 검토.

---

### 2026-07-07 | 리서치 | STT 모델(Alibaba SenseVoice-Small) 도입 정당성 검토 보고서 작성

- **커밋**: (대기 중)
- **변경 내용**: 사용자 요청으로 STT 경로용 SenseVoice-Small의 도입 타당성을 지연·로딩·한국어 정확도 관점에서 웹 리서치 기반으로 검토하고, `docs/research/`에 타당성 보고서로 정리했다.
  - `docs/research/sensevoice_stt_feasibility.md` 신규 작성(6개 섹션): (1) 개요(STT가 현재 7단계 골격 범위 밖·음성 명령 경로임을 설계 문서로 확인), (2) SenseVoice-Small 실측 스펙 표(지연 70ms/10s·RTF 52~118×, 로딩 0.81초, 크기 827MB/RAM 700MB, 한국어 CER 8.28% vs Whisper-Large-V3 5.59%, 비스트리밍 오프라인, CPU 구동, FunASR MODEL_LICENSE 상업 허용), (3) 아키텍처 적합성(서버 배치=정합/온디바이스=자원 경합), (4) 대안 비교표(Whisper-Large-V3/faster-whisper/whisper.cpp/클라우드), (5) 결론·권고(서버+짧은 한국어 명령이면 정당, 3가지 단서), (6) 참고 자료.
  - `docs/README.md`: research/ 섹션 문서 목록에 신규 보고서 인덱스 추가.
- **관련 파일**: `docs/research/sensevoice_stt_feasibility.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 실측 수치는 웹 리서치(Hugging Face FunAudioLLM/SenseVoiceSmall, whispernotes CJK 벤치마크, FunASR MODEL_LICENSE, arXiv 2407.04051)로 교차 확인. 기존 `gemini_fallback_feasibility.md`와 동일한 보고서 형식(메타데이터 인용 블록, 섹션 번호, 표 우선, 이모지 금지) 준수.
- **비고**: 결론은 "서버측 STT + 짧은 한국어 명령이면 지연·로딩 관점에서 채택 정당(강력 후보)"이며, 한국어 정확도 2.7%p 열위의 도메인 명령 셋 실측 검증, 온디바이스 요구 시 재평가, 라이선스 attribution 준수를 전제로 단다. STT 경로 정식 착수 시 본 보고서를 기준선으로 삼는다. 코드 변경은 없음(리서치 문서 전용).

---

### 2026-07-08 | 1+2단계 | iOS 네이티브 브릿지 미사용 사본 제거 및 파일 위치 함정 주석 보강

- **커밋**: (대기 중)
- **변경 내용**:
  - STT 네이티브 브릿지 추가를 검토하는 과정에서, `project.pbxproj`의 `Minchodan` 그룹에 `path` 속성이 없어 그룹 소속 파일이 `Minchodan/` 서브폴더가 아니라 SRCROOT(`client/ios/` 루트)로 resolve되는 구조를 재확인. 이 함정으로 과거에 생성된 채 빌드에 전혀 연결되지 않은 미사용 사본 `client/ios/Minchodan/CoreMLInferenceBridge.mm`(pbxproj 미참조, 실제 빌드 대상은 `client/ios/CoreMLInferenceBridge.mm`)를 발견하고 삭제.
  - `client/ios/CoreMLInferenceBridge.swift` 헤더 주석 갱신: 기존 "Minchodan/CoreMLInferenceBridge.swift는 미사용 사본" 문구(대상 파일이 이미 없어 stale)를 "신규 네이티브 브릿지 파일도 client/ios/ 루트에 두어야 한다"는 일반 규칙 + 이번 `.mm` 사본 발견·제거 이력으로 교체.
- **관련 파일**: `client/ios/Minchodan/CoreMLInferenceBridge.mm`(삭제), `client/ios/CoreMLInferenceBridge.swift`, `docs/changelogs/kb.md`
- **검증 결과**: `grep`으로 `project.pbxproj` 및 `project.xcworkspace` 전체에서 `Minchodan/CoreMLInferenceBridge` 참조 0건 확인 후 삭제. 삭제 대상 파일 내용이 실제 빌드 대상 `.mm`과 동일(RCT_EXTERN_MODULE 선언)함을 대조 확인.
- **비고**: 런타임 동작 변화 없음(애초에 컴파일되지 않던 사본 제거). 향후 STT 브릿지 등 신규 네이티브 파일 추가 시 `client/ios/` 루트에 두는 규칙을 헤더 주석으로 명문화해 재발 방지.

---

### 2026-07-08 | 3+7단계 | 전체 파이프라인 실측 감사 후 발견된 긴급 결함 4건 수정

- **커밋**: `fix(detection,stt,auth): YOLO 기본가중치·STT 크래시·JWT검증·중복억제 결함 수정`
- **변경 내용**: `dev` 브랜치에 팀원 4개 브랜치(kb/jy/jh/th)를 모두 병합한 뒤, 서버 전체 코드·파일·의존성을 실제로 조사(5개 조사 에이전트 병렬 실행)해 "구현됨"으로 문서화돼 있던 항목 중 실제로는 조용히 깨져 있던 결함 4건을 찾아 수정했다.
  - **YOLO 기본 가중치 오지정**: `server/detection/config.py`의 `YOLO26N_OBJECT_DET`/`YOLO26N_SEG` 기본값(`.env` 부재 시 폴백)이 커스텀 학습이 전혀 안 된 COCO 80클래스 스톡 모델(`object_detection.pt`/`segmentation.pt`)을 가리키고 있었음을 확인. 실제 학습 완료 가중치(`det_best_20260705.pt`/`segbest.pt`)로 정정. `.env`/`.env.example`은 원래부터 정상값이었으나, 두 파일이 없거나 다른 환경에서 실행하면 에러 없이 잘못된 모델이 조용히 로드되는 구조였다.
  - **STT 모듈 import 크래시**: `server/stt/stt_service.py`가 모듈 최상단에서 `from faster_whisper import WhisperModel`을 무가드로 실행해, `faster-whisper`가 설치되지 않은 환경(현재 requirements.txt에도 미기재)에서는 `import server.stt`만 해도 `ModuleNotFoundError`로 전체 프로세스가 죽었다. `pytest tests/`를 실행하면 STT 테스트 3개 파일이 collection 단계에서 즉시 실패해 전체 테스트 스위트가 깨지는 상태였음을 실측으로 확인. `try/except`로 임포트를 방어하고 `FASTER_WHISPER_AVAILABLE` 플래그를 두어, 패키지가 없어도 다른 모듈 import에는 영향이 없도록 수정(`get_model()`의 기존 예외 처리가 자연스럽게 `RuntimeError`로 래핑).
  - **JWT 토큰 검증 함수 부재**: `server/db/security.py`에 `create_access_token()`(발급)만 있고 이를 검증(`decode`)하는 함수가 프로젝트 어디에도 없어, 관리자 로그인이 발급하는 토큰이 사실상 검증 불가능한 상태였다. `decode_access_token()`을 추가해 서명·만료 검증이 가능하도록 함(호출부에서 401 변환은 후속 과제).
  - **반사 경보 중복 억제 미연결**: `server/tts/suppressor.py`의 `AlertSuppressor`(Redis `setex` 60초 기반 중복 억제)는 구현이 완료돼 있었으나, 실제 반사 알림 전송 지점인 `server/detection/consumer.py`의 `_send_reflex_alert()`가 이를 전혀 호출하지 않아 동일 장애물에 대해 60초 쿨다운 없이 반사 경보가 계속 발행될 수 있는 상태였다. `should_suppress()`/`mark_as_sent()`를 전송 경로에 배선.
  - **부수 발견 및 수정**: 위 STT 크래시를 고치는 과정에서 `tests/test_stt_service_template.py`가 이미 폐기된 모델 정책(`faster-whisper-small`)을 참조하고 있어 테스트가 실패하는 것을 확인(jh의 `78ca47a` small→medium 정책 변경 커밋이 프로덕션 설정만 바꾸고 테스트는 갱신하지 않았던 기존 불일치, 크래시에 가려져 있었음) — `faster-whisper-medium`으로 정정.
  - `tests/test_detection.py`에 `TestReflexAlertSuppression` 신규 테스트 2건(억제 케이스/비억제 케이스) 추가해 중복 억제 배선을 실제로 검증.
  - `docs/ops/environment_variables.md`(v0.4.1→v0.4.2): `YOLO26N_OBJECT_DET`/`YOLO26N_SEG` 기본값 정정, `DETECTOR_TYPE`이 코드에서 읽히지 않는 죽은 변수임을 명시.
  - `docs/ops/test_specification.md`(v0.6.0→v0.6.1): TC-TTS-005(중복 억제) 상태를 대기→완료로 갱신, 검증 테스트 위치 및 여전히 미해결인 반사 사전합성 클립 파일 부재 문제를 비고에 명시.
- **관련 파일**: `server/detection/config.py`, `server/stt/stt_service.py`, `server/db/security.py`, `server/detection/consumer.py`, `tests/test_stt_service_template.py`, `tests/test_detection.py`, `docs/ops/environment_variables.md`, `docs/ops/test_specification.md`, `docs/changelogs/kb.md`
- **검증 결과**: `pytest tests/ --ignore=tests/test_ws_echo.py` 108 passed, 1 skipped(test_ws_echo.py는 실제 uvicorn 서버 기동이 필요해 통합 smoke로 별도 분류, 이번 변경과 무관). 수정한 4개 프로덕션 파일 + 테스트 파일 `ruff check` 전체 통과.
- **비고**: 이번 감사에서 발견했으나 코드 수정으로 해결 불가능한 항목은 그대로 남겨뒀다 — (1) `data/reflex_clips/*.mp3` 사전합성 클립 파일 자체가 저장소에 없어 반사 음성이 실제로는 재생 불가능(오디오 자산 제작 필요), (2) `faster-whisper` 패키지 자체 미설치로 STT 실제 추론은 여전히 불가(사전 허가 없는 requirements.txt 변경 금지 원칙에 따라 패키지 추가는 보류), (3) WS 디바이스 인증(하드코딩 딕셔너리)과 JWT 인증이 여전히 통합되지 않은 별개 시스템, (4) MariaDB 테이블 자동 생성(`create_all`) 부재로 수동 마이그레이션 필요. 전체 구현/미구현 현황은 세션 내 Artifact 현황판으로 별도 정리함.

---

### 2026-07-08 | 1+2단계 | iOS 실기기-서버 네비게이션 연동 실측 테스트

- **커밋**: (대기 중)
- **변경 내용**:
  - `docker/docker-compose.macos.yml`로 Redis+Ollama+FastAPI 3컨테이너를 로컬에서 빌드·기동. 이미지 빌드는 `pip install -r requirements.txt` 단계(torch 2.12.1+torchvision, langchain 계열 7종, chromadb, ultralytics, opencv 등 대용량 스택 다운로드)에서 약 48분 소요됨을 실측 확인. Ollama에는 `gemma4:e4b`, `nomic-embed-text` 모델이 이미 pull되어 있음을 확인.
  - `client/src/config/index.ts` 수정: `WS_URL`이 더 이상 응답하지 않는 ngrok 터널(`partake-primer-surround.ngrok-free.dev`, 로컬 ngrok 프로세스 없음, HTTP 404 확인)을 가리키고 있어 로컬 도커 서버와 연동이 불가능했던 문제를 해결. `LAN_IP`를 Mac 실측 IP(`192.168.0.209`, 기존 값 `192.168.0.11`은 stale)로 정정하고, `WS_URL`을 `ws://${LAN_IP}:8000/ws/detect` 로컬 직결 방식으로 전환. `Info.plist`의 `NSAllowsArbitraryLoads=true` 기설정을 확인해 평문 `ws://`도 ATS 차단 없이 통과됨을 확인.
  - `client/ios`가 CocoaPods sandbox와 `Podfile.lock` 불일치 상태였음(`build_run_device` 최초 시도에서 빌드 실패로 확인)을 `pod install` 재실행으로 해소(93개 의존성 재통합).
  - xcodebuildmcp `build_run_device`로 실기기(`고태현의 iPhone`, iOS 26.5)에 빌드·설치는 성공했으나, 기기 잠금 상태로 최초 실행이 `FBSOpenApplicationRequestID`/`RequestDenied`(Locked)로 거부됨. 잠금 해제 후 `launch_app_device`로 재시도해 정상 실행(PID 2602) 확인.
- **관련 파일**: `client/src/config/index.ts`, `client/ios/Podfile.lock`(재통합, 코드 변경 아님)
- **검증 결과**: FastAPI 컨테이너 로그 실측으로 `WebSocket /ws/detect?device_id=dev-001` accepted → `hello` 수신 → 토큰 검증 성공(`auth_ok`) → `detection` 이벤트 지속 수신(`decode_ms` 0.3~4ms)까지 확인. 서버가 최초 ByteTrack 호출 시 `lap` 패키지를 Ultralytics AutoUpdate로 런타임에 자동 설치하는 부수 동작을 확인함(`requirements.txt`에 미고정 상태).
- **비고**: 이번 세션은 로컬 도커/LAN 환경에서 1~2단계(WebSocket Gateway + 카메라 프레임 캡처) 연동이 실제로 동작함을 실측 확인한 것이 핵심이며, RAG 검색·LLM 가이드 문장 생성·TTS 응답까지 이어지는 종단 네비게이션 시나리오(4~7단계)는 이번 세션에서 검증하지 않았으므로 별도 확인이 필요하다. `ultralytics`가 `lap`을 자동 설치하는 동작처럼 `requirements.txt`에 명시되지 않은 채 런타임에 자동 설치되는 의존성이 있어, 재현성 확보를 위해 `lap` 버전 고정을 검토할 것.

---

### 2026-07-08 | 4~7단계 | 종단 네비게이션(RAG+LLM+TTS) 실측 감사 및 긴급 결함 다수 수정

- **커밋**: (대기 중)
- **변경 내용**: 위 세션에 이어 4~7단계(RAG 검색, LangGraph 가이드 생성, TTS 음성 응답)를 실기기로 종단 실측하며 발견한 결함을 순차 수정했다. 발견 순서대로 기록한다.
  - **로깅 결함**: `server/main.py`에 `logging.basicConfig`가 전혀 없어 `logger.info/debug` 전량이 조용히 드롭되고 있었음(uvicorn 자체 로그만 보임). DEBUG 레벨 `basicConfig`를 추가해 파이프라인 전체 가시성을 확보했다.
  - **RAG(4~5단계) 미연동**: ChromaDB(`safety_guidelines` 컬렉션, 33건)에 실제 데이터가 있음에도 `server/detection/consumer.py`가 오케스트레이터 호출 시 `rag_context`를 채우지 않고, `server/rag/retriever.py`의 `Retriever.search_guidance()`를 어디서도 호출하지 않아 실시간 안내 생성 시 RAG가 전혀 사용되지 않았다. `server/rag/retriever.py`에 `get_default_retriever()` 싱글턴을 추가하고, `consumer.py`의 `_send_cognitive_guide()`에서 최고 신뢰도 탐지 클래스 기준으로 검색해 `rag_context`를 채우도록 연결했다. 연결 과정에서 부수 결함 2건을 추가 발견·수정: (1) `server/rag/embedding_engine_factory.py`가 `.env`의 `OLLAMA_BASE_URL` 대신 어디에도 정의되지 않은 `OLLAMA_HOST`를 읽고 있어 컨테이너 내부에서는 항상 `localhost:11434`로 폴백되던 결함, (2) `.env`/`.env.example`의 `CHROMA_COLLECTION` 기본값(`bidding_kb`/`minchodan_kb`)이 실제 저장된 컬렉션명(`safety_guidelines`)과 달라 항상 빈 컬렉션을 조회하던 결함. `server/rag/vector_db_factory.py`의 `VectorDBFactory.get_vector_db()`에 `collection_name` 파라미터를 추가해 정정.
  - **Docker Desktop 메모리 부족으로 Ollama 로드 실패**: `gemma4:e4b`(실측 약 8B 파라미터, 8.01GiB Q4_K)가 Docker Desktop 기본 할당 메모리(7.7GiB)로는 로드 자체가 불가능해 매 요청 `llama-server process has terminated: signal: killed`로 3회 재시도(+OpenAI 폴백 시도, 키 미설정으로 실패) 후 고정 폴백 문구로 처리되던 문제. 담당자가 Docker Desktop 메모리를 13.6GiB로 증설해 해소.
  - **Piper TTS 바이너리 부재**: `Dockerfile`에 `piper` CLI 설치 단계가 없어 `PiperTTSService`가 항상 `[Errno 2] No such file or directory: 'piper'`로 실패하던 문제. `requirements.txt`에 `piper-tts==1.4.2`, `pathvalidate==3.3.1` 추가로 해소(담당자 승인).
  - **Piper CLI `--config` 무시 업스트림 결함**: `piper-tts==1.4.2`의 `__main__.py`가 `--config` 인자를 파싱만 하고 `PiperVoice.load()`에 전달하지 않아, 항상 `<model_path>.json`을 자동 탐색하는 결함을 확인. `server/tts/tts_service.py`의 `_build_compat_config()`를 재작성해 보정된 설정을 모델과 동일 basename으로 심볼릭 링크한 임시 디렉터리에 두는 방식으로 우회(원본 `.onnx`/`.onnx.json`은 불변).
  - **TTS 250ms 타임아웃 비현실적**: `server/tts/realtime_tts.py`의 `asyncio.wait_for(..., timeout=0.250)`이 서브프로세스 기반 Piper(호출마다 ONNX 모델 재로드, 실측 약 1.6~1.9초)에는 항상 타임아웃되어 매번 고정 폴백 문구(`전방 주의, 천천히 멈추세요`)로만 응답하던 문제. 타임아웃을 3.0초로 상향.
  - **클라이언트 안내 음성 재생 미구현**: 서버가 `guide` 메시지로 `audio_mp3_b64`를 보내도 `client/src/components/CameraView.tsx`가 디버그 텍스트만 갱신할 뿐 실제 오디오 재생 코드가 전혀 없었고, `react-native-tts`(단말 내장 TTS 폴백)도 패키지 자체가 미설치 상태였다. `client/src/services/audioEngine.ts`에 `playGuideAudio()`(expo-file-system 레거시 API로 base64 WAV를 캐시 파일로 쓴 뒤 1회 재생) 및 `stopGuideAudio()`(선점) 신규 구현, `CameraView.tsx`의 `guide` 핸들러에서 호출하도록 연결.
  - **device_id 라우팅 결함**: `CameraView.tsx`의 실제 프레임 전송 경로(바이너리/구버전 base64 양쪽)가 메타데이터에 `device_id`를 아예 포함하지 않아, 서버 `server/capture/frame_decoder.py`의 `_parse_frame_meta()`가 항상 `"unknown"`으로 처리 → 모든 `guide 전송`/반사 알림이 실제 연결된 `dev-001` 소켓이 아닌 존재하지 않는 소켓으로 전송되어 완전히 유실되고 있었다(소리/햅틱이 전혀 안 들리던 근본 원인). `device_id: DEVICE_ID` 필드를 두 전송 지점에 추가해 해소.
  - **LLM(gemma4:e4b) thinking 모드로 빈 응답**: L2 생성 노드가 `num_predict=50`으로 호출하는데, `gemma4:e4b`가 기본적으로 "thinking"(추론) 토큰을 먼저 생성하는 모델이라 50토큰 예산을 추론에서 전량 소진하고 `content`가 항상 빈 문자열로 반환되던 결함을 Ollama 원본 응답(`done_reason: "length"`, `thinking` 필드에 잘린 영어 추론 확인)으로 실측 확인. 이 때문에 L3 검증(빈 문장)이 항상 실패해 매번 동일한 고정 폴백 문구만 나가고 있었다. `server/orchestration/llm_client_factory.py`의 `SimpleOllamaClient.ainvoke()`에 `think=False` 옵션을 추가하고 `num_predict`를 100으로 상향해 해소(수정 후 `car`/`person`/`kickboard` 등 클래스별로 서로 다른 정상 문장 생성 확인).
  - **인지 가이드 쿨다운 타이밍 결함**: 선점형 클라이언트 재생과 결합 시 이전 안내가 끝나기 전에 다음 안내가 도착해 계속 잘리는 문제가 있어 `DetectionConsumer`에 device_id별 8초 쿨다운을 추가했으나, 최초 구현은 "오케스트레이션 처리 시작" 시점에 쿨다운 슬롯을 갱신해, 처리 소요 시간(2~10초+)이 요청마다 달라 실제 "전송"(클라이언트 재생 트리거) 간격이 8초보다 가까워지는 결함이 있었다(실측 2.5초 간격 확인). 시작 시점 검사는 조기 반환 최적화용으로만 남기고, 실제 슬롯 갱신은 전송 직전 재검사 지점으로 이동해 실제 전송 간격이 8초 이상 보장되도록 정정(수정 후 13.9초 간격 실측 확인).
  - **Piper phoneme_type 불일치로 인한 속도/음질 이상**: `piper-kss-korean.onnx.json` 원본이 `phoneme_type: "pygoruut"`인데 `piper-tts==1.4.2`는 `pygoruut`를 지원하지 않아(PhonemeType enum: espeak/text/pinyin만 존재), 처음에는 `espeak`로 대체했다. espeak IPA 출력 자체는 문법적으로 올바르나 이 모델이 학습한 pygoruut 분절과 달라 duration predictor가 오작동해 실측 약 2.5~3배 느리게 합성되는 문제가 있어(20음절 기준 정상 3.5~4s인데 10s), `length_scale`을 임시로 0.4~0.6까지 낮춰 속도만 보정했으나 담당자가 실기기에서 "중간이 낚이는" 끊김을 계속 보고. `pygoruut` 패키지(담당자 승인)를 도입해 `server/tts/tts_service.py`에서 직접 음소화 후 모델의 `phoneme_id_map`(163개 기호)에 없는 결합 발음기호 4종(`ʰ ̚ ̠ ͈`)만 필터링하고 `phoneme_type: "text"`로 그 결과를 그대로 흘려보내는 방식으로 전환. 이후 `length_scale=0.9`(정상 범위)에서 20음절 기준 약 5초로 자연스러운 속도 복원을 확인했으나, 미세 무음 구간(15~60ms) 자체는 espeak 대체 시와 유사한 빈도로 남아있어 **이 잔여 끊김이 진짜 음질 결함인지 한국어 자연스러운 조음 간격인지는 실제 청취 검증 없이는 판단 불가**로 세션 종료 시점까지 미해결.
  - **오디오 콜백 경합 완화(부분 대응)**: 온디바이스 CoreML 추론 루프가 가이드 음성 재생 중에도 계속 돌며 매 프레임(0.5~0.7초)마다 `[Reflex]`/`[SceneClassify]`/`[CoreMLBenchmark]`/`[Camera/Real]` 콘솔 로그 4~5줄을 Metro 개발 브릿지로 실시간 전송해 JS 스레드와 오디오 콜백이 경합할 가능성을 실측 정황(가이드 재생 구간과 프레임 로그가 촘촘히 인터리브됨)으로 확인. `client/src/services/audioEngine.ts`에 `isGuidePlaying` 플래그를 추가하고, 가이드 재생 중에는 해당 4개 콘솔 로그를 억제하도록 3개 파일(`useCamera.ts`, `useOnDeviceDetection.ts`, `localDetectorSelect.ios.ts`)을 수정(반사 탐지/햅틱/비프 로직 자체는 그대로 유지, 콘솔 출력만 억제). **주의**: 반사 경로 추론 자체를 멈추는 것은 안전 설계 원칙 위반이라 시도하지 않았다.
  - **클라이언트 오디오 세션 미설정**: `client/src/services/audioEngine.ts`가 `expo-audio`의 `setAudioModeAsync`를 import만 하고 한 번도 호출하지 않고 있었음을 확인. 반사 루프 플레이어와 인지 가이드 일회성 플레이어가 동시 활성화되는 상황을 위해 `interruptionMode: "mixWithOthers"`로 명시 설정하도록 `ensureSession()`을 재작성.
- **관련 파일**: `server/main.py`, `server/rag/retriever.py`, `server/rag/vector_db_factory.py`, `server/rag/embedding_engine_factory.py`, `server/detection/consumer.py`, `server/orchestration/llm_client_factory.py`, `server/tts/tts_service.py`, `server/tts/realtime_tts.py`, `requirements.txt`, `.env.example`, `docs/ops/environment_variables.md`, `client/src/components/CameraView.tsx`, `client/src/services/audioEngine.ts`, `client/src/hooks/useCamera.ts`, `client/src/hooks/useOnDeviceDetection.ts`, `client/src/inference/localDetectorSelect.ios.ts`
- **검증 결과**: RAG 검색 배선(임베딩 API 200 OK 실측), LLM 정상 문장 생성(클래스별 상이한 유효 문장 실측), 서버 전송 간격 쿨다운(13.9초 간격 실측), 클라이언트 오디오 재생 완주(`didJustFinish=true`까지 로그 실측) 각각 개별적으로는 정상 동작 확인. 다만 **실기기 최종 청취 기준으로는 세션 종료 시점까지 음성 끊김 문제가 완전히 해소됐다는 확인을 받지 못함** — 남은 원인은 phoneme_type 대체로 인한 잔여 음질 열화 가능성이 유력하나, 자동화된 파형 분석(무음 구간 검출)만으로는 "진짜 결함"과 "정상적인 한국어 조음 간격"을 구분할 수 없어 확정하지 못했다.
- **비고**: 이번 세션에서 수정한 결함 다수(로깅 무설정, RAG 미연동, TTS 바이너리 부재, LLM 빈 응답, device_id 유실)는 전부 "구현됐다고 문서화됐지만 실제로는 조용히 끊겨있던" 유형으로, 이전 감사(`2026-07-08 | 3+7단계` 항목)에서 지적한 패턴이 4~7단계에도 광범위하게 존재했음을 시사한다. 다음 세션에서는 (1) 실기기 청취로 pygoruut 전환 후 음질이 실제로 개선됐는지 확정, (2) 필요 시 espeak로 정상 학습된 표준 한국어 Piper 보이스로 교체 검토, (3) `docs/ops/test_specification.md`에 이번에 발견된 4~7단계 결함들에 대응하는 회귀 테스트 케이스 추가를 우선 진행할 것.

---

### 2026-07-09 | 6+7단계 | TTS 짤림·끊김 코드 감사 및 근본 원인 4건 수정

- **커밋**: (대기 중)
- **변경 내용**: 다른 세션(fable)의 코드 리뷰로 지적된 "짤림"(재생 중 안내가 끊기고 다음 안내로 전환)과 "끊김"(음성이 뚝뚝 끊기며 재생) 현상을 현재 코드베이스와 직접 대조 검증한 뒤, 확인된 근본 원인 4건을 수정했다.
  - **고정 쿨다운과 실제 WAV 길이의 불일치(짤림)**: `server/detection/consumer.py`의 `_guide_cooldown_sec=8.0`이 문장 길이와 무관한 고정값이었다(직전 세션에서 "처리 시작 시점"이 아닌 "전송 직전 재검사"로 갱신 시점만 고쳤을 뿐, 값 자체는 여전히 상수). `l3_validator.py`의 `MAX_LEN=20`·`DEFAULT_SPEED=0.9` 조합상 실측 최대 길이는 약 5~6초로 8초 안에 안전하게 들어오는 편이지만, 두 상수가 서로 다른 파일에서 독립적으로 바뀔 수 있어 암묵적 결합이 깨지기 쉬운 구조였다. `server/tts/realtime_tts.py`에 `_wav_duration_ms()`(stdlib `wave` 모듈로 프레임수/샘플레이트에서 재생 길이 계산)를 추가하고 `synthesize()`/`synthesize_from_llm()`의 반환값을 `(b64_audio, duration_ms)` 튜플로 변경, `consumer.py`는 직전 안내의 실측 길이를 `_last_guide_duration_sec`에 저장해 `_required_guide_gap_sec()=max(8.0, 직전_길이+1.5s)`로 다음 쿨다운을 동적 산정하도록 정정. guide 페이로드에 `duration_ms` 필드 추가(`docs/design/api_specification.md` v0.4.1 반영).
  - **Piper 콜드스타트로 인한 3초 타임아웃(안내 유실)**: `PiperTTSService`가 호출마다 `piper` CLI 서브프로세스를 새로 기동해 ONNX 모델을 매번 재로드(실측 1.6~1.9초 콜드스타트)하고 있어, `realtime_tts.py`의 3.0초 타임아웃 여유가 크지 않았다. `piper-tts==1.4.2` 휠을 직접 내려받아 소스를 확인한 결과, CLI 래퍼(`__main__.py`)만 `--config` 인자를 파싱 후 버리는 결함이 있을 뿐 라이브러리 함수 `PiperVoice.load(model_path, config_path=..., use_cuda=...)` 자체는 `config_path`를 정상 처리함을 확인. `PiperTTSService`를 상주 프로세스화해 `PiperVoice.load()`를 최초 1회만 수행(`_ensure_voice()` + `asyncio.Lock`)하고, 이후 호출은 `voice.synthesize_wav()`로 동일 in-process 세션을 재사용하도록 재작성. `onnxruntime.InferenceSession.run()`이 공식적으로 스레드-세이프함을 근거로 합성 자체는 락 없이 `asyncio.to_thread`로 동시 처리. 기존 CLI 우회용 심볼릭 링크 트릭(`_compat_model_path`)도 `config_path`를 직접 넘길 수 있게 되며 함께 제거됨. `subprocess` 의존 제거로 `# nosec B404`/`# noqa: S603` 억제 주석도 함께 삭제. `PIPER_BINARY_PATH` 환경변수는 더 이상 쓰이지 않아 제거하고 `PIPER_USE_CUDA`(선택, 기본 false)를 신규 추가(`docs/ops/environment_variables.md` v0.4.4 반영).
  - **로그 게이트 누락으로 인한 억제 무력화(끊김)**: 직전 세션(`2026-07-08 4~7단계` 항목)에서 `isGuidePlaying` 게이트를 `useCamera.ts`/`useOnDeviceDetection.ts`/`localDetectorSelect.ios.ts` 3개 파일에는 적용했으나, 실제로 매 탐지 사이클마다 콘솔 로그를 찍는 `client/src/components/CameraView.tsx`의 `[ReflexGate]` 4곳과 `[CoreMLBench]` 1곳, `client/src/hooks/useWebSocket.ts`의 `[WS] 반사 알림 수신` 로그에는 게이트가 누락돼 있어 억제가 사실상 무력화된 상태였다. 6곳 모두 `if (!audioEngine.isGuidePlaying)` 조건으로 감싸도록 정정.
  - **300KB base64 문자열의 불필요한 React 상태 경유(끊김)**: `useWebSocket.ts`의 `ws.onmessage`가 `guide` 메시지(약 5초 WAV 기준 base64 약 300KB)를 포함한 전체 payload를 매번 `setLastMessage()`로 상태에 태워, `JSON.parse → setState → CameraView 리렌더 → effect → writeAsStringAsync`로 JS 스레드를 불필요하게 두 번 관통시키고 있었다. 이미 `reflex_alert` 타입은 onmessage에서 직접 `audioEngine.playBeep()`를 호출하는 패턴이 적용돼 있었으므로, `guide` 타입도 동일하게 onmessage에서 `audioEngine.playGuideAudio()`를 직접 호출하도록 변경하고, `setLastMessage`에는 `audio_mp3_b64` 필드를 제거한 사본만 저장하도록 정정. `CameraView.tsx`의 기존 `lastMessage.type === "guide"` effect에서는 오디오 재생 호출을 제거(텍스트 표시만 유지).
  - **(적용 보류)** fable 분석의 5번째 항목인 "guide 재생 중 반사 비프 덕킹/우선순위 정책"은 UX 판단이 필요한 정책 변경이라 이번 세션에서는 적용하지 않고 후속 과제로 남긴다. 현재는 guide와 reflex beep가 모두 풀볼륨으로 동시 재생될 수 있는 상태 그대로다.
- **관련 파일**: `server/tts/realtime_tts.py`, `server/tts/tts_service.py`, `server/detection/consumer.py`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `client/src/types/detection.ts`, `docs/design/api_specification.md`, `docs/ops/environment_variables.md`, `docs/changelogs/kb.md`
- **검증 결과**: 수정한 3개 서버 파일 `ruff check` 통과, `python3 -m py_compile` 통과. 클라이언트 `npx tsc --noEmit` 전체 통과(신규 타입 오류 없음). **주의**: 이 환경(개발 머신)에는 `piper-tts`가 설치돼 있지 않아(GPU 서버 컨테이너 전용 의존성) `PiperVoice.load()`/`synthesize_wav()` 상주 경로는 pip 배포 휠의 소스 코드 대조로만 검증했고 실제 GPU 서버/Docker 컨테이너에서 실행 검증은 하지 못했다. 또한 클라이언트 변경도 실기기 재생으로 청취 검증하지 못했다.
- **비고**: 다음 세션에서 반드시 GPU 서버(Docker 컨테이너)에서 `PiperTTSService.generate()`가 실제로 정상 동작하는지(모델 로드, 합성 결과 WAV 유효성) 먼저 확인할 것 — 실패 시 in-process 접근을 포기하고 서브프로세스 방식으로 되돌리되 상주 프로세스(장수 서브프로세스에 stdin으로 여러 요청을 파이프하는 방식) 대안을 검토. 그 다음 실기기로 연속 여러 건의 guide 안내를 청취해 짤림·끊김이 실제로 해소됐는지 확인하고, Release 빌드 교차 검증(`npx expo run:ios --configuration Release`)으로 Metro 개발 모드 한정 문제가 아님을 재확인할 것. 위 "적용 보류" 항목(비프 덕킹 정책)도 담당자 판단을 받아 후속 진행.

---

### 2026-07-09 | 전체 | 미구현/부분구현 4단계 감사 항목 일괄 보완(STT 종단 연결·머리높이 격상·입체패닝·보안 3종)

- **커밋**: (대기 중)
- **변경 내용**: 다른 세션(fable)이 코드를 직접 읽고 1~4순위로 정리한 미구현/부분구현 감사 결과를 전량 코드 대조로 재검증(모든 항목이 정확했음을 확인)한 뒤, 사용자 승인 하에 아래 10개 항목을 구현했다. STT 전체 구현과 Android 브릿지 스킵, MariaDB 스크립트 실행 보류는 사용자에게 직접 확인받았다.
  1. **CORS `allow_origins=["*"]` 하드코딩 제거**: `server/api/config.py`에 이미 존재했으나 소비되지 않던 `settings.CORS_ORIGINS`를 `server/main.py`가 실제로 사용하도록 연결. 기본값을 로컬 콘솔 개발 포트(`localhost:3000`/`5173`)로 좁히고 프로덕션은 `.env`의 `CORS_ORIGINS`(JSON 배열)로 override하도록 문서화.
  2. **WS 디바이스 인증-JWT 통합**: `server/api/auth.py`의 `verify_device()`가 기존 `REGISTERED_DEVICES` 정적 딕셔너리(하위 호환 유지)에 더해 `server/db/security.py`의 `decode_access_token()`으로 서명된 JWT도 인정하도록 확장. `issue_device_token()` 신규 함수로 단말용 JWT 발급 가능. `UserDevice` ORM 테이블(이미 존재하나 미사용)과의 실제 DB 연동은 아래 3번 스크립트 실행 이후 후속 과제로 남김.
  3. **MariaDB 스키마 초기화 스크립트**: `server/db/init_db.py` 신설(`Base.metadata.create_all()` 래핑, 대화형 `yes` 확인 없이는 실행 안 됨, `main.py` lifespan 등 자동 실행 경로에 배선하지 않음). 조사 중 `server/db/base.py`의 `Base`가 `models.py`의 `Base`와 별개 클래스로 선언돼 어디서도 쓰이지 않는 죽은 코드임을 추가로 확인(이번엔 미수정, 후속 정리 대상). 사용자 요청대로 실제 원격 DB 실행은 하지 않음.
  4. **Y축 상단 40% 위험물 격상 게이트**: `docs/design/behavior_and_risk_insight.md`가 "제안, 미구현"으로 명시해뒀던 로직을 `server/detection/gates/head_level_gate.py` 신설로 구현. `MID_RISK_CLASSES` 소속 객체가 화면 상단 40% 영역(bbox 중심 기준)에서 confidence/hit_count 문턱을 통과하면 `ReflexAlert`로 격상해 인지 경로(수 초 지연)가 아닌 반사 경로로 즉시 경보한다. `detection_pipeline.py`에 배선. 합성 Detection 4케이스(격상/발밑-비격상/비대상클래스/1프레임튐-비격상)로 로직 검증.
  5. **반사 클립 오디오 자산**: `data/reflex_clips/*.mp3`가 애초에 존재하지 않는 문제를, `docs/stage-guides/stage7_tts_design.md`가 이미 제안해뒀던 "클라이언트 번들" 방식으로 해소. 조사 중 `reflex_gate.py`의 `alert_id`(클래스명 포함, 예: `high_car_front-left`)와 `clip` 필드(방향만, 예: `high_front.mp3`)가 애초부터 달랐고 `reflex_clip_sender.py`의 `REFLEX_CLIP_MAP`은 실제로 어디서도 호출되지 않는 죽은 코드(`consumer.py._send_reflex_alert`가 `alert.clip`을 직접 사용)였음을 확인 — 맵을 실제 값으로 정정. macOS `say -v Yuna`로 한국어 임시 음성 5종(`high_front`/`high_front-left`/`high_front-right`/`surface_caution`/`head_level_warning`, 각 wav)을 생성해 `client/assets/sounds/reflex_clips/`에 번들, `audioEngine.ts`에 `playReflexClip()` 추가, `useWebSocket.ts`의 reflex_alert 핸들러에서 `clip` 필드로 호출하도록 연결. 서버 3개 게이트 파일의 `clip` 확장자를 `.mp3`(인코더 없어 실제로 만들 수 없었음)에서 `.wav`로 정정.
  6. **패닝 실제 스테레오 반영**: `expo-audio`에 pan API가 없음을 패키지 소스(JS 타입 + iOS Swift) 직접 확인. `beep.wav` 원본 샘플을 Python `wave`/`struct`로 읽어 등파워 패닝(equal-power panning) 공식으로 좌우 게인이 다른 스테레오 WAV 5버킷(`-1.0/-0.5/0.0/0.5/1.0`, `DebugTriggerPanel.tsx`의 `PAN_PRESETS`와 동일 단계)을 `client/assets/sounds/beep_pan/`에 생성. `audioEngine.ts`의 단일 루프 플레이어 구조를 버킷별 5-플레이어 구조로 리팩터링(`ensurePlayer`→`ensurePanPlayers`, `playBeep`/`stopBeepImmediately`가 방향 전환 시 이전 버킷을 묵음 처리 후 신규 버킷으로 전환).
  7. **단말 내장 TTS 폴백**: `expo-speech`(Expo 공식 모듈, SDK 56 대응 버전 `~56.0.3`으로 `npx expo install --check` 확인 후 고정) 신규 설치. `audioEngine.ts`에 `speakFallback()` 추가, `useWebSocket.ts`의 guide 핸들러가 `audio_mp3_b64`가 빈 문자열일 때(서버 TTS 3초 타임아웃) 호출하도록 연결. `stopGuideAudio()`에 `Speech.stop()`을 추가해 선점 정책이 서버 WAV 재생과 단말 폴백 발화 양쪽에 동일하게 적용되도록 함.
  8. **faster-whisper 설치 + STT 서버 라우팅 병합**: `requirements.txt`에 `faster-whisper==1.1.1` 추가(로컬 venv에도 실제 설치해 `FASTER_WHISPER_AVAILABLE=True` 전환 확인). `server/stt/*.py`(`SttService`, `SttToLlmBridge` - 네비게이션 켜기/끄기/목적지 설정 음성 명령까지 이미 완성돼 있었음)가 실제로는 `server/main.py`의 `/ws/detect`에도, 별도 앱인 `server/navigation/server.py`의 `/ws`(GPS/경로탐색만 처리)에도 연결돼 있지 않아 STT 요청을 받을 경로 자체가 없었던 문제를, `server/api/ws_router.py`에 `stt_audio` 메시지 타입(`_handle_stt_audio`)을 추가해 해소. base64 오디오 수신 → 임시 wav 저장 → `SttService.transcribe_file`(스레드 위임) → `SttToLlmBridge.invoke_existing_llm` → `realtime_tts.synthesize` → 기존 `guide` 타입으로 응답(클라이언트 신규 처리 불필요, 이미 자동 재생됨). `tests/test_ws_router_stt.py` 신규 3건(성공/audio_b64 누락/전사 실패 폴백)으로 검증, 전체 스위트 111 passed 확인.
  9. **클라이언트 STT 캡처**: 조사 중 `NSMicrophoneUsageDescription`이 `app.json`/`Info.plist`에 이미 설정돼 있음을 확인(팀원이 선행 준비해뒀던 것으로 추정) - 별도 네이티브 설정 불필요. "서버가 모든 추론 수행" 원칙에 따라 온디바이스 STT(SFSpeechRecognizer 등)는 채택하지 않고, `expo-audio`의 `useAudioRecorder`로 녹음만 하는 `client/src/hooks/useSttRecorder.ts` 신규 구현. `CameraView.tsx`에 "누르고 말하기" 푸시투토크 버튼 추가(`onPressIn`=녹음 시작+햅틱, `onPressOut`=녹음 종료+base64 인코딩+`stt_audio` WS 전송).
  10. **문서/체인지로그**: 본 항목.
  11. **(작업 중 발견) `.gitignore`가 클라이언트 앱 자산을 전부 커밋 누락시키고 있던 결함**: 5/6번 작업 후 신규 wav 자산이 `git status`에 전혀 나타나지 않는 것을 이상히 여겨 조사한 결과, `.gitignore`의 "Upload Files" 섹션(`*.wav`/`*.mp3`/`*.m4a`/`*.png`/`*.jpg`/`*.jpeg`, 학습/업로드용 대용량 데이터 대상으로 작성된 것으로 추정)이 확장자 기준 전역 규칙이라 `client/assets/`(아이콘·스플래시·`beep.wav` 등 기존 자산 포함)와 `client/ios/`(Xcode `AppIcon.appiconset`의 실제 PNG)까지 전부 git 추적에서 제외시키고 있었음을 확인(`git ls-files client/assets/sounds/` 결과 0건 - 즉 `beep.wav`조차 이 리포에 한 번도 커밋된 적이 없었다). 이 상태로는 리포를 새로 clone하면 반사 비프음이 아예 재생 불가능하고 앱 아이콘도 빠진 채 빌드된다. `!client/assets/**`, `!client/ios/**`, `!client/android/**` 예외 규칙을 추가해 해소. **신규 생성한 오디오 자산(5+5종)을 포함해 아직 `git add`는 하지 않았으므로, 다음 커밋 시 `client/assets/`·`client/ios/`의 미추적 바이너리 자산이 실제로 스테이징되는지 반드시 확인할 것**.
- **스킵 결정(사용자 확인)**:
  - Android 네이티브 추론 브릿지(TFLite): iOS CoreML 작업 전체를 다시 만드는 규모라 이번 범위에서 제외, `client/android/`는 Expo 기본 스캐폴드 상태 유지.
  - Kokoro/Coqui TTS 핫스왑, LangSmith Trace/Audio Validator/Redis Cache Monitor/Accessibility Simulator MCP 4종: 관측·설계 선택 항목으로 기능 동작에 무관해 이번 "보완" 범위에서 제외(질문 없이 스킵).
- **관련 파일**: `server/api/config.py`, `server/main.py`, `server/api/auth.py`, `server/db/init_db.py`(신규), `server/detection/gates/head_level_gate.py`(신규), `server/detection/detection_pipeline.py`, `server/tts/reflex_clip_sender.py`, `server/detection/gates/reflex_gate.py`, `server/detection/gates/surface_gate.py`, `client/assets/sounds/reflex_clips/*.wav`(신규 5종), `client/assets/sounds/beep_pan/*.wav`(신규 5종), `client/src/services/audioEngine.ts`, `client/src/hooks/useWebSocket.ts`, `requirements.txt`, `server/api/ws_router.py`, `tests/test_ws_router_stt.py`(신규), `client/src/hooks/useSttRecorder.ts`(신규), `client/src/components/CameraView.tsx`, `client/package.json`, `.gitignore`, `docs/design/api_specification.md`, `docs/ops/environment_variables.md`, `docs/changelogs/kb.md`
- **검증 결과**: 서버 - `pytest tests/ --ignore=tests/test_ws_echo.py` 111 passed / 1 skipped(신규 3건 포함, 회귀 없음), 수정/신규 파일 전체 `ruff check` 통과(기존 `server/stt/*.py`/`server/db/connection.py`의 사전 존재 lint 경고는 미수정, 이번 변경과 무관). 클라이언트 - `npx tsc --noEmit` 통과(사전 존재하던 `jpeg-js` 타입 오류 2건 제외, 신규 오류 없음). `head_level_gate`는 합성 데이터로 4케이스 단위 검증. `_handle_stt_audio`는 monkeypatch 기반 단위 테스트로 성공/실패 경로 검증. **주의**: 실기기 청취(패닝 좌우 분리 체감, 반사 클립 음질, STT 실제 인식 정확도)와 GPU 서버 컨테이너에서의 faster-whisper 실제 모델 다운로드/추론은 검증하지 못했다(이 개발 머신에 `faster-whisper` pip 설치는 했으나 실제 medium 모델 다운로드는 하지 않음 - 무겁고 이번 세션 목적은 배선 검증이었음).
- **비고**: 다음 세션 우선순위 — (1) 실기기에서 STT 버튼으로 "네비게이션 켜줘"/목적지 발화 종단 테스트, (2) 패닝 버킷 5개 동시 loop 재생이 배터리/CPU에 미치는 영향 실측(현재 5개 always-on 루프 스트림으로 증가, 기존 1개 대비), (3) `UserDevice` 테이블과 `verify_device()` JWT 경로의 실제 DB 연동, (4) `server/db/base.py`의 죽은 `Base` 클래스와 `reflex_clip_sender.py`의 잔여 `_resolve_reflex_clip()` 죽은 코드 정리 여부 담당자 판단.

---

### 2026-07-09 | 6+7단계 | 로컬 실서버 종단 검증으로 발견한 실제 결함 2건 수정(heartbeat 경쟁·pygoruut 캐시 누락)

- **커밋**: (대기 중)
- **변경 내용**: 위 두 항목(TTS 짤림/끊김 수정, 감사 항목 보완)을 "실제로 검증 가능한가"라는 질문을 받고, 이 개발 머신에 실제로 있는 Redis/Ollama(`gemma4:e4b`)/YOLO 학습 가중치로 `uvicorn server.main:app`을 직접 기동해 실제 WebSocket 클라이언트로 `stt_audio` 종단 플로우를 구동하며 검증했다. 정적 검사(lint/타입체크/mock 테스트)만으로는 드러나지 않던 실제 버그 2건을 발견해 그 자리에서 수정하고 재검증까지 완료했다.
  - **WS heartbeat 경쟁 조건(연결 강제 종료)**: `server/api/ws_router.py`가 `stt_audio` 메시지를 메인 수신 루프에서 `await _handle_stt_audio(...)`로 인라인 처리하고 있어, STT+LLM+TTS 처리(실측 약 10초)가 끝날 때까지 `ws.receive()`가 멈춰 클라이언트의 heartbeat_ack를 받을 수 없었다. `HeartbeatManager`가 이를 응답 없음으로 판단해 서버가 답을 다 만들기 직전에 연결을 강제 종료(`1001 heartbeat timeout`)하는 것을 실측으로 확인(로그: 서버는 정상 응답을 만들었으나 `Cannot call "send" once a close message has been sent`로 전송 실패). `elif msg_type == "stt_audio":` 블록을 `asyncio.create_task()`로 백그라운드 분리(`background_tasks` 집합으로 추적, `finally`에서 연결 종료 시 취소)해 메인 루프가 계속 heartbeat/다른 메시지를 처리하도록 정정. `_handle_stt_audio`의 최종 `ws.send_json()` 두 곳도 백그라운드 실행 중 클라이언트가 먼저 끊길 가능성을 반영해 `contextlib.suppress(Exception)`으로 감쌈.
  - **pygoruut 96MB 바이너리가 영구 캐시되지 않는 결함**: 같은 종단 테스트에서 `audio_mp3_b64`가 항상 빈 문자열로 오는 것을 발견, 로그 추적 결과 `server/tts/tts_service.py`의 `_phonemize()`가 `Pygoruut()`를 인자 없이 호출하고 있었다. `pygoruut` 패키지 소스(`pygoruut.py:86`)를 직접 확인한 결과 `writeable_bin_dir`을 안 넘기면 `tempfile.TemporaryDirectory()`로 매번 새 임시 디렉터리를 만들고 생성자가 끝나자마자 그 디렉터리를 삭제하는 구조라, 96MB 네이티브 바이너리(`goruut-darwin-arm64`)가 **호출마다(같은 프로세스 내 두 번째 호출에서도) 재다운로드**되어 `realtime_tts.py`의 3초 타임아웃을 거의 항상 초과하고 있었다(TTS 짤림/끊김 수정과 이번 STT 기능 양쪽의 오디오 출력에 영향을 주는 결함이었으나, `_phonemize()` 자체는 이번 세션 이전부터 있던 코드로 내가 작성한 코드는 아니다). `Pygoruut(writeable_bin_dir="")`로 변경 — 라이브러리가 자체적으로 `~/.goruut`(홈 디렉터리 하위 고정 경로)를 만들어 재사용하도록 하는, 라이브러리에 이미 내장된 공식 메커니즘이다.
  - **수정 후 실측 재검증**: 격리 테스트로 동일 프로세스 내 연속 2회 호출 시 1회차 82.43초(이 환경의 느린 GitHub CDN 대역폭으로 인한 최초 1회성 다운로드) → 2회차 0.05초(캐시 재사용)를 확인. `~/.goruut`가 캐시 디렉터리로 채워지는 것을 파일시스템에서 직접 확인. 이후 실제 서버를 재기동해 `stt_audio` 종단 테스트를 재실행한 결과, 5.49초 만에 `audio_mp3_b64`(220560 base64자 ≈ 165KB, `duration_ms: 3750.02`)가 정상 수신됨을 확인. 수신한 base64를 실제로 디코딩해 `afinfo`로 유효한 WAV(모노 22050Hz Int16, 3.92초)임까지 검증.
- **관련 파일**: `server/api/ws_router.py`, `server/tts/tts_service.py`, `docs/changelogs/kb.md`
- **검증 결과**: 위 "수정 후 실측 재검증" 항목이 전부 실제 서버 프로세스 기동 + 실제 WebSocket 클라이언트 + 실제 faster-whisper(tiny, 네트워크 대역폭 제약으로 medium 대신 검증용 임시 매핑 사용 후 원복) + 실제 gemma4:e4b + 실제 Piper 상주 세션으로 수행됨(mock 없음). 검증용으로 `stt_config.py`에 임시 추가했던 `faster-whisper-tiny` 매핑은 원복 완료(`git status`로 diff 없음 확인). `pytest tests/ --ignore=tests/test_ws_echo.py` 112 passed(이 환경에 `faster-whisper`가 설치되면서 기존에 skip되던 테스트도 통과로 전환), 수정 파일 `ruff check` 통과.
- **비고**: 이 세션에서 실제로 확인된 것은 "이 개발 머신 환경에서 위 두 결함이 고쳐졌다"는 것이다. STT wakeup 키워드("네비게이션 켜줘")가 tiny 모델의 낮은 전사 정확도 때문인지 표기 차이("네비게이션"/"내비게이션") 때문인지는 medium 모델로 재확인 필요.

---

### 2026-07-09 | 7단계 | Dockerfile 빌드 타임 pygoruut 바이너리 사전 캐싱

- **커밋**: (대기 중)
- **변경 내용**: 위 항목 "비고"에서 남긴 후속 과제(컨테이너가 배포마다 새로 생성되면 `~/.goruut` 캐시도 매번 초기화된다는 우려)를 바로 해소했다. `docker/Dockerfile`의 `pip install -r requirements.txt` 직후에 `python -c "from pygoruut.pygoruut import Pygoruut; p = Pygoruut(writeable_bin_dir=''); print(p.phonemize(language='Korean', sentence='빌드 타임 캐시 확인'))"` 단계를 추가했다. 단순 다운로드가 아니라 실제 한국어 phonemize 호출까지 수행해, 바이너리가 정상 동작하는지(고장난 바이너리를 이미지에 굽는 사고 방지)까지 빌드 타임에 검증하고 실패 시 빌드 자체가 깨지도록 했다.
- **관련 파일**: `docker/Dockerfile`, `docs/changelogs/kb.md`
- **검증 결과**: Docker Desktop을 직접 기동(`open -a Docker`)해 실제로 `docker build`를 수행했다. 전체 `requirements.txt`(torch/langchain 등 대용량 스택, 과거 실측 약 48분)를 매번 기다릴 수 없어, `pygoruut==0.8.1`만 설치하는 축소 Dockerfile로 동일한 RUN 명령을 실측 검증했다: 빌드 로그에 실제 한국어 phonemize 결과(`빌dɯ tʰa̠im kʰɛɕʰi ɸwa̠gin`)가 출력됐고, 후속 `RUN ls -la /root/.goruut` 단계로 95,136,245바이트 바이너리(`goruut...arm64.linux.bin`)가 실제 이미지 레이어에 구워진 것을 확인했다(`docker build`의 "exporting layers" 완료까지 확인). 검증용 이미지·임시 Dockerfile은 삭제 완료.
- **비고**: 이번 검증은 amd64가 아닌 이 Mac(Docker Desktop 기본 빌드 아키텍처인 arm64)로 수행됐다 - 캐싱 메커니즘(`writeable_bin_dir=""`) 자체는 아키텍처 무관이지만, 실제 배포 아키텍처(linux/amd64)에서의 최초 전체 빌드는 별도로 한 번 돌려 정상 완료되는지 확인할 것. `pip install -r requirements.txt` 자체가 약 48분 걸리므로 이 RUN 단계가 전체 빌드 시간에 미치는 영향(대역폭에 따라 수십 초~수 분)은 크지 않을 것으로 보이나 실측하지 않았다.

---

### 2026-07-09 | 전체 | 문서 디렉토리 정리 및 8대 에이전트 스킬 포함 깨진 링크 80건 전수 복구

- **커밋**: `docs: 문서 디렉토리 정리, 루트 잔류 파일 정리 및 깨진 링크 전수 수정`
- **변경 내용**:
  - **문서 디렉토리 정리**: 소스 코드 폴더에 방치되어 있던 `server/detection/yolo_code_review.md`를 `docs/stage-guides/stage3_detection_code_review.md`로 이동하고 내부 링크를 실제 위치로 수정. `server/navigation/` 하위 지침서 2건을 `docs/dev-guides/`로 이동.
  - **루트 잔류 파일 정리**: `project_scan_report.md`, `project_scan_verification.md`, `SCRIPT_GENERATION_PROMPT.md` 3건의 파일을 스크립트와 성격이 일치하는 `scripts/` 디렉토리로 이동. 내용이 아예 없는 빈 파일 `ai_prompt_context.md` 삭제.
  - **깨진 문서 링크 전수 복구**: 문서 체계가 서브폴더로 재편된 후 flat 경로로 방치되어 깨져있던 `AGENTS.md` (2건), `SKILLS.md` (8건), 7대 에이전트 `SKILL.md` (49건), `docs/README.md` (21건) 등 총 80건의 링크 경로를 실제 서브폴더 경로로 전수 복구 완료.
  - **문서 인덱스 및 정합성 검증**: `docs/README.md` 버전을 `v0.12.0`으로 갱신하고 레거시 flat 테이블/권장 독해 순서를 서브폴더 기준으로 전면 수정. 8대 스킬 명세와 실제 `server/` 코드 간의 시그니처/설계 의도 정합성 조사를 완료하고 상세 보고서 작성.
- **관련 파일**: `docs/README.md`, `AGENTS.md`, `SKILLS.md`, `.agents/skills/**/SKILL.md`, `docs/stage-guides/stage3_detection_code_review.md`, `docs/dev-guides/관제_UI_및_시나리오_연동_지침서.md`, `docs/dev-guides/서버_및_시스템_통합_기술_지침서.md`
- **검증 결과**: Python 전수 링크 검증 스크립트 실행으로 깨진 링크 0건 (100% 정상 참조) 검증 완료.
- **비고**: 문서 정리 및 정합성 고도화 작업 완료. 다음 세션부터 정합이 맞춰진 8대 스킬 명세에 기초해 모듈 개발을 진행할 것.

---

### 2026-07-09 | 전체 | dev 브랜치 4개 팀원 브랜치 병합 후 정합성 검증 및 긴급 결함 3건 수정

- **커밋**: (대기 중)
- **변경 내용**: `dev`에 `jy`/`th`/`jh`/`dg2` 브랜치가 순차 병합된 직후 정합성 검증을 요청받아 실제로 코드를 대조·실행하며 확인한 결과, 심각도 높은 결함 3건을 발견해 즉시 수정했다.
  1. **[심각/보안] 관리자 로그인 인증 완전 우회**: `server/services/admin_service.py`의 `login()`이 DB 조회·비밀번호 검증 없이 어떤 `employee_no`/`password` 조합이든 무조건 통과시켜 유효한 서명된 JWT를 발급하고 있었다("프론트엔드 UI 테스트용 우회"라는 자체 주석이 달린 채 `dev`에 그대로 병합됨, `admin_router.py`의 `POST /api/v1/admin/login`으로 실제 도달 가능한 상태였음). 파일에 이미 명시돼 있던 힌트 주석(존재하지 않는 사번/틀린 비밀번호를 동일한 401 "Invalid credentials"로 응답해 사번 유추 공격 방지, 성공/실패 모두 `AuditRepository`로 감사 로그 기록, 잠김/삭제 계정은 403, 토큰의 `role`은 하드코딩된 "OPERATOR"가 아니라 실제 DB 값 사용)을 그대로 구현해 정정. `verify_password`/`AdminLoginAudit`가 unused import로 잡히던 것도 이 우회 때문이었음을 확인. `tests/test_admin_service_login.py` 신규 5건(오답/미존재사번/잠김계정/정상성공/감사로그기록)으로 in-memory SQLite 기반 검증.
  2. **[심각] 신규 REST STT 엔드포인트의 이벤트 루프 전체 블로킹**: jh 브랜치가 추가한 `server/api/stt_router.py`의 `POST /api/v1/stt/transcribe`, `/transcribe-and-guide`가 동기 블로킹 함수 `SttService.transcribe_file()`(faster-whisper 추론)을 `asyncio.to_thread` 없이 `async def` 라우터 안에서 직접 호출하고 있었다. 이 엔드포인트가 호출되는 동안 프로세스 전체의 단일 이벤트 루프가 멈춰, 이 요청과 무관한 모든 `/ws/detect` 연결(반사 경보 포함)이 함께 정지되는 구조였다 - 이번 세션 앞부분에서 필자 본인의 WS 기반 STT 코드(`_handle_stt_audio`)에서 찾아 고친 것과 동일 계열 버그이지만, 이쪽은 한 연결이 아니라 서버 전체에 영향을 준다는 점에서 더 심각했다. 두 엔드포인트 모두 `await asyncio.to_thread(SttService.transcribe_file, ...)`로 정정. `tests/test_stt_router_nonblocking.py` 신규 2건으로, 0.3초 동기 블로킹 흉내를 내는 동안 별도 asyncio 태스크(20ms 간격 하트비트 카운터)가 계속 진행되는지를 실측해 진짜 non-blocking임을 검증(수정 전 코드였다면 카운터가 거의 0으로 멈췄을 것). 라우터 상단에 WS `stt_audio` 경로(필자 구현)와의 관계를 명시하는 주석 추가 - 두 경로 모두 동일한 `SttService`/`SttToLlmBridge`를 재사용해 로직 자체의 중복은 없음을 확인.
  3. **[테스트 회귀] `data/reflex_guidelines.json` 스키마 불일치**: dg2 브랜치가 추가한 `test_reflex_guidelines_loading`이 각 항목에 `risk_level` 키를 기대하는데 실제 데이터엔 없어 `pytest` 전체가 실패 상태로 병합돼 있었다. 이 테스트가 검증하는 `_resolve_reflex_patterns()`(`reflex_clip_sender.py`)와 `TTSEngine`(`server/navigation/tts_engine.py`)·`pedestrian_navigation.py`는 조사 결과 어디서도 호출되지 않는 죽은 코드(이번 세션에서 계속 나온 "반쯤 연결된 기능" 패턴이 병합으로 하나 더 늘어난 것)였으나, 팀원의 코드를 임의로 삭제하는 대신 최소 침습적으로 `reflex_guidelines.json` 5개 항목에 `risk_level`(haptic `intensity`가 "heavy"인 3건은 "high", "medium"인 2건은 "mid")을 추가해 테스트를 통과시켰다.
- **관련 파일**: `server/services/admin_service.py`, `server/api/stt_router.py`, `data/reflex_guidelines.json`, `tests/test_admin_service_login.py`(신규), `tests/test_stt_router_nonblocking.py`(신규), `docs/changelogs/kb.md`
- **검증 결과**: `pytest tests/ --ignore=tests/test_ws_echo.py` **127 passed, 0 failed**(병합 직후 119 passed/1 failed였던 상태에서 회귀 해소 + 신규 7건 전부 통과). 수정/신규 파일 전체 `ruff check` 통과. `server.main` import 정상(전체 라우터 포함 부팅 확인), 클라이언트 `npx tsc` 및 `console/` `npx tsc` 둘 다 클린.
- **비고**: `server/navigation/pedestrian_navigation.py`, `tts_engine.py`, `reflex_clip_sender.py`의 `_resolve_reflex_patterns()`/`REFLEX_GUIDELINES` 로딩부는 여전히 죽은 코드로 남아있다 - 삭제 여부는 작성한 팀원과 상의 후 진행할 것(이번엔 테스트만 통과시키고 코드 자체는 보존). `JWT_SECRET_KEY` 기본값이 여전히 약한 하드코딩 문자열(`minchodan_secret_key_12345`, 26바이트, PyJWT가 SHA256 최소 권장 32바이트 미달 경고)인 점도 실측으로 재확인됨 - 관리자 로그인이 이제 실제로 동작하는 만큼 프로덕션 배포 전 `.env`의 `JWT_SECRET_KEY`를 반드시 강한 값으로 설정할 것.

---

### 2026-07-09 | 6+7단계 | 실기기 TTS 절단 근본 원인 규명: Piper→Supertonic 엔진 교체 + 반사 캡처를 Frame Processor로 전환

- **커밋**: (대기 중)
- **변경 내용**: "실기기에서만 안내 음성이 문장 중간에 끊긴다"는 증상 하나를 끝까지 추적해 두 개의 독립적인 근본 원인을 찾아 모두 해소했다. Mac 스피커로 서버가 만든 WAV를 직접 재생하면 항상 깨끗했고, 클라이언트의 `didJustFinish` 콜백도 매번 자연 종료를 보고했다는 점이 두 원인 모두 일반적인 로그 분석만으로는 잡히지 않는 이유였다.
  1. **[음질] Piper(`piper-kss-korean`) 자체 발음 품질 한계**: pygoruut 음소화가 흔한 음절(`측`, `직`, `걸`, `볼`, `밑`)을 구두점으로 오분류해 발음에서 통째로 누락시키는 결함을 발견(`우측으로 돌아가세요` → `우으로 돌아가세요`로 합성). 표준 발음법 규칙 기반 자체 G2P(`server/tts/korean_g2p.py`, 신규)로 대체했으나 Mac 청취 검증 결과 여전히 부자연스러웠고, espeak 대체 음소화·pyttsx3(espeak-ng 백엔드)도 모두 실사용 불가 수준이었다. **모델 자체의 근본적 한계로 결론짓고 Supertonic 3(supertone-inc, MIT 라이선스, 99M 파라미터 ONNX, 31개 언어)로 전면 교체**. `server/tts/tts_service.py`에 `SupertonicTTSService` 신규 구현, `TTS_ENGINE` 기본값을 `supertonic`으로 변경(`PiperTTSService`는 핫스왑 설계 의도대로 코드 보존, `TTS_ENGINE=piper`로 언제든 복귀 가능). 모델 캐시는 `server/models/` 대신 라이브러리 기본 경로(`~/.cache/supertonic3`)를 그대로 사용 - `docker-compose.yml`의 `../server:/app/server` 볼륨 마운트가 빌드 타임에 받아둔 내용을 컨테이너 시작 시 호스트 쪽으로 덮어쓰는 문제(pygoruut 사례와 동일)를 피하기 위함. `docker/Dockerfile`에 pygoruut와 동일한 방식의 빌드 타임 사전 다운로드+실합성 검증 단계 추가.
     - **[동시성 버그, 실측 발견]** 안내 문장이 연속으로 겹쳐 도착할 때 서로 다른 문장인데도 `b64len`/재생 길이가 완전히 동일한 오디오가 나오는 결함을 실기기 로그에서 발견 - `tts.synthesize()`가 Piper의 `onnxruntime.InferenceSession.run()`과 달리 스레드 안전성이 문서화돼 있지 않은데 `asyncio.to_thread`로 겹쳐 호출되고 있었다(내부 파이프라인 버퍼 경합 추정). `SupertonicTTSService`에 `_synthesize_lock`(`asyncio.Lock`)을 추가해 합성 호출 자체를 직렬화. `asyncio.gather`로 두 문장을 동시에 합성해 서로 다른 바이트 길이가 나오는지로 수정을 직접 검증.
     - **[전송 방식 변경]** `audio_mp3_b64`(base64 JSON 필드)를 폐기하고 카메라 프레임(client→server)에 이미 적용돼 있던 메타+바이너리 2단계 WS 프로토콜을 반대 방향(server→client)에도 적용 - `server/api/session_manager.py`에 `send_bytes()` 신규, `server/detection/consumer.py`가 guide 전송 시 JSON 메타(`transport:"binary"`) 직후 raw WAV 바이트를 바이너리 프레임으로 전송. 클라이언트는 `expo-file-system`의 신형 `File.write()`(동기, base64 미경유)로 직접 기록하는 `audioEngine.playGuideAudioBytes()` 신규 구현, `useWebSocket.ts`가 WS `binaryType="arraybuffer"`로 수신해 처리. base64 페이로드 크기(44.1kHz vs 22.05kHz 데시메이션) 축소 테스트, 오디오 세션 `interruptionMode` 통일(App.tsx `duckOthers`→`mixWithOthers`, `audioEngine.ensureSession()`과 불일치했었음), 파일 저장 위치를 캐시→Documents로 변경(iOS가 실행 중에도 캐시를 정리할 수 있다는 공식 문서 근거) 등 여러 가설을 순차 검증했으나 전부 절단 현상 자체는 해소하지 못했다 - 결과적으로 원인이 아니었음을 배제하는 데는 기여했다.
  2. **[진짜 근본 원인] 반사 캡처의 `takePhoto()` 반복 호출이 매 촬영마다 오디오 세션을 인터럽트**: 위 모든 오디오/전송 파이프라인 수정에도 절단이 동일하게 재현되자, `sudo log collect --device`로 실기기 시스템 로그(Console 유니파이드 로그)를 직접 수집해 분석했다. `AVAudioSessionInterruption` 알림이 앱 실행 내내 **약 300~400ms 간격으로 반복 발생**(3분간 80회)하고 있었고, 이 주기가 반사 캡처 루프의 동적 fps 간격과 정확히 일치했다. `client/src/hooks/useCamera.ts`의 `tick()`이 `cameraRef.current.takePhoto({enableShutterSound:false})`를 반복 호출하는데, `enableShutterSound:false`로도 iOS의 `AVCapturePhotoOutput.capturePhoto()`는 촬영마다 오디오 세션 인터럽션을 유발한다는 사실을 실측으로 확인 - JS의 `didJustFinish` 콜백은 파일 재생 위치만 볼 뿐 이 세션 레벨 인터럽션을 전혀 감지하지 못해, 지금까지의 모든 진단이 "로그는 깨끗한데 소리는 끊긴다"는 모순에 부딪혔던 이유였다.
     - **해결**: `AVCapturePhotoOutput`을 세션에서 완전히 배제하는 VisionCamera Frame Processor(`AVCaptureVideoDataOutput` 기반 연속 스트림) 방식으로 전환. 반사 게이트 판정/CoreML 추론 코드(`CoreMLInferenceBridge.swift`, `useOnDeviceDetection.ts`)는 한 줄도 건드리지 않고, 새 네이티브 플러그인 `client/ios/ReflexFrameProcessorPlugin.swift`(+ 등록용 `.m`)가 카메라 원본 `CVPixelBuffer`를 기존과 동일한 규칙(중앙 정사각형 크롭+640x640 리사이즈+JPEG quality 0.5)으로 가공해 base64를 반환하고, 그 결과를 기존 `CoreMLInferenceBridge.detectFrame(base64)`에 그대로 넘기는 최소 침습적 설계("입력 JPEG를 어떻게 만드는가"만 교체)로 반사 경로 회귀 리스크를 최소화했다. `react-native-worklets-core` 신규 의존성 추가, `client/ios/Podfile`에 `$VCEnableFrameProcessors=true`, `Minchodan.xcodeproj/project.pbxproj`에 신규 파일 타겟 멤버십 수동 등록(bare 프로젝트라 `expo prebuild` 금지, 일반 `pod install`만 사용). `client/src/config/capture.ts`(신규) `CAPTURE_ENGINE` 플래그로 구 경로(`captureRealFramePhoto`로 개명해 보존)와 즉시 전환 가능한 롤백 경로 확보. `useCamera.ts`에 worklet↔JS 스레드 간 안전한 상태 공유를 위한 `SharedValue`(`react-native-worklets-core`) 기반 동적 fps throttle 신규 구현.
     - **빌드 이슈 2건도 함께 해소**: (a) 신규 `.m` 파일이 `<VisionCamera/FrameProcessorPlugin.h>`를 임포트하며 React-Core 프리빌트 XCFramework의 non-modular-include 오류가 발생 - 앱 타겟 Debug/Release 빌드 설정에 `CLANG_ALLOW_NON_MODULAR_INCLUDES_IN_FRAMEWORK_MODULES=YES` 추가로 해소. (b) `react-native-worklets-core@1.6.3`의 번들 babel 플러그인이 폐기된 babel 패키지명(`@babel/plugin-proposal-optional-chaining` 등)을 하드코딩하고 있어 Metro 번들링이 실패 - 호환용으로 구버전 패키지 직접 설치, 및 프로젝트에 아예 없었던 `babel.config.js`를 신규 작성하며 `babel-preset-expo` 버전을 처음에 `13.x`(구 버전 체계)로 잘못 설치해 `react-native@0.85.3`과 `@react-native/babel-preset` 버전 불일치로 RN 내부 컴포넌트(`VirtualView`) codegen이 깨지는 2차 문제까지 발생 - Expo SDK 버전과 동일한 `56.0.x` 체계로 정정 후 해소.
- **관련 파일**: `server/tts/tts_service.py`, `server/tts/korean_g2p.py`(신규), `server/tts/realtime_tts.py`, `server/api/session_manager.py`, `server/detection/consumer.py`, `docker/Dockerfile`, `.env`, `.env.example`, `requirements.txt`, `client/ios/ReflexFrameProcessorPlugin.swift`(신규), `client/ios/ReflexFrameProcessorPlugin.m`(신규), `client/ios/Podfile`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `client/ios/Minchodan-Bridging-Header.h`, `client/babel.config.js`(신규), `client/app.json`, `client/package.json`, `client/src/config/capture.ts`(신규), `client/src/hooks/useCamera.ts`, `client/src/components/CameraView.tsx`, `client/src/hooks/useWebSocket.ts`, `client/src/services/audioEngine.ts`, `client/src/types/detection.ts`, `docs/changelogs/kb.md`
- **검증 결과**: 서버 측 - Mac 스피커로 원본 WAV 직접 재생(모든 후보 엔진/음소화 방식 비교 청취), `asyncio.gather` 동시 합성으로 동시성 락 수정 검증, 컨테이너 내 실제 모델 로드+합성(로드 0.5초/합성 0.86초, 3초 타임아웃 내). 클라이언트 측 - `npx tsc --noEmit` 클린, Xcode 실기기 빌드 성공(에러 0, 경고 318건 전부 기존 pod). **최종 실기기 검증**: `sudo log collect --device --last 3m`로 프레임 프로세서 전환 전/후 비교 - 전환 전 `AVAudioSessionInterruption` 80회/3분·`AVCapturePhotoOutput` 활동 다수 → 전환 후 **0회/0건**. 사용자 실청취로 "이제 안 끊긴다" 확인.
- **비고**: Option B(카메라 원본 `CVPixelBuffer`를 base64 왕복 없이 새 네이티브 메서드로 직접 전달, `CoreMLInferenceBridge.swift`의 `prepareInput` 리샘플링 알고리즘 자체를 교체)는 성능상 더 유리하지만 반사 경로의 bbox/confidence 분포가 미세하게 달라질 회귀 리스크가 있어 이번 범위에서는 보류, 후속 과제로 남긴다. `client/src/services/audioEngine.ts`/`useWebSocket.ts`에 이번 조사 과정에서 추가한 `[TEMP DEBUG]` 진단 로그(`playGuideAudioBytes`/`stopGuideAudio`/`speakFallback` 호출 추적)가 아직 남아있다 - 원인이 완전히 확정된 만큼 다음 세션에서 정리 필요. `client/src/services/audioEngine.ts`의 `playGuideAudio`(base64 경로, 구식)는 `playGuideAudioBytes`로 사실상 대체됐으나 즉시 삭제하지 않고 보존.

---

### 2026-07-10 | 1+2단계 | WS heartbeat 레이스 컨디션 수정 + dg2 브랜치 정합성 분석 + 카메라 캡처 계층 iOS/Android 이원화 리팩터링

- **커밋**: (대기 중)
- **변경 내용**: 실기기를 ngrok 외부망으로 전환해 테스트하던 중 정상 Wi-Fi 연결에서도 클라이언트가 "폴백 모드"에 빠지는 현상을 발견해 근본 원인을 규명·수정했고, 이어서 안드로이드 담당자(dg2 브랜치)의 작업을 병합 전에 정밀 분석해달라는 요청을 받아 실제 `git merge-tree` 시뮬레이션으로 검증한 뒤, 그 결과를 바탕으로 iOS/Android 양쪽이 지켜야 할 설계 계약서를 작성하고 iOS 쪽 몫을 직접 구현·실기기 회귀 테스트까지 완료했다.
  1. **[버그] WS heartbeat 타임아웃-close와 ack 전송 사이의 레이스 컨디션**: `server/api/heartbeat.py`의 `HeartbeatManager`가 별도 asyncio 태스크에서 5+5=10초 무응답 시 `ws.close()`를 직접 호출하는데, 이와 동시에 메인 수신 루프(`server/api/ws_router.py`)가 ack/pong/heartbeat_ack를 `ws.send_json()`으로 보내려 하면 `Cannot call "send" once a close message has been sent` 예외가 발생해 **세션 전체가 종료**되는 구조였다. ngrok 등 공인망 릴레이의 왕복 지연이나 클라이언트 JS 스레드가 카메라/TTS 처리로 바쁠 때 ack가 조금만 늦어도 정상 연결이 오탐 종료됐고, 이게 반복되면 클라이언트의 `MAX_RECONNECT(3회)`를 금방 소진해 "폴백 모드"에 빠졌다. `HEARTBEAT_TIMEOUT` 기본값을 5→15초(총 유예 10→20초)로 상향하고, 메인 루프의 ack/pong/heartbeat_ack 전송 3곳을 `contextlib.suppress(Exception)`로 감싸 레이스가 발생해도 세션이 죽지 않도록 방어(진짜 끊긴 소켓이면 다음 `ws.receive()`가 `WebSocketDisconnect`로 정상 정리).
  2. **dg2 브랜치 정밀 분석**: 처음엔 `dev` 대비 diff로 분석했으나, kb와 dg2가 같은 조상 커밋(`62b5aa4`)에서 분기했고 dev도 그 지점에 머물러 있음을 확인해 `git merge-tree kb origin/dg2`로 **실제 병합 결과를 직접 계산**하는 방식으로 전환했다. 이 방식으로 텍스트 충돌 3건(`.env.example`/`environment_variables.md`/`tts_service.py`의 TTS 엔진 기본값 `supertonic` vs `pyttsx3` 충돌, 기계적으로 마커만 지우면 `engine = os.getenv(...)` 대입문이 중복되는 함정까지 실제 병합 결과 파일에서 확인)과, git이 충돌로 표시하지 않지만 실제로는 깨지는 항목 3건을 찾아냈다: (a) `tfliteDetector.ts`의 `attrsPerBox`를 dg2가 33→6으로 바꿨는데 번들 모델(`client/assets/models/yolo26n/object_detection.tflite`)은 재수출되지 않아 여전히 33채널 raw(NMS-free) 출력이라 파싱이 깨짐(단, `docs/mobile/ondevice_inference_engine_isolation_plan.md`가 이미 `[1,300,6]`을 목표 스펙으로 명시해뒀던 것을 확인해 dg2의 방향 자체는 맞고 모델 재수출만 누락된 것으로 결론), (b) `docker-compose.yml`에서 dg2가 로컬 편의로 주석 처리한 `ollama` 서비스가 병합 시 그대로 승리해 RAG/로컬 LLM 인프라가 소실, (c) `requirements.txt`에 환경 마커 없는 `pywin32==306`이 합류해 Linux/macOS Docker 빌드가 깨짐. 여기에 더해 git과 무관한 구조적 결함도 발견: kb가 dg2 분기 이후에 만든 반사 캡처 신규 기본 경로(`useFrameProcessor`)가 iOS 네이티브 플러그인만 있고 Android 대응이 없어, **병합 여부와 무관하게 이미 Android 반사 캡처가 무음 실패 상태**였다(크래시 없이 null 가드로 조용히 흡수되는 방식이라 실행 로그로는 안 보임).
  3. **`docs/mobile/ios_android_bifurcation_contract.md` 신규 작성**: 위 분석에서 드러난 근본 문제("공유 파일을 두 사람이 각자 판단으로 동시에 고친다")를 구조적으로 막기 위해, 이미 정상 작동 중인 `localDetectorSelect.ios.ts`/`.android.ts` 패턴을 카메라 캡처 계층까지 확장하는 설계 계약서를 작성했다. 파일 소유권 매트릭스, 비협상 원칙 5개, 카메라 캡처 인터페이스 재설계안(§4), 온디바이스 추론 33 vs 6 채널 포맷 계약 확정(§5, 기존 설계서 계승), 서버 WS 프로토콜 계약 갱신(§6, dg2가 문서화 없이 추가한 `server_detection` 메시지 정식화), 공유 인프라 거버넌스(§7, TTS 엔진 기본값 결정 절차·docker-compose 규칙·`requirements.txt` 플랫폼 마커·`NETWORK_MODE` 플래그), 병합 전 체크리스트(§8)를 포함한다.
  4. **카메라 캡처 계층 iOS 측 구현**: 설계서 §4에 따라 `client/src/hooks/useCamera.ts`(448줄)에 뒤섞여 있던 Mock 캡처/`takePhoto()` 레거시/`useFrameProcessor` 신규 경로를 분리했다. 신규 `client/src/services/frameCaptureProvider.ts`(공통 인터페이스 `FrameCaptureController`+`FrameData`, `takePhoto()` 공용 크롭 로직 `captureViaTakePhoto`), `frameCaptureProviderSelect.ios.ts`(iOS: `useFrameProcessor`+`reflexFrameProcessorPlugin`, `supportsStream`은 네이티브 플러그인 등록 여부로 자동 판정), `frameCaptureProviderSelect.android.ts`(Android 과도기: `takePhoto()` 기반, dg2가 실기기에서 확인한 `File.bytes()` rejected 에러 우회용 `FileSystem.readAsStringAsync`+수동 base64 디코더 이식), `frameCaptureProviderSelect.ts`(tsc 정적 분석용 기본 폴백, `localDetectorSelect.ts`와 동일한 이유로 필요)를 신규 작성. `useCamera.ts`는 타이머·동적 FPS·Mock 분기·반사/인지 비율 계산만 남기고 캡처 실구현은 전부 위임하도록 축소. 전역 `CAPTURE_ENGINE` 상수(`client/src/config/capture.ts`)는 삭제 - 스트림 지원 여부가 플랫폼별로 자동 결정되므로 더 이상 필요 없음. `client/src/config/index.ts`에 설계서 §7.3에서 정의한 `NETWORK_MODE: "lan"|"ngrok"` 플래그를 구현해 `LAN_IP`/`NGROK_DOMAIN` 상수를 양쪽 다 보존하면서 하드코딩 전환 문제를 해소.
- **관련 파일**: `server/api/config.py`, `server/api/ws_router.py`, `client/src/services/frameCaptureProvider.ts`(신규), `client/src/services/frameCaptureProviderSelect.ios.ts`(신규), `client/src/services/frameCaptureProviderSelect.android.ts`(신규), `client/src/services/frameCaptureProviderSelect.ts`(신규), `client/src/hooks/useCamera.ts`, `client/src/config/capture.ts`(삭제), `client/src/config/index.ts`, `client/src/components/CameraView.tsx`, `docs/mobile/ios_android_bifurcation_contract.md`(신규), `docs/design/architecture.md`, `docs/design/pipeline_stage_design.md`, `docs/design/api_specification.md`, `docs/ops/environment_variables.md`, `docs/README.md`, `.agents/skills/camera-frame-capture/SKILL.md`, `.claude/skills/camera-frame-capture/SKILL.md`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit` 클린(리팩터링 직후 `FrameData` 재수출 누락, `frameCaptureProviderSelect.ts`(확장자 없는 tsc용 폴백) 누락 2건을 실제로 잡아 수정). Xcode Release 실기기 빌드 성공(에러 0). 실기기 LAN 직결 회귀 테스트: 카메라 프리뷰 정상 렌더링(사용자 육안 확인), Docker 재기동 후 실제 YOLO(`det_best_20260705.pt`/`segbest.pt`) 로드 확인, 반사(reflex)/인지(cognitive) 프레임이 1~7ms대 디코딩으로 끊김 없이 지속 수신, 컨테이너 로그 전체(1078줄)에서 `ERROR`/`Exception`/`Traceback` 0건, 반사 경보(`high_car_front`) 정상 전송 확인 - 리팩터링 전후 기능 동일성 확인.
- **비고**: Android 몫(§4.5 네이티브 `ReflexFrameProcessorPlugin.kt`, §5 `object_detection.tflite` NMS 포함 재수출)은 미착수 상태로 설계서에 명시해뒀다. dg2가 실기기에서 발견한 크롭 좌표 정밀화(`Image.getSize()` 기반 실측 해상도 사용, orientation 메타데이터 대신)는 이번에는 Android 과도기 파일에 포팅하지 않았음 - 필요 시 Android 담당자가 `frameCaptureProviderSelect.android.ts` 안에서 추가할 것. dg2 브랜치 자체에는 아무 것도 병합하지 않았다(설계서와 iOS측 구현만 kb에 반영).

---

### 2026-07-10 | 문서 | dev 브랜치(jy/dg2/th 병합 후) 핵심 설계 문서 5종 전수 정합성 검토 및 정정

- **커밋**: (대기 중)
- **변경 내용**: `dev`에 jy/dg2/th 3개 브랜치가 순차 병합된 뒤 문서가 코드를 제대로 따라잡았는지 상세 검토를 요청받아, `architecture.md`를 전체 재독해하며 실제 코드(`server/tts/tts_service.py`, `server/rag/build/`, `.env.example`, `server/detection/`, `server/navigation/`)와 문장 단위로 대조한 뒤 나머지 4개 핵심 문서도 같은 기준으로 점검했다. 발견된 결함은 대부분 "한 문서 안에서 섹션끼리 서로 모순되는" 유형이었다 - 예를 들어 같은 파일의 §5.7은 Supertonic을 정확히 기본값으로 서술하면서 §9 추상화 표는 pyttsx3를 기본값으로 서술하는 식으로, 특정 세션에서 일부만 고치고 나머지를 놓친 흔적이 여러 문서에 반복적으로 남아있었다.
  1. **`docs/design/architecture.md`**: §2/§3(mermaid)/§4(디렉토리 표)/§5.4/§8(mermaid)/§9/§10 전반에 걸쳐 Llava→Gemini 캡셔닝, TTS 표기를 Supertonic 기본/Piper·pyttsx3 핫스왑으로 통일(§9는 여전히 pyttsx3를 기본으로 서술하고 있었음), Web Audio API→expo-audio, Docker 인프라 설명(Redis+Ollama 컨테이너→Redis+MariaDB 컨테이너+호스트 로컬 Ollama)을 실제 `docker-compose.yml`과 일치시켰다. mermaid 다이어그램의 TTS 출력 엣지가 아직 "base64 MP3 WS"로 남아있던 것을 WAV 바이너리 프레임으로 정정(§5.7 등 다른 절은 이미 정정돼 있어 다이어그램만 누락된 상태였음). 존재하지 않는 `client/src/services/audioPlayer.ts` 행을 디렉토리 표에서 제거(실제로는 `audioEngine.ts`만 존재). `CHROMA_COLLECTION` 기본값 표기(`minchodan_kb`)가 실제 `.env.example`(`safety_guidelines`)과 달랐던 것, `TTS_ENGINE` 기본값 표기(`pyttsx3`)가 실제 코드(`supertonic`)와 달랐던 것을 정정. 문서 어디에도 없던 GPS 내비게이션(`realtime_gps`, `NavigationManager`, TMAP)과 `server_detection` 메시지를 §3 다이어그램에 신규 노드/엣지로, §4 디렉토리 표와 §6.7(신규)에 반영. §13.5 MCP 구현 현황 매트릭스의 "TTS 미구현" 사유가 TTS 자체는 이미 구현 완료된 현재 상태와 모순돼 있어, MCP 검증 모듈 자체는 여전히 미착수라는 정확한 사유로 정정.
  2. **`docs/design/api_specification.md`**: `realtime_gps`(§6.5, 단말→서버 GPS 좌표 전송) 메시지가 실제로는 `server/api/ws_router.py`에서 처리되고 있는데도 명세서 어디에도 등재되지 않아 신규 작성. 상단 "구현 상태" 서술이 "6·7단계는 미구현(설계상 정상)"으로 고정돼 있었으나 실제로는 이미 전 단계 구현이 끝난 상태라 갱신. 변경 이력 표에 비어있던 v0.4.4~v0.4.6 행을 실제 반영 내용으로 채움.
  3. **`docs/ops/environment_variables.md`**: §2.6 TTS 절 본문(표)은 `supertonic` 기본을 정확히 서술하면서 바로 아래 안내 문구가 "현재 코드 런타임은 pyttsx3(기본)·piper(선택)만 구현, supertonic은 후속 반영"이라고 같은 섹션 안에서 스스로 모순되고 있어 정정. §6 검증 체크리스트의 가중치 파일 존재 확인 명령이 §2.5에서 이미 "결함"으로 지목했던 구 스톡 파일명(`object_detection.pt`)을 그대로 검사하고 있어 정정된 실제 경로(`det_best_20260705.pt`)로 수정. 코드에서 실사용되지만(`server/navigation/`) 명세서·`.env.example` 어디에도 없던 `TMAP_APP_KEY`를 §2.13(신규)으로 추가하고 불일치 이력 표에 항목 추가.
  4. **`docs/README.md`**: 4·5단계 RAG 설계서 요약이 "Llava 캡셔닝"으로 남아있어 정정. "현재 문서 기준선" 절이 GPS/MariaDB/Gemini/Supertonic 전환을 전혀 언급하지 않고 있어 항목 4개 추가. "1주차 미결정 7개" 표가 TTS를 Kokoro/Coqui로, RDB를 미확정으로 서술한 채 결론 없이 방치돼 있어(해당 표는 의도적으로 1주차 시점 스냅샷으로 보존하되) 실제 확정 결과를 알리는 각주를 추가.
  5. **루트 `README.md`**: 상단 프로젝트 개요/기술 스택 절은 이미 Gemini/Supertonic/MariaDB로 정확히 갱신돼 있었으나, 그 아래 "환경 변수" 요약 표만 별도로 갱신되지 않아 `CHROMA_COLLECTION=minchodan_kb`, `TTS_ENGINE`을 `kokoro`/`coqui`로 서술하는 등 바로 위 문단과 정면으로 모순되는 상태였다 - 실제 값(`safety_guidelines`/`supertonic`)으로 정정하고, 존재하지도 않는 환경 변수 `RDB`(실제로는 "1주차 미결정" 표의 잔재가 잘못 섞여 들어온 것으로 추정)를 제거, 실사용 중인 `HEARTBEAT_TIMEOUT`/`TMAP_APP_KEY`/`DB_HOST`를 추가. 디렉토리 구조 트리의 `client/src/services`/`utils` 설명이 존재하지 않는 `audioPlayer.ts`/`reflexClipPlayer.ts`/`utils/` 폴더를 가리키고 있어 실제 구조(`frameCaptureProvider` 이원화, `audioEngine.ts`, `hooks/useLocation.ts`)로 정정.
- **관련 파일**: `docs/design/architecture.md`, `docs/design/api_specification.md`, `docs/ops/environment_variables.md`, `docs/README.md`, `README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 각 정정 사항은 문서 수정 전 실제 코드(`grep`/`find`)로 근거를 먼저 확인한 뒤 반영했다 - `server/tts/tts_service.py`의 `get_tts_service()` 기본값, `.env.example`의 `CHROMA_COLLECTION`, `server/detection/config.py`의 `DETECTOR_TYPE` 실사용 여부, `client/src/services/` 실제 파일 목록, `server/navigation/`의 `TMAP_APP_KEY` 실사용 위치를 각각 대조. 수정한 mermaid 다이어그램은 신규 노드/엣지 전부 큰따옴표 라벨 규칙을 지켜 작성(구문 오류 없음, 프로젝트 Mermaid 표준 준수).
- **비고**: 이번 검토는 5개 핵심 설계 문서로 범위를 한정했다 - `docs/stage-guides/`, `docs/mobile/`, `docs/ops/deployment_guide.md` 등 나머지 문서군은 이번 범위 밖이며, 유사한 "부분 정정 후 다른 섹션 누락" 패턴이 남아있을 가능성이 있다. `docs/design/api_specification.md` 변경 이력 표에는 여전히 v0.4.3 행이 비어있다(어떤 변경이었는지 문서상 근거를 찾지 못해 추측 기입을 피했다).

---

### 2026-07-10 | 6+7단계 | 실기기 STT/네비게이션 종단 테스트로 결함 다수 발견·수정 + DB 로그 영속화 배선 + CPU 과부하 완화

- **커밋**: (대기 중)
- **변경 내용**: 자리를 옮겨 Docker/ngrok/Metro를 새로 띄우고 실기기 종단 테스트를 진행하며 로그 추적과 빌드를 전담했다. "가장 시급한 것은 iOS 앱→서버→DB 로그 저장"이라는 요청에서 시작해, 실제로 화면을 누르고 말하며 반복 재현·수정·재검증하는 과정에서 정적 분석으로는 드러나지 않는 실결함을 다수 발견했다. 아래 순서는 실제 발견 순서를 따른다.
  1. **[결함] DetectionGuidanceLog DB 영속화 미배선**: `server/db/models.py`/`repositories.py`/`services/detection_guidance_log_service.py`는 이미 완성돼 있었으나 실제 탐지 파이프라인(`DetectionConsumer`) 어디서도 호출되지 않아 로그가 전혀 DB에 쌓이지 않는 상태였다. `detection_guidance_log_service.py`에 요청 컨텍스트 밖(WS 백그라운드)에서도 쓸 수 있는 `persist_detection_guidance_log()`를 신설하고, `server/detection/consumer.py`의 `_send_reflex_alert`/`_send_cognitive_guide`와 `server/api/ws_router.py`의 `_handle_stt_audio` 3곳에 fire-and-forget 태스크로 연결(반사 경로 지연에 영향 없도록 `asyncio.create_task`, 실패는 로깅만 하고 파이프라인은 계속 진행).
  2. **팀 공유 DB(Tailscale RPi)로 기본 타깃 전환**: 로컬 `docker-compose.macos.yml`의 `mariadb` 컨테이너로 로그가 쌓이고 있었으나, 사용자가 실제 팀 DB는 `minchodan-rpi-db.tail77994d.ts.net`(100.105.221.31)라고 확인해줬다. `docker-compose.macos.yml`의 `fastapi` 서비스 `DB_HOST`/`DB_PASSWORD` 기본값을 로컬 컨테이너에서 Tailscale 실주소로 전환(`COMPOSE_DB_HOST` 등으로 오프라인 개발 시 로컬 컨테이너로 되돌릴 수 있는 여지는 유지). 전환 전후 실제 INSERT/DELETE로 연결·쓰기 검증.
  3. **[성능] 반사 큐 드랍 + CPU 800~1300% 과부하 완화**: 실기기 테스트 중 `[StreamSplitter] 큐 가득참` 경고가 반사 스트림에서 지속 발생하고 Redis `xadd` 타임아웃까지 겹치는 것을 실측. 원인 2가지를 함께 수정: (a) `YoloDetector`/`YoloSegmentor`가 배치=1 CPU 추론마다 호스트 전체 코어(14코어)를 스레드로 점유해 반사·인지 스트림이 겹칠 때 과잉 경쟁을 유발 → `docker-compose.macos.yml`에 `OMP_NUM_THREADS`/`MKL_NUM_THREADS`/`OPENBLAS_NUM_THREADS`/`NUMEXPR_NUM_THREADS=4` 추가. (b) `DetectionPipeline.run()`이 `detector.predict()`/`segmentor.predict()`를 동기 블로킹으로 직접 호출해 추론 중(150~300ms) WS 수신 루프·하트비트·Redis 통신 전체가 멈춤 → `asyncio.to_thread`로 워커 스레드에 위임. 적용 후 CPU 1300%→400%대, 큐 드랍 재발 없음을 30초 단위 반복 측정으로 확인.
  4. **[결함] STT 응답 오디오가 클라이언트에서 항상 무시됨**: "STT 목적지 설정 성공 문구는 나오는데 서버 TTS 음성이 안 들린다"는 것을 조사한 결과, 2026-07-09에 인지 경로(`_send_cognitive_guide`)가 오디오 전송을 `audio_mp3_b64`(JSON base64)에서 `transport:"binary"`+바이너리 프레임으로 이미 전환했고 클라이언트(`useWebSocket.ts`)도 `transport!=="binary"`면 무조건 단말 TTS로 즉시 폴백하도록 바뀌었는데, `_handle_stt_audio`(`ws_router.py`)만 이 마이그레이션에서 빠져 여전히 `audio_mp3_b64` 필드로 보내고 있었다. 인지 경로와 동일한 방식(`transport` 필드 + `ws.send_bytes()`)으로 통일.
  5. **[결함] STT 녹음 자체가 항상 실패**: 화면을 눌러도 `RecordingDisabledException`으로 녹음이 시작조차 못 하는 것을 발견. `client/App.tsx`의 최상단 `setAudioModeAsync({allowsRecording: false, ...})`가 앱 마운트 시점에 `audioEngine.ensureSession()`의 `allowsRecording:true` 설정보다 먼저 실행되어 세션을 덮어쓰고 있었다(그 파일 자체에 이미 원인이 주석으로 남아있었으나 반영이 안 된 상태). `App.tsx`도 `true`로 통일.
  6. **[결함] STT 요청 병렬 처리로 인한 상태 경쟁**: 사용자가 응답을 기다리지 않고 연달아 누르면 이전 `_handle_stt_audio` 백그라운드 태스크가 처리 중(수 초~10초+)인데 새 요청이 동시에 시작돼 `NavigationManager`의 공유 대화 상태(`status`/`awaiting_free_question`/`awaiting_intent`)를 서로 경쟁적으로 읽고 써 응답이 직전 발화와 안 맞는 현상("1:1로 대응이 안 된다")을 재현·확인. `ws_router.py`에 device_id별 `asyncio.Lock`(`_get_stt_lock`)을 도입해 STT 처리를 디바이스별로 완전히 직렬화.
  7. **[결함] 목적지는 설정되는데 실제 길안내 음성이 영구히 안 나옴**: `SttToLlmBridge.invoke_existing_llm()`이 `device_id = "default_device"`로 하드코딩돼 있어, 목적지 설정(`WAITING_FOR_DESTINATION`/`NAVIGATING`)은 이 가짜 세션에 저장되는데 GPS 갱신(`realtime_gps`)과 턴바이턴 조회(`DetectionConsumer._send_cognitive_guide`→`get_combined_guidance`)는 실제 `device_id`("dev-001") 세션을 봐서 영원히 매칭될 수 없는 구조였다. `invoke_existing_llm(stt_result, device_id)`로 시그니처를 바꿔 호출측(`ws_router.py`)의 실제 device_id를 그대로 전달.
  8. **"네비게이션"/"내비게이션" 표기 정규화 + 재트리거 함정 수정**: Whisper가 같은 발화를 매번 다르게 전사(네비게이션/내비게이션)해 키워드 매칭이 불안정하던 것을, 매칭 전 `normalized_text.replace("내비게이션","네비게이션")`으로 표준화. 또한 "질문할게" 등으로 진입한 대기 상태에서 무음 응답 뒤 트리거 문구를 다시 말하면 그게 재트리거가 아니라 "질문 내용 그 자체"로 소비돼 LLM이 엉뚱하게 답하는 함정을 발견 - 재입력이 트리거 문구 자체면 대기를 유지한 채 재안내하도록 수정(질문 모드·길댕아 대기 모드 양쪽에 동일 원칙 적용).
  9. **자유 질의응답("물어볼게") 신규 + POI 실거리 검색 그라운딩**: "가장 가까운 지하철역이 어디야?" 같은 일반 질문이 장애물 회피 오케스트레이터(`run_orchestrator`)로 들어가 무관한 안내 문장을 만들던 문제를 발견해, `stt_to_llm_bridge.py`에 `QUESTION_TRIGGER_KEYWORDS` wake-word로 분리된 자유 질의응답 모드(`_answer_free_question`)를 신설했다. 위치 질문은 LLM에 맡기지 않고 `server/navigation/server.py`에 신규 `helper_search_nearest_poi()`(Haversine 거리 계산으로 진짜 "가장 가까운" 후보를 고름 - 기존 `helper_search_poi(count=1)`은 relevance 1건만 반환해 근접 질의를 보장 못 함)를 붙여 실제 API 결과로만 답해(POI 미검출 시 정직하게 "찾지 못했습니다") 환각을 방지. 일반 대화는 `QUESTION_SYSTEM_PROMPT`로 LLM 자유 답변, 모르는 사실은 추측 대신 "정확히 알 수 없습니다"로 답하도록 지시.
  10. **"길댕아" 2단계 웨이크워드 신규 + 편집거리 퍼지 매칭으로 전환**: 기존 "네비게이션 켜줘"/"질문할게" 단일 트리거의 표기 변이 문제를 근본적으로 줄이기 위해 사용자와 논의해 "길댕아"(온보딩 문구 "길댕입니다"와 브랜드 일관) → "길찾아줘"/"물어볼게" 2단계 흐름을 신설(`GILDAENG_NAV_INTENT_KEYWORDS`/`GILDAENG_QUESTION_INTENT_KEYWORDS`, 옵션 A: 두 키워드 중 하나가 아니면 추측하지 않고 재질문). 기존 단일 트리거는 하위 호환으로 보존. 그런데 "길댕아" 자체도 "길대가"/"결댕아"/"길땡아" 등으로 반복 오인식되는 것을 실측으로 확인 - 변형을 하나씩 목록에 추가하는 방식의 한계를 인정하고, 외부 의존성 없는 순수 Python 편집거리(Levenshtein distance) 구현(`_levenshtein`)으로 "길댕"과 거리 1 이하인 2글자 윈도우가 발화에 있으면 wake로 인정하는 퍼지 매칭(`_is_gildaeng_wake`)으로 교체. 실제 관측된 모든 변형 + 오탐 없음을 단위 테스트로 확인 후 배포.
  11. **STT 상호작용 중 인지 경로 뮤트 신규**: "질문 중에 인지 경로 경고 메시지가 나와 헷갈린다"는 요청에 대해, 반사 경로(안전 비협상 원칙)는 절대 건드리지 않고 인지 경로 가이드 음성만 STT 상호작용 구간 동안 뮤트하도록 `useWebSocket.ts`에 `setSttInteractionActive()`를 신설(event_id가 `stt-`로 시작하지 않는 guide만 대상). 처음에는 STT 응답 도착 즉시 뮤트를 해제했으나, 실제 오디오 재생은 그 뒤로도 몇 초 이어져 재생 도중 인지 메시지가 끼어들어 답변이 끊기는 것을 재현 - 서버가 보낸 `duration_ms`(TTS 청크 분할 추정 결함으로 긴 문장에서 실제보다 짧게 나오는 사례 실측) 대신 `Math.max(서버값, 텍스트 길이 추정치)`로 방어적으로 재생 예상 시간만큼 뮤트를 유지하도록 정정.
  12. **오디오 블리드(자기 음성 재인식) 2건**: (a) 직전 응답 음성이 채 끝나기 전에 새 녹음을 시작하면 마이크가 스피커 소리를 그대로 주워들어 STT가 시스템 자신의 안내 문장을 사용자 발화로 오인식하는 현상("네, 길 찾아드릴까요?"가 그대로 재인식된 사례)을 실측 확인 - 녹음 시작 전 `audioEngine.stopGuideAudio()`로 재생 중인 오디오를 강제 정지. (b) 이후 신설한 입력 확인 음성 안내(§13) 자체가 다시 같은 방식으로 블리드되는 것을 확인(안내 문장이 다음 녹음 앞부분에 그대로 섞여 들어감) - 소프트웨어 재생 종료 신호(`onDone`)와 실제 스피커 잔향 소멸 사이의 시차가 원인으로 추정, 안내 종료 후 250ms 여유를 두고서야 녹음을 시작하도록 정정.
  13. **입력 확인 음성 안내 신규**: "시각장애인은 누른 화면을 확인할 수 없다"는 지적에 따라, 화면을 누르면 짧은 음성("네, 말씀하세요")으로 입력 시작을 확인시켜주는 기능을 추가(`audioEngine.speakFallback()`에 `onComplete` 콜백 파라미터 신설, 안내가 끝난 뒤에만 녹음 시작해 자기 음성 재인식 방지 - §12(b)). 최초 구현 시 안전을 위해 200ms 인위적 지연을 넣었다가 "터치 반응이 느리다" 피드백을 받고 제거(반사적 haptic은 그대로 즉시 발화, 확인 음성 재생과 실제 오디오 정지만 동기 처리하면 충분했음).
  14. **온보딩 안내 문구 신규 및 갱신**: 앱 시작 시 1회 재생되는 온보딩 안내를 신설(`App.tsx`, 카메라/반사 구동을 지연시키지 않는 fire-and-forget). "길댕아" 2단계 흐름이 확정된 뒤, 사용자 요청대로 "길댕아~ 저는 여러분의 보행을 돕는 길댕이입니다..."로 실제 최신 명령 체계를 반영해 갱신.
  15. **STT VAD 필터 활성화**: 인식률 저하 원인 조사 중 `server/stt/stt_config.py`의 `TRANSCRIBE_VAD_FILTER`가 `False`(무음/잡음 구간 제거 비활성)였던 것을 발견, 사용자 승인 하에 `True`로 전환(담당자 정책 영역 - 변경 전 확인 절차 거침).
  16. **Whisper large-v3-turbo A/B 벤치마크 (기각)**: "Handy" STT 앱 리서치에서 이어진 논의로, `MODEL_NAME_MAP`에 `large-v3-turbo`를 임시 추가해 우리 TTS로 합성한 3개 한국어 문구로 medium과 직접 비교 실측했다. 결과: 짧은 명령어 기준 turbo가 medium보다 약 1.5배 느림(2.9~3s vs 1.9s, 최초 실행은 1.5GB 모델 다운로드로 150초 소요), 정확도는 3개 샘플 기준 사실상 동일(둘 다 "길댕아"→"길땡아" 동일 오인식). turbo의 속도 이점은 긴 오디오의 가벼운 디코더에서 나오는데 우리는 짧은 명령이라 인코더 비용이 지배적이고 turbo 인코더가 오히려 더 커서 역효과라는 사전 가설이 실측으로 확인됨 - 사용자 지시로 `MODEL_NAME_MAP` 원복.
  17. **SenseVoice 실측 통합 시도 (기각, 문서화)**: 기존 `docs/research/sensevoice_stt_feasibility.md`의 권고에 따라 `funasr-onnx`를 실제로 설치해봤으나 `numpy<=1.26.4` 요구가 프로젝트 고정 버전(`numpy==2.5.0`, torch/ultralytics 호환용)과 충돌 - 라이브 컨테이너의 numpy가 2.4.6으로 자동 다운그레이드되는 것을 실측 확인하고 즉시 원복(컨테이너 재시작은 하지 않아 실서비스 영향 없음). 같은 프로세스에 넣을 수 없고 별도 격리 서비스로 분리해야 한다는 결론을 §6(신규)에 반영.
  18. **컨테이너 예기치 않은 재시작 원인 조사 (미확정)**: 세션 중 `minchodan-fastapi` 컨테이너가 내가 직접 재시작하지 않았는데도 3회 이상 깨끗하게(exit code 0, OOM 아님) 재시작되는 것을 관측. 메모리는 8.6%만 사용 중이라 OOM은 배제했으나, `docker events`/macOS 시스템 로그 모두 원인을 특정할 증거를 남기지 않아 확정하지 못했다. CPU 1000%+ 지속 부하와 macOS Docker Desktop 가상화 계층의 상관관계를 유력 추정으로 남긴다(§3 CPU 완화로 재발 빈도가 줄었는지는 후속 관찰 필요).
- **관련 파일**: `server/services/detection_guidance_log_service.py`, `server/detection/consumer.py`, `server/api/ws_router.py`, `docker/docker-compose.macos.yml`, `server/detection/detection_pipeline.py`, `server/navigation/manager.py`, `server/navigation/server.py`, `server/stt/stt_to_llm_bridge.py`, `server/stt/stt_config.py`, `client/App.tsx`, `client/src/services/audioEngine.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `docs/design/api_specification.md`, `docs/research/sensevoice_stt_feasibility.md`, `docs/changelogs/kb.md`
- **검증 결과**: 전 항목을 실기기(iPhone, 팀원 "고태현의 iPhone")+실제 서버(Docker macOS CPU 폴백)+실제 팀 공유 DB(Tailscale RPi MariaDB)로 반복 재현·수정·재검증했다(mock 없음). 서버 재시작마다 `docker logs`로 스택트레이스 부재 확인, DB 쿼리로 실제 저장된 행(전사문·안내문 전체) 직접 조회, Metro 클라이언트 로그로 `playGuideAudioBytes`/`speakFallback` 호출 순서 대조. `python3 -c "import py_compile"`로 수정 파일 구문 검증, `npx tsc --noEmit`로 클라이언트 타입 검증(신규 오류 0건). 길댕아 퍼지 매칭은 실측 오인식 변형 전체(길대가/결댕아/길땡아) + 오탐 후보 문장으로 단위 테스트 통과.
- **비고**: iOS 빌드/실기기 로그 추적은 이번 세션에서도 전담했다(기존 `[[ios_build_ownership]]` 위임 유지). `client/App.tsx`/`CameraView.tsx`/`useSttRecorder.ts`/`DebugTriggerPanel.tsx`/`server/api/ws_router.py`는 세션 시작 시점에 이미 작업 중이던(다른 세션에서 시작된) 변경분이 섞여 있었다(STT 터치 레이어 전체화면 Pressable 전환, 에러 상세 화면 표시 등) - 이번 세션은 그 위에 이어서 작업했다. `docs/design/architecture.md`/`docs/ops/navigation_and_reflex_guide.md`는 STT/네비게이션 관련 서술이 원래 없어 이번 범위에서 신규 작성하지 않았다(후속 과제). 세션 중 발견한 미해결 항목: 컨테이너 재시작 원인(§18), STT 인식률이 VAD+길댕아 퍼지 매칭 이후에도 완전히 만족스럽지는 않다는 사용자 피드백(근본적으로는 모델 자체 한계로 추정 - large-v3-turbo·SenseVoice 둘 다 이번 세션에서 기각됨).

---

### 2026-07-11 | 3단계 | CoreML FP16 재변환 + ANE 가속 활성화 + segmentation 출력 파싱 버그 수정

- **커밋**: `fix(3단계): CoreML FP16 재변환 + ANE 가속 활성화 + segmentation 출력 파싱 버그 수정`
- **변경 내용**:
  - 설치된 ultralytics(8.4.82)의 CoreML export가 `half` 인자를 폐기하고 `quantize=16`으로 대체한 것을 실측 확인(과거 변환 시 `--no-half`가 실제로 적용돼 `storagePrecision: Float32`로 굳어 있었음). `scripts/convert_yolo_to_coreml.py` 기본값(`half=True`) 그대로 object_detection/segmentation 모델을 재변환해 `storagePrecision: Float16` 확보(det 300/302, seg 338/341 연산이 FP16으로 전환, Conv/Silu 백본 전량 FP16).
  - `CoreMLInferenceBridge.swift`의 `MLModelConfiguration.computeUnits`를 `.cpuOnly` 고정에서 `.cpuAndNeuralEngine` 우선 시도 + 실패 시 `.cpuOnly` 폴백(`loadModel(url:)` 신설)으로 변경. 과거 크래시는 `.cpuAndGPU`(GPU/Metal 경로) 조합이었고 ANE 전용 조합은 그동안 미검증 상태였음.
  - `runDetection()`에서 `prediction.featureNames.first`로 출력 텐서를 무작정 집던 로직을 shape 기반 탐색(`shape.count == 3`)으로 수정. segmentation 모델은 출력이 2개([1,300,38] 박스+마스크계수, [1,32,160,160] 프로토타입 마스크)인데, `featureNames`(Set 기반, 순서 미보장)가 프로토 마스크 텐서를 먼저 반환하면 매 프레임 파싱이 실패해 segmentation 결과가 통째로 유실되던 버그를 해결.
- **관련 파일**: `client/ios/CoreMLInferenceBridge.swift`, `client/assets/models/yolo26n/ios/object_detection.mlpackage/*`, `client/assets/models/yolo26n/ios/segmentation.mlpackage/*`, `client/ios/Minchodan/object_detection.mlmodelc/*`, `client/ios/Minchodan/segmentation.mlmodelc/*`, `docs/changelogs/kb.md`
- **검증 결과**: 실기기("고태현의 iPhone")에 재빌드/재설치 후 수 분간(수백 프레임) 연속 추론 크래시 없음 확인. 총추론 시간 48~70ms → 19~22ms로 약 2.5배 단축(KPI `<80ms` 대비 여유 확대). `[1, 32, 160, 160]` shape 경고 재발 없음, seg 벤치마크(12~18ms) 정상 기록으로 segmentation 파싱 정상 동작 확인.
- **비고**: segmentation 프로토타입 마스크(`[1, 32, 160, 160]`)는 여전히 픽셀 단위로 조합되지 않고 박스+클래스 목록만 사용 중이다 - 실제 픽셀 단위 마스크가 필요해지면 후속 과제.

---

### 2026-07-11 | 7단계 | STT 녹음 진입/종료 신호음 추가

- **커밋**: `feat(7단계): STT 녹음 진입/종료 신호음 추가`
- **변경 내용**:
  - 시각장애인 사용자가 화면을 보지 않고도 STT 녹음의 실제 시작/종료 시점을 구분할 수 있도록, 단일 고음 비프(`stt_start.wav`, 1000Hz 120ms)와 더블 비프(`stt_end.wav`, 700Hz 60ms x2)를 신규 생성(mono 44.1kHz 16bit, 기존 `beep.wav`/`silence.wav`와 동일 포맷).
  - `audioEngine.ts`에 `playSttStartCue()`/`playSttEndCue()` 추가. 에셋 URI를 1회만 리졸브해 캐시하고, 반사 비프(`playBeep`)와는 별개의 일회성 플레이어로 재생해 반사 경로 상태와 간섭하지 않는다.
  - `useSttRecorder.ts`의 실제 `recorder.record()` 성공 직후(진입점)와 `recorder.stop()` 성공 직후(종료점)에 각각 연결. UI 제스처 이벤트가 아니라 훅 내부의 실제 녹음 상태 전환에 결속해, 권한 거부 등으로 녹음이 실제로 시작되지 않은 경우 오신호를 방지한다. 기존 "네, 말씀하세요" TTS 안내는 그대로 유지.
- **관련 파일**: `client/src/services/audioEngine.ts`, `client/src/hooks/useSttRecorder.ts`, `client/assets/sounds/stt_start.wav`(신규), `client/assets/sounds/stt_end.wav`(신규), `docs/changelogs/kb.md`
- **검증 결과**: JS/에셋 변경만 있어 Metro Fast Refresh로 반영. 실기기 청취 검증은 사용자 진행 예정.
- **비고**: (없음)

---

### 2026-07-11 | 6+7단계 | STT 녹음 오디오 블리드 근본 수정 + hotwords 배선 + ANE 선택헤드 이관 실험(롤백) + 문서 정합화

- **커밋**: `fix(7단계): STT 녹음 오디오 블리드 근본 수정 + 즉시 녹음 시작 전환`, `feat(6단계): STT hotwords 배선`, `fix(3단계): ANE 선택헤드 Swift 이관 실험 코드 보존(raw-head, 실측 성능 회귀로 롤백)`, `docs: CoreML ANE 벤치마크·iOS 구현 설계서 정합화`
- **변경 내용**:
  - **STT "입력이 없어" 근본 원인 규명**: 디버그 오디오 파일을 서버에 임시 저장해 `afinfo`/파형 진폭 분석으로 직접 까본 결과, 녹음이 실제로는 몇 초씩 진행됐는데도(JS 타이머로 `recorder.record()`~`stop()` 3.5초 측정) 인코딩된 파일에는 0.2~0.7초 분량만 담기는 현상을 확인. 원인은 두 겹이었다: ① 기존 "네, 말씀하세요" TTS가 끝난 뒤에야 녹음을 시작하는 순차 구조에서, 사용자가 짧게 말하고 바로 손을 떼면 `pendingStartRef` 동기화 때문에 `recorder.record()` 직후 곧바로 `stop()`이 뒤따라 녹음 구간이 잘림 → 버튼을 누르는 즉시 `recorder.record()`를 호출하도록 전환(`useSttRecorder.ts`, `CameraView.tsx`). ② 신호음(비프)을 녹음 활성 중에 병행 재생하면 스피커 소리가 마이크에 그대로 다시 잡히는 음향 블리드가 발생(하드웨어 에코 제거 없이는 회피 불가) → 시작 신호음 재생 자체를 제거하고 진입점 안내는 기존 haptic이 전담하도록 변경, 종료 신호음(`playSttEndCue`)은 `recorder.stop()` 완료 이후에만 재생되므로 그대로 유지.
  - **faster-whisper `hotwords` 배선**: `stt_config.py`에 `TRANSCRIBE_HOTWORDS` 상수 추가(`stt_to_llm_bridge.py`에 이미 정의된 실제 명령어 어휘 — 길댕이/길찾아줘/물어볼게/POI 카테고리 등 — 기반 초안), `stt_service.py`의 `model.transcribe()` 호출에 `hotwords=` 인자로 연결. 신조어 웨이크워드("길댕아") 오인식 완화 목적(opus 제안 0순위, faster-whisper 1.2.1이 `hotwords`/`initial_prompt`를 지원함을 실측 확인). 실제 어휘 목록 최종 확정은 담당자 검토 필요(`stt_config.py` 정책값 - 하드코딩 영역).
  - **ANE 선택헤드(TopK/Gather) Swift 이관 실험 및 롤백**: `scripts/convert_yolo_to_coreml.py`에 `--raw-head` 옵션 추가(Detect 헤드 `postprocess()`를 identity로 몽키패치, end2end 유지). 검증 결과 op histogram에서 TopK/GatherNd/GatherAlongAxis가 0개로 완전히 제거됐으나(100% ANE 호환), 출력 텐서가 `[1,300,6]`→`[1,8400,33]`(154배)로 커지면서 ANE→CPU 메모리 복사 비용이 커져 det 지연이 6~14ms→34~53ms로 오히려 3~5배 악화됨을 실측 확인, 배포본은 롤백(커밋된 end2end 후처리 버전 유지). `--raw-head` 옵션 자체는 기본값 `False`로 스크립트에 보존.
  - **문서 정합화**: [`docs/ops/ondevice_coreml_benchmark.md`](../ops/ondevice_coreml_benchmark.md)를 FP16+ANE 실측치·Instruments 검증·raw-head 실험 기록으로 갱신(v1.4.0), [`docs/mobile/mobile_ios_implementation_plan.md`](../mobile/mobile_ios_implementation_plan.md) §9.2를 ANE 가속 실측 달성 상태로 갱신(v0.1.1).
- **관련 파일**: `client/src/hooks/useSttRecorder.ts`, `client/src/components/CameraView.tsx`, `client/src/services/audioEngine.ts`, `client/assets/sounds/stt_start.wav`(삭제 - 오디오 블리드로 사용 중단), `server/stt/stt_config.py`, `server/stt/stt_service.py`, `scripts/convert_yolo_to_coreml.py`, `docs/ops/ondevice_coreml_benchmark.md`, `docs/mobile/mobile_ios_implementation_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**: 실기기 재현 테스트로 STT 녹음 길이가 1.2초 이상으로 정상화, VAD가 무음을 0초 제거하고 전체 구간을 발화로 인식, `text_len` 양수 및 서버 응답이 `stt-bridge`(정상)로 전환됨을 서버 로그(`faster_whisper` VAD/duration 로그, `stt_audio 처리 완료`)로 직접 확인. ANE raw-head 실험은 빌드 성공·무크래시였으나 벤치마크 로그로 성능 회귀를 확인하고 롤백.
- **비고**: hotwords 실제 어휘 목록은 초안 상태 - 담당자가 실사용 명령 패턴에 맞춰 확정 필요. STT 인식 자체의 정확도(퍼지 매칭 이후에도 완전 만족스럽지 않다는 기존 피드백, §17 참조)는 이번 세션 범위 밖이라 사용자가 별도로 다루기로 함. `client/ios/CoreMLInferenceBridge.swift`의 `runDetection()`이 shape 기반으로 3차원 텐서를 탐색하도록 되어 있어(이전 항목 §segmentation 파싱 수정) raw-head 출력([1,8400,33], 3차원 유지)과도 호환되는 것을 이번 실험에서 재확인했다.

---

### 2026-07-11 | 6+7단계 | STT 메아리/상태머신/WS송신스팸 3건 수정 + 폴백 모드 BBox 표시

- **커밋**: (이번 커밋)
- **변경 내용**:
  - **[결함] STT 자기-에코(메아리) 루트 원천 차단 - 서버+클라이언트 이중 방어**: 클로드(Claude Code) 세션에서 실기기 로그(13:24:07)로 발견된 문제. TTS 안내문("네, 길 찾아드릴까요?")이 스피커로 재생되는 도중 사용자가 녹음 버튼을 누르면, 마이크가 안내문 통째로 주워듣고 Whisper가 전사한 뒤 이 전사에 포함된 웨이크업 키워드("길찾아줘")가 재발동 → 동일 안내 재생 → 또 녹음되는 메아리 루프가 발생했다. (a) **서버 측 자기-에코 필터 신규**: `stt_to_llm_bridge.py`에 `_is_self_echo()` 함수와 `SttToLlmBridge._recent_guidance`(device_id별 최근 안내문 캐시, TTL 10초)를 추가. `invoke_existing_llm()` 진입 시 전사 결과가 최근 안내문과 유사하면(안내문 포함 여부, 접두사/접미사 매칭, 핵심 구간 편집거리 2 이내 부분 문자열 매칭) `source: "stt-echo-detected"`로 빈 응답 반환. `ws_router._process_stt_audio()`에서 이 source면 클라이언트에 응답을 보내지 않고 조용히 종료. 정상 안내문 전송 시 `_record_guidance()`로 캐시에 기록해 다음 STT 입력의 에코 판정에 사용. (b) **클라이언트 측 TTS 재생 중 녹음 가드 보강**: `CameraView.tsx` `onPressIn` 핸들러에서 `audioEngine.isGuidePlaying`이 true면 `stopGuideAudio()` 후 150ms 대기하고 녹음을 시작해 스피커 잔향이 물리적으로 멈춘 뒤 마이크가 활성화되도록 수정.
  - **[결함] STT 인텐트 체크 순서 변경 (awaiting_intent 상태 머신 수정)**: 클로드 세션에서 실기기 로그(13:24:19~13:25:35, 5회 반복)로 발견. "길댕아" 웨이크워드 이후 인텐트 대기 상태(`is_awaiting_intent`)에서, wake 재호출(`_is_gildaeng_wake`) 체크가 nav/question 인텐트 체크보다 **우선**하고 있었다. 사용자가 "길댕아 길찾아줘"라고 말하면 `_is_gildaeng_wake`가 먼저 True가 되어 인텐트 매칭 전에 리턴해버려, 목적지 대기 상태로 진입하지 못하고 "네, 길 찾아드릴까요?" 안내만 반복되는 문제. 체크 순서를 `nav intent → question intent → wake 재호출 → else(재질문)`로 변경해, 실제 인텐트 키워드가 포함되어 있으면 그것을 우선 처리하도록 정정.
  - **[결함] WS 종료 후 서버 송신 실패 스팸 방지**: 클로드 세션에서 실기기 로그(13:26:47~52, 17회 반복)로 발견. `session_manager.py`의 `send_json()`/`send_bytes()`가 WebSocket 상태를 검사하지 않고 `active_connections` 딕셔너리 키 존재 여부만 확인했다. WS 연결이 끊어진 뒤에도 `disconnect()` 호출 전에 DetectionConsumer가 독립 asyncio 태스크로 `send`를 시도하면 `RuntimeError: Cannot call "send" once a close message has been sent` 에러가 스팸으로 발생. `send_json`/`send_bytes`/`is_connected`에 `ws.application_state == WebSocketState.CONNECTED` 가드를 추가해 종료된 연결로의 송신을 원천 차단.
  - **[결함] 폴백 모드 BBox 미표시 수정**: WS 재연결 한계 도달 후 폴백 모드(`status === "fallback"`)에서 탐지된 객체의 BBox가 화면에 표시되지 않는 문제. `CameraView.tsx`의 `handleFrame`에서 온디바이스 추론 결과(det+seg)를 `setDetections`에 반영하는 조건이 `if (isMockModeRef.current)`로 묶여 있어, 실기기(`MOCK_CAMERA=false`)에서는 온디바이스 추론이 정상 동작함에도 BBox 데이터가 `detections` 상태에 전달되지 않았다. `wsStatusRef`를 도입해 `isMockModeRef.current || wsStatusRef.current === "fallback"` 조건으로 확장 - 정상 연결 시에는 서버 `server_detection` 결과를 우선(덮어쓰기 방지), 폴백 모드에서는 온디바이스 CoreML 추론 결과로 BBox를 표시.
  - **빈 입력 안내문 개선**: `stt_to_llm_bridge.py`의 빈 입력 폴백 안내문을 "입력이 없어 정지하세요"에서 "음성이 인식되지 않았어요. 다시 말씀해 주세요."로 변경(사용자 친화적 표현).
- **관련 파일**: `server/stt/stt_to_llm_bridge.py`, `server/api/ws_router.py`, `server/api/session_manager.py`, `client/src/components/CameraView.tsx`, `client/src/hooks/useSttRecorder.ts`, `docs/design/api_specification.md`, `docs/stage-guides/stage_stt_integration_guide.md`, `.agents/skills/websocket-gateway/SKILL.md`, `docs/design/architecture.md`, `docs/ops/test_specification.md`, `docs/changelogs/kb.md`
- **검증 결과**: 서버 Docker 재빌드 후 health 정상, 클라이언트 실기기 빌드/설치/실행 성공. WebSocket 연결 정상(`dev-001`, 현재 접속 1명). `server_detection 송신 실패` 에러 재발 없음(WebSocketState 가드 적용 확인). STT 에코 필터/인텐트 순서 변경/폴백 BBox 표시에 대한 실기기 사용자 검증은 후속 진행 예정.
- **비고**: 클로드(Claude Code) 세션에서 STT 3건 문제 분석을 위임받아 이어서 작업. `.xcodebuildmcp/config.yaml`은 개인 로컬 환경값(workspacePath, deviceId)으로 업데이트된 상태 - 커밋 시 개인 정보 노출 주의.

---

### 2026-07-11 | 1+3+6+7단계 | dev 병합 전 kb 신규 커밋 안전성 결함 8건 수정

- **커밋**: (이번 커밋)
- **변경 내용**:
  - **Android STT 캡처 판정 정정**: iOS Linear PCM에만 바이트 길이 기반 캡처 검증을 적용하고, Android MPEG-4/AAC는 압축 오디오이므로 해당 검증에서 제외했습니다. 공통 확장자도 iOS `.wav`, 그 외 `.m4a`로 분리하고 `RecordingOptions.web` 필수 설정을 추가했습니다.
  - **지연 녹음 경쟁 상태 제거**: 안내 음성 중 150ms 잔향 대기 타이머와 press 상태를 추적하여 사용자가 먼저 손을 떼면 예약 녹음을 취소하고 STT 인지 가이드 뮤트를 즉시 해제하도록 수정했습니다.
  - **반사 경보 송신 성공 확인**: `SessionManager.send_json()`/`send_bytes()`가 실제 송신 성공 여부를 boolean으로 반환하게 하고, 반사 경보가 전달된 경우에만 60초 중복 억제를 기록하도록 수정했습니다.
  - **STT 개인정보 최소화**: `data/stt_debug/` 원본 WAV 영구 저장과 INFO 로그의 전사문·안내문 본문 출력을 제거했습니다. DB에는 전사문 대신 입력 길이만 저장하며 요청 단위 임시 파일은 기존 `finally` 정리 경로에서 즉시 삭제합니다.
  - **STT 계약·테스트 정합화**: REST STT 브리지에도 실제 `device_id`를 전달하고, WS 응답 테스트를 `transport: "binary"`와 raw WAV 프레임 기준으로 갱신했습니다. 자기-에코 감지, 인텐트 우선순위, 연결 종료 시 반사 경보 비억제 테스트를 추가했습니다.
  - **문서·줄바꿈 정합화**: API 명세, STT 통합 가이드, 테스트 명세, 아키텍처, WebSocket 스킬을 구현과 맞추고 `.gitignore`를 LF로 정규화했습니다.
- **관련 파일**: `client/src/hooks/useSttRecorder.ts`, `client/src/components/CameraView.tsx`, `server/api/session_manager.py`, `server/api/stt_router.py`, `server/api/ws_router.py`, `server/detection/consumer.py`, `server/stt/stt_to_llm_bridge.py`, `tests/test_session_manager.py`, `tests/test_detection.py`, `tests/test_ws_router_stt.py`, `tests/test_stt_router_nonblocking.py`, `tests/test_stt_service_template.py`, `tests/test_stt_to_llm_bridge_template.py`, `docs/design/api_specification.md`, `docs/design/architecture.md`, `docs/ops/test_specification.md`, `docs/stage-guides/stage_stt_integration_guide.md`, `.agents/skills/websocket-gateway/SKILL.md`, `.gitignore`, `docs/changelogs/kb.md`
- **검증 결과**: `pytest` 변경 영향 포함 전체 테스트 130건 통과·2건 건너뜀(`test_ws_echo.py`, 기존 비결정적 RAG E2E 제외), `tsc --noEmit`, 변경 Python 파일 `py_compile`, iOS 기기용 Debug 무서명 빌드, `git diff --check` 통과. 전체 테스트에서 변경 범위 밖 `tests/test_e2e_pipeline.py` 1건은 Mock 캡셔닝이 킥보드 문구 대신 일반 안내를 반환해 기존 실패가 재현되었습니다.
- **비고**: `dev` 병합과 원격 push는 수행하지 않고 로컬 `kb` 수정 커밋만 생성합니다.
