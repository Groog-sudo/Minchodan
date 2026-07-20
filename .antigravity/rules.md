# Minchodan Antigravity Workspace Rules

> **본 파일은 Antigravity IDE/CLI 자동 로드용 요약본입니다** (12,000자 캡 대응).
> 규칙 정본(단일 진실 원천)은 루트 `AGENTS.md`입니다. 본 요약본과 정본이 충돌하면 `AGENTS.md`가 우선합니다.
> 편집은 반드시 `AGENTS.md`에서 하고, pre-commit 훅이 본 요약본의 핵심 섹션 포함 여부를 검증합니다.

---

## 1. 프로젝트 컨텍스트

- **개념**: 시각장애인 보행 보조 스마트 가이드독 AI 플랫폼
- **핵심 원칙(비협상)**: 이중 경로 물리 분리 (반사=즉시 경보 / 인지=상세 가이드)
- **클라이언트**: React Native thin client (카메라 캡처 + 음성/햅틱 재생만)
- **서버**: GPU 서버에서 모든 추론 수행 (FastAPI + WebSocket)
- **UI**: 종단 사용자는 음성만, React 콘솔은 운영자 모니터링용

---

## 2. 기술 스택 (요약)

| 계층 | 스택 |
| :--- | :--- |
| 서버 언어/프레임워크 | Python 3.13, FastAPI, uvicorn, asyncio |
| 탐지 | Yolo 26N Object Detection (NMS-free, sm_120), Yolo 26N Segmentation, ByteTrack |
| 벡터 DB | ChromaDB (로컬 파일, `data/chroma_db/`) |
| LLM 오케스트레이션 | LangGraph (raw 클라이언트: SimpleOllamaClient/SimpleOpenAIClient/SimpleGeminiClient, LangChain 래퍼 미사용, 메시지 스키마는 langchain_core.messages) |
| 로컬 LLM/임베딩 | Ollama (gemma4-e4b, nomic-embed-text), Gemini API (gemini-2.5-flash-lite, VLM 캡셔닝) |
| TTS | Supertonic 3 (기본, ONNX), edge-tts, Piper/pyttsx3 (핫스왑 폴백) |
| STT | faster-whisper-small (hotwords 바이어싱, 서버 기동 시 프리로드) |
| Navigation | TMAP 보행자 경로 API + NavigationManager |
| 메시지 버스 | Redis (Streams + 컨텍스트 TTL) |
| 클라이언트 | React Native, react-native-vision-camera (Frame Processor), CoreML/TFLite (온디바이스 반사), expo-audio, expo-speech |
| 인프라 | Docker (Redis+MariaDB+FastAPI, Ollama는 호스트 로컬), RTX 5090 최대(Blackwell sm_120), Ubuntu/Windows=PyTorch 2.13+cu130, macOS=PyTorch 2.13 MPS/CPU |

---

## 3. 이중 경로 원칙 (비협상)

| 경로 | 역할 | 목표 지연 | 사용 기술 |
| :--- | :--- | :--- | :--- |
| **반사** | 고위험 즉시 경보 | <300ms | 사전합성 고정 음성 클립, 온디바이스 탐지 |
| **인지** | mid/low 위험 상세 가이드 | 지연 허용 | LangGraph L1/L2/L3 + RAG + 실시간 TTS |

- **반사 경로에는 LLM/RAG/실시간 TTS를 절대 경유시키지 않습니다.** 반사 음성은 사전합성 고정 클립만 사용합니다.
- **이중 경로 분리 강제**: `server/detection/gates/`에서 오케스트레이션/RAG/TTS 모듈 임포트 금지.

---

## 4. 코드 구조 (주요 디렉토리)

| 디렉토리 | 역할 |
| :--- | :--- |
| `server/api/` | WebSocket `/ws/detect`, REST 라우터(auth/admin/user/detection_log/stt/monitor) |
| `server/capture/` | 프레임 디코딩, 이중 스트림 분기 |
| `server/detection/` | Object Detection, Segmentation, ByteTrack, Gates |
| `server/rag/` | Vector DB 빌드/검색 |
| `server/orchestration/` | LangGraph L1/L2/L3 (nodes/) |
| `server/tts/` | 실시간 TTS, 반사 클립, 중복 억제 |
| `server/services/` | Service 계층 (Router-Service-Repository 3계층) |
| `server/stt/` | faster-whisper STT, 음성 명령-LLM 브릿지 |
| `server/navigation/` | TMAP 보행자 경로, NavigationManager |
| `server/mcp/` | MCP 연동 (GPU 모니터, Slack, LangSmith 등) |
| `client/` | React Native thin client |
| `console/` | React 운영자 콘솔 |
| `.agents/skills/` | 단계별 구현 스킬 정본 (1~7단계 + 보조) |

---

## 5. 코딩 규칙 (필수 준수)

모든 Python 코드는 `docs/dev-guides/course_codebase_guide.md`의 패턴을 따릅니다.

- **파일 헤더**: 첫 줄에 UTF-8 선언 및 `sys.stdout.reconfigure(encoding="utf-8")` 패턴.
- **임포트 순서**: 표준 라이브러리 → 외부 라이브러리 → 로컬 모듈.
- **경로 처리**: `os.path.dirname(os.path.abspath(__file__))` 또는 `Path(__file__)` 기반. 하드코딩 금지.
- **환경 변수**: `load_dotenv()` + `os.getenv(..., default)` 패턴.
- **방어적 코딩**: None 가드레일, API 키 검증, Mock 폴백, 예외 후 루프 유지, 방어적 dict 접근.
- **계층 분리**: Router → Service → Repository 3계층 (FastAPI).
- **이모지 금지**: 코드 주석, 커밋 메시지, 문서 내 이모지 사용 금지.
- **간결성**: 핵심 로직 위주. 요청 범위 밖 리팩터링/추상화/주석 추가 금지.
- **LF 정책**: 텍스트 파일은 LF 줄바꿈 유지. Windows는 `core.autocrlf=false`, `core.eol=lf`.
- **프레임 버퍼 None 가드**: 디코딩 결과가 None이면 가드레일 처리, 무탐지 시 빈 리스트 반환.

