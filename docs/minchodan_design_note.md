# minchodan 설계 노트 — 7단계 골격

> **이 문서는?** 5인 MVP 팀의 7단계 파이프라인 표준 양식이다. 네 개의 초안을 통합했다 — **문서2(구현 상세)를 본문 백본**으로, **문서1**의 인터페이스·예외 계약, **문서3**의 선택 근거·분업·MVP 스코프, **문서4**의 완료 기준을 각 단계에 이식했다.
> **전제:** 비전 설계서 **v1.1**(이중 경로 / Yolo 26N - Object Detection·Yolo 26N - Segmentation / cu128 / 클래스 분리)을 오버레이로 반영한다. 충돌 시 v1.1이 우선한다.
> **작성일**: 2026-06-23
> **수정일**: 2026-06-24
> **버전**: v0.2.0
> **코딩 패턴 기준**: [`docs/course_codebase_guide.md`](course_codebase_guide.md) (수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준)

---

## 1. 시스템 한눈에

스마트폰은 **thin client**(카메라 캡처 + 음성/햅틱 재생만), 모든 추론은 **데스크톱/노트북 GPU**에서 수행한다. 종단 사용자는 음성으로만 상호작용하며, React 콘솔은 운영자 모니터링용이다.

안전 대응은 **두 경로로 물리 분리**한다(비협상 원칙).

```
                         [단말 카메라]
        ┌── 반사 캡처 8~10fps ──┐   ┌── 인지 캡처 1~2fps ──┐
        ▼                       ▼   ▼                      ▼
  ┌─────────────────── WebSocket /ws/detect ───────────────────┐
  │                                                            │
  ▼ 【즉시 경보 — LLM/RAG/실시간TTS 미경유】     ▼ 【인지 경로 — 1~2Hz】
  Yolo 26N - Object Detection  Reflex Gate     Yolo 26N - Object Detection + Yolo 26N - Segmentation
  Yolo 26N - Segmentation      Surface Gate    Redis Streams
        │ alert_id + 방향                         LangGraph L1/L2/L3 + RAG
        ▼                                          실시간 TTS
  단말: 사전합성 음성 즉시 재생 (선점)            단말: 상세 가이드 음성 재생
  목표 <300ms (Detection 기준)
```

> 로컬 WiFi MVP에서는 즉시 경보도 서버 추론에 의존한다. 네트워크 왕복까지 0으로 만드는 **단말 on-device 반사 레이어는 셀룰러/실환경용 post-MVP**다.

---

## 2. 열 정의 (표준 양식)

각 단계는 아래 11개 필드로 기술한다. 괄호는 출처 초안.

| #   | 필드                            | 의미                                        |
| --- | ------------------------------- | ------------------------------------------- |
| 1   | **주제 / 키워드**               | 단계의 한 줄 정체성                         |
| 2   | **목표·목적**                   | 무엇을 / 왜                                 |
| 3   | **선택 이유** (문서3)           | 스택 채택 근거                              |
| 4   | **핵심 절차** (문서2)           | 구현 흐름 요약 (코드 레벨은 v1.1 부록 참조) |
| 5   | **활용 스택·핵심 함수** (문서2) | 라이브러리·메서드                           |
| 6   | **데이터 인터페이스** (문서1)   | In Out 타입/포맷                            |
| 7   | **의존성·예외** (문서1)         | 선후행 연동 + 필수 가드(try/except)         |
| 8   | **분업** (문서3)                | 담당 분할 제안                              |
| 9   | **MVP 스코프** (문서3)          | 어디까지 / 현실 목표                        |
| 10  | **완료 기준** (문서4)           | Acceptance Criteria (측정 가능)             |
| 11  | **v1.1 반영**                   | 비전 오버레이 변경점 (해당 단계만)          |

---

## 3. 7단계 골격

### 1단계 · 서버와 실시간 통신망 연결

