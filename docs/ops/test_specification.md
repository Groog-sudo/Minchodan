# Minchodan 기능 검증 테스트 명세서

> **작성일**: 2026-06-24
> **버전**: v0.6.9 (2026-07-18 정합성 검토로 발견된 결함 2건 수정 반영: TC-DET-019 테스트 mock에 last_pos 누락으로 실패하던 것을 수정, TC-TTS-009 서버 STT 억제가 응답 전송 직후 즉시 풀리던 gap을 예상 재생시간+마진 TTL로 정정 + 이전 v0.6.8: T1/T2/T3 신규 TC 등재 + 이전 v0.6.7: M1-M7 TC 등재)
> **기준 문서**: `docs/architecture.md`, `docs/api_specification.md`, `docs/minchodan_design_note.md`, [`docs/course_codebase_guide.md`](course_codebase_guide.md), [`docs/code_quality_guide.md`](code_quality_guide.md)

---

## 1. 목적

Minchodan의 기능 검증은 화면 단위 점검이 아니라 아래 흐름이 설계서대로 이어지는지 확인하는 데 목적이 있습니다.

`단말 카메라 캡처  WebSocket 전송  프레임 디코딩  Yolo 26N - Object Detection / Yolo 26N - Segmentation  이중 게이트 분기  (반사) 사전합성 클립 즉시 재생 / (인지) Redis Streams  LangGraph L1/L2/L3 + RAG  실시간 TTS  단말 재생`

핵심 검증 대상은 다음 7가지입니다.

1. WebSocket 실시간 통신 안정성
2. 카메라 이중 캡처·전송 지연
3. 듀얼헤드 탐지·분할·이중 게이트 분기
4. RAG 지식베이스 구축 품질 (hit-rate)
5. RAG 실시간 검색 지연
6. LangGraph 계층 LLM 가이드 품질
7. 이중 채널 음성 출력·선점 재생

---

## 2. 범위

### 2.1 포함 범위

- 1~7단계 파이프라인 흐름
- 반사/인지 이중 경로 분기
- Yolo 26N - Object Detection + Yolo 26N - Segmentation
- ByteTrack 추적 + Redis 컨텍스트 TTL
- ChromaDB 검색 품질
- LangGraph L1/L2/L3 + Fallback
- TTS 합성·선점 재생·햡틱

### 2.2 제외 범위

- 부하 테스트
- 보안 취약점 진단
- 셀룰러/실환경 on-device 반사 레이어 (post-MVP)
- ~~사용자 음성 명령(STT) 경로 (본 골격 범위 밖)~~ **2026-07-09 정정**: 7단계 골격 범위 밖이라는 서술은 유효하나, 실제로 STT는 2026-07-09에 `server/api/ws_router.py`의 `stt_audio` 핸들러로 종단 연결 및 실기동 검증까지 완료됨. **2026-07-11 추가**: 자기-에코 감지·인텐트 우선순위는 `tests/test_stt_to_llm_bridge_template.py`, 바이너리 응답 계약은 `tests/test_ws_router_stt.py`, 반사 경보 미전송 비억제는 `tests/test_detection.py`에서 자동 검증합니다. 플랫폼별 녹음과 지연 시작 취소 기준은 `docs/stage-guides/stage_stt_integration_guide.md` §6(TC-STT-008/009)을 따릅니다.
- 단말 UI 픽셀 단위 디자인 검수

---

## 3. 검증 원칙

### 3.1 로컬 단위 검증과 통합 검증을 분리한다

- 단계별 단위 테스트는 `tests/` 디렉토리에서 자동 검증합니다.
- GPU 추론, Ollama LLM, Redis, 실제 카메라가 필요한 흐름은 통합 smoke 검증으로 분리합니다.

### 3.2 이중 경로 분리를 반드시 확인한다

- 반사 경로가 LLM/RAG/실시간 TTS를 경유하지 않는지 검증합니다.
- 반사 음성이 사전합성 고정 클립만 사용하는지 검증합니다.
- 반사 음성이 인지 음성을 선점 중단시키는지 검증합니다.

### 3.3 현재 설계를 기준으로 명세를 고정한다

