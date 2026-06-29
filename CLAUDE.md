# AI Coding & Communication Guidelines (Minchodan)

> [!IMPORTANT]
> **에이전트 시작 규칙 (Agent Startup Rule)**:
> 에이전트는 세션 시작 직후 다른 작업을 진행하기 전에 반드시 `view_file` 도구를 사용하여 프로젝트 루트의 [SKILLS.md](SKILLS.md) 파일을 열어 처음부터 끝까지 읽어야 합니다.
> Claude Code는 이 규칙과 지침을 세션 시작 시 자동으로 결합하기 위해 최상단의 `@SKILLS.md` 구문을 분석하여 컨텍스트에 주입합니다.

@SKILLS.md

이 문서는 **Minchodan** 프로젝트의 코딩 표준, 기술 스택, 디자인 시스템 및 AI 에이전트의 행동 지침을 정의합니다. 이 프로젝트에 참여하는 모든 AI 에이전트는 본 가이드라인을 반드시 준수해야 합니다.

> **작성일**: 2026-06-24
> **버전**: v0.2.0
> **설계 기준**: `docs/minchodan_design_note.md` (7단계 골격, 비전 설계서 v1.1)
> **코딩 패턴 기준**: [`docs/course_codebase_guide.md`](docs/course_codebase_guide.md) (수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준)

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
- LLM Orchestration: LangGraph, LangChain
- Local LLM/Embedding: Ollama (Gemma2:9b, Llava, nomic-embed-text)
- TTS: Kokoro-82M / Coqui (로컬)
- Message Bus: Redis (Streams + 컨텍스트 TTL)
- Image: OpenCV

### 클라이언트 (단말)

- Framework: React Native (iOS/Android)
- Camera: react-native-vision-camera
- Audio: Web Audio API, react-native-tts (예비)
- Accessibility: Haptics, announceForAccessibility

### 운영 콘솔

- Framework: React
- 구독: SSE 또는 WebSocket

### 인프라

- Container: Docker (Redis + Ollama + FastAPI)
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
  - `api/`: WebSocket `/ws/detect`, 세션 관리, 하트비트
  - `capture/`: 프레임 디코딩, 이중 스트림 분기
  - `detection/`: Yolo 26N - Object Detection, Yolo 26N - Segmentation, ByteTrack, Gates
  - `rag/`: Vector DB 구축(build/) 및 검색
  - `orchestration/`: LangGraph L1/L2/L3 (nodes/)
  - `tts/`: 실시간 TTS, 반사 클립 전송, 중복 억제
  - `bus/`: Redis Streams 인터페이스
  - `models/`: 모델 가중치 (git-ignore)
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

- **Coding Pattern Compliance**: 모든 Python 코드는 [`docs/course_codebase_guide.md`](docs/course_codebase_guide.md)의 코딩 패턴과 함수 시그니처 표준을 준수합니다. 특히 아래 항목은 필수 준수 대상입니다.
  - **파일 헤더 인코딩** (guide 3.1): 모든 Python 파일 첫 줄에 UTF-8 선언 및 `sys.stdout.reconfigure` 패턴 포함.
  - **임포트 순서** (guide 3.2): 표준 라이브러리 → 외부 라이브러리 → 로컬 모듈 순서로 정렬.
  - **경로 처리** (guide 3.3): `os.path.dirname(os.path.abspath(__file__))` 기반 절대 경로 사용. 하드코딩 경로 금지.
  - **환경 변수 로드** (guide 3.4): `load_dotenv()` + `os.getenv(..., default)` 패턴 적용.
  - **방어적 코딩** (guide 17.2): None 가드레일, API 키 검증, Mock 폴백, 예외 후 루프 유지, 방어적 dict 접근 5종 패턴.
  - **계층 분리** (guide 17.1): Router → Service → Repository 3계층 구조 (FastAPI 프로젝트).
- No Emojis: 코드 주석, 커밋 메시지, 문서 내부에서 이모지 사용 금지.
- Conciseness: 코드와 설명은 핵심 로직 위주로 간결하게 작성. 불필요한 서술 지양.
- Pathing: 항상 프로젝트 루트(`./Minchodan`) 기준의 경로 사용.
- UTF-8 Only: 문서, 스크립트, 설정 파일은 UTF-8로 저장.
- LF Policy: 추적되는 텍스트 파일은 LF 줄바꿈을 기준으로 유지합니다. Windows 로컬 Git은 `core.autocrlf=false`, `core.eol=lf`를 권장하며, macOS/Linux도 프로젝트 단위 설정이 필요하면 동일한 값을 사용합니다.
- Defensive Coding: 프레임 버퍼/디코딩 결과가 `None`인 경우 반드시 가드레일 처리. 무탐지 시 에러 없이 빈 리스트 반환(파이프라인 영속성).
- Dual Path Discipline: **반사 경로에는 LLM/RAG/실시간 TTS를 절대 경유시키지 않습니다.** 반사 음성은 사전합성 고정 클립만 사용합니다.
- Mermaid & Markdown Standards:
  - `mermaid` 노드 텍스트는 반드시 큰따옴표(`" "`)로 감싸야 하며, 줄바꿈은 `<br/>`를 사용한다. (`htmlLabels: true` 환경)
  - 모든 구조화된 데이터는 목록 대신 Markdown 표(Table)를 사용하고, 핵심 키워드는 굵게 표시한다.
  - 문서 상단에는 반드시 작성일(`YYYY-MM-DD`)과 버전 정보를 인용 블록(`>`)으로 포함한다.
  - 문서 내 이모지(Emoji) 사용은 절대 금지한다.