- **주제 / 키워드:** 서버-앱 실시간 통신 / WebSocket 세션
- **목표·목적:** 앱과 GPU 서버가 끊김 없이 양방향 통신. 시각장애인의 눈(카메라)과 브레인(AI)을 지연 없이 잇는다.
- **선택 이유:** HTTP 요청-응답으론 실시간 스트리밍 불가. WebSocket은 1회 연결 후 세션 유지하는 전이중 통신으로 최적. React Native로 iOS/Android 동시 대응.
- **핵심 절차:** `FastAPI()` + `CORSMiddleware` `APIRouter().websocket("/ws/detect")` `ws.accept()` welcome 송신 hello 수신·디바이스 토큰 검증 5초 ping/pong 하트비트 루프 `WebSocketDisconnect` 정리 Redis Streams 초기화.
- **활용 스택·핵심 함수:** FastAPI, uvicorn, asyncio / `WebSocket.accept()`, `receive_text()`, `send_json()`, `asyncio.create_task()`
- **데이터 인터페이스:** In `{type:"hello", device_id, token}` Out `{type:"welcome", session_id, server_time}`
- **의존성·예외:** 파이프라인 시작점(선행 없음). 완료 후 2단계에 WS 엔드포인트 공유. **필수 가드:** `WebSocketDisconnect` 포착 소켓 close + 리소스 해제(서버 다운 방지).
- **분업:** RN 경험자 1~2명이 WS 연결 로직 집중·안정화.
- **MVP 스코프:** '시작' 버튼 연결 성공 텍스트 echo 왕복. 초기 안정화에 충분한 시간 확보(불안정 시 전 단계 영향).
- **완료 기준:** 앱서버 양방향 echo 성공, **RTT < 100ms**.

---

### 2단계 · 카메라 화면 전송

- **주제 / 키워드:** 프레임 캡처·전송 / 이중 캡처 스트림
- **목표·목적:** 카메라 화면을 캡처해 서버로 실시간 업로드. 현재 보행 시야를 AI에 전달.
- **선택 이유:** 영상 전체 전송은 대역폭·연산 과부하. 주기적 프레임만 JPEG 압축 후 WS로 송신 = 실시간성·리소스 균형. 무거운 처리는 서버 GPU 담당.
- **핵심 절차:** `react-native-vision-camera` 권한·후면 카메라 **이중 타이머**로 캡처 `takePhoto({qualityPrioritization:'speed'})` JPEG base64 DetectionEvent 조립 `ws.send()`. 서버: `base64.b64decode` `np.frombuffer` `cv2.imdecode` `resize(640,640)` ack.
- **활용 스택·핵심 함수:** react-native-vision-camera, OpenCV / `useCameraDevice('back')`, `np.frombuffer()`, `cv2.imdecode()`
- **데이터 인터페이스:** In 비디오 프레임 Out `{type:"detection", payload:{event_id, device_id, ts, frame_id, thumbnail_jpeg_b64}}`
- **의존성·예외:** 선행=1단계 WS. 출력=3단계 입력. **필수 가드:** 카메라 권한 거부(`NotAllowedError`); 소켓 유실 시 `clearInterval`로 타이머 자원 즉시 해제(메모리 고갈 방지).
- **분업:** 모바일 캡처/전송 1명 전담, 화질·압축·전송속도 테스트 분담.
- **MVP 스코프:** 640해상도로 시작해 전송 속도 확보 후 점진 상향.
- **완료 기준:** 서버 로그에 "수신 640×640, ~42KB" 연속 출력, **캡처수신 < 50ms**.
- ** v1.1 반영:** 단일 2fps는 충돌 회피에 부적합 **반사 캡처 8~10fps / 인지 캡처 1~2fps 이중 스트림**으로 분리. 반사 스트림은 Detection 전용.

---

### 3단계 · AI 기반 장애물 실시간 인식 v1.1 핵심

- **주제 / 키워드:** 객체 탐지 + 의미 분할 + 위험 1차 분류 / 듀얼헤드·이중 게이트
- **목표·목적:** 프레임에서 위험 객체(킥보드·볼라드·계단 등)와 노면 상태(보행 가능 영역·횡단보도·점자블록 파손)를 탐지·분할하고 위험도를 1차 분류.
- **선택 이유:** 실시간 다중 객체 탐지엔 YOLO가 최적이나, **보행 가능 corridor·노면 경계·파손은 바운딩 박스로 표현 불가** 픽셀 단위 분할이 필요. 두 모델은 상호 보완(대체 불가).
- **핵심 절차:**
  1. `cv2.imdecode`로 프레임 복원
  2. **Yolo 26N - Object Detection**(서버 기동 시 1회 로드) `predict(conf=0.35)` 클래스·bbox 파싱
  3. **Yolo 26N - Segmentation** 노면 의미 분할 마스크
  4. **ByteTrack** `update()` Track ID 부여, Redis에 Track별 30초 컨텍스트(`hset`+TTL=30) 접근/이탈·속도 산출
  5. **Reflex Risk Gate(룰베이스, LLM 미경유):** 고위험 클래스 && 근접(면적·하단) 즉시 `alert_id`+방향 (8단계 사전합성 음성)
  6. **Surface Fast-Alert Gate(룰베이스):** P0 노면(횡단보도/맨홀/계단/그레이팅/점자블록파손) 하단 검출 즉시 `alert_id`
  7. mid/low만 `redis_bus.xadd("risk.events", …)`로 인지 경로에 발행