1. 반사 캡처는 8~10fps, 인지 캡처는 1~2fps입니다.
2. Yolo 26N - Object Detection 신뢰도 임계값은 `conf=0.35`입니다.
3. 프레임 리사이즈 크기는 640x640입니다.
4. 노면 클래스는 분리(C2)합니다 (`braille normal/damaged`, `sidewalk normal/damaged`, `crosswalk`, `roadway`, `caution`).
5. L2 가이드는 한국어 1문장, 20자 내, 방향(좌/우/직진/정지) 포함입니다.
6. L3 RETRY는 최대 1회입니다.
7. RAG `similarity_search_with_score`의 `k=5`입니다.
8. Redis Track 컨텍스트 TTL은 30초입니다.
9. 중복 억제 `setex(suppress:…, 60)`는 60초입니다.

---

## 4. 실행 환경

- OS: Windows + PowerShell 또는 macOS/Linux + bash/zsh
- GPU: Blackwell sm_120 (RTX 5090 / 5070 Ti), CUDA 12.8 + cu128 PyTorch 휠
- 서버 루트: `./Minchodan`
- Vector Store: 로컬 `data/chroma_db/`
- 외부 의존성: 호스트 로컬 Ollama(gemma4:e4b, nomic-embed-text), Redis, MariaDB, Piper TTS

---

## 5. 단계별 검증 매트릭스

### 5.1 1단계 - WebSocket 실시간 통신

**테스트 파일:** `tests/test_ws_echo.py`

| ID        | 검증 항목                  | 기준                                     | 상태 |
| --------- | -------------------------- | ---------------------------------------- | ---- |
| TC-WS-001 | WS 연결 성립               | `ws.accept()` 후 welcome 송신            | 완료 |
| TC-WS-002 | hello/welcome 핸드셰이크   | `device_token` 검증 후 `session_id` 발급 | 완료 |
| TC-WS-003 | 양방향 echo 왕복           | echo 요청응답 정상                       | 완료 |
| TC-WS-004 | RTT 측정                   | **RTT < 100ms**                          | 완료 |
| TC-WS-005 | 5초 ping/pong 하트비트     | ping/pong 루프 정상                      | 완료 |
| TC-WS-006 | `WebSocketDisconnect` 정리 | 소켓 close + 리소스 해제                 | 완료 |
| TC-WS-007 | detection 바이너리 전송 프로토콜 | JSON 메타(`transport:"binary"`) + `send_bytes()` 바이너리 프레임 → ack 정상 응답, 메타 없는 고아 바이너리 프레임 무시 | 완료 |
| TC-WS-008 | WS 종료 후 송신 시도 무시 | `SessionManager.send_json/send_bytes`가 `application_state != CONNECTED`일 때 송신 스킵 (consumer 태스크 독립 실행 중 에러 스팸 방지) | 완료 |

> **1단계 비고 (2026-07-01)**: 백그라운드 uvicorn 기동 하하 `tests/test_ws_echo.py` 6개 케이스 전체 검증 통과 완료.
> **1단계 비고 (2026-07-07)**: TC-WS-007은 `tests/test_api_ws.py`(`TestClient.websocket_connect`, 실기기/uvicorn 기동 불필요)에서 실제 `/ws/detect` 라우터 코드 경로를 통해 검증됨.
> **1단계 비고 (2026-07-11)**: TC-WS-008은 `SessionManager`에 `WebSocketState.CONNECTED` 가드를 추가해 WS 종료 후 DetectionConsumer가 독립 태스크로 `send` 시도할 때 발생하던 `Cannot call send once a close message has been sent` 에러 스팸(17회 반복)을 원천 차단. 서버 로그로 에러 소멸 확인.


### 5.2 2단계 - 카메라 화면 전송

**테스트 파일:** `tests/test_frame_decode.py`

