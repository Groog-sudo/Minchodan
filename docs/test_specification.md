# Minchodan 기능 검증 테스트 명세서

> **작성일**: 2026-06-24
> **버전**: v0.1.0
> **기준 문서**: `docs/architecture.md`, `docs/api_specification.md`, `docs/minchodan_design_note.md`

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
- 사용자 음성 명령(STT) 경로 (본 골격 범위 밖)
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

- OS: Windows + PowerShell
- GPU: Blackwell sm_120 (RTX 5090 / 5070 Ti), CUDA 12.8 + cu128 PyTorch 휠
- 서버 루트: `./Minchodan`
- Vector Store: 로컬 `data/chroma_db/`
- 외부 의존성: Ollama(Gemma2:9b, Llava, nomic-embed-text), Redis, Kokoro/Coqui TTS

---

## 5. 단계별 검증 매트릭스

### 5.1 1단계 - WebSocket 실시간 통신

**테스트 파일:** `tests/test_ws_echo.py`

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-WS-001 | WS 연결 성립 | `ws.accept()` 후 welcome 송신 | 대기 |
| TC-WS-002 | hello/welcome 핸드셰이크 | `device_token` 검증 후 `session_id` 발급 | 대기 |
| TC-WS-003 | 양방향 echo 왕복 | echo 요청응답 정상 | 대기 |
| TC-WS-004 | RTT 측정 | **RTT < 100ms** | 대기 |
| TC-WS-005 | 5초 ping/pong 하트비트 | ping/pong 루프 정상 | 대기 |
| TC-WS-006 | `WebSocketDisconnect` 정리 | 소켓 close + 리소스 해제 | 대기 |

### 5.2 2단계 - 카메라 화면 전송

**테스트 파일:** `tests/test_frame_decode.py`

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-FR-001 | base64  cv2 디코딩 | `np.frombuffer`  `cv2.imdecode` 정상 | 대기 |
| TC-FR-002 | 리사이즈 640x640 | 출력 프레임 shape (640,640,3) | 대기 |
| TC-FR-003 | 캡처수신 지연 | **캡처수신 < 50ms** | 대기 |
| TC-FR-004 | 이중 스트림 분기 | 반사 8~10fps / 인지 1~2fps 분리 | 대기 |
| TC-FR-005 | 권한 거부 가드 | `NotAllowedError` 안내 처리 | 대기 |
| TC-FR-006 | 소켓 유실 타이머 해제 | `clearInterval` 자원 해제 | 대기 |

### 5.3 3단계 - AI 장애물 실시간 인식

**테스트 파일:** `tests/test_detection.py`

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-DET-001 | Yolo 26N - Object Detection 킥보드 추론 | `conf≈0.87` | 대기 |
| TC-DET-002 | track_id 부여 | ByteTrack `update()`  track_id | 대기 |
| TC-DET-003 | Detection 추론 지연 | **< 80ms** | 대기 |
| TC-DET-004 | Yolo 26N - Segmentation 마스크 | 노면 의미분할 마스크 생성 | 대기 |
| TC-DET-005 | Reflex Gate 분기 | 고위험+근접  `alert_id`+방향 | 대기 |
| TC-DET-006 | Surface Gate 분기 | P0 노면 하단 검출  `alert_id` | 대기 |
| TC-DET-007 | Redis 컨텍스트 TTL | 30초 후 Track ctx 키 자동 삭제 | 대기 |
| TC-DET-008 | mid/low 발행 | `xadd("risk.events")` 정상 | 대기 |
| TC-DET-009 | 무탐지 빈 리스트 | 에러 없이 빈 리스트 반환 | 대기 |
| TC-DET-010 | 노면 클래스 분리 (C2) | `braille_damaged` 독립 클래스 검출 | 대기 |

### 5.4 4단계 - RAG 지식베이스 구축

**테스트 파일:** `scripts/eval_hitrate.py`

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-RAG-001 | 1fps 프레임 추출 | 영상  프레임 정상 추출 | 대기 |
| TC-RAG-002 | pHash 중복 제거 | 유사 프레임 제거 | 대기 |
| TC-RAG-003 | Llava 한글 캡셔닝 | 캡션 JSON 생성 | 대기 |
| TC-RAG-004 | 임베딩 768d | nomic-embed-text 벡터 차원 | 대기 |
| TC-RAG-005 | ChromaDB persist | 디렉토리 정상 생성 | 대기 |
| TC-RAG-006 | collection 건수 | **≥ 100** (MVP 10~15) | 대기 |
| TC-RAG-007 | Top-5 hit-rate | **≥ 0.6** | 대기 |
| TC-RAG-008 | 메타데이터 정합 | `objects`/`scene_type`이 분리 클래스와 일치 | 대기 |

### 5.5 5단계 - 실시간 대처 수칙 검색

**테스트 파일:** `tests/test_rag_retrieval.py`

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-RET-001 | 읽기 전용 로드 | `Chroma(persist_directory, embedding_function)` | 대기 |
| TC-RET-002 | kickboard 쿼리 정합 | 원본 수칙 일치 반환 + score 정상 | 대기 |
| TC-RET-003 | 검색 지연 | **< 50ms** | 대기 |
| TC-RET-004 | k=5 | 상위 5건 반환 | 대기 |
| TC-RET-005 | 미적중 fallback | 디폴트 안내 문자열 반환 | 대기 |
| TC-RET-006 | DB 손상 가드 | `FileNotFoundError` 시 안내 문자열 | 대기 |

