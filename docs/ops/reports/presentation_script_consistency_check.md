# 발표 대본 전면 정합성 검사 보고서 — 18개 슬라이드 x 최신 코드·문서

> **작성일**: 2026-07-19
> **버전**: v1.0
> **작성 브랜치**: th
> **검사 대상**: `Minchodan_발표대본.md.pdf` (슬라이드 18장 + Q&A 부록)
> **검사 기준**: 현행 코드(th 브랜치 2026-07-19 시점)와 `docs/` 최신 문서
> **자매 문서**: [presentation_template_cache_code_review.md](presentation_template_cache_code_review.md) — 추가 제안 문안(템플릿 캐시) 상세 검토
> **검토 방식**: 코드 수정 없음(읽기 전용). 대본의 검증 가능한 기술 주장을 전수 추출하여 코드·문서와 대조

---

## 1. 종합 판정 요약

| 슬라이드 | 주제 | 판정 | 비고 |
| :--- | :--- | :--- | :--- |
| 1, 2, 18 | 표지·문제 정의·마무리 | 해당 없음 | 검증 대상 기술 주장 없음 |
| 3 | 프로젝트 개요 | **일치** | thin client / GPU 서버 / 콘솔 운영자용 |
| 4 | 이중 경로 물리 분리 | **일치** | 반사 <300ms, 인지 1~2Hz, 게이트 LLM 미경유 |
| 5 | 시스템 아키텍처 | **일치(유의 1건)** | fps·데이터 계층 일치. 반사 클립 서술은 §3.3 참조 |
| 6 | 7단계 파이프라인 KPI | **일치** | KPI 수치가 설계 문서와 동일 |
| 7 | 기술 스택 총괄 | **일치(유의 2건)** | LLM 기본 프로바이더·TTS 시연 엔진은 §3.1, §3.5 참조 |
| 8 | 핵심기술 1 (탐지) | **일치** | 29+4클래스, TTL 30초, 룰베이스 게이트 전부 확인 |
| 9 | 핵심기술 2 (RAG) | **부분 불일치 2건** | 미적중 폴백 경로·쿼리 예시 문구 (§3.2) |
| 10 | 핵심기술 3 (LangGraph) | **부분 불일치 3건** | ChatOllama 표기·기본 프로바이더·폴백 문장 (§3.1) |
| 11 | 핵심기술 4 (이중 채널 음성) | **부분 불일치 2건** | 억제 TTL 60초 시제·반사 오디오 최신 구조 (§3.3) |
| 12 | 보행이론 인사이트 | **일치** | head_level_gate 상단 40%, 클록 포지션 확인 |
| 13 | GPS 내비·음성 명령 | **일치** | TMAP·NavigationManager·faster-whisper-small 기본 |
| 14 | 최근 실측 표본 및 검증 현황 | **일치(2026-07-22 갱신 반영)** | 28/29 클래스(구 가중치 명시), 레이턴시 수치에 측정일·유효성 caveat 추가 후 changelog 원본과 일치 |
| 15 | 실증 테스트 (S1~S8) | **일치** | 재무장 TTL 5초·latest-frame-wins·하단 보조 게이트 코드 확인 |
| 16 | 개발 프로세스 | **일치** | AGENTS.md 정본 구조 그대로 |
| 17 | 한계와 향후 계획 | **부분 불일치 2건** | 셀룰러 미검증 단정·온디바이스 부재 단정 (§3.4) |
| 부록 Q&A | 대비 메모 | **일치(유의 1건)** | hit_count·면적비율 AND 확인. LLM 서술은 §3.1과 동일 유의 |

**총평**: 대본의 골격과 수치(KPI, 실측, 클래스 수, 필드테스트 개선)는 현행 코드·문서와 잘 맞습니다. 다만 **LLM 운영 구성(슬라이드 10)과 RAG 폴백(슬라이드 9), 반사 오디오·억제 정책(슬라이드 11), 한계 서술(슬라이드 17)** 4곳은 코드가 대본보다 더 진화했거나 표현이 부정확하여, 발표 전 수정을 권고합니다.

---

## 2. 불일치 상세 (발표 전 수정 권고)

### 2.1 슬라이드 10 — LangGraph 오케스트레이션 (3건)

