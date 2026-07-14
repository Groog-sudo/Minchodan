# AI Coding & Communication Guidelines (Minchodan)

> [!IMPORTANT]
> **에이전트 시작 규칙 (Agent Startup Rule)**:
> 에이전트는 세션 시작 직후 다른 작업을 진행하기 전에 반드시 `view_file` 도구를 사용하여 프로젝트 루트의 [SKILLS.md](SKILLS.md) 파일을 열어 처음부터 끝까지 읽어야 합니다.
> 에이전트 도구는 이 규칙과 지침을 세션 시작 시 자동으로 결합하기 위해 최상단의 `@SKILLS.md` 구문을 분석하여 컨텍스트에 주입합니다.

@SKILLS.md

이 문서는 **Minchodan** 프로젝트의 코딩 표준, 기술 스택, 디자인 시스템 및 AI 에이전트의 행동 지침을 정의합니다. 이 프로젝트에 참여하는 모든 AI 에이전트는 본 가이드라인을 반드시 준수해야 합니다.

> **작성일**: 2026-06-24
> **버전**: v0.3.4 (2026-07-14 코드-문서 정합성 교차 검증 기반 수정: §2 LLM 오케스트레이션 명세 정정(SimpleGeminiClient 추가, langchain_core.messages 사용 명시), §4 server/ 구조에 services/stt/navigation/mcp 4폴더 추가, models/ Git 추적 정책 정정(object_detection.pt 추적 / det_best/segbest git-ignore) + 기존 v0.3.3 이력 유지: §2 스택 명세화, Llava→Gemini VLM 캡셔닝, edge-tts 추가, react-native-tts → expo-speech 갱신)
> **설계 기준**: `docs/design/minchodan_design_note.md` (7단계 골격, 비전 설계서 v1.1)
> **코딩 패턴 기준**: [`docs/dev-guides/course_codebase_guide.md`](docs/dev-guides/course_codebase_guide.md) (수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준)
> **코드 품질 검증 기준**: [`docs/ops/code_quality_guide.md`](docs/ops/code_quality_guide.md) (Ruff+Bandit+mypy+jscpd+pip-audit 파이프라인)

---

## 1. Project Context

- 개념: 시각장애인 보행 보조 스마트 가이드독 AI 플랫폼
- 핵심 원칙: **이중 경로 물리 분리** (반사=즉시 경보 / 인지=상세 가이드)
- 클라이언트: React Native thin client (카메라 캡처 + 음성/햡틱 재생만)
- 서버: GPU 서버에서 모든 추론 수행 (FastAPI + WebSocket)
- 사용자 인터페이스: 종단 사용자는 음성만, React 콘솔은 운영자 모니터링용

---

## 2. Technical Stack

### 서버 (GPU 추론)

- Language: Python 3.13
- Framework: FastAPI, uvicorn, asyncio
- Detection: Ultralytics Yolo 26N - Object Detection (NMS-free, sm_120 최적화)
- Segmentation: Ultralytics Yolo 26N - Segmentation
- Tracking: ByteTrack
- Vector DB: ChromaDB (로컬 파일 기반, `data/chroma_db/`)
- LLM Orchestration: LangGraph (LLM 호출 클라이언트는 raw 구현: SimpleOllamaClient/SimpleOpenAIClient/SimpleGeminiClient. LangChain 래퍼(LLMChain 등) 미사용이나, 메시지 스키마는 langchain_core.messages 사용. RAG 검색 계층(server/rag/)은 ChromaDB 래퍼(langchain_community.vectorstores) 사용)
- Local LLM/Embedding: Ollama (gemma4-e4b, nomic-embed-text), Gemini API (gemini-2.5-flash-lite, 4단계 VLM 캡셔닝)
- TTS: Supertonic (기본, ONNX 로컬), edge-tts (한국어 자연도 우선), Piper / pyttsx3 (핫스왑 폴백)
- STT (부가, 음성 명령): faster-whisper (기본 small, hotwords 바이어싱, 서버 기동 시 프리로드)
- Navigation (부가, GPS 길안내): TMAP 보행자 경로 API + NavigationManager
- Message Bus: Redis (Streams + 컨텍스트 TTL)
- Image: OpenCV