- **활용 스택·핵심 함수:** Ultralytics Yolo 26N - Object Detection, Yolo 26N - Segmentation, ByteTrack, OpenCV, Redis / `YOLO(...).predict()`, `result.boxes.xyxy/conf/cls`, `result.masks`, `tracker.update()`, `xadd()`
- **데이터 인터페이스:** In 이미지 bytes Out `{event_id, detections:[{class_name, confidence, bbox, track_id}], surface:[{class_name, mask|centroid}], risk_hint, inference_ms}`
- **의존성·예외:** 선행=2단계. 출력=4·5·6단계. **필수 가드:** 빈 버퍼/디코딩 실패(None) 가드레일; 무탐지 시 에러 없이 빈 리스트 반환(파이프라인 영속성).
- **분업:** CV/PyTorch 경험자 1~2명. Colab 검증 서버 이식. 탐지 결과는 전원 검증.
- **MVP 스코프:** 탐지 클래스 우선 3~5개로 시작. 사전학습+커스텀 fine-tuning은 여유 시.
- **완료 기준:** 킥보드 추론 `conf≈0.87, track_id` 출력, **Detection 추론 < 80ms**; 30초 후 Redis ctx 키 자동 삭제(TTL 동작).
- ** v1.1 반영:**
  - 모델: YOLOv8에서 **Yolo 26N - Object Detection**(NMS-free, sm_120, 소형객체 최적화) + **Yolo 26N - Segmentation**으로 전환. RT-DETR은 occlusion 백로그.
  - **이중 게이트 신설**: Reflex(Detection) + Surface(Seg). 둘 다 LLM·RAG·실시간 TTS 미경유, 사전합성 음성.
  - **노면 클래스 분리(C2)**: `braille normal/damaged`, `sidewalk normal/damaged`, `crosswalk` vs `roadway`, caution(stairs/manhole/grating)를 **독립 클래스로 분리**(같은 class로 묶으면 파손 학습 불가). 상세는 v1.1 §5.2/§6.2.
  - KPI: occlusion recall(데이터 ~54% 가림), `braille_damaged`/`crosswalk` mIoU.

---

### 4단계 · 위험 대처 수칙 DB 구축 (RAG 시드)

- **주제 / 키워드:** 로컬 VLM 캡셔닝 + 임베딩 + Vector DB / 오프라인 배치
- **목표·목적:** 장애물별 "왜 위험하고 어떻게 회피하는지" 행동 수칙을 벡터 DB로 구축. 비용 없이 로컬 RAG 제공.
- **선택 이유:** 키워드 매칭은 문맥 이해 불가 의미 기반 벡터 검색 필요. 로컬 VLM/임베딩으로 API 비용 0.
- **핵심 절차(오프라인):** 영상/사진 100+ 수집 1fps 프레임 추출 pHash 중복 제거 로컬 VLM(Llava) 한글 캡셔닝 로컬 임베딩(nomic-embed-text, 768d) `Document` + 메타데이터 `Chroma.from_documents(persist_directory)` hit-rate 평가.
- **활용 스택·핵심 함수:** Ollama(Llava), OllamaEmbeddings, ChromaDB / `embed_query()`, `Chroma.from_documents()`, `imagehash.phash()` — _상용 전환 대비 `Embeddings` 추상 클래스로 랩핑_
- **데이터 인터페이스:** In `List[Document]`(page_content=수칙, metadata={scene_type, risk_level, objects, guidance_template}) Out 로컬 persist 디렉토리(정적 벡터 DB)
- **의존성·예외:** 단독 선행 작업. 산출 DB는 5단계가 경로 연동. **필수 가드:** 임베딩 API 네트워크/인증 오류; 디스크 쓰기 권한·경로(`PermissionError`) 사전 체크.
- **분업:** 2명 주도 — 문서 수집·전처리 1명, LangChain·DB 구축 1명.
- **MVP 스코프:** 10~15개로 작게 시작 검색 품질 확인 후 확장.
- **완료 기준:** collection ≥ 100(또는 MVP 10~15), **Top-5 hit-rate ≥ 0.6**, persist 디렉토리 정상 생성.
- ** v1.1 반영:** 메타데이터 `objects`·`scene_type`을 3단계 **분리 클래스(예: braille_damaged)** 와 일치시켜 검색 정합 확보.