### 코드 품질 검증 (커밋/푸시/PR 시 자동)

- **pre-commit**: Ruff(린트+포맷+보안 1차) + Bandit(보안 심층)
- **pre-push**: mypy(타입) + jscpd(중복) + pip-audit(CVE)
- **GitHub Actions**: PR 게이트
- **자동 수정**: `ruff format . ; ruff check --fix .`
- **전체 검사**: `ruff check . ; bandit -r server/ scripts/ ; mypy server/ ; jscpd ; pip-audit -r requirements.txt`

---

## 6. 커뮤니케이션 규칙

- **언어**: 모든 아티팩트(Plan, Task, Walkthrough)와 대화 응답은 한국어(존댓말)로 작성. 코드/변수명 제외.
- **작업 전 준비**: `docs/design/minchodan_design_note.md`와 본 규칙을 읽고 맥락 파악.
- **아티팩트**: 생성 후 내용 중복 설명 금지, 핵심 질문/결정만 대화로 제시.

---

## 7. Git 브랜칭 전략

- **3계층 구조**: `main`(운영 기준선, 직접 push 금지) / `dev`(통합 개발) / 개인 이니셜(`dg`, `jh`, `jy`, `kb`, `th`)
- 상세: `docs/ops/git_branching_strategy.md`

---

## 8. 금지 행위 (절대)

1. 코드 주석, 커밋 메시지, 문서 내 이모지 사용
2. 영어로 대화 응답/아티팩트 작성 (코드/변수명 제외)
3. 사전 허가 없이 새 Python 라이브러리 추가 (`requirements.txt` 변경)
4. `.env` 실제 값을 코드/문서에 노출
5. 반사 경로에 LLM/RAG/실시간 TTS 경유 (비협상 원칙 위반)
6. `main` 브랜치 직접 push
7. 주요 작업 완료 후 `docs/changelogs/[이니셜].md` changelog 누락

---

## 9. 문서 규칙

- **위계**: `#`(제목) / `##`(섹션) / `###`(하위). 섹션 사이 `---` 구분선.
- **표 우선**: 구조화 데이터는 목록 대신 Markdown 표. 핵심 키워드는 굵게.
- **Mermaid**: 노드 텍스트는 큰따옴표(`" "`), 줄바꿈은 `<br/>`.
- **메타데이터**: 문서 상단에 작성일/버전을 인용 블록(`>`)으로.
- **문서 동기화**: 아키텍처/버전 변경 시 관련 문서 모두 교차 검증 후 일괄 업데이트.

---

## 10. 단계별 스킬 인덱스

작업 시작 시 해당 스킬의 `.agents/skills/<skill>/SKILL.md`를 먼저 읽습니다.

| 스킬 | 단계 | 경로 |
| :--- | :--- | :--- |
| websocket-gateway | 1 | `.agents/skills/websocket-gateway/` |
| camera-frame-capture | 2 | `.agents/skills/camera-frame-capture/` |
| yolo-obstacle-detection | 3 | `.agents/skills/yolo-obstacle-detection/` |
| rag-knowledge-builder | 4 | `.agents/skills/rag-knowledge-builder/` |
| rag-realtime-search | 5 | `.agents/skills/rag-realtime-search/` |
| llm-guidance-orchestrator | 6 | `.agents/skills/llm-guidance-orchestrator/` |
| tts-voice-streamer | 7 | `.agents/skills/tts-voice-streamer/` |
| xcode-build-management | - | `.agents/skills/xcode-build-management/` |
| auto-publish-work | - | `.agents/skills/auto-publish-work/` |
| react-doctor | - | `.agents/skills/react-doctor/` |
| integration-test-orchestrator | - | `.agents/skills/integration-test-orchestrator/` |

> 스킬 정본은 `.agents/skills/`(Git 추적). `.claude/skills/`는 동일 내용 사본(미러). 수정 시 정본 우선, 사본에 동일 반영.

---

## 11. 시작 시퀀스 (세션 진입 시)

1. `README.md` 읽기 (프로젝트 목적, 7단계 파이프라인, KPI)
2. `docs/design/minchodan_design_note.md` 읽기 (7단계 골격 설계)
3. `AGENTS.md` 읽기 (정본 규칙 - 본 요약본의 원본)
4. 작업 유형별 추가 문서 참조 (`docs/README.md` 인덱스 확인)

---

## 12. 핵심 문서 인덱스

| 문서 | 파일 |
| :--- | :--- |
| 코딩 패턴 기준 | `docs/dev-guides/course_codebase_guide.md` |
| 코드 품질 검증 | `docs/ops/code_quality_guide.md` |
| 시스템 아키텍처 | `docs/design/architecture.md` |
| API 명세서 | `docs/design/api_specification.md` |
| 환경 변수 명세서 | `docs/ops/environment_variables.md` |
| 다중 에이전트 셋업 | `docs/dev-guides/multi_agent_setup.md` |
| 스킬 가이드 | `SKILLS.md` |
