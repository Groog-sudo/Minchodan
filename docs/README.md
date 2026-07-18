# Minchodan 문서 인덱스

> **작성일**: 2026-07-11
> **버전**: v0.13.12 (2026-07-17 MariaDB·미디어 저장 API Tailscale 팀 연결 가이드 확장)

## 문서 목록

| 문서                 | 파일                                                   | 설명                                                              |
| -------------------- | ------------------------------------------------------ | ----------------------------------------------------------------- |
| 설계 노트 (원본)     | [design/minchodan_design_note.md](design/minchodan_design_note.md)   | 7단계 골격, 11필드 표준 양식, 비전 v1.1 반영                      |
| **코딩 패턴 기준**   | [dev-guides/course_codebase_guide.md](dev-guides/course_codebase_guide.md)   | **수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준 (필수 준수)** |
| **코드 품질 검증 가이드** | [ops/code_quality_guide.md](ops/code_quality_guide.md) | **Ruff+Bandit+mypy+jscpd+pip-audit 린트·보안·중복·CVE 검증 (코딩 전 필수 참조)** |
| 에이전트 가이드      | [../AGENTS.md](../AGENTS.md)                           | 코딩·커뮤니케이션 규칙, 기술 스택, 디자인 시스템, 문서 인덱스     |
| 시스템 아키텍처      | [design/architecture.md](design/architecture.md)                     | 이중 경로 구조, 컴포넌트 상세, 데이터 계약, 환경 변수, MCP 연동   |
| API 명세서           | [design/api_specification.md](design/api_specification.md)           | WebSocket `/ws/detect` 계약, 이벤트 타입, 메시지 포맷             |
| 테스트 명세서        | [ops/test_specification.md](ops/test_specification.md)         | 7단계별 완료 기준, 검증 매트릭스, 테스트 파일 매핑                |
| Git 브랜칭 전략      | [ops/git_branching_strategy.md](ops/git_branching_strategy.md) | 3계층 브랜치 구조(`master` 또는 `main` / `dev` / 개인), 작업 규칙 |
| 파이프라인 단계 설계 | [design/pipeline_stage_design.md](design/pipeline_stage_design.md)   | 7단계 run mode, 종단 지연 목표, 추상화 지점                       |
| **환경 변수 명세서** | [ops/environment_variables.md](ops/environment_variables.md)   | **환경 변수 단일 명세 (3원화 해소), 카테고리별 분류**             |
| **배포 가이드**      | [ops/deployment_guide.md](ops/deployment_guide.md)             | **Docker 컨테이너 구성·배포 절차·TC-SMOKE-004 연동**              |
| **개인 설정 파일 Git 제외 가이드** | [ops/local_private_config_guide.md](ops/local_private_config_guide.md) | **`Copy_` 접두어 기반 로컬 개인 설정 복사본 제외 규칙** |
| **DB·미디어 API Tailscale 연결 가이드** | [db_tailscale_guide/README.md](db_tailscale_guide/README.md) | **외부 공개 가능한 플레이스홀더 기반 연결·진단 절차. 실접속 정보 문서는 Git 제외 후 내부 공유** |
| **LLM 협업 작업 분담 가이드** | [dev-guides/llm_collaboration_workflow.md](dev-guides/llm_collaboration_workflow.md) | **담당자 직접 작성 영역과 LLM 보조 영역 분리 기준** |
| **YOLO/TTS MVP 다음 작업 계획** | [research/yolo_tts_mvp_next_steps.md](research/yolo_tts_mvp_next_steps.md) | **th 브랜치 다음 세션 작업 순서와 직접 코딩 항목** |
| **dev 통합 개선 실행 계획서** | [ops/dev_8b2f606_improvement_plan.md](ops/dev_8b2f606_improvement_plan.md) | **dev 8b2f606 감사 기반 P0/P1 개선 순서와 완료 기준** |
| **프로젝트 보완점: Mitos (정정본)** | [research/mitos_improvement_roadmap.md](research/mitos_improvement_roadmap.md) | **실기기 검증 기반 안전성·음성 UX·신뢰성·제품화 보완 로드맵. v0.3.0 코드 대조 검증 기록 포함 (루트에서 이동)** |
| **백엔드 DB 아키텍처** | [design/backend_db_architecture.md](design/backend_db_architecture.md) | **SQLAlchemy 비동기 엔진 및 3계층 아키텍처 설계** |
| 2단계 캡처 설계서     | [stage-guides/stage2_capture_design.md](stage-guides/stage2_capture_design.md)   | 2단계 백엔드 FastAPI 구현 설계 (이중 스트림, asyncio.Queue, 디코딩 가드레일) |

