# Minchodan AI Agent Skills

## MANDATORY STARTUP SEQUENCE

이 프로젝트에서 작업을 시작하기 전, 아래 순서를 **반드시** 따르십시오.
건너뛰거나 생략하는 것은 허용되지 않습니다.

---

### Step 1: README 읽기

**파일:** [`README.md`](README.md)

README를 처음부터 끝까지 읽고 다음을 파악합니다:

- 프로젝트 목적 및 핵심 기능 (시각장애인 가이드독 AI, 이중 경로)
- 7단계 파이프라인 요약 및 완료 기준 (KPI)
- 기술 스택 및 디렉토리 구조
- 빠른 시작 및 환경 변수
- 팀 분업 및 문서 인덱스

> README는 프로젝트의 **기준선(baseline)** 역할을 합니다. 모든 작업은 이 기준선을 확인한 뒤 시작합니다.

---

### Step 2: 설계 노트 읽기

**파일:** [`docs/minchodan_design_note.md`](docs/minchodan_design_note.md)

7단계 골격 설계 노트를 읽고 다음을 숙지합니다:

- 7단계 파이프라인의 11개 필드 표준 양식
- 각 단계의 핵심 절차, 활용 스택, 데이터 인터페이스, 의존성·예외
- 분업 제안 및 MVP 스코프
- 비전 설계서 v1.1 반영 사항 (YOLO26, SegFormer, 이중 게이트, 노면 클래스 분리)

---

### Step 3: AGENTS.md 읽기

**파일:** [`docs/AGENTS.md`](docs/AGENTS.md)

AGENTS.md를 읽고 다음을 숙지합니다:

- 기술 스택 (FastAPI, YOLO26, SegFormer, LangGraph, Ollama)
- 코딩 규칙 (이모지 금지, 간결한 코드, 프로젝트 루트 기준 경로)
- 커뮤니케이션 규칙 (한국어 응답 필수)
- Mermaid 및 Markdown 표준

---

### Step 4: 작업 유형별 추가 문서 참조

작업 유형에 따라 아래 문서를 추가로 읽습니다:

| 작업 유형 | 참조 문서 |
| --- | --- |
| 시스템 아키텍처 변경 | [`docs/architecture.md`](docs/architecture.md) |
| 테스트 작성/수정 | [`docs/test_specification.md`](docs/test_specification.md) |
| 파이프라인 단계 설계 | [`docs/pipeline_stage_design.md`](docs/pipeline_stage_design.md) |
| 브랜치/PR 작업 | [`docs/git_branching_strategy.md`](docs/git_branching_strategy.md) |
| 문서 전체 인덱스 | [`docs/README.md`](docs/README.md) |

단계별 구현 작업은 아래 스킬 인덱스를 참조합니다.

---

## SKILL 인덱스 (.agents/skills/)

각 스킬은 단계별 구현 가이드(SKILL.md)와 상세 레퍼런스(references/implementation_detail.md)를 포함합니다. 작업 시작 시 해당 스킬의 `SKILL.md`를 먼저 읽습니다.

| 스킬 | 단계 | 경로 | 설명 |
| --- | --- | --- | --- |
| `websocket-gateway` | 1 | `.agents/skills/websocket-gateway/` | FastAPI WebSocket 실시간 통신, Redis Streams |
| `camera-frame-capture` | 2 | `.agents/skills/camera-frame-capture/` | 이중 캡처(반사 8~10fps/인지 1~2fps), base64 전송 |
| `yolo-obstacle-detection` | 3 | `.agents/skills/yolo-obstacle-detection/` | YOLO26 + SegFormer + ByteTrack + 이중 게이트 |
| `rag-knowledge-builder` | 4 | `.agents/skills/rag-knowledge-builder/` | Llava 캡셔닝 + nomic-embed + ChromaDB 오프라인 빌드 |
| `rag-realtime-search` | 5 | `.agents/skills/rag-realtime-search/` | similarity_search(k=5) < 50ms, VectorDBFactory |
| `llm-guidance-orchestrator` | 6 | `.agents/skills/llm-guidance-orchestrator/` | LangGraph L1/L2/L3, LLMClientFactory 핫스왑 |
| `tts-voice-streamer` | 7 | `.agents/skills/tts-voice-streamer/` | 이중 채널(반사=사전합성/인지=실시간 TTS), 선점 |

---

## CORE PROJECT CONTEXT

Minchodan은 **시각장애인 보행 보조 스마트 가이드독 AI 플랫폼**입니다.