### 5.6 6단계 - 종합 회피 가이드 생성

**테스트 파일:** `tests/test_langgraph.py`

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-LG-001 | bollard 주입 가이드 | 20자 내 안내 정상 적재 | 대기 |
| TC-LG-002 | 방향 키워드 포함 | 좌/우/직진/정지 중 하나 | 대기 |
| TC-LG-003 | L1 위험도 분류 | high 제외, mid/low만 진입 | 대기 |
| TC-LG-004 | L2 Gemma2 ainvoke | 한국어 1문장 생성 | 대기 |
| TC-LG-005 | L3 검증 + RETRY | 위반 시 RETRY(최대 1회) | 대기 |
| TC-LG-006 | Fallback 고정 문장 | 최종 실패 시 "전방 주의, 천천히 멈추세요" | 대기 |
| TC-LG-007 | 조건부 분기 | StateGraph 엣지 정상 | 대기 |
| TC-LG-008 | API 장애 디폴트 | Rate Limit 시 디폴트 수칙 반환 | 대기 |

### 5.7 7단계 - 음성 안내 출력

**테스트 파일:** `tests/test_tts_reflex.py`

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-TTS-001 | 실시간 TTS 합성 | Kokoro/Coqui `generate()`  base64 MP3 | 대기 |
| TC-TTS-002 | 단말 재생 성공 | Web Audio `decodeAudioData()` 재생 | 대기 |
| TC-TTS-003 | 반사 클립 선점 재생 | 인지 음성 중단 후 반사 재생 | 대기 |
| TC-TTS-004 | high 햅틱 동시 출력 | Haptics 동시 동작 | 대기 |
| TC-TTS-005 | 중복 억제 | `setex(suppress:…, 60)` 60초 | 대기 |
| TC-TTS-006 | TTS 실패 우회 | 기기 내장 TTS로 우회 | 대기 |
| TC-TTS-007 | 반사 클립 사전합성 | 실시간 합성 미사용 확인 | 대기 |

---

## 6. 이중 경로 분리 검증

| ID | 검증 항목 | 기준 | 상태 |
| --- | --- | --- | --- |
| TC-PATH-001 | 반사 경로 LLM 미경유 | Reflex/Surface Gate에 LLM 호출 없음 | 대기 |
| TC-PATH-002 | 반사 경로 RAG 미경유 | 반사 메시지에 RAG 검색 없음 | 대기 |
| TC-PATH-003 | 반사 경로 실시간 TTS 미사용 | 사전합성 클립만 사용 | 대기 |
| TC-PATH-004 | 인지 경로 Redis Streams 경유 | `xadd("risk.events")`  `xread` | 대기 |
| TC-PATH-005 | 선점 우선순위 | 반사 WS 고우선 타입 > 인지 | 대기 |

---

## 7. 통합 smoke 검증 (수동/반자동)

GPU, Ollama, Redis, 실제 카메라가 필요한 흐름은 통합 smoke로 분리합니다.

| ID | 검증 항목 | 환경 | 상태 |
| --- | --- | --- | --- |
| TC-SMOKE-001 | 종단 반사 지연 | 실제 카메라 + GPU, 목표 <300ms | 대기 |
| TC-SMOKE-002 | 종단 인지 흐름 | 카메라탐지RAGLangGraphTTS 왕복 | 대기 |
| TC-SMOKE-003 | GPU 환경 검증 | `verify_gpu.py` sm_120 + CUDA 12.8 | 대기 |
| TC-SMOKE-004 | Docker 구성 | Redis + Ollama + FastAPI 컨테이너 | 대기 |
| TC-SMOKE-005 | RAG DB 빌드 | `build_chroma.sh` 오프라인 전체 | 대기 |

---

## 8. 권장 실행 순서

```powershell
# 1. GPU 환경 검증
python scripts\verify_gpu.py

# 2. 단계별 단위 테스트
python tests\test_ws_echo.py
python tests\test_frame_decode.py
python tests\test_detection.py
python tests\test_rag_retrieval.py
python tests\test_langgraph.py
python tests\test_tts_reflex.py

# 3. RAG 품질 평가
python scripts\eval_hitrate.py

# 4. 통합 smoke (수동)
# - Docker 구성 실행
# - 실제 카메라 연결
# - 종단 지연 측정
```

---

## 9. 완료 기준 요약 (KPI)

| 단계 | KPI | 목표 |
| --- | --- | --- |
| 1 | RTT | < 100ms |
| 2 | 캡처수신 | < 50ms |
| 3 | Detection 추론 | < 80ms, conf≈0.87 |
| 4 | Top-5 hit-rate | ≥ 0.6, collection ≥ 100 |
| 5 | RAG 검색 | < 50ms |
| 6 | 가이드 품질 | 20자 내, 방향 포함 |
| 7 | 반사 선점 재생 | 동작, 햅틱 동시 |
| 반사 종단 | Detection 기준 | < 300ms |