### 클라이언트 (단말)

- Framework: React Native (iOS/Android)
- Camera: react-native-vision-camera (Frame Processor 기반 연속 캡처)
- On-device Inference: CoreML(iOS) / TFLite(Android) - 반사 경로 온디바이스 탐지
- Audio: expo-audio (단말 재생 계층, Web Audio API 아님), expo-speech (실제 사용, react-native-tts 미사용). STT 녹음 구간은 AVAudioSession voiceChat(AEC) 전환(`AudioSessionBridge`)
- Map Panel (운영자/데모): react-native-webview + TMap JS API (`NavMapPanel.tsx`)
- Accessibility: Haptics, announceForAccessibility

### 운영 콘솔

- Framework: React
- 구독: SSE 또는 WebSocket

### 인프라

- Container: Docker (Redis + MariaDB + FastAPI), Ollama는 호스트 로컬 프로세스
- GPU: CUDA 12.8 + cu128 PyTorch 휠 (Blackwell sm_120 전제)

---

## 3. Design System

- Theme: 접근성 우선 다크/라이트 대응 (시각장애인 운영자 콘솔)
- Typography: 큰 폰트, 고대비 텍스트 (접근성 기준)
- Responsiveness: 모바일 단말(카메라 프리뷰)과 운영자 콘솔(모니터링) 분리
- Audio First: 종단 사용자 UI는 음성·햅틱이 1순위, 화면은 운영자용

---

## 4. Code Structure

- `server/`: GPU 추론 서버 (FastAPI)
  - `api/`: WebSocket `/ws/detect`, 세션 관리, 하트비트, REST 라우터(auth/admin/user/detection_log/stt/monitor)
  - `capture/`: 프레임 디코딩, 이중 스트림 분기
  - `detection/`: Yolo 26N - Object Detection, Yolo 26N - Segmentation, ByteTrack, Gates
  - `rag/`: Vector DB 구축(build/) 및 검색
  - `orchestration/`: LangGraph L1/L2/L3 (nodes/)
  - `tts/`: 실시간 TTS, 반사 클립 전송, 중복 억제
  - `bus/`: Redis Streams 인터페이스
  - `db/`: RDB ORM/DTO/DDL (사용자, 단말, 관리자, 감사 로그)
  - `models/`: 사전학습 가중치 Git 추적 (yolo26n/object_detection.pt), 커스텀 학습 가중치(det_best_*.pt/segbest.pt)는 git-ignore
  - `services/`: 비즈니스 로직 Service 계층 (Router-Service-Repository 3계층 중 Service). 관리자/사용자/단말/탐지로그 서비스, 이벤트 프레임 저장
  - `stt/`: faster-whisper STT 서비스, 음성 명령-LLM 브릿지, 연락처 저장
  - `navigation/`: TMAP 보행자 경로 API, NavigationManager, 내비게이션 전용 FastAPI(`/ws`)
  - `mcp/`: MCP 연동 모듈 (GPU 모니터, Slack 알림, LangSmith 트레이서, 접근성 시뮬레이터, 오디오 검증, 캐시 모니터)
- `client/`: React Native thin client
- `console/`: React 운영자 모니터링 콘솔
- `data/`: 학습·RAG 데이터
- `training/`: 모델 학습 (오프라인)
- `scripts/`: 유틸리티 스크립트
- `tests/`: 7단계별 검증 테스트
- `docker/`: Docker 구성
- `docs/`: 설계 문서 및 가이드
- `.agents/skills/`: 단계별 구현 스킬 (1~7단계)

---

## 5. AI Coding Rules