핵심 구조:

| 계층 | 역할 |
| --- | --- |
| `server/` | GPU 추론 서버 (FastAPI, WebSocket, 탐지, RAG, LangGraph, TTS) |
| `client/` | React Native thin client (카메라 캡처, 음성/햡틱 재생) |
| `console/` | React 운영자 모니터링 콘솔 |
| `data/` | 학습·RAG 데이터 (원본, 프레임, 캡션, ChromaDB, 반사 클립) |
| `training/` | 모델 학습 (오프라인, YOLO26, SegFormer) |
| `docker/` | Docker 구성 (Redis + Ollama + FastAPI) |

이중 경로 원칙 (비협상):

- **반사 경로**: 고위험 즉시 경보. LLM/RAG/실시간 TTS 미경유. 사전합성 음성 선점 재생. 목표 <300ms.
- **인지 경로**: mid/low 위험 상세 가이드. Redis Streams  LangGraph L1/L2/L3 + RAG  실시간 TTS.

---

## DOCUMENTATION & FORMATTING RULES

프로젝트 내 모든 문서(Markdown 등)를 작성하거나 수정할 때, 에이전트는 다음의 내용 및 형식 규칙을 엄격히 준수해야 합니다. 기존 문서의 통일성을 유지하기 위한 필수 지침입니다.

1. **언어 및 어조 (Language & Tone)**
   - 문서의 모든 설명은 **한국어(존댓말/경어체)** 로 작성합니다. (코드 블록, 변수명 등은 예외)
   - 문장은 간결하고 전문적인 용어를 사용하여 명확하게 전달합니다.

2. **문서 구조 및 마크다운 (Markdown Structure)**
   - **위계질서**: 제목은 `#`, 섹션은 `##`, 하위 섹션은 `###`을 사용합니다.
   - **구분선**: 주요 섹션 사이에는 반드시 구분선(`---`)을 삽입하여 가독성을 높입니다.
   - **구조화**: 비교 데이터, 설정값, 히스토리 등은 표(Table) 형식을 우선 사용합니다.
   - **강조**: 핵심 개념, 버전, 수치 등 중요한 부분은 굵게(`**텍스트**`) 처리합니다.

3. **다이어그램 (Mermaid Charts)**
   - 아키텍처, 타임라인, 프로세스 설명 시 `mermaid` 코드 블록을 적극 활용합니다.
   - **구문 오류 방지**: 노드 텍스트에 공백이나 특수문자가 포함될 경우 반드시 큰따옴표(`"텍스트"`)로 감쌉니다.
   - **가독성 확보**: 텍스트가 길어질 경우 `<br/>` 태그를 적절히 삽입하여 줄바꿈을 유도합니다. (`htmlLabels: true` 설정 적용 중)

4. **메타데이터 패턴**
   - 새 문서 작성 시 상단에 작성일, 버전 등 메타데이터를 인용 블록(`>`)으로 명시하는 기존 패턴을 유지합니다.
   - (예: `> **작성일**: 2026-06-24`)

5. **금지 사항 재강조**
   - 문서 내 **이모지(Emoji)** 사용은 어떤 경우에도 허용되지 않습니다.

---

## PROHIBITED ACTIONS

다음 행위는 **절대 금지**입니다:

1. 코드 주석, 커밋 메시지, 문서 내 이모지 사용
2. 영어로 대화 응답이나 아티팩트 작성 (코드/변수명 제외)
3. 사전 허가 없이 새로운 Python 라이브러리 추가 (`requirements.txt` 변경)
4. `.env` 파일의 실제 값을 코드나 문서에 노출
5. 반사 경로에 LLM/RAG/실시간 TTS를 경유시키는 설계 (비협상 원칙 위반)
6. `master` 브랜치에 직접 push
7. README의 최근 변경 사항을 업데이트하지 않고 주요 작업 완료 처리

---

## WORKFLOW CHECKLIST

세션 시작 시 다음을 확인합니다:

- [ ] `README.md` 읽기 완료
- [ ] `docs/minchodan_design_note.md` 읽기 완료
- [ ] `docs/AGENTS.md` 읽기 완료
- [ ] 작업 유형에 맞는 추가 문서 참조 완료
- [ ] 현재 프로젝트가 GPU/CUDA 환경에서 실행 가능한 상태인지 확인
- [ ] 작업 완료 후 README 최근 변경 사항 업데이트 여부 확인