---

## 6. AI Communication Rules

- Language: 모든 아티팩트(Plan, Task, Walkthrough)와 대화 응답은 **한국어(Korean)**로 작성.
- Compliance: 작업 시작 전 항상 본 문서와 `docs/minchodan_design_note.md`를 읽고 프로젝트의 맥락을 파악.
- Artifact Focus: 아티팩트 생성 후 내용을 중복해서 설명하지 말고, 핵심적인 질문이나 결정 사항만 대화로 제시.

---

## 7. Git Branching Strategy

- Branches: 3계층 구조 (`master` 또는 `main` / `dev` / `[이니셜]`)를 엄격히 준수.
- Roles:
  - `master` 또는 `main`: 운영 기준선. 직접 push 금지.
  - `dev`: 통합 개발 및 머지 브랜치. 직접 push 금지.
  - `dg`, `jh`, `jy`, `kb`, `th`: 개별 개발 브랜치.
- Compliance: 상세 내용은 [`docs/git_branching_strategy.md`](docs/git_branching_strategy.md)를 참조하고, 모든 작업은 PR(Pull Request) 기반으로 진행.

---

## 8. Agent Skills (단계별 구현 가이드)

`.agents/skills/` 폴더에 7단계별 구현 스킬이 있습니다. 작업 시작 시 해당 스킬의 `SKILL.md`를 먼저 읽습니다.

| 스킬                        | 단계 | 경로                                        | 설명                                                                            |
| --------------------------- | ---- | ------------------------------------------- | ------------------------------------------------------------------------------- |
| `websocket-gateway`         | 1    | `.agents/skills/websocket-gateway/`         | FastAPI WebSocket 실시간 통신, Redis Streams                                    |
| `camera-frame-capture`      | 2    | `.agents/skills/camera-frame-capture/`      | 이중 캡처(반사 8~10fps/인지 1~2fps), base64 전송                                |
| `yolo-obstacle-detection`   | 3    | `.agents/skills/yolo-obstacle-detection/`   | Yolo 26N - Object Detection + Yolo 26N - Segmentation + ByteTrack + 이중 게이트 |
| `rag-knowledge-builder`     | 4    | `.agents/skills/rag-knowledge-builder/`     | Llava 캡셔닝 + nomic-embed + ChromaDB 오프라인 빌드                             |
| `rag-realtime-search`       | 5    | `.agents/skills/rag-realtime-search/`       | similarity_search(k=5) < 50ms, VectorDBFactory                                  |
| `llm-guidance-orchestrator` | 6    | `.agents/skills/llm-guidance-orchestrator/` | LangGraph L1/L2/L3, LLMClientFactory 핫스왑                                     |
| `tts-voice-streamer`        | 7    | `.agents/skills/tts-voice-streamer/`        | 이중 채널(반사=사전합성/인지=실시간 TTS), 선점                                  |

> 스킬은 `.agents/skills/` (opencode, 범용) 와 `.claude/skills/` (Claude Code) 양쪽에서 접근 가능합니다. `.claude/skills/`는 `.agents/skills/`의 junction 링크입니다.

---

## 9. 문서 인덱스

| 문서                 | 파일                                                               | 설명                                                              |
| -------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| 설계 노트 (원본)     | [`docs/minchodan_design_note.md`](docs/minchodan_design_note.md)   | 7단계 골격, 비전 v1.1 반영                                        |
| **코딩 패턴 기준**   | [`docs/course_codebase_guide.md`](docs/course_codebase_guide.md)   | **수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준 (필수 준수)** |
| 문서 인덱스          | [`docs/README.md`](docs/README.md)                                 | 문서 목록 및 권장 독해 순서                                       |
| 시스템 아키텍처      | [`docs/architecture.md`](docs/architecture.md)                     | 이중 경로 구조, 컴포넌트 상세, 데이터 계약                        |
| API 명세서           | [`docs/api_specification.md`](docs/api_specification.md)           | WebSocket `/ws/detect` 계약, 이벤트 타입                          |
| 테스트 명세서        | [`docs/test_specification.md`](docs/test_specification.md)         | 7단계별 완료 기준, 검증 매트릭스                                  |
| Git 브랜칭 전략      | [`docs/git_branching_strategy.md`](docs/git_branching_strategy.md) | 3계층 브랜치 구조, 작업 규칙                                      |
| 파이프라인 단계 설계 | [`docs/pipeline_stage_design.md`](docs/pipeline_stage_design.md)   | 7단계 run mode, 종단 지연 목표                                    |
| 에이전트 스킬 가이드 | [`SKILLS.md`](SKILLS.md)                                           | 시작 시퀀스, 문서 규칙, 금지 행위                                 |