- **Coding Pattern Compliance**: 모든 Python 코드는 [`docs/dev-guides/course_codebase_guide.md`](docs/dev-guides/course_codebase_guide.md)의 코딩 패턴과 함수 시그니처 표준을 준수합니다. 특히 아래 항목은 필수 준수 대상입니다.
  - **파일 헤더 인코딩** (guide 3.1): 모든 Python 파일 첫 줄에 UTF-8 선언 및 `sys.stdout.reconfigure` 패턴 포함.
  - **임포트 순서** (guide 3.2): 표준 라이브러리 → 외부 라이브러리 → 로컬 모듈 순서로 정렬.
  - **경로 처리** (guide 3.3): Python 실행 경로는 `os.path.dirname(os.path.abspath(__file__))`로 계산하고 하드코딩하지 않음.
  - **환경 변수 로드** (guide 3.4): `load_dotenv()` + `os.getenv(..., default)` 패턴 적용.
  - **방어적 코딩** (guide 17.2): None 가드레일, API 키 검증, Mock 폴백, 예외 후 루프 유지, 방어적 dict 접근 5종 패턴.
  - **계층 분리** (guide 17.1): Router → Service → Repository 3계층 구조 (FastAPI 프로젝트).
- **Code Quality Verification**: 코드 품질 검증은 [`docs/ops/code_quality_guide.md`](docs/ops/code_quality_guide.md)의 파이프라인을 준수합니다. 커밋·푸시·PR 시 자동 실행됩니다.
  - **검증 도구**: Ruff(린트+포맷+보안 1차), Bandit(보안 심층 2차), mypy(타입 점진적), jscpd(중복 검출), pip-audit(의존성 CVE).
  - **실행 시점 분리**: pre-commit(Ruff+Bandit, 빠름) / pre-push(mypy+jscpd+pip-audit, 느림) / GitHub Actions(PR 게이트).
  - **자동 수정 명령**: `ruff format . ; ruff check --fix .` (커밋 전 실행 권장).
  - **전체 검사 명령**: `ruff check . ; bandit -r server/ scripts/ ; mypy server/ ; jscpd ; pip-audit -r requirements.txt`.
  - **이중 경로 분리 강제**: 반사 경로(`server/detection/gates/`)에서 오케스트레이션/RAG/TTS 모듈 임포트 금지. 현재 코드 리뷰로 강제, 후속 커스텀 Ruff 룰로 자동 탐지 예정.
- No Emojis: 코드 주석, 커밋 메시지, 문서 내부에서 이모지 사용 금지.
- Conciseness: 코드와 설명은 핵심 로직 위주로 간결하게 작성. 불필요한 서술 지양.
- Pathing: 문서·명령은 프로젝트 루트(`./Minchodan`) 기준의 상대경로를 사용하고, Python 실행 경로는 `__file__` 기반으로 계산합니다. 환경별 절대경로 하드코딩은 금지합니다.
- UTF-8 Only: 문서, 스크립트, 설정 파일은 UTF-8로 저장.
- LF Policy: 추적되는 텍스트 파일은 LF 줄바꿈을 기준으로 유지합니다. Windows 로컬 Git은 `core.autocrlf=false`, `core.eol=lf`를 권장하며, macOS/Linux도 프로젝트 단위 설정이 필요하면 동일한 값을 사용합니다.
- Defensive Coding: 프레임 버퍼/디코딩 결과가 `None`인 경우 반드시 가드레일 처리. 무탐지 시 에러 없이 빈 리스트 반환(파이프라인 영속성).
- Dual Path Discipline: **반사 경로에는 LLM/RAG/실시간 TTS를 절대 경유시키지 않습니다.** 반사 음성은 사전합성 고정 클립만 사용합니다.
- Document Synchronization & Cross-Validation: 구현 과정에서 아키텍처/오픈소스 버전이 변경될 경우, Git 커밋/푸시 전에 반드시 관련 문서들을 최신화합니다. 이때 한 문서만 수정하지 않고, 관련된 모든 문서들과 내용이 모순되지 않는지 전체적으로 교차 검증(Cross-validation)하여 누락 없이 일괄 업데이트합니다.
- Educational Vibecoding (Hard/Vibe Split): 3단계 YOLO 탐지, 분할(Segmentation) 등 핵심 로직 구현 시, 담당자가 직접 타이핑하며 체화할 "하드코딩(Hardcode) 영역"과 에이전트가 완성할 "바이브코딩(Vibecode) 영역"을 명확히 분리합니다. 하드코딩 영역에는 발표/면접 방어를 위한 기술적 의도나 파이프라인 설계 이유를 `# 💡 [면접 대비 주석]` 형태로 반드시 첨부해야 합니다.
- Mermaid & Markdown Standards:
  - `mermaid` 노드 텍스트는 반드시 큰따옴표(`" "`)로 감싸야 하며, 줄바꿈은 `<br/>`를 사용한다. (`htmlLabels: true` 환경)
  - 모든 구조화된 데이터는 목록 대신 Markdown 표(Table)를 사용하고, 핵심 키워드는 굵게 표시한다.
  - 문서 상단에는 반드시 작성일(`YYYY-MM-DD`)과 버전 정보를 인용 블록(`>`)으로 포함한다.
  - 문서 내 이모지(Emoji) 사용은 절대 금지한다.

