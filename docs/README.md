# Minchodan 문서 인덱스

> **작성일**: 2026-06-24
> **버전**: v0.8.0 (2026-07-02 문서 카테고리별 폴더 재구성)

---

## 폴더 구조

```
docs/
├── design/          # 핵심 시스템 설계서 (아키텍처, API, 파이프라인)
├── stage-guides/    # 구현 단계별 상세 설계서 (2·3·4·5·6단계)
├── mobile/          # 모바일 앱 구현 계획서 (iOS/Android)
├── research/        # 분석 보고서 및 Post-MVP 검토
├── ops/             # 운영·개발 환경 설정 및 절차
├── dev-guides/      # 코딩 표준, 에이전트 프롬프트, 참고 예시
└── changelogs/      # 팀원별 작업 변경 내역
```

---

## 1. design/ — 핵심 시스템 설계서

> 아키텍처·API·파이프라인 설계 등 시스템 전반을 정의하는 최상위 설계 문서.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| 설계 노트 (원본) | [minchodan_design_note.md](design/minchodan_design_note.md) | 7단계 골격, 비전 v1.1 반영 |
| 시스템 아키텍처 | [architecture.md](design/architecture.md) | 이중 경로 구조, 컴포넌트 상세, 데이터 계약, MCP 연동 |
| API 명세서 | [api_specification.md](design/api_specification.md) | WebSocket `/ws/detect` 계약, 이벤트 타입, 메시지 포맷 |
| 파이프라인 단계 설계 | [pipeline_stage_design.md](design/pipeline_stage_design.md) | 7단계 run mode, 종단 지연 목표, 추상화 지점 |
| 반사 오디오·햅틱 명세 | [reflex_audio_specification.md](design/reflex_audio_specification.md) | 반사 경로 비프음·진동 피드백 기술 명세 |
| 보행이론 인사이트 | [behavior_and_risk_insight.md](design/behavior_and_risk_insight.md) | 보행지도사 이론 기반 행동 패턴 및 위험도 게이트 정의 |

---

## 2. stage-guides/ — 구현 단계별 상세 설계서

> 서버 백엔드 각 구현 단계(2~6단계)의 상세 설계 및 구현 가이드.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| 1단계 WebSocket 설계서 | [stage1_websocket_design.md](stage-guides/stage1_websocket_design.md) | FastAPI 커넥션 생명주기, SessionManager, heartbeat 제어 |
| 2단계 캡처 설계서 | [stage2_capture_design.md](stage-guides/stage2_capture_design.md) | FastAPI 이중 스트림, asyncio.Queue, 디코딩 가드레일 |
| 3단계 탐지 설계서 | [stage3_detection_design.md](stage-guides/stage3_detection_design.md) | Mock 폴백, 이중 게이트(Reflex+Surface), 추상화 |
| 4·5단계 RAG 설계서 | [stage4_5_rag_design.md](stage-guides/stage4_5_rag_design.md) | Llava 캡셔닝 + nomic-embed + ChromaDB 빌드 설계 |
| 4·5단계 데이터 교체 가이드 | [stage4_5_data_replacement_guide.md](stage-guides/stage4_5_data_replacement_guide.md) | 실데이터 교체 및 RAG 재빌드 절차 |
| 4·5단계 디렉토리 가이드 | [stage4_5_directory_guide.md](stage-guides/stage4_5_directory_guide.md) | RAG 백엔드 폴더 및 파일 구조 |
| 4·5단계 구현 이력 로그 | [stage4_5_implementation_log.md](stage-guides/stage4_5_implementation_log.md) | 수정 행동 이력 및 의사결정 기록 |
| 4·5단계 테스트 가이드 | [stage4_5_test_guide.md](stage-guides/stage4_5_test_guide.md) | RAG 백엔드 단위 테스트 실행 가이드 |
| 6단계 오케스트레이션 설계서 | [stage6_orchestration_design.md](stage-guides/stage6_orchestration_design.md) | LangGraph L1/L2/L3, LLM 핫스왑, 가드레일 |

---

## 3. mobile/ — 모바일 앱 구현 계획서