| ID | 검증 항목 | 기준 | 상태 |
| :--- | :--- | :--- | :--- |
| **TC-CAP-001** | base64 cv2 디코딩 | `np.frombuffer` `cv2.imdecode` 정상 | 완료 |
| **TC-CAP-002** | 리사이즈 640x640 | 출력 프레임 shape (640,640,3) | 완료 |
| **TC-CAP-003** | 캡처수신 지연 | **단위 디코딩 지연 < 50ms** | 완료 |
| **TC-CAP-004** | 이중 스트림 분기 | `StreamSplitter`가 reflex/cognitive로 큐 분기 | 완료 |
| **TC-CAP-005** | Redis 메타데이터 발행 | 프레임 제외 메타데이터만 `risk.events` 발행 | 완료 |
| **TC-CAP-006** | 백프레셔 큐 제한 | Queue 크기 100 초과 시 오래된 프레임 drop | 완료 |
| **TC-CAP-007** | 권한 거부 가드 | 단말 `NotAllowedError` 안내 처리 | 코드 작성 완료 |
| **TC-CAP-008** | 소켓 유실 타이머 해제 | 단말 `clearInterval` 자원 해제 | 코드 작성 완료 |
| **TC-CAP-009** | 예외 안전 복구 | 디코딩/Redis 실패 시에도 큐 push 유지 | 완료 |
| **TC-CAP-010** | 바이너리(raw JPEG) 디코딩 | `decode_frame_binary`가 base64 미경유로 `decode_frame`과 동일 결과(shape/size) 산출, 5종 가드레일 동일 적용 | 완료 (2026-07-07) |
| **TC-PATH-006** | 반사 경로 임포트 격리 | `stream_splitter.py`에 LLM/RAG/TTS 임포트 없음 | 완료 |
| **TC-PATH-007** | 인지 경로 임포트 격리 | `stream_splitter.py`에 LLM/RAG/TTS 임포트 없음 | 완료 |

### 5.3 3단계 - AI 장애물 실시간 인식

**테스트 파일:** `tests/test_detection.py`

| ID | 검증 항목 | 기준 | 상태 |
| :--- | :--- | :--- | :--- |
| **TC-DET-001** | Yolo 26N - Object Detection 킥보드 추론 | `conf≈0.87` | 완료 |
| **TC-DET-002** | track_id 부여 | ByteTrack `update()` track_id | 완료 |
| **TC-DET-003** | Detection 추론 지연 | **< 80ms** | 완료 |
| **TC-DET-004** | Yolo 26N - Segmentation 마스크 | 노면 의미분할 마스크 생성 | 완료 |
| **TC-DET-005** | Reflex Gate 분기 | 고위험+근접 `alert_id`+방향 | 완료 |
| **TC-DET-006** | Surface Gate 분기 | P0 노면 하단 검출 `alert_id` | 완료 |
| **TC-DET-007** | Redis 컨텍스트 TTL | 30초 후 Track ctx 키 자동 삭제 | 완료 |
| **TC-DET-008** | mid/low 발행 | `xadd("risk.events")` 정상 | 완료 |
| **TC-DET-009** | 무탐지 빈 리스트 | 에러 없이 빈 리스트 반환 | 완료 |
| **TC-DET-010** | 노면 클래스 분리 (C2) | `braille_damaged` 독립 클래스 검출 | 완료 |
| **TC-DET-011** | 반사 위험도 SSOT 정합 | 서버 `HIGH_RISK_CLASSES`와 단말 `CLASS_MIN_CONFIDENCE`의 고위험 5종 값 일치 (`tests/test_risk_ssot.py`, 계약: `docs/design/risk_ssot_contract.md`) | 완료 (2026-07-11 신설) |
| **TC-DET-012** | 반사 큐 최신성 보장 (P0-2) | `REFLEX_QUEUE_MAXSIZE=2`에서 3프레임 투입 시 oldest drop, 최신 2개 유지. 신선도 초과(`REFLEX_MAX_AGE_S`) 프레임 추론 없이 드롭 (`tests/test_frame_decode.py::TestP0QueueFreshness`) | 완료 (2026-07-17 신설) |
| **TC-DET-013** | 억제 재무장 정책 (P0-1) | `should_rearm()` 밴드 악화(far->medium->near) 판정. near 500ms 스로틀, non-near device 1.5s 쿨다운 + 동일키 5s TTL + 밴드 악화 재발화 (`tests/test_suppressor_rearm.py`) | 완료 (2026-07-17 신설) |
| **TC-DET-014** | 소형 객체 하단 근접 (P0-3) | 발밑(bottom_y>=0.8*H) 소형 객체(area 4~10%) 근접 발동. 하한(4%) 미만 미발동 (`tests/test_detection.py::TestGates`) | 완료 (2026-07-17 신설) |
| **TC-DET-015** | Approach-Lost 재획득 (P0-3) | 직전 hit>=3 + 1s 이내 재탐지 시 `reacquired=True`, reflex_gate MIN_HIT_COUNT 검사 건너뛰어 즉시 발동 (`tests/test_detection.py::TestByteTrackTracker`) | 완료 (2026-07-17 신설) |
| **TC-DET-016** | surface_caution 히스테리시스 (P2-1b) | `SURFACE_CAUTION_CONFIRM_STREAK=2` 연속 프레임 확인 후 반사 발동. 단일 프레임 오탐 스킵. caution alert STAIR_DOWN 힌트 매핑 (`tests/test_detection.py::TestSurfaceCautionHysteresis`) | 완료 (2026-07-17 신설) |
| **TC-DET-017** | STAIR_DOWN 5클래스 활성화 (P2-1c) | 5클래스 모델 `stair_down`/`manhole` 클래스가 surface_gate 즉시 경보 대상. `surface_stair_down` alert STAIR_DOWN 힌트 매핑 (`tests/test_detection.py::TestLatencyAlertAndStairDown`) | 완료 (2026-07-17 신설) |
| **TC-DET-018** | 파이프라인 지연 관측 (P2-2) | `REFLEX_LATENCY_ALERT_MS=300`/`COGNITIVE_LATENCY_ALERT_MS=3000` 초과 시 콘솔 `latency_event`에 `latency_alert=True` 필드 추가 (`tests/test_detection.py::TestLatencyAlertAndStairDown`) | 완료 (2026-07-17 신설) |
| **TC-DET-019** | 접근 객체 선필터 완화 (T1-a) | `direction=="approaching"` 객체는 hit_count 2로 즉시 통과, 정적 객체는 4프레임 요구. `tests/test_detection.py::TestApproachingHitCountRelax` | 신규 (2026-07-18) |