---

## 6. AI Communication Rules

- Language: 모든 아티팩트(Plan, Task, Walkthrough)와 대화 응답은 **한국어(Korean)**로 작성.
- Compliance: 작업 시작 전 항상 본 문서와 `docs/design/minchodan_design_note.md`를 읽고 프로젝트의 맥락을 파악.
- Artifact Focus: 아티팩트 생성 후 내용을 중복해서 설명하지 말고, 핵심적인 질문이나 결정 사항만 대화로 제시.

---

## 7. Git Branching Strategy

- Branches: 3계층 구조 (`master` 또는 `main` / `dev` / `[이니셜]`)를 엄격히 준수.
- Roles:
  - `master` 또는 `main`: 운영 기준선. 직접 push 금지.
  - `dev`: 통합 개발 및 머지 브랜치. 로컬 직접 병합 후 push 허용.
  - `dg`, `jh`, `jy`, `kb`, `th`: 개별 개발 브랜치.
- Compliance: 상세 내용은 [`docs/ops/git_branching_strategy.md`](docs/ops/git_branching_strategy.md)를 참조하고, 모든 작업은 직접 병합 및 push 기반으로 진행.

---

## 8. Agent Skills (단계별 구현 가이드)

`.agents/skills/` 폴더에 7단계별 구현 스킬이 있습니다. 작업 시작 시 해당 스킬의 `SKILL.md`를 먼저 읽습니다.

| 스킬                        | 단계 | 경로                                        | 설명                                                                            |
| --------------------------- | ---- | ------------------------------------------- | ------------------------------------------------------------------------------- |
| `websocket-gateway`         | 1    | `.agents/skills/websocket-gateway/`         | FastAPI WebSocket 실시간 통신, Redis Streams                                    |
| `camera-frame-capture`      | 2    | `.agents/skills/camera-frame-capture/`      | 이중 캡처(반사 8~10fps/인지 1~2fps), base64 전송                                |
| `yolo-obstacle-detection`   | 3    | `.agents/skills/yolo-obstacle-detection/`   | Yolo 26N - Object Detection + Yolo 26N - Segmentation + ByteTrack + 이중 게이트 |
| `rag-knowledge-builder`     | 4    | `.agents/skills/rag-knowledge-builder/`     | Gemini 캡셔닝 + nomic-embed + ChromaDB 오프라인 빌드                             |
| `rag-realtime-search`       | 5    | `.agents/skills/rag-realtime-search/`       | similarity_search(k=5) < 50ms, VectorDBFactory                                  |
| `llm-guidance-orchestrator` | 6    | `.agents/skills/llm-guidance-orchestrator/` | LangGraph L1/L2/L3, LLMClientFactory 핫스왑                                     |
| `tts-voice-streamer`        | 7    | `.agents/skills/tts-voice-streamer/`        | 이중 채널(반사=사전합성/인지=실시간 TTS), 선점                                  |
| `xcode-build-management`    | -    | `.agents/skills/xcode-build-management/`    | iOS Xcode 프로젝트 빌드, 시뮬레이터 관리 및 Swift/SwiftUI 코드 리팩토링/디버깅 |
| `auto-publish-work`         | -    | `.agents/skills/auto-publish-work/`         | 작업 완료 후 문서 정합성 분석, 린트/테스트 검증, Changelog 작성 및 Git 자동 마감 |

