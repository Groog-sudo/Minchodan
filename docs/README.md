# Minchodan 문서 인덱스

> **작성일**: 2026-06-24
> **버전**: v0.1.0

## 문서 목록

| 문서 | 파일 | 설명 |
| --- | --- | --- |
| 설계 노트 (원본) | [minchodan_design_note.md](minchodan_design_note.md) | 7단계 골격, 11필드 표준 양식, 비전 v1.1 반영 |
| 에이전트 가이드 | [AGENTS.md](AGENTS.md) | 코딩·커뮤니케이션 규칙, 기술 스택, 디자인 시스템 |
| 시스템 아키텍처 | [architecture.md](architecture.md) | 이중 경로 구조, 컴포넌트 상세, 데이터 계약, 환경 변수 |
| API 명세서 | [api_specification.md](api_specification.md) | WebSocket `/ws/detect` 계약, 이벤트 타입, 메시지 포맷 |
| 테스트 명세서 | [test_specification.md](test_specification.md) | 7단계별 완료 기준, 검증 매트릭스, 테스트 파일 매핑 |
| Git 브랜칭 전략 | [git_branching_strategy.md](git_branching_strategy.md) | 3계층 브랜치 구조(master/dev/개인), 작업 규칙 |
| 파이프라인 단계 설계 | [pipeline_stage_design.md](pipeline_stage_design.md) | 7단계 run mode, 종단 지연 목표, 추상화 지점 |
| 3단계 탐지 설계서 | [stage3_detection_design.md](stage3_detection_design.md) | 3단계 백엔드 FastAPI 구현 설계 (Mock 폴백, 이중 게이트, 추상화) |
| 디렉토리 구조 | [../directory_Structure.md](../directory_Structure.md) | 계획된 물리적 폴더 구조 |
| 에이전트 스킬 | [../skills.md](../skills.md) | 시작 시퀀스, 문서 규칙, 금지 행위 |

---

## 권장 독해 순서

1. [`../README.md`](../README.md) - 프로젝트 개요 및 7단계 요약
2. [`minchodan_design_note.md`](minchodan_design_note.md) - 7단계 상세 설계 (백본)
3. [`AGENTS.md`](AGENTS.md) - 코딩·커뮤니케이션 규칙
4. [`course_codebase_guide.md`](course_codebase_guide.md) - **코딩 패턴·함수 시그니처 표준 (코딩 전 필수 참조)**
5. [`architecture.md`](architecture.md) - 시스템 아키텍처 및 컴포넌트
6. [`api_specification.md`](api_specification.md) - WebSocket API 계약
7. [`pipeline_stage_design.md`](pipeline_stage_design.md) - 파이프라인 단계 설계
8. [`stage3_detection_design.md`](stage3_detection_design.md) - 3단계 백엔드 구현 설계 (코딩 에이전트 필수 참조)
9. [`test_specification.md`](test_specification.md) - 검증 기준

---

## 현재 문서 기준선

- **이중 경로 원칙**(비협상): 반사 경로(즉시 경보, LLM/RAG/실시간 TTS 미경유, 사전합성 음성)와 인지 경로(mid/low 상세 가이드, LangGraph + RAG + 실시간 TTS)를 물리 분리합니다.
- **모바일은 thin client**입니다. 카메라 캡처와 음성/햡틱 재생만 담당하며, 모든 추론은 GPU 서버에서 수행합니다.
- **3단계는 듀얼헤드 + 이중 게이트**입니다. YOLO26 Detection(Reflex Gate) + SegFormer(Surface Gate)가 모두 룰베이스로 동작하며 LLM을 경유하지 않습니다.
- **노면 클래스는 분리**(C2)합니다. `braille normal/damaged`, `sidewalk normal/damaged`, `crosswalk`, `roadway`, `caution`(stairs/manhole/grating)을 독립 클래스로 학습합니다.
- **반사 음성은 사전합성 고정 클립**(앱 번들)입니다. 실시간 TTS 합성은 금지하며, 반사 음성은 인지 음성을 중단시키고 선점 재생합니다.
- **Whisper는 STT 전용**이며 7단계(가이드 출력)에 등장하지 않습니다. 사용자 음성 명령(STT) 경로는 본 골격 범위 밖입니다.
- **Vector DB는 ChromaDB 로컬 파일 기반**(`data/chroma_db/`)이며, `VectorDBFactory`로 Qdrant 핫스왑을 대비합니다.
- **LLM은 로컬 Ollama(Gemma2:9b)** 기본이며, `LLMClientFactory(BaseChatModel)`로 gpt-4o-mini 핫스왑을 대비합니다.
- **학습 환경은 Blackwell sm_120 / CUDA 12.8 + cu128 PyTorch 휠**이 필요합니다. 11.8/12.1 휠은 silent CPU 폴백이 발생합니다.
- **로컬 WiFi MVP**에서는 즉시 경보도 서버 추론에 의존합니다. 단말 on-device 반사 레이어는 post-MVP입니다.

---

## 1주차 미결정 7개 (잠정 기본값)

| 항목 | MVP 잠정 | 대안/승급 |
| --- | --- | --- |
| Vector DB | ChromaDB | Qdrant |
| 임베딩 | nomic-embed-text | gemini-embedding-001 |
| L2 LLM | Gemma2:9b | gpt-4o-mini |
| On-device 추론 | 없음 (thin client) | 반사 레이어 (post-MVP) |
| 통신 프로토콜 | WS·REST·SSE·Redis | WebRTC/gRPC 등 |
| TTS | Kokoro/Coqui | OpenAI TTS |
| RDB | (미정) | MariaDB/PostgreSQL |