| # | 대본 서술 | 코드 실측 | 권고 |
| :--- | :--- | :--- | :--- |
| 1 | "ChatOllama gemma4:e4b `ainvoke`" | LangChain 래퍼(ChatOllama)를 쓰지 않고 **raw 구현** `SimpleOllamaClient`(Ollama 공식 SDK, `llm_client_factory.py:51-91`)를 사용. AGENTS.md §2도 "LangChain 래퍼 미사용" 명시 | "Ollama SDK 기반 자체 비동기 클라이언트"로 표현 수정. 심사자가 코드를 열람하면 ChatOllama 임포트가 없어 즉시 반박 가능 |
| 2 | "로컬 LLM(gemma4:e4b)을 기본으로 사용, 실패 시 gpt-4o-mini 핫스왑" | **시연·운영 기본은 `LLM_PROVIDER=gemini`**(`llm_client_factory.py:278`, 기본값 "gemini"). Ollama는 옵션이며, 시연 환경은 ollama 패키지 미설치까지 전제(`:16-23` 주석). L2 1차 실패 시 OpenAI 폴백(`l2_generator.py:146-169`)과 GPU 모니터 핫스왑(`start_gpu_monitor`)은 실재 | "로컬 우선 설계이나 시연 구성은 Gemini API 기본"임을 밝히거나, 대본의 '로컬 기본' 문장을 설계 의도(프라이버시·비용) 설명으로 한정. Q&A 부록의 동일 서술도 함께 조정 |
| 3 | "실패 시 '전방 주의, 천천히 멈추세요' 고정 문장 대체" | 2026-07-14부터 탐지 객체가 있으면 **동적 폴백** `"{N시 방향/전방} {객체} 주의하세요"`(`fallback_node.py:47-54`). 고정 문장은 무탐지 시에만 | "탐지 객체가 있으면 방향+객체명 동적 문장, 없으면 고정 문장"으로 갱신하면 오히려 개선 사례로 발표 가능 |

### 2.2 슬라이드 9 — RAG 검색 (2건)

| # | 대본 서술 | 코드 실측 | 권고 |
| :--- | :--- | :--- | :--- |
| 1 | "유사도 기준 미달 시 룰 기반 기본 문구로 안전하게 대체" | 룰 폴백 모듈(`server/rag/fallback.py`)은 실재하나 **실시간 파이프라인 미배선**. 미적중 시 `"관련 수칙 없음"` 문자열로 L2 LLM에 직행(`consumer.py:1181,1228`)하고, 정적 폴백은 L3 최종 실패 시 `fallback_node`가 담당 | "미적중 시 수칙 없이도 LLM이 탐지 정보만으로 생성하고, 그마저 실패하면 L3 폴백 문장으로 대체"로 수정. 현 서술은 아키텍처 질문에서 반박 위험 |
| 2 | 쿼리 예시 "킥보드 보행 중 회피 방법" | 실제 쿼리는 영문 라벨 그대로 `f"{class_name} 보행 중 회피 방법"` = **"scooter 보행 중 회피 방법"**(`retriever.py:64`) | 콘솔·로그 라이브 시연 시 노출되므로 예시를 실제 문자열로 맞추거나 "클래스명 기반 쿼리 자동 생성"으로 두루뭉술하게 표현 |

### 2.3 슬라이드 5·11 — 반사 오디오·중복 억제 (2건)

| # | 대본 서술 | 코드 실측 | 권고 |
| :--- | :--- | :--- | :--- |
| 1 | (11) "같은 경보 반복 방지를 위해 Redis에 60초 중복 억제 캐시" | 반사 경보는 **객체(track)+거리 밴드별 재무장 정책, TTL 5초**(`suppressor.py:16` `REFLEX_SUPPRESS_TTL_S=5`, near는 0.5초 스로틀만)로 이미 교체됨. 60초는 레거시 상수와 인지 TTS 기본 TTL로만 잔존 | 슬라이드 15에서 "60초 → 5초 재무장으로 개선"을 발표하므로, 슬라이드 11에서 60초를 **현재형으로 말하면 자체 모순**. 11에서는 "객체·거리별 재무장 억제(기본 5초)"로 말하거나 억제 언급을 15로 미룰 것 |
| 2 | (5·11) "반사 = 단말 번들 고정 클립을 alert_id로 즉시 선점 재생" | 최신 구조는 **거리 기반 스테레오 패닝 비프 + 햅틱이 1차**이고, 사전합성 음성 클립은 별개 채널로 재생하되 **긴급(비프 간격 100ms 이하)에는 클립을 재생하지 않고 비프만** 사용(`audioEngine.ts:80-90,709-712`, 실기기 피드백 반영) | "긴급은 비프+햅틱 즉시, 여유 있는 고위험은 사전합성 클립 병행"으로 한 문장 보완. 시연 중 긴급 상황에서 음성 클립이 안 나와도 설명이 서게 됨 |

### 2.4 슬라이드 17 — 한계 서술 (2건)