> 스킬은 `.agents/skills/` (opencode, 범용) 와 `.claude/skills/` (Claude Code) 양쪽에서 접근 가능합니다. `.claude/skills/`는 `.agents/skills/`의 junction 링크입니다.

---

## 9. 문서 인덱스

> 문서 전체 목록은 [`docs/README.md`](docs/README.md)를 참조하십시오. 하단은 AI 에이전트 작업 시 빈번하게 참조하는 핵심 문서만 간추린 목록입니다.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| 설계 노트 (원본) | [`docs/design/minchodan_design_note.md`](docs/design/minchodan_design_note.md) | 7단계 골격, 비전 v1.1 반영 |
| **코딩 패턴 기준** | [`docs/dev-guides/course_codebase_guide.md`](docs/dev-guides/course_codebase_guide.md) | **수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준 (필수 준수)** |
| **코드 품질 검증 가이드** | [`docs/ops/code_quality_guide.md`](docs/ops/code_quality_guide.md) | **Ruff+Bandit+mypy+jscpd+pip-audit 린트·보안·중복·CVE 검증** |
| 문서 인덱스 | [`docs/README.md`](docs/README.md) | 문서 목록 및 권장 독해 순서 |
| 시스템 아키텍처 | [`docs/design/architecture.md`](docs/design/architecture.md) | 이중 경로 구조, 컴포넌트 상세, 데이터 계약, MCP 연동 |
| API 명세서 | [`docs/design/api_specification.md`](docs/design/api_specification.md) | WebSocket `/ws/detect` 계약, 이벤트 타입 |
| 테스트 명세서 | [`docs/ops/test_specification.md`](docs/ops/test_specification.md) | 7단계별 완료 기준, 검증 매트릭스 |
| Git 브랜칭 전략 | [`docs/ops/git_branching_strategy.md`](docs/ops/git_branching_strategy.md) | 3계층 브랜치 구조, 작업 규칙 |
| 파이프라인 단계 설계 | [`docs/design/pipeline_stage_design.md`](docs/design/pipeline_stage_design.md) | 7단계 run mode, 종단 지연 목표 |
| **환경 변수 명세서** | [`docs/ops/environment_variables.md`](docs/ops/environment_variables.md) | **환경 변수 단일 명세 (3원화 해소)** |
| **배포 가이드** | [`docs/ops/deployment_guide.md`](docs/ops/deployment_guide.md) | **Docker 컨테이너 구성·배포 절차·TC-SMOKE-004** |
| 2단계 캡처 설계서 | [`docs/stage-guides/stage2_capture_design.md`](docs/stage-guides/stage2_capture_design.md) | 2단계 백엔드 FastAPI 구현 설계 (이중 스트림, asyncio.Queue) |
| 3단계 탐지 설계서 | [`docs/stage-guides/stage3_detection_design.md`](docs/stage-guides/stage3_detection_design.md) | 3단계 백엔드 FastAPI 구현 설계 |
| 6단계 오케스트레이션 설계서 | [`docs/stage-guides/stage6_orchestration_design.md`](docs/stage-guides/stage6_orchestration_design.md) | 6단계 종합 회피 가이드 생성 설계 |
| 보행이론 인사이트 | [`docs/design/behavior_and_risk_insight.md`](docs/design/behavior_and_risk_insight.md) | 보행지도사 이론 기반 행동 패턴 및 위험도 게이트 정의 |
| **Post-MVP 하이브리드 로드맵** | [`docs/research/post_mvp_hybrid_roadmap.md`](docs/research/post_mvp_hybrid_roadmap.md) | **하이브리드 온디바이스-서버 아키텍처 청사진 (post-MVP)** |
| 에이전트 스킬 가이드 | [`SKILLS.md`](SKILLS.md) | 시작 시퀀스, 문서 규칙, 금지 행위 |