### 5.4 4단계 - RAG 지식베이스 구축

**테스트 파일:** `scripts/eval_hitrate.py`

| ID         | 검증 항목         | 기준                                        | 상태 |
| ---------- | ----------------- | ------------------------------------------- | ---- |
| TC-RAG-001 | 1fps 프레임 추출  | 영상 프레임 정상 추출                       | 완료 |
| TC-RAG-002 | pHash 중복 제거   | 유사 프레임 제거                            | 완료 |
| TC-RAG-003 | 캡셔닝 VLM 한글 캡션 생성 | 코드 내 설정에 따라 Gemini API 또는 Llava 로컬 캡션 JSON 생성 | 완료 |
| TC-RAG-004 | 임베딩 768d       | nomic-embed-text 벡터 차원                  | 완료 |
| TC-RAG-005 | ChromaDB persist  | 디렉토리 정상 생성                          | 완료 |
| TC-RAG-006 | collection 건수   | **≥ 100** (MVP 10~15)                       | 완료 |
| TC-RAG-007 | Top-5 hit-rate    | **≥ 0.6**                                   | 대기 |
| TC-RAG-008 | 메타데이터 정합   | `objects`/`scene_type`이 분리 클래스와 일치 | 완료 |

### 5.5 5단계 - 실시간 대처 수칙 검색

**테스트 파일:** `tests/test_retriever.py`

| ID         | 검증 항목           | 기준                                            | 상태 |
| ---------- | ------------------- | ----------------------------------------------- | ---- |
| TC-RET-001 | 읽기 전용 로드      | `Chroma(persist_directory, embedding_function)` | 완료 |
| TC-RET-002 | kickboard 쿼리 정합 | 원본 수칙 일치 반환 + score 정상                | 완료 |
| TC-RET-003 | 검색 지연           | **< 50ms**                                      | 완료 |
| TC-RET-004 | k=5                 | 상위 5건 반환                                   | 완료 |
| TC-RET-005 | 미적중 fallback     | 디폴트 안내 문자열 반환                         | 완료 |
| TC-RET-006 | DB 손상 가드        | `FileNotFoundError` 시 안내 문자열              | 완료 |