| # | 대본 서술 | 실측 | 권고 |
| :--- | :--- | :--- | :--- |
| 1 | "지금까지 검증은 로컬 WiFi 환경 기준(셀룰러 미검증)" | `docs/ops/wireless_test_guide.md`에 **LTE/5G 터널링 경유 실기기 연동 테스트** 명세·트러블슈팅 실측이 존재하고, 2026-07-15 changelog에 Tailscale 경유 실기기 검증 이력 존재 | "상시 검증 기준선은 로컬 WiFi이며, 셀룰러는 터널링 기반 예비 검증 단계"로 완화. 현 표현은 팀이 이미 한 작업을 스스로 지우는 셈 |
| 2 | "진짜 의미의 온디바이스 반사 레이어는 아직 없다" | 온디바이스 추론 브릿지는 **이미 구현·실기기 배포됨**: iOS CoreML(`CoreMLInferenceBridge.swift`), Android TFLite(`tfliteDetector.ts`), 2026-07-16 changelog에 변환 모델(`object_detection260714` 등) 실기기 설치 확인. 단 반사 경보가 서버 왕복 없이 완결되는지는 미검증. 참고로 `docs/README.md` 기준선(온디바이스는 post-MVP)과 AGENTS.md §2(온디바이스 탐지 등재)가 서로 어긋나 있음 | "온디바이스 추론 모듈은 배포되어 검증 중이며, 반사 경보의 완전 온디바이스 완결은 향후 과제"로 정밀화. 아울러 `docs/README.md` 기준선 문구는 팀 차원 정정 필요(본 보고서 범위 밖) |

### 2.5 슬라이드 7 — 기술 스택 (유의)

- "음성 합성은 Supertonic 기본": 코드 기본값과 일치합니다(`tts_service.py:594`, `TTS_ENGINE` 기본 `supertonic`). 다만 **최근 실기기 시연(2026-07-18 changelog)은 한국어 자연도 문제로 `TTS_ENGINE=edge`(edge-tts, 인터넷 필요)로 운용**한 이력이 있습니다. 발표 시연을 edge로 돌릴 계획이면 "기본 Supertonic + 시연은 Edge Neural, 오프라인 폴백 Supertonic" 한 마디를 준비해 두는 것이 안전합니다.
- LLM 스택 서술("Ollama gemma4:e4b")은 §2.1의 2번 유의 사항이 동일하게 적용됩니다.

---

## 3. 일치 확인 근거 (주요 항목)

| 슬라이드 | 대본 주장 | 확인 근거 |
| :--- | :--- | :--- |
| 5 | 반사 8~10fps / 인지 1~2fps 이중 캡처 | `client/src/config/index.ts:83-84` (`REFLEX_FPS=8`, `COGNITIVE_FPS=2`) |
| 6 | KPI: RTT<100ms, 캡처<50ms, Detection<80ms, hit-rate>=0.6, 검색<50ms, 20자·방향, 클립 선점 | `docs/design/pipeline_stage_design.md`, `docs/ops/test_specification.md`, README 동일 수치 |
| 8 | Detection 29클래스 | `server/detection/risk_rules.py:72-103` `CLASS_TEXT` 29개 항목 |
| 8 | Segmentation 4클래스 (braille_normal/sidewalk_normal/caution/roadway) | `server/detection/gates/surface_gate.py:20` |
| 8 | ByteTrack + Redis 컨텍스트 TTL 30초 | `server/bus/redis_client.py:19`, `server/bus/producer.py:20` (`DEFAULT_TRACK_TTL=30`) |
| 8, 부록 | 게이트는 룰베이스, 면적비율·hit_count AND 결합 | `server/detection/gates/reflex_gate.py:30,96` (`MIN_HIT_COUNT`) |
| 9 | 4단계 파이프라인(1fps 추출, pHash, Gemini VLM, nomic-embed 768차원, ChromaDB) | `docs/stage-guides/stage4_5_rag_design.md`, `.agents/skills/rag-knowledge-builder/` |
| 10 | L1 mid/low만 진입, L3 검증·재시도 최대 1회 | `server/orchestration/graph.py:42,54` (`MAX_RETRY=1`) |
| 11 | TTS 전환 스토리(Kokoro/Coqui 계획 → Piper → Supertonic, Piper 핫스왑 보존) | AGENTS.md §2, `tts_service.py:474,588-597` |
| 12 | 상단 40% head-level 격상 경보 | `server/detection/gates/head_level_gate.py:31` (`TOP_REGION_RATIO=0.40`) |
| 12 | 클록 포지션(9시~3시) 자기중심 좌표 | `server/detection/direction.py:78-93` (`CLOCK_HOURS`, `estimate_clock_direction`) |
| 13 | TMAP 보행자 API + NavigationManager + realtime_gps/nav_route | `server/navigation/manager.py`, AGENTS.md §2 |
| 13 | faster-whisper-small 기본 | `server/stt/stt_config.py:83` (`DEFAULT_REQUEST_MODEL`) |
| 14 | 클래스 검증 28/29 성공(구 가중치 det_best_20260705.pt/segbest.pt, 2026-07-06 기준), stop 클래스 0/3, 세그 4클래스 전부 | `docs/ops/model_class_validation_report.md:100` |
| 14 | 실측(측정일 명시): 서버 JPEG 디코딩 0.8~0.9ms(2026-07-12) / Detection 추론(서버) 200~330ms(2026-07-13, 스레드풀 적용 전) / Chroma RAG 51.7~77.9ms(2026-07-12, 현재 기본 경로 아님) / gemma4:e4b 1.0~2.8초(2026-07-13, Fast Lane 적용 전) | `docs/changelogs/kb.md`(2026-07-12·07-13 항목 원본 수치) — `pipeline_stage_design.md:70-73`은 반올림된 구값(56~78ms 등)이라 changelog 원본으로 대체 |
| 15 | S2: 억제 재무장, TTL 5초 | `server/tts/suppressor.py:16` (`REFLEX_SUPPRESS_TTL_S=5`) |
| 15 | S3: 큐 축소 + latest-frame-wins | `server/capture/stream_splitter.py:14`(P0-2), `server/api/session_manager.py:28-33`(maxsize=1) |
| 15 | S4: 하단 근접 보조 게이트 | `server/detection/distance_policy.py:46-47,134-135` (`BOTTOM_OVERRIDE_*`) |
| 16 | AGENTS.md 단일 진실 원천, Hard/Vibe 분리, 품질 파이프라인 | AGENTS.md §5·§10, `docs/ops/code_quality_guide.md` |

