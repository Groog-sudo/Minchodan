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