---

### 5단계 · 실시간 대처 수칙 검색 (RAG)

- **주제 / 키워드:** 의미 유사도 검색 / 읽기 전용 로드
- **목표·목적:** 탐지 객체가 나타나면 4단계 DB에서 관련 수칙을 지연 없이 매칭.
- **선택 이유:** 코사인 유사도 기반 의미 검색이 키워드 매칭보다 정확. 로컬 임베딩으로 50ms 내 무비용 검색.
- **핵심 절차:** `Chroma(persist_directory, embedding_function)` 읽기 전용 로드 탐지 클래스로 쿼리 생성(`f"{label} 보행 중 회피 방법"`) `similarity_search_with_score(query, k=5)` `page_content` 결합 LangGraph `state["rag_context"]` 저장. 미적중 시 룰 기반 fallback.
- **활용 스택·핵심 함수:** ChromaDB / `similarity_search_with_score()` — _VectorDBFactory로 ChromaQdrant 추상화_
- **데이터 인터페이스:** In 탐지 클래스/쿼리(String) Out 결합 컨텍스트(String)
- **의존성·예외:** 선행=3단계 라벨 + 4단계 DB. 출력=6단계 Context. **필수 가드:** DB 손상/경로 부재(`FileNotFoundError`); 유사도 기준 미달 시 디폴트 안내 문자열 반환(중단 금지).
- **분업:** 랭체인 1~2명, 검색 정확도·속도 집중 테스트.
- **MVP 스코프:** top_k 3~5 조정하며 품질 확인.
- **완료 기준:** 'kickboard' 쿼리에 원본 수칙 일치 반환 + score 정상, **검색 < 50ms**.

---

### 6단계 · 종합 회피 가이드 생성 (계층 LLM)

- **주제 / 키워드:** LangGraph 오케스트레이션 / L1·L2·L3 + Fallback
- **목표·목적:** 탐지 정보 + RAG 수칙을 종합해 최종 우회 지시 문장 생성(방향·거리·행동 포함).
- **선택 이유:** 탐지 유무로 워크플로를 제어하는 상태 그래프가 적합. 로컬 LLM으로 RTT·토큰비용·프라이버시 해결, 성능 부족 시에만 상용 승급.
- **핵심 절차:** `StateGraph(OrchState)`
  - **L1**: 룰 기반 위험도 분류(high는 이미 즉시 경보 처리됨 / mid·low만 진입)
  - **L2**: RAG+탐지 결합 프롬프트로 ChatOllama(gemma4-e4b) `ainvoke` — "한국어 1문장, 20자 내, 방향(좌/우/직진/정지) 포함"
  - **L3**: 길이·방향 키워드 검증, 위반 시 L2 RETRY(최대 1회)
  - Fallback/핫스왑: L3 실패율 >10% 또는 `LLM_PROVIDER=openai` 시 gpt-4o-mini 자동 전환; 최종 실패 시 고정 문장("전방 주의, 천천히 멈추세요")
- **활용 스택·핵심 함수:** LangGraph, LangChain, ChatOllama / `StateGraph()`, `ainvoke()` — _LLMClientFactory(BaseChatModel)로 로컬상용 핫스왑_
- **데이터 인터페이스:** In `OrchState{event, risk_level, rag_context}` Out 가이드 문장(String)
- **의존성·예외:** 선행=3·5단계. 출력=7단계. **필수 가드:** API 장애/Rate Limit/네트워크 차단 시 디폴트 수칙 문장 즉시 반환(프레임워크 정지 금지).
- **분업:** 랭체인 숙련 1~2명. 프롬프트 튜닝 집중, 문장 품질은 전원 검토.
- **MVP 스코프:** temperature 0.2~0.3으로 일관·안전 우선.
- **완료 기준:** (장애물=True, label=bollard, RAG=무릎충돌) 주입 시 20자 내·방향 포함 안내 정상 적재, 조건부 분기 정상.

---

### 7단계 · 음성 안내 출력 (이중 채널)