---

## 4. 추가 제안 내용(템플릿 캐시)의 반영 상태

- 사용자 제안("고정 프롬프트 템플릿 캐시 + 탐지 객체 동적 치환")에 대한 코드 정합성 판정과 용어 정정, 슬라이드 10 말미 반영 문안은 자매 문서 [presentation_template_cache_code_review.md](presentation_template_cache_code_review.md)에 확정되어 있습니다.
- 해당 문서의 실측 경고(사전합성 클립 `data/guide_clips/` WAV 0건, 시연 전 `scripts/build_guide_clips.py` 실행 필요)는 본 검사에서도 재확인되었습니다.

---

## 5. 발표 전 최종 체크리스트

| # | 항목 | 관련 절 |
| :--- | :--- | :--- |
| 1 | 슬라이드 10: ChatOllama 표기 제거, "Gemini 기본 + Ollama/OpenAI 핫스왑" 구성으로 문구 정리 | §2.1 |
| 2 | 슬라이드 9: "룰 기반 fallback 대체" 문장을 실제 경로(관련 수칙 없음 → LLM → L3 폴백)로 수정 | §2.2 |
| 3 | 슬라이드 11: 60초 억제 서술을 재무장 정책(5초)으로 갱신하거나 15번으로 이동, 긴급 비프 전용 정책 한 줄 추가 | §2.3 |
| 4 | 슬라이드 17: 셀룰러·온디바이스 "미검증/없음" 단정 완화 | §2.4 |
| 5 | 시연 서버에서 `python scripts/build_guide_clips.py` 실행(패스트 레인 클립 캐시 생성) | §4 |
| 6 | 시연 TTS 엔진 결정(edge = 자연도 우선·인터넷 필요 / supertonic = 오프라인) 및 답변 준비 | §2.5 |
| 7 | 템플릿 캐시 추가 문안은 자매 문서 5절 문안을 슬라이드 10 말미에 삽입 | §4 |

---

## 6. 검사 한계

- 대본 원본이 PDF로만 존재하여 저장소 내 직접 수정은 불가하며, 본 보고서의 권고 문안을 대본 편집 시 수동 반영해야 합니다.
- 슬라이드 12의 햅틱 이중화(고위험 연속 진동/중위험 이중 진동)와 슬라이드 15의 안드로이드 센터크롭·bbox 파싱 수정은 changelog·문서 근거로만 확인했으며 단말 코드 라인 단위 대조는 생략했습니다.
- 코드는 일절 수정하지 않았습니다. `docs/README.md` 기준선(온디바이스 post-MVP)과 AGENTS.md §2(온디바이스 탐지 등재) 간 상충은 팀 합의가 필요한 사항으로 기록만 남깁니다.