### 5.6 6단계 - 종합 회피 가이드 생성

**테스트 파일:** `tests/test_langgraph.py`

| ID        | 검증 항목           | 기준                                      | 상태 |
| --------- | ------------------- | ----------------------------------------- | ---- |
| TC-LG-001 | bollard 주입 가이드 | 20자 내 안내 정상 적재                    | 완료 |
| TC-LG-002 | 방향 키워드 포함    | 좌/우/직진/정지 중 하나                   | 완료 |
| TC-LG-003 | L1 위험도 분류      | high 제외, mid/low만 진입                 | 완료 |
| TC-LG-004 | L2 gemma4-e4b ainvoke   | 한국어 1문장 생성                         | 완료 |
| TC-LG-005 | L3 검증 + RETRY     | 위반 시 RETRY(최대 1회)                   | 완료 |
| TC-LG-006 | Fallback 고정 문장  | 최종 실패 시 "전방 주의, 천천히 멈추세요" | 완료 |
| TC-LG-007 | 조건부 분기         | StateGraph 엣지 정상                      | 완료 |
| TC-LG-008 | API 장애 디폴트     | Rate Limit 시 디폴트 수칙 반환            | 완료 |
| TC-LG-009 | GPU Monitor 핫스왑  | GPU 리소스 임계치 돌파 시 OpenAI 핫스왑   | 완료 |
| **TC-LG-010** | 발화 가치 게이트 (P1-2) | 동일 상황(객체+표면 서명) 반복 안내 `COGNITIVE_UTTERANCE_COOLDOWN_S=30s` 내 TTS 합성 생략. 새 객체/표면 변화/보도 이탈/쿨다운 경과 시 발화 (`tests/test_detection.py::TestUtteranceValueGate`) | 완료 (2026-07-17 신설) |
| **TC-LG-011** | 반사 후속 avoidance fast lane (P1-1) | 단일 객체 + 방향 확정 시 `build_avoidance_guidance()` 템플릿으로 즉시 우회 방향 안내 (LangGraph 우회). 다중 객체/방향 불확정 시 LangGraph 폴백 (`tests/test_langgraph.py::TestAvoidanceFastLane`) | 완료 (2026-07-17 신설) |
| **TC-LG-012** | 인지 발화 회랑/접근 필터 (T2-G) | 12시 회랑 밖 정적 객체 또는 far 정적 객체는 `GUIDE_LOW_RISK_NARRATION=false`일 때 무발화. 보도 이탈·고위험·접근 객체·유의미 노면은 통과 (`tests/test_detection.py::TestSpeechWorthyFilter`) | 신규 (2026-07-18) |
| **TC-LG-013** | 12시 회랑 접근 쿨다운 단축 (T1-b) | `direction=="approaching"` + `front` + `near/medium`이면 `_required_guide_gap_sec`가 3초로 단축 (`tests/test_detection.py::TestApproachingCooldownShortcut`) | 신규 (2026-07-18) |

### 5.7 공통 - MCP 및 실시간 관제 스트림

**테스트 파일:** `tests/test_mcp_integration.py`, `tests/test_mcp_gpu.py`

> **최종 검증일**: 2026-06-27 (pytest 9.1.1 + pytest-asyncio 1.4.0, **3 passed in 21.60s**)

| ID         | 검증 항목                          | 기준                                                                   | 상태 |
| ---------- | --------------------------------- | ---------------------------------------------------------------------- | ---- |
| TC-MCP-001 | SSE 모니터링 브로드캐스트         | `/api/v1/monitor/stream` `connection_established` + 페이로드 정상 전송 | 완료 |
| TC-MCP-002 | GPU Mock 폴백 및 임계치 트리거     | `MOCK_GPU_USAGE_PCT` 90% 시 `should_fallback=True`, 20% 시 `False`     | 완료 |
| TC-MCP-003 | LLMClientFactory 핫스왑 라이프사이클 | 부하 95% 시 Ollama->OpenAI 전환, 복구 10% 시 Ollama 복귀              | 완료 |


### 5.8 7단계 - 음성 안내 출력

**테스트 파일:** `tests/test_tts_reflex.py`