> React Native 클라이언트 앱(iOS/Android) 구현 계획 및 설계서.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| 모바일 공통 계획서 | [mobile_app_implementation_plan.md](mobile/mobile_app_implementation_plan.md) | 플랫폼 공통 1+2단계 구현 계획 (iOS/Android 담당자 기준) |
| iOS 구현 설계서 | [mobile_ios_implementation_plan.md](mobile/mobile_ios_implementation_plan.md) | iOS 전용 1+2단계 구현 설계 (Mac mini 환경 기준) |
| Android 구현 설계서 | [mobile_android_implementation_plan.md](mobile/mobile_android_implementation_plan.md) | Android 전용 1+2단계 구현 설계 |
| 온디바이스 추론 엔진 격리 설계서 | [ondevice_inference_engine_isolation_plan.md](mobile/ondevice_inference_engine_isolation_plan.md) | YOLO26n + CoreML 이중 전략 기반 플랫폼별 추론 엔진 격리 (Post-MVP) |

---

## 4. research/ — 분석 보고서 및 Post-MVP 검토

> 성능·지연 분석, LLM 모델 검토, Post-MVP 아키텍처 타당성 등 기술 리서치 문서.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| 이중 Gemma4 지연 분석 | [dual_gemma4_latency_analysis.md](research/dual_gemma4_latency_analysis.md) | Gemma 4-E4B/E2B 이중 LLM 구성 성능 영향도 분석 |
| 지연 시간 영향도 분석 | [latency_impact_analysis.md](research/latency_impact_analysis.md) | 6단계 오케스트레이션 내 정밀 분석 LLM 추가 지연 영향도 |
| Gemini Fallback 검토 | [gemini_fallback_feasibility.md](research/gemini_fallback_feasibility.md) | Fallback LLM 대체 모델 비용 비교 및 최적 모델 선정 |
| Post-MVP 온디바이스 타당성 | [post_mvp_ondevice_feasibility.md](research/post_mvp_ondevice_feasibility.md) | 엣지 TFLite 추론 가능성 검증서 |
| Post-MVP 하이브리드 로드맵 | [post_mvp_hybrid_roadmap.md](research/post_mvp_hybrid_roadmap.md) | 하이브리드 온디바이스-서버 아키텍처 청사진 (post-MVP) |

---

## 5. ops/ — 운영·개발 환경 설정 및 절차

> 환경 변수 명세, 배포, 코드 품질 검증, 브랜치 전략, 테스트 명세 등 팀 운영 기준 문서.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| **환경 변수 명세서** | [environment_variables.md](ops/environment_variables.md) | **환경 변수 단일 명세 (3원화 해소), 카테고리별 분류** |
| **배포 가이드** | [deployment_guide.md](ops/deployment_guide.md) | **Docker 컨테이너 구성·배포 절차·TC-SMOKE-004 연동** |
| **실기기 무선 연동 가이드** | [wireless_test_guide.md](ops/wireless_test_guide.md) | **실기기(LTE) 및 Docker 연동 구조, 터널링, 트러블슈팅 상세 가이드** |
| **AI 모델 및 하드웨어 구성 지침** | [ai_model_hardware_setup.md](ops/ai_model_hardware_setup.md) | **GPU 요구사항(verify_gpu) 및 Ollama 로컬 모델(gemma4:e4b/llava/nomic) 풀링 가이드** |
| **Redis Streams 데이터 스키마 명세** | [redis_streams_schema.md](ops/redis_streams_schema.md) | **risk.events 스트림 페이로드 필드 정의 및 중복 알림 TTL 캐시 명세** |
| **모바일 빌드 트러블슈팅 가이드** | [mobile_build_troubleshooting.md](ops/mobile_build_troubleshooting.md) | **iOS 샌드박싱/Rosetta ffi 및 Android SDK/JDK 버전 충돌 해결 핸드북** |
| **코드 품질 검증 가이드** | [code_quality_guide.md](ops/code_quality_guide.md) | **Ruff+Bandit+mypy+jscpd+pip-audit 검증 파이프라인** |
| Git 브랜칭 전략 | [git_branching_strategy.md](ops/git_branching_strategy.md) | 3계층 브랜치 구조 (`main` / `dev` / 개인), PR 작업 규칙 |
| 테스트 명세서 | [test_specification.md](ops/test_specification.md) | 7단계별 완료 기준, 검증 매트릭스, 테스트 파일 매핑 |

---

## 6. dev-guides/ — 코딩 표준 및 참고 자료