| 3단계 탐지 설계서     | [stage-guides/stage3_detection_design.md](stage-guides/stage3_detection_design.md) | 3단계 백엔드 FastAPI 구현 설계 (Mock 폴백, 이중 게이트, 추상화) |
| 6단계 오케스트레이션 설계서 | [stage-guides/stage6_orchestration_design.md](stage-guides/stage6_orchestration_design.md) | 6단계 종합 회피 가이드 생성 설계 (LangGraph, LLM 핫스왑, 가드레일) |
| **Post-MVP 하이브리드 로드맵** | [research/post_mvp_hybrid_roadmap.md](research/post_mvp_hybrid_roadmap.md) | **하이브리드 온디바이스-서버 아키텍처 청사진 (post-MVP), 엣지 반사+클라우드 인지 이중 루프** |
| **iOS/Android 이원화 통합 계약서** | [mobile/ios_android_bifurcation_contract.md](mobile/ios_android_bifurcation_contract.md) | **파일 소유권·인터페이스 계약·인프라 거버넌스로 병합 충돌 방지 (kb/dg2 병합 시뮬레이션 근거)** |
| 보행이론 인사이트 보고서 | [design/behavior_and_risk_insight.md](design/behavior_and_risk_insight.md) | 보행지도사 이론 기반 행동 패턴 및 위험도 게이트 정의              |
| **변경 사항 기록**   | [changelogs/README.md](changelogs/README.md)           | 팀원별 작업 내역, 날짜순 changelog 목록                           |
| Changelog 템플릿     | [changelogs/TEMPLATE.md](changelogs/TEMPLATE.md)       | 신규 changelog 작성 양식                                           |
| 디렉토리 구조        | [Directory_Structure.md](Directory_Structure.md)       | 계획된 물리적 폴더 구조                                           |
| 에이전트 스킬        | [../SKILLS.md](../SKILLS.md)                           | 시작 시퀀스, 문서 규칙, 금지 행위                                 |

---

## AI 프롬프트 사용