| ID         | 검증 항목           | 기준                                 | 상태 |
| ---------- | ------------------- | ------------------------------------ | ---- |
| TC-TTS-001 | 실시간 TTS 합성     | Kokoro/Coqui `generate()` base64 MP3 | 대기 |
| TC-TTS-002 | 단말 재생 성공      | Web Audio `decodeAudioData()` 재생   | 대기 |
| TC-TTS-003 | 반사 클립 선점 재생 | 인지 음성 중단 후 반사 재생          | 완료 |
| TC-TTS-004 | high 햅틱 동시 출력 | Haptics 동시 동작                    | 완료 |
| TC-TTS-005 | 중복 억제           | `setex(suppress:…, 60)` 60초         | 완료 |
| TC-TTS-006 | TTS 실패 우회       | 기기 내장 TTS로 우회                 | 대기 |
| TC-TTS-007 | 반사 클립 사전합성  | 실시간 합성 미사용 확인              | 완료 |
| **TC-TTS-008** | 통합 오디오 우선순위 조정자 (T3-C) | STT 상호작용 중 인지 안내(priority=1) 드롭, STT 응답(priority=2)은 인지 안내를 선점. 반사(P3)는 항상 통과. 단말 `audioEngine` 우선순위 상태 및 콜백 해제 검증 (TSC + 단말 수동) | 신규 (2026-07-18) |
| **TC-TTS-009** | 서버 STT 활성 중 인지 발행 억제 (T3-S) | `_handle_stt_audio`가 `_process_stt_audio` 진입 시 `manager.set_stt_active(true)`. 응답 전송 후에는 `_estimate_stt_hold_seconds()`가 계산한 예상 재생시간+마진만큼 `ttl_seconds`로 연장(2026-07-18 정정 - 최초 구현은 전송 직후 즉시 해제하는 gap이 있었음). `DetectionConsumer._send_cognitive_guide`는 STT 활성 device_id에서 조기 반환. 반사 경로는 억제되지 않음 (`tests/test_ws_router_stt.py::test_stt_audio_success_extends_stt_active_ttl`, `TestEstimateSttHoldSeconds`, `tests/test_detection.py`) | 신규 (2026-07-18, 2026-07-18 억제 창 정정) |

> **7단계 비고 (2026-07-01)**: `docs/reflex_audio_specification.md`에 근거한 입체 비프음(`audioEngine.ts`) 및 햅틱 엔진(`hapticEngine.ts`) 구현 완료. 반사 경보 수신 시 인지 음성 선점 차단 및 동시 햅틱 피드백 검증 완료.
> **7단계 비고 (2026-07-08)**: TC-TTS-005 — `AlertSuppressor`(60초 setex)는 구현돼 있었으나 실제 반사 전송 경로(`server/detection/consumer.py`의 `_send_reflex_alert`)에서 호출되지 않아 중복 억제가 실질적으로 동작하지 않던 결함을 발견해 연결. `tests/test_detection.py::TestReflexAlertSuppression` 2건(억제/비억제 각 케이스)으로 검증 완료.
>
> **2026-07-09 해소**: 위에서 미해결로 남겼던 반사 클립 파일 부재 문제를 해소했다. `data/reflex_clips/*.mp3`(서버 경유)가 아니라 `client/assets/sounds/reflex_clips/*.wav`(단말 번들) 방식으로 실제 구현: macOS `say`로 한국어 임시 음성 5종을 생성해 번들하고 `audioEngine.playReflexClip()`/`useWebSocket.ts` reflex_alert 핸들러에 연결. 조사 중 `reflex_gate.py`의 `alert_id`(클래스명 포함)와 `clip`(direction 기준)이 애초부터 다른 값이었고, `reflex_clip_sender.py`의 `REFLEX_CLIP_MAP`이 실제로는 어디서도 호출되지 않는 죽은 코드였음도 함께 확인·정정. 상세는 `docs/changelogs/kb.md`(2026-07-09) 참조. 실기기 청취(음질) 검증은 아직 미완.


### 5.9 공통 - 정적 분석 게이트 (코드 품질 검증)

**기준 문서:** [`docs/code_quality_guide.md`](code_quality_guide.md)

> **도입 상태**: 완료. 2026-06-27 도구 설치 및 설정 파일 작성 완료.