- **주제 / 키워드:** TTS 출력 / 반사=사전합성, 인지=실시간 합성
- **목표·목적:** 최종 가이드를 한글 음성으로 변환·재생. 화면을 못 보는 사용자에게 귀로 전달.
- **선택 이유:** 서버 합성으로 단말 부담·배터리 절감. 로컬 TTS로 클라우드 요금 제거, 로컬망에서도 끊김 없음.
- **핵심 절차:** **(인지)** 로컬 TTS(Kokoro/Coqui) `generate(guidance_text, voice="ko")` base64 MP3 WS 스트리밍 단말 Web Audio 재생. **(반사)** 단말에 사전 번들된 고정 클립을 `alert_id`로 즉시 재생. 중복 억제 `setex(suppress:…, 60)`. 햅틱·접근성(`announceForAccessibility`) 연동.
- **활용 스택·핵심 함수:** Kokoro-82M/Coqui(서버), react-native-tts(예비), Web Audio, Haptics / `local_tts.generate()`, `decodeAudioData()` — _TTSService 추상화, 출력은 MP3/WAV로 규격 통일_
- **데이터 인터페이스:** In 가이드 문장(String) / `alert_id`(반사) Out 오디오 bytes(ArrayBuffer)
- **의존성·예외:** 선행=6단계(인지) / 3단계 게이트(반사). 파이프라인 종착. **필수 가드:** TTS 호출 실패/타임아웃 시 기기 내장 TTS로 우회(시스템 중단 금지).
- **분업:** 모바일 1명이 수신·재생, 전체 지연 측정.
- **MVP 스코프:** '위험물+행동' 핵심만 짧게.
- **완료 기준:** 서버 합성단말 재생 성공; 반사 클립 **선점 재생** 동작; high 수신 시 햅틱 동시 출력.
- ** v1.1 반영:**
  - **반사 음성 = 사전합성 고정 클립**(앱 번들). 실시간 TTS 합성 금지 — 즉시 경보의 핵심.
  - **선점(preempt):** 반사 음성은 인지 음성을 중단시키고 재생. WS에서 반사 이벤트는 별도 고우선 타입.
  - **Whisper는 STT 전용**이며 본 7단계(가이드 출력)에 등장하지 않는다. 사용자 음성 명령(STT) 경로는 별도 — 본 골격 범위 밖.

---

## 4. 부록

### A. 공통 데이터 계약

- 모든 단계 이벤트는 `event_id`로 추적. Redis Streams 채널: `risk.events`(인지), 반사는 WS 고우선 타입으로 우회.
- 프레임 원본을 Redis에 직접 싣지 말 것(`frame.hex()` 비효율) — 참조 키/공유 메모리 사용 권장.

### B. 1주차 미결정 7개 (잠정 기본값 확정 필요)

| 항목           | MVP 잠정          | 대안/승급             |
| -------------- | ----------------- | --------------------- |
| Vector DB      | ChromaDB          | Qdrant                |
| 임베딩         | nomic-embed-text  | gemini-embedding-001  |
| L2 LLM         | gemma4-e4b        | gpt-4o-mini           |
| On-device 추론 | 없음(thin client) | 반사 레이어(post-MVP) |
| 통신 프로토콜  | WS·REST·SSE·Redis | WebRTC/gRPC 등        |
| TTS            | Kokoro/Coqui      | OpenAI TTS            |
| RDB            | (미정)            | MariaDB/PostgreSQL    |

> **On-device 추론 Post-MVP 상세 설계서**: [`docs/post_mvp_hybrid_roadmap.md`](post_mvp_hybrid_roadmap.md) (2026-07-01, v0.1.0) — 하이브리드 엣지-클라우드 이중 루프, `yolo26n` CoreML/TFLite 포팅, `Frame Processor` 병행 구조, 점진적 전환 4단계(포스트 A~D) 청사진.

### C. 학습 환경 전제 (v1.1 C3)

3·4단계 모델 학습은 **RTX 5090 / 5070 Ti(Blackwell sm_120)** **CUDA 12.8 + cu128 PyTorch 휠 필수**. 11.8/12.1 휠은 silent CPU 폴백. 학습 전 `verify_gpu.py`로 `device_capability ≥ (12,0)` 및 GPU 연산 1 step 검증. TensorRT 엔진은 데모 머신에서 재빌드(세대 간 전송 불가).

### D. 출처 매핑

백본 문서2 / 인터페이스·예외 문서1 / 선택근거·분업·MVP 문서3 / 완료기준 문서4 / 비전 오버레이 설계서 v1.1.