> 코딩 패턴·함수 시그니처 표준, 에이전트 프롬프트 아카이브, 설계서 예시.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| **코딩 패턴 기준** | [course_codebase_guide.md](dev-guides/course_codebase_guide.md) | **수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준 (필수 준수)** |
| 에이전트 작업 지시서 | [antigravity_agent_prompt__4_5_final.md](dev-guides/antigravity_agent_prompt__4_5_final.md) | Antigravity 에이전트 4·5단계 RAG 작업 지시서 (최종 병합본) |
| 설계서 예시 | [신규_설계서_예시_2.md](dev-guides/신규_설계서_예시_2.md) | 장애물 탐지 설계 참고 예시 문서 |

---

## 7. changelogs/ — 팀원별 작업 변경 내역

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| Changelog 목록 | [changelogs/README.md](changelogs/README.md) | 팀원별 작업 내역, 날짜순 changelog 목록 |
| Changelog 템플릿 | [changelogs/TEMPLATE.md](changelogs/TEMPLATE.md) | 신규 changelog 작성 양식 |

---

## 권장 독해 순서

1. [`../README.md`](../README.md) — 프로젝트 개요 및 7단계 요약
2. [`design/minchodan_design_note.md`](design/minchodan_design_note.md) — 7단계 상세 설계 (백본)
3. [`../AGENTS.md`](../AGENTS.md) — 코딩·커뮤니케이션 규칙
4. [`dev-guides/course_codebase_guide.md`](dev-guides/course_codebase_guide.md) — **코딩 패턴·함수 시그니처 표준 (코딩 전 필수)**
5. [`ops/code_quality_guide.md`](ops/code_quality_guide.md) — **코드 품질 검증 파이프라인 (코딩 전 필수)**
6. [`design/architecture.md`](design/architecture.md) — 시스템 아키텍처 및 컴포넌트
7. [`design/api_specification.md`](design/api_specification.md) — WebSocket API 계약
8. [`ops/environment_variables.md`](ops/environment_variables.md) — **환경 변수 단일 명세 (설정 전 필수)**
9. [`ops/deployment_guide.md`](ops/deployment_guide.md) — **Docker 배포 절차 (배포 전 필수)**
10. [`design/pipeline_stage_design.md`](design/pipeline_stage_design.md) — 파이프라인 단계 설계
11. [`design/behavior_and_risk_insight.md`](design/behavior_and_risk_insight.md) — 보행이론 기반 위험도 정의
12. [`stage-guides/stage2_capture_design.md`](stage-guides/stage2_capture_design.md) — 2단계 구현 설계
13. [`stage-guides/stage3_detection_design.md`](stage-guides/stage3_detection_design.md) — 3단계 구현 설계
14. [`stage-guides/stage6_orchestration_design.md`](stage-guides/stage6_orchestration_design.md) — 6단계 오케스트레이션 설계
15. [`ops/test_specification.md`](ops/test_specification.md) — 검증 기준
16. [`research/post_mvp_hybrid_roadmap.md`](research/post_mvp_hybrid_roadmap.md) — **Post-MVP 하이브리드 로드맵**

---

## 현재 문서 기준선

- **이중 경로 원칙**(비협상): 반사 경로(즉시 경보, LLM/RAG/실시간 TTS 미경유, 사전합성 음성)와 인지 경로(mid/low 상세 가이드, LangGraph + RAG + 실시간 TTS)를 물리 분리합니다.
- **모바일은 thin client**입니다. 카메라 캡처와 음성/햡틱 재생만 담당하며, 모든 추론은 GPU 서버에서 수행합니다.
- **3단계는 듀얼헤드 + 이중 게이트**입니다. Yolo 26N - Object Detection(Reflex Gate) + Yolo 26N - Segmentation(Surface Gate)가 모두 룰베이스로 동작하며 LLM을 경유하지 않습니다.
- **반사 음성은 사전합성 고정 클립**(앱 번들)입니다. 실시간 TTS 합성은 금지하며, 반사 음성은 인지 음성을 중단시키고 선점 재생합니다.
- **Vector DB는 ChromaDB 로컬 파일 기반**(`data/chroma_db/`)이며, `VectorDBFactory`로 Qdrant 핫스왑을 대비합니다.
- **LLM은 로컬 Ollama(gemma4:e4b)** 기본이며, `LLMClientFactory(BaseChatModel)`로 gpt-4o-mini 핫스왑을 대비합니다.
