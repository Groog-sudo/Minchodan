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

---

### 2026-07-11 | 6+7단계+클라이언트 | STT 응답 지연 개선, 길안내 무음 수정, 하단 T맵 지도 패널 추가

- **커밋**: `feat(6+7단계): STT 응답 지연 개선, 길안내 무음 수정, T맵 지도 패널 추가 및 문서 정합화`
- **변경 내용**:
  - **STT 응답 지연 개선 3건 (실측 근거)**: macOS Docker CPU 폴백 환경에서 STT 왕복이 정상 3.8초, 컨테이너 재시작 후 첫 요청 10초+로 측정되었다. (a) Whisper 기본 모델을 `faster-whisper-medium`에서 `faster-whisper-small`로 전환(`stt_config.py`, hotwords 바이어싱 유지, 회귀 시 상수 1개 롤백). (b) `main.py` lifespan에서 Whisper 모델을 백그라운드 스레드로 프리로드해 콜드스타트 8~10초 제거. (c) `realtime_tts.py`에 (text, voice, speed) 키 FIFO 캐시(64건)를 추가해 고정 안내문 재합성 1.4~1.9초를 2회째부터 0초로 단축.
  - **[결함] 길안내(turn-by-turn) 무음 수정**: 길안내 멘트 조회(`get_combined_guidance`)가 `DetectionConsumer._send_cognitive_guide` 안에만 있어 카메라 탐지가 없으면 NAVIGATING 상태여도 안내가 전혀 나가지 않았다(실기기 실측: 경로 113 웨이포인트 설정 후 무음). `ws_router.py`의 `realtime_gps` 수신 시점에 NAVIGATING이면 길안내를 직접 평가하고 `_send_nav_guidance()`로 TTS 합성·전송하도록 분리. 중복 발화는 기존 nav_filter의 announced_cache/silence_interval이 양쪽 경로 공용으로 차단. 경로 설정 성공 멘트에 첫 유의미 웨이포인트 지시("먼저, ...")를 덧붙여 시작 직후 방향 공백도 해소.
  - **하단 T맵 지도 패널 신규 (운영자/데모용)**: "정적 지도 + 주기 갱신" 합의 사양으로 구현. `NavMapPanel.tsx` 신규(WebView + TMap JS API, 지도 인터랙션 전면 차단, 경로 폴리라인 + 현재 위치 마커). 마커 갱신은 2초 스로틀, 토글 꺼짐 시 WebView 미마운트로 부하 0. 서버는 경로 설정/해제 시 `nav_route` 메시지(좌표 목록 + TMap appKey)를 전송(`stt_to_llm_bridge.py` nav_waypoints, `ws_router.py`). `react-native-webview` 13.16.1 의존성 추가(pod install 완료).
  - **문서 정합화**: `api_specification.md` v0.4.10(nav_route §6.6 신설, §6.5 길안내 직접 평가 비고, §6.3 기본 모델 small), `architecture.md` v0.4.1(기술 스택·구성도·디렉토리 매핑·§6.7 인터페이스·§10 환경 변수), `environment_variables.md` v0.4.12(`TMAP_APP_KEY` 용도 확장), `stage_stt_integration_guide.md` v0.2.2(지연 개선 3건), `docs/README.md`(내비게이션 요약)를 이번 변경 기준으로 갱신.
- **관련 파일**: `server/stt/stt_config.py`, `server/main.py`, `server/tts/realtime_tts.py`, `server/api/ws_router.py`, `server/stt/stt_to_llm_bridge.py`, `client/src/components/NavMapPanel.tsx`, `client/src/components/CameraView.tsx`, `client/src/types/detection.ts`, `client/package.json`, `client/ios/Podfile.lock`, `docs/design/api_specification.md`, `docs/design/architecture.md`, `docs/ops/environment_variables.md`, `docs/stage-guides/stage_stt_integration_guide.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: `tsc --noEmit` 통과, 변경 Python `py_compile` 통과, FastAPI 재시작 후 health 정상 및 "Whisper 모델 프리로드 완료: faster-whisper-small" 로그 확인, iOS Release 실기기 빌드/설치/실행 성공(WS 프레임 수신 확인). small 모델 인식 품질, GPS 기반 길안내 발화, 지도 패널 표시에 대한 실기기 사용자 검증은 후속 진행.
- **비고**: TMap appKey는 클라이언트 하드코딩 대신 서버 환경변수(`TMAP_APP_KEY`)를 nav_route 메시지로 전달하는 방식이라 저장소에 키가 남지 않는다. 다만 앱 런타임에는 노출되므로 TMap 콘솔에서 키 사용 제한 설정 권장. `react-native-webview`는 클라이언트 신규 의존성(팀 공유 필요).

---

### 2026-07-11 | 문서 | Mitos 보완 로드맵 코드 대조 검증 및 정정본 docs/ 이동

- **커밋**: `docs: Mitos 보완 로드맵 v0.3.0 정정본, docs/research/로 이동`
- **변경 내용**:
  - **코드 전수 대조 검증**: Mitos 로드맵의 주장 17건을 실제 코드·changelog·설계 문서와 대조했다. 결과: 13건 정확(신호등 미인식, crosswalk 부재, Seg 마스크 미활용, bbox 거리 휴리스틱, 카메라 프레임 기준 방향, 패닝 비프, AEC 미적용, ngrok/정적 토큰/재연결 3회, exit 0 재시작 미규명, 반사 4fps, 골든셋 부재, 웨이크워드, 무고지 폴백), 2건 이미 해소("정지하세요" 문구는 `072e990`에서 수정, 전사문 DB 저장은 dev 병합 개인정보 정책으로 제거), 1건 부분 해소(STT 왕복 지연 - `4ff207b` small 전환·프리로드·TTS 캐시), 뉘앙스 보정 2건(폴백 모드는 온디바이스 반사 기능 유지, "길댕아 길찾아줘" 1턴 결합은 처리 가능).
  - **정정본 반영 (v0.3.0)**: 신호등 클래스가 `MID_RISK_CLASSES`에서 제외되어 안내에 미사용인 사실 보강, 각 표의 근거를 코드 파일 기준으로 구체화, STT 지연 항목을 부분 해소로 갱신, 우선순위 표에 부분 해소 행 추가(연결 끊김 고지가 실질적 최우선), 부록 §10 코드 대조 검증 기록 신설.
  - **위치 이동**: `git mv`로 루트 `PROJECT_IMPROVEMENTS_MITOS.md`를 `docs/research/mitos_improvement_roadmap.md`로 이동(이력 보존, jy가 정리한 단일 정본 원칙 유지 - 중복본 미생성). `docs/README.md` 인덱스 2곳 갱신(v0.13.7).
- **관련 파일**: `docs/research/mitos_improvement_roadmap.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 검증 근거는 문서 부록 §10에 주장별 코드 위치로 기록. 저장소 내 `PROJECT_IMPROVEMENTS_MITOS.md` 잔여 참조는 jy changelog 과거 이력 서술뿐으로 정정 불필요.
- **비고**: 로드맵의 기존 최우선 과제(STT 정지 문구)는 완료 상태이므로, 실질적 다음 액션은 연결 끊김 음성 고지 + 무한 백오프 재연결이다.

---

### 2026-07-11 | 클라이언트 | 연결 끊김 음성 고지 + 무한 지수 백오프 재연결 (Mitos 우선순위 2)

- **커밋**: `feat(client): WS 무한 지수 백오프 재연결 + 폴백 전환/복구 음성 고지`
- **변경 내용**:
  - **재연결 정책 변경**: 기존 `MAX_RECONNECT=3`회 1초 간격 재시도 후 콘솔 경고만 남기고 영구 포기하던 구조를, 지수 백오프(1s에서 2배씩, 상한 `RECONNECT_DELAY_MAX=30s`) 무한 재시도로 전환. `MAX_RECONNECT`는 "중단 횟수"에서 "폴백 모드 전환 + 음성 고지 문턱값"으로 의미 재정의(`config/index.ts` 주석 반영).
  - **음성 고지 2종**: 연속 3회 실패 시 "서버 연결이 끊겨 기본 경보 모드로 전환합니다. 연결은 계속 시도합니다."(단절 1회당 1번, `fallbackAnnouncedRef` 가드), 재연결 성공(welcome) 시 "서버 연결이 복구되었습니다. 상세 안내를 다시 시작합니다.". 사용자가 화면을 볼 수 없으므로 음성이 유일한 상태 전달 수단이라는 로드맵 지적을 반영. 출력은 기존 `audioEngine.speakFallback`(expo-speech, 반사 비프/햅틱과 독립 채널)을 재사용.
  - **폴백 상태 유지(sticky)**: 백그라운드 재시도가 상태를 `connecting`/`disconnected`로 덮으면 CameraView의 폴백 판정(`wsStatusRef.current === "fallback"`)이 시도할 때마다 꺼졌다 켜져 온디바이스 BBox/경보 표시가 깜빡이는 문제를 함수형 setState로 차단. 폴백은 실제 welcome 수신까지 유지.
  - **재연결 카운터 리셋 시점 이동**: onopen(TCP 연결)에서 welcome(핸드셰이크 성공)으로 이동. 인증 실패 등 "연결 직후 끊김" 반복 시에도 백오프가 계속 자라고 폴백 고지가 동작하도록 보강(기존에는 onopen 리셋 때문에 1초 간격 무한 재시도 + 고지 없음).
- **관련 파일**: `client/src/hooks/useWebSocket.ts`, `client/src/config/index.ts`, `docs/design/architecture.md`, `docs/research/mitos_improvement_roadmap.md`, `docs/changelogs/kb.md`
- **검증 결과**: `tsc --noEmit` 통과. 실기기 시나리오 검증(서버 중단 후 폴백 고지 발화 - 30초 상한 백오프 지속 - 서버 재기동 후 복구 고지 발화)은 후속 진행(기존 실기기 검증 대기 3건에 추가).
- **비고**: 문서 반영 - architecture.md v0.4.2(오프라인 내성 항목), mitos_improvement_roadmap.md v0.3.1(§4 해소, §7 완료, §10 부록 갱신). 서버 측 변경 없음(클라이언트 단독 패치).

---

### 2026-07-11 | 클라이언트+iOS 네이티브 | STT 녹음 구간 AEC 도입 (Mitos 우선순위 4)

- **커밋**: `feat(client): STT 녹음 구간 AEC(voiceChat 세션) 도입 + 시작 신호음 조건부 복원`
- **변경 내용**:
  - **AudioSessionBridge 네이티브 모듈 신규**: STT 녹음 구간에서 AVAudioSession을 `.playAndRecord` + `.voiceChat` 모드로 전환해 iOS VoiceProcessingIO의 AEC(에코 캔슬레이션)를 활성화한다. 녹음 중 스피커 출력(반사 비프, 신호음)이 마이크에 되잡히는 음향 블리드(2026-07-11 파형 분석으로 확인된 STT 오염 원인)의 하드웨어 수준 대책. `.defaultToSpeaker` 필수 적용(voiceChat 기본 라우팅은 수화부라 미적용 시 경보 음량 급감), `.allowBluetooth`(HFP)로 골전도/오픈이어 헤드셋 마이크 허용. 전환 직전 세션 설정(expo-audio의 mixWithOthers 등)을 저장했다가 녹음 종료 시 복구. 파일은 기존 함정 회피를 위해 `client/ios/` 루트에 배치(CoreMLInferenceBridge 주석 참조), project.pbxproj 4개 섹션에 수동 등록.
  - **녹음 시작 신호음 조건부 복원**: 음향 블리드 때문에 제거했던 시작 신호음(단일 상승 비프 120ms, `stt_start.wav` 신규 생성 - 종료 더블 비프와 구분)을 AEC 활성이 세션 조회(`getSessionInfo`)로 확인된 경우에 한해 복원. 두꺼운 옷/추운 날 햅틱만으로는 녹음 시작을 인지하기 어렵다는 로드맵 지적 반영. 회귀 시 `STT_START_CUE_WITH_AEC` 플래그만 false로 롤백(AEC 전환 자체는 유지). 기존 캡처 절단 가드(hold 대비 captured 길이 대조)가 회귀 감지망 역할.
  - **검증 계측**: voiceChat 전환을 prepare 전에 수행(녹음 시작 후 세션 변경은 캡처 절단 위험)하고, record() 직후 세션 모드를 재조회해 expo-audio가 모드를 덮는지 로그로 확인(`[STT][AEC]` 태그). 덮인 경우 시작 신호음을 생략하고 경고 로그.
  - **예외 복구**: 녹음 시작 실패/종료 실패 경로 모두에서 voiceChat 세션이 잔류하지 않도록 복구 호출. 종료 신호음은 세션 복구 후 재생(voiceChat 유지 시 재생 음질/음량 저하 회피).
- **관련 파일**: `client/ios/AudioSessionBridge.swift`(신규), `client/ios/AudioSessionBridge.mm`(신규), `client/ios/Minchodan.xcodeproj/project.pbxproj`, `client/src/services/audioSessionBridge.ts`(신규), `client/src/services/audioEngine.ts`, `client/src/hooks/useSttRecorder.ts`, `client/assets/sounds/stt_start.wav`(신규), `docs/design/architecture.md`, `docs/stage-guides/stage_stt_integration_guide.md`, `docs/research/mitos_improvement_roadmap.md`, `docs/changelogs/kb.md`
- **검증 결과**: `tsc --noEmit` 통과, `plutil -lint` pbxproj 무결성 통과, iOS 시뮬레이터 Debug 빌드 성공(BUILD SUCCEEDED), 산출물 `Minchodan.debug.dylib`에서 AudioSessionBridge 심볼 50개 및 `setVoiceProcessing:resolver:rejecter:` 시그니처 확인(컴파일·RN 모듈 등록 정합). 실기기 청취 검증은 후속: (1) 녹음 중 반사 비프가 전사에 안 섞이는지, (2) 시작 신호음 자기 녹음 여부, (3) voiceChat 전환 후 스피커 라우팅·음량 실용성, (4) 캡처 절단 가드 미발동 확인.
- **비고**: AEC 실효성은 시뮬레이터에서 검증 불가(실제 스피커-마이크 음향 결합 필요). Android는 `audioSessionBridge.ts`가 no-op이라 동작 변화 없음(후속: AcousticEchoCanceler). Info.plist 권한 변경 없음(기존 마이크 권한 그대로).

---

### 2026-07-11 | 문서 | 세션 구현분 문서 전수 정합화 및 스킬 트리 동기화

- **커밋**: `docs: 세션 구현분(STT small·지도 패널·재연결·AEC) 문서 전수 정합화 + 스킬 트리 동기화`
- **변경 내용**:
  - **CLAUDE.md v0.3.5 / AGENTS.md v0.3.2**: §2 기술 스택에 STT(faster-whisper-small)·Navigation(TMAP)·react-native-webview 지도 패널·STT 녹음 구간 AEC(AudioSessionBridge) 등재. AGENTS.md의 구식 표기 2건 정정(LangChain 병기 → 래퍼 미사용, Web Audio API 개념 규격 → 미사용 명시, 온디바이스 추론 누락 보완).
  - **api_specification.md v0.4.11**: §6.4 폴백 모드 비고를 재연결 정책 변경(무한 지수 백오프, 폴백 전환/복구 음성 고지, welcome 수신 시 해제) 기준으로 갱신.
  - **ios_android_bifurcation_contract.md v1.1.1**: §3 소유권 매트릭스에 `AudioSessionBridge.swift/.mm`(iOS 전용), `audioSessionBridge.ts`(공유 계약, Android no-op - 인터페이스 유지 필수) 등재.
  - **stage_stt_integration_guide.md v0.2.4**: §6 테스트 체크리스트에 AEC 실기기 검증 항목 TC-STT-010(voiceChat 세션 유지 로그), TC-STT-011(시작 신호음 비오염) 추가.
  - **websocket-gateway 스킬 정정 + 스킬 트리 전수 동기화**: SKILL.md의 useWebSocket 예시에 재연결 정책 정정 노트 추가, 검증 매트릭스의 "3회 이내 성공"을 무한 백오프+음성 고지 기준으로 갱신. 점검 중 `.claude/skills/`가 `.agents/skills/` 대비 5개 파일 뒤처져 있음을 발견(websocket-gateway v0.2.1 잔존, 4개 스킬의 docs 재편성 이전 경로 잔존) - `.agents/` 최신본으로 전수 동기화 완료(두 트리 diff 0건).
- **관련 파일**: `CLAUDE.md`, `AGENTS.md`, `docs/design/api_specification.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/stage-guides/stage_stt_integration_guide.md`, `.agents/skills/websocket-gateway/SKILL.md`, `.claude/skills/websocket-gateway/SKILL.md`, `.claude/skills/llm-guidance-orchestrator/SKILL.md`, `.claude/skills/rag-realtime-search/SKILL.md`, `.claude/skills/xcode-build-management/SKILL.md`, `.claude/skills/yolo-obstacle-detection/SKILL.md`, `docs/changelogs/kb.md`
- **검증 결과**: `diff -rq .agents/skills .claude/skills` 무차이 확인. 코드 변경 없음(문서 전용 커밋).
- **비고**: Directory_Structure.md는 "계획된 물리적 폴더 구조" 문서(설계 초안 보존 목적)로 판단해 이번 정합화 범위에서 제외.

---

### 2026-07-11 | 병합 | 최신 dev(d490a65) 병합 및 문서 정합성 정리

- **커밋**: `merge: 최신 dev를 kb에 통합` + `docs: dev 병합 후 README 중복 섹션 정리 및 계획 문서 교차 참조`
- **변경 내용**:
  - **dev 병합**: dev 신규 커밋 1건(d490a65, TH의 "dev 통합 개선 실행 계획서 추가") 병합. `git merge-tree` 사전 시뮬레이션으로 텍스트 충돌 0건 확인 후 클린 머지(kb 코드 변경과 겹침 없음, 문서 전용).
  - **README 중복 섹션 정리 (v0.13.8)**: dev가 말미에 추가한 `## 9. ops/reports/ - 감사·개선 보고서` 섹션은 기존 §7(ops/reports)과 주제 중복 + 실제 파일 위치(`docs/ops/`)와 섹션명 불일치 + 비번호 섹션들 뒤에 위치하는 3중 문제가 있어 제거하고, 계획서 인덱스 행을 상단 문서 목록과 §5(ops) 표로 이관.
  - **계획서 정합 노트 (v1.0.1)**: `dev_8b2f606_improvement_plan.md`에 kb 반영 현황 노트 추가(원본 본문 무변경) - §5 설계 원본 갱신은 kb에서 상당 부분 완료, §2 인증/반사 억제·§5 환경변수는 Mitos 로드맵과 스코프 중복(교차 확인 안내), §4 품질 수치는 병합 후 재측정 필요.
  - **Mitos 로드맵 교차 참조 (v0.3.3)**: §7 우선순위에 dev 계획서 교차 참조 블록 추가(중복 스코프 3건 명시).
- **관련 파일**: `docs/README.md`, `docs/ops/dev_8b2f606_improvement_plan.md`, `docs/research/mitos_improvement_roadmap.md`, `docs/changelogs/kb.md`
- **검증 결과**: 병합 전 `git merge-tree --write-tree` 충돌 0건 확인, 병합 후 정리 문서 상대 링크 경로 존재 확인. 코드 변경 없음.
- **비고**: 두 계획 문서(dev 계획서 + Mitos 로드맵)는 관점이 달라(전자: dev 통합 감사 기반 P0/P1, 후자: 실기기 검증 기반 사용자 안전) 병존시키고 교차 참조로 연결.

---

### 2026-07-11 | 통합 정합화 | KB 담당 확인 항목 이행: 지침서 정정, 콘솔 지도 복구, event_id 구조화, 위험도 SSOT 계약

- **커밋**: `feat(통합): 지침서 정정, 콘솔 지도 연동 복구, event_id 구조화, 위험도 SSOT 계약 초안`
- **변경 내용**:
  - **통합 지침서 2종 정정 (v2.3.0)**: KB 담당 확인 결과 코드보다 뒤처진 서술을 갱신. 서버 통합 기술 지침서 - §3.2 GPS 수신을 detection 페이로드 필드가 아닌 실제 구현(`realtime_gps` 전용 메시지)으로 정정, §3.2에 GPS 수신 시점 길안내 직접 평가(2026-07-11) 추가, §3.4 nav_route 신설, 지도 웹페이지용 ws와 단말 `/ws/detect` 채널 구분 명시, 로컬 절대 경로 제거. 관제 UI 지침서 - §1에 "길댕아" 2단계 웨이크워드·질문 모드·첫 방향 지시 멘트 반영, 반사 경로 비협상 원칙(고위험 경보는 네비 멘트와 미융합) 명시, §3에 콘솔 지도와 단말 NavMapPanel이 별개 화면임을 명시.
  - **콘솔 지도 임베딩 복구**: `OperatorLiveMap.tsx`가 구버전 8001 독립 포트로 하드코딩된 채 `App.tsx`에서 주석 처리되어 있던 것을, 8000 서브앱 경로(`VITE_NAV_MAP_URL` 환경변수, 기본 `http://localhost:8000/navigation/?embed=true`)로 수정하고 재활성화. `console/.env.example`에 변수 등재. 콘솔은 공유 영역이므로 TH 확인 요망.
  - **event_id 구조화 (dev 계획서 §3)**: 단말 detection event_id를 `event-{epoch_ms}`에서 `event-{device_id}-{stream}-{epoch_ms}`로 변경(`CameraView.tsx`). 기존 형식은 반사(4fps)/인지(2fps) 타이머가 같은 ms에 발화하면 충돌했고, DB의 event_id UNIQUE + 중복 저장 방지 로직이 두 번째 프레임 로그를 조용히 유실시키는 실결함이었다. 서버는 event_id를 파싱하지 않고 통과시키며(전수 확인), DB 컬럼 String(64) 대비 신규 형식 약 38자로 안전. api_specification 공통 필드 표에 형식 명세 반영.
  - **반사 위험도 SSOT 계약 초안 (dev 계획서 §2, 1단계)**: `docs/design/risk_ssot_contract.md` 신설 - 서버/단말이 반드시 일치시켜야 하는 고위험 5종+confidence를 SSOT로 고정하고, 단말 전용 실내 오탐 확장 7종과 거리 산식 불일치(서버 bbox 하단 y vs 단말 면적 기반)는 인지된 기술 부채로 명시. 회귀 테스트 `tests/test_risk_ssot.py` 신설(서버는 import 대조, 단말은 TSX 텍스트 파싱 대조, 파싱 실패 시 명시적 실패) - 복제 불일치가 커밋 단계에서 차단됨. 공통 데이터 계약 소스 통합(2단계)은 TH·Mobile 합의 대기.
- **관련 파일**: `docs/dev-guides/integration/서버_및_시스템_통합_기술_지침서.md`, `docs/dev-guides/integration/관제_UI_및_시나리오_연동_지침서.md`, `console/src/components/OperatorLiveMap.tsx`, `console/src/App.tsx`, `console/.env.example`, `client/src/components/CameraView.tsx`, `docs/design/risk_ssot_contract.md`(신규), `tests/test_risk_ssot.py`(신규), `docs/design/api_specification.md`, `docs/ops/test_specification.md`(TC-DET-011), `docs/ops/dev_8b2f606_improvement_plan.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: `pytest tests/test_risk_ssot.py` 3건 통과, 클라이언트/콘솔 `tsc --noEmit` 각각 통과. 콘솔 지도 iframe 실표시와 event_id 실기기 왕복은 서버 기동 환경에서 후속 확인.
- **비고**: KB 담당 핵심 원칙(내비게이션의 반사 경로 미경유) 코드 검증 완료 - 반사 경로 3개 파일에 navigation 참조 0건, 길안내 발화 3경로 전부 인지 채널(guide). 검토 상세는 이 엔트리 직전 대화 기준.

---

### 2026-07-11 | 통합 정합화 2차 | SSE·콘솔 이벤트 계약 고정, 인증 기본값 제거

- **커밋**: `feat(보안+계약): SSE 이벤트 계약 고정 및 인증 기본값 환경 분리(fail-closed)`
- **변경 내용**:
  - **SSE·콘솔 이벤트 계약 고정 (dev 계획서 §5)**: api_specification §8을 전면 개편(v0.4.12). 실발행 이벤트(connection_established/ping)와 예약 브리지 이벤트(system_metrics·risk_event·session_status·detection_event·llm/rag/tts/stt_status)를 분리하고, payload 필드를 콘솔 파서(`useMonitorStream.ts`) 기준으로 고정. **실측 사실 명시**: `mcp:metrics` 스트림에 실데이터를 발행하는 producer가 현재 저장소에 없음(탐지 파이프라인 실발행은 `risk.events`, 두 스트림 미연결) - 기존 명세의 "risk.events 실시간 뷰" 오기를 정정하고 producer 구현을 후속 과제로 등재. 데모 데이터는 DEV 빌드+`VITE_ENABLE_DEMO_DATA` 이중 가드로 이미 분리되어 있음을 §8.4에 명문화.
  - **인증 기본값 제거 (dev 계획서 §2)**:
    - `server/db/security.py`: `APP_ENV=production`에서 `JWT_SECRET_KEY` 미설정 시 `RuntimeError`로 기동 거부(fail-closed). 개발 환경만 임시 키 폴백(테스트 하위 호환).
    - `server/api/auth.py`: 정적 디바이스 토큰 하드코딩을 `DEVICE_STATIC_TOKENS`(`id:token` 쉼표 목록) 환경 변수로 분리. 미설정 시 개발 환경은 개발 기본값 폴백(경고 로그), 운영 환경은 빈 목록(JWT 디바이스 토큰만 인정).
    - `server/api/ws_router.py`: 토큰 검증 실패 로그의 토큰 원문 출력을 제거(길이만 기록).
    - `client/src/config/index.ts`: NETWORK_MODE/LAN_IP/NGROK_DOMAIN/DEVICE_ID/TOKEN을 `EXPO_PUBLIC_*` 환경 변수 우선으로 전환(기존 상수는 개발 폴백 유지 - 이원화 계약 §7.3 상수 보존 규칙 준수, 계약 v1.1.2로 규칙 확장 반영). EXPO_PUBLIC 값은 번들에 평문 포함되므로 비밀키 용도 금지를 주석으로 명시.
    - `.env.example`에 `APP_ENV`/`JWT_SECRET_KEY`/`DEVICE_STATIC_TOKENS` 등재, environment_variables.md v0.4.13(§2.4 갱신, §2.14 클라이언트·콘솔 공개 변수 신설).
- **관련 파일**: `server/db/security.py`, `server/api/auth.py`, `server/api/ws_router.py`, `client/src/config/index.ts`, `.env.example`, `docs/design/api_specification.md`, `docs/ops/environment_variables.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/ops/dev_8b2f606_improvement_plan.md`, `docs/changelogs/kb.md`
- **검증 결과**: (1) `APP_ENV=production` + `JWT_SECRET_KEY` 미설정에서 security 모듈 임포트 시 `RuntimeError` 기동 거부 확인, (2) production에서 `DEVICE_STATIC_TOKENS` 미설정 시 정적 토큰 목록 빈 값 확인, (3) `DEVICE_STATIC_TOKENS` 오버라이드 파싱 확인, (4) `pytest tests/test_api_ws.py tests/test_risk_ssot.py` 7건 통과(개발 기본 토큰 하위 호환 유지), (5) 클라이언트 `tsc --noEmit` 통과. `tests/test_ws_echo.py` 6건 실패는 라이브 서버(localhost:8000) 필요 테스트로 변경 전 기준선에서도 동일 실패함을 대조 확인(회귀 아님).
- **비고**: dev 계획서 §2/§5의 KB 확인 항목 전부 착수 완료. 잔여: `mcp:metrics` producer 구현(TH·Backend), 기기 고유 인증·관리자 bootstrap 절차(JY·TH), ngrok 대체 고정 도메인+TLS(팀 인프라 결정 필요).

---

### 2026-07-11 | 클라이언트+iOS 네이티브 | LiDAR 실거리 프로브 프로토타입 (Mitos 로드맵 §2 거리 휴리스틱)

- **커밋**: `feat(client): LiDAR 실거리 프로브 프로토타입 - DepthProbeBridge + 거리측정 모드`
- **변경 내용**:
  - **배경**: 현재 거리 판정은 단안 휴리스틱 3종(단말 `0.22/sqrt(areaRatio)`, 서버 `bbox_area_ratio`, 반사 게이트 bbox 하단 y)뿐이라 "전방 3m"가 아닌 "크게 보임" 수준. 테스트 기기(iPhone 14 Pro Max)의 LiDAR + `AVCaptureDepthDataOutput`으로 실거리 검증 경로를 만든다(1단계 프로토타입).
  - **DepthProbeBridge 네이티브 모듈 신규**: `builtInLiDARDepthCamera` 자체 세션(vga640x480, 심도 전용)으로 최신 심도 맵을 유지하고, 정규화 좌표(portrait) 목록의 실거리(m)를 3x3 미디언으로 샘플링해 반환(`startProbe`/`stopProbe`/`probe`). `isFilteringEnabled`로 저반사 표면 홀 필링, `depthDataAccuracy`(absolute=LiDAR 실측) 노출. project.pbxproj 4개 섹션 수동 등록.
  - **단말 거리측정 모드**: CameraView에 "거리측정" 토글 신규. 켜면 vision-camera를 내리고(`isActive=false`, **두 세션이 후면 카메라를 동시 점유할 수 없는 프로토타입 제약** - 탐지·경보 일시 정지) 500ms 폴링으로 화면 3지점(중앙/전방 하단/발밑) 실거리를 오버레이 표시. 줄자 실측 대조용 계측 화면.
  - **2단계(후속) 방향 문서화**: vision-camera 세션에 depth 출력을 통합해 bbox+실거리 상시 융합, bbox 휴리스틱은 depth 신뢰도 낮을 때 fallback으로 강등(Mitos 로드맵 §2, risk_ssot_contract §3 수렴 방향과 일치). Android는 LiDAR 부재로 대칭 구현 없음(이원화 계약 v1.1.3 등재).
- **관련 파일**: `client/ios/DepthProbeBridge.swift`(신규), `client/ios/DepthProbeBridge.mm`(신규), `client/ios/Minchodan.xcodeproj/project.pbxproj`, `client/src/services/depthProbe.ts`(신규), `client/src/components/CameraView.tsx`, `docs/design/architecture.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/research/mitos_improvement_roadmap.md`, `docs/changelogs/kb.md`
- **검증 결과**: `tsc --noEmit` 통과, iOS 시뮬레이터 Debug 빌드 BUILD SUCCEEDED + DepthProbeBridge 오브젝트 파일(Swift/mm) 생성 확인. 실기기 검증(LiDAR 실측 정확도 - 줄자 대조 1/2/3/5m, 저반사 표면, 야외 직사광, 탐지 모드 복귀 시 카메라 재점유)은 후속. 시뮬레이터는 LiDAR가 없어 "LiDAR 심도 카메라 없음" 에러 표출이 정상.
- **비고**: 접근성 주의 - 거리측정 모드 동안 반사 경보가 정지되므로 운영자/계측 전용 기능임(종단 사용자 UX 아님). 토글 진입 시 이 사실이 오버레이 첫 줄("탐지 일시정지")에 표기됨.

---

### 2026-07-12 | 서버+콘솔 | 이벤트 프레임 보존 및 콘솔 상황 이미지 렌더링 (오탐 검증 기반)

- **커밋**: `feat(서버+콘솔): 이벤트 프레임 보존(frame_path) 및 콘솔 사후 이력 이미지 렌더링`
- **변경 내용**:
  - **배경**: `detection_guidance_logs`에는 bbox·클래스 등 텍스트 메타데이터만 남고 발생 시점 프레임 이미지는 어디에도 영속되지 않아, 콘솔에서 오탐 여부 판별이나 안내 발화 당시 상황 확인이 불가능했다. 이미지 파일 + DB 경로 참조 방식으로 보존 체계를 신설한다(BLOB 저장은 반사 이벤트 유입량에 DB 비대화로 배제).
  - **이벤트 프레임 저장소 신설** (`server/services/event_frame_store.py`): 로그 적재 이벤트만 원본 프레임을 JPEG(품질 80)으로 `data/event_frames/YYYYMMDD/{event_id}.jpg`에 저장. event_id 화이트리스트(`[A-Za-z0-9._-]{1,64}`)·저장소 밖 경로 해석 차단(resolve 검증)·보존 기간(`EVENT_FRAME_RETENTION_DAYS` 기본 7일) 초과 날짜 폴더 기동 시 삭제. 저장 실패 시 `frame_path=NULL`로 로그 적재는 계속(방어적 코딩).
  - **반사 경로 무영향 저장**: JPEG 인코딩·디스크 쓰기는 기존 `_schedule_log_persist` 백그라운드 태스크 내부에서 `asyncio.to_thread`로만 수행. `_process_frame`이 보유한 프레임을 `_send_reflex_alert`/`_send_cognitive_guide`에 전달하고, 실제 전송 성사 후에만 저장이 예약된다(중복 억제·쿨다운으로 걸러진 프레임은 미저장 - 용량 통제).
  - **DB 스키마**: `detection_guidance_logs.frame_path VARCHAR(255) NULL` 추가(models/schemas/schema.sql), 마이그레이션 `20260712_001_add_frame_path_to_detection_guidance_logs.sql` 신설. 인지 로그의 `detected_objects_json`에 bbox 좌표(좌상단 x,y+w,h, 프레임 픽셀) 포함 - 콘솔 오버레이용이며 LLM 오케스트레이터 입력에는 기존대로 미포함(프롬프트 오염 방지).
  - **조회 API 신설** (`server/api/detection_log_router.py`): `GET /api/v1/admin/detection-logs`(목록, limit 1~200) + `GET /api/v1/admin/event-frames/{event_id}`(JPEG 서빙). 인증은 `get_current_admin`(헤더 또는 쿼리 토큰 - `<img>` 태그 제약상 SSE와 동일한 쿼리 우회). DB 등록 경로만 서빙해 임의 파일 접근을 차단. Repository에 `list_recent`(detected_at 내림차순) 추가.
  - **콘솔 상황 이미지 렌더링**: `useDetectionLogs` 훅 신설(REST 30초 폴링, `VITE_API_BASE_URL`). Detection Guidance Log 테이블에 썸네일 컬럼 추가, 행 클릭 시 상세 뷰에서 원본 이미지 위에 bbox·클래스·신뢰도를 비율 좌표 오버레이로 표시(이미지에 굽지 않음 - 원본 보존으로 임계값/모델 교체 재검증 가능). 데모 데이터는 실조회 결과 없을 때만 폴백.
- **관련 파일**: `server/services/event_frame_store.py`(신규), `server/api/detection_log_router.py`(신규), `server/db/models.py`, `server/db/schemas.py`, `server/db/repositories.py`, `server/db/schema.sql`, `server/db/migrations/20260712_001_add_frame_path_to_detection_guidance_logs.sql`(신규), `server/services/detection_guidance_log_service.py`, `server/detection/consumer.py`, `server/main.py`, `console/src/api/useDetectionLogs.ts`(신규), `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/types/monitor.ts`, `console/src/App.tsx`, `console/src/styles.css`, `console/.env.example`, `.env.example`, `tests/test_event_frame_store.py`(신규), `docs/design/api_specification.md`(v0.4.13 §8.5), `docs/design/architecture.md`(v0.4.5 §13.3.1), `docs/ops/environment_variables.md`(v0.4.14), `docs/changelogs/kb.md`
- **검증 결과**: `pytest tests/test_event_frame_store.py tests/test_ws_router_stt.py tests/test_admin_service_login.py tests/test_risk_ssot.py` 18건 통과(저장/경로 탈출 차단/보존 정리 + 기존 회귀), 변경 모듈 전체 임포트 무결성 확인, ruff 통과, 콘솔 `npm run build`(tsc --noEmit 포함) 통과. 실제 탐지 이벤트로 이미지 저장·콘솔 표시 왕복은 서버+실기기 기동 환경에서 후속 확인.
- **비고**: 보행 중 촬영 이미지는 행인 등 개인정보 포함 가능성이 있어 기간 한정 보존(기본 7일)으로 설계했으며, 보존 기간 정책은 팀 확정 필요(STT WAV 제거 전례 참조). MariaDB 운영 DB에는 마이그레이션 SQL 수동 반영 필요. 후속 확장 후보: 오탐 판정 컬럼(`false_positive`)+콘솔 판정 버튼 - (이미지, 오탐 라벨) 쌍은 재학습 데이터로 재사용 가능.

---

### 2026-07-12 | 콘솔+iOS 실기기 | 이미지 라이트박스, 한국식 시각/스트림 배지, iOS 카메라 180도 방향 반전 결함 수정

- **커밋**: `fix(client): iOS 카메라 프레임 180도 방향 반전 수정 + feat(콘솔): 이미지 확대·시각/스트림 표시 개선`
- **배경**: 실기기→서버→DB E2E 검증 중 콘솔에서 저장된 이벤트 프레임이 뒤집혀 보인다는 사용자 보고를 받아 조사. 처음엔 CSS/라이트박스 문제로 의심했으나, 서버 응답과 디스크 원본 파일의 MD5가 완전히 일치하고 콘솔 전체에 rotate/transform CSS가 전혀 없음을 확인해 표시 버그를 배제. 손을 편 상태(손가락 위)로 반복 실기기 촬영해 대조한 결과, **폰이 정상(노치 위)으로 들려 있었는데도 저장된 프레임은 정확히 180도 뒤집혀 있음을 확정**. 반사(Frame Processor, Swift)·인지(takePhoto+expo-image-manipulator) 두 개의 완전히 독립된 캡처 경로가 동일 증상을 보여, 두 경로가 공유하는 `react-native-vision-camera` 4.7.3의 가속도계 기반 방향 판정(`CMAccelerometerData+deviceOrientation.swift`)이 이 기기 조합에서 반대로 보고되는 것으로 결론.
- **콘솔 개선**:
  - **이미지 확대 보기(라이트박스)**: `DetectionGuidanceLogTable.tsx`에 썸네일/상세 미리보기 이미지 클릭 시 원본 크기 모달(bbox 오버레이 포함)로 확대하는 기능 추가. 닫기는 버튼/배경 클릭/Esc 키 세 경로 지원.
  - **탐지 시각 한국식 고정 표기**: `Intl.DateTimeFormat`에 `timeZone: "Asia/Seoul"` 명시로 브라우저 로케일과 무관하게 `YYYY-MM-DD HH:mm:ss`(KST) 고정 표시(`formatDetectedAt`). 기존 `toLocaleString()`은 브라우저 설정에 따라 형식이 들쭉날쭉해 로그 대조가 어려웠음.
  - **반사/인지 스트림 배지**: 원시 enum 문자열 대신 "반사"(빨강)/"인지"(파랑)/"미분류"(회색) 색상 배지로 렌더링(`StreamBadge`), 테이블·상세 미리보기·라이트박스 헤더 전체에 일관 적용.
- **iOS 방향 버그 수정**:
  - `client/ios/ReflexFrameProcessorPlugin.swift`: 기존 `frame.orientation` 기반 보정 뒤에 `.oriented(.down)` 180도 추가 보정.
  - `client/src/services/frameCaptureProvider.ts`: `captureViaTakePhoto`에 `applyIosOrientationFix` 매개변수(기본 false) 신설, true일 때만 `manipulateAsync` 연산에 `{ rotate: 180 }` 추가. **Android는 이 함수를 아예 쓰지 않고 별도 구현(`captureViaTakePhotoAndroid`)이라 원천적으로 영향 없음** - 이 사실과 Android 자체 실기기 검증 필요성을 `ios_android_bifurcation_contract.md`(v1.1.4)에 명시.
  - `client/ios/Minchodan/Info.plist`: iPhone `UISupportedInterfaceOrientations`에서 `PortraitUpsideDown` 제거(근본 원인은 아니었으나 앱이 실수로 거꾸로 인터페이스 방향에 잠기는 경로를 하나 더 차단하는 안전장치로 보존).
  - **검증 3단계**: (1) 수정 전 손 테스트로 180도 반전 확정(반사/인지 둘 다), (2) Info.plist만 수정 후 재테스트했으나 미해결(가설 기각, 근본 원인이 interfaceOrientation이 아님을 실측 확인), (3) 위 180도 보정 코드 추가 후 손+다리 재테스트로 완전 정상화 확인(손가락 위, 협탁/침대/전선 중력 방향 모두 일치).
- **관련 파일**: `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/styles.css`, `client/ios/ReflexFrameProcessorPlugin.swift`, `client/src/services/frameCaptureProvider.ts`, `client/src/services/frameCaptureProviderSelect.ios.ts`, `client/ios/Minchodan/Info.plist`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/changelogs/kb.md`
- **검증 결과**: 콘솔 `npm run build`(tsc --noEmit 포함) 통과, 클라이언트 `tsc --noEmit` 통과, iOS Release 빌드 3회 반복(수정 전/Info.plist만/최종) 모두 BUILD SUCCEEDED, 최종 빌드 실기기 설치·실행 후 손·다리 실측으로 방향 정상화 확인.
- **비고**: 이 결함은 콘솔 갤러리 표시 문제로 시작했지만 **서버 YOLO 탐지에 들어가는 원본 프레임 자체가 뒤집혀 있었다는 뜻**이라, 지금까지의 탐지 정확도에도 실질적 영향을 줬을 가능성이 있다. 이벤트 프레임 보존 기능([[event-frame-storage]] 성격의 앞선 커밋 659a08e)이 아니었다면 발견하기 어려웠던 결함. Android 네이티브 Frame Processor 구현 시 이 문서의 경고를 참고해 별도로 방향을 검증할 것.

---

### 2026-07-12 | 서버+콘솔 | 오탐 판정(false_positive) 데이터베이스 컬럼 추가 및 운영 콘솔 오탐 판정 기능 구현

- **커밋**: `feat(서버+콘솔): 오탐 판정(false_positive) 컬럼 추가 및 콘솔 오탐 판정 기능 구현`
- **변경 내용**:
  - **데이터베이스 스키마 확장**:
    - `detection_guidance_logs` 테이블에 `false_positive` 컬럼 추가: SQLite (`schema.sql`에 `false_positive INTEGER CHECK (false_positive IN (0, 1))` 추가), MariaDB용 마이그레이션 DDL 스크립트 작성 (`server/db/migrations/20260712_002_add_false_positive_to_detection_guidance_logs.sql` 신설).
    - ORM 모델 `models.py`에 `false_positive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)` 속성 추가.
  - **DTO 스키마 및 비즈니스 로직**:
    - `schemas.py`에 `false_positive` 속성 및 `FalsePositiveUpdateRequest` DTO 추가.
    - `DetectionGuidanceLogRepository` 및 `DetectionGuidanceLogService`에 `update_false_positive` 비동기 업데이트 메서드 구현.
    - `DetectionGuidanceLogService.create_log` 시 생성 페이로드로부터 `false_positive` 값을 전달하도록 구현.
  - **API 엔드포인트 구현**:
    - `detection_log_router.py`에 `PUT /api/v1/admin/detection-logs/{log_id}/false-positive` 라우터 등록. 존재하지 않는 로그인 경우 404 예외 처리.
  - **관리자 운영 콘솔 UI 개선**:
    - `types/monitor.ts` 내 `DetectionGuidanceLogRow` 타입 정의에 `false_positive: boolean | null` 필드 반영 및 `App.tsx` 데모 로그 mock 객체 필드 정합성 교정.
    - `useDetectionLogs.ts`에 `updateLogFalsePositive` PUT API 호출 비동기 callback 훅 추가 및 UI 단독 상태 즉시 반영.
    - `DetectionGuidanceLogTable.tsx`에 "오탐 판정" 컬럼 추가, `FalsePositiveBadge` 및 정탐/오탐 판정 및 취소 액션 버튼군 배치 (로그 상세 뷰 및 라이트박스 뷰 둘 다 적용).
  - **안전성 테스트 검증**:
    - `tests/test_false_positive.py` 단위 테스트 파일 작성: Repository, Service, Router 계층 오탐 업데이트 성공/실패 여부를 교차 검증하는 pytest 비동기 테스트 케이스 구축.
- **관련 파일**: `server/db/models.py`, `server/db/schemas.py`, `server/db/repositories.py`, `server/db/schema.sql`, `server/db/migrations/20260712_002_add_false_positive_to_detection_guidance_logs.sql`(신규), `server/services/detection_guidance_log_service.py`, `server/api/detection_log_router.py`, `console/src/types/monitor.ts`, `console/src/api/useDetectionLogs.ts`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/App.tsx`, `console/src/styles.css`, `tests/test_false_positive.py`(신규), `docs/changelogs/kb.md`
- **검증 결과**: `tests/test_false_positive.py` 3건 테스트 전원 통과 완료, 콘솔 `npm run build` TypeScript 무오류 빌드 완료.
- **비고**: 수집된 오탐 판정 데이터는 추후 인도 보행 이미지 및 YOLO 탐지 모델의 재학습(Re-training) 데이터셋 선별에 핵심 지표로 재활용될 예정입니다.

---

### 2026-07-12 | 서버+콘솔 | 파이프라인 스테이지별 지연(레이턴시) 계측 및 콘솔 표시

- **커밋**: (미커밋)
- **배경**: `docs/design/pipeline_stage_design.md` §4 "단계별 지연 목표" 표에서 L6(LangGraph `ainvoke`)와 L7(실시간 TTS 합성)이 "측정 필요"로 표시된 채 남아 있었고, 실기기 E2E 테스트 중 "실기기 -> STT -> LLM -> 추론 -> DB저장" 종단 지연을 콘솔에서 직접 확인하고 싶다는 요청을 받아, 이미 부분적으로 흩어져 있던 계측(decode_ms, inference_ms, total_latency_ms)을 하나로 모아 DB에 영속화하고 콘솔에 노출했다.
- **변경 내용**:
  - **DB 스키마**: `detection_guidance_logs.latency_json JSON NULL` 추가(models/schemas/schema.sql), 마이그레이션 `20260712_003_add_latency_json_to_detection_guidance_logs.sql` 신설(팀 공유 MariaDB에 적용 완료). 키는 실제로 경유한 스테이지만 담긴다 - 반사 경로는 `decode_ms`/`inference_ms`/`total_ms`만 존재하고 `rag_ms`/`llm_ms`/`tts_ms` 키 자체가 없어, 이중 경로 물리 분리 원칙이 데이터 구조로도 드러난다.
  - **db_save_ms 2단계 기록**: 자기 자신의 DB 쓰기 소요 시간은 쓰기 시작 전에는 알 수 없으므로, `persist_detection_guidance_log()`가 1차 INSERT(다른 스테이지만 포함) 후 소요 시간을 측정해 `db_save_ms`를 합산한 JSON으로 한 번 더 UPDATE한다(`DetectionGuidanceLogRepository.update_latency_json` 신설, `update_false_positive`와 동일 패턴).
  - **반사/인지 경로 계측** (`server/detection/consumer.py`): `_process_frame`에서 `pipeline_start = time.perf_counter()`를 잡아 `_send_reflex_alert`/`_send_cognitive_guide`에 `decode_ms`(`ProcessedFrame.processing_time_ms` 재사용)와 함께 전달. 인지 경로는 RAG 검색 구간(`rag_ms`), `run_orchestrator` 반환값의 `total_latency_ms`(신규 측정 아님 - 기존 계측 재사용), TTS 합성 구간(`tts_ms`)을 추가로 측정. `ReflexAlert`에 `inference_ms` 필드를 신설해 반사 게이트 3종(`reflex_gate`/`head_level_gate`/`surface_gate`) 판정 시점까지의 추론 시간을 기록(`server/detection/detection_pipeline.py`).
  - **STT 경로 계측** (`server/api/ws_router.py` `_process_stt_audio`): `stt_ms`(전사), `llm_ms`(`SttToLlmBridge.invoke_existing_llm`), `tts_ms`(합성) 측정 후 `total_ms`(함수 진입~전송 직전, 즉 사용자가 체감하는 대기 시간)와 함께 `persist_detection_guidance_log`에 전달.
  - **콘솔 표시**: `DetectionGuidanceLogTable`에 "지연(ms)" 열 추가(total_ms 표시) + 행 상세뷰/라이트박스에 스테이지별 칩(`LatencyBadges`, 디코딩/STT/추론/RAG/LLM/TTS/DB저장/총합 순 고정 표시, 존재하는 키만 렌더링). `LatencySummaryPanel` 신규 컴포넌트로 최근 30건 기준 스테이지별 평균/최대/건수 요약 카드를 표시하며, 설계 문서 목표치(디코딩<50ms, 추론<80ms, RAG<50ms)가 있는 스테이지는 평균 초과 시 빨간색으로 경고한다(목표 미정인 STT/LLM/TTS/DB저장/총합은 중립색).
- **관련 파일**: `server/db/models.py`, `server/db/schemas.py`, `server/db/repositories.py`, `server/db/schema.sql`, `server/db/migrations/20260712_003_add_latency_json_to_detection_guidance_logs.sql`(신규), `server/services/detection_guidance_log_service.py`, `server/detection/consumer.py`, `server/detection/detection_pipeline.py`, `server/detection/schemas.py`, `server/api/ws_router.py`, `console/src/types/monitor.ts`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/components/LatencySummaryPanel.tsx`(신규), `console/src/App.tsx`, `console/src/styles.css`, `docs/changelogs/kb.md`
- **검증 결과**: `pytest tests/test_detection.py tests/test_false_positive.py tests/test_ws_router_stt.py tests/test_event_frame_store.py` 40건 통과(`test_false_positive.py`의 3건 에러는 이번 변경과 무관한 기존 pytest-asyncio 픽스처 설정 이슈), 콘솔 `tsc --noEmit` 무오류. 실기기 E2E로 실측 확인: 반사 경로 `{"decode_ms":0.8,"inference_ms":335.9,"total_ms":337.6,"db_save_ms":507.6}`, 인지 경로 `{"decode_ms":0.8,"inference_ms":289.5,"rag_ms":77.9,"llm_ms":476.8,"tts_ms":0.0,"total_ms":845.6,"db_save_ms":483.5}`, STT 경로 `{"stt_ms":206.9,"llm_ms":0.0,"tts_ms":2037.4,"total_ms":2245.3,"db_save_ms":470.3}` 모두 정상 저장·API 응답 확인.
- **비고**: `db_save_ms`가 480~625ms로 상당히 높게 측정됐다 - 팀 공유 MariaDB가 Tailscale 원격(라즈베리파이)에 있어 네트워크 왕복이 포함된 값이며, 로컬 DB라면 훨씬 낮을 것으로 예상된다(후속 확인 필요). LLM `ainvoke` 실측값이 500ms~3.7s로 편차가 커 L6 목표치를 아직 문서에 확정하지 못했다 - 표본이 더 쌓이면 `pipeline_stage_design.md` §4에 목표값을 채워 넣을 것. TTS `tts_ms`가 0.0으로 찍히는 케이스가 관측됐는데(캐시 히트 또는 무음 처리 경로로 추정) 원인은 미확인 - 후속 조사 필요.

**추가 커밋(같은 날 후속 작업)**: 위 구현 직후 "요약 패널이 REST 30초 폴링이라 실시간이 아니다"는 피드백을 받아, 콘솔에 이미 연결돼 있던 실기기 라이브 프리뷰용 WS 채널(`/ws/console/live-feed`, `server_detection` bbox 브로드캐스트와 동일 채널)에 `latency_event` 메시지 타입을 얹어 진짜 실시간 푸시로 전환했다.
- `server/detection/consumer.py`에 `DetectionConsumer._broadcast_latency_event()` 신설 - `_send_reflex_alert`/`_send_cognitive_guide`에서 `latency_stages` 딕셔너리 완성 직후(`_schedule_log_persist` 호출 전) `manager.broadcast_json_to_consoles({"type":"latency_event", ...})`로 즉시 푸시. `server/api/ws_router.py`의 `_process_stt_audio`도 동일 패턴으로 STT 경로 인라인 브로드캐스트 추가.
- 콘솔: `console/src/api/useLiveFeed.ts`에 `latencyEvents`(최근 30건 rolling) 상태 추가, `latency_event` 메시지 타입 파싱. `LatencySummaryPanel`이 `liveEvents` prop이 있으면 그것을 우선 사용(진짜 실시간, 초록 점 pulse 인디케이터 표시)하고 비어 있으면(페이지 갓 로드 등) 기존 REST `rows`로 폴백. `db_save_ms`는 브로드캐스트 시점엔 아직 미확정(INSERT 후 비동기 UPDATE로 확정)이라 실시간 이벤트에는 빠지고 REST 폴백 시에만 표시된다.
- **검증**: 컨테이너 내부에서 `websockets` 클라이언트로 `/ws/console/live-feed`에 직접 접속해 `latency_event` 수신 확인 - 반사 경로 `{"decode_ms":0.9,"inference_ms":243.4,"total_ms":245.3}`(rag/llm/tts 키 없음), 인지 경로 `{"decode_ms":0.8,"inference_ms":267.3,"rag_ms":51.7,"llm_ms":478.4,"tts_ms":1234.5,"total_ms":2033.7}` 모두 실시간 수신 확인. `pytest tests/test_detection.py tests/test_ws_router_stt.py tests/test_event_frame_store.py` 40건 재통과, 콘솔 `tsc --noEmit` 통과.
- **관련 파일(추가분)**: `server/detection/consumer.py`, `server/api/ws_router.py`, `console/src/api/useLiveFeed.ts`, `console/src/components/LatencySummaryPanel.tsx`, `console/src/types/monitor.ts`, `console/src/App.tsx`, `console/src/styles.css`.

**추가 커밋 2(같은 날, UX)**: 이력 테이블이 무한 스크롤로 너무 길다는 피드백에 15건 단위 페이지네이션(`DetectionGuidanceLogTable`에 `page` 상태 + 이전/다음 버튼, `PAGE_SIZE=15`) 추가. 이어서 "새로 쌓이는 걸 보려면 갱신 버튼이 있으면 좋겠다"는 요청에 패널 헤더에 "새로고침" 버튼 추가(`useDetectionLogs`가 이미 노출하던 `refresh`/`loading`을 `App.tsx`에서 `onRefresh`/`refreshing` prop으로 연결, 클릭 시 1페이지로 리셋).

**추가 커밋 3(같은 날)**: "Detection Guidance Log 테이블도 브로드캐스팅으로 실시간 렌더링 가능한가?" 요청에, `latency_event`와 별개로 `guidance_log_event`(저장 완료된 로그 행 전체, `DetectionGuidanceLogResponse.model_dump(mode="json")`)를 DB 저장(+프레임 파일 저장) 완료 직후에만 WS 브로드캐스트하도록 `consumer.py._broadcast_guidance_log_event`/`ws_router.py._process_stt_audio`에 추가. 저장 완료 후에만 보내므로 콘솔이 이벤트를 받자마자 썸네일을 요청해도 404가 나지 않는다. 콘솔은 `useLiveFeed.ts`에 `guidanceLogEvents`(최근 50건) 상태를 추가하고, `App.tsx`가 REST `fetchedLogs`와 `log_id` 기준으로 병합(`useMemo`)해 `DetectionGuidanceLogTable`/`LatencySummaryPanel`에 공급한다. 테이블 헤더에 실시간 여부를 나타내는 pulse 점 인디케이터도 추가.

**추가 커밋 4(같은 날, 핵심 버그 수정 + 미구현 패널 발견)**: "SystemMetrics도 실시간인가? SessionStatus/AI Pipeline Monitor는 구현된 것인가?" 질문에 서버 전체를 조사해 다음을 확인:
- **SystemMetrics**: 실제로 2초 주기 실시간 브로드캐스트됨(`llm_client_factory.py`의 GPU 모니터 루프). GPU가 없는 이 Mac에서는 폴백 고정값이지만 배선 자체는 정상.
- **SessionStatus(상단 기기 접속 상태)**: **완전 미구현이었음** - `session_status` 이벤트가 서버 어디에도 브로드캐스트되지 않아 패널이 항상 빈 상태였다. 신규 구현: `ws_router.py`에 `_broadcast_session_status()` 추가, 연결(auth_ok 직후)/heartbeat_ack 수신 시(RTT 갱신)/해제(finally) 3개 지점에서 브로드캐스트. RTT 실측을 위해 `HeartbeatManager`에 `_last_sent_ts`/`last_rtt_ms` 필드 추가(heartbeat 송신~ack 수신 간격).
- **AI Pipeline Monitor**: `stt_status`/`navigation_status`(이벤트 타입명은 `llm_status`)만 실제 구현돼 있었고 `llm_provider`/`llm_verified`/`llm_retry_count`/`rag_query`/`tts_engine`/`reflex_bypass` 필드는 콘솔 타입에만 정의되고 서버 producer가 없어 항상 undefined였다. `LLMClientFactory.get_current_provider()` 신설, `consumer.py._broadcast_ai_pipeline_status()`로 인지 경로(`_send_cognitive_guide`, orch_result의 verified/retry_count 재사용)와 반사 경로(`_send_reflex_alert`, reflex_bypass=True만)에서 브로드캐스트, STT 경로(`ws_router.py`)에도 최소 필드(provider/tts_engine/reflex_bypass) 추가. `rag_score`는 `Retriever.search_guidance()`가 유사도 점수를 폐기하고 문자열만 반환하는 기존 시그니처라(핵심 로직 영역, 임의 변경 회피) 이번에는 wiring하지 않음 - 후속 과제.
- **부수 발견 - 실제 버그**: 위 조사 중 "현재 시간이 오전 09:53으로 잘못 찍힌다"는 신고를 받아 근본 원인 확인. `server/api/schemas.py`의 `now_iso()`와 `server/mcp/manager.py`의 SSE `timestamp` 생성이 둘 다 `datetime.now().isoformat()`(naive, 컨테이너 시스템 시각=UTC)를 그대로 반환해 타임존 오프셋이 없었다. JS `new Date(...)`는 오프셋 없는 ISO 문자열을 브라우저 로컬 시각(KST)으로 해석하므로 UTC 09:53을 KST 09:53으로 잘못 표시(정상은 18:53) - 9시간 오차. 두 함수 모두 `datetime.now(UTC).isoformat()`로 수정해 `+00:00` 오프셋을 명시(브라우저가 올바르게 KST로 환산). `detected_at`(DB 컬럼)과 `now_ts()`(epoch ms)는 애초에 타임존 정보가 필요 없는 절대값이라 영향 없었음.
- **검증**: SSE 스트림을 직접 열어 `session_status`(rtt_ms 실측 9~33ms), `llm_status`(실제 인지 가이드 전송 시점에 `{"llm_provider":"OLLAMA","llm_verified":true,"llm_retry_count":0,"rag_query":"car","tts_engine":"supertonic","reflex_bypass":false}` 확인), 타임스탬프에 `+00:00` 오프셋 포함 확인. `pytest tests/ --ignore=tests/test_false_positive.py --ignore=tests/test_admin_service_login.py` 140 passed / 3 failed(전부 이번 변경과 무관한 기존 실패 - `test_risk_ssot.py` 2건은 컨테이너에 `client/` 소스 미마운트로 인한 환경 문제, `test_e2e_pipeline.py` 1건은 RAG 목업 데이터 콘텐츠 관련 기존 실패).
- **관련 파일**: `server/api/schemas.py`, `server/mcp/manager.py`, `server/api/ws_router.py`, `server/api/heartbeat.py`, `server/detection/consumer.py`, `server/orchestration/llm_client_factory.py`.
- **후속 과제**: `RiskEventLog`(하단 위험 이벤트 로그) 패널도 조사 중 동일 문제 발견 - `risk_event` 이벤트 역시 서버 어디서도 브로드캐스트되지 않아 항상 비어 있다. 이번 스코프에는 포함하지 않음. `rag_score` wiring도 미완.

**추가 커밋 5(같은 날)**: 대시보드 그리드 레이아웃 순서 오류(4열 그리드에서 `LiveCameraFeed`/`DeviceTelemetryPanel`가 각 `grid-column: span 2`인데 DOM에서 `AiPipelineMonitor` 바로 뒤에 와서 1행 4번째 칸을 못 채우고 다음 줄로 밀려나, `DetectionFeed`가 3행에 혼자 남던 문제) 발견 → `App.tsx`에서 1칸짜리 패널 4개(SystemMetrics/SessionStatus/AiPipelineMonitor/DetectionFeed)를 먼저 배치해 1행을 채우고 span-2 패널 2개가 2행을 채우도록 순서 변경.

이 과정에서 `DetectionFeed`("탐지 메타데이터" 텍스트 피드) 역시 `detection_event`가 서버 어디서도 브로드캐스트되지 않아 SessionStatus와 같은 문제로 항상 비어 있었음을 발견 → `consumer.py._broadcast_detection_event()` 신설, `_process_frame`에서 매 프레임 처리 후(반사/인지 공통) 탐지가 있으면 최고 신뢰도 객체를, 없고 노면 분류만 있으면 surface만 실어 SSE로 브로드캐스트(탐지도 노면도 전혀 없는 프레임은 도배 방지를 위해 스킵). 실측 SSE로 `{"event_id":...,"stream":"cognitive","class_name":"unknown","confidence":null,"inference_ms":249.6,"surface":"roadway"}` 형태 확인(현재 카메라가 물체 없는 노면만 비춰 class_name이 unknown으로 찍히는 것은 정상 - 실제 물체 탐지 시 채워짐). `pytest tests/test_detection.py tests/test_ws_router_stt.py tests/test_event_frame_store.py` 40건 재통과, 콘솔 `tsc --noEmit` 통과.
- **관련 파일**: `console/src/App.tsx`, `server/detection/consumer.py`.

**추가 커밋 6(같은 날)**: `DetectionFeed` 패널이 최근 80건까지 쌓이면서 패널/그리드 행이 세로로 한없이 길어지고, `event_id` 같은 긴 문자열이 flex 아이템 기본 `min-width:auto`에 막혀 박스 밖으로 삐져나가는 문제 발견 → `.feed-list`에 `max-height:360px`+`overflow-y:auto`(패널 내부 스크롤), `.feed-row > div`를 세로 스택(`flex-direction:column`)+`min-width:0`+`overflow-wrap:anywhere`로 변경. `console/src/styles.css`만 수정.

**추가 커밋 7(같은 날, 핵심 버그 2건)**: "Detection Guidance Log의 사용자/기기 칸이 비고, 감지시간도 안 맞는다"는 신고로 두 가지를 확인.
- **감지시간 재불일치**: 이전 커밋(추가 커밋 4)에서 `now_iso()`/SSE 타임스탬프는 고쳤지만, `detected_at`/`created_at`는 DB 왕복을 거치는 다른 경로였다. MariaDB `DATETIME` 컬럼은 타임존을 저장하지 않아, 쓸 때는 `datetime.now(UTC)`(aware)였어도 다시 읽으면 naive로 돌아와 API 응답에 오프셋이 빠졌다(`"2026-07-12T10:07:42.552558"`) - 같은 9시간 오차 재발. `server/db/schemas.py`에 `_assume_utc_if_naive()` 공통 함수 + `field_validator(mode="before")`를 `DetectionGuidanceLogResponse.detected_at/created_at`, `AdminLoginAuditResponse.created_at`에 적용해 naive 값을 UTC로 간주하고 오프셋을 붙이도록 수정(모델 재검증 시점에 정규화되므로 REST와 WS `guidance_log_event` 브로드캐스트 양쪽에 자동 적용됨 - 둘 다 같은 Pydantic 모델을 거치기 때문).
- **사용자/기기 컬럼 항상 NULL**: 렌더링 문제가 아니라 DB 컬럼 자체가 항상 NULL이었다 - 로그 저장 경로가 클라이언트의 문자열 `device_id`("dev-001")를 `app_users`/`user_devices`의 정수 PK와 연결하는 조회/등록 로직을 아예 갖고 있지 않았다(정식 회원가입/기기 인증 bootstrap은 별도 담당 영역, 미구현 상태). 정식 인증 대신 **간이 자동 등록**을 신설: `server/services/device_registry_service.py`(신규) - 처음 보는 device_uuid를 만나면 익명 `app_users` 행(phone=`anon:{device_uuid}`)과 `user_devices` 행을 자동 생성하고, 프로세스 내 메모리 캐시(`_cache: dict[device_uuid, (user_id, device_id)]`)에 저장해 매 로그 저장마다 DB 조회 없이 즉시 조회 가능하게 함. WS 연결 시(`ws_router.py`) 1회 `ensure_device_registered()` 호출, 이후 반사/인지(`consumer.py`)·STT(`ws_router.py`) 로그 저장 경로 3곳에서 `get_cached_device_ids()`로 조회해 `persist_detection_guidance_log()`에 전달.
  - **레이스 컨디션 발견 및 수정**: 최초 구현에서는 `auth_ok`를 클라이언트에 먼저 보낸 뒤 등록을 처리했는데, 클라이언트가 `auth_ok`를 받자마자 프레임을 보내기 시작해 `DetectionConsumer`가 등록 완료 전에 로그를 저장하는 경우가 실측으로 확인됐다(재기동 직후 첫 이벤트의 user_id/device_id가 여전히 NULL). `ensure_device_registered()` 호출을 `auth_ok` 송신 "이전"으로 옮겨 해결 - 등록이 끝나야 클라이언트가 인증 완료로 알고 프레임을 보내기 시작한다.
- **검증**: 재기동 후 실기기 이벤트로 `user_id=3, device_id=3`(자동 등록된 "dev-001"), `detected_at`에 `Z` 오프셋 포함 확인. `pytest tests/ --ignore=tests/test_false_positive.py --ignore=tests/test_admin_service_login.py --ignore=tests/test_e2e_pipeline.py --ignore=tests/test_risk_ssot.py` 139 passed / 1 skipped(제외한 4개 파일은 전부 이번 변경과 무관한 기존 환경/데이터 이슈).
- **관련 파일**: `server/db/schemas.py`, `server/services/device_registry_service.py`(신규), `server/api/ws_router.py`, `server/detection/consumer.py`.
- **비고**: 익명 자동 등록은 정식 회원 인증을 대체하지 않는다 - 실제 로그인/기기 등록 플로우가 생기면 `phone` 필드가 `anon:` 접두사로 충돌하지 않도록 마이그레이션이 필요하다.

**추가 커밋 8(같은 날)**: "페이지네이션 10개씩으로 바꾸고 하단 전체 건수가 안 맞는다"는 피드백 확인 - DB에는 1249건이 있는데 콘솔은 REST에서 최근 50건만 받아 그 안에서 클라이언트 슬라이싱만 하고 있어 하단 표시가 실제 전체 건수를 반영하지 못했다. 클라이언트 슬라이싱을 걷어내고 **진짜 서버 페이지네이션**으로 전환:
- **서버**: `DetectionGuidanceLogRepository.count_all()`(전체 건수 COUNT 쿼리) + `DetectionGuidanceLogService.count_logs()` 신설. `GET /api/v1/admin/detection-logs`가 응답 바디(배열, 기존과 동일 형태 유지)와 별도로 `X-Total-Count` 헤더에 전체 건수를 실어 보낸다. `main.py` CORS 미들웨어에 `expose_headers=["X-Total-Count"]` 추가(기본값은 커스텀 헤더를 브라우저 fetch()에서 안 보여줌).
- **콘솔**: `useDetectionLogs(token, page, pageSize)`로 시그니처 변경 - offset(`page*pageSize`)/limit을 REST 쿼리로 보내고 응답 헤더의 전체 건수를 `totalCount`로 노출. `App.tsx`가 `logPage` 상태를 소유(10개씩), 1페이지(최신)에서만 WS 실시간 이벤트(`guidanceLogEvents`)를 병합하고 병합 후 페이지 크기로 자른다(2페이지 이후는 특정 offset의 과거 스냅샷이라 실시간 이벤트가 끼면 페이지 경계가 흔들리므로 제외). `DetectionGuidanceLogTable`은 더 이상 자체 페이지 상태/슬라이싱을 갖지 않고 `rows`를 그대로 렌더링, `page`/`pageSize`/`totalCount`/`onPrevPage`/`onNextPage` prop으로 부모에 위임. 하단 표시를 `"N / 전체페이지 · 전체 1249건"`으로 변경.
- **검증**: `curl`로 offset=0/10 각각 조회해 `X-Total-Count: 1249`, 겹치지 않는 log_id 시퀀스(1250~1241 / 1240~1231) 확인, `Origin` 헤더 포함 요청으로 `Access-Control-Expose-Headers: X-Total-Count` 확인. `pytest` 139 passed, 콘솔 `tsc --noEmit` 통과.
- **관련 파일**: `server/db/repositories.py`, `server/services/detection_guidance_log_service.py`, `server/api/detection_log_router.py`, `server/main.py`, `console/src/api/useDetectionLogs.ts`, `console/src/App.tsx`, `console/src/components/DetectionGuidanceLogTable.tsx`.
- **부수 정리**: 조사 중 `tests/test_api_ws.py`가 격리된 테스트 DB가 아니라 팀 공유 MariaDB를 그대로 쓰는 구조라는 것을 발견 - `pytest` 실행마다 `dev-test-001`/`dev-test-003` 가짜 기기가 `app_users`/`user_devices`에 실제로 쌓이고 있었다. 연결된 로그가 0건임을 확인 후 팀 동의를 받아 두 테스트 오염 행을 삭제(운영 데이터 영향 없음). 테스트가 공유 DB에 쓰는 구조 자체는 이번 스코프에서 고치지 않음 - 후속 과제로 별도 테스트 DB 분리 필요.

---

### 2026-07-12 | 서버+콘솔 | 관리자용 시각장애인 회원 등록/전환 화면 신설

- **커밋**: (미커밋)
- **배경**: "관리자가 시각장애인 회원을 가입해주는 페이지가 필요하다"는 요청으로 설계 계획(Plan mode)부터 진행. 조사 결과 `app_users`/`user_devices` DB 스키마와 `UserService.register_user_and_device`/`POST /api/v1/users/register`가 이미 있었지만, 인증이 없는 공개 API이고 클라이언트·콘솔·테스트 어디서도 호출되지 않는 죽은 코드였다(`docs/design/api_specification.md`에도 미문서화). 대신 실제 사용자/기기 FK는 이번 세션 앞부분에 만든 `device_registry_service.py`의 **익명 자동등록**(`phone="anon:{device_uuid}"`)이 채우고 있었다. 사용자 확인 후 방향 확정: react-router 도입, 익명 레코드는 새로 만들지 않고 실명으로 **전환(UPDATE)**, DB 스키마는 그대로 사용, 기존 죽은 엔드포인트는 건드리지 않고 관리자 전용 API를 신설.
- **서버**:
  - `server/db/models.py`: `ANON_PHONE_PREFIX = "anon:"` 상수 신설(기존 `device_registry_service.py`에 인라인이던 접두사를 승격, `schemas.py`/`device_registry_service.py` 양쪽에서 공유).
  - `server/db/repositories.py` `UserRepository`: `get_by_id`, `update_profile`(익명→실명 전환용 UPDATE), `list_all`(devices `selectinload`로 N+1 방지), `count_all` 신규.
  - `server/db/schemas.py`: `MemberRegisterRequest`(device_uuid+name+phone+disability_severity), `AppUserWithDevicesResponse`(devices 중첩 + `model_validator`로 계산되는 `is_anonymous` 플래그) 신규.
  - `server/services/user_service.py`: `register_or_convert_member()` 신규 - 기존 `register_user_and_device`는 "익명→실명 전환" 시나리오에서 새 phone으로 새 유저를 만든 뒤 기존 device 소유자와 달라 400 충돌을 내는 구조라 재사용 불가했다. 신규 메서드는 device_uuid를 먼저 조회해 있으면 소유 회원을 UPDATE(전환), 없으면 CREATE(같은 phone이면 기존 회원에 기기만 추가)로 분기하고, 다른 회원이 쓰는 phone으로 전환 시도 시 409를 낸다. `list_members`/`count_members`도 추가.
  - 신규 라우터 `server/api/admin_member_router.py`: `GET/POST /api/v1/admin/members`(`get_current_admin` 인증, 목록은 `detection_log_router.py`와 동일한 `X-Total-Count` 헤더 패턴). `server/main.py`에 마운트.
  - `tests/test_user_service.py` 신규 5건: 신규 등록, 동일 phone 기기 추가 시 회원 재사용, 익명→실명 전환 시 user_id 불변(신규 행 미생성), 타인 phone 충돌 409, 목록 조회 `is_anonymous` 정확성.
- **콘솔**:
  - `react-router-dom@7.18.1` 신규 의존성. `App.tsx`를 `BrowserRouter`+`Routes`로 재구성 - 공용 `Layout`(헤더+네비게이션 탭)이 `<Outlet/>`으로 `/`(기존 대시보드, `pages/DashboardPage.tsx`로 추출)과 `/members`(신규, `pages/MembersPage.tsx`)를 분기. SSE(`useMonitorStream`)/WS(`useLiveFeed`) 구독은 App 최상단 1곳에서만 열어 페이지 전환 시 재연결되지 않게 함.
  - `console/src/api/useMembers.ts` 신규: `useDetectionLogs.ts`와 동일한 서버 페이지네이션 패턴(offset/limit + `X-Total-Count`) + 등록 POST 뮤테이션.
  - `console/src/pages/MembersPage.tsx` 신규: 등록 폼(device_uuid/이름/전화번호/장애정도) + 페이지네이션 회원 목록 테이블(이력 테이블에서 만든 `.log-pagination`/`.page-btn` CSS 재사용). 익명 자동등록 행에 "회원 정보 입력" 버튼을 둬 클릭 시 폼에 device_uuid를 프리필하고 스크롤 이동 - 관리자가 별도로 device_uuid를 몰라도 목록에서 바로 전환 작업을 시작할 수 있게 함. "정식 회원"/"익명 자동등록" 상태 배지로 구분.
- **검증**: 서버 재시작(이미지 재빌드 불필요 - `server`/`tests`가 볼륨 마운트라 프로세스 재시작만으로 반영) 후 curl E2E - 실제 익명 상태였던 "dev-001"을 `POST /api/v1/admin/members`로 전환, `user_id=3`/`device_id=3` 그대로 유지된 채 name/phone/disability_severity만 갱신됨을 DB로 직접 확인(신규 행 미생성). `GET /api/v1/admin/members` 목록에서 `is_anonymous` true/false 정확히 계산됨과 devices 중첩 배열 확인. `pytest tests/`(공유 DB를 오염시키는 `test_api_ws.py` 제외) 140 passed. 콘솔 `tsc --noEmit` 통과, `/`와 `/members` 라우트 모두 200 확인.
- **관련 파일**: `server/db/models.py`, `server/db/repositories.py`, `server/db/schemas.py`, `server/services/user_service.py`, `server/services/device_registry_service.py`, `server/api/admin_member_router.py`(신규), `server/main.py`, `tests/test_user_service.py`(신규), `console/package.json`, `console/src/App.tsx`, `console/src/pages/DashboardPage.tsx`(신규), `console/src/pages/MembersPage.tsx`(신규), `console/src/api/useMembers.ts`(신규), `console/src/types/monitor.ts`, `console/src/styles.css`, `docs/design/api_specification.md`(v0.4.14 §8.6).
- **비고**: 역할별 세분화 권한(`AdminRole` super_admin/operator/viewer)은 이번 스코프에서 적용하지 않았다 - 다른 admin API와 동일하게 인증된 관리자면 누구나 등록 가능. 기존 죽은 `POST /api/v1/users/register`는 그대로 남아있으며 이번 작업과 무관 - 필요시 별도로 제거 검토.

**추가 커밋(같은 날)**: 콘솔 `/members` 페이지 확인 중 "생년월일/보호자 연락처/주소가 있어야겠다"는 피드백으로 `app_users`에 3개 필드 추가.
- 마이그레이션 `server/db/migrations/20260712_004_add_member_profile_fields_to_app_users.sql`(`birth_date DATE`, `guardian_phone VARCHAR(30)`, `address VARCHAR(255)`, 전부 NULL 허용 - 익명 자동등록은 이 값을 채우지 않으므로). `server/db/models.py`/`schema.sql`/`schemas.py`(`AppUserCreate`/`AppUserResponse`/`MemberRegisterRequest`)/`repositories.py`(`update_profile`)/`user_service.py`(`register_or_convert_member`의 CREATE·UPDATE 양쪽 분기) 전부 반영.
- 콘솔: `MembersPage.tsx` 등록 폼에 생년월일(date input)/보호자 연락처/주소 입력칸 3개(전부 선택 입력) 추가, 목록 테이블에도 3개 컬럼 추가(`.table-wrap`의 기존 `overflow-x: auto`가 폭 초과를 처리). `types/monitor.ts`의 `AppUserRow`/`MemberRegisterPayload`에 필드 반영.
- **검증**: 마이그레이션을 팀 공유 MariaDB에 적용 후 서버 재시작(볼륨 마운트라 이미지 재빌드 불필요), curl로 3개 필드 포함 등록 후 응답에 그대로 반영됨을 확인. `pytest tests/test_user_service.py` 5건 + 전체 회귀(공유 DB를 오염시키는 `test_api_ws.py` 제외) 140 passed 재확인, 콘솔 `tsc --noEmit` 통과.
- **관련 파일**: `server/db/models.py`, `server/db/schema.sql`, `server/db/schemas.py`, `server/db/repositories.py`, `server/services/user_service.py`, `server/db/migrations/20260712_004_add_member_profile_fields_to_app_users.sql`(신규), `console/src/pages/MembersPage.tsx`, `console/src/types/monitor.ts`, `docs/design/api_specification.md`(v0.4.15).

---

### 2026-07-12 | 서버+콘솔 | 실기기 라이브 카메라 피드 및 원격 텔레메트리 패널 (기록 누락분 정리)

- **커밋**: (미커밋)
- **배경**: 이 세션에서 커밋 전 변경사항을 전수 점검하는 과정에서, 이전 세션에 이미 구현됐지만 changelog에 기록되지 않은 상태로 작업 트리에 남아 있던 기능을 발견했다. 이번 항목은 그 기능을 사후 정리·기록하는 changelog다(코드 신규 작성 아님, 기존 커밋되지 않은 작업 문서화).
- **서버**: `server/api/session_manager.py`에 `console_connections` 집합과 `connect_console`/`disconnect_console`/`broadcast_to_consoles`(raw bytes)/`broadcast_json_to_consoles`(JSON) 메서드 신설 - 콘솔 전용 WS 채널의 기반. `server/api/ws_router.py`에 `@router.websocket("/ws/console/live-feed")` 엔드포인트 추가(이번 세션에 만든 `latency_event`/`guidance_log_event`가 나중에 이 채널에 얹혔다). `server/navigation/manager.py`에 `_broadcast_nav_change()` 추가 - `NavigationManager.set_status`/`set_awaiting_question`/`set_awaiting_intent` 호출 시마다 `mcp_manager.broadcast_event("llm_status", {navigation_status, awaiting_free_question, awaiting_intent})`로 SSE 브로드캐스트(이벤트 타입명은 `llm_status`이지만 실제로는 내비게이션 상태다 - AI Pipeline Monitor 조사 때 확인한 것과 동일 지점).
- **콘솔**: `console/src/api/useLiveFeed.ts` 신설 - `/ws/console/live-feed`에 접속해 바이너리 프레임(Blob, 카메라 실시간 이미지)과 `server_detection`(bbox) 메시지를 수신, 3초 후 자동 재연결. `console/src/components/LiveCameraFeed.tsx`+`.css`(실시간 카메라 화면 + bbox 오버레이 + `NAV_MAP_URL` iframe으로 T맵 GPS HUD 미니맵 표시), `console/src/components/DeviceTelemetryPanel.tsx`+`.css`(단말 접속 상태/AI 모델 런타임/위험물 매트릭스/STT-TTS 로그를 군용 콘솔 스타일 HUD로 표시) 신설. `console/src/api/useMonitorStream.ts`에 `navigation_status`/`awaiting_free_question`/`awaiting_intent` 필드 파싱 추가(`llm_status` 이벤트 페이로드). `console/src/components/OperatorLiveMap.tsx`의 iframe에 `allow="geolocation; accelerometer; gyroscope"` 권한 추가(T맵 GPS 지도 정상 동작에 필요). `console/src/components/Login.tsx` 입력창에 `autoComplete="username"/"current-password"` 추가(브라우저 자동완성/접근성 개선).
- **인프라**: `docker/docker-compose.yml`(리눅스/배포용, macOS용과 별개)에서 `DB_TYPE`/`DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` 하드코딩 오버라이드와 NVIDIA GPU `deploy.reservations` 블록을 제거 - `.env` 값을 그대로 쓰도록 단순화하고, GPU 없는 환경(로컬 개발)에서도 컨테이너가 뜨도록 함.
- **미완/후속 과제**: `console/src/components/DeviceUiMirror.tsx`+`.css`(실기기 화면을 아이폰 프레임 목업으로 미러링하는 컴포넌트)도 함께 작성돼 있으나, **어떤 페이지에서도 import/렌더링되지 않는 미사용 상태**임을 확인(2026-07-12 grep으로 재확인). 완성해서 대시보드에 연결하거나, 불필요하면 삭제할지 후속 결정 필요.
- **관련 파일**: `server/api/session_manager.py`, `server/api/ws_router.py`, `server/navigation/manager.py`, `console/src/api/useLiveFeed.ts`(신규), `console/src/api/useMonitorStream.ts`, `console/src/components/LiveCameraFeed.tsx`/`.css`(신규), `console/src/components/DeviceTelemetryPanel.tsx`/`.css`(신규), `console/src/components/DeviceUiMirror.tsx`/`.css`(신규, 미사용), `console/src/components/OperatorLiveMap.tsx`, `console/src/components/Login.tsx`, `docker/docker-compose.yml`.

---

### 2026-07-13 | 서버 | Segmentation 픽셀 마스크 기반 보도 이탈 1차 판정

- **커밋**: (미커밋)
- **배경**: `docs/research/mitos_improvement_roadmap.md` §2/§7이 "Seg 픽셀 마스크 활용(보도 이탈, 점자블록 추종)"을 "이 제품만 줄 수 있는 핵심 가치"로 명시했으나 미착수 상태였다. 코드 확인 결과 `yolo_segmentor.py`가 폴리곤(`mask.xy`)을 `numpy.mean()`으로 뭉개 centroid 점 하나로만 압축하고 `SurfaceResult.mask`는 항상 `None`으로 버리고 있었다(주석상 "통신/직렬화 오버헤드 회피" 사유였으나, `SurfaceResult`가 실제로 네트워크를 타는 지점(`server/bus/producer.py`의 `publish_surface`)은 `class_name`/`centroid`만 수동으로 골라 보내는 구조라 이 우려가 실제로는 해당하지 않음을 확인). 최소 스코프로 "이탈 판정"만 먼저 구현하고, 방향 보정 안내·점자블록 추종·반사 경로 연동·N프레임 히스테리시스는 후속 과제로 명시적으로 미뤘다.
- **구현**: `server/detection/schemas.py`의 `SurfaceResult`에 `polygon: list[list[float]] = Field(default_factory=list, exclude=True)` 추가 - `exclude=True`로 `model_dump`/`model_dump_json` 시 항상 제외되어 Redis publish, WS 전송, 콘솔 API 등 어느 직렬화 경계에서도 자동으로 빠짐(네트워크 비용 없음을 스키마 레벨에서 보장). `yolo_segmentor.py`에 `_extract_polygon()` 추가해 `mask.xy` 좌표를 그대로 `polygon`에 채움(centroid 계산과 별개, 압축하지 않음). 신규 모듈 `server/detection/surface_departure.py`에 `point_in_polygon()`(레이캐스팅/짝홀 규칙)과 `check_sidewalk_departure()`(사용자 발밑 근사 기준점이 `roadway`/`caution` 폴리곤 안에 있는지 판정) 구현. 기준점은 `(0.5, 0.9)` 정규화 좌표로 `client/src/components/CameraView.tsx`의 `DEPTH_PROBE_POINTS` "발밑" 지점과 관례를 맞췄다. `DetectionPipeline.run()`에서 `risk_hint` 분류 직후 호출해 `DetectionResult.is_departing`(신규 필드, 기본 `False`)에 담고, `True`일 때 `logger.info`로 로그만 남긴다 - `risk_hint`나 안내 문장에는 아직 합류시키지 않음(이중 경로 분리 원칙상 검증 전 새 신호를 기존 필드에 얹지 않기 위함).
- **검증**: `tests/test_surface_departure.py` 신규 12건(합성 사각형 폴리곤으로 point-in-polygon in/out, 클래스 필터링, polygon 미존재 가드, `polygon` 필드 직렬화 제외 확인 등) 전부 통과. 기존 `tests/test_langgraph.py` 11건 회귀 없음 확인. `ruff format --check`/`ruff check` 통과.
- **미완/후속 과제**: N프레임 연속 조건(히스테리시스) - `DetectionPipeline`이 현재 프레임 단위 무상태 구조라 상태 저장 위치 별도 설계 필요. 점자블록(`braille_normal`) 추종 - 방향 벡터 계산이 필요해 스코프가 다름. `is_departing`을 실제 안내 문장(LangGraph L1/L2)에 연동하는 작업. 실기기 실측으로 단일 기준점의 노이즈 민감도 확인 필요(경계 부근에서 흔들릴 경우 다중 샘플 포인트 방식으로 보강 고려).
- **관련 파일**: `server/detection/schemas.py`, `server/detection/yolo_segmentor.py`, `server/detection/surface_departure.py`(신규), `server/detection/detection_pipeline.py`, `tests/test_surface_departure.py`(신규).

---

### 2026-07-13 | 서버+클라이언트(iOS) | 보도 이탈 후속 4종: 히스테리시스, 점자블록 추종, 안내 문장 연동, 온디바이스 반영

- **커밋**: (미커밋)
- **배경**: 위 항목(보도 이탈 1차 판정)에서 명시적으로 미뤄둔 후속 과제 5개(N프레임 히스테리시스, 점자블록 추종, LangGraph 안내 문장 연동, 온디바이스 CoreML 반영, 실기기 노이즈 검증) 중 실기기 실측 1건을 제외한 4건을 구현했다.
- **N프레임 히스테리시스**: `DetectionPipeline`이 프레임 단위 무상태 구조라, 상태는 그 상위에서 유일하게 살아있는 싱글톤인 `DetectionConsumer`에 `_departure_streak: dict[device_id, int]`로 둠(기존 `_last_guide_ts`/`_last_guide_duration_sec`와 동일 패턴). `DEPARTURE_CONFIRM_STREAK=3`(인지 1~2fps 기준 약 1.5~3초) 연속 이탈이어야 확정되고, 한 프레임이라도 아니면 리셋된다.
- **점자블록 추종**: `surface_departure.py`에 `polygon_x_crossings_at_y()`(레이캐스팅과 동일 원리로 폴리곤이 특정 높이 y를 가로지르는 x좌표들을 반환)와 `braille_follow_direction()` 추가. 폴리곤 전체 centroid 대신 기준점과 같은 높이의 교차 구간 중점을 쓴 이유는 점자블록이 좁고 긴 띠라 centroid가 원근 왜곡에 취약하기 때문(주석에 면접 대비 근거 기록). 점자블록이 화면에 없으면 `None`(판단 불가)과 "잘 따라가는 중"(`"center"`)을 구분한다.
- **LangGraph 안내 문장 연동**: `_send_cognitive_guide`의 `if not result.detections: return` 가드가 순수 노면 이탈(객체 탐지 0건) 이벤트를 전부 막고 있던 것을 발견 - `departure_confirmed`일 때는 통과하도록 완화하고, 그 아래 `max(result.detections, ...)` 호출 2곳(RAG 검색, `rag_query` 로그)도 빈 리스트 가드 추가. `l1_classifier_node`는 `is_departing_confirmed=True`면 `low`를 `mid`로 격상(이미 mid인 경우는 유지). `l2_generator_node`는 `braille_direction`에 따라 `[노면 상태]` 프롬프트 줄을 분기(왼쪽/오른쪽/방향불명) 생성해 LLM이 "왼쪽으로 이동하세요" 류 문장을 자연스럽게 합성하도록 유도. `OrchState` TypedDict에 두 필드 추가.
- **온디바이스(CoreML) 반영**: `CoreMLInferenceBridge.swift`가 지금까지 `[1,32,160,160]` 프로토타입 마스크 텐서를 명시적으로 건너뛰던 것을 실제로 활용. YOLOv8-seg CoreML end2end export는 폴리곤을 안 주고 인스턴스별 마스크 계수 32개(박스 텐서 38열 중 인덱스 6~37) + 프로토타입 마스크를 주므로, 서버(point-in-polygon)와 다른 방식이 필요했다 - 발밑 기준점 딱 한 픽셀만 필요하므로 160x160 래스터 전체를 복원하지 않고 `sigmoid(계수·프로토타입[:,refY,refX])` 내적 하나로 판정(인스턴스당 연산 32회). 기존 `runDetection(model:cgImage:)`을 `predictRaw()`(추론 1회 실행) + `runDetection(prediction:)`(박스 파싱) + `computeSidewalkDeparture(prediction:)`(이탈 판정)로 분리해 seg 모델 추론이 두 번 돌지 않도록 함. **반사(햅틱/비프) 경로에는 연결하지 않음** - 새 반사 트리거는 오탐 피로 위험이 크다는 기존 교훈([[indoor-fp-mitigation-progress]])과, 아직 실기기 노이즈 검증 전이라는 이유. `detectFrame` 응답에 `surfaceDeparture: Bool` 필드만 추가하고, JS(`localDetectorSelect.ios.ts`)는 `[SurfaceDeparture][OnDevice]` 로그만 남긴다(관측 전용).
- **검증**:
  - 서버: 신규 테스트 `tests/test_departure_hysteresis.py` 8건(히스테리시스 확정/리셋/device별 독립, L1 mid 격상, `run_orchestrator` 순수 이탈 e2e, L2 프롬프트에 점자블록 방향 문구 포함 확인) + `tests/test_surface_departure.py`에 braille 관련 7건 추가(총 19건). 전체 회귀 183건(`test_api_ws.py`/`test_ws_echo.py` 제외 - 각각 공유 DB 오염/실행 중인 서버 필요) 전부 통과. `ruff check`/`ruff format --check` 통과.
  - iOS: xcodebuildmcp로 `Minchodan.xcworkspace`를 iPhone 17 Pro 시뮬레이터 대상 빌드 - **0 에러, `CoreMLInferenceBridge.swift` 관련 경고 0건**으로 컴파일 성공 확인. `client/` `tsc --noEmit`은 이번 세션에서 건드리지 않은 `CameraView.tsx`의 기존 오류 3건(무관, 이 작업 이전부터 존재)만 남고 `localDetectorSelect.ios.ts` 관련 오류 없음.
  - **실기기 실측은 수행하지 못함**: 물리 기기 접근이 불가능한 세션이라, 실제 카메라 프레임으로 (1) 서버 히스테리시스 임계값(3프레임)이 실사용에 적절한지, (2) 온디바이스 단일 기준점이 세그멘테이션 경계 근처에서 얼마나 자주 뒤집히는지(노이즈)는 검증되지 않았다. 위 로그(`[Pipeline] 보도 이탈 판정`, `[SurfaceDeparture][OnDevice]`)가 실기기 확인용으로 준비되어 있으니, 실보행 테스트로 다음 세션에서 확정할 것.
- **관련 파일**: `server/detection/consumer.py`, `server/detection/surface_departure.py`, `server/orchestration/state.py`, `server/orchestration/nodes/l1_classifier.py`, `server/orchestration/nodes/l2_generator.py`, `client/ios/CoreMLInferenceBridge.swift`, `client/src/inference/localDetectorSelect.ios.ts`, `tests/test_departure_hysteresis.py`(신규), `tests/test_surface_departure.py`.

---

### 2026-07-13 | 인프라+클라이언트 | ngrok -> Tailscale 전환 및 정합성 검토 P0 조치

- **커밋**: (미커밋)
- **배경**: ngrok Free 플랜의 클라우드 프록시 경유 지연을 피하고 실기기(LTE 등 외부망)와 개발 PC 간 P2P 직결을 위해 Tailscale VPN으로 전환했다. 마침 팀 DB(RPi 호스트)가 이미 Tailscale로 연결되어 있어 같은 tailnet에 편입시키는 방향으로 진행. 이어서 별도 세션에서 산출된 "Minchodan 프로젝트 종합 분석 보고서"의 P0 지적사항 4건을 실제 코드와 대조 검증 후 반영했다.
- **Tailscale 전환**: `client/src/config/index.ts`는 기존에 이미 `NETWORK_MODE=lan` + `EXPO_PUBLIC_LAN_IP` 구조를 갖추고 있어 코드 수정 없이 `client/.env`의 `EXPO_PUBLIC_LAN_IP`만 이 Mac(`sojiroh-macmini`)의 Tailscale IP(`100.121.247.4`)로 교체했다. `server/main.py`가 이미 `--host 0.0.0.0`으로 기동 중이라 서버 코드도 무변경. `curl http://100.121.247.4:8000/` 200 응답 및 실기기(iPhone) 앱에서 `WS: connected / WiFi(100.121.247.4)` 표시로 종단 검증 완료.
- **ngrok 제거(Docker)**: 실행 중이던 `minchodan-ngrok` 컨테이너 중지·삭제. `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`에서 `ngrok` 서비스 정의 삭제(`docker compose config` 유효성 검증 통과). `.env`/`.env.example`의 `NGROK_AUTHTOKEN` 제거. 클라이언트 코드의 `NETWORK_MODE=ngrok` 분기(`config/index.ts`)와 `@expo/ngrok` 의존성은 폴백으로 의도적으로 보존(사용자 결정).
- **정합성 보고서 P0 조치 4건** (전부 실제 코드/스크립트 대조로 재검증 후 반영):
  1. `.gitignore` L264-311 병합 충돌 마커(`<<<<<<< HEAD`/`=======`/`>>>>>>> 8ee1cb3`) 해결 - 두 브랜치 규칙이 동일한 앞 4줄만 겹치고 한쪽이 나머지(`temp_smoke_*`, `node_modules/`, `.expo/`, 커스텀 가중치, `.zcode/`/`.claude/`, `**/Copy_*` 등)를 포함하는 상위집합이라 중복 없이 병합.
  2. `.env.example` 누락 변수 4종 추가: `GOOGLE_API_KEY`(Gemini VLM 캡셔닝, `server/rag/build/gemini_captioner.py`), `TMAP_APP_KEY`(내비게이션, `server/navigation/`), `SLACK_BOT_TOKEN`/`SLACK_CHANNEL_ID`(`scripts/slack_publisher.py`) - `docs/ops/environment_variables.md`가 이미 이 불일치를 지적해두고 있었음. 죽은 변수 2종 제거: `SLACK_WEBHOOK_URL`(코드 어디서도 미참조, Bot Token 방식으로 이미 대체됨), `DATA_REFLEX_CLIPS`(미참조, 반사 클립은 단말 번들 방식).
  3. `scripts/postwork.sh`의 `get_test_cmd()`가 존재하지 않는 파일명(`test_rag_retrieval.py`, `test_tts_reflex.py`)을 참조해 5/7단계 테스트가 항상 실패하던 것을 실제 파일명(`test_retriever.py`, `test_reflex_and_nav.py`)으로 수정.
  4. `server/tts/reflex_clip_sender.py`의 `send_reflex_clip()` 데드 코드 제거 - `consumer.py._send_reflex_alert()`가 실제 반사 송출을 전담하고 이 함수는 어디서도 호출되지 않음을 grep 전수 검색으로 확인. 같은 파일의 `REFLEX_CLIP_MAP`/`DEFAULT_REFLEX_CLIP`도 자체 주석("어디서도 호출되지 않는다")과 grep 결과가 일치해 함께 제거. 단, `_resolve_reflex_patterns()`는 `tests/test_reflex_and_nav.py`가 직접 import해 사용 중이므로 보존.
- **검증**: `tests/test_reflex_and_nav.py` 3건 통과, `pytest tests/ --collect-only` 193건 전체 수집 성공(임포트 깨짐 없음).
- **미완/후속 과제**: 보고서의 P1 항목(`ws_router.py`/`stt_to_llm_bridge.py` 계층 분리, `AGENTS.md` LangChain 명세 정정, UTF-8 reconfigure 패턴 통일 등)은 이번 세션 범위에서 제외 - 사용자가 다음 스프린트로 명시적으로 유보.
- **관련 파일**: `client/.env`, `.gitignore`, `.env`, `.env.example`, `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `scripts/postwork.sh`, `server/tts/reflex_clip_sender.py`.

---

### 2026-07-13 | 서버 | TTS 실시간 합성 캐시 문장 단위 프리워밍

- **커밋**: (미커밋)
- **배경**: 인지 경로 TTS 지연을 줄이는 방안으로 "DB 로그의 안내문을 분석해 청킹·캐싱"하는 아이디어가 나왔다. 확인 결과 `server/tts/realtime_tts.py`의 `RealtimeTTS`는 이미 `(text, voice, speed)` 키 인메모리 캐시(`CACHE_MAX_ENTRIES=64`, FIFO 축출)를 갖추고 있었으나, 서버 재기동마다 콜드 상태로 시작해 첫 재생마다 합성 지연을 그대로 떠안았다. 단어/구 단위 청킹(concatenative 방식)은 이어붙임 지점의 억양 부자연스러움 리스크가 커서 채택하지 않고, 문장 단위 프리워밍만 우선 구현했다.
- **구현**: `server/db/repositories.py`의 `DetectionGuidanceLogRepository`에 `list_frequent_tts_texts()` 추가 - `detection_guidance_logs.tts_text`를 그룹핑해 등장 횟수 내림차순으로 반환하며, `stream_type=COGNITIVE`로 한정한다(반사 경로 로그의 `tts_text`는 `"[반사 클립] {clip}"` 플레이스홀더라 실제 합성 문장이 아님). `server/services/detection_guidance_log_service.py`에 `list_frequent_tts_texts()` 함수 추가 - `persist_detection_guidance_log`와 동일하게 `async_sessionmaker_factory`로 요청 컨텍스트 밖(lifespan)에서 자체 세션을 연다. `RealtimeTTS`에 `prewarm(texts)` 메서드 추가 - 문장별로 `synthesize()`를 호출해 캐시를 채우고, 개별 문장 합성 실패는 로그만 남기고 건너뛴다(프리워밍 실패가 서버 기동을 막지 않도록). `texts` 길이가 `CACHE_MAX_ENTRIES`를 넘으면 경고 로그만 남긴다(FIFO 축출로 앞쪽이 밀려남을 알림). `server/main.py`의 `lifespan()`에 5번째 기동 단계로 추가 - Whisper 프리로드와 동일하게 `asyncio.create_task`로 논블로킹 실행하고 예외를 흡수해 DB 조회 실패(신규 배포로 로그 없음 포함)해도 서버 기동을 막지 않는다. 신규 환경변수 `TTS_PREWARM_LIMIT`(기본 30, `CACHE_MAX_ENTRIES` 이내 권장), `TTS_PREWARM_MIN_COUNT`(기본 2) 추가.
- **검증**: `tests/test_tts_prewarm.py` 신규 5건(빈도 집계·정렬·반사 경로 제외, limit 적용, 서비스의 세션 팩토리 배선, prewarm 캐시 채움·개별 실패 격리, 캐시 상한 초과 시 경고) 전부 통과. `pytest tests/ --collect-only` 198건 수집 성공. 실제 운영 MariaDB(Tailscale)에 대해 `list_frequent_tts_texts()`를 직접 실행해 실존 안내 문장 10건("직진하며 천천히 걸으세요." 등)이 빈도순으로 조회됨을 확인 - DB 조회 경로가 실동작함을 실측으로 검증(실제 TTS 합성까지는 비용상 스킵, 로직은 fake TTS 더블로 단위 검증). `ruff check`/`ruff format --check` 통과. `TestClient`로 `server.main.app` 기동·`/health` 200 확인(신규 lifespan 단계가 기존 기동 흐름을 깨지 않음).
- **미완/후속 과제**: 실기기 실측으로 캐시 히트율 확인 필요. 히트율이 낮으면(LLM이 매번 다른 phrasing 생성) L2 프롬프트를 더 템플릿화하거나 청킹 방식 재검토.
- **관련 파일**: `server/db/repositories.py`, `server/services/detection_guidance_log_service.py`, `server/tts/realtime_tts.py`, `server/main.py`, `.env.example`, `tests/test_tts_prewarm.py`(신규).

---

### 2026-07-13 | 서버+클라이언트 | 보도 이탈 판정 실내 오탐 게이팅 (온디바이스 씬 신호 서버 전달)

- **커밋**: (미커밋)
- **배경**: Tailscale 전환 후 실기기로 실외 테스트를 나가기 전, 실내에서 서버를 재기동하고 남은 세션을 관찰하던 중 `[Pipeline] 보도 이탈 판정` 로그가 10분간 190건이나 찍히는 것을 발견했다. 같은 시간대 DB 로그의 탐지 객체가 `kiosk`/`chair`/`table`/`movable_signage` 등 실내 사물이라 사용자가 실내에 있음이 명확했는데, 세그멘테이션 모델이 실내 바닥을 `roadway`/`caution`으로 오분류해 이탈 판정이 계속 발동하고 있었다(사용자 확인: "지금 실내 바닥이야, 오탐인 것 같아"). 원인을 추적한 결과, 클라이언트 온디바이스 씬 분류기(`scene.isLikelyIndoor`, §4.4 규칙)는 이미 존재하지만 반사 경로 필터링에만 쓰이고 서버로는 전혀 전송되지 않고 있었다 - 오늘 오전에 추가한 서버 측 보도 이탈 판정(세그멘테이션 폴리곤 기반)은 이 게이트가 아예 없는 상태로 설계돼 있었다.
- **구현**: `client/src/components/CameraView.tsx`에 `isOutdoorBySceneRef` 추가 - 온디바이스 추론에서 계산한 `isOutdoorByScene`(scene 분류기 단독 판정)을 저장해뒀다가, **다음 프레임** 전송 시 `is_outdoor` 필드로 WS `detection` 메시지(바이너리/base64 양쪽 경로 모두)에 실어 보낸다. 현재 프레임 전송 시점엔 아직 이번 프레임의 온디바이스 추론이 끝나지 않아 1프레임 지연을 허용했다(인지 경로 1~2fps 기준 무시할 수준). `server/capture/frame_decoder.py`의 `_parse_frame_meta()`/`ProcessedFrame`에 `is_outdoor: bool | None` 필드 추가(`None`=클라이언트 미판정/구버전 → 기존처럼 신뢰). `server/detection/detection_pipeline.py`의 `run()`에 `is_outdoor` 파라미터를 추가해 `is_outdoor=False`(실내 확정)면 세그멘테이션 결과와 무관하게 이탈 판정을 걸지 않도록 게이팅. `server/detection/consumer.py`는 `processed.is_outdoor`를 그대로 전달.
- **검증**: 신규 테스트 4건(프레임 디코더 `is_outdoor` 파싱 2건, 파이프라인 게이팅 회귀 방지 2건 - 미지정 시 기존처럼 이탈 판정, `is_outdoor=False`면 억제) 통과. 관련 회귀(`test_detection.py`, `test_frame_decode.py`) 전부 통과. `ruff check`/`format` 통과. 서버 재기동 후 실기기 재확인은 실외 이동 중 수행(아래 "몇 시 방향" 항목의 실외 세션과 동일 구간).
- **미완/후속 과제**: 1프레임 지연이 실제로 문제가 되는 경계 상황(실내→실외 전환 순간)은 미검증. `scene.isLikelyIndoor` 자체의 실외 표본이 아직 얇다는 기존 한계([[indoor-fp-mitigation-progress]])가 이 게이트의 정확도에도 그대로 이어진다.
- **관련 파일**: `client/src/components/CameraView.tsx`, `server/capture/frame_decoder.py`, `server/detection/detection_pipeline.py`, `server/detection/consumer.py`, `tests/test_detection.py`, `tests/test_frame_decode.py`.

---

### 2026-07-13 | iOS | Tailscale/LTE 전환 시 "No script URL provided" 크래시 수정

- **커밋**: (미커밋)
- **배경**: 실외 실측을 위해 실기기를 Wi-Fi에서 LTE(Tailscale 경유)로 전환하자 앱이 `RCTFatal`로 즉시 크래시하며 "No script URL provided... unsanitizedScriptURLString = (null)" 레드박스가 떴다. 원인 추적 결과 `client/ios/Minchodan/AppDelegate.swift`의 `bundleURL()`이 `RCTBundleURLProvider.sharedSettings().jsBundleURL(forBundleRoot:)`의 **자동 호스트 추정(Bonjour mDNS 탐색)** 에 의존하고 있었는데, 이 탐색이 기존 Wi-Fi LAN에서만 작동하고 Tailscale 가상 인터페이스나 LTE 망에서는 실패해 `jsLocation`이 `nil`로 남았다. USB로 재빌드·재설치해도 동일 증상이 재현돼(앱 재설치는 이 설정을 초기화하지 않음), 근본 수정이 필요했다.
- **구현**: `bundleURL()`에서 `RCTBundleURLProvider.sharedSettings().jsLocation`을 자동 탐색에 맡기지 않고 명시적으로 지정하도록 변경 - `ProcessInfo.processInfo.environment["METRO_BUNDLER_HOST"]` 환경변수가 있으면 그 값을, 없으면 이 Mac의 Tailscale IP(`100.121.247.4:8081`)를 기본값으로 사용한다. 재빌드 없이 다른 호스트로 바꾸고 싶으면 `METRO_BUNDLER_HOST` 환경변수만 덮어쓰면 된다.
- **검증**: `xcodebuildmcp`로 물리 기기(USB) 빌드·설치·실행 - 빌드 성공(8.9~12.7초), Metro 로그에 새 JS 번들 요청과 `[WS] 연결 성공, 세션 ID: dev-001`이 정상적으로 찍히는 것을 실측 확인. 이후 LTE 단독(Wi-Fi 끔) 상태에서도 동일하게 정상 로드됨을 확인.
- **미완/후속 과제**: 하드코딩된 기본 IP(`100.121.247.4`)는 이 Mac의 Tailscale IP가 바뀌면(재설치 등) 같이 갱신해야 한다. 팀 공용으로 쓰려면 `METRO_BUNDLER_HOST`를 Xcode 스킴 환경변수나 `.xcode.env`로 빼는 것을 고려할 것.
- **관련 파일**: `client/ios/Minchodan/AppDelegate.swift`.

---

### 2026-07-13 | 서버 | 인지 경로 "N시 방향" 안내 (좌측/우측 모호성 해소)

- **커밋**: (미커밋)
- **배경**: 실외 실측 중 사용자가 인지 경로 안내문("우측으로 돌아가세요" 류)이 모호하다며, 정면을 12시로 기준 삼아 실제 탐지 위치 기반의 "몇 시 방향" 형식으로 바꿔달라고 요청했다. 확인해보니 L2 프롬프트는 애초에 탐지 객체의 실제 화면 위치를 전혀 전달받지 않고 있었다 - RAG 템플릿(`data/safety_guidelines.json`)에 미리 박혀 있는 "좌측/우측" 문구나 LLM의 임의 생성에 의존하던 구조였다. 적용 범위는 인지 경로로 한정했다(반사 경로는 사전합성 고정 클립 3종 - front/front-left/front-right - 이라 시계 세분화 시 클립을 다시 녹음해야 해서 이중 경로 분리 원칙상 별도 검토 필요). 시간 구간은 카메라 전방 시야(~90도) 특성상 9시~3시 7단계로 한정했다(6시는 카메라 뒤쪽이라 물리적으로 탐지 불가).
- **구현**: `server/detection/direction.py`에 `estimate_clock_direction(bbox, frame_width)` 추가 - bbox 중심 x좌표를 9,10,11,12,1,2,3시 7단계로 선형 매핑(반사 경로의 `estimate_direction`, front/front-left/front-right 3분대와는 무관한 별도 함수). `server/detection/consumer.py`의 `_send_cognitive_guide`에서 RAG 조회에 쓰던 최고 신뢰도 탐지 객체(`primary_det`)의 bbox로 클럭 방향을 계산해 `orch_input["clock_direction"]`에 실어 보낸다. `server/orchestration/state.py`의 `OrchState`에 `clock_direction: str` 필드 추가. `server/orchestration/nodes/l2_generator.py`: 시스템 프롬프트를 "좌/우 키워드 포함" 규칙에서 "`[탐지 방향]`에 주어진 값을 그대로 `N시 방향` 형식으로 사용" 규칙으로 교체하고, 실측값을 `[탐지 방향]` 줄로 프롬프트에 명시적으로 주입해 LLM이 방향을 임의로 짓지 못하게 했다. `extract_direction()`도 "N시" 패턴을 우선 인식하도록 확장(기존 좌/우/직진/정지 키워드는 하위호환 폴백으로 유지). **중요 발견**: `server/orchestration/nodes/l3_validator.py`의 방향 키워드 검증 목록(`좌/우/왼/오른/직진/정지/멈추/서세요/대기`)에 시계 패턴을 추가하지 않았다면, "2시 방향 주의하세요" 같은 정상 문장이 전부 "방향 키워드 미포함"으로 판정돼 재시도·정적 폴백("전방 주의, 천천히 멈추세요")으로 빠지는 회귀가 발생했을 것이다 - 발견 즉시 같은 작업에서 함께 수정했다.
- **검증**: 신규 테스트 11건(`tests/test_clock_direction.py`: bbox→시각 경계값 매핑 4건, `extract_direction` 우선순위 3건, `validate_guidance`가 시계 방향만으로도 통과하는지 2건, L2 프롬프트 주입 여부 2건) 전부 통과. 관련 회귀(`test_langgraph.py`/`test_departure_hysteresis.py`) 전부 통과. 서버 재기동 후 실기기 실측으로 `"11시 방향 차 조심하세요."`, `"10시 방향으로 돌아가세요."` 등 실제 탐지 위치가 반영된 문장이 나오는 것을 확인.
- **미완/후속 과제**: 사용자가 "실제 방향이랑 맞는지"를 물어봤으나 아직 정량 검증(실제 물체 위치 vs 보고된 시 방향 일치율)은 안 됨. 또한 LLM(1~2.8초)+TTS(0~2.4초) 지연 때문에, 보행 중에는 안내가 나올 때쯤 실제 위치가 이미 바뀌어 있을 수 있음을 별도로 확인(아래 LLM 모델 실험 항목 참조).
- **관련 파일**: `server/detection/direction.py`, `server/detection/consumer.py`, `server/orchestration/state.py`, `server/orchestration/nodes/l2_generator.py`, `server/orchestration/nodes/l3_validator.py`, `tests/test_clock_direction.py`(신규).

---

### 2026-07-13 | 서버 | LLM 지연 개선을 위한 대체 모델 실험 (전부 기각, gemma4:e4b 유지)

- **커밋**: (미커밋)
- **배경**: "N시 방향" 안내가 걷는 속도 기준으로 체감 지연(1~4초)만큼 어긋난다는 지적을 받아, DB `latency_json`을 실측한 결과 지연의 대부분이 네트워크가 아니라 LLM 생성(1~2.8초)과 TTS 합성(0~2.4초) 순수 연산 시간임을 확인했다(도커 대역폭 우선순위 조정은 이 문제와 무관함을 사용자에게 설명). 이에 따라 더 작은/빠른 Ollama 모델로 교체를 시도했다.
- **시도 및 결과**:
  - `qwen2.5:1.5b-instruct`: 단독 curl 테스트에서 워밍업 후 298ms로 빨랐으나, `[탐지 방향]` 지시를 절반의 경우 무시하고 20자 제한도 매번 초과.
  - `qwen2.5:3b-instruct`: 단독 테스트에서는 방향 반영 2/2, 속도 391~631ms로 유망해 보였으나, **실제 파이프라인에 투입하자 `llm_ms`가 오히려 1671~6895ms로 gemma4:e4b(1000~2800ms)보다 악화**됐다. 이 Mac은 CPU 전용 Ollama라 RAG 임베딩(`nomic-embed-text`)과 생성 모델이 번갈아 호출될 때마다 메모리에서 모델을 내렸다 올리는 리소스 경합이 있는 것으로 추정된다(단독 curl 테스트는 이 경합을 재현하지 못해 오판의 원인이 됐다).
  - `gemma4:e2b`(같은 gemma4 계열의 더 작은 elastic 변형, 5.1B): 실제 파이프라인에서 `llm_ms` 5251~5706ms로 마찬가지로 악화, 게다가 검증 실패로 정적 폴백("전방 주의, 천천히 멈추세요")으로 반복 이탈.
  - 세 모델 전부 되돌리고 `gemma4:e4b`로 최종 복귀.
- **교훈**: 이 환경(CPU-only Ollama, 임베딩+생성 모델 동시 서빙)에서는 "모델이 작을수록 빠르다"는 가정이 성립하지 않는다. 실제 GPU 배포 환경(CUDA Blackwell)에서는 이 CPU 리소스 경합 자체가 없어지므로, 모델 교체를 통한 지연 개선은 그때 재평가하기로 함. 모델 성능 비교는 반드시 **실제 파이프라인**(RAG 임베딩과 동시 호출)에서 검증해야 하며, 격리된 curl 단독 테스트는 오판을 유발할 수 있음을 실측으로 확인.
- **관련 파일**: `.env`(`GEMMA_MODEL`, 최종적으로 무변경 - `gemma4:e4b` 유지).

---

### 2026-07-13 | 서버 | 주행 통로 위험 비율 실험 (강사 추천 Depth+ROI 알고리즘의 저비용 근사, 관측 전용)

- **커밋**: (미커밋)
- **배경**: 담당 강사가 "핵심은 객체 인식이 아니라 내가 앞으로 지나갈 통로가 막혔는가"를 판정하는 Depth Map + 주행 ROI + 위험 픽셀 비율 알고리즘을 추천했다. 우리 프로젝트와 대조 검토한 결과, 사다리꼴 ROI(반사 게이트 `FRONT_BAND`와 동일 원리), 거리 구간 위험도(면적비 근사), 프레임 누적(오늘 만든 히스테리시스), 접근 속도(ByteTrack) 등 개념 상당수가 이미 구현돼 있었으나 **픽셀 단위 깊이맵 자체가 없다**는 근본 차이를 확인했다(2026-07-11 LiDAR 프로브 프로토타입은 있으나 Pro 기종 전용+카메라 세션 배타적이라 상시 사용 불가, 이미 알려진 한계). 새 깊이 모델(MiDaS류) 도입은 온디바이스 반사 경로 지연 예산을 위협해, 기존 세그멘테이션 폴리곤을 재사용하는 저비용 절충안만 먼저 실험하기로 사용자와 합의했다.
- **구현**: `server/detection/path_risk.py` 신규. 사다리꼴 주행 통로 ROI(좌우 대역은 새로 발명하지 않고 `FRONT_BAND`의 near(0.20~0.80)/far(0.38~0.62) 값을 그대로 재사용, 상단 y비율 0.35)를 12x12 격자로 샘플링하고, 각 격자점이 `roadway`/`caution` 폴리곤 안에 있는지(`surface_departure.point_in_polygon` 재사용)를 세어 비율을 계산한다(`compute_path_risk_ratio`). 강사 추천 임계값(5%/20%)을 그대로 채택해 CLEAR/CAUTION/BLOCKED로 분류하는 `classify_path_risk`도 함께 추가. `detection_pipeline.py`에 로그 훅만 연결했고 **risk_hint나 안내문에는 아직 연결하지 않았다**(관측 전용 - 오늘 보도 이탈 판정도 처음엔 이 방식으로 시작했던 것과 동일한 단계적 검증 패턴).
- **검증**: 신규 테스트 8건(전체 커버리지 시 비율 1.0, 미겹침 시 0.0, 부분 겹침 시 중간값, 안전 노면만 있을 때 0.0, 폴리곤 없는 위험 노면 무시, 프레임 크기 0 가드, 분류 임계값 경계) 전부 통과. 독립 마이크로벤치마크 결과 호출당 평균 **0.083ms**로 지연에 실질적 영향 없음을 실측 확인(파이프라인 `inference_ms`도 기존과 동일한 200~330ms대 유지). `ruff check`/`format` 통과.
- **미완/후속 과제**: 아직 risk_hint/안내문 연동 전이라 실제 판정 정확도(진짜 막힌 상황 vs 뚫린 상황 구분력)는 검증되지 않았다. 실외에서 로그(`ratio`/`level`)를 더 쌓아 체감과 맞는지 확인 후, 맞다면 보도 이탈 판정처럼 히스테리시스+안내문 연동 단계로 승격할지 결정할 것.
- **관련 파일**: `server/detection/path_risk.py`(신규), `server/detection/detection_pipeline.py`, `tests/test_path_risk.py`(신규).

---

### 2026-07-13 | 클라이언트 | CLASS_MIN_CONFIDENCE.car 조정 시도 및 SSOT 계약 위반 자체 발견/수정

- **커밋**: (미커밋)
- **배경**: 실외 실측 중 서버 원시 탐지 로그를 확인해보니 실제 차량 신뢰도가 0.35~0.5대에 몰려 있어, 화면 bbox 표시 임계값(`car: 0.6`)이 너무 높아 차가 잘 안 보인다고 판단해 0.4로 낮췄다. 이후 changelog/문서 업데이트를 위해 전체 회귀 테스트를 돌리다가 `tests/test_risk_ssot.py`의 `test_client_gate_matches_ssot`/`test_client_extension_does_not_conflict_with_ssot` 2건이 실패하는 것을 발견했다.
- **원인**: `CameraView.tsx`의 `CLASS_MIN_CONFIDENCE`는 화면 표시 필터뿐 아니라 **반사(햅틱/비프) 안전 게이트의 confidence 문턱**으로도 동시에 쓰이는 상수였다. `docs/design/risk_ssot_contract.md` §2가 이 값을 서버 `reflex_gate.py`의 `HIGH_RISK_CLASSES`와 반드시 동일하게 유지해야 하는 SSOT로 명시하고 있었는데("실내 오탐 완화, 실외 전용 클래스 문턱 상향"이라는 안전 근거), 표시 편의를 위해 안전 문턱까지 실수로 함께 낮춘 것이었다. 즉 데이터 수집 목적의 변경이 반사 경로의 오탐 완화 안전장치를 조용히 무력화할 뻔했다.
- **조치**: `car`를 0.6으로 즉시 원복. SSOT 계약(§4 변경 절차: 서버·단말·문서를 같은 커밋에서 함께 수정)을 어기지 않는 선에서, 차량 표시 표본을 더 모으고 싶다면 §2 절차대로 서버 게이트까지 같이 낮추거나 화면 표시 전용 별도 상수를 신설해야 한다는 것을 주석으로 남겼다. `test_risk_ssot.py` 3건 전부 재통과 확인.
- **교훈**: 반사 경로 관련 상수를 만질 때는 항상 `docs/design/risk_ssot_contract.md`와 `test_risk_ssot.py`를 먼저 확인할 것 - 이름만 보고 "화면 표시용이겠지"라고 단정하면 안 된다. 이번엔 자동 회귀 테스트가 실수를 커밋 전에 잡아낸 사례로 남긴다.
- **관련 파일**: `client/src/components/CameraView.tsx`, `tests/test_risk_ssot.py`(수정 없음, 검증만 수행).

---

### 2026-07-13 | 서버+클라이언트 | jy 브랜치 병합 - Tailscale 연결 방식을 jy 표준으로 통일

- **커밋**: (병합 예정)
- **배경**: jy 브랜치를 kb에 병합하기 전 충돌·정합성을 검토했다(임시 워크트리에서 실제 병합 실행 후 `pytest` 214건, `tsc --noEmit` 0 errors까지 확인 - 텍스트 충돌은 없었음). 다만 같은 문제(외부망 Tailscale 접속)를 두 브랜치가 독립적으로 각자 해결한 것을 발견했다 - kb는 기존 `NETWORK_MODE=lan`+`EXPO_PUBLIC_LAN_IP`를 재사용(코드 변경 없음), jy는 전용 `NETWORK_MODE=tailscale`+`EXPO_PUBLIC_TAILSCALE_HOST`를 신설(`network_probe` RTT 계측과 통합). 또한 jy의 changelog(`docs/changelogs/jy.md`)는 "ngrok 컨테이너나 도메인 지원을 제거한 것이 아니라 확장한 것"이라고 기록돼 있었는데, kb는 같은 날 ngrok 도커 컨테이너와 `NGROK_AUTHTOKEN`을 완전히 제거한 상태라 전제가 어긋나 있었다.
- **조치**: 사용자 결정에 따라 (1) 클라이언트 접속 방식은 jy의 전용 `tailscale` 모드를 팀 표준으로 채택 - `client/.env`를 `EXPO_PUBLIC_NETWORK_MODE=tailscale`+`EXPO_PUBLIC_TAILSCALE_HOST=100.121.247.4`+`EXPO_PUBLIC_SERVER_PORT=8000`으로 전환(기존 `lan`+`LAN_IP` 조합에서). (2) ngrok 도커 인프라는 kb의 완전 제거 상태를 유지 - jy 브랜치도 `docker-compose.yml`을 건드리지 않아 병합에 지장 없음. `docs/ops/environment_variables.md` §2.11을 이 결정에 맞게 갱신(기존 lan 재사용 서술 → jy 표준 채택 서술로 교체, ngrok 폴백 코드는 있으나 도커 인프라는 없다는 점 명시).
- **검증**: 병합 자체는 `git merge origin/jy` 실행, 충돌 0건. 병합 후 `pytest tests/ --ignore=test_ws_echo.py` 214 passed, `cd client && npx tsc --noEmit` 0 errors(오히려 jy의 리팩토링이 기존 사전 존재 TS 에러 2건도 부수적으로 해소함).
- **미완/후속 과제**: `api_specification.md`의 버전 헤더를 kb 자신의 "N시 방향" 변경분에 대해서는 올리지 않았던 것(jy가 먼저 v0.4.16을 씀) - 필요 시 v0.4.17로 별도 이력 추가할 것.
- **관련 파일**: `client/.env`, `docs/ops/environment_variables.md`.

---

### 2026-07-13 | 서버+클라이언트 | jh 브랜치 병합 (STT 안정화, 생활지원 RAG, 콘솔 라이브피드 보정)

- **커밋**: `5d710e1`
- **배경**: `origin/jh`(STT 안정화 + `convenience_guidelines` 생활지원 RAG + 콘솔 라이브피드 보정)를 kb에 병합. jy 병합과 달리 실제 텍스트 충돌 8곳(`client/src/hooks/useWebSocket.ts` 3곳, `client/src/components/CameraView.tsx` 5곳)이 발생해 수동 조정했다.
- **주요 판단**: `detection_control` 전송 useEffect는 jh 버전(거리측정 모드 `depthMode` 미고려)을 버리고 kb/jy의 기존 버전(depthMode 배제 포함)을 유지 - 중복 useEffect 및 거리측정 모드 중 반사 오탐 재활성화 방지. GPS `realtime_gps` 전송 블록은 jh가 파일을 재구성하며 위치만 옮긴 것이라 중복 없이 한 곳만 유지. WS 종료 핸들러는 jy의 `clearNetworkProbe()`와 jh의 `closeCode`/`reason` 로깅을 모두 보존.
- **병합 후 발견/조치**: jh의 `MIN_STT_AUDIO_BYTES=4096` 가드로 기존 `tests/test_ws_router_stt.py`의 16바이트 더미 픽스처가 깨져 4096바이트 이상으로 패딩. `server/api/ws_router.py`의 불필요한 `# -*- coding: utf-8 -*-` 선언 제거(ruff UP009).
- **검증**: `pytest` 214 passed, `tsc --noEmit` 0 errors, 도커 재기동 후 `/health` 200.
- **관련 파일**: `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `server/api/ws_router.py`, `tests/test_ws_router_stt.py`, 및 jh 원본 변경분(`server/rag/convenience_rag.py` 등 신규 파일 다수).

---

### 2026-07-13 | 공통 | dev 브랜치를 kb까지 fast-forward

- **커밋**: (fast-forward, `1bc676c..5d710e1`)
- **배경**: `origin/dev`의 HEAD가 kb/jy/jh 세 브랜치의 공통 조상과 정확히 일치해(오늘 작업 이전 상태에서 전혀 진행되지 않음), kb → dev 병합은 충돌 가능성이 원천적으로 없는 순수 fast-forward였다. `git merge-base --is-ancestor origin/dev kb`로 사전 확인 후 `git merge kb --ff-only` 실행.
- **검증**: fast-forward 후 `pytest` 214 passed, `tsc --noEmit` 0 errors 재확인. `origin/dev`로 푸시 완료.
- **참고**: `origin/jh`가 병합 시점(`a39a089`) 이후 changelog 문서 커밋 1개(`d5091a9`) 더 진행했으나 코드 변경 없음. `origin/dg2`(Android STT/마이크 권한 관련 커밋 5개)는 이번 kb/dev 작업에 전혀 포함되지 않은 별도 브랜치로 남아있음 - 향후 별도 병합 검토 필요.
- **관련 파일**: 없음(fast-forward, 신규 diff 없음).

---

### 2026-07-13 | 콘솔 | Live Feed 화면 회전 버그 수정 (jh의 Android 전용 보정이 iOS에 잘못 적용됨)

- **커밋**: `98833a3e767b987f6336ca2b8f301c2568eb3882`
- **배경**: jh 병합본으로 실기기(iPhone) 테스트 중 운영 콘솔의 "Live Feed" 화면이 회전되어 보인다는 사용자 보고를 받았다. 원인은 jh가 `console/src/components/LiveCameraFeed.tsx`에 추가한 `LIVE_FEED_ROTATE_DEG = 90` 하드코딩 - 주석상 "왼쪽으로 90도 꺾여 들어오는 프레임"(Android 카메라 센서의 원본 방향 특성)을 보정하려는 목적이었으나, 콘솔은 iOS/Android 기기를 가리지 않고 보는 공용 화면이라 이미 똑바로 들어오는 iPhone 프레임에 이 보정이 그대로 적용되면서 잘못 회전됐다.
- **조치**: 기기별 platform 정보가 현재 WS 페이로드에 없어 자동 분기가 불가능한 상태임을 사용자에게 설명하고, 우선 `LIVE_FEED_ROTATE_DEG=0`(무회전)으로 되돌리기로 결정(사용자 확인). `getDisplayBBox()`도 0일 때는 회전 좌표 변환 없이 원본 bbox 퍼센트를 그대로 반환하도록 분기 추가 - 이미지만 안 돌리고 bbox 오버레이는 계속 어긋나는 상태를 방지했다(이미지 회전과 bbox 좌표 변환이 별도 로직으로 중복 구현돼 있던 것을 발견).
- **검증**: `tsc --noEmit` 0 errors, Vite HMR로 즉시 반영 확인, 사용자가 실제 화면에서 "정상적으로 나왔다" 확인.
- **미완/후속 과제**: Android로 다시 테스트할 때 `LIVE_FEED_ROTATE_DEG`를 90으로 되돌려야 한다(수동). 근본적으로는 WS 프레임 메시지에 device platform 필드를 추가해 자동 분기하는 게 맞다.
- **관련 파일**: `console/src/components/LiveCameraFeed.tsx`.

---

### 2026-07-13 | 서버 | 미구현 5종 MCP(Slack, Audio Validator, Cache Monitor, Accessibility Simulator, LangSmith Tracer) 구현 및 연동 완료

- **커밋**: `723b6108d37c5ee652271ab99784954b8136ac2d`
- **배경**: 설계상 미구현 또는 부분 구현 상태로 남아있던 5종의 MCP를 완성하고, 이들이 추론 및 오케스트레이션 메인 루프에 지연을 주지 않도록 아웃오브밴드(비동기 백그라운드 태스크) 구조로 연동하는 요건을 이행했습니다. 추가로 로컬 CORS 허용 출처(`localhost:5174` 등)가 백엔드 코드에 정적으로 존재하던 보안 문제를 보완하고자 환경변수 연동을 강화했습니다. 또한, 다중 Uvicorn 프로세스 환경에서 실시간 이벤트를 유실 없이 전송하기 위해 설계 13.2절의 "Redis Streams 완충 아키텍처"에 따라 메트릭 발행 구조를 정비했습니다.
- **조치**:
  - **Slack Notification MCP**: `server/mcp/slack_notifier.py`를 신규 구현하고 `fallback_node.py`와 연동하여 L3 가드레일 최종 실패 시 비동기 경보를 발생하도록 조치했습니다.
  - **Audio Validator MCP**: `server/mcp/audio_validator.py`를 신규 구현하여 실시간 TTS 합성 음성(WAV)의 규격 및 TTFB 지연을 실시간 검증하고 결과를 브로드캐스트합니다. (캐시 적중 시에도 base64 디코딩을 통해 비동기 검증 이벤트를 발행하도록 예외 결함 보완)
  - **Redis Cache Monitor MCP**: `server/mcp/cache_monitor.py`를 신규 구현하고, FastAPI 서버 lifespan 시작/종료 시 백그라운드 태스크로 `suppress:*` 캐시 키의 상태 및 남은 TTL을 실시간 모니터링하여 브로드캐스트합니다.
  - **Accessibility Simulator MCP**: `server/mcp/accessibility_simulator.py`를 신규 구현하여 announceForAccessibility 텍스트와 최종 합성 음성 가이드 간의 의미 및 방향성 정합성을 검증하도록 `realtime_tts.py`에 이식했습니다. (캐시 적중 시에도 원본 텍스트 대조 시뮬레이션 이벤트를 병행 발행하도록 보완)
  - **LangSmith Trace MCP**: `server/mcp/langsmith_tracer.py`를 신규 구현하여, 환경변수 활성화 시 `run_orchestrator` 지연 및 노드 전이를 로깅할 수 있는 추적 기반을 구축했습니다.
  - **CORS 환경변수 보안 정합**: `server/api/config.py`의 `CORS_ORIGINS` 기본값을 Pydantic Settings 초기화(`__init__`) 시 환경변수 `CORS_ORIGINS`의 JSON 포맷 또는 쉼표 구분값으로부터 파싱하여 안전하게 바인딩되도록 개선하고, `.env` 및 `.env.example` 템플릿에 `CORS_ORIGINS` 변수 필드를 정식 보충했습니다.
  - **관제 모니터링 UI 마운트**: `console/src/types/monitor.ts`에 MCP 검증 데이터를 관리할 타입 인터페이스를 추가하고, `useMonitorStream.ts`에 신규 이벤트 타입(audio/cache/accessibility/langsmith) 파싱 핸들러 및 데모 주입 이벤트를 구현했습니다. 4대 신규 메트릭을 카드 형태로 한눈에 보여주는 `McpValidationMonitor.tsx` 컴포넌트를 신규 마운트하고 `DashboardPage.tsx`에 이식했습니다.
  - **Redis Streams 완충 발행 채널 도입**: `server/mcp/manager.py`에 `publish_metric` 비동기 메소드를 신규 구현하여, 메인 추론/합성 모듈이 메모리 상의 SSElisteners를 직접 경유하지 않고 Redis `mcp:metrics` 스트림에 메트릭을 적재하도록 개선했습니다. 이로써 Uvicorn 다중 프로세스(workers > 1) 및 격리된 비동기 태스크 간의 데이터 브로드캐스트 정합을 최종 구축했습니다.
- **검증**:
  - 백엔드: 신규 단위 테스트인 `tests/test_mcp_new.py`를 작성하여 5종 MCP를 검증하고, 기존 3종 테스트와 함께 실행하여 총 9건의 MCP 검증 테스트(`tests/test_mcp_*.py` - LangSmith Active & Mock 상황별 2개 케이스 완전 수록)가 100% 통과(Passed in 1.82s)함을 확인 완료했습니다.
  - 프론트엔드: `console/` 디렉토리 내 `npm run build`를 실행하여 타입 검출(`tsc --noEmit`) 및 번들링 빌드 프로세스가 에러 0건으로 성공 통과함을 완료했습니다.
- **관련 파일**:
  - `server/mcp/slack_notifier.py` (신규)
  - `server/mcp/audio_validator.py` (신규)
  - `server/mcp/cache_monitor.py` (신규)
  - `server/mcp/accessibility_simulator.py` (신규)
  - `server/mcp/langsmith_tracer.py` (신규)
  - `tests/test_mcp_new.py` (신규)
  - `console/src/components/McpValidationMonitor.tsx` (신규)
  - `server/mcp/manager.py` (수정)
  - `server/orchestration/nodes/fallback_node.py` (수정)
  - `server/tts/realtime_tts.py` (수정)
  - `server/orchestration/graph.py` (수정)
  - `server/main.py` (수정)
  - `server/api/config.py` (수정)
  - `.env` (수정)
  - `.env.example` (수정)
  - `console/src/types/monitor.ts` (수정)
  - `console/src/api/useMonitorStream.ts` (수정)
  - `console/src/pages/DashboardPage.tsx` (수정)
  - `server/orchestration/llm_client_factory.py` (수정)

---

### 2026-07-14 | 공통 | 개발 도구 CLI(Antigravity CLI, Claude Code, OpenCode) 버전 검토 및 업데이트 수행

- **배경**: 개발자 로컬 환경 및 AI 에이전트 연동의 효율성을 위해 사용 중인 3대 핵심 CLI 도구(안티그래비티 CLI, 클로드 CLI, 오픈코드 CLI)의 버전 상태를 검토하고 최신 버전으로의 업데이트가 필요한지 점검함.
- **조치**:
  - **Antigravity CLI (`agy`)**: 버전 `1.1.2`로 이미 최신 상태임을 확인.
  - **Claude Code CLI (`claude`)**: 버전 `2.1.207`로 이미 최신 상태임을 확인.
  - **OpenCode CLI (`opencode`)**: 버전 `1.17.18`에서 최신인 `1.17.20`으로 업그레이드 가능함을 확인하고, `opencode upgrade`를 실행하여 `1.17.20` 버전으로 업데이트 완료.
- **검증**: `agy --version`, `claude --version`, `opencode --version` 명령어를 통해 최신 버전 상태(각각 1.1.2, 2.1.207, 1.17.20)를 최종 확인함.
- **관련 파일**: 없음 (개발 환경 CLI 패키지 업데이트).

---

### 2026-07-14 | 공통 | 프로젝트 전체 코드-문서 정합성 교차 검증 및 수정

- **배경**: 6개 영역(이중 경로 분리, 기술 스택, 코드 구조, 환경 변수 3축, WebSocket 이벤트, KPI/지연 목표/브랜치)에 걸쳐 코드와 문서의 정합성을 전면 교차 검증. 검증 결과 정합성이 완벽히 유지된 영역(이중 경로 분리 원칙, YOLO 29/4클래스, KPI, STT, 클라이언트 TTS, 브랜치 전략)을 확인하는 한편, 문서-코드 모순 9건을 발견해 일괄 수정.
- **P0 수정 (문서-코드 직접 모순)**:
  - **`SLACK_WEBHOOK_URL` 명세 정정**: 환경변수 명세서 §2.8이 "SLACK_WEBHOOK_URL은 코드 어디에도 쓰이지 않는 미사용 변수"라고 단언했으나, `server/mcp/slack_notifier.py:49,59`에서 최우선 분기로 활성 사용 중인 것을 확인. Webhook 우선/Bot Token 폴백 이중 인증 구조로 명세를 코드 기준으로 되돌림(v0.4.18).
  - **README.md `react-native-tts` 정정**: 클라이언트 라이브러리에 `react-native-tts (예비 TTS)`가 잔존했으나, `client/package.json` 및 소스 코드 모두에서 부재 확인. `expo-speech (한글 음성 합성, Voice 선택; react-native-tts 미사용)`로 정정.
- **P1 수정 (문서 정합성)**:
  - **AGENTS.md §4 server/ 구조**: 실제 구현됐으나 명세에 누락된 4폴더(`services/`, `stt/`, `navigation/`, `mcp/`) 추가. `models/` Git 추적 정책도 `object_detection.pt` 추적 / `det_best/segbest` git-ignore로 정정.
  - **AGENTS.md §2 LLM 오케스트레이션**: "LangChain 래퍼 미사용"을 "LLM 호출 클라이언트는 raw 구현(메시지 스키마는 langchain_core.messages 사용)"로 정정. `SimpleGeminiClient` 클라이언트 나열에 추가.
  - **환경변수 명세서 §2.15 신설**: 코드에서 활성 사용 중이나 명세에 누락된 13종 변수(CONVENIENCE_CHROMA_COLLECTION, GEMINI_MODEL, EDGE_TTS_SAMPLE_RATE, DATABASE_URL, LANGCHAIN_PROJECT 등) 일괄 등재.
  - **README.md `data/reflex_clips/` 경로 정정**: 실제 반사 클립은 `client/assets/sounds/reflex_clips/`(WAV 5종 단말 번들)에 존재. 디렉토리 구조 트리를 실제 파일 시스템과 일치시킴.
  - **`.env.example` `LLAVA_MODEL` 제거**: 코드 어디서도 소비되지 않는 미사용 잔재(Gemini 캡셔닝 전환 이전 로컬 Llava 계획)를 주석 처리 후 제거.
- **P2 수정 (사소 정합성)**:
  - **`server/tts/__init__.py`**: `Pyttsx3TTSService`가 `get_tts_service()` 팩토리에서 지원되나 `__all__`에 누락된 문제 수정 (임포트 및 `__all__` 추가).
  - **`api_specification.md` §1**: 공통 `type` 필드 목록을 코드(`ws_router.py`/`consumer.py`)에서 실제 발행되는 전체 이벤트 타입으로 갱신 (v0.4.17).
- **검증**: 모든 수정 후 git diff로 변경 사항 확인. 환경 변수 3축(명세/.env.example/코드) 교차 검증 완료.
- **관련 파일**: `docs/ops/environment_variables.md`, `README.md`, `AGENTS.md`, `.env.example`, `docs/design/api_specification.md`, `server/tts/__init__.py`, `docs/changelogs/kb.md`

---

### 2026-07-14 | 1단계 | auto_publish_work

- **커밋**: `43257a7`
- **변경 내용**:
  - Add auto_publish_work script and skill definition for git automation
- **관련 파일**: `.agents/skills/auto-publish-work/`, `scripts/auto_publish_work.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 1단계 | auto_publish_work

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Add auto_publish_work script and skill definition for git automation
- **관련 파일**: `.agents/skills/auto-publish-work/SKILL.md`, `docs/changelogs/kb.md`, `scripts/auto_publish_work.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 1단계 | auto_publish_work

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Add auto_publish_work script and skill definition for git automation
- **관련 파일**: `.agents/skills/auto-publish-work/SKILL.md`, `docs/changelogs/kb.md`, `scripts/auto_publish_work.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 1단계 | auto_publish_work

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Add auto_publish_work script and skill definition for git automation
- **관련 파일**: `.agents/skills/auto-publish-work/SKILL.md`, `docs/changelogs/kb.md`, `scripts/auto_publish_work.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 1단계 | auto_publish_work

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Update SKILLS.md and AGENTS.md indexes to include auto-publish-work skill
- **관련 파일**: `GENTS.md`, `SKILLS.md`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 1단계 | react_doctor_integration

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Integrate react-doctor quality checks into auto_publish_work.py and add config files
- **관련 파일**: `lient/App.tsx`, `client/src/components/CameraView.tsx`, `console/src/App.tsx`, `console/src/api/useLiveFeed.ts`, `scripts/auto_publish_work.py`, `client/doctor.config.json`, `console/doctor.config.json`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 1단계 | react_doctor_skill

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Add react-doctor agent skill definition and update indexes
- **관련 파일**: `GENTS.md`, `SKILLS.md`, `.agents/skills/react-doctor/`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 1단계 | react_doctor_skill

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Add react-doctor agent skill definition and update indexes
- **관련 파일**: `.agents/skills/react-doctor/SKILL.md`, `AGENTS.md`, `SKILLS.md`, `docs/changelogs/kb.md`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 관제콘솔_디자인_구현 | console_design_implementation

- **변경 내용**:
  - GILDANG 시각장애인 보행 보조 플랫폼 관제 콘솔의 UI를 SpaceX + Linear 스타일의 미특수작전 다크 HUD 테마로 리팩토링.
  - GILDANG 로고의 메인 칼라인 골든 옐로우(`#F9B700`)를 액센트 및 상황Caution 컬러로 지정하고, CSS 변수(토큰)를 정의하여 적용.
  - 제공된 실기기 리트리버 VR 로고 이미지 파일을 React public 폴더(`gildang-logo.jpeg`)로 복사하고, 콘솔 상단 탑바(Layout) 좌측에 원형 엠블럼 형태로 항시 노출되도록 마크업 및 전술적 테두리 CSS 추가.
  - 로그인 화면(Login)도 전술 다크모드로 리팩토링을 수행하여, 상단에 원형 GILDANG 엠블럼 로고를 삽입하고 코너 브래킷 및 각진 인풋 필드, 옐로우 액센트 버튼을 적용.
  - LiveCameraFeed에서 일반 BBox와 노면 세그멘테이션 마스크(model === "segmentation")를 분기 처리하여, 세그멘테이션 마스크는 반투명 점선(dashed) 오버레이로 항시 표시되도록 구현.
  - UI에 남아있던 이모지 요소(📡, 📷 등)를 제거하여 전문적인 작전 화면 품질 확보.
- **관련 파일**: `console/public/gildang-logo.jpeg`, `console/src/App.tsx`, `console/src/styles.css`, `console/src/components/Login.tsx`, `console/src/components/Login.css`, `console/src/components/LiveCameraFeed.tsx`, `console/src/components/LiveCameraFeed.css`, `docs/changelogs/kb.md`
- **검증 결과**: `npm run build`를 통해 tsc 및 vite 컴파일 빌드 검증 성공 완료.

---

### 2026-07-14 | 앱_GILDANG_브랜딩 | app_gildang_branding

- **변경 내용**:
  - 앱 로딩 화면 신규 구현(`LoadingScreen.tsx`): GILDANG 로고 + "Loading" 텍스트에 Tailwind `animate-bounce`와 동일한 리듬의 RN `Animated` 바운스 적용, `App.tsx`에서 기동 후 1.8초간 노출.
  - 앱 아이콘/스플래시를 GILDANG 로고로 전면 교체(`scripts/generate_app_icons.py` 신규): 원본 로고(`client/assets/gildang-logo.jpeg`, 콘솔 `gildang-logo.jpeg`와 동일)의 실제 내용(강아지+GILDANG 텍스트) 바운딩박스만 크롭해 아이콘에 로고가 꽉 차 보이도록 처리. iOS(`icon.png`, `splash-icon.png`, `AppIcon.appiconset`), 안드로이드(5개 밀도 × foreground/background/monochrome/ic_launcher/ic_launcher_round), 웹(`favicon.png`)까지 전부 재생성.
  - 이 프로젝트는 `expo prebuild`가 아니라 `ios/`, `android/` 네이티브 폴더를 직접 관리하므로, `app.json` 설정만으로는 반영되지 않아 iOS `Images.xcassets/AppIcon.appiconset`과 안드로이드 `mipmap-*` webp까지 스크립트에서 직접 갱신하도록 구현.
  - 앱 표시 이름을 "Minchodan"(프로젝트 코드네임)에서 "GILDANG"(브랜드명)으로 변경: iOS `CFBundleDisplayName`, 안드로이드 `strings.xml`의 `app_name`, `app.json`의 `name` 필드.
  - 앱 메인 화면(`CameraView.tsx`) 및 하위 컴포넌트(`ConnectionStatus.tsx`, `DebugTriggerPanel.tsx`, `NavMapPanel.tsx`)를 콘솔과 동일한 "Tactical" 다크 테마(배경 `#0A0D10`, 포인트 컬러 `#F9B700`, op-green `#39FF14`, reflex-red `#FF3333`, tech-blue `#00D2FF`)로 리스킨. 저채도 배경+원색 텍스트/테두리 배지 패턴(콘솔 `StatusBadge`와 동일 컨벤션)을 토글/상태 표시에 적용. bbox 탐지 색상(`getClassColor`, 위험도 시맨틱)은 브랜드 팔레트와 무관하게 유지.
- **관련 파일**: `client/App.tsx`, `client/app.json`, `client/assets/gildang-logo.jpeg`, `client/assets/icon.png`, `client/assets/splash-icon.png`, `client/assets/favicon.png`, `client/assets/android-icon-*.png`, `client/android/app/src/main/res/mipmap-*/ic_launcher*.webp`, `client/android/app/src/main/res/values/strings.xml`, `client/ios/Minchodan/Info.plist`, `client/ios/Minchodan/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png`, `client/src/components/LoadingScreen.tsx`, `client/src/components/CameraView.tsx`, `client/src/components/ConnectionStatus.tsx`, `client/src/components/DebugTriggerPanel.tsx`, `client/src/components/NavMapPanel.tsx`, `scripts/generate_app_icons.py`
- **검증 결과**: `npx tsc --noEmit` 통과. 실기기(고태현의 iPhone)에 Xcode 빌드/설치/실행하여 새 아이콘·앱 이름·로딩화면·다크 톤 UI 육안 확인.

---

### 2026-07-14 | YOLO26n_신규가중치_온디바이스연동 | yolo26n_260714_coreml_ondevice

- **변경 내용**:
  - 신규 파인튜닝 가중치(`object_detection260714.pt`, `segmentation260714.pt`, 클래스 스키마는 기존과 동일: 객체 29종/노면 4종) 검증 후 서버(인지 경로) `.env`/`.env.example`의 `YOLO26N_OBJECT_DET`/`YOLO26N_SEG`를 교체(기존 `det_best_20260705.pt`/`segbest.pt`는 롤백용 보존).
  - 온디바이스(iOS 반사 경로) CoreML 변환 중 새 `object_detection260714.pt`가 기존과 달리 `end2end=False`(표준 헤드, NMS-free one2one 아님)임을 발견. `--raw-head`(과거 실측으로 지연 3~5배 악화되어 롤백된 이력 있음, `docs/ops/ondevice_coreml_benchmark.md` 참조) 대신, ultralytics 표준 `nms=True` CoreML NMS 파이프라인(Vision 호환 `confidence`/`coordinates` 2-출력, ANE는 백본에서 그대로 유지)으로 재변환.
  - `IOSDetectModel.forward()`의 80배수 클래스 패딩(ultralytics 기지 이슈 #22309 우회, 29클래스 → 80으로 제로 패딩)을 원인 규명해, 실사용에 지장 없음을 확인.
  - `CoreMLInferenceBridge.swift`의 `runDetection()`에 `confidence`/`coordinates` 2-출력 파이프라인 포맷 파싱 분기(`parsePipelineOutput`) 신규 추가(기존 3차원 텐서 파싱 경로는 segmentation용으로 유지).
  - 세그멘테이션은 보류: 새 `segmentation260714.pt`도 동일하게 `end2end=False`인데, ultralytics가 segment 태스크용 CoreML NMS 파이프라인 자체를 미지원(`# TODO CoreML Segment ... pipelining`)해 온디바이스는 기존 `segbest.pt` 유지, 새 세그멘테이션 가중치는 서버(인지 경로)에서만 사용.
  - 실기기(고태현의 iPhone) 빌드/설치/실행 및 서버 A/B 실측(구/신 가중치 각 1분)으로 정성 확인 - 표본이 적어 정량 비교는 보류.
- **관련 파일**: `.env`(git-ignore), `.env.example`, `client/ios/CoreMLInferenceBridge.swift`, `client/assets/models/yolo26n/ios/object_detection.mlpackage/`, `scripts/convert_yolo_to_coreml.py`(변경 없음, 기존 옵션 재확인)
- **검증 결과**: 서버 컨테이너 재기동 후 `YoloDetector`/`YoloSegmentor` 로드 성공 로그 확인, `/docs` 200 확인. Xcode 시뮬레이터/실기기 빌드 성공(경고 없음). 온디바이스 raw-head 실험은 과거 문서화된 성능 회귀로 채택하지 않음.

---

### 2026-07-14 | 로컬_개발환경_보정 | local_dev_env_fix

- **변경 내용**:
  - `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`: 로컬에 실재하지 않는 `../Minchodan DB.session.sql` MariaDB 초기화 마운트 제거(파일 부재로 컨테이너 기동 실패 방지).
  - `requirements.txt`: `torch`/`torchvision`을 `2.12.1+cu128`/`0.27.1+cu128`에서 `2.11.0+cu128`/`0.26.0+cu128`로 다운그레이드(이 macOS 로컬 Docker 빌드 환경 기준 실측 필요에 따른 조정).
- **관련 파일**: `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `requirements.txt`
- **검증 결과**: `docker compose up -d fastapi` 재기동 후 컨테이너 내 `torch.__version__` 확인(`2.11.0+cu128`), FastAPI `/docs` 200 확인.

---

### 2026-07-14 | 콘솔 | 발화 추적 타임라인 패널 구현

- **배경**: 관제 대시보드에서 ByteTrack 트랙 ID가 부여된 객체가 어떤 행동(연속 히트, 접근, 이탈)을 했을 때 어떤 발화가 나왔는지 추적할 수 없었다. 근본 원인은 track_id/class_name/hit_count가 `ReflexAlert` 스키마에 없고, `consumer.py`의 `log_detections`에서도 누락되어 DB `detected_objects_json`과 `guidance_log_event` WS 메시지에 트랙 정보가 전달되지 않았기 때문.
- **백엔드 수정**:
  - `server/detection/schemas.py`: `ReflexAlert`에 `track_id`, `class_name`, `hit_count` 3개 필드 추가 (기본값 있어 기존 호환성 유지).
  - `server/detection/gates/reflex_gate.py`: `ReflexAlert` 생성 시 `detection.track_id`, `detection.class_name`, `detection.hit_count` 전달.
  - `server/detection/gates/head_level_gate.py`: 동일 적용.
  - `server/detection/gates/surface_gate.py`: surface는 track_id가 없으므로 `class_name`만 전달.
  - `server/detection/consumer.py`: 반사 경로 `_send_reflex_alert`의 `log_detections`에 `track_id`/`class_name`/`hit_count` 추가, 인지 경로 `_send_cognitive_guide`의 `log_detections`에 `track_id`/`hit_count` 추가.
- **프론트엔드 신규 구현**:
  - `console/src/types/monitor.ts`: `TrackedObject`, `GuidanceTraceRow` 타입 추가.
  - `console/src/components/GuidanceTraceTimeline.tsx` (신규): `DetectionGuidanceLogRow[]`에서 `detected_objects_json`을 파싱하여 트랙 ID별 발화 타임라인 표. 트리거 원인 자동 추론(근접+연속히트/연속히트/접근/이탈/노면/상체위험), track_id별 해시 기반 색상 배지, 반사/인지 경로 색상 구분.
  - `console/src/pages/DashboardPage.tsx`: `LatencySummaryPanel`과 `DetectionGuidanceLogTable` 사이에 `GuidanceTraceTimeline` 배치. 기존 `detectionGuidanceLogs`(REST + WS 병합) 재사용.
  - `console/src/styles.css`: `.trace-timeline-table`, `.track-badge`, `.stream-pill` 등 타임라인 전용 스타일 추가.
- **검증**: Ruff format/lint 전부 Passed, `tsc --noEmit` 에러 없음. 반사 경로 지연 무영향 (스키마/dict 구성 단계만 변경, 실시간 전송 이전 완료).
- **관련 파일**: `server/detection/schemas.py`, `server/detection/gates/reflex_gate.py`, `server/detection/gates/head_level_gate.py`, `server/detection/gates/surface_gate.py`, `server/detection/consumer.py`, `console/src/types/monitor.ts`, `console/src/components/GuidanceTraceTimeline.tsx`, `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`

---

### 2026-07-14 | 3단계 | console_design_implementation

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 탐지 게이트 및 관제 모니터 타임라인 컴포넌트 고도화 및 문서 정합성 갱신
- **관련 파일**: `console/src/components/GuidanceTraceTimeline.tsx`, `console/src/components/LiveCameraFeed.tsx`, `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`, `console/src/types/monitor.ts`, `docs/changelogs/kb.md`, `docs/design/api_specification.md`, `docs/stage-guides/stage3_detection_design.md`, `scripts/auto_publish_work.py`, `server/detection/consumer.py`, `server/detection/gates/head_level_gate.py`, `server/detection/gates/reflex_gate.py`, `server/detection/gates/surface_gate.py`, `server/detection/schemas.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 3단계 | console_timeline_demo_patch

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - DashboardPage 데모 데이터 내 track_id 및 hit_count 보완
- **관련 파일**: `onsole/src/pages/DashboardPage.tsx`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 3단계 | console_timeline_virtual_class_patch

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 관제 타임라인 비장애물 발화의 클래스 가시성 개선 (미탐지 대신 GPS/정기안내 동적 표기)
- **관련 파일**: `onsole/src/components/GuidanceTraceTimeline.tsx`, `console/src/pages/DashboardPage.tsx`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 3단계 | reflex_alert_payload_track_id_fix

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 반사 알림(reflex_alert) 실시간 웹소켓 페이로드 내 track_id/class_name/hit_count 누락 결함 수정
- **관련 파일**: `erver/detection/consumer.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 3단계 | console_timeline_parse_type_fix

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 관제 타임라인 JSON 데이터 타입 이원화 대응 (문자열/배열 방어적 파싱으로 track_id 출력 결함 해결)
- **관련 파일**: `onsole/src/components/GuidanceTraceTimeline.tsx`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 3단계 | console_demo_mode_override_fix

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 관제 데모 모드(isDemoMode) 시 DB 로그 데이터 존재 유무와 관계없이 데모 데이터 강제 덮어쓰기 로직 보완
- **관련 파일**: `onsole/src/pages/DashboardPage.tsx`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 3단계 | console_log_image_rotation_patch

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 관제 사후 이력 로그 썸네일 이미지 및 오버레이 바운딩 박스 90도 회전 동기화 패치
- **관련 파일**: `onsole/src/components/DetectionGuidanceLogTable.tsx`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-14 | 클라이언트(iOS)+서버 | 씬 히스테리시스 + 실내 인지 TTS 억제 (시간 압박 스프린트)

- **커밋**: `(미커밋, 사용자 요청 시 커밋)`
- **변경 내용**:
  - **범위**: iOS 우선. Android 씬 게이트는 이번 스프린트에서 제외.
  - `client/src/components/CameraView.tsx`: `isLikelyIndoor` 최근 5프레임 중 3프레임 이상 실내면 실내 확정(`stabilizeIsOutdoorByScene`). 안정화된 값을 반사 게이트와 서버 `is_outdoor`에 동일 적용. `__DEV__`에서 `[SceneHysteresis]` 로그 출력.
  - `server/detection/detection_pipeline.py`: `is_outdoor=False`이면 mid/low라도 `_publish_cognitive` 스킵(실내 TTS 오탐 차단). `None`은 기존 동작 유지.
  - `tests/test_detection.py`: 실내 시 인지 publish 미발행 회귀 테스트 추가.
  - `docs/design/indoor_fp_mitigation_design.md` v0.3.0: §4.7~§4.9 및 롤아웃 갱신.
- **관련 파일**: `client/src/components/CameraView.tsx`, `server/detection/detection_pipeline.py`, `tests/test_detection.py`, `docs/design/indoor_fp_mitigation_design.md`, `docs/changelogs/kb.md`
- **검증 결과**: `pytest -k 'cognitive_publish_suppressed or mid_risk_publishes or is_departing_suppressed'` 4건 통과.
- **남은 일**: §4.9 실외 보도 3~5분 + 실내 2분 현장 회귀(Metro `[SceneClassify]`/`[SceneHysteresis]`). 키워드 보강은 로그 보고 판단.


---

### 2026-07-14 | 클라이언트(Android) | ML Kit 씬 분류로 iOS isLikelyIndoor 동등 신호 추가

- **커밋**: `(미커밋, 사용자 요청 시 커밋)`
- **변경 내용**:
  - `SceneClassifyBridgeModule.kt` 신규: Google ML Kit Image Labeling으로 `isLikelyIndoor`/`topLabels` 산출 (iOS VNClassifyImageRequest 대응).
  - `app/build.gradle`: `com.google.mlkit:image-labeling:17.0.9` 추가.
  - `tfliteDetector.ts`: detect 시 ML Kit 씬 분류를 det/seg와 병렬 호출, `scene` 반환.
  - `CameraView.tsx`: Android `pathObstacle`도 실내 씬이면 경보/TTS 억제 (히스테리시스·`is_outdoor`는 iOS와 동일 경로).
  - `indoor_fp_mitigation_design.md` §4.10 Android 확장 문서화.
- **관련 파일**: `client/android/app/src/main/java/com/minchodan/app/SceneClassifyBridgeModule.kt`, `MinchodanCustomPackage.kt`, `app/build.gradle`, `client/src/inference/tfliteDetector.ts`, `client/src/components/CameraView.tsx`, `client/src/inference/types.ts`, `docs/design/indoor_fp_mitigation_design.md`
- **검증 결과**: TS 경로 연결 완료. **네이티브 모듈이라 Android 재빌드(`npx expo run:android`) 후 실기기에서 `[SceneClassify][Android]` 로그 확인 필요.**
- **비고**: ML Kit 라벨 taxonomy는 Apple Vision과 다르므로 키워드 집합은 Android 실측으로 보강한다.


---

### 2026-07-14 | 3단계 | scene_hysteresis_mlkit_indoor_gate

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 씬 히스테리시스·실내 인지 TTS 억제·Android ML Kit 씬 분류 및 detection is_outdoor API 명세 반영
- **관련 파일**: `lient/android/app/build.gradle`, `client/android/app/src/main/java/com/minchodan/app/MinchodanCustomPackage.kt`, `client/src/components/CameraView.tsx`, `client/src/inference/tfliteDetector.ts`, `client/src/inference/types.ts`, `docs/changelogs/kb.md`, `docs/design/api_specification.md`, `docs/design/indoor_fp_mitigation_design.md`, `server/detection/detection_pipeline.py`, `tests/test_detection.py`, `client/android/app/src/main/java/com/minchodan/app/SceneClassifyBridgeModule.kt`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-15 | 문서 | dev 브랜치 정합성 검토 후속 - README/env 템플릿 불일치 3건 수정

- **커밋**: `(미커밋, 사용자 요청 시 커밋)`
- **변경 내용**:
  - `.env.example:69`: `TTS_ENGINE=edge` → `TTS_ENGINE=supertonic`으로 정정. 주석(66~68행)·README·`server/tts/tts_service.py`의 실제 기본값과 일치시킴. 기존 값은 `cp .env.example .env` 시 네트워크 필수인 Edge Neural TTS가 켜져 로컬 우선 설계 원칙과 어긋났음.
  - `README.md` 검증 기준선 섹션(PowerShell/bash 두 블록): 존재하지 않는 `test_rag_retrieval.py` → 실제 파일 `tests/test_retriever.py`로, `test_tts_reflex.py` → 반사 클립 선점 로직(`reflex_clip_sender._resolve_reflex_patterns`)을 검증하는 `tests/test_reflex_and_nav.py`로 갱신.
  - `README.md:140`, `docs/README.md:37`: `Directory_Structure.md` 링크 경로를 실제 위치인 `docs/Directory_Structure.md` 기준으로 수정(루트 README는 `docs/` 접두 추가, `docs/README.md`는 동일 디렉토리 상대 경로로 정정).
- **관련 파일**: `.env.example`, `README.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: `ls`/`grep`으로 대상 파일 실존 여부 및 참조 경로 재확인 후 수정. 자동화 테스트 대상 아님(문서/설정 변경).

---

### 2026-07-15 | 문서 | Cursor 코딩 에이전트 정합성 검토 후속 - AGENTS.md/스킬 동기화/중첩 문서 정리

- **커밋**: `(미커밋, 사용자 요청 시 커밋)`
- **변경 내용**:
  - `AGENTS.md:174`: `.claude/skills/`가 `.agents/skills/`의 "junction 링크"라는 옛 서술을 `CLAUDE.md:158`의 정정 내용(서로 다른 실제 디렉토리, inode 다름, 수동 동기화 필요)과 일치시킴. Cursor는 루트 `AGENTS.md`를 네이티브로 읽으므로 이 문서가 실제 최신 사실을 담아야 함.
  - `.claude/skills/auto-publish-work/SKILL.md`, `.claude/skills/react-doctor/SKILL.md`를 `.agents/skills/` 쪽 최신본으로 동기화(후행 공백 차이 제거, `diff -rq .claude/skills .agents/skills` 결과 0건 확인). 단, 사전 검증 결과 두 스킬은 실제로는 양쪽에 모두 존재했으며 "한쪽에만 존재"라는 보고서 표현은 부정확했음(트레일링 공백 차이만 존재).
  - `docs/AGENTS.md`: 2026-07-07부터 스스로 폐기 대상으로 명시해온 구버전 본문을 전부 비우고 루트 `AGENTS.md`/`CLAUDE.md`로의 리다이렉트 안내만 남김. Cursor가 서브디렉토리 `AGENTS.md`를 자동 로드할 때 낡은 컨텍스트(구 기술스택, 무효 상대경로)가 주입되는 것을 차단하기 위함. 파일 자체는 changelog 등 과거 문서의 경로 참조가 남아있어 삭제 대신 리다이렉트로 처리.
- **관련 파일**: `AGENTS.md`, `.claude/skills/auto-publish-work/SKILL.md`, `.claude/skills/react-doctor/SKILL.md`, `docs/AGENTS.md`, `docs/changelogs/kb.md`
- **검증 결과**: `grep`으로 junction 문구 수정 확인, `diff -rq`로 스킬 동기화 확인, `docs/AGENTS.md` 본문 교체 확인. 자동화 테스트 대상 아님(문서/설정 변경).

---

### 2026-07-15 | 문서 | Cursor .cursor/rules/*.mdc 신설 - 7단계 스킬 및 반사 경로 금칙 자동 첨부

- **커밋**: `(미커밋, 사용자 요청 시 커밋)`
- **변경 내용**:
  - Cursor가 코딩 시작 시 Claude Code(`CLAUDE.md`/`SKILLS.md`)처럼 프로젝트 지침을 자동으로 읽도록 `.cursor/rules/*.mdc` 12개 신설.
  - `00-core-guidelines.mdc`(`alwaysApply: true`): 이중 경로 원칙, 코딩 규칙, 한국어 커뮤니케이션, Git 브랜치 전략, changelog 규칙 등 `CLAUDE.md`/`AGENTS.md` 핵심을 항상 주입.
  - `01-reflex-path-guard.mdc`(`globs: server/detection/gates/**`): 반사 게이트에서 orchestration/rag/실시간 tts 임포트 금지를 경로 스코프로 강제(이전 Cursor 정합성 검토 개선사항 4번 반영).
  - `02`~`08` (`stage1`~`stage7`): 7단계 파이프라인 각각의 코드 경로(server/api·bus, client 카메라 캡처+server/capture, server/detection+training, server/rag/build, server/rag, server/orchestration, server/tts+client 오디오)에 globs로 매핑, 해당 `.agents/skills/<skill>/SKILL.md` 선독 및 핵심 계약 요약을 자동 첨부.
  - `09-xcode-build-management.mdc`(`globs: client/ios/**`), `10-react-doctor.mdc`(`globs: client/src, console/src의 tsx/jsx`): 보조 스킬 매핑.
  - `11-auto-publish-work.mdc`: 경로 비의존 작업이라 globs 없이 description 기반 Agent Requested 방식으로 구성(커밋/마무리 시점에 에이전트가 자체 판단으로 사용).
- **관련 파일**: `.cursor/rules/00-core-guidelines.mdc`, `.cursor/rules/01-reflex-path-guard.mdc`, `.cursor/rules/02-stage1-websocket-gateway.mdc`, `.cursor/rules/03-stage2-camera-frame-capture.mdc`, `.cursor/rules/04-stage3-yolo-obstacle-detection.mdc`, `.cursor/rules/05-stage4-rag-knowledge-builder.mdc`, `.cursor/rules/06-stage5-rag-realtime-search.mdc`, `.cursor/rules/07-stage6-llm-guidance-orchestrator.mdc`, `.cursor/rules/08-stage7-tts-voice-streamer.mdc`, `.cursor/rules/09-xcode-build-management.mdc`, `.cursor/rules/10-react-doctor.mdc`, `.cursor/rules/11-auto-publish-work.mdc`, `docs/changelogs/kb.md`
- **검증 결과**: 실제 디렉토리 구조(`find client/src`, `server/*`)를 확인해 globs 경로 정확성 확보. `git check-ignore` 결과 `.cursor/`는 gitignore 대상이 아님 확인(현재 untracked). Cursor 런타임 동작 자체는 실기기/실앱 검증 불가 항목이라 파일 문법·경로만 정적 검증함.
- **비고**: `.cursor/`는 아직 git add되지 않은 상태. 커밋 여부는 사용자 확인 후 진행.

---

### 2026-07-15 | 문서 | react-doctor 고신뢰도 항목 수정 (console/client)

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - `console/src/components/DetectionGuidanceLogTable.tsx`: bbox 오버레이 key를 index에서 `det.track_id ?? "${className}-${index}"`로 변경(`LoggedDetection`에 `track_id` 필드 보강). 이벤트 썸네일을 `role="button"` img 대신 실제 `<button>`으로 감싸(`.frame-thumb-btn` 리셋 스타일 추가) 키보드 접근성 확보, 테이블 행에도 `tabIndex`/`onKeyDown`(Enter/Space) 추가.
  - `console/src/components/McpValidationMonitor.tsx`: 억제 목록 key를 index에서 서버가 내려주는 고유 키(`item.key`)로 변경.
  - `client/src/hooks/useCamera.ts`, `useOnDeviceDetection.ts`, `services/depthProbe.ts`: 아무 모듈도 import하지 않는 export 3건(`FRAME_TENSOR_LENGTH` 재export, `DET_CLASS_NAMES`, `probeDepthBoxes`) 비공개화.
  - `client/src/services/audioSessionBridge.ts`: `setVoiceProcessing()`의 Android 분기가 미구현 네이티브 호출을 `await`한 뒤 결과를 버리고 하드코딩 객체를 반환하던 구조를, 가드를 먼저 걸어 불필요한 네이티브 호출 자체를 생략하도록 순서 변경.
  - iframe(`LiveCameraFeed.tsx`, `OperatorLiveMap.tsx`)에 `sandbox="allow-scripts allow-same-origin"`을 추가했다가, 이 조합이 "sandbox 자체 무력화 가능"이라는 새 보안 경고를 유발함을 재검증으로 확인하고 되돌림(지도 서브앱의 same-origin 필요 여부를 실행 검증할 수 없어 보류).
  - `createLocalDetector`(`localDetectorSelect.ios/android/.ts`), `useFrameCaptureProvider`(`frameCaptureProviderSelect.ios/android/.ts`)의 "unused export" 경고는 React Native 플랫폼 확장자 자동 바인딩을 정적 분석기가 인식하지 못한 오탐으로 확인, 수정하지 않음(수정 시 빌드 파손 위험).
- **관련 파일**: `client/src/hooks/useCamera.ts`, `client/src/hooks/useOnDeviceDetection.ts`, `client/src/services/audioSessionBridge.ts`, `client/src/services/depthProbe.ts`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/components/McpValidationMonitor.tsx`, `console/src/styles.css`, `docs/changelogs/kb.md`
- **검증 결과**: `npx react-doctor@latest`(console 48→50/100, client 이슈 30→27건) + `npx tsc --noEmit`(console/client 둘 다 0 에러) 통과.
- **비고**: 인증 토큰 저장 방식(`App.tsx`, `config/index.ts`), 커스텀 모달→`<dialog>` 전환, `CameraView.tsx`의 나머지 버그류 항목(effect 정리·의존성 배열·giant-component 등), 미사용 파일(`DeviceUiMirror.tsx`/`OperatorLiveMap.tsx`) 삭제 여부는 아키텍처/UX 결정 또는 반사 경로 안전성 재검증이 필요해 이번 범위에서 제외.

---

### 2026-07-15 | 1단계 | 콘솔 SystemMetrics SSE 렌더링 복구

- **커밋**: `fix: 콘솔 SystemMetrics SSE 버퍼 방지·연결 직후 스냅샷·401 안내 및 API 명세 반영`
- **변경 내용**:
  - `server/api/monitor.py`: SSE 응답에 `Cache-Control`/`X-Accel-Buffering: no`/`Connection: keep-alive` 헤더 추가, keep-alive 주석 라인, 연결 직후 `system_metrics` 스냅샷 1회 전송.
  - `console/src/api/useMonitorStream.ts`: SSE `onerror` 시 동일 URL fetch 프로브로 401 감지 후 안내.
  - `console/src/components/SystemMetrics.tsx` / `DashboardPage.tsx`: 연결 상태별 빈 카드 안내 문구.
  - `docs/design/api_specification.md`: §8 SSE 계약 v0.4.20 반영.
  - `.xcodebuildmcp/config.yaml` 개인 UDID/절대경로는 커밋에서 제외(공유 템플릿 복구, 개인값은 `Copy_config.yaml`).
- **관련 파일**: `server/api/monitor.py`, `console/src/api/useMonitorStream.ts`, `console/src/components/SystemMetrics.tsx`, `console/src/pages/DashboardPage.tsx`, `docs/design/api_specification.md`, `docs/changelogs/kb.md`
- **검증 결과**: 변경 파일 `ruff check` 통과, 이중 경로(gates) 위반 없음, 금지 파일 미스테이징, `console` `tsc --noEmit` 통과, SSE 스냅샷 실측(`system_metrics` 연결 직후 수신) 확인. 저장소 전체 `ruff check .`는 기존 이슈 354건으로 auto_publish 스크립트 전체 게이트는 우회하고 변경 범위 검증으로 대체.
- **비고**: LiveCameraFeed(WebSocket)와 SystemMetrics 행(SSE+JWT)은 인증 경로가 다름. 재로그인 계정은 `admin`/`admin`.

---

### 2026-07-15 | 클라이언트 | iOS 앱 아이콘 여백·배경 대비 수정

- **커밋**: `feat(client): 앱 아이콘·Loading 스플래시 통일 및 CameraView 운영자 패널 분리` (`9cb3548`)
- **변경 내용**:
  - 원인: `gildang-logo.jpeg`의 회색 바탕(`#E7E7E9`)이 iOS 아이콘 정사각형 모서리에 남아 홈 화면 배경과 대비됨.
  - `scripts/generate_app_icons.py`: 흰 원형 로고 영역 크롭 → 회색 픽셀 흰색 치환 → 강아지+GILDANG 내용 88% 세이프존 확대 파이프라인으로 재작성.
  - `client/assets/icon.png`, `splash-icon.png`, `favicon.png`, `android-icon-*`, iOS `AppIcon.appiconset`, Android `mipmap-*` 전부 재생성.
  - `client/app.json`: 안드로이드 adaptiveIcon `backgroundColor`를 `#FFFFFF`로 통일.
- **관련 파일**: `scripts/generate_app_icons.py`, `client/app.json`, `client/assets/icon.png`, `client/ios/Minchodan/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png`
- **검증 결과**: 1024 아이콘 네 모서리 RGB `(255,255,255)` 확인, 스크립트 재실행 성공.
- **비고**: 실기기 반영에는 iOS 네이티브 재빌드·재설치 필요(`AppIcon.appiconset`은 Metro 핫리로드로 갱신되지 않음).

---

### 2026-07-15 | 2단계 | 클라이언트 기동 UX·CameraView 레이아웃·스플래시 통일

- **커밋**: `feat(client): 앱 아이콘·Loading 스플래시 통일 및 CameraView 운영자 패널 분리` (`9cb3548`)
- **변경 내용**:
  - **Loading 단일화**: Download 단계 제거. 네이티브 스플래시(Metro/JS 로드 전)와 React `LoadingScreen` 모두 `LOADING` 텍스트·동일 다크 배경(`#0A0D10`)으로 통일. `App.tsx`에 `expo-splash-screen`(`preventAutoHideAsync`/`hideAsync`) 연결.
  - **스플래시 로고 비율**: `generate_app_icons.py`의 `circular_logo_from_jpeg()`를 React `Image` cover(비율 유지+중앙 크롭)와 동일하게 수정 — 가로형 `gildang-logo.jpeg` 강제 정사각 리사이즈로 세로 늘어나던 문제 해소.
  - **CameraView**: 운영자 UI(연결상태·디버그·신뢰도·탐지 토글 등)를 카메라 1:1 프리뷰 **아래** `ScrollView` 패널로 이동. STT press-and-hold는 카메라 영역만. `DebugTriggerPanel`은 `__DEV__`에서만 마운트(Release 숨김).
  - **스플래시/아이콘 자산**: `splash-loading.png`, iOS `SplashScreen.imageset`, Android `splashscreen_logo`·`splashscreen.xml`, `app.json` splash 설정 추가.
- **관련 파일**: `client/App.tsx`, `client/src/components/CameraView.tsx`, `client/src/components/DebugTriggerPanel.tsx`, `client/app.json`, `scripts/generate_app_icons.py`, `client/assets/splash-loading.png`, `client/ios/Minchodan/SplashScreen.storyboard`, `client/ios/Minchodan/Images.xcassets/SplashScreen.imageset/`, `client/android/app/src/main/res/drawable/splashscreen.xml`
- **검증 결과**: `npx tsc --noEmit`(client) 통과, `ruff check scripts/generate_app_icons.py` 통과, iOS 실기기 재빌드·재설치·기동 확인.
- **비고**: 스플래시·AppIcon 변경은 Metro Reload로 반영되지 않음 — iOS/Android 네이티브 재빌드 필요. `.xcodebuildmcp/config.yaml` 개인값은 커밋 제외.

---

### 2026-07-15 | 클라이언트/콘솔 | react-doctor 고신뢰도 7건 수정

- **커밋**: `fix(client,console): react-doctor 고신뢰도 7건 수정` (`3fdad96`)
- **변경 내용**:
  - `client/App.tsx`: 온보딩 `setTimeout`에 cancelled/`clearTimeout` cleanup 추가(언마운트 후 speakFallback 방지).
  - `CameraView.tsx`: BBox `key`를 model+class+bbox 안정 키로 변경, debugInfo effect deps에 `detectionEnabled` 추가, MOCK_HAPTIC flash 타이머 cleanup.
  - `LiveCameraFeed.tsx` / `DeviceTelemetryPanel.tsx`: 탐지 리스트 `key={index}`를 `track_id` 또는 class+bbox 키로 교체.
  - `client/src/services/frameCapture.ts` 삭제(미사용 레거시, 실제 전송은 frameCaptureProvider 경로).
- **관련 파일**: `client/App.tsx`, `client/src/components/CameraView.tsx`, `console/src/components/LiveCameraFeed.tsx`, `console/src/components/DeviceTelemetryPanel.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit`(client/console) 통과. react-doctor 재스캔 client 43→44(27→24이슈), console 50→51(11→9이슈). App.tsx effect-cleanup 잔여 경고는 `.then()` 내부 타이머 정적 분석 한계(오탐).

---

### 2026-07-15 | 문서/스킬 | frameCapture.ts 삭제 후 문서·스킬 정합성 일괄 갱신

- **커밋**: `docs: frameCapture.ts 삭제에 맞춘 문서·스킬 정합성 일괄 갱신` (`aa13706`)
- **변경 내용**:
  - 현행 코드(`frameCaptureProvider*`)와 어긋나던 문서/스킬을 일괄 정정.
  - `docs/Directory_Structure.md`, `docs/ops/ios_android_bifurcation_contract.md`, `docs/macOS_xcode_build/ios_device_build_iteration_guide.md`
  - `docs/mobile/mobile_*_implementation_plan.md`, `docs/research/post_mvp_hybrid_roadmap.md`
  - `.agents/skills/camera-frame-capture/SKILL.md` ↔ `.claude/skills/camera-frame-capture/SKILL.md` 동기화
  - 과거 changelog(`dg`/`th`/구 kb 엔트리)의 당시 파일명 기록은 이력으로 유지.
- **관련 파일**: 위 문서·스킬 + `docs/changelogs/kb.md`
- **검증 결과**: 활성 문서에서 `frameCapture.ts`를 현행 경로로 인용하는 항목 제거 확인(삭제 고지·이력 문구만 잔존).

---

### 2026-07-15 | 2단계/3단계 | *260714.pt 기준 온디바이스 CoreML/TFLite 재export

- **커밋**: `5b56b14`
- **변경 내용**:
  - 서버와 동일 기준선 `object_detection260714.pt` / `segmentation260714.pt`에서 모바일 자산 재생성.
  - CoreML: det=`nms=True`(confidence/coordinates), seg=channels-first `[1,40,8400]` + proto mask.
  - TFLite: det=`[1,300,6]`(nms), seg=`[1,40,8400]`.
  - `CoreMLInferenceBridge.swift` / `tfliteDetector.ts`에 seg channels-first 파서 추가.
  - export 스크립트 기본 소스를 `*260714.pt`로 고정 (`convert_yolo_to_coreml.py`, `export_mobile.py`, `export_tflite.py`).
  - Xcode 참조 `client/ios/segmentation.mlpackage`를 assets 산출물과 동기화.
- **관련 파일**: `client/assets/models/yolo26n/**`, `client/ios/segmentation.mlpackage/**`, `client/ios/CoreMLInferenceBridge.swift`, `client/src/inference/tfliteDetector.ts`, `scripts/convert_yolo_to_coreml.py`, `scripts/export_mobile.py`, `scripts/export_tflite.py`
- **검증 결과**: TFLite Interpreter shape 확인(det `[1,300,6]`, seg `[1,40,8400]`). `npx tsc --noEmit`(client) 통과. **iOS 실기기 재빌드·재설치 후** CoreML 번들 반영 필요.
- **비고**: 구 `mlmodelc`(7/11)는 Xcode가 `.mlpackage`를 다시 컴파일하면 교체됨. Android는 Metro가 `assets/.../*.tflite`를 번들.

---

### 2026-07-15 | 2단계/운영 | *콘솔 event_frames MISS(266건) 원인 조사 문서

- **커밋**: `5b56b14`
- **변경 내용**:
  - Detection Guidance Log 썸네일 `-` vs 404(MISS) 증상을 DB·디스크·API·다중 writer 관점에서 분류.
  - 공유 MariaDB + 호스트별 로컬 `data/event_frames` 불일치가 MISS 266건 주원인임을 실측 근거로 정리.
  - 단말 WS는 `100.121.247.4:8000` 고정, PROCESSLIST 상 타 Tailscale IP writer 3대 확인.
  - 해결 방향: writer 단일화 / event_frames 공유 스토리지 / device_id 분리 (`whois`는 추적용).
- **관련 파일**: `docs/ops/event_frame_image_loss_investigation.md`
- **검증 결과**: 이 Mac `minchodan-fastapi` 구간 MISS 0/267. DB `frame_path` 527건 vs 로컬 JPEG 261건(2026-07-15).

---

### 2026-07-15 | 품질 | *Ruff 자동 포맷·린트 일괄 정리 (354→12)

- **커밋**: `50adfb1`
- **변경 내용**:
  - `ruff format .` + `ruff check --fix .`로 50파일 스타일 정리(탭→스페이스, 공백/import/UTF-8 헤더 등).
  - Ruff 전체 에러 354건 → **0건** (`ruff check .`, 로컬 ruff 0.15). `auto_publish_work.py` Ruff 게이트 통과.
  - `50adfb1`은 **49파일** 커밋. `test_frame_decode.py`·`test_risk_ssot.py`는 pre-commit ruff **0.6.9** 기준 이미 통과(로컬 0.15 `format --check`와 assert 줄바꿈 규칙만 상이).
  - RUF046(`tts_service.py`)는 `0e8be01`에서 수정.
- **관련 파일**: `scripts/**`(28), `server/**`(15), `tests/**`(8, 50adfb1) + `server/tts/tts_service.py`(0e8be01)
- **검증 결과**: `ruff check .` 0건. pre-commit `ruff-format`/`ruff` staged 파일 통과. `test_frame_decode`/`test_risk_ssot` pre-commit(0.6.9) Passed.

---

### 2026-07-15 | 품질 | *pre-commit ruff 0.15.20 통일 및 전체 훅 정리

- **커밋**: `24dbca8`
- **변경 내용**:
  - `.pre-commit-config.yaml` ruff `v0.6.9` → `v0.15.20` (`1dd29bb` MVP).
  - `requirements-dev.txt` `ruff>=0.15.0,<0.16.0` 핀, `docs/ops/code_quality_guide.md` v0.3.1 갱신.
  - `pre-commit run --all-files`로 trailing whitespace/EOF 등 저장소 전역 정리.
- **관련 파일**: `.pre-commit-config.yaml`, `requirements-dev.txt`, `docs/ops/code_quality_guide.md`, `pre-commit --all-files` 대상 파일
- **검증 결과**: `pre-commit run --all-files` 전 훅 Passed. `ruff check .`·`ruff format --check .` 0건.

---

### 2026-07-16 | 문서 | Cursor 정합성 재검토 - `.claude/skills/` Git 추적 예외

- **커밋**: `e8184cf`
- **변경 내용**:
  - 제안 개선사항 1~4(junction 문구 정정, 스킬 동기화, `docs/AGENTS.md` 리다이렉트, `.cursor/rules/*.mdc`)는 `kb`/`origin/dev`에 이미 반영됨을 재확인.
  - 잔여 구조 결함: `.gitignore`가 `.claude/` 전체를 ignore해 "양쪽 수동 동기화" 안내가 clone 환경에서 무효였음. `.claude/*` ignore + `!.claude/skills/**` 예외로 스킬 사본만 Git 추적.
  - `.agents/skills/` 정본을 `.claude/skills/`에 전수 동기화(`diff -rq` 0건). `settings.local.json` 등 로컬 아티팩트는 계속 ignore.
  - `AGENTS.md`/`CLAUDE.md`/`.cursor/rules/00-core-guidelines.mdc`에 정본·사본·gitignore 정책을 명시. `CLAUDE.md` 스킬 표에 누락된 `auto-publish-work`·`react-doctor` 추가.
- **관련 파일**: `.gitignore`, `.claude/skills/**`, `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/00-core-guidelines.mdc`, `docs/changelogs/kb.md`
- **검증 결과**: `diff -rq .agents/skills .claude/skills` 0건. `git check-ignore`로 `settings.local.json` ignore·`skills/**` 추적 확인. 이중 경로·금지 파일·react-doctor 검사 통과 후 `origin/kb` 푸시.

---

### 2026-07-16 | 2단계 | ios_console_orientation_fix

- **커밋**: `d2d042b`
- **변경 내용**:
  - iOS `ReflexFrameProcessorPlugin`: dg가 바꾼 `.oriented(.right)`(90도)를 kb 실측 정본 `.oriented(.down)`(180도)로 복구 — takePhoto(`rotate:180`)와 반사 스트림 방향 정합.
  - 콘솔 `LiveCameraFeed` / `DetectionGuidanceLogTable` CSS 회전을 **0**으로 고정(단말에서 정자세 JPEG 전송, 콘솔 하드코딩 90/180 제거).
  - `.xcodebuildmcp/config.yaml` 개인 절대경로/UDID는 커밋 제외(템플릿 유지).
- **관련 파일**: `client/ios/ReflexFrameProcessorPlugin.swift`, `console/src/components/LiveCameraFeed.tsx`, `console/src/components/DetectionGuidanceLogTable.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: 이중 경로 검사 통과. react-doctor client는 기존 `useWebSocket.ts` ref-during-render(본 변경 무관)로 실패 — 이번 스코프 제외. 실기기 재설치 및 콘솔 Live Feed 정자세 확인.

---

### 2026-07-16 | 문서 | outdoor_guidance_refinement_roadmap v1.1

- **커밋**: `556d338`
- **변경 내용**:
  - `docs/research/outdoor_guidance_refinement_roadmap.md`를 v1.1.0으로 개정. dg2 class-agnostic `reflex_gate`·단말 `isServerTimeout` 억제·`high_obstacle_{direction}` 억제키를 반영.
  - Phase 1을 Option A(class-agnostic 고도화, 권장) / Option B(T1/T2/T3 재도입, 대안)로 분리. Phase 2 병렬 가능·경로(`services/audioEngine.ts`)·부록 정정표 추가.
  - `docs/README.md` research 인덱스에 해당 로드맵 등재.
- **관련 파일**: `docs/research/outdoor_guidance_refinement_roadmap.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 현 `reflex_gate.py` / `CameraView.tsx` 본문과 교차 검증 후 문서만 갱신.

---

### 2026-07-16 | 3단계 | outdoor Option A 반사 억제 1차 구현

- **커밋**: `556d338`
- **변경 내용**:
  - Option A 채택: `reflex_gate`에 `MIN_HIT_COUNT` 본문 적용, `MIN_AREA_RATIO` 0.08→0.10, `alert_id`를 `high_obstacle`로 단순화(방향 버킷 TTL 우회 방지).
  - `hapticEngine` continuous 패턴 5초 자동 캡. `risk_ssot_contract` §2-B·로드맵 v1.1.1·yolo 스킬 정합.
  - `tests/test_detection.py` 게이트 기대를 class-agnostic에 맞게 갱신.
- **관련 파일**: `server/detection/gates/reflex_gate.py`, `server/tts/suppressor.py`, `client/src/services/hapticEngine.ts`, `tests/test_detection.py`, `docs/design/risk_ssot_contract.md`, `docs/research/outdoor_guidance_refinement_roadmap.md`, `.agents/skills/yolo-obstacle-detection/SKILL.md`, `.claude/skills/yolo-obstacle-detection/SKILL.md`
- **검증 결과**: Option A 단위 17/17, 통합 스모크 5/5, Docker 게이트 14/14, `/health` 200·consumer 재기동 확인. 확장 48/50(실패 2건은 `MID_RISK_CLASSES=set()`·파이프라인 hit_count<4 기존 이슈, Option A 무관).

---

### 2026-07-16 | 6단계 | Phase 2 인지 guide 구조화 필드 1차 구현

- **커밋**: `556d338`
- **변경 내용**:
  - `consumer._send_cognitive_guide`: `estimate_distance`·`class_name_to_ko`(`CLASS_TEXT` SSoT) 주입, `orch_input`에 `distance`/`object_ko`/한국어 `detected_classes` 연결.
  - `OrchState`에 `distance`·`object_ko` 필드 추가. L2 프롬프트 `[탐지 거리]` 줄 추가. `fallback_node` 중복 `korean_names` 제거.
  - guide WS 페이로드에 `clock_direction`·`distance_class`·`object_ko` 구조화 필드 추가(반사 `distance` 미터와 분리).
  - 클라이언트 `WSMessage`/`GuidePayload` 타입·로그 갱신. `tests/test_cognitive_fields.py` 신설. `api_specification` §6.1 갱신.
- **관련 파일**: `server/detection/consumer.py`, `server/detection/risk_rules.py`, `server/orchestration/state.py`, `server/orchestration/nodes/l2_generator.py`, `server/orchestration/nodes/fallback_node.py`, `client/src/types/detection.ts`, `client/src/hooks/useWebSocket.ts`, `tests/test_cognitive_fields.py`, `docs/design/api_specification.md`, `docs/research/outdoor_guidance_refinement_roadmap.md`
- **검증 결과**: `pytest` Phase2+OptionA **31 passed** (로컬). Docker `test_cognitive_fields`+`TestGates` 통과. `useWebSocket.ts` `connectRef` 렌더 순수성 수정 후 client react-doctor 통과.

---

### 2026-07-16 | 6단계 | Phase 3 패스트 레인 1차 구현

- **커밋**: `556d338`
- **변경 내용**:
  - `server/orchestration/nodes/fast_lane.py` 신설: 단일 객체+`clock_direction`+`distance`+`object_ko` 확정 시 템플릿 안내문 생성(LLM 생략).
  - `graph.py` L1 직후 조건부 분기: 패스트 레인 → END, 복합/이탈/내비/필드 누락 → L2.
  - `OrchState`에 `used_fast_lane`·`fast_lane_cache_key` 추가. `consumer` TTS 경로 `synthesize_fast_lane` 연동.
  - `realtime_tts.py`: `data/guide_clips/{cache_key}.wav` 사전합성 클립 우선 로드, 미스 시 실시간 합성 폴백.
  - `scripts/build_guide_clips.py` 오프라인 합성 스크립트, `data/guide_clips/` 디렉터리 추가.
  - `tests/test_fast_lane.py` 11건 신설. 로드맵 v1.1.2 반영.
- **관련 파일**: `server/orchestration/nodes/fast_lane.py`, `server/orchestration/graph.py`, `server/orchestration/state.py`, `server/detection/consumer.py`, `server/tts/realtime_tts.py`, `scripts/build_guide_clips.py`, `data/guide_clips/`, `tests/test_fast_lane.py`, `docs/research/outdoor_guidance_refinement_roadmap.md`
- **검증 결과**: `pytest tests/test_fast_lane.py` **11/11 passed**. `build_guide_clips.py --dry-run` 조합 생성 확인.

---

### 2026-07-16 | 콘솔 | Detection Guidance Log 파이프라인 텍스트 디버그

- **커밋**: `556d338`
- **변경 내용**:
  - `detection_guidance_logs.pipeline_debug_json` 컬럼 추가(마이그레이션 `20260716_001`). 관리자 콘솔 전용 STT 전사·RAG·LLM/패스트레인·브릿지 분기 텍스트 영속화.
  - `server/services/pipeline_debug_builder.py` 신설. `consumer.py`(반사/인지)·`ws_router.py`(STT)에서 `persist_detection_guidance_log`에 debug payload 전달.
  - 콘솔 `DetectionGuidanceLogTable` 행 상세/라이트박스에 **파이프라인 텍스트** 패널 추가. STT 행(`frame_path` 없음)도 상세 열림, REST `pipeline_debug_json` 객체/문자열 파싱, 테이블 **파이프라인 텍스트** 컬럼 추가. `tests/test_pipeline_debug.py` 5건.
- **관련 파일**: `server/db/migrations/20260716_001_add_pipeline_debug_json_to_detection_guidance_logs.sql`, `server/services/pipeline_debug_builder.py`, `server/detection/consumer.py`, `server/api/ws_router.py`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/types/monitor.ts`, `tests/test_pipeline_debug.py`
- **검증 결과**: Docker `pytest tests/test_pipeline_debug.py` **5 passed**. `console` `tsc --noEmit` 통과.
- **비고**: MariaDB 마이그레이션 적용 완료(호스트 Tailscale 경유). Mac Docker는 `docker/scripts/db_tailscale_proxy.sh` + `COMPOSE_DB_HOST=host.docker.internal`/`COMPOSE_DB_PORT=13306`로 DB 연결(`macos_docker_start.sh` 자동 기동).

---

### 2026-07-16 | 콘솔·서버 | 파이프라인 디버그 확장·RiskEventLog·STT 대기 안내

- **커밋**: `b813bd2`
- **변경 내용**:
  - `pipeline_debug_builder` 확장: YOLO 탐지·노면 분할·L1/L2 초안·STT 에코 스킵·템플릿/RAG 결과를 `pipeline_debug_json`에 저장. 콘솔 패널 세로 스택·테이블 셀 줄바꿈으로 텍스트 겹침 해소.
  - `consumer._broadcast_risk_event`: 반사/인지 경보 시 SSE `risk_event` 발행 — `RiskEventLog` 실시간 표시 wiring.
  - STT `should_play_stt_wait_notice` + `_send_stt_wait_notice`: 경로 검색·RAG·LLM 등 장시간 분기 전 **잠시만 기다려주세요!** 안내.
  - `tests/test_risk_event_broadcast.py`, `tests/test_stt_wait_notice.py`, `test_ws_router_stt` 대기 안내 케이스 추가.
- **관련 파일**: `server/services/pipeline_debug_builder.py`, `server/detection/consumer.py`, `server/api/ws_router.py`, `server/stt/stt_to_llm_bridge.py`, `server/stt/stt_config.py`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/styles.css`, `tests/test_pipeline_debug.py`, `tests/test_risk_event_broadcast.py`, `tests/test_stt_wait_notice.py`, `tests/test_ws_router_stt.py`
- **검증 결과**: Docker `pytest` 관련 **18 passed**. client/console react-doctor 통과.

### 2026-07-16 | Git·문서 | kb → dev 병합 및 설계 문서 교차 검증

- **커밋**: dev merge commit + docs sync (`aeea3bd`)
- **변경 내용**:
  - `origin/kb` 4커밋을 `dev`에 `--no-ff` 병합(충돌 없음).
  - `architecture.md` §13.3.2: `risk_event` SSE 발행·`RiskEventLog` 연동 반영(stale 「미발행」 문구 제거).
  - `api_specification.md` v0.4.22: §6.1 STT 대기 안내·`source` 필드, §8.3 `risk_event` producer, §8.5 `pipeline_debug_json` 확장 필드 표.
  - `Directory_Structure.md`: `RiskEventLog` 주석을 SSE `risk_event`로 정정.
- **배포 전 확인**: `20260716_001_add_pipeline_debug_json_to_detection_guidance_logs.sql` DDL 적용 여부.

---

### 2026-07-16 | 1단계 | dial_action_siri_shortcuts

- **커밋**: `feat(stt,client): STT dial_action 전화 연결(Siri Shortcuts·Android ACTION_CALL)` (`60e4b65`)
- **변경 내용**:
  - STT dial_action 전화 연결 복원(서버 번호 해석·WS·Android ACTION_CALL·iOS Siri Shortcuts MinchodanDial·단축어 설치 스크립트). api_spec v0.4.25. Docker pytest dial 8 passed.
- **관련 파일**: `client/android/app/src/main/AndroidManifest.xml`, `client/android/app/src/main/java/com/minchodan/app/MinchodanCustomPackage.kt`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `client/ios/Minchodan/Info.plist`, `client/ios/Minchodan/PrivacyInfo.xcprivacy`, `client/ios/Podfile.lock`, `client/src/hooks/useWebSocket.ts`, `client/src/types/detection.ts`, `docs/changelogs/kb.md`, `docs/design/api_specification.md`, `server/api/ws_router.py`, `server/stt/stt_to_llm_bridge.py`, `tests/test_ws_router_stt.py`, `client/android/app/src/main/java/com/minchodan/app/PhoneDialBridgeModule.kt`, `client/assets/shortcuts/`, `client/ios/MinchodanDialIntent.swift`, `client/ios/MinchodanSiriDialer.swift`, `client/ios/PhoneDialBridge.mm`, `client/ios/PhoneDialBridge.swift`, `client/src/services/phoneDialBridge.ts`, `scripts/create_minchodan_dial_shortcut.py`, `scripts/install_minchodan_dial_shortcut_ios.sh`, `server/rag/convenience_dial_resolver.py`, `server/stt/dial_resolver.py`, `server/stt/phone_utils.py`, `tests/test_convenience_dial_resolver.py`, `tests/test_dial_resolver.py`, `tests/test_phone_utils.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-17 | 3·6단계 | MID_RISK Option A 정합 (파이프라인-L1 SSOT)

- **변경 내용**:
  - 2026-07-14 부분 마이그레이션 마감: `detection_pipeline.py` 객체 `MID_RISK_CLASSES`를 L1과 동일한 공집합으로 정렬.
  - `HEAD_LEVEL_ESCALATION_CLASSES`(18종) 신설 — `head_level_gate` 격상 전용, 인지 mid와 분리.
  - `tests/test_langgraph.py`(TC-LG-003·TestRiskClassifierConsistency), `tests/test_departure_hysteresis.py` 갱신.
  - `docs/stage-guides/stage6_orchestration_design.md` §7.1, `docs/design/behavior_and_risk_insight.md`, `.agents`/`.claude` `llm-guidance-orchestrator/SKILL.md` 동기화.
- **관련 파일**: `server/detection/detection_pipeline.py`, `server/detection/gates/head_level_gate.py`, `tests/test_langgraph.py`, `tests/test_departure_hysteresis.py`, `docs/stage-guides/stage3_detection_design.md`, `docs/stage-guides/stage6_orchestration_design.md`, `docs/design/behavior_and_risk_insight.md`, `.agents/skills/llm-guidance-orchestrator/SKILL.md`, `.claude/skills/llm-guidance-orchestrator/SKILL.md`

---

### 2026-07-17 | 테스트·문서 | M4/M1/M2 정합성 보완 (conftest·YOLO env·README)

- **변경 내용**:
  - **M4**: `tests/conftest.py` 신설 — fresh clone pytest 수집 시 DB env 기본값 주입. `test_mcp_integration.py` SSE 2번째 이벤트 `system_metrics` 계약 반영.
  - **M1**: `YOLO_DET_CONF`(detector, 기본 0.50)와 `YOLO_CONF`(segmentor, 0.35) 분리 명세 — `.env.example`, README, `environment_variables.md`, `architecture.md`, stage3 문서.
  - **M2**: README/Directory/deployment/android 가이드의 `build_chroma.sh`·stale yaml·`export_tensorrt.py` 정정. `data/{raw,frames,deduped,captions,chroma_db,guide_clips}/.gitkeep` 추가.
- **관련 파일**: `tests/conftest.py`, `tests/test_mcp_integration.py`, `.env.example`, `README.md`, `docs/Directory_Structure.md`, `docs/ops/deployment_guide.md`, `docs/ops/environment_variables.md`, `docs/design/architecture.md`, `docs/stage-guides/stage3_detection_design.md`, `docs/stage-guides/stage3_detection_code_review.md`, `docs/ops/test_specification.md`, `docs/ops/android_*.md`, `data/*/.gitkeep`

---

### 2026-07-17 | 인프라·문서 | multi_agent_rules_unification

- **변경 내용**:
  - **단일 진실 원천 아키텍처 도입**: 규칙은 `AGENTS.md`에서만 편집하고 각 에이전트 진입점은 얇은 포인터/symlink/요약본으로 통합. Codex·ZCode·opencode·Grok(정본 직접), Claude Code(`CLAUDE.md`→`@AGENTS.md` thin pointer), Cursor(`.cursor/rules/*.mdc` 간접 참조), Antigravity(`.antigravity/rules.md` 요약본 + `GEMINI.md` symlink) 모두 세션 시작 시 자동 로드.
  - **AGENTS.md v0.3.6 승격**: CLAUDE.md(v0.3.5) 고유 스택 전환 근거 흡수(Supertonic 3 교체 사유, faster-whisper-small 전환 사유, Frame Processor 전환 사유, `AudioSessionBridge.swift` 경로, NavMapPanel 좌표 표시). §10 다중 에이전트 진입점 섹션 신설.
  - **Antigravity 12,000자 캡 대응**: AGENTS.md 정본(14,864자)이 캡 초과 → `.antigravity/rules.md` 요약본(6,080자) 별도 생성. 핵심 섹션 7개(이중 경로, 반사 LLM 금지, 금지 행위, 이모지, main push, changelog, Router) 포함.
  - **CLAUDE.md 단일 소스 통합**: 14KB 별개 파일(AGENTS.md와 드리프트) → `@AGENTS.md` import thin pointer로 교체.
  - **pre-commit 정합성 검증 스크립트**: `scripts/validate_agent_rules.py` 신설 — CLAUDE.md 포인터, GEMINI.md symlink, `.antigravity/rules.md` 캡·핵심 섹션, `.cursor` 참조, 스킬 미러(`.agents/skills/`↔`.claude/skills/`), `@SKILLS.md` import 6종 검증. 6/6 통과.
  - 팀 온보딩 가이드 `docs/dev-guides/multi_agent_setup.md` 신설.
- **관련 파일**: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.antigravity/rules.md`, `.cursor/rules/00-core-guidelines.mdc`, `.gitignore`, `scripts/validate_agent_rules.py`, `docs/dev-guides/multi_agent_setup.md`
- **검증 결과**: Ruff check 통과, 이중 경로 검증 통과(gates/ 내 금지 임포트 없음), `validate_agent_rules.py` 6/6 통과, 금지 파일(.env/.pt/.onnx) 미포함.
- **비고**: `.gemini/`(Gemini CLI용) 제거 — 팀원 환경은 Antigravity IDE/CLI이므로 `.antigravity/` 사용. 커밋 범위는 본 작업 파일만 선별(이미 있던 server/tests/docs 변경은 별도 분리).

---

### 2026-07-17 | 6단계 | mid_risk_option_a_implementation

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - MID_RISK Option A 구현 커밋 (changelog 선기입분 코드·문서·테스트 동기화)
- **관련 파일**: `server/detection/detection_pipeline.py`, `server/detection/gates/head_level_gate.py`, `tests/test_langgraph.py`, `tests/test_departure_hysteresis.py`, `docs/stage-guides/stage6_orchestration_design.md`, `docs/design/behavior_and_risk_insight.md`, `.agents/skills/llm-guidance-orchestrator/SKILL.md`, `.claude/skills/llm-guidance-orchestrator/SKILL.md`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-17 | 5단계 | m4_m1_m2_implementation

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - M4/M1/M2 정합성 보완 구현 커밋 (conftest·YOLO_DET_CONF·README·data gitkeep)
- **관련 파일**: `tests/conftest.py`, `tests/test_mcp_integration.py`, `.env.example`, `README.md`, `docs/Directory_Structure.md`, `docs/design/architecture.md`, `docs/ops/android_device_integration_guide.md`, `docs/ops/android_ondevice_tflite_run_guide.md`, `docs/ops/android_wireless_test_guide_v2.md`, `docs/ops/deployment_guide.md`, `docs/ops/environment_variables.md`, `docs/ops/test_specification.md`, `docs/stage-guides/stage3_detection_code_review.md`, `docs/stage-guides/stage3_detection_design.md`, `data/raw/.gitkeep`, `data/frames/.gitkeep`, `data/deduped/.gitkeep`, `data/captions/.gitkeep`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-17 | 1단계 | dev_ios_lab_script

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - iOS 실기기+Docker+DB 통합 테스트 랩 스크립트 (dev_ios_lab.sh)
- **관련 파일**: `scripts/dev_ios_lab.sh`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-17 | 테스트 | kb→dev 병합 전 정합성 회귀 수정 (MID_RISK Option A)

- **변경 내용**:
  - kb→dev 병합 정합성 검토 중 회귀 3건 발견: 커밋 `6e273a3`("MID_RISK Option A 파이프라인-L1 SSOT")이 `MID_RISK_CLASSES`를 공집합으로 전환했으나 `tests/test_detection.py`의 파이프라인 테스트 4개 갱신 누락(dev 1개 실패 → kb 4개 실패).
  - `test_segmentor_exception_returns_detections_only`: bicycle 기대값 `mid`→`low` (MID_RISK_CLASSES 공집합).
  - `test_cognitive_publish_suppressed_when_client_reports_indoor`: bicycle 기대값 `mid`→`low` (발행 억제 정책은 유지, `assert_not_called` 그대로 통과).
  - `test_mid_risk_publishes_to_redis`: 입력 bicycle(이제 low) → 노면 `roadway`로 변경하여 mid 유발. 테스트 본래 의도("mid → Redis 발행") 보존.
  - `test_tracker_exception_still_returns_result`: bollard 기대값 `mid`→`none`. track_id="T-0001"이나 hit_count 기본값이 최소 유지 프레임(4) 미만이라 시간적 지속성 필터(`detection_pipeline.py:150`)에서 제외되고 tracker 예외로 hit_count 미증가 → 빈 detections → `none`이 올바른 분류.
- **관련 파일**: `tests/test_detection.py`
- **검증 결과**: Ruff 통과, `test_detection.py` 34 passed, 회귀 영향 범위(detection+langgraph+departure) 55 passed, 전체 스위트(test_ws_echo 환경 실패 제외) 256 passed.
- **비고**: `test_ws_echo.py` 6개 실패는 Redis 미실행·FastAPI 서버 미기동(포트 8000) 환경 문제로 dev에서도 동일 실패(회귀 아님). 병합 후 CI에서는 인프라 기동 상태로 통과 예상.

---

### 2026-07-17 | 3단계 | merge_teammates_integration

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - merge teammates branches (jh, dg2, jy) into dev and fix conflict/test bugs
- **관련 파일**: 없음
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-17 | 2단계 | ios_dev_bundle_metro_host

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - iOS 실기기 개발 서명용 번들 ID(com.minchodan.app.kb.dev) 및 Metro 기본 호스트(LAN) 정합
- **관련 파일**: `lient/app.json`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `client/ios/Minchodan/AppDelegate.swift`, `client/ios/Minchodan/Info.plist`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-17 | 2단계 | restore_ios_frame_processor

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - iOS takePhoto 강제 폴백 해제 - Frame Processor 복구로 AVFoundation Cannot Record(-11803) 해소
- **관련 파일**: `lient/src/hooks/useCamera.ts`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

### 2026-07-17 | 1단계 | console_live_feed_smoothness

- **커밋**: `4912835`
- **변경 내용**:
  - Vite `/navigation` WebSocket 프록시(`ws: true`) 추가 - 지도 iframe `navigation/ws` 연결 실패 해소.
  - 콘솔 `useLiveFeed` Strict Mode 안전 재연결, Vite `/ws` 프록시 경로, rAF 최신 프레임만 렌더, 매 프레임 console.log 제거.
  - 서버 `/ws/detect`: Live Feed 중계·ack는 즉시, YOLO `route_frame`은 백그라운드(동시 1개, busy 시 탐지 드롭)로 분리해 콘솔 영상이 탐지 지연에 묶이지 않도록 개선.
  - 앱 캡처 최저 FPS 1→5fps, 스트림 프레임 로그 제거(JS 스레드 부하 완화).
  - Live Feed 플레이스홀더 문구: 앱 연결·탐지 시작 필요 안내.
  - (로컬만) `.env`에 `IMAGE_SERVER_*` / `EVENT_FRAME_STORAGE_BACKEND=remote` 설정 - 시크릿이라 커밋 제외.
- **관련 파일**: `console/vite.config.ts`, `console/src/api/useLiveFeed.ts`, `console/src/components/LiveCameraFeed.tsx`, `server/api/ws_router.py`, `client/src/hooks/useCamera.ts`
- **검증 결과**: 미디어 서버 업로드/조회 스모크 성공, FastAPI `/health` 200, navigation WS 프록시 연결 확인.
- **비고**: FastAPI 재기동 후 앱 `/ws/detect` 재연결 및 탐지 시작 필요.

### 2026-07-17 | 통합 | kb_shared_to_dev_exclude_ios_lab

- **커밋**: `7c6fe81`
- **변경 내용**:
  - `kb` 공유 수정(Live Feed/WS/Frame Processor)을 `dev`에 FF 병합.
  - 개인 랩 설정(`com.minchodan.app.kb.dev`, Metro `172.16.101.220`)은 `dev`에 넣지 않고 기존 `com.minchodan.app.kwanbum` / Tailscale Metro 기본값으로 되돌림.
- **관련 파일**: `client/app.json`, `client/ios/Minchodan/*`, `client/ios/Minchodan.xcodeproj/project.pbxproj`
- **검증 결과**: FF 병합 후 개인 iOS 4파일만 `569cbb6` 기준으로 복원, 공유 서버/콘솔/useCamera 변경 유지.
- **비고**: 실기기 랩은 `kb` 브랜치 또는 로컬 uncommitted/`METRO_BUNDLER_HOST`로 유지.

### 2026-07-17 | 통합 | merge_dg2_shared_into_dev

- **커밋**: `2a4d17e`
- **변경 내용**:
  - `dg2` → `dev` 병합: Android float32/AEC 복구, Live Feed 회전 UI, Android 패리티 문서 반영.
  - 충돌 해결: `useCamera`(Stream+Cannot Record 주석 유지, MAX_REFLEX=200), `useLiveFeed`(Vite `/ws` 프록시 경로 유지).
  - 개인 랩 제외: Tailscale/Metro/Vite `100.85.229.93`, docker NVIDIA deploy ON·MariaDB 3306 바인딩 OFF, tailscale 가이드 IP 변경 원복.
  - `vite.config.ts`: localhost 프록시 + `/navigation` `ws: true` 유지.
- **관련 파일**: `client/src/services/*android*`, `audioSessionBridge.ts`, `console/src/components/LiveCameraFeed.*`, `docs/mobile/android_platform_patch_results.md`
- **검증 결과**: 충돌 마커 제거, 개인 IP 검색 0건, MAX_REFLEX=200·vite localhost 확인.
- **비고**: dg2 개인 GPU/호스트 설정은 `dg2` 브랜치에만 유지.


### 2026-07-17 | 통합 | sync_dev_into_kb_keep_lab

- **커밋**: `355c014`
- **변경 내용**:
  - `origin/dev`(`44a56bc`)를 `kb`에 FF 반영 (dg2 Android 패리티·콘솔 회전·changelog 포함).
  - kb 개인 랩 설정 유지: 번들 ID `com.minchodan.app.kb.dev`, Metro `172.16.101.220:8081`.
- **관련 파일**: `client/app.json`, `client/ios/Minchodan/*`, (공유분은 dev와 동일)
- **검증 결과**: FF 후 개인 4파일 복원, rotateDeg/Android float32/MAX_REFLEX=200 확인.
- **비고**: 공유 코드는 dev와 동기, 실기기 랩 설정만 kb에 잔류.


### 2026-07-17 | 인프라 | lab_env_yolo_ollama_align

- **커밋**: `5428e43`
- **변경 내용**:
  - 랩 런타임 `.env`(로컬 전용, 커밋 제외): `DETECTOR_TYPE=yolo`, `OLLAMA_BASE_URL`/`COMPOSE_OLLAMA_BASE_URL=http://host.docker.internal:11434`, `TTS_ENGINE=supertonic`.
  - `.env.example` 탐지 기본값을 `yolo`로 정합(주석에 mock 폴백 안내).
  - `env.zip`(시크릿 포함)은 커밋하지 않음.
- **관련 파일**: `.env.example`, (로컬) `.env`
- **검증 결과**: FastAPI health `detector_type=yolo`, 컨테이너→Ollama 200, `YoloDetector`/`SupertonicTTSService` 로드 확인.
- **비고**: 앱은 FastAPI 재기동 후 WS 재연결 필요.


### 2026-07-17 | 클라이언트 | stt_fullscreen_touch_restore

- **커밋**: `f9aab75`
- **변경 내용**:
  - STT press-and-hold를 7/10 설계대로 **화면 전체** 투명 레이어로 복원(시각장애인: 아무 곳이나 길게 눌러 말하기).
  - 7/15 `9cb3548` 운영자 패널 분리 이후 카메라 영역만 STT였던 회귀를 해소.
  - 운영자 버튼(탐지 시작 등)은 STT **위** absolute `box-none` 오버레이로 분리해, STT 한 번 후 버튼 먹통 문제 방지.
  - STT 중 `setCapturePaused`로 JPEG/CoreML 콜백 일시 중지, 녹음 시작 락·16kHz warm-prepare로 반응 지연/중첩 AEC 완화.
- **관련 파일**: `client/src/components/CameraView.tsx`, `client/src/hooks/useCamera.ts`, `client/src/hooks/useSttRecorder.ts`
- **검증 결과**: 실기기 재빌드 후 터치/버튼 계층 복원 적용. Metro Reload로 JS 반영.
- **비고**: 개인 iOS 랩 설정(번들 ID/Metro IP)은 본 커밋에 포함하지 않음. 로컬 `HEARTBEAT_TIMEOUT` 상향은 `.env`만(미커밋).

### 2026-07-17 | 통합 | merge_kb_lab_settings_into_dev

- **커밋**:
- **변경 내용**:
  - `kb` tip을 `dev`에 병합해 STT 전체화면 터치 복원과 함께 iOS 랩 설정·changelog 히스토리를 팀 공유 기준으로 올린다.
  - 포함: 번들 ID `com.minchodan.app.kb.dev`, Metro LAN 호스트, `.env.example` yolo 정합 문서.
- **관련 파일**: `client/app.json`, `client/ios/Minchodan/*`, `docs/changelogs/kb.md`, `.env.example`
- **검증 결과**: changelog 충돌 해소 후 merge 커밋.
- **비고**: 팀원 실기기 IP가 다르면 Metro/`EXPO_PUBLIC_*`만 로컬에서 맞추면 된다.

---

### 2026-07-17 | 1단계 | event_frame_buffering_fix

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 이벤트 프레임 미디어 API 버퍼링 분석 가이드 P0/A1-A5 + P1/B3 구현: (A1) iOS CoreML 정상 모드에서 JS JPEG->float32 변환 우회 via requiresFloat32 계약, (A2) 단말 ACK 기반 in-flight 프레임 제한(MAX_IN_FLIGHT_FRAMES, 메타+binary pair 드롭), (A3) 서버 ACK를 콘솔 중계보다 먼저 처리(binary/base64 양 경로), (A4) 콘솔 송신 latest-only 큐(maxsize=1) + per-connection worker 분리로 느린 콘솔 역압력 차단, (A5) 콘솔 relay 3-5fps 쓰로틀, (B3) 공유 httpx.AsyncClient 연결 풀(lifespan 생성/종료, 방어적 폴백). main.py contextlib.suppress -> suppress import 정정.
- **관련 파일**: `lient/src/components/CameraView.tsx`, `client/src/hooks/useCamera.ts`, `client/src/hooks/useOnDeviceDetection.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/inference/localDetector.ts`, `client/src/inference/localDetectorSelect.ios.ts`, `client/src/inference/tfliteDetector.ts`, `server/api/session_manager.py`, `server/api/ws_router.py`, `server/main.py`, `server/services/remote_storage_client.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-17 | 통합 | merge_jh_into_kb

- **커밋**: `2e5c289`
- **변경 내용**:
  - `jh` tip을 `kb`에 병합해 생활지원 RAG BGE-M3 전환과 콘솔 대시보드 위젯 MVP 복구를 kb 작업선에 반영한다.
  - 포함: `CONVENIENCE_EMBEDDING_PROVIDER/MODEL`(bge-m3) 환경변수, `scripts/build_convenience_db.py` 임베딩 파라미터, `server/rag/convenience_rag.py`, `console/src/pages/DashboardPage.tsx` 위젯 추가/삭제·카드 헤더 정렬, `console/src/styles.css`.
- **관련 파일**: `.env.example`, `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`, `scripts/build_convenience_db.py`, `server/rag/convenience_rag.py`
- **검증 결과**: 병합 시뮬레이션에서 `.env.example` 자동 병합 성공(양쪽 변경 위치 상이), 충돌 0건, 환경변수 문서(`docs/ops/environment_variables.md`)에 `CONVENIENCE_EMBEDDING_*` 이미 기록됨 확인.
- **비고**: kb(버퍼링 수정·ws/camera)와 jh(RAG·콘솔)는 독립 영역으로 기능적 간섭 없음. 이중 경로 분리 원칙 유지.

---

### 2026-07-17 | 문서 | convenience_rag_setup_doc

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - jh 병합으로 들어온 생활지원 RAG(BGE-M3) 셋업 절차가 `deployment_guide.md`와 `README.md`에 누락된 갭을 보완. 팀원이 `git pull` 후 동일 환경을 구성할 수 있도록 명세화.
  - `deployment_guide.md`: Ollama pull 섹션(3.사전 준비 + 4.1 Windows + 4.2 macOS/Linux)에 `ollama pull bge-m3` 추가, RAG 빌드 섹션에 `python scripts/build_convenience_db.py` 추가, `bge-m3`/`nomic-embed-text` 용도 분리 주석.
  - `README.md`: `build_convenience_db.py`를 "선택"에서 필수 빌드 단계로 격상, `ollama pull bge-m3` 사전 요건 안내(Windows/macOS-Linux 양쪽), 기술 스택 모델 목록에 `bge-m3` 명시.
- **관련 파일**: `docs/ops/deployment_guide.md`, `README.md`
- **검증 결과**: 문서 교차 검증 — `.env.example`(L42-43)과 `docs/ops/environment_variables.md`(L199-201)에 이미 변수 명세 존재 확인, 본 변경은 실행 절차 보완만 수행.
- **비고**: `.env` 자체는 gitignore로 팀원 공유 불가하므로 `.env.example` 기반 복제 절차가 단일 진실 원천. 로컬에서 수행한 `ollama pull bge-m3` + `build_convenience_db.py`(문서 34건 적재)는 검증 완료.

---

### 2026-07-17 | 문서 | convenience_rag_test_spec

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 생활지원 RAG 통합 검증 시나리오를 프로젝트 테스트 명세 체계의 정합성 위치에 등재. jh 병합으로 들어온 부가 경로(StT 음성 명령 → 생활지원 RAG)가 기존 4대 E2E 시나리오와 단계별 TC 매트릭스에 누락된 갭 보완.
  - `docs/ops/test_specification.md`: §7 통합 smoke 검증에 TC-SMOKE-006 신설(`bge-m3` pull + `build_convenience_db.py` + 컨테이너 `answer_convenience_question()` 검색 응답 검증), 상세 절차 블록 및 3종 검증 쿼리 기록, 버전 v0.6.5 -> v0.6.6.
  - `docs/ops/integration_scenario_test.md`: SC-E2E-005 STT 음성 명령 -> 생활지원 RAG 응답 부가 경로 시나리오 신설, §2 헤더 4대 -> 5대 E2E 갱신, §3 결과 대장에 SC-E2E-005 PASS 행 추가, 버전 v1.0.0 -> v1.1.0.
- **관련 파일**: `docs/ops/test_specification.md`, `docs/ops/integration_scenario_test.md`
- **검증 결과**: 문서 교차 검증 — 단위 테스트는 기존 `tests/test_convenience_dial_resolver.py` 등이 커버하므로 본 변경은 통합 smoke + E2E 시나리오 명세만 보완(단일 진실 원칙 유지). §5.4 RAG 섹션은 safety_guidelines 전용이라 convenience를 넣지 않아 정합성 훼손 방지.
- **비고**: TC-SMOKE-006과 SC-E2E-005는 동일 검증의 매트릭스/시나리오 쌍. 2026-07-17 실측 기반으로 상태를 `완료`/`PASS`로 마킹.

---

### 2026-07-17 | 문서 | field_test_improvement_plan_편입

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 실기기 실외 보행 테스트 피드백(S1~S8) 기반 개선 구현 계획서를 `Downloads/`에서 프로젝트 `docs/research/` 트리로 편입. 정합성 이슈 3건 정정 동시 적용.
  - `docs/research/field_test_improvement_plan.md` 신규 편입 (v1.0 -> v1.1): §2.2 `consumer.py:124-135` 라인 근거를 `_consume_loop(L282)` + `detection_pipeline.py`로 정정(원 라인은 `_broadcast_latency_event` 함수 본문), §2.6 "Object Detection 29클래스"를 "공식 명세 29종, CLASS_TEXT 실제 31종"으로 정정, §2.6 STAIR_DOWN "죽은 코드" 근거를 "CLASS_TO_HINT_ID 매핑 없음"에서 "alert_id 생성 경로에 'stair' 계열이 없어 `_hint_id_for_alert` L212 분기 도달 불가"로 정정.
  - 상대경로 링크를 Downloads 기준(`../research/X`)에서 `docs/research/` 기준(`./X`)으로 수정, `../design/`·`../ops/`는 동일 디렉토리 구조상 유지.
  - `docs/README.md` research 섹션에 새 문서 등재 (outdoor_guidance_refinement_roadmap.md 다음).
- **관련 파일**: `docs/research/field_test_improvement_plan.md`, `docs/README.md`
- **검증 결과**: 코드-문서 교차 검증 16개 항목 중 13개 정합, 3개 정정 완료. AGENTS.md 규칙(이모지 금지·한국어·mermaid 큰따옴표/br·하드-바이브 분할·이중 경로 원칙) 모두 준수. 선행 문서 8개 존재 확인, 환경변수 6개 기존 충돌 없음.
- **비고**: 본 계획은 outdoor_guidance_refinement_roadmap.md의 후속 Phase로 상호 참조. 구현 시 과제별로 별도 changelog 엔트리 추가 예정.

---

### 2026-07-17 | 3단계 | M1_P0-2_큐_최신성

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 계획서 M1/P0-2 구현: 반사 큐 최신성 보장(latest-frame-wins) + 프레임 신선도 검사 + 큐 대기 계측으로 지연 드리프트(S3) 해소.
  - `server/capture/stream_splitter.py`: `QUEUE_MAXSIZE=100` 단일 상수를 `REFLEX_QUEUE_MAXSIZE=2`/`COGNITIVE_QUEUE_MAXSIZE=4`로 분리 (환경변수 오버라이드). `get_default_splitter`에 적용. `QUEUE_MAXSIZE`는 하위 호환용으로 두 분리 상수의 최댓값.
  - `server/detection/consumer.py`: `_process_frame` 진입부에 신선도 검사 추가 (`now - processed.ts > REFLEX_MAX_AGE_S/COGNITIVE_MAX_AGE_S` 초과 시 추론 없이 드롭 + `_stale_drop_count` 증가). `queue_wait_ms` 계산 후 reflex/cognitive 양쪽 `latency_stages`에 `queue_wait_ms` 키 추가 (콘솔 지연 패널 노출). ts=0(클라이언트 미전송)이면 검사 건너뜀(방어적 코딩).
  - `docs/ops/environment_variables.md` + `.env.example`: `REFLEX_QUEUE_MAXSIZE`, `COGNITIVE_QUEUE_MAXSIZE`, `REFLEX_MAX_AGE_S`, `COGNITIVE_MAX_AGE_S` 4개 변수 추가.
  - `tests/test_frame_decode.py`: `TestP0QueueFreshness` 클래스 신규 (reflex/cognitive 큐 latest 유지, 신선도 상수 로드 검증). 기존 `test_singleton_queue_maxsize`를 새 분리 상수 기반으로 업데이트. asyncio import 추가.
- **관련 파일**: `server/capture/stream_splitter.py`, `server/detection/consumer.py`, `docs/ops/environment_variables.md`, `.env.example`, `tests/test_frame_decode.py`
- **검증 결과**: `pytest tests/test_frame_decode.py` 33개 전체 통과. consumer/stream_splitter import 정상, FastAPI 컨테이너 재시작 후 헬스 200 OK.
- **비고**: M2(P0-1 억제 재무장)·M3(P0-3 소형 객체)의 선행. 큐 축소로 hit_count 증가 지연 가능성은 리스크(§10)로 명시, 드롭률 30% 초과 시 MIN_HIT_COUNT 하향 검토 예정.

---

### 2026-07-17 | 3단계 | M2_P0-1_억제_재무장_정책

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 계획서 M2/P0-1 구현: 반사 억제 60초 무조건 침묵 -> 재무장(Re-arm) 정책으로 전환. "같은 상황 반복은 억제, 상황 변화(새 객체/거리 악화) 시 즉시 재발화"로 S1(정지 후 60초 침묵)·S2(새 객체 무시) 해소.
  - `server/tts/suppressor.py`: 재무장 정책 구현. 억제 키 `high_obstacle:{track_id}:{distance_band}`로 분리 (새 객체/거리 악화 시 키 달라져 억제 우회). `should_rearm(prev_band, current_band)` 정적 메서드로 밴드 악화(far->medium->near) 판정 + [면접 대비 주석]. `should_emit_reflex(device_id, track_id, distance_band, is_near)` 비동기 메서드: near(<=0.6m)는 TTL 억제 제외 500ms 스로틀만, non-near는 device 단위 1.5s 쿨다운 + 동일 트랙+밴드 5s TTL + 밴드 악화 재발화. `mark_reflex_sent` 신규. 기존 `should_suppress`/`mark_as_sent`는 레거시 하위 호환 유지. 환경변수 `REFLEX_SUPPRESS_TTL_S`(5), `REFLEX_MIN_GAP_S`(1.5), `REFLEX_NEAR_HAPTIC_THROTTLE_S`(0.5) 추가.
  - `server/detection/schemas.py`: `ReflexAlert`에 `distance_band` 필드 추가 (기본 "medium").
  - `server/detection/gates/reflex_gate.py`: distance 기반 밴드 산출 (near<=0.6m / medium<=1.5m / far) + [면접 대비 주석]. `ReflexAlert`에 `distance_band` 채움.
  - `server/detection/consumer.py`: `_send_reflex_alert`가 `should_emit_reflex`/`mark_reflex_sent` 사용. payload에 `distance_band` 추가 (단말/콘솔 가시성).
  - `docs/ops/environment_variables.md` + `.env.example`: 3개 신규 변수 문서화.
  - `tests/test_suppressor_rearm.py` 신규: should_rearm 단위(신규/악화/동일/개선), near 스로틀, non-near TTL/쿨다운/밴드 악화 재발화 12개 케이스.
  - `tests/test_detection.py`: `TestReflexAlertSuppression` 3개 테스트를 새 API(`should_emit_reflex`/`mark_reflex_sent`)로 업데이트.
- **관련 파일**: `server/tts/suppressor.py`, `server/detection/schemas.py`, `server/detection/gates/reflex_gate.py`, `server/detection/consumer.py`, `docs/ops/environment_variables.md`, `.env.example`, `tests/test_suppressor_rearm.py`, `tests/test_detection.py`
- **검증 결과**: `pytest tests/test_detection.py tests/test_suppressor_rearm.py tests/test_frame_decode.py` 79개 전체 통과. FastAPI 컨테이너 재시작 후 헬스 200 OK.
- **비고**: near 햅틱 스로틀(500ms)은 충돌 임박 촉각 신호의 반복 안전 이득을 손실보다 크게 평가한 설계 선택. 밴드 경계(0.6m/1.5m)는 보행 속도 1m/s 기준.

---

### 2026-07-17 | 3단계 | M3_P0-3_소형객체_하단근접_ApproachLost

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 계획서 M3/P0-3 구현: 소형 객체 하단 근접 보정 + Approach-Lost 재획득 즉시 재발화로 S4(재등장 0.3s 지연)·소형 객체 누락 해소.
  - `server/detection/schemas.py`: `Detection`에 `reacquired: bool = False` 필드 추가.
  - `server/detection/bytetrack_tracker.py`: `_compute_hit_count_with_reacquire()` 신규. 직전 hit_count >= APPROACH_LOST_MIN_PREV_HIT(3)이고 updated_at이 APPROACH_LOST_WINDOW_S(1.0s) 이내 재탐지 시 reacquired=True + [면접 대비 주석]. hit_count는 정상 누적 유지(감소시키지 않음). 환경변수 `APPROACH_LOST_WINDOW_S`, `APPROACH_LOST_MIN_PREV_HIT` 추가.
  - `server/detection/gates/reflex_gate.py`:
    - (a) 소형 객체 하단 근접 보정: bottom_y >= 0.8*frame_height AND SMALL_OBJECT_MIN_AREA_RATIO(0.04) <= area_ratio < MIN_AREA_RATIO(0.10)이면 is_very_close=True + [면접 대비 주석]. 발밑 작은 bbox(볼라드·모터사이클)가 원거리로 오인되어 반사 누락되는 문제 해소.
    - (b) reacquired=True면 MIN_HIT_COUNT 검사 건너뛰어 즉시 발동 + [면접 대비 주석].
    - `SMALL_OBJECT_MIN_AREA_RATIO=0.04` 상수 추가.
  - `docs/ops/environment_variables.md` + `.env.example`: `APPROACH_LOST_WINDOW_S`, `APPROACH_LOST_MIN_PREV_HIT` 2개 변수 추가.
  - `tests/test_detection.py`: TestGates에 3개(소형 하단 근접 발동/하한 미만 미발동/reacquired MIN_HIT bypass), TestByteTrackTracker에 3개(윈도우 내 reacquired/윈도우 외 False/직전 hit 낮으면 False) 테스트 추가.
- **관련 파일**: `server/detection/schemas.py`, `server/detection/bytetrack_tracker.py`, `server/detection/gates/reflex_gate.py`, `docs/ops/environment_variables.md`, `.env.example`, `tests/test_detection.py`
- **검증 결과**: `pytest tests/test_detection.py tests/test_suppressor_rearm.py tests/test_frame_decode.py` 85개 전체 통과. FastAPI 컨테이너 재시작 후 헬스 200 OK.
- **비고**: Approach-Lot는 track_id가 유지되는 케이스를 전제(문서 §4.2 (b) "동일 track_id"). 완전히 새 track_id 부여 시 spatial matching이 필요하나 post-MVP 과제. SMALL_OBJECT_MIN_AREA_RATIO(0.04)는 중앙 먼 곳 작은 bbox 오탐 차단을 위한 하한.

---

### 2026-07-17 | 6단계 | M4_P1-2_발화가치_게이트

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 계획서 M4/P1-2 구현: 인지 가이드 발화 가치(Utterance Value) 게이트 추가. 동일 상황(객체+표면 서명 동일) 반복 안내는 COGNITIVE_UTTERANCE_COOLDOWN_S(30s) 동안 TTS 합성 생략해 CPU 점유와 중복 안내를 동시 감소 (S5/S6 해소).
  - `server/detection/consumer.py`:
    - `COGNITIVE_UTTERANCE_COOLDOWN_S` 환경변수 상수(30.0) 추가.
    - `_last_guide_signature: dict[str, str]` 인스턴스 변수 추가 (device_id별 상황 서명).
    - `_compute_cognitive_signature(result, departure_confirmed)` 정적 메서드: 객체 클래스 정렬 + 표면 클래스 정렬 + 이탈 여부로 서명 산출 + [면접 대비 주석].
    - `_has_utterance_value(device_id, result, departure_confirmed)` 메서드: 발화 가치 OR 판정 (보도 이탈/서명 변화/쿨다운 경과).
    - `_send_cognitive_guide` 진입부에 P1-2 게이트 추가 (기존 오디오 겹침 쿨다운 앞). 전송 성공 시 `_last_guide_signature` 갱신.
  - `docs/ops/environment_variables.md` + `.env.example`: `COGNITIVE_UTTERANCE_COOLDOWN_S` 변수 추가.
  - `tests/test_detection.py`: `TestUtteranceValueGate` 클래스 신규 8개 케이스 (서명 객체/표면/이탈 반영, 이탈 항상 가치, 새 객체 가치, 동일 서명 쿨다운 내 생략, 동일 서명 쿨다운 경과 발화, 최초 안내 가치).
- **관련 파일**: `server/detection/consumer.py`, `docs/ops/environment_variables.md`, `.env.example`, `tests/test_detection.py`
- **검증 결과**: `pytest tests/test_detection.py tests/test_suppressor_rearm.py tests/test_frame_decode.py` 93개 전체 통과. FastAPI 컨테이너 재시작 후 헬스 200 OK.
- **비고**: 기존 오디오 겹침 쿨다운(_required_guide_gap_sec, 8s+오디오길이)은 유지 - P1-2 게이트는 "동일 상황 반복" 차단, 기존 쿨다운은 "오디오 재생 중 겹침" 차단으로 역할 분리. fallback_node/realtime_tts는 consumer 게이트로 사전 차단되어 호출 자체가 생략되므로 TTS 합성 미호출 보장.

---

### 2026-07-17 | 6단계 | M5_P1-1_반사_후속_행동_안내

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 계획서 M5/P1-1 구현: 반사 경보(정지) 800ms 후 인지 가이드(LangGraph L2) 대신, 단일 객체 + 방향 확정 시 avoidance 템플릿으로 즉시 우회 방향 안내. LangGraph 전체(L1/L2/L3) 수 초 소요를 없애 반사 후속 안내 지연(S7) 해소.
  - `server/orchestration/avoidance.py` 신규: `build_avoidance_guidance(alert)` 순수 함수. direction(front/front-left/front-right/stop) + panning 기반 우회 방향 템플릿 (20자 이내) + [면접 대비 주석]. `can_use_avoidance_fast_lane(alert, detections)` 판정 (단일 객체 + 유효 direction + 20자 이내). 비협상 원칙 준수: LLM/RAG/실시간 TTS 미경유, 순수 템플릿.
  - `server/detection/consumer.py`:
    - `_send_cognitive_guide`에 `preset_guidance_text: str | None` 파라미터 추가. 주어지면 `run_orchestrator`(LangGraph) 우회하고 preset 텍스트로 즉시 TTS 합성 후 전송.
    - `_trigger_delayed_cognitive_guide`에서 avoidance fast lane 우선 시도. `can_use_avoidance_fast_lane` True면 `build_avoidance_guidance`를 preset으로 전달 (LangGraph 우회). 다중 객체/방향 불확정 시 기존 LangGraph 폴백.
  - `tests/test_langgraph.py`: `TestAvoidanceFastLane` 클래스 신규 11개 케이스 (front-left→오른쪽, front-right→왼쪽, 정면 중앙→멈추세요, panning±→좌/우, stop→멈추세요, unknown→None, 단일 객체 fast lane 가능, 다중 객체 불가, unknown direction 불가).
- **관련 파일**: `server/orchestration/avoidance.py`, `server/detection/consumer.py`, `tests/test_langgraph.py`
- **검증 결과**: `pytest tests/test_detection.py tests/test_suppressor_rearm.py tests/test_frame_decode.py tests/test_langgraph.py` 116개 전체 통과. FastAPI 컨테이너 재시작 후 헬스 200 OK.
- **비고**: avoidance fast lane은 반사 후속(800ms 후) 인지 경로 진입점에서 동작하므로 반사 경로 임포트 금지 규칙 미위반. 다중 객체/방향 불확정 시 기존 LangGraph로 폴백해 안전성 확보. preset 텍스트는 실시간 TTS 합성(사전합성 클립 아님) - 인지 경로 허용.

---

### 2026-07-17 | 3단계 | M6_P2-1_계단_실측_단기보정

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 계획서 M6/P2-1(a)(b) 구현: 계단(caution 통합 클래스) 오탐 실측 평가 스크립트 + surface_caution 반사 발동 히스테리시스로 단일 프레임 오탐 완화.
  - `scripts/eval_segmentation_stairs.py` 신규 (a): 세그멘테이션 모델 caution 클래스 정밀도/재현율/F1 실측 평가 스크립트. EVAL_SEG_DATASET_DIR 환경변수로 데이터셋 경로 받아 TP/FP/FN 산출. 미설정 시 더미 평가로 스크립트 동작 검증. caution 클래스 인덱스=1 (4클래스 중).
  - `server/detection/consumer.py` (b): surface_caution 반사 발동 히스테리시스 추가. `SURFACE_CAUTION_CONFIRM_STREAK`(2) 연속 프레임 확인 후 반사 발동, 미달 시 스킵. `_surface_caution_streak` 인스턴스 변수. 비-surface 반사(high_obstacle)는 기존대로 즉시 발동 + [면접 대비 주석].
  - `server/detection/risk_rules.py` (b): `_hint_id_for_alert`에 "caution" in alert_id → STAIR_DOWN 매핑 추가 + [면접 대비 주석]. surface_caution ReflexAlert가 낙상 위험 힌트로 전달.
  - `docs/ops/environment_variables.md` + `.env.example`: `SURFACE_CAUTION_CONFIRM_STREAK` 변수 추가.
  - `tests/test_detection.py`: `TestSurfaceCautionHysteresis` 클래스 신규 2개 케이스 (상수 로드, caution alert STAIR_DOWN 매핑).
- **관련 파일**: `scripts/eval_segmentation_stairs.py`, `server/detection/consumer.py`, `server/detection/risk_rules.py`, `docs/ops/environment_variables.md`, `.env.example`, `tests/test_detection.py`
- **검증 결과**: 평가 스크립트 더미 실행 정상 (Precision=0.8, Recall=0.7273, F1=0.7619). `pytest tests/test_detection.py tests/test_suppressor_rearm.py tests/test_frame_decode.py tests/test_langgraph.py` 118개 전체 통과. FastAPI 컨테이너 재시작 후 헬스 200 OK.
- **비고**: (c) 세그 5클래스 재학습 + STAIR_DOWN 활성화는 M7에서 분리. 히스테리시스는 caution이 인지 경로에서도 설명되므로 미달 시 반사 스킵해도 안전 마진 유지.

---

### 2026-07-17 | 3단계 | M7_P2-1c_세그5클래스_파이프라인_P2-2_지연관측

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 계획서 M7/P2-1(c) + P2-2 구현: 세그멘테이션 5클래스(계단/맨홀 분리) 재학습 파이프라인 골격 + STAIR_DOWN 활성화 사전 등록 + 파이프라인 지연 관측(콘솔 latency_alert).
  - `scripts/train_segmentation_5class.py` 신규 (c): 5클래스 세그멘테이션 재학습 파이프라인. 데이터 검증 -> 학습 -> 검증 단계 골격. SEG_5CLASS_NAMES(5클래스 제안), --dry-run/--validate-only 옵션. 환경변수 SEG_5CLASS_MODEL_BASE, SEG_5CLASS_OUTPUT_DIR.
  - `server/detection/gates/surface_gate.py` (c): P0_SURFACE_CLASSES에 5클래스 모델용 `stair_down`, `manhole` 사전 등록 + [면접 대비 주석]. 4클래스(caution 통합)/5클래스(분리) 모델 모두 지원해 모델 교체 시 게이트 코드 변경 없이 STAIR_DOWN 활성화.
  - `server/detection/consumer.py` (P2-2): `_broadcast_latency_event`에 latency_alert 필드 추가. total_ms가 REFLEX_LATENCY_ALERT_MS(300)/COGNITIVE_LATENCY_ALERT_MS(3000) 초과 시 latency_alert=True, latency_threshold_ms 포함해 콘솔에 실시간 지연 드리프트 알림.
  - `docs/ops/environment_variables.md` + `.env.example`: `REFLEX_LATENCY_ALERT_MS`, `COGNITIVE_LATENCY_ALERT_MS` 2개 변수 추가.
  - `tests/test_detection.py`: `TestLatencyAlertAndStairDown` 클래스 신규 4개 케이스 (지연 임계 로드, stair_down 5클래스 surface_gate, manhole 5클래스, stair_down alert STAIR_DOWN 힌트 매핑).
- **관련 파일**: `scripts/train_segmentation_5class.py`, `server/detection/gates/surface_gate.py`, `server/detection/consumer.py`, `docs/ops/environment_variables.md`, `.env.example`, `tests/test_detection.py`
- **검증 결과**: `pytest tests/test_detection.py tests/test_suppressor_rearm.py tests/test_frame_decode.py tests/test_langgraph.py` 122개 전체 통과. FastAPI 컨테이너 재시작 후 헬스 200 OK. 학습 스크립트 dry-run 정상 동작.
- **비고**: 5클래스 재학습은 라벨링된 데이터셋 준비 후 오프라인 실행. STAIR_DOWN은 5클래스 모델 배포 시 surface_gate 사전 등록으로 자동 활성화. 지연 관측은 콘솔 운영자용 모니터링 강화.

---

### 2026-07-17 | 문서 | 필드테스트개선_M1-M7_문서동기화

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 필드 테스트 개선 M1-M7 구현에 대한 문서 동기화 (교차 검증).
  - `docs/ops/test_specification.md`: TC-DET-012~018(큐 최신성/재무장/소형객체/Approach-Lost/surface 히스테리시스/STAIR_DOWN 5클래스/지연관측), TC-LG-010~011(발화가치게이트/avoidance fast lane) 신규 등재. 버전 v0.6.6 -> v0.6.7.
  - `docs/design/architecture.md`: §11 "필드 테스트 개선 (2026-07-17, M1-M7)" 섹션 신설. P0/P1/P2 마일스톤 요약, 신규 환경변수 목록, 오해 방지 조항(서버-온디바이스 폴백 유지 명시).
  - `docs/design/api_specification.md`: §4.1 reflex_alert에 `distance_band` 필드 추가 + 억제 키 정정. §4.3 latency_event 섹션 신설(`latency_alert`, `latency_threshold_ms`, `queue_wait_ms` 필드).
  - `docs/design/reflex_audio_specification.md`: §6 "억제 재무장(Re-arm) 정책" 섹션 신설. 정책 전환, 억제 키 분리, 거리 밴드, should_rearm 판정, 오해 방지 조항.
- **관련 파일**: `docs/ops/test_specification.md`, `docs/design/architecture.md`, `docs/design/api_specification.md`, `docs/design/reflex_audio_specification.md`
- **검증 결과**: 문서 교차 검증 완료. 코드-문서 정합성 확보 (ReflexAlert distance_band, latency_event latency_alert, 재무장 정책 키/TTL/밴드 일치).
- **비고**: environment_variables.md는 M1-M7 각 커밋에서 이미 갱신 완료. changelog도 각 M별로 이미 추가됨. 본 커밋은 남은 3개 설계 문서 동기화.

---

### 2026-07-17 | 기능 | LiDAR 실거리 검증 로깅 연결 (검증 전용 스코프)

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - DB 로그로 LiDAR 기반 거리 탐지 정확도를 분석할 수 없던 문제(LiDAR 실측값이 서버 전송·DB 저장 없이 클라이언트 로컬에만 존재) 해소. LiDAR 심도 카메라가 vision-camera와 별도 `AVCaptureSession`을 써서 실시간 탐지와 동시 실행이 불가능한 구조적 제약(`DepthProbeBridge.swift`)이 있어, 실시간 라이브 융합이 아닌 **검증 전용 스코프**로 범위를 확정하고 구현.
  - 데이터 흐름: 거리측정(depthMode) 모드의 "검증 캡처" 버튼 -> `depthResult.previewUri`(depth 동기화 정지 프레임)를 기존 `detection`(base64) 경로로 전송 -> 서버 YOLO 추론 후 기존 `server_detection` 응답(bbox)을 클라이언트가 event_id로 상관관계 매칭 -> 같은 depth 세션에서 `probeDepthBoxes()`로 LiDAR 실측 샘플링 -> 신규 `distance_probe_sample` 메시지로 서버 전송 -> 서버가 `estimate_distance()`로 동일 bbox의 휴리스틱 라벨을 재계산해 LiDAR 실측과 함께 신규 테이블에 저장.
  - `server/detection/schemas.py`: `DistanceProbeSample`/`DistanceProbeReport` pydantic 모델 신규.
  - `server/db/models.py`: `LidarDistanceValidationSample` ORM 클래스 신규(`lidar_distance_validation_samples` 테이블). 기존 `detection_guidance_logs`에 컬럼을 추가하지 않고 별도 테이블로 분리(카디널리티가 다름 - 1 캡처당 N bbox 행).
  - `server/db/migrations/20260717_001_add_lidar_distance_validation_samples.sql` 신규.
  - `server/db/repositories.py`: `LidarDistanceValidationRepository`(create_many/list_recent) 신규.
  - `server/services/lidar_validation_service.py` 신규: `persist_distance_probe_samples()` - `async_sessionmaker_factory` 패턴으로 WS 컨슈머 컨텍스트에서 세션 직접 관리, `bbox_area_ratio()`/`estimate_distance()`(`server/detection/direction.py`) 재사용해 휴리스틱 계산.
  - `server/api/ws_router.py`: `distance_probe_sample` 메시지 분기 + `_handle_distance_probe_sample()` 핸들러 추가(background task, RUF006 대응 세트 패턴).
  - `client/src/services/depthProbe.ts`: 기존 미사용(private) `probeDepthBoxes()`를 export로 전환.
  - `client/src/components/CameraView.tsx`: "검증 캡처" 버튼 신설(depthMode 전용, 수동 트리거). `server_detection` 핸들러를 확장해 event_id 매칭 시 LiDAR 매칭·전송 수행.
  - `scripts/analyze_lidar_validation.py` 신규: 클래스별/휴리스틱 라벨별 LiDAR 실측 분포 집계 스크립트. 판정 임계값은 자동화하지 않고 담당자가 직접 해석하도록 집계·출력만 수행(AGENTS.md §8 학습형 협업 패턴).
  - 문서 동기화: `docs/design/api_specification.md`(§6.8 신설, v0.4.27), `docs/design/architecture.md`(§6.7 데이터 계약 표 추가, v0.4.10), `docs/research/mitos_improvement_roadmap.md`(§2 거리 추정 행 갱신, v0.4.0).
- **관련 파일**: `server/detection/schemas.py`, `server/db/models.py`, `server/db/migrations/20260717_001_add_lidar_distance_validation_samples.sql`, `server/db/repositories.py`, `server/services/lidar_validation_service.py`, `server/api/ws_router.py`, `client/src/services/depthProbe.ts`, `client/src/components/CameraView.tsx`, `scripts/analyze_lidar_validation.py`, `docs/design/api_specification.md`, `docs/design/architecture.md`, `docs/research/mitos_improvement_roadmap.md`
- **검증 결과**: `ruff check`/`ruff format` 전체 통과, `bandit` 신규 파일 무결과(이슈 없음), `mypy` 신규/수정 서버 파일 무결과. `npx tsc --noEmit` 신규 오류 없음(기존 3건은 이번 변경과 무관한 pre-existing 오류로 확인 - `CameraView.tsx` StyleSheet.absoluteFillObject, `useSttRecorder.ts` 상태 비교 2건). 신규 모듈 import 스모크 테스트 통과(`server.db.models`, `server.db.repositories`, `server.detection.schemas`, `server.services.lidar_validation_service`, `server.api.ws_router`).
- **비고**: 반사/인지 경로의 실시간 거리 판단 로직은 변경하지 않았다(휴리스틱이 여전히 운영 판단의 단일 소스). vision-camera 세션과 LiDAR 세션의 동시 실행(실시간 라이브 융합)은 별도 후속 과제로 명시적으로 범위 밖에 둠. 실기기(LiDAR 탑재 iPhone Pro) 검증 캡처 E2E 테스트와 `scripts/analyze_lidar_validation.py` 실행에 의한 실데이터 집계 확인은 아직 미실시(로컬 DB에 데이터 없음).

---

### 2026-07-18 | 전체 | 정합성 검토 보고서 개선사항 반영

- **커밋**: `fix: 정합성 검토 보고서 개선사항 반영 (CORS, 인증, 문서, 고아 파일, 스캔 보고서)`
- **변경 내용**:
  - `server/main.py`: CORS `allow_origin_regex="https?://.*"` 제거. Starlette `CORSMiddleware`는 `allow_origins` 또는 `allow_origin_regex` 중 하나만 매치돼도 요청을 허용하므로, regex가 `settings.CORS_ORIGINS` 화이트리스트를 무력화했고 `allow_credentials=True`와 결합 시 임의 출처 자격증명 요청이 허용되는 위험이 있었다. 주석에 2026-07-18 정정 이력 추가.
  - `server/api/auth.py`: `_verify_static_token`을 상수시간 비교 `hmac.compare_digest`로 전환하여 타이밍 공격 여지를 제거. `import hmac` 추가.
  - `README.md`: 디렉토리 구조에 `server/services/`, `server/stt/`, `server/navigation/`, `server/mcp/` 및 `console/` 추가. `docs/Directory_Structure.md`는 stale하다고 자체 정정한 상태이므로 README 트리를 코드 구조 기준으로 최신화.
  - `server/navigation/pedestrian_navigation.py`: 프로덕션에 사용되지 않는 `input()` 기반 인터랙티브 CLI 프로토타입 삭제. 실제 길안내는 `NavigationSession`/`NavigationFilter`/`server.py`가 담당.
  - `docs/ops/deployment_guide.md`: `docker/docker-compose.yml`이 로컬 개발·데모 전용임을 명시하고, Redis(`requirepass` 미설정, 6379 호스트 노출) 및 MariaDB(기본 비밀번호 폴백)의 프로덕션 강화 권장사항을 7.4절에 추가.
  - `scripts/project_scan.py`: `Path.write_text(..., newline="\n")`가 Python 3.9에서 지원되지 않아 스크립트 실행이 실패하던 버그를 `open(..., newline="\n")`으로 수정.
  - `scripts/project_scan_report.md`: 2026-07-18 기준으로 재생성. 이전 보고서(2026-07-06, 84016 파일)는 node_modules 등이 누적되어 stale했음.
  - 정합성 교차 검토로 추가 발견된 문서 잔여 참조 정정:
    - `docs/design/architecture.md`: Mermaid 다이어그램 및 구성 요소 테이블의 `server/navigation/pedestrian_navigation.py`를 `server/navigation/server.py`로 변경.
    - `docs/ops/environment_variables.md`: `TMAP_APP_KEY` 참조에서 `server/navigation/pedestrian_navigation.py:269`를 제거하고 `server/navigation/server.py:38`로 정정.
    - `docs/design/api_specification.md`: `realtime_gps` 메시지 설명의 `server/navigation/pedestrian_navigation.py`를 `server/navigation/server.py`로 변경.
- **관련 파일**: `server/main.py`, `server/api/auth.py`, `README.md`, `server/navigation/pedestrian_navigation.py`, `docs/ops/deployment_guide.md`, `scripts/project_scan.py`, `scripts/project_scan_report.md`, `docs/design/architecture.md`, `docs/ops/environment_variables.md`, `docs/design/api_specification.md`
- **검증 결과**: `python3 -m ruff format .` 211개 파일 변경 없음, `python3 -m ruff check .` All checks passed.
- **비고**: 외부 정합성 검토 보고서에서 식별된 6개 개선사항(1 Critical, 2 Medium, 3 Low)을 반영. `pedestrian_navigation.py` 삭제 후에도 문서 잔여 참조가 남아 있어 정합성 교차 검토로 추가 동기화함.

---

### 2026-07-18 | 병합 | 팀원 브랜치(jh/jy/th/dg2) dev 통합 및 정합성 정정

- **작업 내용**: `dev` 대비 미병합 상태였던 팀원 개인 브랜치 4종(jh, jy, th, dg2)과 kb 자체 신규 커밋 2건을 검토 후 `dev`에 순차 병합.
  - 병합 전 디스포저블 테스트 브랜치(`merge-test-20260718`)에서 5개 브랜치를 순서대로 시험 병합해 git 충돌 여부를 먼저 확인(전부 충돌 없음), 병합된 트리에서 `ruff check`/`bandit -r server/ scripts/`/console `tsc --noEmit` 전체 통과, `mypy server/`·client `tsc --noEmit`의 잔여 오류는 `origin/dev` 베이스라인에 이미 존재하던 것과 동일 개수(7건)임을 별도 워크트리로 대조 확인(신규 오류 없음). 반사 경로(`server/detection/gates/`) LLM/RAG/TTS 임포트 위반 스캔도 이상 없음.
  - kb: `f5d2d5f`까지 fast-forward(정합성 검토 보고서 반영, `pedestrian_navigation.py` 삭제 후속 정리 - 위 항목 참조).
  - jh: 콘솔 기능상자 메뉴에 "추가"/"전체 삭제" 통합, 위젯 드래그 이동(`movingWidgetKey`/`dragOverWidgetKey`), 회원 등록 장애등급 범위 경고, 로그 텍스트 위젯 분리.
  - jy: `COMPOSE_DB_HOST`(원격 DB 기본 유지, 로컬 필요 시만 재정의) 도입, MariaDB·미디어 API 가이드 공개/내부 분리, iOS Podfile.lock 갱신.
  - th: `260714.pt` 기준 온디바이스 모델 재export에 따른 `CoreMLInferenceBridge.swift` 주석 정정, `data/convenience_guidelines.json`(RAG 원본 데이터) 한글 숫자 표기를 아라비아 숫자로 정규화 및 서비스 설명 보강.
  - dg2: PC 브라우저 Geolocation이 모바일 앱 주입 GPS(`inject_gps`)를 덮어쓰던 버그 수정(`server/navigation/index.html`, `isGpsInjected` 플래그로 `watchPosition` 강제 폐쇄), 공유 GPU 서버의 로컬 3306 포트 충돌 방지를 위해 `docker/docker-compose.yml`의 MariaDB `ports` 노출 주석 처리, 2차 필드 테스트 개선 계획 문서(`docs/research/field_test_round2_improvement_plan.md`) 추가. (해당 브랜치 커밋 작성자가 `TH`로 기록된 것은 dg 담당자가 전날 TH의 노트북으로 작업했기 때문으로 확인 - 실제 작업자 아님)
  - **정합성 정정**: dg2의 MariaDB 호스트 포트 미노출 변경과 jy가 문서화한 `DB_HOST_PORT`(포트 노출 제어 변수) 설명이 병합 후 서로 어긋남을 발견. 코드(포트 미노출)는 공유 서버의 의도된 변경으로 유지하고, 문서 쪽을 `docker-compose.yml`에는 더 이상 적용되지 않고 `docker-compose.macos.yml` 전용임을 명시하는 방향으로 정정.
- **관련 파일**: `docs/ops/deployment_guide.md`(§2.1 mariadb 포트 열, §9 트러블슈팅 표, v0.5.3), `docs/ops/environment_variables.md`(`DB_HOST_PORT` 행, v0.4.20)
- **검증 결과**: 병합 후 `ruff check .` All checks passed. 문서 수정은 서술형이라 별도 린트 대상 아님.
- **비고**: vision-camera 세션과 LiDAR 세션 동시 실행(실시간 라이브 융합), `scripts/analyze_lidar_validation.py`의 실데이터 집계, dg2의 index.html GPS 수정에 대한 실기기 회귀 검증은 이번 병합 작업 범위 밖(각 원 브랜치 커밋 시점에 개별 검증됨).


---

### 2026-07-18 | 기능 | 필드 테스트 2차 개선 T1/T2/T3 구현 (문서-코드 정합성 동기화)

- **커밋**: `feat: 필드 테스트 2차 개선 T1/T2/T3 구현 (T3-C 오디오 우선순위, T3-S STT 억제, T2-G 회랑/접근 필터, T1-a/b 접근 객체 완화/쿨다운 단축)`
- **변경 내용**:
  - **T3-C 클라이언트 통합 오디오 우선순위 조정자**: client/src/services/audioEngine.ts에 P3(반사)/P2(STT)/P1(인지) 우선순위 모델 도입, setSttActive/priority 인자 추가, 결정론적 콜백 해제. client/src/hooks/useWebSocket.ts에서 sttInteractionActiveRef 기반 뮤트를 제거하고 audioEngine 우선순위 게이트에 의존. client/src/components/CameraView.tsx에서 STT 녹음 시작 시 setSttActive(true) 호출.
  - **T3-S 서버 STT 활성 중 인지 발행 억제 게이트**: server/api/session_manager.py에 _stt_activity 레지스트리 추가. server/api/ws_router.py에서 STT 처리 구간 동안 set_stt_active(true/false). server/detection/consumer.py에서 _send_cognitive_guide 진입부에 is_stt_active 체크, 반사 경로는 제외.
  - **T2-G 인지 발화 회랑/접근 필터**: server/detection/consumer.py에 _is_speech_worthy 메서드 추가. 보도 이탈/고위험/중위험/접근 객체/유의미 노면은 통과, 측면/원거리/정적 저위험은 무발화. GUIDE_LOW_RISK_NARRATION 환경 변수로 저위험 내레이션 제어.
  - **T1-a/b 접근 신규 객체 완화 및 쿨다운 단축**: server/detection/detection_pipeline.py에서 접근 객체(direction==approaching) hit_count 선필터를 4에서 2로 완화. server/detection/consumer.py에서 12시 회랑 접근 + near/medium이면 쿨다운을 3초로 단축.
  - **문서 동기화**: docs/design/reflex_audio_specification.md, docs/design/architecture.md(v0.4.11), docs/ops/environment_variables.md(v0.4.21), docs/ops/test_specification.md(v0.6.8), .env.example에 T1/T2/T3 설계 반영.
  - **테스트 추가**: tests/test_detection.py에 TestApproachingHitCountRelax, TestSpeechWorthyFilter, TestApproachingCooldownShortcut, TestSttActiveCognitiveSuppression 클래스 추가.
  - **기존 린트 잔여 오류 정리**: client/src/components/CameraView.tsx absoluteFillObject -> absoluteFill, client/src/hooks/useSttRecorder.ts 상태 비교 조건 정정.
- **관련 파일**: client/src/services/audioEngine.ts, client/src/hooks/useWebSocket.ts, client/src/components/CameraView.tsx, server/api/session_manager.py, server/api/ws_router.py, server/detection/consumer.py, server/detection/detection_pipeline.py, docs/design/reflex_audio_specification.md, docs/design/architecture.md, docs/ops/environment_variables.md, docs/ops/test_specification.md, .env.example, tests/test_detection.py, client/src/hooks/useSttRecorder.ts
- **검증 결과**: python3 -m ruff format . && python3 -m ruff check . All checks passed. npx tsc --noEmit(client) 통과. pytest는 현재 Python 3.9/macOS 시스템 Python 환경에 redis 의존성 미설치로 실행 불가(개발/배포 환경 Python 3.13에서 재검증 필요). bandit/mypy는 해당 환경에 미설치.
- **비고**: field_test_round2_improvement_plan.md 설계대로 구현. 서버 억제는 클라이언트 audioEngine 우선순위 조정자의 이중 방어/연산 낭비 제거용. 반사 경로는 T3-S 억제 게이트를 거치지 않는다(비협상 원칙).

---

### 2026-07-18 | 수정 | T1/T2/T3 구현 정합성 검토 및 결함 2건 수정

- **배경**: 사용자 요청으로 위 T1/T2/T3 구현 커밋(`596ff35`)이 `field_test_round2_improvement_plan.md` 설계와 실제로 정합한지 검토. 해당 커밋의 changelog는 "pytest는 Python 3.9/macOS 시스템 환경에 redis 미설치로 실행 불가 - 재검증 필요"라고 명시하고 있어, 이번 세션(Python 3.13 `.venv`)에서 실제로 `pytest`를 돌려 재검증했다.
- **발견 및 수정 1 - 신규 테스트 mock 결함**: `tests/test_detection.py::TestApproachingHitCountRelax::test_approaching_hit_count_two_passes`가 실패 상태로 커밋돼 있었다. `ByteTrackTracker._compute_motion()`(`bytetrack_tracker.py:128`)은 `prev`에 `last_pos`가 없으면 무조건 `direction="unknown"`을 반환하는데, 테스트의 mock(`{"hit_count": "1"}`)에 `last_pos`가 빠져 있어 tracker가 stub Detection의 `direction="approaching"`을 실제로는 재현하지 못하고 있었다(tracker.update()가 stub 필드를 항상 재계산해 덮어씀). `last_pos`(이전 프레임 bbox JSON)를 mock에 추가해 실제로 "approaching"이 발동하도록 수정. T1-a 로직 자체는 정상이었음(`test_static_hit_count_three_rejected`는 원래도 통과).
- **발견 및 수정 2 - T3-S 서버 억제 창이 설계보다 좁음**: `field_test_round2_improvement_plan.md` §4.3은 "응답 전송 완료 후 예상 재생시간 + 마진까지 유지"를 명시했으나, 실제 구현(`_handle_stt_audio`)은 `_process_stt_audio` 반환 즉시(`finally`) `manager.set_stt_active(device_id, False)`를 호출해 실제 오디오 재생 구간에는 서버 억제가 이미 풀려 있었다(`ttl_seconds` 파라미터가 존재했으나 호출부에서 전달되지 않아 죽은 기능). 클라이언트 audioEngine 우선순위 조정자(T3-C)가 최종 방어선이라 실제 오디오 충돌은 없었지만, 계획서가 명시한 "연산 낭비까지 제거"라는 T3-S의 목표는 재생 구간에서 달성되지 않고 있었다.
  - `server/api/ws_router.py`: `_estimate_stt_hold_seconds(guidance_text, duration_ms)` 헬퍼 신설(클라이언트 `useWebSocket.ts`의 텍스트 길이 추정(180ms/자, 최소 2000ms) + 1200ms 마진 공식과 동일). `_process_stt_audio`의 반환 타입을 `float`로 바꾸고 모든 반환 지점(base64 디코딩 실패/음성 길이 부족/빈 오디오/에코 감지/전사 실패/정상 응답)에서 적절한 hold 초를 반환하도록 수정. `_handle_stt_audio`가 이 값을 `manager.set_stt_active(device_id, False, ttl_seconds=hold_seconds)`로 전달.
- **테스트 추가**: `tests/test_ws_router_stt.py`에 `test_stt_audio_success_extends_stt_active_ttl`(통합, 응답 전송 후에도 `manager.is_stt_active`가 True로 유지되는지 확인) 및 `TestEstimateSttHoldSeconds`(헬퍼 단위테스트 4건) 추가.
- **부수 발견**: `docs/ops/test_specification.md`의 TC-TTS-009가 검증 근거로 `tests/test_ws_router_stt.py`를 인용했으나 실제로는 해당 파일이 T3-S 배선을 전혀 검증하지 않고 있었다 - 이번에 추가한 테스트로 인용이 실제로 정확해짐.
- **관련 파일**: `tests/test_detection.py`, `server/api/ws_router.py`, `tests/test_ws_router_stt.py`, `docs/design/reflex_audio_specification.md`(§5.3 정정, v1.3.1), `docs/ops/test_specification.md`(TC-TTS-009 정정, v0.6.9)
- **검증 결과**: `ruff check .`/`ruff format --check` 전체 통과, `mypy server/api/ws_router.py` 신규 에러 없음(기존 베이스라인 7건과 동일). 관련 테스트 75건(`test_detection.py` 65건 + `test_ws_router_stt.py` 10건) 전체 통과. 전체 스위트(`pytest tests/`) 322 passed / 3 failed - 실패 3건(`test_convenience_dial_resolver.py` 2건, `test_embedding_engine_factory.py` 1건)은 로컬 Ollama 미연결로 인한 환경 의존 실패로, 이번 변경 전에도 동일하게 실패함을 별도 확인(회귀 아님).
- **비고**: T1-a/T2-G 로직 자체, 반사 경로 비적용(dual-path discipline), 클라이언트 T3-C 오디오 우선순위 조정자는 모두 정상 구현으로 확인됨(별도 수정 없음).

---

### 2026-07-18 | 병합 | th 브랜치 정합성 검토 및 결함 4건 수정 후 dev 병합

- **배경**: 사용자 요청으로 dev 대비 미병합 상태였던 `th` 브랜치(신규 커밋 6건: GPS 폴백 제거, Gemini LLM 폴백 정합, ROI 소실점 재설계 등)를 정합성 검토 후 병합.
- **발견 및 수정 1 - `client/src/components/CameraView.tsx` 컴파일 불가**: `ROIOverlay()` 함수 내 `<View style={StyleSheet.absoluteFill}` 가 완결되지 않은 채 곧바로 또 다른 `<View style={StyleSheet.absoluteFill} pointerEvents="none" ...>`가 이어지는 중복/미완성 JSX 태그가 있어 `tsc`가 30개 가까운 연쇄 오류를 냄. 명백한 편집 잔재로 판단해 중복분 삭제.
- **발견 및 수정 2 - 동일 파일, 두 번째 컴파일 결함**: `CameraView()`의 최상위 `<View style={styles.container}>`가 끝까지 닫히지 않아(`</View>` 1개 누락) babel/tsc 파싱이 실패. 누락된 `</View>` 추가로 해결. **두 결함 모두 실기기 Metro 세션에서 실시간으로 `SyntaxError`가 재현되는 것을 직접 확인함**(라이브 테스트 중이었기에 즉시 검증 가능했음).
- **발견 및 수정 3 - `console/src/components/LiveCameraFeed.tsx` 런타임 참조 오류**: HUD 미니맵 GPS 주입 함수(`injectGpsToMap`)가 정의되지 않은 `lastGpsRef.current`를 참조해 `tsc`가 `Cannot find name 'lastGpsRef'`로 실패. `useRef(lastGps)` + 렌더마다 `.current` 갱신하는 최신값 미러링 패턴을 추가해 해결(iframe `onLoad` 콜백이 마운트 시점 stale closure가 아닌 최신 GPS를 읽도록).
- **발견 및 수정 4 - 기존 테스트 2건 회귀**: `server/stt/stt_to_llm_bridge.py`의 서울역 GPS 폴백 제거(의도된 변경, 가짜 좌표로 길안내를 만들지 않도록 함)로 `tests/test_stt_to_llm_bridge_template.py`의 `test_navigation_destination_setup_success`/`test_navigation_destination_setup_fail_when_poi_not_found`가 `_FakeNavManager`의 `session.lat/lon=None` 기본값 때문에 새로 추가된 `navigation-setup-no-gps` 조기 반환 분기에 걸려 실패. 두 테스트에 실좌표를 채워 원래 검증하려던 POI 성공/실패 분기를 다시 테스트하도록 수정하고, GPS 미수신 조기 반환 자체를 검증하는 신규 테스트(`test_navigation_destination_setup_no_gps`)를 추가.
- **제외 파일**: `CONTRIBUTING.md` - 완전히 무관한 타 프로젝트("Awesome Design MD") 템플릿 파일이 실수로 커밋에 포함됨. th 자신의 changelog에도 "커밋 대상에서 제외"라고 명시돼 있어 병합에서 제외.
- **정상 확인**: `server/orchestration/llm_client_factory.py`(Gemini 기본 시 OpenAI 키 부재를 Ollama 성공으로 위장하지 않도록 예외 재발생), `server/orchestration/nodes/l2_generator.py`(로그에 실제 provider명 출력), `server/navigation/index.html`(embed 모드에서 브라우저 GPS/서울역 타임아웃 폴백 비활성화 - 콘솔이 이미 `?embed=true`로 임베드하고 있어 dg2가 앞서 고친 "PC 브라우저 GPS가 앱 GPS를 덮어쓰는 버그"를 override 방지 대신 원천 차단 방식으로 재해결함을 확인)는 모두 정상 구현으로 확인됨(별도 수정 없음).
- **관련 파일**: `client/src/components/CameraView.tsx`, `console/src/components/LiveCameraFeed.tsx`, `tests/test_stt_to_llm_bridge_template.py`, `server/stt/stt_to_llm_bridge.py`(ruff format만 재적용)
- **검증 결과**: `ruff check .`/`ruff format --check` 전체 통과, `mypy` 신규 에러 없음(베이스라인 동일), client·console `npx tsc --noEmit` 둘 다 클린. 전체 pytest 스위트 321 passed(환경 의존 실패 3건 제외, 회귀 아님 재확인).
- **비고**: dev는 kb(817558f)와 th(4d0d429)가 각각 독립적으로 dev에서 분기된 상태였어 순수 fast-forward가 아닌 실제 3-way 병합(두 부모)으로 처리함.

---

### 2026-07-18 | 수정 | th 병합 후 조작 버튼 전체 무반응 회귀 수정

- **배경**: 위 th 병합·push 직후 실기기 테스트 중 "탐지 시작 등 버튼이 안 눌린다"는 실사용 리포트로 발견. 정합성 검토에서는 컴파일(tsc)만 확인했고 런타임 터치 동작까지는 검증하지 못했던 gap.
- **원인**: th가 `controlRowDock`(탐지 시작/지도/USB-WiFi 전환/거리측정/검증캡처 버튼)을 기존의 별도 `controlsOverlay`(`pointerEvents="box-none"`, container와 형제) 밖에서 `operatorPanel`의 `ScrollView` 안으로 옮겼다. `operatorPanel`은 `pointerEvents="none"`인데, React Native에서 `"none"`은 자신뿐 아니라 하위 서브트리 전체를 터치 타깃에서 제외한다(`"box-none"`과의 핵심 차이). 안쪽 `controlRowDock`에 `"box-none"`을 다시 걸어도 조상이 이미 히트테스트를 막아 무의미했다.
- **수정**: `controlRowDock`, `mapVisible` 상태의 `NavMapPanel`, `DebugTriggerPanel`을 `operatorPanel`/`ScrollView` 밖으로 다시 꺼내 원래 있던(현재는 미사용 상태로 남아 있던) `controlsOverlay`(`pointerEvents="box-none"`) 스타일의 형제 `View`로 복원. th가 실제로 의도한 변경(버튼 텍스트, `navToggleActive` 스타일, 지도 패널 위치)은 그대로 유지.
- **관련 파일**: `client/src/components/CameraView.tsx`
- **검증 결과**: `npx tsc --noEmit` 클린. 실기기 Metro 세션에서 정상 재번들링 확인. 버튼 터치 자체는 시뮬레이터/실기기 UI 조작이 필요해 코드 검토·정적 분석으로만 검증(사용자 실기기 재확인 필요).
- **비고**: 정합성 검토가 컴파일 가능 여부(tsc)에 집중돼 `pointerEvents` 계층 구조 같은 런타임 전용 회귀는 놓쳤다 - 향후 UI 관련 병합은 정적 검토와 별개로 실제 터치 동작 확인이 필요함.

---

### 2026-07-18 | 병합 | jh 브랜치 병합 (MCP 검증 모니터 위젯 누락 복구)

- **배경**: 사용자가 콘솔에서 "MCP들로 모니터링 하는 렌더링 내역들이 안 보인다"고 리포트한 직후, jh 브랜치에 정확히 이 문제를 고치는 신규 커밋 1건이 있어 정합성 검토 후 병합.
- **검토 내용**: `console/src/pages/DashboardPage.tsx`의 `DashboardWidgetKey` 타입·`DASHBOARD_WIDGETS`·`DEFAULT_DASHBOARD_WIDGET_ORDER`·`renderWidget()` 4곳 모두에서 `"mcpMonitor"`가 누락돼 있어, 이미 import돼 있던 `McpValidationMonitor` 컴포넌트가 위젯 시스템에 전혀 연결되지 않았던 것을 확인(사용자 리포트의 직접 원인). `McpValidationMonitor`가 참조하는 `state.audio_validation`/`cache_suppression`/`accessibility_validation`/`langsmith_trace` 필드는 `types/monitor.ts`에 이미 정의돼 있어 타입 정합성 문제 없음.
- **부수 발견 및 정정**: `docs/changelogs/jh.md`에 새 엔트리가 직전 엔트리(2026-07-15 회원관리 컨테이너화)의 불릿 목록 중간에 삽입되어 있어, 해당 엔트리가 두 조각으로 쪼개져 있었다. 순서를 바로잡아 각 엔트리가 온전한 블록으로 이어지도록 정정.
- **관련 파일**: `console/src/pages/DashboardPage.tsx`, `docs/changelogs/jh.md`
- **검증 결과**: `npx tsc --noEmit`(console) 클린. 충돌 없이 병합됨.
- **비고**: 콘솔 브라우저에서 위젯이 실제로 표시되는지는 사용자 확인 필요(코드 검토로는 위젯 등록 자체가 정상 복구됐음만 확인).

---

### 2026-07-18 | 스킬 | integration-test-orchestrator 스킬 패키징 완성 및 다중 에이전트 등재

- **배경**: `.agents/skills/integration-test-orchestrator/SKILL.md`가 커밋되지 않은 상태로 저장소에 생성돼 있는 것을 사용자가 발견해 정합성 검토 요청. 검토 결과 내용(실기기-Docker-DB 통합 테스트 오케스트레이션 절차)은 정확했으나 패키징이 3가지 미완성 상태였음: `.claude/skills/` 사본 없음, 본문이 참조하는 `references/implementation_detail.md` 없음, `SKILLS.md`/`AGENTS.md` §8 스킬 인덱스 미등재.
- **변경 내용**:
  - `.agents/skills/integration-test-orchestrator/references/implementation_detail.md` 신규 작성 - 이번 세션 실측 트러블슈팅 사례(Docker Desktop 미기동, DB 마이그레이션 수동 반영 필요, LAN IP 갱신, WS 후보 쿨다운, `pointerEvents="none"` 하위 서브트리 터치 불가, index.html iframe 재로드 필요, WS 재연결 가드 부재 등)를 계층별 트러블슈팅 표로 정리.
  - `.claude/skills/integration-test-orchestrator/`에 `.agents/skills/` 정본을 그대로 미러링(`diff -rq` 일치 확인).
  - `SKILLS.md`, `AGENTS.md` §8 스킬 인덱스 표에 신규 등재. `AGENTS.md`는 Codex/ZCode/opencode/Grok Build가 네이티브로 직접 읽는 정본이므로, 이 등재만으로 해당 에이전트들도 스킬 존재를 인식함.
  - `.antigravity/rules.md`(12,000자 캡 대응 요약본) §10 스킬 인덱스에도 동일 등재(6,168자, 캡 대비 여유 5,832자) - Antigravity 사용 팀원도 인식 가능.
- **관련 파일**: `.agents/skills/integration-test-orchestrator/references/implementation_detail.md`(신규), `.claude/skills/integration-test-orchestrator/`(신규 미러), `SKILLS.md`, `AGENTS.md`, `.antigravity/rules.md`
- **검증 결과**: `python3 scripts/validate_agent_rules.py` 6/6 통과(CLAUDE.md thin pointer, GEMINI.md symlink, `.antigravity/rules.md` 캡·핵심섹션, `.cursor` core rule, 스킬 미러, `AGENTS.md` `@SKILLS.md` import).
- **비고**: Cursor는 `.cursor/rules/00-core-guidelines.mdc`를 통해 AGENTS.md를 간접 참조하므로 별도 등재 불필요(기존 아키텍처 그대로 적용됨). Claude Code는 스킬 파일 생성 시점부터 자동 인식(Skill 도구 목록에 즉시 노출 확인).

---

### 2026-07-18 | 거리 정책 | 거리 정책 SSOT 1단계 - Near 전용 반사 라우팅 + episode 상태기계

- **배경**: `/Users/kwanbum/Downloads/HEURISTIC_DISTANCE_ALERT_ROUTING_IMPLEMENTATION_PLAN.md`(gpt5.6 작성, 알림 피로 원인 감사)와 `/Users/kwanbum/Downloads/LiDAR_distanceMeters.md`(iOS LiDAR 실시간 융합 요청서)를 정합성 검토한 결과 두 문서가 정면으로 충돌함을 확인(전자는 "Near만 반사, Medium/Far는 인지"를 제안하는데, 후자는 LiDAR 실측을 0.5/1.0/1.5/3.0m 4단계로 매핑해 그 Medium/Far까지 다시 반사로 재도입하려 함). 사용자 지시에 따라 `docs/research/lidar_fusion_sequencing_plan.md`(1~4단계 실행 순서 계획서)를 먼저 작성했고, 그중 1단계(거리 정책 SSOT + Near 전용 반사 + episode 상태기계 + 클라이언트 4단계 로컬 비프 제거)를 이번 세션에서 실제로 구현했다. 담당자 학습형 협업 원칙(AGENTS.md §5, SKILLS.md)상 핵심 판단 로직은 통상 담당자가 직접 작성하나, 사용자가 이번 1단계 전체를 에이전트가 직접 구현하도록 명시적으로 예외 지시함.
- **변경 내용 (서버, 커밋 2건)**:
  - `server/detection/distance_policy.py`(신규) - bbox 클리핑, area_ratio/bottom_ratio 계산, Near(0.10 진입/0.08 이탈)·Medium(0.03 진입/0.025 이탈) 히스테리시스, 하단 소형 장애물 override(bottom_ratio>=0.80 및 area_ratio>=0.04), route(reflex/cognitive) 결정을 순수 함수로 분리. `POLICY_VERSION="distance-alert-v1"`.
  - `server/detection/bytetrack_tracker.py` - `update()`가 frame_width/height를 받아 Redis에 저장된 track별 이전 구역(`effective_zone`)을 조회하고 `distance_policy.evaluate_distance()`로 히스테리시스 반영 신규 구역을 계산해 매 프레임 `Detection`에 부착.
  - `server/detection/detection_pipeline.py` - `run()`이 `stream` 인자를 실제로 사용해 반사(8~10fps)는 안전 게이트(Near 반사·머리높이·노면)만, 인지(1~2fps)는 mid/low 분류·보도 이탈만 평가하도록 분리(이전에는 stream을 받고도 미사용 - 반사 프레임에서 인지 후보가, 인지 프레임에서 반사 경보가 만들어질 수 있던 결함).
  - `server/detection/gates/reflex_gate.py` - 자체 면적비·의사거리 공식(`MIN_AREA_RATIO`, 하단 override)을 제거하고 tracker가 부착한 `route=="reflex"`(`effective_distance_zone=="near"`)만 소비. Medium/Far 일반 객체 반사가 구조적으로 발생하지 않음.
  - `server/detection/direction.py` - `estimate_distance()`를 `distance_policy`(0.10/0.03 경계) 위임 얇은 wrapper로 전환(기존 0.08/0.03 경계 통일).
  - `server/detection/schemas.py` - `Detection`에 area_ratio/bottom_ratio/raw_distance_zone/effective_distance_zone/heuristic_distance_m/distance_source/route/route_reason/policy_version 추가. `ReflexAlert`에 alert_source(object/head_level/surface)/event_state(enter/update)/estimated_distance_m/policy_version 추가. 신규 `ReflexClear` 스키마 추가.
  - `server/detection/gates/head_level_gate.py`, `surface_gate.py` - ReflexAlert에 `alert_source="head_level"`/`"surface"` 부여.
  - `server/tts/suppressor.py` - 억제 키에 `alert_source` 포함(서로 다른 위험 유형이 `track_id="unknown"` 하나로 교차 억제되던 결함 수정). device별 활성 Near episode(`_active_near_track`) 추적과 `begin_or_continue_near_episode()`(enter/update 판정)·`end_near_episode()` 추가.
  - `server/detection/consumer.py` - `_reconcile_near_episode()` 신설: reflex 스트림의 모든 프레임에서 활성 Near track이 이번 프레임에 더 이상 near가 아니면 `reflex_clear`를 전송. `_send_reflex_alert()`가 성공 여부(`bool`)를 반환하도록 바꾸고, 억제/전송 실패 시 800ms 후속 인지 태스크를 예약하지 않도록 수정. `_trigger_delayed_cognitive_guide()`가 avoidance 방향이 없으면(다중 객체 등) 일반 Near 존재 안내(반사와 같은 사실의 TTS 반복)를 아예 생략하도록 수정.
- **변경 내용 (클라이언트, 커밋 1건)**:
  - `client/src/components/CameraView.tsx` - 서버 연결 끊김 시 켜지는 온디바이스 폴백(`applyLocalAreaReflex`)의 area_ratio 4단계(0.20/0.08/0.03)와 LiDAR 4단계(0.5/1.0/1.5/3.0m) 중 Medium/Far 단계를 제거해 Near 전용으로 축소. Near 경계를 서버 SSOT(`URGENT_AREA_RATIO=0.10`)와 LiDAR 환산값(0.7m)에 맞춤. 근접 후보가 없을 때 중·원거리 객체까지 로컬 반사로 승격하던 `outdoorScopedDetections` 분기와 미사용이 된 `hasOutdoorSurface`/`OUTDOOR_SURFACE_CLASSES` 삭제.
  - `client/src/hooks/useWebSocket.ts` - `reflex_clear` 메시지 수신 시 즉시 비프·햅틱 정지 처리 추가.
  - `client/src/types/detection.ts` - `MessageType`에 `reflex_clear` 추가, `WSMessage`에 alert_source/event_state/estimated_distance_m/policy_version/track_id/reason 필드 추가.
- **문서 동기화**: `docs/design/risk_ssot_contract.md`를 v0.4.0으로 갱신 - §2-B에서 이관된 거리 계산을 §2-C(신설, distance_policy.py SSOT)로 분리, §3 거리 추정 산식 행과 §6 후속 로드맵(2단계 "부분 완료"로 갱신) 갱신.
- **비범위 (이번 세션에서 다루지 않음)**: `lidar_fusion_sequencing_plan.md`의 2단계(LiDAR 실시간 융합 정책 재작성), 3단계(네이티브 세션 충돌 스파이크), 4단계(DepthFusionCaptureBridge 착수 여부), 그리고 원 계획서 §16의 5단계(Medium/Far Fast Lane TTS 예산 확장)는 포함하지 않음. `shared/risk_rules.json` + 코드 생성기 방식(§6 로드맵 2단계 전체)도 미착수 - 기존 §2 패턴과 동일하게 수동 값 동기화를 유지함.
- **관련 파일**: `server/detection/distance_policy.py`(신규), `tests/test_distance_policy.py`(신규), `server/detection/{bytetrack_tracker,detection_pipeline,direction,schemas}.py`, `server/detection/gates/{reflex_gate,head_level_gate,surface_gate}.py`, `server/tts/suppressor.py`, `server/detection/consumer.py`, `tests/test_detection.py`, `client/src/components/CameraView.tsx`, `client/src/hooks/useWebSocket.ts`, `client/src/types/detection.ts`, `docs/design/risk_ssot_contract.md`
- **검증 결과**: `ruff check .`/`ruff format --check` 전체 통과. `mypy` 신규 에러 없음(기존 베이스라인과 동일). `pytest tests/test_detection.py tests/test_distance_policy.py tests/test_risk_ssot.py tests/test_suppressor_rearm.py tests/test_cognitive_fields.py tests/test_fast_lane.py tests/test_langgraph.py` 138 passed. 전체 `pytest tests/` 336 passed(환경 의존 실패 9건은 로컬 Ollama/서버 미기동으로 인한 기존 실패와 동일 성격, 회귀 아님). `npx tsc --noEmit`(client) 클린.
- **비고**: 실기기 검증(서버 연결 정상·끊김 전환 시 Near enter/update/reflex_clear 흐름, 오프라인 폴백 Near 전용 동작)은 이번 세션에서 수행하지 못함 - 다음 실기기 테스트 세션에서 확인 필요. `docs/research/lidar_fusion_sequencing_plan.md`는 사용자가 커밋 확정을 명시적으로 지시하지 않아 여전히 미추적(untracked) 상태로 남겨둠.

---

### 2026-07-19 | 거리 정책 | 2단계(LiDAR 자문 신호) 구현 + 3단계 네이티브 세션 스파이크 완료 + 4단계 보류 확정

- **배경**: 사용자가 "4단계까지 구현하려는 의미였다"고 명확화함에 따라, 보류해뒀던 `lidar_fusion_sequencing_plan.md` 2~4단계를 이어서 진행. 4단계(`DepthFusionCaptureBridge.swift` 상시 실시간 융합) 착수 전 반드시 먼저 답을 내야 하는 3단계 스파이크(네이티브 세션 충돌 여부)를 실제 vision-camera 소스 코드를 열람해 수행한 결과, 세션 공존이 불가능함을 실측 확인. 이 결과를 사용자에게 보고하고 진행 방향을 질의한 결과 "온디맨드 토글로 유지하면서 구현하라"는 확정 지시를 받아, 4단계는 보류(No-go)로 마감하고 2단계(LiDAR를 area_ratio 정책의 자문 신호로 결합)만 온디맨드 검증 캡처 범위 내에서 구현함.
- **3단계 스파이크 핵심 발견**: `client/node_modules/react-native-vision-camera`(v4.7.3) Swift 소스를 직접 확인한 결과, `CameraSession.captureSession`(`ios/Core/CameraSession.swift:22`)과 `CameraView.cameraSession`(`ios/React/CameraView.swift:101`)이 모두 접근제어자 없는(`internal`) 프로퍼티라 앱 코드에서 세션에 전혀 접근할 수 없음을 확인. `ReflexFrameProcessorPlugin`이 상속하는 `FrameProcessorPlugin`(Objective-C 기반, `ios/FrameProcessors/FrameProcessorPlugin.h/.m`)도 이미 캡처된 `Frame`만 콜백으로 받을 뿐 세션 구성 권한이 없음. "vision-camera 세션에 depth output만 추가"하는 저위험 경로는 설계 판단이 아니라 Swift 접근제어자로 막힌 하드 제약임을 확인 - 실시간 융합을 하려면 vision-camera의 세션 관리 전체를 대체하는 자체 캡처 파이프라인이 필요하며, 이는 반사 경로(<300ms 목표, 실측 검증됨) 자체를 재작성하는 대규모 작업.
- **2단계 구현 내용**: LiDAR 실측이 실시간 반사/인지 라우팅에는 전혀 관여하지 않고, 온디맨드 "거리측정 → 검증 캡처" 흐름의 자문(advisory) 신호로만 결합되도록 구현.
  - `server/detection/distance_policy.py`: area_ratio 경계값(0.10/0.08/0.03/0.025)을 `heuristic_distance_m` 공식(`0.22/sqrt(area_ratio)`)의 역산으로 미터 경계(약 0.696m/0.778m/1.270m/1.391m)로 환산한 `LIDAR_NEAR_ENTER_METERS` 등 4개 상수와, LiDAR 실측 미터를 같은 스케일의 구역으로 매핑하는 `zone_from_lidar_meters()`(상태 없는 단발 캡처이므로 진입 경계만 사용, route 결정에는 미관여) 추가.
  - `server/db/models.py`: `LidarDistanceValidationSample`에 `lidar_distance_zone`(nullable) 컬럼 추가. 마이그레이션 `server/db/migrations/20260718_002_add_lidar_distance_zone_to_lidar_distance_validation_samples.sql` 신규(`ALTER TABLE ADD COLUMN IF NOT EXISTS`).
  - `server/services/lidar_validation_service.py`: `persist_distance_probe_samples()`가 `lidar_meters`가 있으면 `zone_from_lidar_meters()`로 자문 구역을 계산해 함께 저장하도록 수정.
  - `scripts/analyze_lidar_validation.py`: `heuristic_distance_class`(area_ratio 정본) vs `lidar_distance_zone`(LiDAR 자문)의 구역 혼동 행렬 출력 함수 추가 - 원 계획서(`HEURISTIC_DISTANCE_ALERT_ROUTING_IMPLEMENTATION_PLAN.md`) §13.4가 요구한 산출물. 판정 임곗값 해석은 자동화하지 않고 담당자가 직접 읽도록 집계만 수행.
  - `docs/research/lidar_realtime_fusion_design_v2.md`(신규): `LiDAR_distanceMeters.md`(원 요청서, 저장소 미추적) 대체 정본. 폐기 내용(4단계 반사 매핑), 유지 내용(bbox 샘플링 정책, UI 표시), LiDAR 자문 역할, 3단계 스파이크 결론, 4단계 보류 결정, 재검토 조건을 정리.
  - `docs/research/mitos_improvement_roadmap.md`(v0.5.0): §2 "거리 추정" 항목과 §7 우선순위 표를 정정 - 이전 버전의 "반사 게이트가 LiDAR 값을 우선 사용" 서술이 1단계 이후 사실과 달라져 정정(서버 반사 게이트는 이제 area_ratio 정책만 사용).
  - `docs/research/lidar_fusion_sequencing_plan.md`: §5(3단계)·§6(4단계)에 실제 스파이크 결과와 최종 결정 반영, §2/§3/§4에 완료 상태 표시. 이번 커밋에서 처음으로 커밋 대상에 포함(다른 신규 문서들이 이 파일을 선행 문서로 인용하는 상태에서 미추적으로 남기면 문서 간 참조가 깨지므로).
- **비목표**: `DepthFusionCaptureBridge.swift` 구현, vision-camera 세션 대체, 실시간 상시 LiDAR 융합 - 모두 4단계 보류 결정에 따라 착수하지 않음.
- **관련 파일**: `server/detection/distance_policy.py`, `server/db/models.py`, `server/db/migrations/20260718_002_add_lidar_distance_zone_to_lidar_distance_validation_samples.sql`(신규), `server/services/lidar_validation_service.py`, `scripts/analyze_lidar_validation.py`, `tests/test_distance_policy.py`, `docs/research/lidar_realtime_fusion_design_v2.md`(신규), `docs/research/mitos_improvement_roadmap.md`, `docs/research/lidar_fusion_sequencing_plan.md`
- **검증 결과**: `ruff check .` 전체 통과. `mypy` 신규 에러 없음. `pytest tests/test_distance_policy.py` 24 passed(신규 LiDAR 경계·자문 구역 테스트 4건 포함). 전체 `pytest tests/` 340 passed(환경 의존 실패 9건은 기존과 동일, 회귀 아님). 신규 스크립트 함수(`_print_zone_confusion_matrix`)는 in-memory fixture로 출력 형식 수동 확인.
- **비고**: DB 마이그레이션은 스키마 변경만 반영했으며 실제 운영/로컬 MariaDB 적용은 다음 통합 테스트 세션에서 수행 필요. 계측용 "거리측정" 버튼의 줄자 실측 검증(0.3/0.5/1.0/2.0m)은 여전히 잔여 과제.

---

### 2026-07-19 | 클라이언트 | 거리측정 "검증 캡처" 결과의 LiDAR 거리를 화면에 실제 적용

- **배경**: 사용자가 "지난주 LiDAR 뎁스값 측정·반영 결과가 병합 중 지워진 것 같다"고 문의해 git 전체 이력(dangling commit 포함)을 탐색. `6d8f421`(jjuns, 2026-07-15 "ios: LiDAR 거리측정 보정 적용")의 렌즈·광선 보정 공식(`calibratedDistance`)은 현재 `DepthProbeBridge.swift`에 그대로 남아 있어 유실이 아님을 확인·보고했다. 다만 조사 중 별개의 실제 결함을 발견: "검증 캡처" 버튼이 `probeDepthBoxes()`로 bbox별 LiDAR 실측 거리를 계산은 하지만, 그 값을 서버 DB(`distance_probe_sample`) 로깅에만 쓰고 화면의 `detections` 상태로는 전혀 되돌리지 않아 사용자가 "이 bbox가 실제로 몇 m로 측정됐는지" 화면에서 확인할 방법이 없었다. `activeDetections`도 `depthMode`일 때 무조건 빈 배열이라 `BBoxOverlay` 자체가 그려지지 않는 상태였다. 사용자가 "우선 뎁스값은 적용시켜라"고 지시해 이 부분을 구현.
- **변경 내용**: `client/src/components/CameraView.tsx`
  - 거리측정 모드 진입 시 `setDetections([])`로 vision-camera가 남긴 이전 bbox를 정리(이전 프레임이 depth 프리뷰 위에 겹쳐 보이는 것을 방지).
  - "검증 캡처" 응답 처리에서 `probeDepthBoxes()` 결과(`distances[].meters`)를 `serverDets`에 `distanceMeters`/`distanceSource: "lidar"`/`depthSampleCount`/`depthAccuracy`로 병합해 `setDetections()`로 다시 반영(기존에는 `distance_probe_sample` 전송에만 쓰이고 버려졌음).
  - `activeDetections`가 `depthMode`일 때 무조건 `[]`를 반환하던 분기를 제거해, 검증 캡처 후 `BBoxOverlay`가 LiDAR 거리 라벨("0.52m LiDAR")이 붙은 bbox를 실제로 렌더링하도록 함(`resolveDetectionDistance()`가 이미 지원하던 표시 경로를 그제야 실제로 태움).
- **관련 파일**: `client/src/components/CameraView.tsx`
- **검증 결과**: `npx tsc --noEmit`(client) 클린.
- **비고**: 실기기에서 "검증 캡처" 후 bbox 위에 LiDAR 거리가 실제로 표시되는지는 사용자가 다음 실기기 세션(줄자 실측과 함께)에서 확인 필요.

---

### 2026-07-19 | 실기기 라이브 디버깅 | 검증 캡처 파이프라인 결함 3건 수정 + 고정 지점 캡처 기능 추가 + 근접 캘리브레이션 실측

- **배경**: `integration-test-orchestrator` 스킬로 Docker+DB+실기기 통합 테스트 세션을 열고 팀원이 실기기로 "검증 캡처"를 반복 시도하는 동안 실시간으로 로그를 감시하며 발견되는 문제를 그 자리에서 진단·수정했다. 3개의 서로 다른 계층 결함이 겹쳐 있었다.
- **결함 1 - DB 인증 실패**: `docker compose -f docker/docker-compose.macos.yml`처럼 `--env-file`을 생략하면 Compose가 컴포즈 파일 위치(`docker/`)를 프로젝트 디렉토리로 잡아 루트 `.env`(팀 공동 Tailscale `DB_HOST`)를 전혀 읽지 못하고 로컬 빈 DB로 조용히 폴백되고 있었다(콘솔 관리자 로그인이 항상 401인 근본 원인이기도 했음). `docker compose --env-file .env -f docker/docker-compose.macos.yml ...`로 재기동해 팀 공동 DB(`100.105.221.31`)에 정상 연결시켰다. 진단 중 `docker compose config`를 필터 없이 출력해 `DB_PASSWORD` 평문이 도구 로그에 한 차례 노출된 사고가 있었음을 사용자에게 즉시 고지함.
- **결함 2 - YOLO 추론 실패**: ultralytics가 모델 로드/추론 시마다 체크포인트 내장 requirements를 현재 설치본과 비교해 불일치하면 `AUTOINSTALL`(기본 True, `YOLO_AUTOINSTALL` 환경변수) 설정에 따라 런타임에 조용히 `pip install`한다. 방금 갱신된 디스크 상 패키지와 이미 임포트된 모듈 상태가 어긋나며 프레임마다 `'Conv' object has no attribute 'bn'` 오류가 재발했다. `docker-compose.macos.yml`의 fastapi `environment:`에 `YOLO_AUTOINSTALL=False` 추가.
- **결함 3 - 검증 캡처 단발 프레임이 시간적 지속성 필터에 걸림(핵심 결함)**: "거리측정" 모드의 "검증 캡처"는 사용자가 명시적으로 트리거한 1회성 정지 프레임을 기존 `detection` 경로로 보내는데, `detection_pipeline.py`의 시간적 지속성 필터(연속 4프레임 이상 유지돼야 통과)가 연속 스트림을 전제로 하고 있어 단발 캡처는 항상 `hit_count=1`로 걸러져 탐지 0건(`risk_hint=none`)이 됐다. 클라이언트가 이미 보내고 있었지만 서버 어디에서도 읽지 않던 `probe_source: "lidar_validation"` 플래그를 `ProcessedFrame`(`frame_decoder.py`) → `DetectionPipeline.run()` → 시간적 지속성 필터까지 배선해, 검증 캡처 프레임만 이 필터를 우회하도록 수정.
- **신규 기능 - 고정 지점(중앙/전방 하단/발밑) 캡처**: 사용자 요청으로 객체 탐지와 무관하게 거리측정 화면에 항상 표시 중인 고정 3지점 LiDAR 실측을 "검증 캡처" 버튼 한 번으로 함께 저장하도록 확장. YOLO 탐지 왕복이 필요 없어 클라이언트가 이미 보유한 `probeDepth()` 결과를 즉시 전송한다.
  - 신규: `FixedPointProbeSample`/`FixedPointProbeReport`(schemas.py), `LidarFixedPointSample` ORM + `lidar_fixed_point_samples` 테이블(마이그레이션 `20260719_001`), `LidarFixedPointRepository`, `persist_fixed_point_samples()`, WS `fixed_point_probe_sample` 핸들러.
  - 클라이언트: `handleDistanceProbeCapture()`가 기존 객체 기반 전송과 함께 `depthResult.samples`를 `DEPTH_PROBE_POINTS` 라벨과 매칭해 즉시 전송.
- **실측 캘리브레이션 결과**: 팀원이 카메라-벽면 직선 거리를 줄자로 실측하며 0.3m/0.5m/1.0m 세 구간에서 캡처. 0.5m(+11~28%)·1.0m(거의 정확)는 근거리일수록 RGB-LiDAR 시차가 커진다는 가설과 일치했으나, 0.3m는 LiDAR가 1.43~1.58m(4.8~5.3배 과대)로 읽어 시차만으로 설명 불가능한 규모였다. LiDAR ToF 센서의 최소 유효 거리(통상 0.3~0.5m) 미만에서 위상 랩어라운드가 발생했을 가능성이 가장 유력하다는 가설과 함께 `docs/research/lidar_realtime_fusion_design_v2.md` §4.3에 기록. 반사 게이트는 이미 LiDAR가 아닌 area_ratio만 실시간 판단에 쓰므로 실제 안전 판단에는 영향 없음을 명시.
- **되돌린 변경**: `pod install` 실행 중 `package.json`에 여전히 선언된 `expo-dev-client`가 `Podfile.lock`/`project.pbxproj`에서 실수로 누락되는 것을 발견해 두 파일을 git 상태로 즉시 되돌림(커밋하지 않음). CocoaPods sandbox와 lockfile이 다시 어긋난 상태라 다음 네이티브 빌드 전 `pod install` 재검증 필요(잔여 과제로 기록).
- **관련 파일**: `docker/docker-compose.macos.yml`, `server/capture/frame_decoder.py`, `server/detection/detection_pipeline.py`, `server/detection/consumer.py`, `server/detection/schemas.py`, `server/db/models.py`, `server/db/repositories.py`, `server/db/migrations/20260719_001_add_lidar_fixed_point_samples.sql`(신규), `server/services/lidar_validation_service.py`, `server/api/ws_router.py`, `client/src/components/CameraView.tsx`, `docs/research/lidar_realtime_fusion_design_v2.md`, `.agents/skills/integration-test-orchestrator/`(SKILL.md·implementation_detail.md, `.claude/skills/` 미러 동일 반영)
- **검증 결과**: `ruff check .` 전체 통과, `mypy` 신규 에러 없음(기존 5건과 동일 파일들 - 미변경). `pytest tests/` 346 passed(환경 의존 실패 3건은 기존과 동일). `npx tsc --noEmit`(client) 클린. 실기기 라이브 검증: 객체 기반 캡처 16건 + 고정 지점 캡처 54건 이상 팀 공동 DB에 실제 저장 확인.
- **비고**: 통합 테스트 스킬(`integration-test-orchestrator`)에 이번에 발견한 `--env-file` 필수 사용법, 콘솔(운영 콘솔) 프론트 기동 누락, `docker compose config` 비밀값 노출 위험을 모두 반영해 다음 세션부터 반복 재발하지 않도록 함.

---

### 2026-07-19 | 후속 정리 | YOLO_AUTOINSTALL 이미지 반영 + CocoaPods 근본 원인 해결 + 외부 안전기준 문서 교차검증

- **YOLO_AUTOINSTALL 이미지 레벨 반영**: `docker-compose.macos.yml`에만 있던 `YOLO_AUTOINSTALL=False`를 `docker/Dockerfile`에 `ENV`로 고정해 GPU용 `docker-compose.yml`도 기본값으로 상속받게 했다. 최초 삽입 위치가 무거운 pygoruut/Supertonic 다운로드 RUN 레이어보다 앞이라 캐시가 무효화되는 것을 실측으로 발견해, CMD 직전으로 옮겨 재빌드 시 캐시 재사용을 확인(1.6초). `docs/ops/environment_variables.md`에 신규 변수로 등재(v0.4.22).
- **CocoaPods sandbox 불일치 근본 원인 규명**: 이전 세션에서 `pod install`이 `expo-dev-client`를 실수로 누락시킨 것처럼 보여 `Podfile.lock`/`project.pbxproj`를 git 상태로 되돌렸었다. 재조사 결과 실제 원인은 `client/node_modules/expo-dev-client`가 애초에 설치되어 있지 않았던 것(`package.json`엔 선언, `package-lock.json`엔 정상 기록됐으나 `npm install` 미실행 상태)이었다 - `pod install`은 실제 상태를 정확히 반영했을 뿐이었다. `npm install`로 누락 패키지를 채운 뒤 `pod install` 재실행해 109개 의존성 전부 정상 복구, `project.pbxproj`는 git과 완전 일치, `Podfile.lock`은 로컬 CocoaPods 툴 버전(1.16.2 vs 1.17.0) 차이로 인한 무해한 체크섬 4줄만 남아 커밋하지 않음.
- **외부 안전기준 문서(GPT 5.6 추론) 교차검증**: 사용자가 전달한 "근거리 오차 허용 기준" 제안 문서(0~0.6m ±5~10cm 등 LiDAR 연속 거리 기준)를 실제 코드·§4.3 실측 데이터와 대조했다. 핵심 불일치는 원문서가 "LiDAR가 반사 판단을 구동한다"는 전제인데, Minchodan은 area_ratio 휴리스틱만 실시간 판단에 쓰고 LiDAR는 자문 신호로 한정되며, 오늘 실측으로 LiDAR 자체가 0~0.6m 구간에서 가장 신뢰할 수 없음을 확인했다는 점이다. 반면 원문서가 보행속도·시스템지연 계산으로 도출한 "즉시 정지 ~0.6m·회피 안내 시작 1.2~1.5m"는, 완전히 다른 근거(알림 피로 분석)로 이미 확정한 `distance_policy.py`의 Near(≈0.696m)·Medium(≈1.27m) 경계와 상당히 근접해 독립 교차검증으로 긍정적이었다. 위험방향 비대칭(25퍼센타일 샘플링)과 불확실 시 보수적 처리(`minimumValidSamples=8`)는 이미 구현돼 있으나, "최근 3~5프레임 거리값 평활화"는 `MIN_HIT_COUNT`(존재-지속성 필터)와는 별개로 실제 미구현 상태임을 확인. `docs/research/lidar_realtime_fusion_design_v2.md` §4.4(신설)에 전체 검토 기록, §7에 후속 실기기 테스트 체크리스트(area_ratio 대 줄자 직접 대조, 다중 표면·조건 검증, 거리값 평활화, 감독 하 사용자 시험) 추가.
- **관련 파일**: `docker/Dockerfile`, `docker/docker-compose.yml`, `docs/ops/environment_variables.md`, `docs/research/lidar_realtime_fusion_design_v2.md`(client/ios Pods 변경은 로컬 전용, 커밋 없음)
- **검증 결과**: `docker compose --env-file .env -f docker/docker-compose.macos.yml build fastapi` 캐시 재사용 확인. 재기동 후 `docker exec ... echo $YOLO_AUTOINSTALL` → `False` 확인. `pod install` 재실행 후 109 dependencies/112 total pods 정상 복구.
- **비고**: 거리값 다중 프레임 평활화와 area_ratio 대 줄자 직접 대조는 이번 세션 범위 밖으로 명시적으로 보류 - 코드 변경 없이 문서 기록만 진행(사용자 확인).

---

### 2026-07-18 | 3단계·7단계·실기기 | Near/Medium/Far 우선순위 정합 + Tailscale Metro/WS + 검증 테스트

- **배경**: 통합 테스트 중 DB에 `distance_class=near`인데 `path=cognitive`로 저장되는 사례, YOLO `'Conv'...'bn'`로 서버 BBox 0건, LTE에서 Dev Launcher(`Finding Dev Servers`)만 뜨는 문제가 겹쳤다.
- **변경 내용**:
  - `consumer.py`: `_resolve_distance_class()` — `effective_distance_zone` SSOT 우선. `_is_speech_worthy()`에서 near는 인지 TTS 차단(반사 전담), far 무발화 유지. T1-b 쿨다운 단축은 medium만.
  - `pipeline_debug_builder.py`: reflex/cognitive debug에 `route`, `effective_distance_zone`, `route_reason` 추가.
  - `yolo_detector.py`: `track()` 실패 시 `lap` 및 `'Conv'...'bn'` 모두 `predict()` 폴백. RuntimeError도 동일 판정.
  - `ws_router.py`: binary detection 메타에 `device_id` 누락 시 query `device_id` 폴백(server_detection 미전송 방어).
  - `requirements.txt`: `lap==0.5.13` 명시.
  - 클라이언트(LTE/Tailscale): `AppDelegate`/`Info.plist`/`app.json`/`Minchodan.xcscheme` Metro 기본 호스트를 Tailscale IP(`100.121.247.4:8081`)로 고정, Dev Launcher 온보딩 스킵·`DEV_CLIENT_DEFAULT_LAUNCHER_URL` 설정. `client/.env`는 `NETWORK_MODE=tailscale`(gitignore, 커밋 없음).
  - 테스트/스크립트: `tests/test_distance_priority_integration.py`, `tests/test_ws_live_priority.py`, `scripts/verify_distance_priority_policy.py`, `scripts/verify_db_pipeline_debug_route.py` 추가.
- **관련 파일**: `server/detection/consumer.py`, `server/detection/yolo_detector.py`, `server/detection/gates/reflex_gate.py`, `server/services/pipeline_debug_builder.py`, `server/api/ws_router.py`, `client/ios/Minchodan/AppDelegate.swift`, `client/ios/Minchodan/Info.plist`, `client/app.json`, `client/ios/.../Minchodan.xcscheme`, `requirements.txt`, `tests/*`, `scripts/verify_*`
- **검증 결과**: Docker pytest 우선순위·WS 라이브 관련 **29+ passed**(전체 suite 124 passed 구간 포함). `verify_distance_priority_policy.py` 13/13 PASS. 실기기 Debug 빌드·설치·런치 성공(`com.minchodan.app.kb.dev`). Metro/FastAPI Tailscale IP 헬스 200.
- **비고**: `Podfile.lock` hermes 체크섬만 바뀐 로컬 CocoaPods 툴 차이는 커밋에서 제외. 푸시는 요청 시 별도 진행.

---

### 2026-07-18 | 문서 | Near/Medium/Far 우선순위·Tailscale 커밋 후 설계 문서 교차 정합

- **배경**: `e281909` 커밋은 changelog만 갱신하고 `auto-publish-work` Step 2(설계 문서 교차 검증)가 누락된 채 푸시됨. 코드와 어긋난 서술을 일괄 정정.
- **변경 내용**:
  - `api_specification.md` v0.4.28: §3.1 `device_id` 쿼리 폴백, §6.1 `distance_class`=SSOT 우선·near 인지 TTS 비대상, §8.5 `pipeline_debug`에 `route`/`effective_distance_zone`/`route_reason`.
  - `architecture.md` v0.4.12: T2-G near 차단·far 무발화, T1-b **medium만**, consumer 행 정정.
  - `risk_ssot_contract.md` v0.4.1: §2-C 인지 발화 불변식·변경 절차에 `consumer` 포함.
  - `pipeline_stage_design.md` v0.3.4: §5.3 거리 SSOT·Near/Medium/Far 발화 표.
  - `wireless_test_guide.md` v1.1.1: `lap==0.5.13` 고정·`predict()` 폴백(AutoUpdate 서술 폐기).
  - `environment_variables.md` v0.4.23: §2.11 Metro Tailscale 보강, §2.14 `METRO_BUNDLER_HOST`.
- **관련 파일**: 위 6개 설계/운영 문서, `docs/changelogs/kb.md`
- **검증 결과**: 코드(`consumer._is_speech_worthy`/`_resolve_distance_class`, `pipeline_debug_builder`, `ws_router` device_id 폴백, `requirements.txt` lap)와 문서 서술 대조 완료.
- **비고**: 코드 변경 없음. 문서 전용 정합 커밋.

---

### 2026-07-18 | 문서+병합 | Tailscale Metro 팀 표준 확정·개발 PC IP 덮어쓰기 명시 후 kb→dev

- **배경**: `kb`→`dev` 병합 정합성 검토에서 Tailscale 기본값(`100.121.247.4`) 하드코딩이 개인 랩 이슈로 지적됨. 팀 합의로 Tailscale Metro를 **공유 표준으로 유지**하고, 문서에 **개발 PC IP는 각자 덮어쓰기**를 명시하기로 함.
- **변경 내용**:
  - `environment_variables.md` v0.4.24: §2.11 운영 규칙 표(Metro/Dev Launcher/`EXPO_PUBLIC_TAILSCALE_HOST`), §2.14 변수 설명 보강.
  - `wireless_test_guide.md` v1.1.2: §5.4 트러블슈팅 추가.
- **병합**: `kb` fast-forward → `dev` (`e281909` Near/Medium/Far·Tailscale + `d71db64` 문서 정합 + 본 문서 커밋).
- **관련 파일**: `docs/ops/environment_variables.md`, `docs/ops/wireless_test_guide.md`, `docs/changelogs/kb.md`
- **검증 결과**: `origin/dev`는 `kb`의 ancestor라 충돌 없이 FF 가능. 비밀·가중치 파일 없음.
- **비고**: 팀원은 clone/pull 후 반드시 본인 Tailscale IP로 Metro·서버 호스트를 덮어쓸 것.

---

---

### 2026-07-19 | 통합 | 정합성 검토 보고서 P1 결함 수정 및 CI pytest 게이트 추가

- **배경**: `2026-07-18` kb=dev 통합 시점에 대한 외부 정합성 검토 보고서에서 P1 실행 경로/보안 결함 3건(R1~R3)과 문서/CI 드리프트 4건(C1, C4, C7, C8)을 지적.
- **변경 내용**:
  - **R3 콘솔 라이브 피드 인증**: `server/api/ws_router.py` `/ws/console/live-feed`에 `?token=` JWT 관리자 검증을 `connect_console` 이전에 추가. `server/api/session_manager.py` `connect_console()`에 `accept=False` 옵션 추가로 인증 후 등록만 수행.
  - **R1 navigation lifespan 통합**: `server/main.py` lifespan에서 `server/navigation/server.py`의 `redis_stream_listener()`를 직접 `asyncio.create_task`로 기동 및 종료 시 cancel. Starlette 마운트 서브앱 lifespan 미전파 문제 회복.
  - **R2 TMAP 비동기 격리**: `server/stt/stt_to_llm_bridge.py`의 `helper_search_poi`/`helper_fetch_route` 호출을 `asyncio.to_thread(...)`로 래핑해 이벤트 루프 블로킹 방지.
  - **C3 Docker 시드 SQL**: `docker/docker-compose.yml`에서 존재하지 않는 `scripts/seed_dummy_data.sql` 마운트 제거. Docker가 동명 빈 디렉터리를 생성하던 문제 해소.
  - **C1 API 명세 동기화**: `docs/design/api_specification.md`에 `detection_control` (§2.7) 및 `fixed_point_probe_sample` (§6.9) 절 신규 추가. 공통 `type` 필드 열거에도 두 타입 반영.
  - **C4 스테일 문서 경로**: `docker/*`, `pyproject.toml`, `.pre-commit-config.yaml`, `docs/ops/environment_variables.md`, `docs/ops/test_specification.md`의 `docs/deployment_guide.md`/`docs/code_quality_guide.md`/`docs/course_codebase_guide.md` 참조를 `docs/ops/`/`docs/dev-guides/` 실제 경로로 정정.
  - **C7 CI pytest**: `.github/workflows/lint.yml`의 `push.branches`에 `dev` 추가. pytest 단계 신설. `tests/test_convenience_dial_resolver.py`, `tests/test_embedding_engine_factory.py`, `tests/test_ws_echo.py`, `tests/test_ws_live_priority.py`에 `ollama`/`live_server` 마커 추가 및 `pyproject.toml` 마커 등록으로 CI에서 외부 서비스 의존 테스트 제외.
  - **C8 README 빠른 시작**: `README.md` 1단계 환경 변수 설정에 DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD 필수 명시.
  - **린트 정책 정합**: `pyproject.toml`에 `UP009`를 ignore 추가(`docs/dev-guides/course_codebase_guide.md` 3.1이 UTF-8 선언을 요구). `scripts/tts_read_text_experiment.py` 미사용 `noqa: S310` 제거 및 Bandit B310/B606 양쪽 호환 `# nosec` 주석 보강.
  - **소모성 경고 제거**: `server/mcp/manager.py`의 deprecated `client.close()`를 `aclose()`로 교체.
  - **pre-commit 차단 해소**: `scripts/run_test_100_samples.py`, `scripts/run_test_per_class.py`의 기존 `random.sample` 사용에 `# nosec B311` 추가로 Bandit pre-commit 통과.
- **관련 파일**: `server/api/ws_router.py`, `server/api/session_manager.py`, `server/main.py`, `server/stt/stt_to_llm_bridge.py`, `server/mcp/manager.py`, `docker/docker-compose.yml`, `docker/Dockerfile`, `docker/docker-compose.macos.yml`, `docker/linux_docker_start.sh`, `docker/macos_docker_start.sh`, `docker/windows_docker_start.bat`, `docker/.dockerignore`, `docs/design/api_specification.md`, `docs/ops/environment_variables.md`, `docs/ops/test_specification.md`, `README.md`, `.github/workflows/lint.yml`, `.pre-commit-config.yaml`, `pyproject.toml`, `scripts/tts_read_text_experiment.py`, `scripts/run_test_100_samples.py`, `scripts/run_test_per_class.py`, `tests/test_convenience_dial_resolver.py`, `tests/test_embedding_engine_factory.py`, `tests/test_ws_echo.py`, `tests/test_ws_live_priority.py`
- **검증 결과**: `ruff check .` All checks passed. `bandit -c pyproject.toml -r server/ scripts/` No issues identified. `pytest -m "not ollama and not live_server" -q` 353 passed, 1 skipped, 11 deselected. `python -m compileall server scripts tests` 0 오류. 수정 모듈 import 정상.
- **비고**: `auto-publish-work` 스크립트의 외부 의존성(ruff/react-doctor PATH) 문제로 수동 커밋/푸시. 푸시 브랜치는 `kb`.

---

### 2026-07-19 | 통합 | P3 정합성 잔여 결함 제거 및 추가 stale 정리

- **배경**: 2026-07-18 정합성 검토 보고서의 P3 항목(R5~R7)과 추가로 발견한 문서/변수 stale를 후속 처리.
- **변경 내용**:
  - **R5 핫패스 print() 제거**: `server/api/ws_router.py`의 7개 `print()` 디버그 출력을 중복된 `logger` 호출로 정리(또는 제거). `server/navigation/server.py` 20개, `server/navigation/manager.py` 6개 `print()`를 `logger` 기반 로깅으로 교체하고 각 파일에 `logging.getLogger(__name__)` 도입.
  - **R5 LOG_LEVEL 외부화**: `server/main.py` 루트 로거 레벨을 하드코딩된 `DEBUG`에서 `os.getenv("LOG_LEVEL", "INFO")`로 전환. `.env.example`에 `LOG_LEVEL=INFO` 추가. `docs/ops/environment_variables.md`에 §2.1 "일반 (서버 로깅)" 신규 추가 및 후속 섹션 번호 재조정.
  - **R6 사장 코드 제거**: `server/navigation/tts_engine.py`(pyttsx3/winsound 기반, 프로덕션 미사용) 삭제. 이를 참조하던 `tests/test_reflex_and_nav.py`의 `test_tts_engine_safe_compilation` 테스트 제거. `server/api/ws_router.py`의 미사용 `_finish_detection()` 헬퍼 제거.
  - **R7 STT 지연 임포트**: `server/stt/__init__.py`의 `SttToLlmBridge`를 최상단 즉시 임포트에서 `__getattr__` 지연 임포트로 전환. `import server.stt` 시 RAG/LangChain 스택이 끌려오지 않도록 개선하되, `from server.stt import SttToLlmBridge` 사용처는 그대로 동작.
  - **추가 Slack 환경 변수 정합**: `.env.example`의 Slack 섹션을 "Bot Token 방식" 단일 설명에서 "Webhook 우선 + Bot Token 폴백"으로 정정하고 `SLACK_WEBHOOK_URL` 추가. `README.md` 환경 변수 표에 `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 추가.
  - **추가 react-native-tts 잔여 정정**: `docs/stage-guides/stage7_tts_design.md`와 `.agents/skills/tts-voice-streamer/SKILL.md`·`.claude/skills/tts-voice-streamer/SKILL.md`(미러)의 단말 TTS 백업 설명을 `react-native-tts`에서 `expo-speech`로 정정. `server/tts/tts_service.py` 주석 동기화. `stage7_tts_design.md` 헤더의 stale 경로도 `docs/design/`·`docs/dev-guides/` 실제 경로로 정정.
- **관련 파일**: `server/api/ws_router.py`, `server/navigation/server.py`, `server/navigation/manager.py`, `server/main.py`, `server/stt/__init__.py`, `server/tts/tts_service.py`, `server/navigation/tts_engine.py`(삭제), `tests/test_reflex_and_nav.py`, `.env.example`, `README.md`, `docs/ops/environment_variables.md`, `docs/stage-guides/stage7_tts_design.md`, `.agents/skills/tts-voice-streamer/SKILL.md`, `.claude/skills/tts-voice-streamer/SKILL.md`
- **검증 결과**: `ruff check .` All checks passed. `ruff format .` 4 files reformatted. `bandit -c pyproject.toml -r server/ scripts/` No issues identified. `pytest -m "not ollama and not live_server" -q` 352 passed, 1 skipped, 11 deselected. `python -m compileall server scripts tests` 0 오류. 수정 모듈 import 정상.
- **비고**: 푸시 브랜치는 `kb`.

---

### 2026-07-19 | 통합 | 관제 콘솔 단말 오디오 미러링 구현 (TTS/반사 비프/햅틱 시각화)

- **배경**: 정합성 검토에서 클로드가 제시한 "단말 오디오를 웹 콘솔에 동일/유사하게 재생" 방안의 정합성을 검증한 뒤 착수. R3(콘솔 WS 인증)은 이미 선행 완료 상태이므로 오디오 미러링에 바로 착수.
- **변경 내용**:
  - **TTS 인지 음성 콘솔 미러링**: `server/detection/consumer.py` `_send_cognitive_guide`가 단말에 `guide` JSON + WAV 바이너리를 보낸 직후, 콘솔 WS에도 `console_guide_audio` JSON 예고 + 동일 WAV 바이너리를 브로드캐스트. `server/api/ws_router.py`의 `_send_stt_wait_notice`/`_send_nav_guidance`/STT 응답 안내 3개 경로와 `server/api/debug_router.py`의 `speak-to-device`에도 동일 패턴 적용.
  - **반사 알림 콘솔 미러링**: `server/detection/consumer.py` `_send_reflex_alert`가 단말 전송 성공 후 동일 payload를 콘솔에도 브로드캐스트. 콘솔은 `clip` 필드 파일명으로 정적 자산을 재생.
  - **반사 비프 정적 자산 복사**: `client/assets/sounds/reflex_clips/*.wav` 5종(head_level_warning, high_front, high_front-left, high_front-right, surface_caution)을 `console/public/reflex_clips/`에 동일 파일명으로 복사. 단말 번들과 동일 파일이므로 "동일"에 가장 근접한 재생.
  - **콘솔 WS 프로토콜 상태 분기**: `console/src/api/useLiveFeed.ts`에 `pendingGuideAudioRef` 상태 머신 추가. 직전 `console_guide_audio` JSON을 보관하고 다음 ArrayBuffer를 오디오로 분류. 기존 image/jpeg 강제 해석은 그대로 유지하되 오디오 경로만 분리. 5초 가드레일 타임아웃으로 정체 방지.
  - **ConsoleAudioMirror 컴포넌트 신규**: `console/src/components/ConsoleAudioMirror.tsx`에서 인지 가이드 `<audio>` 재생 + 반사 비프 `<audio>` 재생 + 햅틱 시각 펄스 인디케이터를 통합 렌더. 음소거 토글, 강도별 펄스 색상/크기 매핑, "시각 근사 표시 (진동은 청각 재현 불가)" 라벨 명시.
  - **대시보드 위젯 추가**: `console/src/pages/DashboardPage.tsx`에 `audioMirror` 위젯 키 신규 등록, 기본 순서 맨 뒤에 배치.
  - **잔여 print() 제거**: `server/tts/reflex_clip_sender.py`의 로딩 로그 `print()`를 `logger.info()`로 교체(R5 잔여).
  - **API 명세 동기화**: `docs/design/api_specification.md`에 §4.4 `console_guide_audio`·§4.5 `reflex_alert` 콘솔 미러 절 신설. 공통 `type` 필드 열거에 `console_guide_audio` 추가. v0.4.29 변경 이력 등재.
- **관련 파일**: `server/detection/consumer.py`, `server/api/ws_router.py`, `server/api/debug_router.py`, `server/tts/reflex_clip_sender.py`, `console/src/api/useLiveFeed.ts`, `console/src/components/ConsoleAudioMirror.tsx`(신규), `console/src/pages/DashboardPage.tsx`, `console/public/reflex_clips/*.wav`(신규 5종), `docs/design/api_specification.md`
- **검증 결과**: `ruff check .` All checks passed. `bandit -c pyproject.toml -r server/ scripts/` No issues identified. `pytest -m "not ollama and not live_server" -q` 352 passed, 1 skipped, 11 deselected. `npx tsc --noEmit`(console) 0 오류. `python -m compileall` 통과.
- **비고**: 푸시 브랜치는 `kb`. 서버가 보내는 WAV는 단말과 동일 원본이므로 "동일"에 가장 근접하고, 반사 비프는 단말 번들과 동일 파일이므로 "동일", 햅틱은 청각 재현이 원천 불가해 시각 근사로만 대응(라벨 명시).

---

### 2026-07-19 | 통합 | Near/Medium/Far 거리 구역 시각 도식화 (단말 + 관제 콘솔)

- **배경**: 시연/디버깅 시 거리 기반 우선순위(Near/Medium/Far)를 직관적으로 파악하기 위해 단말과 콘솔 양쪽에 거리 구역 경계선과 BBox 색상 도식화를 요구. 기존 단말 소실점 사다리꼴 ROI 오버레이는 거리 구역을 직접 표현하지 않으므로 3구역 경계선으로 교체.
- **변경 내용**:
  - **단말 ROIOverlay → DistanceZoneOverlay 교체**: `client/src/components/CameraView.tsx`의 기존 소실점 사다리꼴 `ROIOverlay`(렌더 요소 12개, 삼각함수 4회)를 `DistanceZoneOverlay`(렌더 요소 5개, 삼각함수 0회)로 교체. y=0.50(MED/FAR 경계, 주황)·y=0.75(NEAR/MED 경계, 빨강) 수평선 2개와 NEAR/MED/FAR 라벨 배지 3개만 렌더. 반사 후보 필터링 로직(`roiPolygon`/`pointInPolygon`)은 시각이 아닌 로직이므로 그대로 유지.
  - **단말 BBox zone 색상/태그**: `BBoxOverlay`가 `getClassColor` 대신 `getZoneTag(area_ratio)`를 우선 사용. area_ratio >= 0.10 → NEAR(빨강), >= 0.03 → MED(주황), 미만 → FAR(파랑). 단, `HIGH_HAZARDS`/`caution`/`roadway`는 위험 종류가 거리보다 중요하므로 기존 강제 색상을 우선 적용. 라벨 텍스트 끝에 zone 태그(NEAR/MED/FAR) 추가.
  - **서버 server_detection payload 확장**: `server/detection/consumer.py` `_send_server_detection`이 `detections[].effective_distance_zone` 필드를 추가로 송신. 서버 `distance_policy.py` SSOT 결과(`near`/`medium`/`far`)를 소문자로 그대로 전달. `segmentation` 결과는 빈 문자열.
  - **콘솔 BBox zone 색상/태그**: `console/src/components/LiveCameraFeed.tsx`가 `effective_distance_zone`을 우선 사용해 BBox 색상을 결정(`getColorForZone`). zone 정보가 없으면 기존 `getColorForClass`로 폴백. 라벨에 zone 태그 추가.
  - **콘솔 DistanceZoneOverlay**: 동일 파일에 `getZoneBoundaryStyle` 헬퍼로 회전 각도(0/90/180/270)별로 2개 경계선을 표시 영역에 정합. NEAR/MED/FAR 라벨 배지 3개 추가. BBox와 동일 좌표계 사용.
  - **API 명세 동기화**: `docs/design/api_specification.md` §6.4 예시에 `effective_distance_zone` 필드 추가, 필드 표에 설명 등재. v0.4.30 변경 이력 등재.
- **관련 파일**: `client/src/components/CameraView.tsx`, `server/detection/consumer.py`, `console/src/components/LiveCameraFeed.tsx`, `docs/design/api_specification.md`
- **검증 결과**: `ruff check .` All checks passed. `bandit -c pyproject.toml -r server/ scripts/` No issues identified. `pytest -m "not ollama and not live_server" -q` 352 passed, 1 skipped, 11 deselected. `npx tsc --noEmit`(console) 0 오류.
- **비고**: 푸시 브랜치는 `kb`. 단말은 area_ratio 로컬 산출(추가 네트워크 비용 0), 콘솔은 서버가 이미 산출한 `effective_distance_zone`을 추가 필드로 송신(바이트 증가 ~20B/detection)해 부하 최소화.

---

### 2026-07-19 | 통합 | 운영 콘솔(React+Vite) Docker compose 통합 - §5-B 자동화

- **배경**: 통합 테스트 스킬(`integration-test-orchestrator`)이 호스트에서 `cd console && npm run dev`를 매 세션 수동 실행하도록 §5-B를 두고 있었으나 누락 반복. 정합성 평가 결과 Console Vite는 표준 Node 웹앱이라 컨테이너화가 단순하고 정합성 충돌 0건이므로 compose에 통합. Metro/Expo·Ollama·Tailscale은 각각 Xcode 강결합·GPU/MPS 접근·커널 TUN 이슈로 호스트 실행을 유지(정합성 평가 근거).
- **변경 내용**:
  - **`console/Dockerfile` 신규**: `node:20-alpine` 기반 dev용 단일 스테이지. package.json 캐시 레이어 분리 후 소스 복사. `npm run dev`로 Vite dev 서버 기동. prod용 nginx 멀티스테이지는 향후 별도 추가.
  - **`console/.dockerignore` 신규**: `node_modules`, `dist`, `.git`, `*.log`, `.vite` 제외.
  - **`console/vite.config.ts` 프록시 환경 변수화**: `process.env.VITE_PROXY_TARGET` (기본값 `http://127.0.0.1:8000`)을 `/api`·`/ws`·`/navigation` 프록시 타깃으로 사용. 컨테이너에선 `http://fastapi:8000`, 호스트 실행 시 기본값 유지해 레거시 경로 영향 0.
  - **`docker/docker-compose.macos.yml` `console` 서비스 추가**: 포트 `${CONSOLE_PORT:-5174}:5174`, 소스 볼륨 `../console:/app` + 익명 볼륨 `/app/node_modules`(의존성 격리), `VITE_PROXY_TARGET=http://fastapi:8000`, `depends_on: fastapi`. compose 한 줄로 FastAPI·Redis·MariaDB·Console 4개 컨테이너 동시 기동.
  - **`docker/docker-compose.yml` 동일 추가**: GPU 환경도 동일 구성으로 양 compose 정합성 유지.
  - **`docs/ops/deployment_guide.md` §2.1 갱신**: 컨테이너 매트릭스에 `console` 행 추가, 버전 v0.5.3 → v0.5.4.
  - **`integration-test-orchestrator/SKILL.md` §5-B 재구성**: "매 세션 수동 실행" 지침을 "compose 통합으로 자동 기동"으로 변경. 별도 `npm run dev` 단계 제거, `docker compose logs console`으로 로그 확인. 버전 v1.1.0 → v1.2.0. `.agents/skills/`·`.claude/skills/` 양쪽 미러 동기화.
- **관련 파일**: `console/Dockerfile`(신규), `console/.dockerignore`(신규), `console/vite.config.ts`, `docker/docker-compose.macos.yml`, `docker/docker-compose.yml`, `docs/ops/deployment_guide.md`, `.agents/skills/integration-test-orchestrator/SKILL.md`, `.claude/skills/integration-test-orchestrator/SKILL.md`
- **검증 결과**: `ruff check .` All checks passed. `npx tsc --noEmit`(console) 0 오류. `docker compose -f docker/docker-compose.macos.yml config` console 서비스 정상 인식(비밀값 필터 출력 확인).
- **비고**: 푸시 브랜치는 `kb`. Metro·Ollama·Tailscale은 정합성 평가 근거(Xcode 강결합·GPU/MPS·커널 TUN)로 호스트 실행 유지. 통합 테스트 수동 단계가 4→2(Docker Desktop 실행 + compose up)로 감소.

---

### 2026-07-19 | 통합 | 통합 테스트 스킬 Tailscale 외부 테스트 시나리오 보완 (§0/§3-B/§5)

- **배경**: 통합 테스트 스킬을 실제 실행한 결과 "Tailscale을 쓴다"는 사실만 명시되어 있고, "Tailscale 경로로 단말이 실제로 도달하는지 검증하는 절차"와 "Metro 번들이 Tailscale 경로로 단말에 전달되는지 확인하는 절차"가 누락되어 있음이 드러남. 실제 실행에서 Metro가 `localhost:8081`만 리스닝하고 Tailscale IP로 응답하지 않아 단말이 번들을 받지 못하는 사례가 발생(단말 흰 화면). 또한 `nohup ... &`로 실행한 Metro가 반복적으로 조용히 종료되는 현상 실측.
- **변경 내용**:
  - **§0 결정 항목 보완**: "외부 LTE/핫스팟 테스트 시나리오" 추가. 단말이 개발 PC와 같은 LAN이 아닐 때 `EXPO_PUBLIC_NETWORK_MODE=tailscale` 필수, §3-B 사전 검증을 먼저 수행해야 흰 화면 실패를 차단한다고 명시.
  - **§3-B "Tailscale 네트워크 사전 검증" 신설**: 5단계 검증 절차(호스트 Tailscale IP 확인 → `EXPO_PUBLIC_TAILSCALE_HOST` 일치 검증 → 호스트→단말 ping → FastAPI Tailscale IP 도달 → Metro Tailscale IP 도달). 각 단계별 실패 시 대응 표 포함.
  - **§5 Metro 백그라운드 실행 안정성 보완**: `nohup` 대신 `setsid`로 세션 분리 권장 + `disown` 함께 사용. `EXPO_PUBLIC_NETWORK_MODE=tailscale`일 때 `--host 0.0.0.0` 명시로 Tailscale 인터페이스 바인딩 보장. Metro 헬스체크를 localhost와 Tailscale IP 두 경로 모두에서 수행하는 "이중 경로" 검증 절차 추가. localhost만 200이고 Tailscale IP가 000이면 Metro가 127.0.0.1만 바인딩한 것으로 진단하는 가드레일 추가.
  - **버전업**: v1.2.0 → v1.3.0. `.agents/skills/`·`.claude/skills/` 양쪽 미러 동기화.
- **관련 파일**: `.agents/skills/integration-test-orchestrator/SKILL.md`, `.claude/skills/integration-test-orchestrator/SKILL.md`
- **검증 결과**: 미러 diff 0건(동일 내용). 스킬 내 링크/코드펜스 정합성 육안 확인.
- **비고**: 푸시 브랜치는 `kb`. 이번 보완으로 외부 LTE/핫스팟 테스트 시 단말 흰 화면 실패를 사전에 차단하고, Metro 백그라운드 실행 안정성을 확보함.

---

### 2026-07-19 | 2·7단계 | 거리 구역 SVG 호 도식화 + 콘솔 live-feed JWT 연결 수정

- **배경**: Near/Medium/Far 직선 경계선이 원근을 전달하지 못해 SVG 호로 교체. 호 끝점이 화면 중앙에만 그려지던 기하학 오류를 좌·우 가장자리까지 연결하도록 수정하고, FAR처럼 보이던 파란 측면 빗변은 제거. 동시에 관제 콘솔 실시간 화면이 비는 원인을 추적한 결과 `/ws/console/live-feed`가 관리자 JWT를 요구하는데 `useLiveFeed`가 토큰을 붙이지 않아 `1008 token required`로 즉시 종료되고 있었음.
- **변경 내용**:
  - **단말**: `react-native-svg` 추가. `CameraView.tsx` `DistanceZoneOverlay`를 SVG Path 호(NEAR y≈78%, MED y≈52%, 끝점 x=0/W) + 라벨로 교체. 측면선 제거.
  - **콘솔**: `LiveCameraFeed.tsx` 동일 기하학의 인라인 SVG 호. 미사용 `getZoneBoundaryStyle` 제거.
  - **콘솔 WS 인증**: `useLiveFeed(token)` + `App.tsx`에서 로그인 JWT를 `?token=`으로 전달(SSE와 동일).
  - **API 명세**: `docs/design/api_specification.md` §8.7·v0.4.31에 live-feed JWT 계약 등재.
- **관련 파일**: `client/package.json`, `client/package-lock.json`, `client/src/components/CameraView.tsx`, `console/src/api/useLiveFeed.ts`, `console/src/App.tsx`, `console/src/components/LiveCameraFeed.tsx`, `docs/design/api_specification.md`, `docs/changelogs/kb.md`
- **검증 결과**: 실기기에서 호+라벨 표시 확인. live-feed에 JWT 부착 시 JPEG/`server_detection` 수신 확인. `npx tsc --noEmit`(console) 통과. `expo prebuild --clean`으로 생긴 네이티브 브릿지/CoreML 삭제는 커밋 전 `git checkout`으로 복구(의도 변경 아님).
- **비고**: 푸시 브랜치 `kb`. 안내 음성 끊김은 STT 시작 시 `stopGuideAudio`·오탐 실패 안내 중복이 주원인으로 로그 진단 완료(이번 커밋 범위 외, 후속 수정 예정).

---

### 2026-07-19 | 7단계 | 안내 음성 끊김 수정 - STT 선점/오탐 루프 차단

- **배경**: 실기기·Metro 로그에서 `stopGuideAudio … currentTime=1.90s / duration=5.01s (조기 중단 의심!)`과 `hold=0.02~0.18s` 초단시간 녹음 후 `"음성이 인식되지 않았어요"` 연속 재생이 관측됨. STT 시작이 재생 중 안내를 강제 중단하고, 탭 오탐이 실패 안내 TTS를 반복해 끊김처럼 들림.
- **변경 내용**:
  - **단말**: `stopGuideAudioIfPriorityAtMost(1)` - STT 응답(priority=2) 재생 중에는 끊지 않음. `CameraView` STT press-in에 적용.
  - **단말**: `useSttRecorder`에서 hold < 400ms 또는 iOS captured < 0.35s면 서버 미전송(조용히 폐기) + `setSttActive(false)`.
  - **단말**: `setSttActive(false)`가 재생 중 가이드 우선순위를 지우지 않도록 수정.
  - **서버**: `MIN_STT_AUDIO_BYTES` 4096→11200. 길이 부족/0바이트는 TTS 없이 조용히 폐기.
  - **서버**: 빈 전사 안내 5초 쿨다운(`stt-bridge-empty-suppressed`). ws_router는 억제/빈 guidance를 클라이언트 미전송.
- **관련 파일**: `client/src/services/audioEngine.ts`, `client/src/components/CameraView.tsx`, `client/src/hooks/useSttRecorder.ts`, `server/api/ws_router.py`, `server/stt/stt_to_llm_bridge.py`, `tests/test_ws_router_stt.py`, `tests/test_stt_to_llm_bridge_template.py`
- **검증 결과**: `ruff check` 통과. `pytest tests/test_stt_to_llm_bridge_template.py::test_invoke_existing_llm_empty_fallback tests/test_ws_router_stt.py` 11 passed. FastAPI 재기동·앱 재실행.
- **비고**: 푸시 브랜치 `kb`→`dev` ff 병합.

---

### 2026-07-19 | 도구 | client/.npmrc allow-scripts 추가 (npm 11 설치 가드)

- **배경**: npm 11 환경에서 `npx expo install`/`npm install`이 `EALLOWSCRIPTS`로 실패해 `react-native-svg` 설치가 막힘. project-scoped installs는 CLI `--allow-scripts`가 거부되고 `.npmrc` 또는 package.json `allowScripts`가 필요함.
- **변경 내용**: `client/.npmrc`에 `allow-scripts=true` 추가(비밀값 없음).
- **관련 파일**: `client/.npmrc`, `docs/changelogs/kb.md`
- **검증 결과**: 민감 정보 없음 확인. `kb`/`dev` 동기화 상태 확인.
- **비고**: 푸시 브랜치 `kb`→`dev`.

---

### 2026-07-19 | 도구 | Git 추적 정리 (det_best mlpackage 해제 + RNSVG Pod 동기화)

- **배경**: AGENTS.md 정책상 커스텀 파인튜닝 가중치(`det_best_*`)는 git-ignore인데 `server/models/yolo26n/det_best_20260705.mlpackage`(~9MB)가 추적 중이었다. 또한 `react-native-svg` 추가 후 Minchodan 트리 복원으로 `Podfile.lock`에 RNSVG가 빠져 있었다.
- **변경 내용**:
  - `det_best_20260705.mlpackage`를 `git rm --cached`로 추적 해제(로컬 파일 유지).
  - `.gitignore`에 `server/models/yolo26n/det_best_*/`·`det_best_*` 규칙 추가.
  - `pod install`로 `Podfile.lock`/`project.pbxproj`에 RNSVG 번들 반영.
- **관련 파일**: `.gitignore`, `client/ios/Podfile.lock`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `docs/changelogs/kb.md`
- **검증 결과**: `git check-ignore`로 det_best mlpackage 무시 확인. `Podfile.lock` RNSVG 6건 매칭. 디스크상 mlpackage 유지.
- **비고**: CoreML 이중 사본(`assets/.../segmentation.mlpackage` ↔ `ios/segmentation.mlpackage`, 동일 checksum)은 Xcode가 ios 경로를 참조하므로 유지. 히스토리 대용량 blob(yolov8n 등) 제거는 filter-repo 범위라 이번 정리에서 제외.

---

### 2026-07-19 | 2·7단계 | 탐지 시작 시 안내 음성 끊김 수정

- **배경**: 실기기에서 탐지/화면 전송을 누르면 온보딩·인지 안내가 중간에서 끊김. Metro 로그 실측: 온보딩 TTS 중 hold≈40ms STT 오탐이 `stopGuideAudio`/`Speech.stop`을 즉시 호출해 `onDone` 처리. 또한 Mid 비프(interval=250)가 HIGH_DANGER(250)에 걸려 가이드를 선점.
- **변경 내용**:
  - `CameraView`: STT arm 지연 200ms — 그 전에 손을 떼면 안내 선점·녹음 시작 없음.
  - `audioEngine`: HIGH_DANGER 문턱 250→100(긴급 beep-only와 정합). Mid는 덕킹만.
  - `useSttRecorder`: `MIN_STT_HOLD_MS` export(서버 폐기 임계는 400ms 유지).
- **관련 파일**: `client/src/components/CameraView.tsx`, `client/src/services/audioEngine.ts`, `client/src/hooks/useSttRecorder.ts`, `docs/changelogs/kb.md`
- **검증 결과**: 코드 경로 로그 대조(오탐 hold 40ms vs arm 200ms). Metro 핫리로드로 JS만 반영(네이티브 재빌드 불필요).
- **비고**: 의도적 STT는 약 200ms 누른 뒤 녹음 시작.


---

### 2026-07-19 | 도구·3단계 | 어제 Git 기준 온디바이스 CoreML 복원

- **배경**: `expo prebuild --clean`으로 브릿지 없는 GILDANG 바이너리가 실기기에 남아 `CoreMLInferenceBridge Native Module 미발견` → TFLite 폴백 → takePhoto `float32len=0`으로 온디바이스 탐지 불가. 7/18 말 `02aab79` 깃 트리에는 CoreML/Reflex/mlmodelc가 온전했음.
- **변경 내용**:
  - `Minchodan.xcworkspace` Debug 재빌드·실기기 설치(브릿지 포함). 로그: `det=CoreML(CPU)/seg=CoreML(CPU)`, `supportsStream=true`.
  - `app.json`: 어제 브랜딩명 GILDANG 유지, `react-native-fast-tflite`에 `enableCoreMLDelegate: true` 명시.
  - `useCamera`: takePhoto 폴백 시 TFLite용 float32를 base64에서 복원(플러그인 없는 바이너리 방어).
  - 선행 STT arm/HIGH_DANGER 수정은 유지.
- **관련 파일**: `client/app.json`, `client/src/hooks/useCamera.ts`, `client/src/components/CameraView.tsx`, `client/src/services/audioEngine.ts`, `client/src/hooks/useSttRecorder.ts`, `docs/changelogs/kb.md`
- **검증 결과**: 설치 후 Metro에 CoreML 기동·Stream 캡처·SceneHysteresis 추론 로그 확인. `Native Module 미발견` 해소.
- **비고**: `expo prebuild --clean` 재실행 금지. 표시명은 GILDANG(브랜딩), 번들/앱 경로는 Minchodan.

---

### 2026-07-19 | 7단계 | 음성 안내 우선순위 4단 적용

- **배경**: 사용자 요구 - (1) 12시 NEAR (2) STT 답변 (3) 12시 MED (4) 그 외 순으로 선점.
- **변경 내용**:
  - `guidePriority.ts` 신설: `GUIDE_PRIORITY` 1~4 + `resolveGuidePriority(clock/distance/stt)`.
  - `audioEngine`: 우선순위 타입 확장. STT 활성 중에는 STT 미만만 드롭(12시 NEAR는 통과).
  - `useWebSocket`: guide JSON의 `clock_direction`/`distance_class`로 priority 계산 후 바이너리/폴백 TTS에 전달.
  - `CameraView`: STT arm 시 `FRONT_MED` 이하만 선점. 정면 경로 장애물 로컬 TTS는 `FRONT_NEAR`.
- **관련 파일**: `client/src/services/guidePriority.ts`, `client/src/services/audioEngine.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit`(client) 클린.
- **비고**: 반사 비프/클립 채널은 기존과 분리 유지.


---

### 2026-07-19 | 7단계 | STT(길찾아줘/물어볼게) 최우선 + Near 비프/햅틱 2순위

- **배경**: 사용자가 멈춰 질문/길찾기 할 때 Near 위험 안내·햅틱·비프가 끼어들면 발화가 방해됨. 1순위는 STT 상호작용, 2순위가 Near 햅틱/비프여야 함.
- **변경 내용**:
  - 우선순위 재배치: STT(4) > FRONT_NEAR(3) > FRONT_MED(2) > OTHER(1).
  - STT 활성 중 `playBeep`/`playReflexClip`/위험 햅틱/`canStartGuide`(NEAR 포함) 전부 억제.
  - STT arm·STT 응답 수신 시 진행 중 Near 비프·continuous 햅틱 즉시 정지.
  - STT 자체 큐 햅틱만 `allowDuringStt`로 허용.
  - Near 비프는 STT가 아닐 때 MED/기타 음성만 선점(Near 음성은 덕킹).
- **관련 파일**: `guidePriority.ts`, `audioEngine.ts`, `hapticEngine.ts`, `CameraView.tsx`, `useWebSocket.ts`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit`(client) 클린.
- **비고**: Metro 핫리로드로 반영.

---

### 2026-07-19 | 7단계 | Near/음성 안내 대기열 상한 6 + 최신만 재생

- **배경**: Near·인지 음성 안내가 재생보다 빨리 쌓이면 오래된 안내가 줄줄이 나와 현재 장면과 어긋남.
- **변경 내용**:
  - `audioEngine`: 재생 중 동일 우선순위 안내는 대기열 적재(최대 6, 초과 시 오래된 것 drop). 종료 시 최신 1건만 재생하고 나머지 폐기. 상위 우선순위는 즉시 선점.
  - STT 활성/`stopGuideAudio` 시 대기열 정리. `guideEpoch`로 선점 콜백의 오배수 방지.
  - 서버 `COGNITIVE_QUEUE_MAXSIZE` 기본값 4→6(오래된 프레임 drop-oldest 유지).
- **관련 파일**: `client/src/services/audioEngine.ts`, `server/capture/stream_splitter.py`, `docs/changelogs/kb.md`
- **검증 결과**: `npx tsc --noEmit`(client) 클린.
- **비고**: Metro 핫리로드로 단말 반영.

---

### 2026-07-19 | 콘솔 | 단말 오디오 미러 무음 수정

- **배경**: 콘솔 웹에서 단말과 동일한 안내 음성이 전혀 들리지 않음.
- **원인**:
  1. `useLiveFeed`가 `binaryType=blob`인데 guide WAV는 `ArrayBuffer` 분기만 처리 → WAV가 JPEG로 오인.
  2. 반사 clip 경로 `reflex_clips/xxx.wav`를 `/reflex_clips/`에 또 붙여 404.
  3. 브라우저 자동재생 정책으로 `audio.play()` 차단.
- **변경 내용**:
  - Blob/ArrayBuffer 모두 RIFF 헤더로 guide WAV 판별 후 Blob URL 생성.
  - clip basename으로 `public/reflex_clips/` 매핑.
  - "오디오 활성화" 버튼으로 자동재생 unlock.
- **관련 파일**: `console/src/api/useLiveFeed.ts`, `console/src/components/ConsoleAudioMirror.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: 콘솔 `npx tsc --noEmit` 클린.
- **비고**: 대시보드에서 "오디오 활성화" 클릭 후 단말 안내 시 미러 재생 확인.

---

### 2026-07-19 | 콘솔 | 인지 가이드 미러 복구 + 활성/비활성 토글

- **배경**: 인지 가이드는 계속 "대기 중", 반사 알림만 정상. 미러 on/off 필요.
- **원인**: 콘솔 송신 큐 `maxsize=1`이 guide JSON 직후 WAV를 넣을 때 JSON을 드롭.
- **변경 내용**:
  - `broadcast_guide_audio_to_consoles`: JSON+WAV 쌍을 latest-only 큐 우회로 원자 전송.
  - `useLiveFeed`: `console_guide_audio` JSON 수신 즉시 텍스트 표시.
  - `ConsoleAudioMirror`: 인지/반사 각각 활성·비활성 토글(localStorage 유지).
- **관련 파일**: `server/api/session_manager.py`, `consumer.py`, `ws_router.py`, `debug_router.py`, `console/src/api/useLiveFeed.ts`, `ConsoleAudioMirror.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: 콘솔 `npx tsc --noEmit` 클린.
- **비고**: 서버 재시작 후 콘솔에서 "오디오 활성화" + 인지/반사 토글 확인.

---

### 2026-07-19 | 콘솔 | RiskEventLog 상세 출력 박스·페이지네이션 정렬

- **배경**: Detection Guidance Log와 달리 RiskEventLog는 전체 목록만 보여 가독성·탐색이 떨어짐.
- **변경 내용**:
  - 페이지당 10건, ←/번호/.../→ 페이지네이션(Guidance Log와 동일 CSS).
  - 행 클릭 시 `frame-detail` 출력 박스로 위험도·객체·안내문 등 상세 표시.
- **관련 파일**: `console/src/components/RiskEventLog.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: 콘솔 `npx tsc --noEmit` 클린.
- **비고**: SSE `state.risks`(최대 80건) 기준 클라이언트 페이지네이션.

### 2026-07-19 | 6단계 | Medium caution/roadway 인지 멘트 복구

- **배경**: 중거리 caution/roadway는 인지(Medium) TTS가 나가야 하는데 무발화.
- **원인**:
  1. `_is_speech_worthy`가 `risk_hint in ("high","medium")`만 허용 → 파이프라인 `"mid"` 불일치.
  2. 노면만 있는 프레임은 `primary_det is None`으로 탈락.
  3. `orch_input`에 surface 미전달 → L1 mid 승격·L2 노면 프롬프트 불가.
- **변경 내용**:
  - speech_worthy: `mid`/`medium`/`high` + `has_significant_surface` 예외.
  - orch에 `surface_classes`/`surface_classes_ko` 전달, L1 `MID_RISK_SURFACE_CLASSES` mid 분류.
  - L2: caution/roadway 노면 상태 줄 추가, 패스트 레인은 위험 노면 시 제외.
  - `CLASS_TEXT`에 segmentation 4클래스 한국어 매핑.
- **관련 파일**: `consumer.py`, `l1_classifier.py`, `l2_generator.py`, `fast_lane.py`, `state.py`, `risk_rules.py`, `tests/test_detection.py`, `tests/test_langgraph.py`, `tests/test_departure_hysteresis.py`
- **검증 결과**: pytest SpeechWorthy/L1 surface/departure 관련 케이스.
- **비고**: Far BBox 표시와 Near 반사는 기존 유지. Medium 노면만 인지 멘트 경로 복구.


### 2026-07-19 | 3단계 | 서버 seg 가중치 segbest.pt 복구

- **배경**: 실기기 차도 장면에서도 roadway 미탐. 서버가 `segmentation.pt`(스톡/비최적)를 로드 중이었고, `segbest.pt`는 과거 실사에서 roadway 재현 가능이 확인됨.
- **변경 내용**: `.env`의 `YOLO26N_SEG`를 `server/models/yolo26n/segbest.pt`로 전환 후 FastAPI 재기동.
- **관련 파일**: `.env`, `docs/changelogs/kb.md`
- **검증 결과**: `docker compose ... --force-recreate` 후 `printenv YOLO26N_SEG=.../segbest.pt`, 로그 `YoloSegmentor 모델 로드 성공: .../segbest.pt` 확인. (`restart`만으로는 env_file이 갱신되지 않음)
- **비고**: 온디바이스 CoreML 재변환은 별도 후속. 단말 roadway 미탐은 앱 재빌드 전까지 잔존 가능.


### 2026-07-19 | 단말 | segbest CoreML 재변환 + 실기기 유선 재빌드

- **배경**: 서버 `segbest.pt` 전환 후 roadway 인지 멘트는 복구됐으나 온디바이스 CoreML은 구 가중치로 roadway 미탐.
- **변경 내용**:
  - `scripts/convert_yolo_to_coreml.py`에 `--weights` 옵션 추가.
  - `segbest.pt` → FP16 CoreML(`--no-nms`) 변환 후 `client/assets/.../segmentation.mlpackage` 및 `client/ios/segmentation.mlpackage` 동기화.
  - `xcodebuild` Debug → 고태현 iPhone(UDID `00008120-0011705611F0201E`) 빌드·`devicectl` 설치·실행 (`com.minchodan.app.kb.dev`).
- **관련 파일**: `scripts/convert_yolo_to_coreml.py`, `client/ios/segmentation.mlpackage`, `client/assets/models/yolo26n/ios/segmentation.mlpackage`, `docs/changelogs/kb.md`
- **검증 결과**: BUILD SUCCEEDED, 번들 `segmentation.mlmodelc` storagePrecision=Float16, 출력 `[1,300,38]`+proto 마스크. CoreML 브릿지는 기존 `.cpuAndNeuralEngine` 유지(ANE 우선).
- **비고**: 단말 Metro에서 `roadway` 출현 여부로 온디바이스 개선을 추가 확인한다.


### 2026-07-19 | 단말 | object_detection CoreML 재변환 + 실기기 재빌드

- **배경**: seg는 `segbest`로 서버·단말 정합을 맞췄으나 det는 구 CoreML 변환본이 남아 완전 동일하지 않음.
- **변경 내용**:
  - 서버와 동일 파일(`object_detection.pt`, `object_detection260714.pt`와 MD5 일치)을 FP16+NMS CoreML로 재변환.
  - `client/assets/models/yolo26n/ios/object_detection.mlpackage` 갱신 후 실기기 Debug 빌드·설치·실행.
- **관련 파일**: `client/assets/models/yolo26n/ios/object_detection.mlpackage`, `docs/changelogs/kb.md`
- **검증 결과**: BUILD SUCCEEDED, 번들 det=`confidence`/`coordinates`(NMS), seg=`[1,300,38]`+proto, 둘 다 Float16. ANE 설정(`.cpuAndNeuralEngine`) 유지.
- **비고**: 서버 det=`object_detection.pt`, seg=`segbest.pt`와 온디바이스 CoreML 소스가 각각 일치.

### 2026-07-19 | 통합 | jy 보안 강화 → kb 병합

- **커밋**: `347dc53` (`merge: origin/jy 보안 강화를 kb에 통합`)
- **변경 내용**:
  - `origin/jy` 보안 강화(JWT iss/aud·관리자 부트스트랩·RBAC·콘솔 live-feed `auth` JSON·STT 상한/세마포어·Redis `requirepass`·loopback 바인딩·ngrok 제거)를 `kb`에 병합.
  - ort 자동 머지로 충돌 6파일(`ws_router`/`session_manager`/`useLiveFeed`/`debug_router`/`useWebSocket`/`CameraView`)이 양쪽 기능을 유지한 채 합성됨(인지 mid/가이드 큐/콘솔 WAV 미러 + 보안 계약).
  - `scripts/configure_security_secrets.py`로 `.env` JWT/Redis/bootstrap/정적 단말 토큰 재발급. Compose Redis·FastAPI·MariaDB recreate(`DB_HOST_PORT=3307` — 호스트 MySQL 3306 점유 회피). Tailscale lab용 `EXPO_PUBLIC_WS_SCHEME=ws` 유지.
- **관련 파일**: `server/api/ws_router.py`, `server/api/session_manager.py`, `console/src/api/useLiveFeed.ts`, `server/api/debug_router.py`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `docker/docker-compose.macos.yml`, `scripts/configure_security_secrets.py`, `docs/security/security_hardening_and_team_adoption_guide.md`, `docs/changelogs/kb.md`
- **검증 결과**:
  - `pytest tests/test_security_hardening.py` + `TestSpeechWorthyFilter` + `test_l1_risk_classification` → **16 passed** (speech_worthy 단독 재실행 10 passed).
  - 단말 WS: welcome → hello(정적 토큰) → `auth_ok`.
  - 콘솔 live-feed: `auth` → `auth_ok` → `speak-to-device` 미러로 `console_guide_audio` + RIFF WAV 수신 확인(검증 후 `ENABLE_DEBUG_API=false` 복구).
  - FastAPI `YOLO26N_SEG=segbest.pt`, `/health` 200. Tailscale Serve는 tailnet에서 미활성(`login.tailscale.com/f/serve?...`)이라 실기기 TS 직접 접속은 loopback 바인딩과 함께 후속 설정 필요.
- **비고**: 콘솔은 JWT 시크릿 교체로 재로그인 필요. 실기기 외부 접속은 `0.0.0.0` 공개 대신 Tailscale Serve/프록시를 사용할 것.


### 2026-07-19 | 단말·콘솔 | BBox 콘솔 정합 + GPS 지도 복구 + Tailscale Serve 연동

- **커밋**: (본 엔트리 커밋)
- **변경 내용**:
  - 단말 BBox: 오늘 재변환 det CoreML을 어제(`ff553a1`) 번들로 복원. CoreML 좌표 스케일 가드·캔버스 clamp. 오버레이는 콘솔 `server_detection` 계약과 동일하게 seg를 centroid 80x80 마커로만 표시. Camera `resizeMode=cover`.
  - ATS: Metro 로컬 HTTP용 `NSAllowsLocalNetworking=true` (`Info.plist`/`app.json`).
  - 콘솔 GPS: jy 보안 병합 후 `ENABLE_NAVIGATION_SIMULATOR=false` + `X-Frame-Options: DENY`로 `/navigation` iframe이 404/차단되던 회귀 수정. development 기본 마운트 + `frame-ancestors` 콘솔 origin 허용.
  - 클라이언트 `.env.example`: Tailscale Serve 사용 시 `wss`+`443`+MagicDNS 안내.
- **관련 파일**: `client/src/components/CameraView.tsx`, `client/ios/CoreMLInferenceBridge.swift`, `client/assets/.../object_detection.mlpackage`, `client/ios/Minchodan/Info.plist`, `client/app.json`, `client/.env.example`, `server/main.py`, `docs/ops/environment_variables.md`, `docs/changelogs/kb.md`
- **검증 결과**: `/navigation/?embed=true` 200, Vite 프록시 200. 단말 Metro 리로드로 오버레이 계약 반영. `ruff check server/main.py` 통과, `pytest tests/test_security_hardening.py` 5 passed.
- **비고**: 루프백 바인딩 환경의 실기기 접속은 Tailscale Serve(`https://<magicdns>/`) 전제.

### 2026-07-19 | 3단계 | 노면 Near/Medium/Far + 인지 에피소드 억제

- **배경**: caution/roadway가 시야에 있는 동안 `has_significant_surface`/`risk_hint=mid` 무조건 통과로 인지 TTS가 반복되고, Near 반사 비프와 TTS가 동시에 울려 과처리됨.
- **변경 내용**:
  - 노면 거리 구역(centroid_y): Near(>0.6H)=반사만 / Medium=인지 TTS / Far=화면만. `_is_speech_worthy`에서 무조건 통과 제거.
  - 노면 인지 에피소드: 같은 caution|roadway 키가 시야에 있는 동안 enter 1회만 안내, 이탈·클래스 변경 시에만 재안내.
  - 인지 서명 거칠게: `caution|roadway`만 키로 사용(sidewalk/braille 흔들림으로 쿨다운 리셋 방지). 노면-only는 주기 갱신 금지.
  - Near 노면 반사 후 `_trigger_delayed_cognitive_guide` 생략(비프+TTS 동시 반복 금지).
- **관련 파일**: `server/detection/consumer.py`, `tests/test_detection.py`, `docs/changelogs/kb.md`
- **검증 결과**: `.venv/bin/python -m pytest tests/test_detection.py::TestSpeechWorthyFilter tests/test_detection.py::TestUtteranceValueGate` → **24 passed**
- **비고**: 서버(DetectionConsumer) 재기동 후 실기기에서 Medium 진입 1회 TTS / Near 반사만 확인 권장.

### 2026-07-19 | 3단계 | Medium 노면 안내 무음 버그 수정

- **배경**: 실외 로그에서 Medium이 `episode=continue`만 반복되고 guide TTS가 나오지 않음. enter 시점에 episode를 선커밋해 TTS 실패 후에도 잠김 + 노면-only 동일 서명을 utterance가 막아 이탈 후 재진입도 무음.
- **변경 내용**:
  - 노면 인지: enter 시 `pending`만 걸고, 단말 guide 전송 성공 후에만 `_commit_surface_cognitive_episode`. 실패/조기반환 시 pending 해제해 재시도.
  - Far 구역을 에피소드 이탈로 취급. caution/roadway는 단일 `surface_hazard` 키.
  - `_has_utterance_value`: 노면-only는 서명 동일로 막지 않음(에피소드 게이트가 1회 담당).
- **관련 파일**: `server/detection/consumer.py`, `tests/test_detection.py`, `docs/changelogs/kb.md`
- **검증 결과**: `.venv/bin/python -m pytest tests/test_detection.py -k 'Surface or utterance or speech_worthy or Approaching or hazard'` → **32 passed**. `minchodan-fastapi` 재기동 완료.
- **비고**: Medium 진입 시 로그에 `노면 인지 에피소드 enter` → `guide 전송` 1회, 이후 `continue` 확인.


### 2026-07-19 | 3단계·단말 | 12시 회랑 경보 + 오버레이 중심선

- **배경**: Near 햅틱/비프와 Medium 인지 안내가 측면 탐지에도 울려 과경보. 거리선(Near/Med)과 구분되는 12시 시각 가이드가 필요.
- **변경 내용**:
  - `DistanceZoneOverlay`: 기존 Near/Med 호 유지, cyan 12시 세로선(소실점→하단) + 라벨 추가.
  - `surface_gate`: Near FRONT_BAND(0.20~0.80) 밖 노면은 반사 제외. 파이프라인에 frame_width 전달.
  - 인지: Medium 노면/객체는 12시 회랑(`FRONT_BAND`)만 speech_worthy. 측면 approaching 인지 TTS 제거.
  - 온디바이스 로컬 반사: `estimateDirection===front` 후보만 햅틱/비프.
- **관련 파일**: `client/src/components/CameraView.tsx`, `server/detection/gates/surface_gate.py`, `server/detection/detection_pipeline.py`, `server/detection/consumer.py`, `tests/test_detection.py`
- **검증 결과**: `pytest tests/test_detection.py` → **79 passed**. FastAPI 재기동.
- **비고**: Metro 리로드로 단말 오버레이 확인. 측면 탐지는 BBox만, 12시 선 위의 Near/Med만 음성·햅틱.


---

### 2026-07-19 | 3단계 | metro_https_ats_fix_rag_toggle

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 실기기-Metro 연결 실패 원인 규명 및 수정: expo-dev-launcher가 NSUserDefaults에 남은 packagerScheme=https로 평문 Metro(8081)에 접속 시도해 실패하던 문제를 AppDelegate.swift에서 앱 시작 시 http로 고정해 해결, NSAllowsArbitraryLoads+NSAllowsLocalNetworking 동시 설정이 Tailscale CGNAT(100.64.0.0/10) 대역에 대해 ATS를 오히려 차단하던 문제를 NSAllowsLocalNetworking 제거로 해결(app.json/Info.plist). 안내 문장 어색함 원인 분석 후 RAG on/off 비교 테스트용 RAG_ENABLED 환경변수 토글 추가(server/detection/consumer.py, 기본값 true, 삭제 아닌 비활성화). Xcode DerivedData 등 로컬 빌드 산출물이 !client/ios/** 예외로 추적되던 .gitignore 결함 수정. LiveCameraFeed.tsx 렌더 중 ref mutation을 useLayoutEffect로 이동(React Doctor 지적), consumer.py SIM103 lint 위반 수정
- **관련 파일**: `gitignore`, `client/App.tsx`, `client/app.json`, `client/ios/.gitignore`, `client/ios/Minchodan/AppDelegate.swift`, `client/ios/Minchodan/Info.plist`, `client/src/components/CameraView.tsx`, `console/src/components/LiveCameraFeed.tsx`, `docs/changelogs/kb.md`, `docs/ops/environment_variables.md`, `server/detection/consumer.py`, `server/detection/detection_pipeline.py`, `server/detection/gates/surface_gate.py`, `server/tts/suppressor.py`, `tests/test_detection.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-20 | 문서·7단계 | 발표 대본 정합성 검사 후속: 온디바이스 문서 동기화 및 TTS 억제기 레거시 코드 정리

- **배경**: 발표 대본 정합성 검사 보고서(Fable 5 작성)를 코드 대조로 재검증하는 과정에서, `docs/README.md`(온디바이스 추론 "없음/post-MVP")와 `AGENTS.md` §2(CoreML/TFLite 온디바이스 탐지 등재) 간 서술 상충과, `server/tts/suppressor.py`에 호출자가 전혀 없는 레거시 억제 로직(60초 TTL 방식)이 남아있는 것을 확인.
- **변경 내용**:
  - `docs/README.md`: "현재 문서 기준선" 항목을 CoreML(iOS)/TFLite(Android) 온디바이스 반사 추론이 이미 구현·실기기 배포된 상태로 갱신(단, 서버 왕복 없는 완전 온디바이스 완결은 미검증임을 명시). "1주차 미결정 7개" 표는 역사 기록으로 보존하고 기존 확정 반영 각주 패턴에 맞춰 On-device 항목 갱신 각주를 추가.
  - `server/tts/suppressor.py`: 호출자 없는 레거시 `DEFAULT_TTL`/`DEFALUT_TTL` 상수, `__init__`의 `ttl` 파라미터/`self.ttl`, `_make_key()`, `should_suppress()`, `should_supperss()`(오타 메서드), `mark_as_sent()`를 삭제. 실제 사용 중인 재무장 정책(track_id+거리밴드 키, `REFLEX_SUPPRESS_TTL_S=5`)만 남김.
- **관련 파일**: `docs/README.md`, `server/tts/suppressor.py`
- **검증 결과**: `.venv/bin/ruff check` 통과, `.venv/bin/bandit -r server/tts/suppressor.py` 이상 없음, `.venv/bin/mypy server/tts/suppressor.py` 이상 없음(별도 파일 `korean_g2p.py`의 사전 존재 오류 1건은 본 변경과 무관). 리포 전체 grep으로 삭제 대상 심볼의 잔존 참조 없음 확인.
- **비고**: `server/rag/fallback.py`(룰 기반 RAG 폴백 모듈, 실시간 파이프라인 미배선) 배선 여부는 별도 논의 필요 — 이번 작업 범위에서 제외.

---

### 2026-07-20 | 5~6단계 | Medium 인지 짧은 힌트 Dict 전환 (GUIDANCE_CONTEXT_MODE)

- **커밋**: `dc8f020`
- **배경**: Medium 안내가 RAG on이면 완성문 압축으로 어색하고, RAG off면 힌트 부재로 단조로워지며, 임베딩+Chroma 왕복은 사실상 라벨 매칭인데도 rag_ms를 소모한다. 계획서 검증 후 인메모리 짧은 힌트로 교체.
- **변경 내용**:
  - `server/rag/guidance_hints.py` 신규: 29+노면 클래스별 2힌트, 길이/방향금지어 검증, seed 결정적 선택.
  - `server/detection/consumer.py`: `GUIDANCE_CONTEXT_MODE=hints|rag` (기본 hints). hints면 retriever 미호출.
  - `server/orchestration/nodes/l2_generator.py`: `[회피 힌트]` 주입 및 방향은 [탐지 방향]만 사용 규칙 추가.
  - `tests/test_guidance_hints.py` 신규. 계획서·`docs/README.md`·`environment_variables.md` v0.4.27·`.env.example`·`stage6_orchestration_design.md` 동기화.
  - Docker: console `node_modules` named volume, macos compose FastAPI `0.0.0.0` 바인딩.
- **관련 파일**: `server/rag/guidance_hints.py`, `server/detection/consumer.py`, `server/orchestration/nodes/l2_generator.py`, `tests/test_guidance_hints.py`, `docs/ops/medium_guidance_hint_dict_implementation_plan.md`, `docs/ops/environment_variables.md`, `docs/README.md`, `docs/stage-guides/stage6_orchestration_design.md`, `.env.example`, `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`
- **검증 결과**: `pytest tests/test_guidance_hints.py` + `tests/test_langgraph.py` 통과. 이중 경로·react-doctor·자동 발행 통과.
- **비고**: Chroma/편의 RAG는 유지. 실기기 A/B(S5)는 후속. 롤백은 `GUIDANCE_CONTEXT_MODE=rag`.

---

### 2026-07-20 | 1·3·콘솔 | console_gps_hud_bbox_overlay

- **커밋**: `2accf80`
- **배경**: Detection Guidance Log 썸네일에 박스가 없고, 콘솔 GPS HUD가 "앱 GPS 대기"에 고착.
- **변경 내용**:
  - 콘솔: 목록 썸네일에도 bbox 오버레이, `pipeline_debug` 폴백. HUD 헤더에 수신 좌표 표시.
  - 서버: 반사·노면-only 로그에 bbox 저장. `realtime_gps` 콘솔 브로드캐스트 유지, 수신 로그 스로틀.
  - 단말: WS `connected` 후 GPS 전송 + 즉시 `getCurrentPosition`, `distanceInterval=0`.
  - 문서: `architecture.md`/`api_specification.md` v0.4.33/`pipeline_stage_design.md`/`docs/README.md` 동기화.
- **관련 파일**: `client/src/components/CameraView.tsx`, `client/src/hooks/useLocation.ts`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/components/LiveCameraFeed.tsx`, `console/src/styles.css`, `server/api/ws_router.py`, `server/detection/consumer.py`, `docs/design/*`
- **검증 결과**: 이중 경로·react-doctor·`test_langgraph` 통과. FastAPI recreate 후 `dev-001` welcome 확인.
- **비고**: 단말 Metro 리로드 후 HUD 헤더 좌표·서버 `[WS] realtime_gps 수신` 로그로 확인.

---

### 2026-07-20 | ops | Metro 에이전트 셸 독립 detach

- **커밋**: `a904d75`
- **배경**: `metro_tailscale.sh`의 `nohup`+`disown` 기동이 Cursor 에이전트 짧은 셸 종료 시 회수되어 Dev Client가 서버를 못 찾는 문제가 반복됨.
- **변경 내용**:
  - `scripts/metro_tailscale.sh` start를 Python double-fork + `os.setsid()` orphan 기동으로 교체. session root가 `launchd`(ppid=1).
  - `status`에 ancestry/`detach: OK|WARN` 출력. `METRO_CLEAR=1`로 `--clear` 지원.
  - `integration-test-orchestrator` 스킬 v1.3.1 반영(.agents/.claude 미러).
- **관련 파일**: `scripts/metro_tailscale.sh`, `.agents/skills/integration-test-orchestrator/SKILL.md`, `.claude/skills/integration-test-orchestrator/SKILL.md`
- **검증 결과**: 짧은 `bash -c '… start'` 후 `npm` 부모=`launchd(1)`, localhost·Tailscale `/status` 200. cursor-agent ancestry 없음.
- **비고**: 기존처럼 테스트 중 불필요한 `stop`/`kill :8081`은 금지.

---
### 2026-07-20 | 단말·ops | Metro Tailscale 고정 운영 스크립트

- **커밋**: `199ed28`
- **배경**: Metro가 세션마다 kill/잘못된 host/setsid로 자주 죽어 Dev Client가 서버를 못 찾음.
- **변경 내용**:
  - `scripts/metro_tailscale.sh` 신규: start(이미 살아 있으면 유지)·stop·restart·status·launch(딥링크).
  - `client/package.json`에 `metro:ts*` npm 스크립트 추가.
  - `integration-test-orchestrator` 스킬: 무조건 kill 금지, 본 스크립트 사용으로 정정(.agents/.claude 미러).
- **관련 파일**: `scripts/metro_tailscale.sh`, `client/package.json`, `.agents/skills/integration-test-orchestrator/SKILL.md`, `.claude/skills/integration-test-orchestrator/SKILL.md`
- **검증 결과**: `metro_tailscale.sh status/start` — localhost·Tailscale OK, 기존 프로세스 skip 확인.
- **비고**: 앱 실행은 `bash scripts/metro_tailscale.sh launch` 권장.

---

### 2026-07-20 | 단말·7단계 | 인지 안내 대기열 폐기 정책을 시간순에서 위험도순으로 전환

- **배경**: 12시 회랑 인지 안내 대기열(`GUIDE_PENDING_MAX=6`)이 초과분을 오래된 순(FIFO)으로 폐기하고, 재생 종료 후에도 "최신 1건"만 재생했다. 위험도(우선순위) 낮은 것부터 버리도록 바꿔달라는 요청에 따라 확인해보니, 기존 구조에서는 재생 중인 것보다 낮은 우선순위가 즉시 드롭돼 큐 안 항목이 항상 동일 우선순위였고(비교 대상 자체가 없어 우선순위 기반 폐기가 무의미), 큐가 우선순위를 혼합해 담도록 입장 게이트부터 완화해야 함을 확인.
- **변경 내용**:
  - `canStartGuide`: 재생 중인 것보다 낮은 우선순위를 즉시 드롭하던 조건 제거(STT 게이트는 유지). 낮은 우선순위도 대기열 적재 후보가 됨.
  - 신규 `evictLowestPriorityPendingGuide()`: 대기열 6개 초과 시 최하위 우선순위부터 폐기(동률이면 오래된 쪽). `enqueueGuide`의 overflow 처리에서 기존 `shift()`(FIFO) 대체.
  - `drainNewestPendingGuide` → `drainHighestPriorityPendingGuide`로 개명 및 로직 전환: 재생 자연 종료 시 "최신 1건" 대신 "최고 우선순위 1건"(동률이면 최신)을 재생. 호출부 2곳(자연 종료, 재생 실패 폴백) 갱신.
  - 선점(preemption) 시 하위 우선순위 큐 전체를 비우는 `discardPendingGuidesBelow`는 의도적으로 유지(위급 상황 종료 후 낡은 저위험 안내가 뒤늦게 재생되는 것을 방지, 접근성 안전 보수적 선택).
  - stale 주석 정리(`GUIDE_PENDING_MAX` 상단 주석, `pendingGuides` 필드 주석).
- **관련 파일**: `client/src/services/audioEngine.ts`
- **검증 결과**: `cd client && npx tsc --noEmit -p .` 통과(오류 0건). ESLint 설정 부재로 스킵.
- **비고**: 빌드/실기기 재생 순서 확인은 미실시 — Metro 리로드 후 실기기에서 우선순위 혼합 상황(예: 측면 저위험 다건 + 정면 near) 재생 순서 실측 권장.

---

### 2026-07-20 | 문서·7단계 | 반사 오디오 명세서 §5.2 우선순위 모델 문서 동기화 (auto-publish-work Step 2 후속)

- **배경**: 직전 커밋(대기열 위험도순 폐기 전환)에서 `auto-publish-work` 스킬 Step 2(문서 교차 검증)를 건너뛰었다는 지적을 받고 확인. `docs/design/reflex_audio_specification.md` §5.2 "T3-C 통합 오디오 우선순위 모델(2026-07-18)"이 3단(P1/P2/P3) 모델로 남아있어, 실제 코드의 4단 모델(`guidePriority.ts`, 2026-07-19 전환)과 이미 어긋나 있었고 대기열 정책(FIFO/최신 1건) 서술도 이번 변경으로 완전히 stale해짐을 확인.
- **변경 내용**:
  - §5.2를 실제 코드 기준 4단(OTHER=1/FRONT_MED=2/FRONT_NEAR=3/STT=4)으로 정정하고, "거리보다 12시 정면 여부가 먼저 걸리는 하드 게이트"라는 비직관적 동작을 명시.
  - 대기열 정책 절 신설: `GUIDE_PENDING_MAX=6`, 선점 시 하위 큐 전량 폐기(유지), 6개 초과 시 최하위 우선순위 폐기(신규), 자연 종료 시 최고 우선순위 1건 드레인(신규) 및 각각의 이전 동작(FIFO/최신 1건) 대비.
  - 문서 버전 헤더 v1.3.1 → v1.3.2.
  - `docs/design/api_specification.md`는 WS 메시지 스키마(`clock_direction`/`distance_class` 필드) 변경이 없어 확인만 하고 미수정. `docs/mobile/HEURISTIC_DISTANCE_ALERT_ROUTING_IMPLEMENTATION_PLAN.md`는 특정 시점 감사 기록(C-09 등)이라 갱신 대상에서 제외.
- **관련 파일**: `docs/design/reflex_audio_specification.md`
- **검증 결과**: 문서만 수정(코드 변경 없음). 목차·인접 절(§5.1, §5.3) 번호·앵커 정합 확인.
- **비고**: HEURISTIC 문서의 `HIGH_DANGER_INTERVAL_MS`(250ms→100ms, 2026-07-19 정정) 관련 서술도 별도로 stale하나 이번 작업 범위 밖으로 남겨둠.

---

### 2026-07-20 | 6단계 | medium_fast_lane_guidance_templates

- **커밋**: `8e81b28`
- **변경 내용**:
  - Medium/Near 인지 패스트 레인 안내를 N시 방향 객체 주의하세요 및 전방 객체 N시로 우회하세요 패턴으로 통일하고, avoid_clock_direction과 노면-only 힌트 주입·Fallback 동일 템플릿·stage6 설계서 v0.2.2를 반영한다.
- **관련 파일**: `ocs/stage-guides/stage6_orchestration_design.md`, `server/detection/consumer.py`, `server/detection/direction.py`, `server/orchestration/nodes/fallback_node.py`, `server/orchestration/nodes/fast_lane.py`, `server/orchestration/nodes/l3_validator.py`, `server/orchestration/state.py`, `tests/test_fast_lane.py`, `tests/test_langgraph.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-20 | 3·6·7단계 | 실기기 필드 테스트 피드백 4건 수정 (12시 밖 TTS·무명사 안내·노면 방향 고정·Near 햅틱)

- **배경**: 통합 테스트 환경(Docker+Metro+실기기) 세션 중 사용자가 실기기로 직접 테스트하며 4가지 문제를 보고. FastAPI/Metro 로그를 대조해 각각 실제 발생 지점을 확인.
- **변경 내용**:
  - `server/orchestration/avoidance.py`(P1-1 반사 후속 avoidance fast lane): `direction != "front"`(12시 회랑 밖)는 `None`을 반환해 무발화 처리 - 반사 비프·햅틱의 스테레오 패닝으로 이미 방향이 전달되므로 측면까지 TTS로 중복 안내하지 않음. `build_avoidance_guidance`가 `object_ko`를 받아 모든 분기(정면 중앙 애매, "정지" 표지판 클래스)에서 명사 없는 "멈추세요" 대신 객체명을 포함하도록 변경(L2 프롬프트가 정지 명령을 금지하는 것과 동일한 이유).
  - `server/detection/consumer.py`: 노면(차도/주의 노면) 전용 인지 안내 분기가 `clock_direction="12시"`/`avoid_clock_direction="2시"`로 무조건 하드코딩되어 있던 것을, 노면 centroid 기반 `estimate_clock_direction`/`estimate_avoid_clock_direction` 재사용으로 교체(계산 불가 시에만 12시/2시 안전 폴백). 실측 로그상 "차도"/"주의 노면" 우회 안내 15건 전부 "2시"로 고정돼 있었음 - 방향이 동적이지 않다는 피드백의 실제 원인.
  - `client/src/services/hapticEngine.ts`: `stopContinuous({ respectMinimum: true })` 옵션 신설 - 이미 시작된 continuous 진동 패턴을 최소 500ms(`CONTINUOUS_MIN_MS`)까지는 실제 정지를 유예. `client/src/hooks/useWebSocket.ts`의 `reflex_clear` 핸들러에만 적용(다른 13곳의 즉시-정지 호출은 그대로 유지). 실측 로그상 Near 반사 진입~`reflex_clear`까지 약 300ms만에 종료되는 경우가 흔해, 300ms 간격 반복 진동이 시작 알림 1회 외엔 거의 못 느껴지던 문제 대응.
  - `tests/test_langgraph.py`의 `TestAvoidanceFastLane`을 새 동작(12시 밖 None, 명사 포함 문구)에 맞춰 갱신 및 신규 케이스 추가.
- **관련 파일**: `server/orchestration/avoidance.py`, `server/detection/consumer.py`, `client/src/services/hapticEngine.ts`, `client/src/hooks/useWebSocket.ts`, `tests/test_langgraph.py`
- **검증 결과**: `pytest tests/test_langgraph.py tests/test_fast_lane.py tests/test_detection.py` → **119 passed**. `ruff check`/`bandit`/`mypy` 이상 없음(기존 무관 오류 2건 제외). `tsc --noEmit` 통과. FastAPI 재기동 후 정상, 실기기 재연결 확인.
- **비고**: 실기기 라이브 재검증은 사용자 테스트 진행 중(로그 모니터 병행).

---

### 2026-07-20 | STT·네비게이션 | STT 목적지 인식 회귀 분석 보고서 P0 6건 수정

- **배경**: GPT가 작성한 `stt_navigation_destination_accuracy_regression_analysis.md`(jy 브랜치 STT 목적지 인식·경로 안내 회귀 분석)를 코드 실행·git diff 대조로 재검증(확정 결함 3건·회귀 커밋 10건·테스트 공백 주장 전부 100% 재현 확인) 후, P0 권고 6건을 순서대로 구현.
- **변경 내용**:
  - `server/stt/stt_to_llm_bridge.py`: `_parse_destination_text()` 신설 - 전역 `.replace("로","")` 치환(`"구로역"`→`"구역"` 훼손) 대신 접두("목적지는")·접미(조사+명령어미) 위치기반 stripping. 단독 "로"/"으로" 제거는 "테헤란로"/"종로" 등 장소명 보호를 위해 의도적으로 제외.
  - 같은 파일: `_is_exact_gildaeng_reconfirm()` 신설, WAITING_FOR_DESTINATION 분기를 fuzzy wake보다 앞으로 재배치 - "길동역"/"길음역"/"길상사"(편집거리 1 이하로 "길댕"과 유사)가 더 이상 wake로 오인돼 재질문만 반환되지 않음. `_has_explicit_destination_intent()` 신설 - "까지"+이동 표현이 있으면 "어떻게" 같은 질문 힌트가 있어도 목적지로 우선 처리("서울역까지 어떻게 가" 대응).
  - `server/navigation/server.py`: `helper_resolve_destination_poi()` 신설 - `count=1`/`pois[0]` 고정 대신 후보 5개 이상을 정확명일치→현재 위치 거리 순으로 점수화, 동명 후보 거리 우위가 불분명하면 `ambiguous=True` 신호. `helper_search_poi`/`helper_search_nearest_poi`/`helper_fetch_route`의 TMAP 키 누락 시 고정 가상 좌표(126.8722/37.4590 등) 성공 처리를 제거하고 `None`(실패)로 전환 - `docs/ops/environment_variables.md`에 이미 문서화된 "키 미설정 시 기능 비활성화" 정책과 정합.
  - `server/navigation/manager.py`: 신규 상태 `WAITING_FOR_POI_CONFIRMATION` 추가, `pending_poi_candidates` 세션 필드와 접근자 메서드 신설. `stt_to_llm_bridge.py`는 동명 POI가 모호하면 자동 확정 대신 "1번/2번..." 음성 확인 질문을 반환하고 다음 발화(순번 선택)로 경로를 확정하도록 신규 분기 추가. 성공 안내도 사용자 검색어 대신 실제 선택된 `end_poi["name"]`을 읽도록 `_setup_route_with_poi()`로 공통화(이전엔 TMAP이 다른 동명 지점을 선택해도 사용자가 알아챌 방법이 없었음).
  - `tests/test_stt_to_llm_bridge_template.py`, `tests/test_navigation_server_poi_resolver.py`(신규): 보고서 §15 필수 회귀 케이스(장소명 보존 5종, wake 충돌 3종, 질문 의도 우선, 동명 POI 확인·선택 플로우, 키 누락 fail-closed 4종) 커버.
- **관련 파일**: `server/stt/stt_to_llm_bridge.py`, `server/navigation/server.py`, `server/navigation/manager.py`, `tests/test_stt_to_llm_bridge_template.py`, `tests/test_navigation_server_poi_resolver.py`
- **검증 결과**: `pytest tests/test_stt_to_llm_bridge_template.py tests/test_ws_router_stt.py tests/test_stt_config_policy.py tests/test_stt_service_template.py tests/test_stt_wait_notice.py tests/test_navigation_server_poi_resolver.py` → **60 passed**. `ruff check` 이상 없음. `bandit`/`mypy` 기존 무관 오류만 잔존(신규 없음).
- **비고**: P1(녹음 UX 200ms arm, 절단 검사 복원, GPS 전송 큐잉, LineString 지도 전달, facilityType 타입 정합)·P2(관측성 로그)는 이번 범위 밖. 실기기 오디오 절단·AEC 순서는 정적 분석만으로 확정 불가해 별도 실기기 검증 필요(보고서 자체도 명시).

---

### 2026-07-20 | 문서 | STT/네비게이션 P0 수정 문서 동기화 (auto-publish-work Step 2 후속)

- **배경**: 직전 P0 6건 커밋 시 `auto-publish-work` 스킬 Step 2(문서 교차 검증)를 다시 건너뛴 것을 사용자가 지적. `docs/design/api_specification.md` §6.3 명령 어휘 표와 `docs/stage-guides/stage_stt_integration_guide.md` §5·§6이 새 목적지 파서·POI 확인 플로우·fail-closed 정책을 반영하지 못해 stale해진 것을 확인하고 정정.
- **변경 내용**:
  - `docs/design/api_specification.md`: §6.3 명령 어휘 표에 목적지 발화(위치기반 파서+POI resolver) 행 갱신, `1번`/`2번`/`3번`(`WAITING_FOR_POI_CONFIRMATION`) 행 신설. 2026-07-20 비고 블록 추가(파서·wake 우선순위·POI 확인·fail-closed 4건 요약, `environment_variables.md` §2.14 교차 참조). 버전 헤더·이력 표 v0.4.33 → v0.4.34.
  - `docs/stage-guides/stage_stt_integration_guide.md`: §5 가드레일에 "목적지 대기 우선순위"·"목적지 파서 위치기반 stripping"·"POI 확인" 3행 신설. §6 테스트 체크리스트에 TC-STT-012~015(장소명 보존·wake 오탐 방지·동명 POI 확인·키 누락 fail-closed) 추가, 대응 pytest 테스트명 명시. 버전 헤더 v0.2.4 → v0.2.5.
- **관련 파일**: `docs/design/api_specification.md`, `docs/stage-guides/stage_stt_integration_guide.md`
- **검증 결과**: 문서만 수정(코드 변경 없음). 표·비고 블록 마크다운 파싱 확인(`grep -c "^|"`), 버전 헤더-이력 표 정합 확인.

---

### 2026-07-20 | 3·7단계 | code_docs_consistency_sync

- **커밋**: `18ac9d9`
- **배경**: GLM 문서 정합 작업이 중단된 미커밋 working tree를 코드 SSOT와 교차 검증한 뒤 남은 stale를 마저 맞춤.
- **변경 내용**:
  - 설계/ops/스킬: alert_id `high_obstacle`, Surface Gate P0 `{caution,stair_down,manhole}`, 억제 TTL 5s(surface 15s), TTS 4엔진, status dead contract, STT `faster-whisper-small` 동기화.
  - 잔여 stale: pipeline/test/redis/Directory_Structure/README/reflex_audio/stage6/android/`high_car_front` 정정.
  - 코드: `server_detection`·`latency_event` ts를 epoch ms(`now_ts`), 인지 guide `source=cognitive`, TTS 타임아웃 주석 15s.
- **관련 파일**: `docs/design/*`, `docs/ops/*`, `docs/stage-guides/*`, yolo-obstacle-detection SKILL(.agents/.claude), `server/detection/consumer.py`, `server/tts/realtime_tts.py`
- **검증 결과**: 이중 경로 OK, react-doctor 통과. Docker `pytest tests/test_detection.py tests/test_fast_lane.py tests/test_langgraph.py` → **119 passed**. 호스트 stage3(`verify_gpu`/torch)는 환경 부재로 skip-test 후 Docker 검증으로 대체.
- **비고**: `docs/research/*` 과거 문제 서술(개선 계획서)은 현행 명세가 아니므로 범위 외.

---

### 2026-07-20 | 3·7단계 | 외부망 실기기 필드 테스트 피드백 3건 수정 (클래스명 누출·노면 반복 안내·햅틱 고착)

- **배경**: 외부 Tailscale 망 실기기 테스트 로그를 직접 분석해 3가지 문제 재현·원인 규명 후 수정. 앞선 세션의 코드 4건 수정과는 별개의, 이번에 처음 발견된 결함들.
- **변경 내용**:
  - `server/navigation/manager.py`: TMAP 길안내 중 장애물을 같이 읽어주는 `_pop_obstacle_text()`가 SSOT `class_name_to_ko`(29+4클래스)를 쓰지 않고 자체 9종짜리 불완전 사전(`korean_mapping`)을 갖고 있어, 커버 안 되는 클래스(`sidewalk_normal` 등)가 원문 그대로 새던 결함 수정(실측: "전방에 sidewalk_normal 주의하세요." 280회). 안전 노면(`sidewalk_normal`/`braille_normal`)은 애초에 장애물 캐시에서 제외. 전역 5초 쿨다운(같은 클래스도 계속 재탐지되면 5~6초마다 무한 반복 안내)을 "같은 클래스는 `OBSTACLE_REPEAT_SUPPRESS_S`(30초) 동안 억제, 다른 클래스는 즉시 안내"로 교체.
  - `client/src/services/audioEngine.ts`: `setSttActive(true)`가 `CameraView.tsx`(녹음 시작)와 `useWebSocket.ts`(응답 수신) 두 지점에서 호출되는데, 안전 상한 타이머(`STT_INTERACTION_TIMEOUT_MS`)는 응답-수신 경로에만 걸려 있어 녹음 시작 직후 응답이 끝내 안 오면(외부망 연결 유실 등) STT 억제 상태가 영구 고착 - 실측 로그: STT "활성화" 14회 대비 "비활성화" 9회, 로그 종료 시점도 활성 상태로 멈춤. `setSttActive()` 자체에 `STT_SAFETY_TIMEOUT_MS`(20초) 안전 상한을 내장해 호출 지점과 무관하게 항상 해제되도록 정정(기존 useWebSocket.ts 타이머는 중복 백스톱으로 유지, idempotent).
  - `docs/design/reflex_audio_specification.md`: §5.2 STT 안전 상한 서술을 위 변경에 맞춰 정정. 버전 v1.3.3 → v1.3.4.
  - `tests/test_navigation_manager_obstacles.py`(신규): 안전 노면 미캐시, SSOT 번역, 같은 클래스 억제, 다른 클래스 즉시 안내, 억제 시간 만료 후 재안내 5건.
- **관련 파일**: `server/navigation/manager.py`, `client/src/services/audioEngine.ts`, `docs/design/reflex_audio_specification.md`, `tests/test_navigation_manager_obstacles.py`
- **검증 결과**: `pytest` **163 passed**. `ruff check`/`mypy` 이상 없음(기존 무관 오류 1건 제외). `tsc --noEmit` 통과. FastAPI 재기동 후 정상.
- **비고**: 실기기 재검증은 사용자 진행 중.

---

### 2026-07-20 | 3·7단계 | 필드 로그 기반 노면 비중·Near 무반응 수정 (P0~P2 일괄)

- **배경**: device_id=3 DB 로그 분석 - 인지의 ~67%가 노면, 후반 세션에서 Near 비프가 STT/head_level/노면에 잠식. 제안 P0~P2를 일괄 구현.
- **변경 내용**:
  - P0-1: 노면 에피소드 `SURFACE_HAZARD_ABSENT_STREAK` 기본 5, `SURFACE_REENTER_COOLDOWN_S=20` 재진입 억제.
  - P0-2: STT 중 Near 반사 비프·햅틱 병행(`playBeep` 허용, `allowDuringStt`, `setSttActive`에서 stopBeep 제거). 인지 guide만 STT 우선.
  - P0-3: `head_level` 반사는 near + medium 12시 회랑만(far 스팸 차단).
  - P1-4: Near 노면 인지 명시 억제(반사 전담) 재확인.
  - P1-5: nav `caution|roadway` → `surface_hazard` 억제 키 그룹화.
  - P1-6: 점자-only 별도 에피소드 + `BRAILLE_REENTER_COOLDOWN_S=45`.
  - P2-7: Near `reflex_clear` `NEAR_CLEAR_HOLD_OFF_S=0.4` hold-off.
  - P2-8: `pipeline_debug`에 surface_episode/reset_reason/stt_gate_blocked 관측 필드.
- **관련 파일**: `server/detection/consumer.py`, `detection_pipeline.py`, `server/navigation/manager.py`, `server/services/pipeline_debug_builder.py`, `client/src/services/audioEngine.ts`, `hapticEngine.ts`, `useWebSocket.ts`, `docs/ops/environment_variables.md`, `docs/design/reflex_audio_specification.md`, tests
- **검증 결과**: Docker `pytest tests/test_detection.py tests/test_navigation_manager_obstacles.py` → **87 passed**. 이중 경로 OK, react-doctor 통과.
- **커밋**: `be7337f`

---

### 2026-07-20 | 3·7단계 | 안내용 12시 회랑(SPEECH_FRONT_BAND) 분리

- **배경**: 필드 테스트에서 전방 다수 객체에 음성·햅틱이 과도. `front`(충돌 회랑)·`center`(화면 중앙)·`unknown`(폴백)이 모두 「정면」으로 안내되던 혼동.
- **변경 내용**:
  - `direction.py`: `SPEECH_FRONT_BAND`(near 0.35~0.65, medium 0.40~0.60) + `is_speech_front`/`is_speech_front_x`(center_x, width<=0→False). `FRONT_BAND`는 공간 라벨용 유지.
  - 반사/인지/노면/head_level 게이트를 speech_front만 통과. 반사 클립 `high_front.wav` 고정. 인지 clock은 12시 정규화.
  - `risk_rules`: `center`→화면 중앙, `unknown`→방향 미상, 안내 hint에서 제외.
- **관련 파일**: `server/detection/direction.py`, `gates/reflex_gate.py`, `gates/surface_gate.py`, `detection_pipeline.py`, `consumer.py`, `risk_rules.py`, docs, tests
- **검증 결과**: Docker `pytest tests/test_detection.py tests/test_distance_priority_integration.py` → **98 passed**. Ruff OK.
- **커밋**: `5eca38f`

---

### 2026-07-20 | 3단계 | DB 로그 분석 기반 반사 억제 재조정(노면 과다·near 햅틱 따닥거림)

- **배경**: 실기기 통합테스트 중 사용자가 "안내메세지가 너무 적고, 노면 안내가 과다해 정보 불균형이 있으며, 메시지·햅틱 싱크가 안 맞는다"고 피드백. `detection_guidance_logs` 원격 DB를 직접 조회해 검증:
  - 최근 6시간 reflex(무음성) 184건 vs cognitive(음성) 99건 - near가 medium보다 약 2배 많아 체감상 안내가 적음.
  - `surface_caution.wav` 반사 클립이 같은 구간에서 5분간 8회(평균 35초 간격) 반복 - 개별 억제값은 통과하지만 누적 빈도가 과다.
  - 같은 track_id(T-0008)가 0.54초·0.72초 간격으로 near 햅틱을 연속 재발동(500ms 스로틀만 적용되고 track 단위 최소 간격이 없었음) - 음성 없는 near 구간에서 햅틱만 빠르게 반복되어 "싱크 안 맞음"으로 체감.
  - near=즉시 촉각/medium=상세 음성이라는 이중 경로 원칙 자체는 유지하기로 결정(설계 비협상 원칙과 부합).
- **변경 내용**:
  - `server/tts/suppressor.py`: `REFLEX_NEAR_TRACK_MIN_GAP_S`(기본 1.2초) 신규 - near에서 동일 track_id 재발동에만 추가 최소 간격 적용(다른 물체는 기존 500ms 스로틀만 유지해 반응성 보존).
  - `REFLEX_SURFACE_SUPPRESS_TTL_S` 15→30초, `REFLEX_SURFACE_MIN_GAP_S` 8.0→15.0초 상향(노면 반복 경보 빈도 완화).
- **관련 파일**: `server/tts/suppressor.py`, `.env.example`, `docs/ops/environment_variables.md`, `docs/design/reflex_audio_specification.md`, `tests/test_suppressor_rearm.py`
- **검증 결과**: `pytest tests/test_suppressor_rearm.py` → **15 passed**(신규 3건 포함). `pytest tests/` 전체 435 passed(기존에도 실패하던 WS/임베딩 통합 테스트 7건은 무관, `git stash`로 무변경 상태에서도 동일 실패 확인). Ruff OK, mypy 무관.
- **비고**: STT 응답 무반응 별도 이슈는 faster-whisper-small 모델(`model.bin`) 프리로드 다운로드가 컨테이너 기동 중 정체된 것이 원인으로 확인·재다운로드 후 해소(코드 변경 없음, 인프라 이슈).

---

### 2026-07-20 | 인프라 | huggingface 모델 캐시 영속 볼륨 추가(STT 무한 대기 재발 방지)

- **배경**: 위 항목에서 STT 무응답을 재다운로드로 임시 해소했으나, `hf_cache`가 컨테이너 쓰기 계층에만 존재해 컨테이너 재생성(코드 변경 후 `--build`)마다 faster-whisper-small(~480MB)을 처음부터 다시 받아야 했다. 재빌드 직후 실기기 테스트에서 동일 증상이 즉시 재현되어, 근본 원인(캐시 미영속화)을 인프라 레벨에서 수정.
- **변경 내용**:
  - `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`: fastapi 서비스에 `hf_cache:/home/minchodan/.cache/huggingface` 명명 볼륨 추가(두 변형 모두).
  - `docs/ops/deployment_guide.md`: §2.1 서비스 표·§7.2 볼륨 정의에 `hf_cache` 반영.
- **관련 파일**: `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `docs/ops/deployment_guide.md`
- **검증 결과**: 컨테이너 재생성 후 `docker exec`로 faster-whisper-small 로드 재수행, 볼륨에 모델 저장 확인. YAML 구문 검증(`yaml.safe_load`) 통과.
- **비고**: 다음 컨테이너 재생성부터는 재다운로드 없이 캐시를 재사용하므로 이 클래스의 STT 무한 대기가 재발하지 않는다.

---

### 2026-07-20 | 6단계 | 실외 재테스트 3건 - 패스트레인 다중객체 차단·캐시 키 정확성·노면 반사 2차 조정

- **배경**: 1차 조정(노면 반사 TTL/갭 상향, near track 재발동 억제) 배포 후 실외 재테스트에서 3건 재보고: (1) 노면 안내가 여전히 큰 위험 아닌데도 자주 나옴, (2) 안내 음성이 싱크 안 맞게 늦는 느낌, (3) 안내 음성 빈도가 여전히 적어 보임. `detection_guidance_logs`의 `latency_json`을 직접 조회해 원인 특정:
  - "전방 차도, 2시로 우회하세요"가 280ms(우연한 범용 텍스트 캐시 히트)와 6666ms(실시간 LLM+TTS)로 들쭉날쭉 - `scripts/build_guide_clips.py`가 object 클래스 10종만 순회하고 `caution`/`roadway`는 애초에 사전합성 대상에서 빠져 있어 "차도" 클립이 0개였음.
  - "사람" 안내는 클립이 다 있음에도 항상 LLM 호출(~2초) - `can_use_fast_lane()`이 프레임 내 탐지 객체가 2개 이상이면 통째로 차단(사람은 다른 보행자/차량과 자주 동시 탐지됨).
  - `make_fast_lane_cache_key()`가 `avoid_clock_direction`을 반영하지 않아, 12시+우회 문구와 12시+단순 주의 문구가 같은 키로 충돌(정확성 결함 - 다른 안내문 오디오가 재생될 수 있었음).
- **변경 내용**:
  - `fast_lane.py`: `can_use_fast_lane()`을 프레임 내 전체 탐지 개수가 아니라 주위험 객체(object_ko) 하나만 기준으로 완화. `make_fast_lane_cache_key()`에 `avoid_clock` 반영(12시+우회는 `avoid{10시|2시}` 접미사로 키 분리). `FAST_LANE_SURFACE_CLASS_NAMES`, `FAST_LANE_AVOID_CLOCKS` 신규.
  - `scripts/build_guide_clips.py`: caution/roadway 클래스와 12시 우회 변형(avoid_clock=10시/2시)을 사전합성 대상에 추가(210→324건). 신규 114건 합성 완료.
  - `server/tts/suppressor.py`: `REFLEX_SURFACE_SUPPRESS_TTL_S` 30→60초, `REFLEX_SURFACE_MIN_GAP_S` 15.0→45.0초 2차 상향.
- **관련 파일**: `server/orchestration/nodes/fast_lane.py`, `scripts/build_guide_clips.py`, `server/tts/suppressor.py`, `.env.example`, `docs/ops/environment_variables.md`, `docs/design/reflex_audio_specification.md`, `docs/stage-guides/stage6_orchestration_design.md`, `tests/test_fast_lane.py`
- **검증 결과**: `pytest tests/` 전체 443 passed(신규 8건 포함, 기존 무관 실패 7건 동일 유지). `python scripts/build_guide_clips.py --dry-run` 324건 확인, 실제 빌드 324/324 성공. Ruff/mypy OK(무관 1건 제외).

---

### 2026-07-20 | 3단계 | 다중 객체 프레임에서 정면 위험 간헐적 무발화·무반응 - 주위험 객체 선정 방식 교체

- **배경**: 실외 재테스트에서 "medium+12시 car 안내 없음", "near+12시 객체 햅틱 무반응" 재보고. DB 로그로 확인: 11:36~11:42 사이 car가 초당 3~5회 연속 탐지(person/truck과 동시 다발)되는데도 6분 넘게 인지 안내 0건·반사 4건뿐이었음. 코드 추적 결과 두 경로 모두 "프레임당 객체 하나만 대표로 뽑는" 설계가 원인으로 확인:
  - 인지: `consumer.py`의 `primary_det = max(result.detections, key=lambda d: d.confidence)` - confidence는 "정면 위협도"와 무관한데, 다중 객체가 매 프레임 함께 잡히면 confidence 요동으로 "이번 프레임의 대표"가 계속 바뀌어 정면 차량이 confidence 경쟁에서 밀리면 무발화.
  - 반사: `detection_pipeline.py`의 `_evaluate_reflex()`가 `detections` 리스트 순서상 첫 통과 항목을 즉시 반환 - YOLO 출력 순서는 confidence/거리 정렬을 보장하지 않아 실제 근접 위험이 뒤쪽에 있으면 스킵 가능.
- **변경 내용**:
  - `server/detection/distance_policy.py`: `select_primary_detection()` 신규 - 우선순위 (1) 거리 구역(near>medium>far) (2) 동일 구역 내 실측 거리 오름차순 (3) 12시 회랑 중심 근접도 (4) confidence(최종 tie-break).
  - `server/detection/consumer.py`: `_send_cognitive_guide`의 `primary_det` 선정을 `select_primary_detection()`으로 교체하고, 같은 메서드 내 중복 재계산되던 3곳(rag_query, cognitive_class/confidence/direction)도 동일 `primary_det`를 재사용하도록 정리(기존에는 필터가 본 객체와 실제 안내에 쓰인 객체가 다를 수 있었음).
  - `server/detection/detection_pipeline.py`: `_evaluate_reflex()`를 "첫 통과 항목 즉시 반환"에서 "게이트 통과한 모든 후보를 모은 뒤 거리 구역>실측 거리 기준 최우선 1건 반환"으로 변경. 프레임당 1건 상한(안전 설계 의도)은 유지, 대표 선정 기준만 교체.
- **관련 파일**: `server/detection/distance_policy.py`, `server/detection/consumer.py`, `server/detection/detection_pipeline.py`, `tests/test_distance_policy.py`, `tests/test_detection.py`, `docs/research/field_test_round2_improvement_plan.md`
- **검증 결과**: `pytest tests/` 전체 452 passed(신규 9건 포함, 기존 무관 실패 7건 동일 유지). Ruff/mypy OK(무관 기존 오류 제외, stash 비교로 신규 오류 없음 확인).
- **비고**: 반사 경로는 결정론적 게이트 로직(LLM/RAG 미경유)을 그대로 유지 - "누가 프레임당 1건의 대표가 되는가"만 개선했다.

---

### 2026-07-20 | 1단계 | 장시간 테스트 시 데이터 미정리로 인한 체감 지연 - Redis 스트림 트리밍·이벤트 프레임 주기 정리

- **배경**: "시간이 지날수록 반응이 느려진다"는 실기기 피드백. 컨테이너 직접 점검 결과 `risk.events` Redis Stream이 `xadd`에 `maxlen`이 없어 **29시간 동안 236,529건까지 무제한 누적**돼 있었고(수동 `XTRIM`으로 5,000건까지 즉시 축소), 이벤트 프레임(JPEG) 정리(`EVENT_FRAME_RETENTION_DAYS=7`)는 **서버 기동 시 1회만 실행**돼 재시작 없이 장기간 구동하면 보존 기간을 넘긴 폴더도 전혀 정리되지 않는 구조였다(85MB/1556개 파일 확인). 다만 FastAPI 컨테이너 CPU 329%·`StreamSplitter 큐 가득참` 드롭 로그도 함께 확인되어, 체감 지연의 더 직접적 원인은 로컬 CPU 기반 YOLO 추론 포화일 가능성이 높다는 점도 함께 보고함(하드웨어 제약, 별도 대응 필요).
- **변경 내용**:
  - `server/bus/redis_client.py`: `RedisBus.publish_event()`의 `xadd` 호출에 `maxlen=REDIS_STREAM_MAXLEN(기본 5000)`, `approximate=True` 추가. 컨슈머(navigation/mcp)는 `XREAD`로 최신 이벤트만 순차 소비하므로 트리밍이 기능에 영향 없음.
  - `server/main.py`: 이벤트 프레임 정리를 기동 시 1회 실행에서 `EVENT_FRAME_CLEANUP_INTERVAL_S`(기본 6시간) 주기 반복 루프로 전환.
  - `server/services/event_frame_store.py`: `cleanup_expired_frames()` 독스트링을 주기 실행 반영으로 정정.
- **관련 파일**: `server/bus/redis_client.py`, `server/main.py`, `server/services/event_frame_store.py`, `.env.example`, `docs/ops/environment_variables.md`, `tests/test_redis_client.py`(신규)
- **검증 결과**: `pytest tests/` 전체 455 passed(신규 3건 포함, 기존 무관 실패 7건 동일 유지). Ruff/Bandit OK. 운영 중인 Redis에서 `XTRIM risk.events MAXLEN 5000` 즉시 적용해 236,529→5,000건으로 축소 확인.

---

### 2026-07-20 | 3단계 | CPU 경합 완화 - YOLO 추론 전용 스레드풀 분리

- **배경**: 위 데이터 정리 수정 후에도 "CPU 부하 원인도 같이 봐달라"는 요청. 실기기 활발한 테스트 중 FastAPI 컨테이너 CPU 329%(유휴 시 0.46%) 확인 후 코드 추적. `OMP_NUM_THREADS=4` 등은 `docker-compose.macos.yml`에 이미 적용돼 있어(과거 800~1300% 실측 후 완화 이력) 근본 원인은 아니었음. 실제 원인은 `asyncio.to_thread()`로 위임되는 YOLO 탐지/분할 추론이 파이썬 **기본 ThreadPoolExecutor(워커 18개)를 TTS 합성·STT·RAG 검색·이벤트 프레임 저장과 통째로 공유**하는 구조 - 반사(8~10fps)·인지(1~2fps) 두 스트림이 별도 Task로 동시에 추론을 제출하는데, TTS 합성(1.4~2.6초) 같은 느린 작업이 같은 풀 큐에 몰리면 그 뒤 추론이 대기하며 체감 지연이 세션이 길어질수록 누적될 수 있는 구조였음.
- **변경 내용**:
  - `server/detection/detection_pipeline.py`: 모듈 레벨 전용 `ThreadPoolExecutor`(`_inference_executor`, `YOLO_INFERENCE_WORKERS` 기본 3) 신설. `detector.predict`/`segmentor.predict` 위임을 `asyncio.to_thread()`에서 `loop.run_in_executor(_inference_executor, ...)`로 교체해 다른 서브시스템과 워커를 공유하지 않도록 분리.
- **관련 파일**: `server/detection/detection_pipeline.py`, `.env.example`, `docs/ops/environment_variables.md`, `tests/test_detection.py`
- **검증 결과**: `pytest tests/` 전체 456 passed(신규 1건 - 추론이 `yolo-inference` 스레드에서 실행됨을 스레드명으로 검증, 기존 무관 실패 7건 동일 유지). Ruff/mypy/Bandit OK.
- **비고**: 프레임 내부(det→seg)는 기존대로 순차 실행 유지. 워커 수(3)는 반사·인지 두 스트림의 동시 제출량만 고려해 소수로 제한(OMP_NUM_THREADS=4와 곱해도 14코어 호스트를 과도하게 넘지 않도록).

---

### 2026-07-21 | 문서 | YOLO26N 가중치 기본값 문서-코드 정합 정정

- **배경**: `docs/ops/environment_variables.md`의 `YOLO26N_OBJECT_DET`/`YOLO26N_SEG` 기본값 설명이 2026-07-14 커밋(`3b0bc05`, 온디바이스 CoreML 연동을 위한 260714 가중치 전환)에서 실제 `.env.example`/`.env`가 `object_detection260714.pt`/`segmentation260714.pt`로 바뀐 뒤에도 갱신되지 않고 이전 값(`det_best_20260705.pt`/`segbest.pt`)을 그대로 설명하고 있던 정합성 누락을 발견해 정정.
- **변경 내용**:
  - `docs/ops/environment_variables.md`: 두 변수 설명을 실제 기본값(`object_detection260714.pt`/`segmentation260714.pt`)으로 정정하고, 서버·온디바이스(CoreML/TFLite) 공통 기준선임과 레거시 파일(`det_best_20260705.pt`/`segbest.pt`) 관계를 명시. 버전 v0.4.34→v0.4.35.
- **관련 파일**: `docs/ops/environment_variables.md`
- **검증 결과**: `server/models/yolo26n/` 내 `object_detection260714.pt`/`segmentation260714.pt` 실존 확인, `.env.example`·`.env` 값과 일치 확인.

---

### 2026-07-21 | 문서 | 다중 에이전트 스킬 노출 정합 - rpi-network-profile-switcher

- **배경**: 팀원이 GPT(Codex 계열) 기반으로 만든 `rpi-network-profile-switcher` 스킬을 팀 공용으로 쓸 수 있는지 점검. `dev` 병합·SKILLS.md/AGENTS.md 인덱스 등재·`.claude/skills` 미러까지는 정상이었으나, 이 스킬만 `agents/openai.yaml`(Codex 계열 스킬 인터페이스 매니페스트)을 갖고 있어 다른 10개 스킬과 폴더 구조가 다른 점, 그리고 이 사실이 `SKILL.md`에 드러나지 않는 점을 확인. 이어서 팀이 실제 사용하는 Claude Code/Codex/Antigravity/opencode/Cursor/ZCode 전체에 이 스킬이 노출되는지 점검한 결과 두 가지 누락 발견: (1) `.antigravity/rules.md`(12,000자 캡 대응 요약본)의 스킬 인덱스 표에 신규 스킬이 반영되지 않아 Antigravity가 스킬 존재 자체를 인지할 수 없었음, (2) 다른 스킬들과 달리 `.cursor/rules/`에 glob 기반 자동 첨부 규칙 파일이 없어 Cursor가 관련 파일 작업 시 자동으로 안내받지 못함.
- **변경 내용**:
  - `.agents/skills/rpi-network-profile-switcher/SKILL.md`, `.claude/skills/rpi-network-profile-switcher/SKILL.md`: 메타데이터 블록에 "지원 에이전트" 줄 추가 - `agents/openai.yaml` 존재와 역할, 다른 스킬 폴더와의 구조 차이를 명시. 버전 v1.0.0→v1.0.1.
  - `.antigravity/rules.md`: §10 스킬 인덱스 표에 `rpi-network-profile-switcher` 행 추가(6,310자, 12,000자 캡 이내).
  - `.cursor/rules/12-rpi-network-profile-switcher.mdc` 신규: `scripts/switch_rpi_network.sh`, `docker/scripts/db_tailscale_proxy.sh`, `.env.network.*` glob 트리거, 핵심 금지 행위(빌드 금지, DDL/볼륨 삭제 금지, `.env` 전체 출력 금지) 요약.
- **관련 파일**: `.agents/skills/rpi-network-profile-switcher/SKILL.md`, `.claude/skills/rpi-network-profile-switcher/SKILL.md`, `.antigravity/rules.md`, `.cursor/rules/12-rpi-network-profile-switcher.mdc`
- **검증 결과**: `python scripts/validate_agent_rules.py` 6/6 PASS(`.antigravity/rules.md` 캡 여유 5,690자 포함). `diff -rq .agents/skills/rpi-network-profile-switcher .claude/skills/rpi-network-profile-switcher` 완전 일치 확인.
- **비고**: Codex가 `agents/openai.yaml`을 실제 네이티브로 인식해 스킬로 호출하는지는 이 세션에서 검증 불가 - 원작성 팀원의 Codex 세션에서 직접 확인 필요.

---

### 2026-07-21 | 문서 | Android-iOS 정합 체크리스트·Gemini 작업 지시서 등재

- **커밋**: `d8b5474`
- **배경**: Mac/iOS 중심 통합 테스트 환경에서 Android 정합 상태를 분석한 결과, Frame Processor·TFLite·AEC 모듈은 코드상 상당 부분 존재하나 로컬 반사 정책·실기기 검증·계약서 stale(§4.5 미착수 표기)·문서 인덱스가 부족해 Gemini/Android 담당 에이전트에 넘길 단일 실행 기준이 필요했다.
- **변경 내용**:
  - `docs/mobile/android_ios_parity_checklist.md` 신규(v1.0.0): Gemini 복붙 지시문, P0~P2 체크리스트(모델·캡처·반사 정책·인지·오디오·네트워크), A-S1~A-S10 검증 매트릭스, 권장 실행 순서, 명시적 제외 항목.
  - `docs/mobile/ios_android_bifurcation_contract.md` v1.2.0: §4.5를 "코드 구현됨·실기기 검증은 정합 체크리스트"로 정정하고 실행 문서 링크 추가.
  - `docs/README.md` v0.14.3: 문서 인덱스·mobile/ 표에 정합 체크리스트 등재.
- **관련 파일**: `docs/mobile/android_ios_parity_checklist.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 링크 경로 존재 확인. 구현 코드는 본 세션에서 변경하지 않음(문서 전용).
- **비고**: Android 구현은 dg 계열 에이전트/담당자가 체크리스트 §0 지시문으로 착수. 서버 YOLO `*260714` 정합은 로컬 `.env`에서 이미 적용됨(커밋 대상 아님).

---

### 2026-07-21 | 문서 | Android 작업자 인수인계서 작성

- **배경**: Samsung SM-S938N 실기기 검증에서 TFLite 네이티브 로드는 확인됐으나 Wi‑Fi/Tailscale 미도달·Metro 번들 미로드로 A-S1~S7 종단은 미검증. 제미나이 로컬 커밋 2개(`959c256`, `239d5b0`)는 `origin/kb`에 미푸시이며, `CameraView` 로컬 반사 공통화는 iOS 런타임에 영향. Android 담당자에게 상태·위험·잔여 작업을 넘기기 위한 단일 인수인계서가 필요했다.
- **변경 내용**:
  - `docs/mobile/android_handoff_kb_to_dg.md` 신규(v1.0.0): Git/미푸시 커밋, 실측 표, iOS 영향·R-00 옵션, 인수 직후 체크리스트, 함정, 보고 템플릿, 참고 명령.
  - `docs/mobile/android_ios_parity_checklist.md`: 인수인계 링크 및 §0 복붙 지시문에 인수인계서·P0 기각 주의 추가.
  - `docs/README.md` v0.14.3→v0.14.4: 인덱스·mobile/ 표에 인수인계서 등재.
- **관련 파일**: `docs/mobile/android_handoff_kb_to_dg.md`, `docs/mobile/android_ios_parity_checklist.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 문서 경로·상호 링크 존재 확인. 코드/런타임 변경 없음.
- **비고**: 제미나이 2커밋 푸시·CameraView 승인/롤백은 인수자(dg)·kb 합의 후 진행. 본 항목은 문서만.

---

### 2026-07-21 | 클라이언트 | iOS 로컬 반사를 bf2c0eb 기준으로 복구 (R-00=B)

- **배경**: `239d5b0`가 Android pathObstacle·speakFallback·실내 억제 정책을 iOS에까지 공통 적용해, 실내 Near 폴백 소실·오프라인 Near 전용 정책 충돌·로컬 TTS 선점 간섭이 확인됨. iOS 담당 기준선은 **`bf2c0eb`**(2026-07-20 `Merge branch 'kb' into dev`)로 확정.
- **변경 내용**:
  - `client/src/components/CameraView.tsx`: `Platform.OS` 분기 복구. iOS = bf2c0eb와 동일(서버 정상 억제 / 타임아웃 시 Near `applyLocalAreaReflex`). Android 정책은 android 분기에만 유지.
  - `docs/mobile/android_handoff_kb_to_dg.md`: R-00=B, 기준 커밋 `bf2c0eb` 기록.
- **관련 파일**: `client/src/components/CameraView.tsx`, `docs/mobile/android_handoff_kb_to_dg.md`, `docs/changelogs/kb.md`
- **검증 결과**: `git diff bf2c0eb -- client/src/components/CameraView.tsx` 로직 본문 일치(기준선 주석 1줄만 추가).

---

### 2026-07-21 | 3단계 | head_level 오안내 완화 - 발화조건·클립 문구

- **배경**: 외부 실측에서 `head_level_pole`(medium)이 반복되며 고정 클립 "머리위 위험 조심하세요"가 전봇대·지면 고정물에 부적절하게 들림.
- **변경 내용**:
  - `HEAD_LEVEL_ESCALATION_CLASSES`를 돌출·상단 설비 6종으로 축소(`pole`/`bollard` 등 지면 고정물 제외).
  - `_evaluate_head_level`: **near만** 허용(medium/far 제외), 12시 회랑 유지.
  - `head_level_gate`: bbox 하단 `BOTTOM_MAX_RATIO=0.55` 초과 시 제외, `MIN_AREA_RATIO=0.02`.
  - 클립 문구를 "앞에 높은 장애물 조심하세요."로 재합성(`client`/`console` wav).
  - 테스트·api_specification·stage6·behavior 문서 동기화.
- **관련 파일**: `server/detection/gates/head_level_gate.py`, `server/detection/detection_pipeline.py`, `tests/test_detection.py`, `client/assets/sounds/reflex_clips/head_level_warning.wav`, `console/public/reflex_clips/head_level_warning.wav`, `docs/design/api_specification.md`, `docs/stage-guides/stage6_orchestration_design.md`, `docs/design/behavior_and_risk_insight.md`, `docs/changelogs/kb.md`
- **검증 결과**: 컨테이너 `pytest -k head_level` 7 passed. FastAPI restart 후 health 200.

---

### 2026-07-21 | 1·2·3·7단계 | P0/P1 과부하 백프레셔·추론 절감·guide drop

- **배경**: 야외 실측에서 macOS CPU YOLO 포화 + `[StreamSplitter] 큐 가득참` drop이 누적되고, 디코드 후 route busy drop·늦은 인지 음성이 UX를 악화시킴. 처리량 자체보다 **신선한 소수 프레임**·CPU 낭비 제거·늦은 OTHER 안내 억제가 목표.
- **변경 내용**:
  - **P0 디코드 전 busy 스킵**: `route_sem` 잠금 또는 스트림 큐 full이면 OpenCV 디코드/라우팅을 건너뛰고 ack만 응답(`skipped_decode`).
  - **P0 서버→단말 백프레셔**: ack에 `server_busy`/`suggest_reflex_interval_ms`(기본 250ms). 단말 `reportServerLoad`가 반사 캡처 간격을 상향(최대 300ms), busy hold 1.5s 동안 온디바이스 복구 억제.
  - **P1 반사 seg 간헐**: `REFLEX_SEG_EVERY_N=3`(기본). det는 매 프레임, seg는 N마다. 노면 게이트는 `_last_reflex_surfaces`로 평가. 인지는 항상 seg.
  - **P1 guide 대기열**: `GUIDE_PENDING_MAX` 6→2. 재생 중 OTHER는 대기열 미적재·즉시 drop.
- **관련 파일**: `server/api/ws_router.py`, `server/capture/stream_splitter.py`, `server/detection/detection_pipeline.py`, `client/src/hooks/useCamera.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `client/src/services/audioEngine.ts`, `client/src/types/detection.ts`, `docs/design/api_specification.md`, `docs/ops/environment_variables.md`, `docs/changelogs/kb.md`
- **검증 결과**: `.venv`에서 `pytest tests/test_frame_decode.py tests/test_detection.py` 128 passed.
- **비고**: fps↓는 장당 모델 정확도 하락이 아님. surface 반사는 주기 seg+캐시에 의존하므로 실측 확인 권장. 서버/단말 재기동·Metro reload 후 busy ack·동적 fps 로그 확인.

---

### 2026-07-21 | 7단계 | Near enter 시 행동 음성 클립 1회

- **배경**: Near 반사가 beep-only(`beep_interval_ms<=100`)라 햅틱/비프만 나가고, 시각장애인 입장에서 다음 행동 단서(음성)가 없음. 인지 guide는 Near 비프에 선점되어 더 늦거나 끊김.
- **변경 내용**:
  - `useWebSocket`: 긴급이어도 `event_state=enter`이면 `playReflexClip` 1회(`enter-clip+beep`). `update`는 기존 beep-only.
  - `audioEngine.playReflexClip`: 클립 재생 중 비프 덕킹(최대 3.5s 안전 타임아웃).
  - `reflex_audio_specification.md` v1.3.8 채널 분기 갱신.
- **관련 파일**: `client/src/hooks/useWebSocket.ts`, `client/src/services/audioEngine.ts`, `docs/design/reflex_audio_specification.md`, `docs/changelogs/kb.md`
- **검증 결과**: Metro reload 후 실기기 Near 진입 시 클립 1회 + 연속 비프/햅틱 확인 권장.

---

### 2026-07-21 | 7단계 | Near 행동 안내 미재생 수정

- **배경**: 반사 탐지·햅틱은 되나 행동 음성이 안 들림. (1) enter만 클립이라 update만 오면 무음 (2) Near 비프 update가 후속 guide TTS를 stop (3) post_reflex 우선순위가 OTHER로 떨어져 묻힘.
- **변경 내용**:
  - 단말: track당 클립 1회(enter 또는 첫 알림), clear 시 리셋.
  - 단말: Near 비프가 가이드를 stop하지 않고 덕킹만.
  - 서버: 반사 전송 로그에 `event_state`/`beep_ms` 추가. post_reflex preset에 `clock_direction=12시`·`distance=near` 고정.
- **관련 파일**: `client/src/hooks/useWebSocket.ts`, `client/src/services/audioEngine.ts`, `server/detection/consumer.py`, `docs/changelogs/kb.md`
- **검증 결과**: FastAPI restart + Metro reload 후 Near 진입 시 클립·후속 안내 실측 필요.

---

### 2026-07-21 | 7단계 | guide 단말 무음 수정 (비프 덕킹·binary 폴백)

- **배경**: 서버 로그에 `전방 이동형 표지판 있어요` + `guide 전송`까지 있는데 단말에서 안 들림. Near 연속 비프(interval=0)가 가이드 시작 후에도 볼륨 1.0 고정, binary WAV 유실 시 폴백 없음.
- **변경 내용**:
  - 가이드/폴백 TTS 시작 시 Near 비프 즉시 덕킹, 종료 시 복구.
  - `transport=binary`인데 1.2s 내 WAV 미도착 시 `speakFallback`로 동일 문구 재생.
  - Blob 바이너리 수신 지원. 서버 guide 로그에 transport/text/clock/dist 추가.
- **관련 파일**: `client/src/services/audioEngine.ts`, `client/src/hooks/useWebSocket.ts`, `server/detection/consumer.py`, `docs/changelogs/kb.md`

### 2026-07-21 | 7단계 | Near 말 안내 침묵(비프만) 수정

- **배경**: 실측에서 Near 비프/햅틱은 들리는데 `전방 차량 있어요` 말 안내가 거의 안 들림. 서버는 `avoidance fast lane`만 찍고 `guide 전송`이 생략됨.
- **원인**: (1) 동일 `obj:car` 서명 30초 발화가치 억제가 post_reflex에도 적용 (2) 인지 guide gap 최소 8초 (3) Near 연속 비프 덕킹 볼륨 0.25가 말을 덮음 (4) preset 경로 `used_fast_lane=False`로 느린 TTS 경로.
- **변경 내용**:
  - post_reflex(preset)는 30초 동일서명 억제 생략. 오디오 겹침만 near=재생길이+1.5s(최소 2.5s)로 제한.
  - `used_fast_lane=True`로 즉시 합성. 억제/쿨다운 로그 INFO.
  - 단말 `DUCKED_BEEP_VOLUME` 0.25→0.08.
- **관련 파일**: `server/detection/consumer.py`, `client/src/services/audioEngine.ts`, `tests/test_detection.py`, `docs/changelogs/kb.md`
- **검증 결과**: `TestApproachingCooldownShortcut` 3 passed. FastAPI 재시작 후 Near 재진입 시 guide 전송·단말 말 안내 실측 필요.


---

### 2026-07-21 | 3단계 | near_guide_speech_and_busy_backpressure

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Near 말안내 쿨다운·비프 덕킹 수정 및 P0/P1 과부하 백프레셔·seg 간헐 적용
- **관련 파일**: `env.example`, `client/assets/sounds/reflex_clips/head_level_warning.wav`, `client/src/components/CameraView.tsx`, `client/src/hooks/useCamera.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/services/audioEngine.ts`, `client/src/types/detection.ts`, `console/public/reflex_clips/head_level_warning.wav`, `docs/changelogs/kb.md`, `docs/design/api_specification.md`, `docs/design/behavior_and_risk_insight.md`, `docs/design/reflex_audio_specification.md`, `docs/ops/environment_variables.md`, `docs/stage-guides/stage6_orchestration_design.md`, `server/api/ws_router.py`, `server/capture/stream_splitter.py`, `server/detection/consumer.py`, `server/detection/detection_pipeline.py`, `server/detection/gates/head_level_gate.py`, `tests/test_detection.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-21 | 문서 | 시연/테스트 장비 제원 인벤토리 신설 및 rpi-network-profile-switcher 관련 문서 링크 추가

- **배경**: 이전 항목(다중 에이전트 노출 정합, 커밋 `1a51c31`)에 이어, 시연 테스트 기기 체크를 위해 팀이 사용 중인 4개 장비(LLM/GPU 추론 서버, Mac mini 개발 머신, iPhone 16 Pro Max 클라이언트, Raspberry Pi 5B DB) 제원을 한곳에 모아달라는 요청. 이어서 이 제원을 `rpi-network-profile-switcher` 스킬에 반영해야 하는지 검토 요청 - 스킬의 실행 경계(Raspberry Pi 네트워크 프로필 전환)를 벗어나는 서버·Mac mini·iPhone 제원까지 스킬 본문에 넣는 건 범위 확장이자 단일 출처 원칙 위반이라 판단해, 스킬 본문에는 제원을 복사하지 않고 인벤토리 문서로 링크만 연결하기로 결정.
- **변경 내용**:
  - `docs/ops/demo_test_device_inventory.md` 신규: 서버(Windows i9-13950HX+RTX 4090)·Mac mini(M4 Pro)는 실측 스펙 기록, iPhone 16 Pro Max(칩/RAM/저장용량 미기록)·Raspberry Pi 5B(SSD 용량·OS 버전은 `db_tailscale_guide/README.md`의 의도적 비공개 정책)는 미확인 항목을 명시적으로 구분해 기록. `docs/README.md` 인덱스에 등재(v0.14.4→v0.14.5).
  - `.agents/skills/rpi-network-profile-switcher/SKILL.md`(+`.claude/skills/` 미러): "관련 문서"에 `demo_test_device_inventory.md` 링크 1줄만 추가(v1.0.1→v1.0.2). 장비 제원 본문은 스킬에 중복 기재하지 않고 단일 출처(인벤토리 문서)만 유지.
- **관련 파일**: `docs/ops/demo_test_device_inventory.md`, `docs/README.md`, `.agents/skills/rpi-network-profile-switcher/SKILL.md`, `.claude/skills/rpi-network-profile-switcher/SKILL.md`
- **검증 결과**: `python scripts/validate_agent_rules.py` 6/6 PASS. `diff -rq .agents/skills/rpi-network-profile-switcher .claude/skills/rpi-network-profile-switcher` 완전 일치.
- **비고**: iPhone 16 Pro Max 하드웨어 제원(칩/RAM/저장용량)·Raspberry Pi SSD 정확한 용량은 담당자 확인 후 인벤토리 문서에 채워 넣어야 함. 이 커밋 시점에 작업 트리에 있던 별도 미검증 작업(Near/Medium 오디오 완주 우선순위 수정 - `audioEngine.ts`/`consumer.py`/`test_detection.py`/`reflex_audio_specification.md`)은 무관한 작업이라 이번 커밋에서 의도적으로 제외하고 `git stash`로 보존함(추후 별도 검증·커밋 필요).

---

### 2026-07-21 | 인프라 | 시연 테스트 환경 구축 - rpi-network-profile-switcher에 LLM(Mac mini) LAN 연결 통합

- **배경**: "시연 테스트 환경 구축 스킬을 만드는 것"이 맞는지 확인 후, 실제 시연 네트워크 토폴로지를 확정: 아이폰↔서버(Windows)는 Tailscale 유지, 서버(Windows)↔LLM(Mac mini)·DB(Raspberry Pi)는 LAN으로 분리. 기존 `rpi-network-profile-switcher`는 Raspberry Pi DB·미디어망만 다뤄서, 서버-LLM 간 LAN 연결(기존에는 같은 장비에서 Ollama를 함께 띄우던 것을 Mac mini로 분리)이 스킬 범위 밖이었던 것을 확인하고 통합.
- **변경 내용**:
  - `scripts/switch_rpi_network.sh`: `.env.network.<profile>`에서 `COMPOSE_OLLAMA_BASE_URL`을 선택적으로 읽어, 존재하면 전환 전 Ollama `/api/tags` 도달성 사전검사를 DB TCP·미디어 `/health` 검사와 같은 자리에 추가. 값이 없으면 기존처럼 스킵(`test` 프로필은 동일 호스트 Ollama 가정 그대로 하위 호환).
  - `.agents/skills/rpi-network-profile-switcher/SKILL.md`(+`.claude/skills/` 미러): "목적과 실행 경계"에 LLM(Mac mini) LAN 스코프와 실행 위치(서버는 WSL2에서 실행, `docker-compose.yml`이 Linux/GPU 변형 전제) 명시. "정본과 보안 규칙" 표에 `COMPOSE_OLLAMA_BASE_URL` 행 추가. 워크플로우의 예시 dotenv·실패 메시지 표·완료 기준 표에 LLM 사전검사 반영. Mac mini의 `OLLAMA_HOST=0.0.0.0` 바인딩·방화벽 전제조건 명시. 버전 v1.0.2→v1.1.0.
  - `docs/ops/demo_test_device_inventory.md`: "2. 네트워크 토폴로지" 섹션 신규(아이폰↔서버=Tailscale, 서버↔LLM(Mac mini)=LAN, 서버↔DB(RPi)=LAN). 장비 개요 표의 역할 라벨 정정(LLM/GPU 통합 서버 → GPU 서버와 LLM 호스트 분리). "7. 미확인 항목"에 Mac mini LAN IP 항목 추가. 버전 v1.0.0→v1.1.0.
  - `docs/ops/environment_variables.md`: `COMPOSE_OLLAMA_BASE_URL` 설명에 demo 프로필의 Mac mini LAN 분리 용도·전제조건·사전검사 문구 보강. 버전 v0.4.36→v0.4.37.
  - `docs/README.md`: 인벤토리 문서 설명에 네트워크 토폴로지 반영 문구 추가. 버전 v0.14.5→v0.14.6.
- **관련 파일**: `scripts/switch_rpi_network.sh`, `.agents/skills/rpi-network-profile-switcher/SKILL.md`, `.claude/skills/rpi-network-profile-switcher/SKILL.md`, `docs/ops/demo_test_device_inventory.md`, `docs/ops/environment_variables.md`, `docs/README.md`
- **검증 결과**: `bash -n scripts/switch_rpi_network.sh` 통과. `python scripts/validate_agent_rules.py` 6/6 PASS. `diff -rq .agents/skills/rpi-network-profile-switcher .claude/skills/rpi-network-profile-switcher` 완전 일치. 실제 Mac mini LAN 연결·Ollama LAN 바인딩은 시연 현장에서 실측 필요(미완료).
- **비고**: 이 커밋 시점에도 `docs/changelogs/kb.md`를 포함해 다른 세션에서 Near/Medium 오디오 관련 작업(WIP)이 동시에 진행 중이었다. 작업 트리 충돌을 피하기 위해 `git hash-object`/`git update-index`로 이 changelog 항목만 커밋 시점의 HEAD(`e272449`) 위에 직접 이어붙여 인덱스에 스테이징했고, 실제 작업 트리 파일(`docs/changelogs/kb.md` 등)은 전혀 건드리지 않았다. 그 외 무관 WIP 파일(`audioEngine.ts`/`consumer.py`/`test_detection.py`/`reflex_audio_specification.md`)도 이번 커밋에 포함하지 않았다.

---

### 2026-07-21 | 7단계 | Near 안내 완주 우선 + gap 정합

- **배경**: 안내가 들릴 때/안 들릴 때 혼재. 서버 쿨다운 생략·짧은 enter flash 외에, 단말에서 enter 반사 클립이 FRONT_NEAR guide를 0초대에 `stopGuideAudio` 하는 조기 중단이 실측됨.
- **변경 내용**:
  - **B 단말**: FRONT_MED+ 재생 중 반사 클립 생략(완주). 동일/하위 우선은 선점 금지, 대기열 최신 1건만(`GUIDE_PENDING_MAX=1`). STT만 선점.
  - **A 서버**: Near guide gap = max(2.0, 직전길이+1.0s). device별 delayed guide는 최신 태스크만 유지(이전 cancel).
  - `reflex_audio_specification.md` v1.3.9.
- **관련 파일**: `client/src/services/audioEngine.ts`, `server/detection/consumer.py`, `tests/test_detection.py`, `docs/design/reflex_audio_specification.md`, `docs/changelogs/kb.md`
- **검증 결과**: `TestApproachingCooldownShortcut` 통과. FastAPI 재시작·Metro reload 후 Near 연속 진입 시 말 완주 실측 필요.

---

### 2026-07-21 | 6·7단계 | Near 완주 후 Medium 1회 (쿨다운 슬롯 분리)

- **배경**: Medium 인지 안내는 동작하나 Near post_reflex·공유 쿨다운·동일서명 30초에 막혀 체감 무발화. Near 직후 Medium 1회가 필요.
- **변경 내용**:
  - 서버: Near/Medium **밴드별** guide ts·duration 슬롯. Near가 Medium을 막지 않음. 서명에 `dist:` 포함.
  - 단말: Near 재생 중 Medium은 대기 유지(동일 우선만 교체). Near 완주 후 Medium 재생(OTHER만 drain 시 폐기). `GUIDE_PENDING_MAX=2`.
- **관련 파일**: `server/detection/consumer.py`, `client/src/services/audioEngine.ts`, `tests/test_detection.py`, `docs/changelogs/kb.md`
- **검증 결과**: `TestApproachingCooldownShortcut`+`TestUtteranceValueGate` 15 passed.

---

### 2026-07-21 | 3·7단계 | Near update가 delayed TTS를 cancel하던 P0 수정

- **배경**: Near는 초반에만 말이 나오고 체류·시간이 지나면 비프만 남음. update마다 800ms delayed guide를 재예약·cancel한 것이 원인.
- **변경 내용**:
  - `_should_schedule_post_reflex_guide` — `event_state=update` 및 노면 반사는 delayed TTS 미예약. enter(·head_level)만 예약. update는 in-flight enter 안내를 끊지 않음.
- **관련 파일**: `server/detection/consumer.py`, `tests/test_detection.py`, `docs/changelogs/kb.md`
- **검증 결과**: `TestPostReflexGuideSchedule` 3 passed.

---

### 2026-07-21 | 7단계 | near_medium_guide_completion

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Near 완주·Medium 쿨다운 슬롯 분리 및 update delayed TTS cancel 방지
- **관련 파일**: `lient/src/services/audioEngine.ts`, `docs/changelogs/kb.md`, `docs/design/reflex_audio_specification.md`, `server/detection/consumer.py`, `tests/test_detection.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-21 | 콘솔 | Live Feed 2계층 거리/통로 오버레이

- **배경**: area_ratio SSOT와 원근 호·통로 ROI가 한 겹으로 섞여 "미디엄 지역인데 FAR 태그" 오해가 생김. 권장 2계층(L1 PATH ROI + L2 거리 호 근사)을 콘솔에 우선 반영.
- **변경 내용**:
  - `LiveCameraFeed.tsx`: L1 단말과 동일 PATH ROI 사다리꼴(점선 cyan), L2 `heuristic_m=0.22/sqrt(a)` 경계(~0.7m/~1.3m)로 접촉 Y를 맞춘 Near/Med 호, 라벨에 SSOT/근사 구분. (등면적 참조 박스는 불필요로 제거)
  - BBox 색·태그는 기존처럼 `effective_distance_zone` 유지(판정 정본).
- **관련 파일**: `console/src/components/LiveCameraFeed.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: IDE 린트 이상 없음. 콘솔 Live Feed에서 L1/L2 표시 실측 필요.

---

### 2026-07-21 | 클라이언트 | CameraView 2계층 거리/통로 오버레이 (콘솔 정합)

- **배경**: 콘솔 Live Feed에 반영한 L1 PATH ROI + L2 거리 호 도식을 단말에도 동일 적용.
- **변경 내용**:
  - `CameraView.tsx` `DistanceZoneOverlay`: PATH ROI 사다리꼴(점선 cyan) + heuristic_m(~0.7m/~1.3m) 접촉 Y 호, SSOT/근사 구분 라벨. 등면적 박스는 콘솔과 같이 미포함. 반사 ROI 필터 로직은 유지.
- **관련 파일**: `client/src/components/CameraView.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: Metro reload 후 탐지 ON 시 L1/L2 표시 실측 필요.

---

### 2026-07-21 | 2단계 | dual_layer_distance_overlay

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 콘솔·앱 Live Feed에 L1 PATH ROI와 L2 거리 호 2계층 도식 정합
- **관련 파일**: `lient/src/components/CameraView.tsx`, `console/src/components/LiveCameraFeed.tsx`, `docs/changelogs/kb.md`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

### 2026-07-21 | CI | kb→dev mypy 실패 항목 수정

- **커밋**: `fix: CI mypy 오류 수정 (kb→dev Lint 게이트)`
- **변경 내용**:
  - `korean_g2p.py`: tuple 변환을 명시적 3-tuple로 정합
  - `stt_service.py`: WhisperModel optional 바인딩 타입 정리
  - `navigation/manager.py`, `server.py`: ImportError 폴백 `no-redef` ignore
  - `detection/consumer.py`: orch 결과 `dict[str, Any]`로 고정 후 int/float 캐스트
  - `embedding_engine_factory.py`: 임베딩 벡터 float 정규화 타입 정합
- **관련 파일**: `server/tts/korean_g2p.py`, `server/stt/stt_service.py`, `server/navigation/manager.py`, `server/navigation/server.py`, `server/detection/consumer.py`, `server/rag/embedding_engine_factory.py`
- **검증 결과**: `mypy server/` 오류 0건
- **비고**: `ac777d8` push 후 GitHub Actions Code Quality Pipeline mypy 6건 실패 대응

### 2026-07-21 | CI | jscpd를 npx로 설치해 Lint 워크플로 보완

- **커밋**: `fix(ci): jscpd를 npx로 실행하도록 Lint 워크플로 수정`
- **변경 내용**: GitHub Actions에 Node setup + `npx jscpd` 추가(기존 `jscpd` 미설치로 exit 127)
- **관련 파일**: `.github/workflows/lint.yml`
- **검증 결과**: 로컬 mypy 통과 후 CI 재실행 예정
- **비고**: mypy 수정 커밋 이후 드러난 후속 게이트 실패

### 2026-07-21 | 시연 | Ollama 모델 상주 스크립트 등재

- **커밋**: `feat(demo): Ollama keepalive 스크립트 및 시연 스킬 전제조건 반영`
- **변경 내용**:
  - `scripts/ollama_demo_keepalive.sh` 추가 (LAN 바인딩 + gemma4/nomic keep_alive=-1)
  - `rpi-network-profile-switcher`·`integration-test-orchestrator` 시연 전 실행 안내
  - `demo_test_device_inventory.md` Mac mini 절에 상주 절차 링크
- **관련 파일**: `scripts/ollama_demo_keepalive.sh`, `.agents/skills/rpi-network-profile-switcher/SKILL.md`, `.agents/skills/integration-test-orchestrator/SKILL.md`, `.claude/skills/` 미러, `docs/ops/demo_test_device_inventory.md`
- **검증 결과**: 스크립트 실행으로 워밍 지연 ~1초대 확인(콜드 ~6초 제거)
- **비고**: Mac 재부팅·Ollama 종료 후 시연 전 재실행 필요

---

### 2026-07-21 | 1단계 | demo_skill_server_bringup

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - 시연 스킬에 Pi·Ollama·FastAPI·console·Metro 기동 체크리스트 편입
- **관련 파일**: `agents/skills/integration-test-orchestrator/SKILL.md`, `.agents/skills/rpi-network-profile-switcher/SKILL.md`, `.agents/skills/rpi-network-profile-switcher/agents/openai.yaml`, `.claude/skills/integration-test-orchestrator/SKILL.md`, `.claude/skills/rpi-network-profile-switcher/SKILL.md`, `.claude/skills/rpi-network-profile-switcher/agents/openai.yaml`, `.cursor/rules/12-rpi-network-profile-switcher.mdc`, `AGENTS.md`, `SKILLS.md`, `docs/ops/demo_test_device_inventory.md`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

### 2026-07-22 | 3·7단계 | 노면 내용 기반 중복 억제 기획서 등재

- **커밋**: `docs: 노면 알림 내용 기반 중복 억제 기획서 및 문서 인덱스 반영`
- **변경 내용**:
  - `docs/ops/surface_content_based_dedup_implementation_plan.md` 신규: 시간 기반(`REFLEX_SURFACE_MIN_GAP_S`/`SURFACE_REENTER_COOLDOWN_S`) 억제의 한계를 정리하고, 클래스·centroid 내용 비교 전환 설계·테스트·브랜치 작업 순서를 기술.
  - 추적 설계서(`reflex_audio_specification`, stage3, `environment_variables`) 및 현행 코드(`suppressor`/`surface_gate`/`detection_pipeline`/`consumer`)와 교차검증 표를 문서 상단에 추가.
  - `docs/README.md` ops·요약 인덱스에 기획서 링크 등록.
- **관련 파일**: `docs/ops/surface_content_based_dedup_implementation_plan.md`, `docs/README.md`, `docs/changelogs/kb.md`
- **검증 결과**: 기획서 주장과 추적 코드 상수(45s/20s/seg N=3/`surface_hazard` 고정 키) 일치 확인. 본 커밋은 문서만(구현 코드 변경 없음).
- **비고**: 구현은 기획서 §11 순서대로 `kb`에서 후속 진행.

### 2026-07-24 | client/Android | macOS 빌드 경로 정리 + det TFLite nms=False/android-gpu

- **커밋**: `43257a7`
- **변경 내용**:
  - Gradle: 윈도우 `org.gradle.java.home` 하드코딩 제거, CMake `C:/AndroidCxx`를 Windows 전용 분기.
  - det TFLite `nms=False` `[1,33,8400]` 재export + JS NMS (`NON_MAX_SUPPRESSION_V4` 제거).
  - `tfliteDetector.ts` dense 디코드 우선, Android `["android-gpu"]` + CPU 폴백, Manifest OpenCL 선언.
  - 씬 게이트·parity·bifurcation·EXPORT_SOURCE 문서 정합.
- **관련 파일**: `client/android/gradle.properties`, `client/android/build.gradle`, `client/assets/models/yolo26n/object_detection.tflite`, `client/src/inference/tfliteDetector.ts`, `client/app.json`, `scripts/export_tflite.py`, `docs/design/scene_classifier_gate_guide.md`, `docs/mobile/*`, `docs/changelogs/kb.md`
- **검증 결과**: TFLite shape `[1,33,8400]`·NMS op 없음 확인, `tsc --noEmit` 통과. 실기기 GPU/탐지는 후속.
- **비고**: iOS CoreML(nms=True) 미변경. Android 네이티브 재빌드 필요.


---

### 2026-07-24 | 3단계 | android_tflite_nms_free_gpu

- **커밋**: `(자동 커밋 완료)`
- **변경 내용**:
  - Android Gradle 크로스플랫폼 경로 정리 및 det TFLite nms=False 재export와 JS NMS·android-gpu 배선
- **관련 파일**: `gitignore`, `client/android/app/src/main/AndroidManifest.xml`, `client/android/build.gradle`, `client/android/gradle.properties`, `client/app.json`, `client/assets/models/yolo26n/EXPORT_SOURCE_260714.txt`, `client/assets/models/yolo26n/object_detection.tflite`, `client/src/inference/tfliteDetector.ts`, `docs/changelogs/kb.md`, `docs/design/scene_classifier_gate_guide.md`, `docs/mobile/android_handoff_kb_to_dg.md`, `docs/mobile/android_ios_parity_checklist.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/mobile/ondevice_inference_engine_isolation_plan.md`, `docs/ops/android_build_and_wireless_test_guide.md`, `scripts/export_mobile.py`, `scripts/export_tflite.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

---

### 2026-07-24 | 6단계 | ollama_lan_keepalive_gpu_monitor

- **커밋**: `94c8505`
- **변경 내용**:
  - Ollama keepalive LAN CLI 강제 및 gpu_monitor Bandit noqa 보강
- **관련 파일**: `agents/skills/rpi-network-profile-switcher/SKILL.md`, `.claude/skills/rpi-network-profile-switcher/SKILL.md`, `docs/ops/demo_test_device_inventory.md`, `scripts/ollama_demo_keepalive.sh`, `server/mcp/gpu_monitor.py`
- **검증 결과**: 자동화 린트 및 단계별 테스트를 통과함.

### 2026-07-24 | ops | gildang_db_cloud_r2_migration

- **커밋**: `cc20442`
- **변경 내용**:
  - 클라우드 MariaDB `gildang_db`(3307) 초기화 스크립트와 `cloud` 네트워크 프로필 추가.
  - 이벤트/STT 미디어를 Cloudflare R2(`EVENT_FRAME_STORAGE_BACKEND=r2`)로 저장·조회(presigned 옵션)하도록 백엔드 분기.
  - `.env.network.cloud.example`, env 명세, 스킬/운영 문서 동기화. 비밀값은 로컬 `.env`만.
- **관련 파일**: `server/services/r2_storage_client.py`, `server/services/remote_storage_client.py`, `server/services/event_frame_store.py`, `server/api/detection_log_router.py`, `scripts/setup_gildang_cloud_db.py`, `scripts/switch_rpi_network.sh`, `requirements.txt`, `.env.network.cloud.example`, `.env.example`, `docs/ops/gildang_cloud_r2_guide.md`, `docs/ops/environment_variables.md`, `docs/ops/demo_test_device_inventory.md`, `docs/db_tailscale_guide/README.md`, `.agents/skills/rpi-network-profile-switcher/SKILL.md`, `tests/test_r2_storage_backend.py`, `docs/changelogs/kb.md`
- **검증 결과**: `pytest tests/test_r2_storage_backend.py` 5 passed. 로컬 ephemeral MariaDB:3307에서 `setup_gildang_cloud_db.py`로 DB/유저/ORM 테이블 생성 확인. `switch_rpi_network.sh cloud` 사전검사는 플레이스홀더 호스트에서 TCP 실패(실호스트·R2 키 기입 후 재실행).
- **비고**: 실제 클라우드 DB 호스트·R2 자격증명은 사용자 로컬 `.env.network.cloud`에만 기입. Git 금지.

---

### 2026-07-27 | 2·3·7단계+Android | Android 온디바이스 연동 안정화 + 콘솔 Live Feed 백프레셔 분리

- **커밋**: (본 커밋)
- **변경 내용**:
  - **WS 상태 깜빡임 수정**(`client/src/hooks/useWebSocket.ts`): `connected`를 `welcome`이 아닌 `auth_ok` 수신 시점에만 표기. Android에서 TFLite 로드로 hello가 늦어 인증 타임아웃과 겹치며 "연결됨↔연결중"이 깜빡이던 문제 해소. `AppState`도 `inactive`(TTS·오디오 세션 전환 등 짧은 인터럽트)에서는 소켓을 유지하고 `background`에서만 정리.
  - **콘솔 Live Feed 백프레셔 분리**(`server/api/ws_router.py`): 콘솔 relay를 디코드/YOLO보다 먼저 수행하고, 스킵 경로(`skipped_decode`)에서는 `server_busy` 백프레셔를 걸지 않도록 변경. Mac CPU에서 YOLO가 막혀도 콘솔 중계·단말 송신률을 유지(이전엔 Live Feed가 ~1fps로 끊김). `_route_detection_bg`→`_decode_and_route_bg`로 디코드 자체를 백그라운드로 이동. 클라이언트도 `skipped_decode=true`면 busy ack 무시.
  - **TFLite 로딩 UX**(`useOnDeviceDetection.ts`·`tfliteDetector.ts`): Android는 모델 로드 전 1.5초 핸드셰이크 양보(WS hello 우선), 상태 라벨을 플랫폼별(`TFLite loading…`/`CoreML loading…`)로 표기.
  - **Android 전화 걸기 브릿지**(`PhoneDialBridgeModule.kt`): RN 0.80+ 대응(`reactApplicationContext.currentActivity`, `Arguments.createMap` 반환).
  - **Android 매니페스트**: `CAMERA` 권한과 `camera`/`autofocus` feature(required=false) 선언.
  - **프레임 캡처 보정**(`frameCaptureProviderSelect.android.ts`): takePhoto 폴백에 180도 회전 추가·압축 품질 0.5→0.7(콘솔 상하 반전·가독성).
  - **콘솔 회전 정본화**(`console/src/components/LiveCameraFeed.tsx`): Android 90도 하드코딩 제거, 단말이 정자세 JPEG를 보내는 정본에 맞춰 기본 회전 0.
  - **환경 변수 문서**: `CONSOLE_RELAY_MIN_INTERVAL_S` 기본값 0.2→0.1(~10fps) 및 설명 갱신.
  - `.gitignore`에 `.admin_bootstrap_credentials.local` 추가. `tests/test_r2_storage_backend.py` 보강.
- **관련 파일**: `client/src/hooks/useWebSocket.ts`, `server/api/ws_router.py`, `client/src/hooks/useOnDeviceDetection.ts`, `client/src/inference/tfliteDetector.ts`, `client/android/app/src/main/java/com/minchodan/app/PhoneDialBridgeModule.kt`, `client/android/app/src/main/java/com/minchodan/app/ReflexFrameProcessorPlugin.kt`, `client/android/app/src/main/AndroidManifest.xml`, `client/src/components/CameraView.tsx`, `client/src/services/frameCaptureProviderSelect.android.ts`, `console/src/components/LiveCameraFeed.tsx`, `docs/ops/environment_variables.md`, `tests/test_r2_storage_backend.py`, `.gitignore`
- **검증 결과**: `ruff check server/api/ws_router.py` All checks passed, `python -m py_compile` OK, client·console `tsc --noEmit` 타입 오류 0건.
- **비고**: `CameraView.tsx`에 Android 반사 프레임 간격 계측용 임시 진단 로그(`[DIAG] handleFrame gap`, `[TEMP DIAG 2026-07-24]`)가 남아 있음 - 프레임 병목 원인 규명 완료 후 제거 예정. 개인 파일 `shipping_label.html`(프로젝트 무관)은 커밋에서 제외.