```
docs/
├── design/          # 핵심 시스템 설계서 (아키텍처, API, 파이프라인)
├── stage-guides/    # 구현 단계별 상세 설계서 (2·3·4·5·6단계)
├── mobile/          # 모바일 앱 구현 계획서 (iOS/Android)
├── research/        # 분석 보고서 및 Post-MVP 검토
├── ops/             # 운영·개발 환경 설정 및 절차
│   └── reports/     # 단발성 운영 보고서
├── db_tailscale_guide/ # 외부 공개용 가이드와 Git 제외 내부 연결 문서
├── dev-guides/      # 코딩 표준 및 개발 참고 자료
│   ├── prompts/     # 1회성 에이전트 작업 프롬프트 아카이브
│   ├── templates/   # 설계서 예시/템플릿
│   └── integration/ # 콘솔·서버 통합 지침서
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
| **실내 오탐 완화 2차 설계서** | [indoor_fp_mitigation_design.md](design/indoor_fp_mitigation_design.md) | **물리적 타당성 필터 + VNClassifyImageRequest 씬 분류기 게이트 설계** |
| **씬 분류기 게이트 해설(팀 학습용)** | [scene_classifier_gate_guide.md](design/scene_classifier_gate_guide.md) | **VNClassifyImageRequest 게이트 기법을 배경·원리·코드 위치·FAQ로 풀어 쓴 학습용 문서** |
| **반사 위험도 SSOT 계약 (초안)** | [risk_ssot_contract.md](design/risk_ssot_contract.md) | **서버/단말 고위험 클래스·confidence 단일 계약, 회귀 테스트(`tests/test_risk_ssot.py`) 연동 (TH·Mobile 합의 전 초안)** |

---

## 2. stage-guides/ — 구현 단계별 상세 설계서

> 서버 백엔드 각 구현 단계(2~6단계)의 상세 설계 및 구현 가이드.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| 1단계 WebSocket 설계서 | [stage1_websocket_design.md](stage-guides/stage1_websocket_design.md) | FastAPI 커넥션 생명주기, SessionManager, heartbeat 제어 |
| 2단계 캡처 설계서 | [stage2_capture_design.md](stage-guides/stage2_capture_design.md) | FastAPI 이중 스트림, asyncio.Queue, 디코딩 가드레일 |
| 3단계 탐지 설계서 | [stage3_detection_design.md](stage-guides/stage3_detection_design.md) | Mock 폴백, 이중 게이트(Reflex+Surface), 추상화 |
| 4·5단계 RAG 설계서 | [stage4_5_rag_design.md](stage-guides/stage4_5_rag_design.md) | Gemini VLM 캡셔닝(최초 계획 Llava에서 전환) + nomic-embed + ChromaDB 빌드 설계 |
| 4·5단계 데이터 교체 가이드 | [stage4_5_data_replacement_guide.md](stage-guides/stage4_5_data_replacement_guide.md) | 실데이터 교체 및 RAG 재빌드 절차 |
| 4·5단계 디렉토리 가이드 | [stage4_5_directory_guide.md](stage-guides/stage4_5_directory_guide.md) | RAG 백엔드 폴더 및 파일 구조 |
| 4·5단계 구현 이력 로그 | [stage4_5_implementation_log.md](stage-guides/stage4_5_implementation_log.md) | 수정 행동 이력 및 의사결정 기록 |
| 4·5단계 테스트 가이드 | [stage4_5_test_guide.md](stage-guides/stage4_5_test_guide.md) | RAG 백엔드 단위 테스트 실행 가이드 |
| 6단계 오케스트레이션 설계서 | [stage6_orchestration_design.md](stage-guides/stage6_orchestration_design.md) | LangGraph L1/L2/L3, LLM 핫스왑, 가드레일 |
| 7단계 TTS 설계서 | [stage7_tts_design.md](stage-guides/stage7_tts_design.md) | 이중 채널(반사=사전합성/인지=실시간 TTS), 선점 재생 설계 |
| STT 통합 가이드 | [stage_stt_integration_guide.md](stage-guides/stage_stt_integration_guide.md) | `stt_audio -> STT -> Bridge -> TTS -> guide` 흐름, 메시지 계약, 테스트 체크리스트 |
| **3단계 YOLO 코드 리뷰** | [stage3_detection_code_review.md](stage-guides/stage3_detection_code_review.md) | **3단계 탐지 파이프라인 코드 분석, 준수 점검, 종합 평가 및 개선 제안** |

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
| SenseVoice-Small STT 검토 | [sensevoice_stt_feasibility.md](research/sensevoice_stt_feasibility.md) | 음성 명령(STT) 경로용 SenseVoice-Small 도입 정당성(지연·로딩·한국어 정확도) |
| **프로젝트 보완점: Mitos (정정본)** | [mitos_improvement_roadmap.md](research/mitos_improvement_roadmap.md) | **안전성·음성 UX·신뢰성·검증 체계·제품화 보완 로드맵. v0.3.0에서 코드 대조 검증 기록(§10) 추가, 루트 `PROJECT_IMPROVEMENTS_MITOS.md`에서 이동** |
| **실외 안내 고도화 로드맵** | [outdoor_guidance_refinement_roadmap.md](research/outdoor_guidance_refinement_roadmap.md) | **실외 테스트 기반 반사 과다·LLM 지연·안내 품질 3-Phase 로드맵 (v1.1: class-agnostic 게이트 정합)** |
| **실사용 필드 테스트 개선 계획** | [field_test_improvement_plan.md](research/field_test_improvement_plan.md) | **실기기 실외 보행 테스트 피드백(S1~S8) 기반 P0/P1/P2 개선 구현 계획. 억제 재무장·큐 최신성·소형 객체 사각지대·후속 행동 안내·발화 가치 게이트·계단 인식 (v1.1: 정합성 이슈 3건 정정 편입)** |

---

## 5. ops/ — 운영·개발 환경 설정 및 절차

> 환경 변수 명세, 배포, 코드 품질 검증, 브랜치 전략, 테스트 명세 등 팀 운영 기준 문서.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| **환경 변수 명세서** | [environment_variables.md](ops/environment_variables.md) | **환경 변수 단일 명세 (3원화 해소), 카테고리별 분류** |
| **배포 가이드** | [deployment_guide.md](ops/deployment_guide.md) | **Docker 컨테이너 구성·배포 절차·TC-SMOKE-004 연동** |
| **DB·미디어 API Tailscale 연결 가이드** | [db_tailscale_guide/README.md](db_tailscale_guide/README.md) | **외부 공개 가능한 플레이스홀더 기반 연결·진단 절차. 실접속 정보 문서는 Git 제외 후 내부 공유** |
| **Android 빌드 및 무선 테스트 가이드** | [android_build_and_wireless_test_guide.md](ops/android_build_and_wireless_test_guide.md) | **Android 개발 빌드, adb reverse, 무선 연동 기본 절차** |
| **Android WiFi/USB 이중 접속** | [android_wifi_usb_transport.md](ops/android_wifi_usb_transport.md) | **평상시 WiFi vs 개발 USB 토글, 노트북 핫스팟 `192.168.137.1` 실측** |
| **Android 무선 테스트 가이드 v2** | [android_wireless_test_guide_v2.md](ops/android_wireless_test_guide_v2.md) | **실기기 테스트 중 Metro 연결 끊김, adb 데드락, reverse 복구 절차 상세판** |
| **Android STT/실내 탐지 인식 문제 리포트** | [android_stt_recognition_issue_report.md](ops/android_stt_recognition_issue_report.md) | **STT 인식 실패 + 실내 탐지 저하 종합 원인 분석 및 개선 방향** |
| **실기기 무선 연동 가이드** | [wireless_test_guide.md](ops/wireless_test_guide.md) | **실기기(LTE) 및 Docker 연동 구조, 터널링, 트러블슈팅 상세 가이드** |
| **AI 모델 및 하드웨어 구성 지침** | [ai_model_hardware_setup.md](ops/ai_model_hardware_setup.md) | **GPU 요구사항(verify_gpu) 및 호스트 로컬 Ollama 모델(gemma4:e4b/nomic) 풀링 가이드** |
| **Redis Streams 데이터 스키마 명세** | [redis_streams_schema.md](ops/redis_streams_schema.md) | **risk.events 스트림 페이로드 필드 정의 및 중복 알림 TTL 캐시 명세** |
| **모바일 빌드 트러블슈팅 가이드** | [mobile_build_troubleshooting.md](ops/mobile_build_troubleshooting.md) | **iOS 샌드박싱/Rosetta ffi 및 Android SDK/JDK 버전 충돌 해결 핸드북** |
| **코드 품질 검증 가이드** | [code_quality_guide.md](ops/code_quality_guide.md) | **Ruff+Bandit+mypy+jscpd+pip-audit 검증 파이프라인** |
| **개인 설정 파일 Git 제외 가이드** | [local_private_config_guide.md](ops/local_private_config_guide.md) | **`Copy_` 접두어 기반 로컬 개인 설정 복사본 제외 규칙** |
| **iOS CoreML ANE 벤치마크** | [ondevice_coreml_benchmark.md](ops/ondevice_coreml_benchmark.md) | **CoreML ANE 온디바이스 추론 지연 벤치마크 및 서버 KPI 비교** |
| **모델 클래스별 검증 보고서** | [model_class_validation_report.md](ops/model_class_validation_report.md) | **YOLO26n 33클래스(탐지29+세그멘테이션4) 샘플 이미지 탐지 검증 결과** |
| Git 브랜칭 전략 | [git_branching_strategy.md](ops/git_branching_strategy.md) | 3계층 브랜치 구조 (`main` / `dev` / 개인), PR 작업 규칙 |
| 테스트 명세서 | [test_specification.md](ops/test_specification.md) | 7단계별 완료 기준, 검증 매트릭스, 테스트 파일 매핑 |
| **dev 통합 개선 실행 계획서** | [dev_8b2f606_improvement_plan.md](ops/dev_8b2f606_improvement_plan.md) | **dev 8b2f606 감사 결과 기반 P0/P1 개선 순서와 완료 기준 (Mitos 로드맵과 교차 참조)** |

---

## 6. dev-guides/ — 코딩 표준 및 참고 자료

> 코딩 패턴·함수 시그니처 표준, 에이전트 프롬프트 아카이브, 설계서 예시, 통합 지침서.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| **코딩 패턴 기준** | [course_codebase_guide.md](dev-guides/course_codebase_guide.md) | **수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준 (필수 준수)** |
| 에이전트 작업 지시서 | [antigravity_agent_prompt__4_5_final.md](dev-guides/prompts/antigravity_agent_prompt__4_5_final.md) | Antigravity 에이전트 4·5단계 RAG 작업 지시서 (최종 병합본) |
| 설계서 예시 | [신규_설계서_예시_2.md](dev-guides/templates/신규_설계서_예시_2.md) | 장애물 탐지 설계 참고 예시 문서 |
| **관제 UI 연동 지침서** | [관제_UI_및_시나리오_연동_지침서.md](dev-guides/integration/관제_UI_및_시나리오_연동_지침서.md) | **관제 콘솔 실시간 지도 iframe 임베딩 및 대화형 길안내 시나리오 연동 가이드** |
| **서버 통합 기술 지침서** | [서버_및_시스템_통합_기술_지침서.md](dev-guides/integration/서버_및_시스템_통합_기술_지침서.md) | **네비게이션 백엔드 모듈 배치, 의존성, 핵심 5대 소스코드 결합 사양** |

---

## 7. ops/reports/ — 단발성 운영 보고서

> 운영 규칙 그 자체가 아니라, 특정 통합 작업의 결과를 남기는 보고서 모음.

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |

---

## 8. changelogs/ — 팀원별 작업 변경 내역

| 문서 | 파일 | 설명 |
| :--- | :--- | :--- |
| Changelog 목록 | [changelogs/README.md](changelogs/README.md) | 팀원별 작업 내역, 날짜순 changelog 목록 |
| Changelog 템플릿 | [changelogs/TEMPLATE.md](changelogs/TEMPLATE.md) | 신규 changelog 작성 양식 |

---

## 권장 독해 순서

1. [`../README.md`](../README.md) - 프로젝트 개요 및 7단계 요약
2. [`design/minchodan_design_note.md`](design/minchodan_design_note.md) - 7단계 상세 설계 (백본)
3. [`../AGENTS.md`](../AGENTS.md) - 코딩·커뮤니케이션 규칙
4. [`dev-guides/course_codebase_guide.md`](dev-guides/course_codebase_guide.md) - **코딩 패턴·함수 시그니처 표준 (코딩 전 필수 참조)**
5. [`ops/code_quality_guide.md`](ops/code_quality_guide.md) - **코드 품질 검증 파이프라인 (린트·보안·중복·CVE, 코딩 전 필수 참조)**
6. [`design/architecture.md`](design/architecture.md) - 시스템 아키텍처 및 컴포넌트
7. [`design/api_specification.md`](design/api_specification.md) - WebSocket API 계약
8. [`ops/environment_variables.md`](ops/environment_variables.md) - **환경 변수 단일 명세 (설정 전 필수 참조)**
9. [`ops/deployment_guide.md`](ops/deployment_guide.md) - **Docker 배포 절차 (배포 전 필수 참조)**
10. [`dev-guides/llm_collaboration_workflow.md`](dev-guides/llm_collaboration_workflow.md) - **담당자 직접 작성 영역과 LLM 보조 영역 분리 기준**
11. [`research/yolo_tts_mvp_next_steps.md`](research/yolo_tts_mvp_next_steps.md) - **th 브랜치 다음 세션 작업 순서와 직접 코딩 항목**
12. [`design/backend_db_architecture.md`](design/backend_db_architecture.md) - **백엔드 비동기 DB 및 3계층 아키텍처 설계 (코딩 전 필수 참조)**
13. [`design/pipeline_stage_design.md`](design/pipeline_stage_design.md) - 파이프라인 단계 설계
14. [`design/behavior_and_risk_insight.md`](design/behavior_and_risk_insight.md) - 보행이론 기반 시각장애인 행동 패턴 및 위험도 정의 인사이트 보고서
15. [`stage-guides/stage2_capture_design.md`](stage-guides/stage2_capture_design.md) - 2단계 백엔드 구현 설계 (코딩 에이전트 필수 참조)
16. [`stage-guides/stage3_detection_design.md`](stage-guides/stage3_detection_design.md) - 3단계 백엔드 구현 설계 (코딩 에이전트 필수 참조)
17. [`stage-guides/stage6_orchestration_design.md`](stage-guides/stage6_orchestration_design.md) - 6단계 종합 회피 가이드 생성 설계 (코딩 에이전트 필수 참조)
18. [`ops/test_specification.md`](ops/test_specification.md) - 검증 기준
19. [`research/post_mvp_hybrid_roadmap.md`](research/post_mvp_hybrid_roadmap.md) - **Post-MVP 하이브리드 온디바이스 로드맵 (MVP 완성 후 착수)**

---

## 현재 문서 기준선

- **이중 경로 원칙**(비협상): 반사 경로(즉시 경보, LLM/RAG/실시간 TTS 미경유, 사전합성 음성)와 인지 경로(mid/low 상세 가이드, LangGraph + RAG + 실시간 TTS)를 물리 분리합니다.
- **모바일은 thin client**입니다. 카메라 캡처와 음성/햡틱 재생만 담당하며, 모든 추론은 GPU 서버에서 수행합니다.
- **3단계는 듀얼헤드 + 이중 게이트**입니다. Yolo 26N - Object Detection(Reflex Gate) + Yolo 26N - Segmentation(Surface Gate)가 모두 룰베이스로 동작하며 LLM을 경유하지 않습니다.
- **노면 클래스는 분리**(C2)합니다. `braille normal/damaged`, `sidewalk normal/damaged`, `crosswalk`, `roadway`, `caution`(stairs/manhole/grating)을 독립 클래스로 학습합니다.
- **반사 음성은 사전합성 고정 클립**(앱 번들)입니다. 실시간 TTS 합성은 금지하며, 반사 음성은 인지 음성을 중단시키고 선점 재생합니다.
- **Whisper는 STT 전용**이며 7단계(가이드 출력)에 등장하지 않습니다. 사용자 음성 명령(STT) 경로는 본 골격 범위 밖입니다.
- **Vector DB는 ChromaDB 로컬 파일 기반**(`data/chroma_db/`)이며, `VectorDBFactory`로 Qdrant 핫스왑을 대비합니다.
- **LLM은 로컬 Ollama(gemma4:e4b)** 기본이며, `LLMClientFactory(BaseChatModel)`로 gpt-4o-mini 핫스왑을 대비합니다.
- **4단계 캡셔닝은 Gemini API**(`gemini-2.5-flash-lite`, 최초 계획 로컬 Llava에서 전환)입니다.
- **7단계 TTS는 Supertonic 기본**(`TTS_ENGINE=supertonic`)이며, Piper/pyttsx3는 핫스왑 폴백입니다.
- **부가 기능으로 GPS 실시간 내비게이션**(`realtime_gps` WS 메시지 + TMAP 보행자 경로 API)을 지원합니다. 길안내 발화는 `realtime_gps` 수신 시점에 직접 평가하며(카메라 탐지와 분리, 2026-07-11), 경로 좌표는 `nav_route` 메시지로 단말 하단 T맵 지도 패널(운영자/데모용)에 전달됩니다.
- **DB는 MariaDB**입니다(세션·디바이스·탐지-가이드 로그 영속화). Docker Compose에서 Ollama는 컨테이너가 아닌 호스트 로컬로 실행됩니다.
- **학습 환경은 Blackwell sm_120 / CUDA 12.8 + cu128 PyTorch 휠**이 필요합니다. 11.8/12.1 휠은 silent CPU 폴백이 발생합니다.
- **로컬 WiFi MVP**에서는 즉시 경보도 서버 추론에 의존합니다. 단말 on-device 반사 레이어는 post-MVP입니다.

---

## 1주차 미결정 7개 (잠정 기본값)

| 항목           | MVP 잠정           | 대안/승급              |
| -------------- | ------------------ | ---------------------- |
| Vector DB      | ChromaDB           | Qdrant                 |
| 임베딩         | nomic-embed-text   | gemini-embedding-001   |
| L2 LLM         | gemma4-e4b         | gpt-4o-mini            |
| On-device 추론 | 없음 (thin client) | 반사 레이어 (post-MVP) |
| 통신 프로토콜  | WS·REST·SSE·Redis  | WebRTC/gRPC 등         |
| TTS            | Kokoro/Coqui       | OpenAI TTS             |
| RDB            | 비동기 SQLAlchemy  | MariaDB/PostgreSQL     |

> **2026-07-10 확정 반영**: 위 표는 1주차 시점의 잠정 기본값이며 현재는 확정 상태입니다. **TTS**는 Kokoro/Coqui가 아닌 **Supertonic**(기본, Piper/pyttsx3 핫스왑)으로 구현됐고, **RDB**는 비동기 SQLAlchemy 계층 위에서 **MariaDB**로 확정됐습니다. 상세는 [`design/architecture.md`](design/architecture.md) §2·§5.7, [`design/backend_db_architecture.md`](design/backend_db_architecture.md)를 참조합니다.