| ID         | 검증 항목                | 기준                                                                   | 상태     |
| ---------- | ------------------------ | ---------------------------------------------------------------------- | -------- |
| TC-LINT-001 | Ruff 린트 통과          | `ruff check .` 위반 0건 (I/E/W/F/UP/S/B/SIM/C4/RUF/PT 룰)              | 완료     |
| TC-LINT-002 | Ruff 포맷 통과          | `ruff format --check .` 변경사항 0건                                   | 완료     |
| TC-LINT-003 | Bandit 보안 스캔 통과   | `bandit -r server/ scripts/` HIGH/CRITICAL 0건                         | 완료     |
| TC-LINT-004 | mypy 타입 검사 통과     | `mypy server/` error 0건 (점진적, per-file ignore 허용)                | 완료     |
| TC-LINT-005 | jscpd 중복 검출 기준선  | `jscpd` 중복률 2.01% (threshold 5% 이내)                               | 완료     |
| TC-LINT-006 | pip-audit 의존성 CVE    | `pip-audit -r requirements.txt` - chromadb CVE-2026-45829 알려짐 (fix 대기) | 부분 완료 |
| TC-LINT-007 | 이중 경로 분리 강제     | 반사 경로(`server/detection/gates/`)에 LLM/RAG/TTS 임포트 0건          | 코드 리뷰 |
| TC-LINT-008 | pre-commit 훅 동작      | `pre-commit install` 완료, `pre-commit run --all-files` 전체 통과       | 완료     |
| TC-LINT-009 | GitHub Actions CI 통과  | PR 시 lint.yml 워크플로우 전체 통과                                    | 대기     |

> **실행 시점 분리**: TC-LINT-001~003은 pre-commit, TC-LINT-004~006은 pre-push, TC-LINT-007~009는 PR 시 CI. 상세는 [`code_quality_guide.md`](code_quality_guide.md) 7절·8절 참조.

---

## 6. 이중 경로 분리 검증

| ID          | 검증 항목                    | 기준                                | 상태     |
| ----------- | ---------------------------- | ----------------------------------- | -------- |
| TC-PATH-001 | 반사 경로 LLM 미경유         | Reflex/Surface Gate에 LLM 호출 없음 | 완료     |
| TC-PATH-002 | 반사 경로 RAG 미경유         | 반사 메시지에 RAG 검색 없음         | 완료     |
| TC-PATH-003 | 반사 경로 실시간 TTS 미사용  | 사전합성 클립만 사용                | 완료     |
| TC-PATH-004 | 인지 경로 Redis Streams 경유 | `xadd("risk.events")` `xread`       | 발행 완료 |
| TC-PATH-005 | 선점 우선순위                | 반사 WS 고우선 타입 > 인지          | 대기     |

---

## 7. 통합 smoke 검증 (수동/반자동)

GPU, Ollama, Redis, 실제 카메라가 필요한 흐름은 통합 smoke로 분리합니다.

| ID           | 검증 항목      | 환경                               | 상태 |
| ------------ | -------------- | ---------------------------------- | ---- |
| TC-SMOKE-001 | 종단 반사 지연 | 실제 카메라 + GPU, 목표 <300ms     | 대기 |
| TC-SMOKE-002 | 종단 인지 흐름 | 카메라탐지RAGLangGraphTTS 왕복     | 대기 |
| TC-SMOKE-003 | GPU 환경 검증  | `verify_gpu.py` sm_120 + CUDA 12.8 | 대기 |
| TC-SMOKE-004 | Docker 구성    | Redis + MariaDB + FastAPI 컨테이너 + 호스트 Ollama 연결 | 대기 |
| TC-SMOKE-005 | RAG DB 빌드    | `python scripts/build_safety_db.py` | 대기 |
| TC-SMOKE-006 | 생활지원 RAG 통합 | `ollama pull bge-m3` + `python scripts/build_convenience_db.py` 후 컨테이너에서 `answer_convenience_question()` 검색 응답 검증 (2026-07-17 신설, jh 병합 반영) | 완료 |

> **TC-SMOKE-006 상세 절차 (2026-07-17 검증 완료)**
>
> 사전 요건: `.env`에 `CONVENIENCE_EMBEDDING_PROVIDER=ollama`, `CONVENIENCE_EMBEDDING_MODEL=bge-m3` 설정, 호스트 Ollama에 `bge-m3:latest` 적재, Docker 컨테이너가 `data/chroma_db/` 볼륨 마운트.
>
> 1. 호스트에서 `python scripts/build_convenience_db.py` 실행 → `data/chroma_db/convenience_guidelines/` 컬렉션 생성 (문서 34건 적재 확인).
> 2. `docker compose restart fastapi` 후 헬스체크 200 확인.
> 3. 컨테이너 내부에서 `get_default_convenience_service()` 로드 후 `search(question, k=3)` 직접 호출.
> 4. 검증 쿼리 3종:
>    - "복지 전화번호 알려줘" → 복지관/센터 연락처 정상 반환 (적중)
>    - "동사무소 몇 시까지 해?" → 데이터 부재 시 "정보 없음" 정직 응답 (환각 방지 가드레일 동작)
>    - "시각장애인 혜택 뭐 있어?" → 시각장애인 협회/센터 정상 반환 (적중)
> 5. `answer_convenience_question()` 비동기 호출 시 answer 본문이 검색 결과를 반영해 자연어 응답 생성 확인.
>
> Pass 조건: 컨테이너가 호스트 Ollama(`host.docker.internal:11434`)를 통해 `bge-m3` 임베딩을 정상 호출하고, ChromaDB 볼륨 마운트로 호스트 빌드 DB를 읽어 검색 결과를 반환할 것.

---

## 8. 권장 실행 순서

### Windows (PowerShell)

```powershell
# 0. 정적 분석 게이트 (코드 품질 검증)
# - 상세: docs/code_quality_guide.md 참조
ruff format . ; ruff check . ; bandit -r server/ scripts/ ; mypy server/ ; jscpd ; pip-audit -r requirements.txt

# 1. GPU 환경 검증
python scripts\verify_gpu.py

# 2. 단계별 단위 테스트
python tests\test_ws_echo.py
python tests\test_frame_decode.py
python tests\test_detection.py
python tests\test_rag_retrieval.py
python tests\test_langgraph.py
python tests\test_tts_reflex.py
python tests\test_mcp_gpu.py
python tests\test_mcp_integration.py

# 3. RAG 품질 평가
python scripts\eval_hitrate.py

# 4. 통합 smoke (수동)
# - Docker 구성 실행
# - 실제 카메라 연결
# - 종단 지연 측정
```

### macOS / Linux (bash 또는 zsh)

```bash
# 0. 정적 분석 게이트 (코드 품질 검증)
# - 상세: docs/code_quality_guide.md 참조
ruff format . && ruff check . && bandit -r server/ scripts/ && mypy server/ && jscpd && pip-audit -r requirements.txt

# 1. GPU 환경 검증
python scripts/verify_gpu.py

# 2. 단계별 단위 테스트
python tests/test_ws_echo.py
python tests/test_frame_decode.py
python tests/test_detection.py
python tests/test_rag_retrieval.py
python tests/test_langgraph.py
python tests/test_tts_reflex.py
python tests/test_mcp_gpu.py
python tests/test_mcp_integration.py

# 3. RAG 품질 평가
python scripts/eval_hitrate.py

# 4. 통합 smoke (수동)
# - Docker 구성 실행
# - 실제 카메라 연결
# - 종단 지연 측정
```

---

## 9. 완료 기준 요약 (KPI)

| 단계      | KPI            | 목표                    |
| --------- | -------------- | ----------------------- |
| 공통      | 정적 분석 게이트 | Ruff/Bandit/mypy/jscpd/pip-audit 전체 통과 |
| 1         | RTT            | < 100ms                 |
| 2         | 캡처수신       | < 50ms                  |
| 3         | Detection 추론 | < 80ms, conf≈0.87       |
| 4         | Top-5 hit-rate | ≥ 0.6, collection ≥ 100 |
| 5         | RAG 검색       | < 50ms                  |
| 6         | 가이드 품질    | 20자 내, 방향 포함      |
| 7         | 반사 선점 재생 | 동작, 햅틱 동시         |
| 반사 종단 | Detection 기준 | < 300ms                 |
