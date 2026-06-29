# Minchodan 시스템 아키텍처 설계서

> **작성일**: 2026-06-24
> **버전**: v0.2.0
> **설계 기준**: `docs/minchodan_design_note.md` (7단계 골격, 비전 설계서 v1.1)
> **코딩 패턴 기준**: [`docs/course_codebase_guide.md`](course_codebase_guide.md) (수업 전체 코드베이스 코딩 패턴·함수 시그니처 표준)

---

## 1. 프로젝트 개요

Minchodan은 시각장애인 보행 보조를 위한 스마트 가이드독 AI 플랫폼입니다. 스마트폰 카메라로 주변을 캡처해 GPU 서버로 전송하고, 서버에서 장애물·노면 상태를 실시간으로 탐지·분할한 뒤, 위험도에 따라 두 갈래 안전 대응 경로로 분기합니다. 가장 큰 특징은 **이중 경로 물리 분리 원칙**(비협상)입니다.

---

## 2. 기술 스택

### 서버 (GPU 추론)

- Python 3.13, FastAPI, uvicorn, asyncio
- Ultralytics Yolo 26N - Object Detection, Yolo 26N - Segmentation
- ByteTrack (객체 추적)
- Redis (Streams 이벤트 버스 + Track 컨텍스트 TTL=30)
- LangGraph + LangChain (L1/L2/L3 오케스트레이션)
- Ollama (Llava 캡셔닝, gemma4-e4b 가이드 생성, nomic-embed-text 임베딩)
- ChromaDB (로컬 파일 기반 벡터 저장소)
- Kokoro-82M / Coqui (로컬 TTS)
- OpenCV (프레임 디코딩)

### 클라이언트 (단말)

- React Native (iOS/Android)
- react-native-vision-camera (후면 카메라, 이중 캡처 타이머)
- Web Audio API (인지 음성 재생)
- Haptics + announceForAccessibility (접근성)

### 운영 콘솔

- React (운영자 모니터링용)
- SSE 또는 WebSocket 구독

### 인프라

- Docker (Redis + Ollama + FastAPI 컨테이너)
- CUDA 12.8 + cu128 PyTorch 휠 (Blackwell sm_120 전제)

---

## 3. 시스템 아키텍처 구성도

```mermaid
graph TD
    subgraph Client ["Client Layer (Thin Client)"]
        Phone["React Native App<br/>(카메라 캡처 + 음성/햡틱)"]
    end

    subgraph Server ["GPU Server (FastAPI)"]
        subgraph Api ["1. 통신망"]
            WS["WebSocket /ws/detect"]
            Session["Session Manager"]
            Heartbeat["Heartbeat 5s ping/pong"]
        end

        subgraph Capture ["2. 프레임 수신"]
            Decoder["Frame Decoder<br/>(base64  cv2  640x640)"]
            Splitter["Stream Splitter<br/>(반사 8~10fps / 인지 1~2fps)"]
        end

        subgraph Detection ["3. 탐지·분할·게이트"]
            YOLO["Yolo 26N - Object Detection"]
            Seg["Yolo 26N - Segmentation"]
            Tracker["ByteTrack Tracker"]
            ReflexGate["Reflex Risk Gate<br/>(룰베이스, LLM 미경유)"]
            SurfaceGate["Surface Fast-Alert Gate<br/>(룰베이스, LLM 미경유)"]
        end

        subgraph Rag ["4·5. Vector DB 구축·검색"]
            Builder["Build (오프라인)<br/>Llava 캡셔닝 + 임베딩"]
            Retriever["Retriever<br/>(similarity_search k=5)"]
            Fallback["Rule Fallback"]
        end

        subgraph Orch ["6. LangGraph 오케스트레이션"]
            L1["L1 Classifier<br/>(룰 기반 위험도)"]
            L2["L2 Generator<br/>(ChatOllama gemma4-e4b)"]
            L3["L3 Validator<br/>(길이·방향 검증)"]
            FallbackNode["Fallback Node<br/>(고정 문장)"]
        end

        subgraph TTS ["7. 음성 출력"]
            RealtimeTTS["실시간 TTS<br/>(Kokoro/Coqui)"]
            ClipSender["Reflex Clip Sender<br/>(사전합성 클립)"]
            Suppressor["Suppressor<br/>(Redis setex 60)"]
        end

        subgraph Bus ["Redis Bus"]
            RedisStreams["Redis Streams<br/>(risk.events)"]
            RedisCtx["Redis Hash<br/>(Track ctx TTL=30)"]
        end
    end

    subgraph Data ["Data & Storage"]
        Chroma[("ChromaDB<br/>(data/chroma_db)")]
        Clips[("reflex_clips/<br/>사전합성 MP3")]
        Models[("models/<br/>Yolo 26N - Object Detection<br/>Yolo 26N - Segmentation 가중치")]
    end

    Phone <-->|"WebSocket"| WS
    WS --> Decoder
    Decoder --> Splitter
    Splitter -->|"반사 스트림"| YOLO
    Splitter -->|"인지 스트림"| YOLO
    YOLO --> Tracker
    YOLO --> Seg
    Tracker --> RedisCtx
    YOLO --> ReflexGate
    Seg --> SurfaceGate
    ReflexGate -->|"alert_id + 방향"| ClipSender
    SurfaceGate -->|"alert_id"| ClipSender
    ClipSender -->|"고우선 WS"| Phone
    ReflexGate -->|"mid/low"| RedisStreams
    SurfaceGate -->|"mid/low"| RedisStreams
    RedisStreams --> L1
    L1 --> L2
    L2 --> L3
    L3 --> RealtimeTTS
    L3 -->|"RETRY 1회"| L2
    L3 -->|"실패"| FallbackNode
    FallbackNode --> RealtimeTTS
    Retriever --> L2
    Builder --> Chroma
    Chroma --> Retriever
    Retriever --> Fallback
    RealtimeTTS -->|"base64 MP3 WS"| Phone
    Suppressor --> RealtimeTTS

    classDef gate fill:#fde,stroke:#c33,stroke-width:2px;
    classDef storage fill:#9cf,stroke:#333,stroke-width:2px;
    class ReflexGate,SurfaceGate gate;
    class Chroma,Clips,Models storage;
```

---

## 4. 디렉토리 구조 및 기능 매핑

| 디렉토리 / 파일                               | 기능적 역할                                                                | 단계 |
| :-------------------------------------------- | :------------------------------------------------------------------------- | :--- |
| `server/api/`                                 | WebSocket 엔드포인트, 세션 관리, 하트비트                                  | 1    |
| `server/api/ws_router.py`                     | `APIRouter` + `WebSocket /ws/detect`                                       | 1    |
| `server/api/session_manager.py`               | `device_token` 검증, `session_id` 발급                                     | 1    |
| `server/api/heartbeat.py`                     | 5초 ping/pong asyncio 루프                                                 | 1    |
| `server/capture/frame_decoder.py`             | base64 `np.frombuffer` `cv2.imdecode` resize(640,640)                      | 2    |
| `server/capture/stream_splitter.py`           | 반사 스트림(8~10fps) / 인지 스트림(1~2fps) 분기                            | 2    |
| `server/detection/yolo_detector.py`           | Yolo 26N - Object Detection `predict(conf=0.35)`, boxes 파싱               | 3    |
| `server/detection/yolo_segmentor.py`          | Yolo 26N - Segmentation 마스크 생성                                        | 3    |
| `server/detection/bytetrack_tracker.py`       | ByteTrack `update()` track_id 부여                                         | 3    |
| `server/detection/gates/reflex_gate.py`       | Reflex Risk Gate (고위험 + 근접 alert_id+방향)                             | 3    |
| `server/detection/gates/surface_gate.py`      | Surface Fast-Alert Gate (P0 노면 하단 검출 alert_id)                       | 3    |
| `server/detection/schemas.py`                 | `DetectionResult`, `SurfaceResult`, `RiskEvent` 타입                       | 3    |
| `server/rag/build/frame_extractor.py`         | 영상 1fps 프레임 추출                                                      | 4    |
| `server/rag/build/dedup_phash.py`             | pHash 중복 제거                                                            | 4    |
| `server/rag/build/llava_captioner.py`         | Ollama(Llava) 한글 캡셔닝                                                  | 4    |
| `server/rag/build/db_builder.py`              | `Chroma.from_documents(persist_directory)`                                 | 4    |
| `server/rag/retriever.py`                     | `similarity_search_with_score(k=5)`                                        | 5    |
| `server/rag/fallback.py`                      | 유사도 미달 시 룰 기반 fallback 문자열                                     | 5    |
| `server/rag/vector_db_factory.py`             | Chroma Qdrant 핫스왑 추상화                                                | 4·5  |
| `server/orchestration/state.py`               | `OrchState` TypedDict (event, risk_level, rag_context)                     | 6    |
| `server/orchestration/graph.py`               | `StateGraph` 조립, 노드 등록, 엣지 정의                                    | 6    |
| `server/orchestration/nodes/l1_classifier.py` | L1 룰 기반 위험도 분류 (mid/low만 진입)                                    | 6    |
| `server/orchestration/nodes/l2_generator.py`  | L2 ChatOllama(gemma4-e4b) ainvoke (20자/방향)                              | 6    |
| `server/orchestration/nodes/l3_validator.py`  | L3 길이·방향 키워드 검증, RETRY(최대 1회)                                  | 6    |
| `server/orchestration/nodes/fallback_node.py` | 최종 실패 고정 문장                                                        | 6    |
| `server/orchestration/llm_client_factory.py`  | `BaseChatModel` Ollama(gemma4-e4b) gpt-4o-mini 핫스왑                      | 6    |
| `server/tts/realtime_tts.py`                  | 인지 경로 Kokoro/Coqui `generate()` base64 MP3                             | 7    |
| `server/tts/reflex_clip_sender.py`            | 반사 경로 alert_id 사전합성 클립 WS 고우선 전송                            | 7    |
| `server/tts/suppressor.py`                    | Redis `setex(suppress:…, 60)` 중복 억제                                    | 7    |
| `server/tts/tts_service.py`                   | `TTSService` 추상화, MP3/WAV 규격 통일                                     | 7    |
| `server/bus/redis_client.py`                  | aioredis 연결 풀                                                           | 3·6  |
| `server/bus/producer.py`                      | `xadd("risk.events", …)` 인지 경로 발행                                    | 3    |
| `server/bus/consumer.py`                      | `xread` 구독, orchestration 진입                                           | 6    |
| `server/models/yolo26n/`                      | Yolo 26N - Object Detection 및 Yolo 26N - Segmentation 가중치 (git-ignore) | 3    |
| `data/raw/`                                   | AI Hub 보행자 데이터셋 원본                                                | 4    |
| `data/frames/`                                | 영상 1fps 추출 프레임                                                      | 4    |
| `data/deduped/`                               | pHash 중복 제거 후 프레임                                                  | 4    |
| `data/captions/`                              | Llava 캡셔닝 결과 JSON                                                     | 4    |
| `data/chroma_db/`                             | ChromaDB persist 디렉토리                                                  | 4    |
| `data/reflex_clips/`                          | 사전합성 반사 음성 클립 (alert_id별 MP3)                                   | 7    |
| `training/`                                   | 모델 학습 (오프라인)                                                       | 3    |
| `client/src/hooks/useWebSocket.ts`            | WS 연결·hello/welcome 핸드셰이크                                           | 1    |
| `client/src/hooks/useCamera.ts`               | `useCameraDevice('back')` + 이중 타이머                                    | 2    |
| `client/src/services/frameCapture.ts`         | `takePhoto({qualityPrioritization:'speed'})` base64                        | 2    |
| `client/src/services/audioPlayer.ts`          | `decodeAudioData()` Web Audio 재생                                         | 7    |
| `client/src/services/reflexClipPlayer.ts`     | 반사 클립 즉시 재생 (선점 로직)                                            | 7    |
| `client/src/utils/haptics.ts`                 | Haptics + `announceForAccessibility`                                       | 7    |
| `console/src/`                                | 운영자 모니터링 (DetectionFeed, RiskEventLog, SessionStatus)               | -    |

---

## 5. 7단계 컴포넌트 상세

### 5.1 1단계 - 서버-앱 실시간 통신 (WebSocket)

- `FastAPI()` + `CORSMiddleware` `APIRouter().websocket("/ws/detect")`
- `ws.accept()` welcome 송신 hello 수신·디바이스 토큰 검증 5초 ping/pong 하트비트 루프
- `WebSocketDisconnect` 포착 소켓 close + 리소스 해제
- 완료 후 2단계에 WS 엔드포인트 공유

### 5.2 2단계 - 카메라 화면 전송 (이중 캡처)

- `react-native-vision-camera` 권한·후면 카메라 **이중 타이머**로 캡처
- 반사 캡처 8~10fps / 인지 캡처 1~2fps 분리 (v1.1 반영, 충돌 회피)
- `takePhoto({qualityPrioritization:'speed'})` JPEG base64 `ws.send()`
- 서버: `base64.b64decode` `np.frombuffer` `cv2.imdecode` `resize(640,640)` ack
- 카메라 권한 거부(`NotAllowedError`); 소켓 유실 시 `clearInterval`로 타이머 자원 즉시 해제

### 5.3 3단계 - AI 장애물 실시간 인식 (듀얼헤드 + 이중 게이트) v1.1 핵심

1. `cv2.imdecode`로 프레임 복원
2. **Yolo 26N - Object Detection** `predict(conf=0.35)` 클래스·bbox 파싱
3. **Yolo 26N - Segmentation** 노면 의미 분할 마스크
4. **ByteTrack** `update()` Track ID 부여, Redis `hset`+TTL=30 접근/이탈·속도 산출
5. **Reflex Risk Gate(룰베이스, LLM 미경유)**: 고위험 클래스 && 근접(면적·하단) 즉시 `alert_id`+방향
6. **Surface Fast-Alert Gate(룰베이스)**: P0 노면(횡단볼도/맨홀/계단/그레이팅/점자블록파손) 하단 검출 즉시 `alert_id`
7. mid/low만 `redis_bus.xadd("risk.events", …)`로 인지 경로에 발행
8. **방어적 코딩**: Detector/Segmentor 중 하나가 예외를 던져도 나머지 결과는 유지하고 파이프라인은 멈추지 않음. Redis 연결 실패 시에도 탐지 결과는 정상 반환

노면 클래스 분리(C2): `braille normal/damaged`, `sidewalk normal/damaged`, `crosswalk`, `roadway`, `caution`(stairs/manhole/grating)을 **독립 클래스**로 분리합니다.

### 5.4 4단계 - 위험 대처 수칙 DB 구축 (RAG 시드, 오프라인 배치)

- 영상/사진 100+ 수집 1fps 프레임 추출 pHash 중복 제거
- 로컬 VLM(Llava) 한글 캡셔닝 로컬 임베딩(nomic-embed-text, 768d)
- `Document` + 메타etadata(`scene_type`, `risk_level`, `objects`, `guidance_template`) `Chroma.from_documents(persist_directory)`
- 메타데이터 `objects`·`scene_type`을 3단계 분리 클래스(예: `braille_damaged`)와 일치시켜 검색 정합 확보

### 5.5 5단계 - 실시간 대처 수칙 검색 (RAG)

- `Chroma(persist_directory, embedding_function)` 읽기 전용 로드
- 탐지 클래스로 쿼리 생성(`f"{label} 보행 중 회피 방법"`) `similarity_search_with_score(query, k=5)`
- `page_content` 결합 LangGraph `state["rag_context"]` 저장
- 미적중 시 룰 기반 fallback
- `VectorDBFactory`로 Chroma Qdrant 추상화

### 5.6 6단계 - 종합 회피 가이드 생성 (LangGraph 계층 LLM)

- `StateGraph(OrchState)` 조립
- **L1**: 룰 기반 위험도 분류 (high는 이미 즉시 경보 처리됨 / mid·low만 진입)
- **L2**: RAG+탐지 결합 프롬프트로 ChatOllama(gemma4-e4b) `ainvoke` — "한국어 1문장, 20자 내, 방향(좌/우/직진/정지) 포함"
- **L3**: 길이·방향 키워드 검증, 위반 시 L2 RETRY(최대 1회)
- **Fallback/핫스왑**: L3 실패율 >10% 또는 `LLM_PROVIDER=openai` 시 gpt-4o-mini 자동 전환; 최종 실패 시 고정 문장("전방 주의, 천천히 멈추세요")
- `LLMClientFactory(BaseChatModel)`로 로컬상용 핫스왑

### 5.7 7단계 - 음성 안내 출력 (이중 채널)

- **(인지)** 로컬 TTS(Kokoro/Coqui) `generate(guidance_text, voice="ko")` base64 MP3 WS 스트리밍 단말 Web Audio 재생
- **(반사)** 단말에 사전 번들된 고정 클립을 `alert_id`로 즉시 재생 (실시간 TTS 합성 금지)
- **선점(preempt)**: 반사 음성은 인지 음성을 중단시키고 재생. WS에서 반사 이벤트는 별도 고우선 타입
- 중복 억제 `setex(suppress:…, 60)`
- 햅틱·접근성(`announceForAccessibility`) 연동
- `TTSService` 추상화, 출력은 MP3/WAV로 규격 통일

---

## 6. 핵심 데이터 인터페이스

### 6.1 이벤트 추적

- 모든 단계 이벤트는 `event_id`로 추적
- Redis Streams 채널: `risk.events`(인지), 반사는 WS 고우선 타입으로 우회
- 프레임 원본을 Redis에 직접 싣지 말 것(`frame.hex()` 비효율) — 참조 키/공유 메모리 사용 권장

### 6.2 1단계 인터페이스

| 방향 | 페이로드                                    |
| ---- | ------------------------------------------- |
| In   | `{type:"hello", device_id, token}`          |
| Out  | `{type:"welcome", session_id, server_time}` |

### 6.3 2단계 인터페이스

| 방향 | 페이로드                                                                              |
| ---- | ------------------------------------------------------------------------------------- |
| In   | 비디오 프레임                                                                         |
| Out  | `{type:"detection", payload:{event_id, device_id, ts, frame_id, thumbnail_jpeg_b64}}` |

### 6.4 3단계 인터페이스

| 방향 | 페이로드                                                                                                                             |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------ |
| In   | 이미지 bytes                                                                                                                         |
| Out  | `{event_id, detections:[{class_name, confidence, bbox, track_id}], surface:[{class_name, mask\|centroid}], risk_hint, inference_ms}` |

### 6.5 6단계 인터페이스

| 방향 | 페이로드                                    |
| ---- | ------------------------------------------- |
| In   | `OrchState{event, risk_level, rag_context}` |
| Out  | 가이드 문장(String)                         |

### 6.6 7단계 인터페이스

| 방향 | 페이로드                               |
| ---- | -------------------------------------- |
| In   | 가이드 문장(String) / `alert_id`(반사) |
| Out  | 오디오 bytes(ArrayBuffer)              |

---

## 7. 이중 경로 동작 모드

| 경로     | 위험도  | 흐름                                                            | 음성                      | 목표 지연               |
| -------- | ------- | --------------------------------------------------------------- | ------------------------- | ----------------------- |
| **반사** | high    | Detection Reflex Gate / Seg Surface Gate 사전합성 클립          | 사전합성 고정 클립 (선점) | <300ms (Detection 기준) |
| **인지** | mid/low | Detection+Seg Redis Streams LangGraph L1/L2/L3 + RAG 실시간 TTS | 실시간 합성 상세 가이드   | 1~2Hz                   |

반사 경로는 **LLM/RAG/실시간 TTS를 절대 경유하지 않습니다** (비협상 원칙).

---

## 8. 챗봇-LangGraph 자동화 흐름

```mermaid
sequenceDiagram
    participant Phone as 단말
    participant WS as WebSocket
    participant Det as Detection Layer
    participant Redis as Redis Streams
    participant L1 as L1 Classifier
    participant L2 as L2 Generator
    participant L3 as L3 Validator
    participant RAG as RAG Retriever
    participant TTS as 실시간 TTS

    Phone->>WS: 인지 프레임 (1~2fps)
    WS->>Det: 프레임 디코딩
    Det->>Det: Yolo 26N - Object Detection + Yolo 26N - Segmentation + ByteTrack
    alt high 위험 (반사)
        Det-->>Phone: alert_id + 방향 (사전합성 클립, LLM 미경유)
    else mid/low 위험 (인지)
        Det->>Redis: xadd("risk.events")
        Redis->>L1: 위험도 분류
        L1->>RAG: 탐지 클래스 쿼리
        RAG-->>L1: 수칙 컨텍스트 (k=5)
        L1->>L2: RAG+탐지 결합 프롬프트
        L2->>L3: 가이드 문장 (20자/방향)
        L3->>L3: 검증 (위반 시 RETRY 1회)
        L3->>TTS: 가이드 문장
        TTS-->>Phone: base64 MP3 (Web Audio)
    end
```

---

## 9. 추상화 지점 (핫스왑)

| 추상화     | 기본                               | 대안                 | 위치                                         |
| ---------- | ---------------------------------- | -------------------- | -------------------------------------------- |
| Vector DB  | ChromaDB                           | Qdrant               | `server/rag/vector_db_factory.py`            |
| LLM Client | ChatOllama(gemma4-e4b)             | gpt-4o-mini          | `server/orchestration/llm_client_factory.py` |
| Embeddings | OllamaEmbeddings(nomic-embed-text) | gemini-embedding-001 | `server/rag/build/` (Embeddings 추상 클래스) |
| TTS        | Kokoro/Coqui                       | OpenAI TTS           | `server/tts/tts_service.py`                  |

---

## 10. 환경 변수

> **단일 명세**: 환경 변수의 전체 목록·타입·필수 여부·기본값·참조는 [`docs/environment_variables.md`](environment_variables.md)를 기준으로 합니다. 본 절은 핵심 변수 요약만 제공합니다.

| 변수                | 설명                                      | 기본값                   |
| ------------------- | ----------------------------------------- | ------------------------ |
| `LLM_PROVIDER`      | LLM 공급자 (`ollama` 또는 `openai`)       | `ollama`                 |
| `OLLAMA_BASE_URL`   | Ollama 서버 주소                          | `http://localhost:11434` |
| `GEMMA_MODEL`       | L2 가이드 생성 모델                       | `gemma4-e4b`             |
| `LLAVA_MODEL`       | 4단계 캡셔닝 모델                         | `llava`                  |
| `EMBEDDING_MODEL`   | 임베딩 모델                               | `nomic-embed-text`       |
| `REDIS_URL`         | Redis 연결 URL                            | `redis://localhost:6379` |
| `CHROMA_PATH`       | ChromaDB persist 디렉토리                 | `data/chroma_db`         |
| `CHROMA_COLLECTION` | ChromaDB 컬렉션명                         | `bidding_kb`             |
| `WS_HOST`           | WebSocket 서버 바인드 호스트              | `0.0.0.0`                |
| `WS_PORT`           | WebSocket 서버 포트                       | `8000`                   |
| `DETECTOR_TYPE`     | 탐지기 유형 (`mock` 또는 `yolo`)          | `mock`                   |
| `TTS_ENGINE`        | TTS 엔진 (`kokoro` 또는 `coqui`)          | `kokoro`                 |
| `YOLO_CONF`         | Yolo 26N - Object Detection 신뢰도 임계값 | `0.35`                   |
| `FRAME_SIZE`        | 프레임 리사이즈 크기                      | `640`                    |
| `REFLEX_FPS`        | 반사 캡처 목표 fps                        | `10`                     |
| `COGNITIVE_FPS`     | 인지 캡처 목표 fps                        | `2`                      |
| `OPENAI_API_KEY`    | OpenAI 전환 시 필요                       | (미설정)                 |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL (경보 발행)    | (미설정)                 |

> **불일치 해소 이력**: 2026-06-27 환경 변수 3원화(`.env.example`·본 절·루트 `README.md`)를 단일 명세서로 통합. 상세 내용은 [`docs/environment_variables.md`](environment_variables.md) 4절을 참조.

---

## 11. 학습 환경 전제 (v1.1 C3)

3·4단계 모델 학습은 **RTX 5090 / 5070 Ti(Blackwell sm_120)** **CUDA 12.8 + cu128 PyTorch 휠 필수**입니다. 11.8/12.1 휠은 silent CPU 폴백이 발생합니다. 학습 전 `scripts/verify_gpu.py`로 `device_capability ≥ (12,0)` 및 GPU 연산 1 step 검증합니다. TensorRT 엔진은 데모 머신에서 재빌드합니다(세대 간 전송 불가).

---

## 12. 검증 기준선 (계획)

코드 검증:

- `python -m pytest tests/test_ws_echo.py -v` - 1단계: RTT < 100ms echo 검증
- `python -m pytest tests/test_frame_decode.py -v` - 2단계: 캡처수신 < 50ms 검증
- `python -m pytest tests/test_detection.py -v` - 3단계: 게이트 분기, track_id, 예외 영속성 검증
- `python -m pytest tests/test_rag_retrieval.py -v` - 5단계: kickboard 쿼리 < 50ms 검증
- `python -m pytest tests/test_langgraph.py -v` - 6단계: bollard 주입 20자/방향 포함 검증
- `python -m pytest tests/test_tts_reflex.py -v` - 7단계: 반사 클립 선점 재생 검증
- `python scripts/eval_hitrate.py` - 4단계: Top-5 hit-rate ≥ 0.6 평가
- `python scripts/verify_gpu.py` - GPU: sm_120 + CUDA 12.8 검증

상세 검증 기준은 [`docs/test_specification.md`](test_specification.md)를 참조합니다.

---

## 13. MCP (Model Context Protocol) 연동 및 저지연 가드레일

본 프로젝트의 관측 가능성(Observability) 확보와 자원 관리를 위해 MCP를 연동하되, 핵심 지표인 **로우 레이턴시(반사 경로 < 300ms)**를 훼손하지 않도록 비동기 설계를 강제합니다.

### 13.1 단계별 MCP 연동 매트릭스

| 대상 단계 | MCP 구분 | RAG와의 차별점 및 구체적 역할 |
| :--- | :--- | :--- |
| **6단계 (오케스트레이션)** | **LangSmith Trace MCP** | `StateGraph` 내의 노드 전이 및 실행 지연(Latency)을 시각적으로 추적하고 가드레일 위반 시의 재시도 루프를 감시합니다. |
| **6단계 (오케스트레이션)** | **System / GPU Monitor MCP** | GPU 자원 사용량과 CUDA 메모리 한계를 모니터링하여 로컬 Ollama 모델 부하 임계치 도달 시 OpenAI GPT-4o-mini로의 핫스왑을 제어합니다. |
| **7단계 (음성 출력)** | **Audio Validator MCP** | 실시간 생성된 음성 안내(base64 MP3)의 샘플 레이트 규격(24kHz) 준수 여부, 오디오 TTFB 및 무음 구간(Silence)을 검증합니다. |
| **7단계 (음성 출력)** | **Redis Cache Monitor MCP** | 중복 경보 방지를 위한 `suppress:alert_id` 캐시 키와 TTL(60초)의 정밀 상태를 상시 모니터링하고 관리합니다. |
| **7단계 (음성 출력)** | **Accessibility Simulator MCP** | `announceForAccessibility` 텍스트와 실제 재생되는 오디오 파일 간의 의미 정합성을 시각장애인 접근성 관점에서 비교 검증합니다. |
| **공통 (경보)** | **Slack Notification MCP** | L3 가드레일 최종 실패(Fallback 작동) 및 추론 서버 크리티컬 예외 발생 시 실시간으로 개발팀 채널에 즉시 에러 로그를 전송합니다. |

### 13.2 저지연(Low-Latency) 보장을 위한 3대 가드레일

모니터링 데이터 수집으로 인해 메인 추론/전송 스레드에 블로킹(Blocking)이 발생하는 것을 방지하기 위해 다음 원칙을 반드시 준수합니다.

1. **아웃오브밴드 비동기 처리 (Out-of-Band)**: 메인 API 통신 및 오디오 전송 루프 내에 MCP 연동 코드를 인라인(Inline)으로 배치하는 것을 전면 금지하며, `asyncio.create_task` 등 비동기 백그라운드 태스크나 멀티프로세싱을 사용하여 통신 오버헤드 지연을 **0ms**로 유지합니다.
2. **Redis Streams 완충**: 메인 파이프라인은 로컬 Redis 버퍼에 초고속(<1ms)으로 메트릭 데이터만 밀어 넣고, MCP 수집기가 별도의 프로세스에서 이 이벤트를 컨슈밍하여 비동기 처리하도록 구성해 결합도를 완전히 제거합니다.
3. **운영 환경 조건부 비활성화 (No-op)**: 개발 및 QA(CI/CD) 테스트 단계에서만 상세 모니터링 MCP를 기동하고, 프로덕션(Production) 빌드 단계에서는 해당 모니터링 함수를 `No-op` (더미 함수) 처리하여 가동 자원 오버헤드를 제로화합니다.

### 13.3 프론트엔드 관제 연동 및 SSE 전송 규격

통합 MCP 모듈이 Redis Streams에서 수집한 메트릭 데이터는 운영자 콘솔(React)에서 실시간으로 모니터링할 수 있도록 FastAPI의 SSE(Server-Sent Events) 채널을 통해 전달됩니다.

1. **관제 연동 아키텍처**
   - **이벤트 발행자(Publisher)**: 메인 추론 모듈이 `mcp:metrics` Redis Stream으로 메트릭을 초고속 발행합니다.
   - **수집/가공기(MCP Manager)**: 백그라운드에서 실행되는 `MCPManager`가 스트림 데이터를 컨슈밍하고 정규화합니다.
   - **브로드캐스터(FastAPI Router)**: `/api/v1/monitor/stream` 엔드포인트를 통해 연결된 클라이언트들에게 SSE 형식으로 정규화된 JSON 데이터를 전송합니다.

2. **SSE 이벤트 전송 데이터 포맷**
   - 프론트엔드에서 수신하는 실시간 JSON 규격은 다음과 같습니다:

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| **event_type** | `string` | 모니터링 이벤트 종류 (`gpu_status`, `audio_validation`, `cache_suppression`, `system_error`) |
| **timestamp** | `string` | ISO 8601 형식의 이벤트 발생 일시 |
| **payload** | `dict` | 각 이벤트 타입에 대응하는 상세 메트릭 오브젝트 |

3. **이벤트 페이로드 예시**
   - **gpu_status**: `{"gpu_usage_pct": 45.2, "memory_used_mb": 2048, "current_provider": "ollama"}`
   - **audio_validation**: `{"alert_id": "ref_alert_001", "ttfb_ms": 120, "is_valid": true}`
   - **cache_suppression**: `{"suppressed_keys": ["suppress:ref_alert_001"], "ttl_seconds": 45}`
   - **system_error**: `{"error_message": "Ollama connection timeout, hot-swapping to OpenAI", "severity": "warning"}`

### 13.4 MCP별 자격 증명 및 API 키 요구사항

각 MCP 및 연동 기술 스택의 외부 API 의존성과 키 발급 필요 여부는 아래와 같이 정의됩니다.

1. **외부 자격 증명(API Key) 요구 사항**
   - 상용 SaaS 서비스 또는 클라우드 모니터링 연동을 활성화하기 위해 다음의 키를 `.env` 설정에 필수로 기입해야 합니다.

| 연동 모듈 | 필수 환경변수 필드 | 발급처 및 용도 |
| :--- | :--- | :--- |
| **OpenAI 핫스왑 폴백** | `OPENAI_API_KEY` | **OpenAI API Platform**<br/>GPU 자원 초과 시 로컬 Ollama에서 GPT-4o-mini 백업 모델로 실시간 핫스왑하기 위해 사용됩니다. |
| **Slack Notification MCP** | `SLACK_WEBHOOK_URL` | **Slack App Console (Incoming Webhooks)**<br/>L3 가드레일 최종 실패 및 서버 크리티컬 예외 상황 발생 시 개발팀 전용 채널로 실시간 경보 메시지를 발행하기 위해 사용됩니다. |
| **LangSmith Trace MCP** | `LANGCHAIN_API_KEY`<br/>`LANGCHAIN_TRACING_V2` | **LangSmith Platform**<br/>StateGraph의 비정상 루프 및 병목 구간 모니터링을 활성화하기 위해 선택적으로 기입합니다. |

2. **자격 증명이 불필요한 로컬/내부 모듈**
   - 로컬 머신의 자원을 직접 쿼리하거나 오프라인 분석을 활용하므로 별도의 외부 자격 증명이 불필요합니다.

| 모듈명 | 분석 대상 및 작동 방식 | 비고 |
| :--- | :--- | :--- |
| **Redis Streams** | 로컬 메모리 기반 버퍼 통신 | 로컬 Docker 네트워크의 Redis 환경을 직접 사용하여 키가 불필요합니다. |
| **System / GPU Monitor MCP** | PyTorch CUDA API 및 OS 자원 조회 | 하드웨어 드라이버 수준의 자원을 직접 점검하므로 인증이 필요 없습니다. |
| **Audio Validator MCP** | 생성된 base64 오디오 바이너리 헤더 직접 분석 | 로컬에서 무음 구간 및 샘플 레이트 규칙을 파싱하는 순수 연산이므로 키가 필요 없습니다. |
| **Accessibility Simulator MCP** | 스키마 정합성 직접 대조 연산 | 시각장애인 텍스트와 실제 합성된 음성 가이드 간의 일치 여부를 대조하는 순수 연산 모듈입니다. |

### 13.5 내부 MCP 구현 현황 및 단계적 착수 로드맵

`server/mcp/` 패키지의 현재 구현 상태와 향후 착수 시점을 명시합니다. 설계 6종 중 구현 시점이 도래한 모듈만 단계적으로 착수되었으며, 7단계 의존 모듈은 7단계 착수 시 동시 구현을 원칙으로 합니다.

1. **구현 현황 매트릭스 (2026-06-27 기준)**

| MCP 모듈 | 대상 단계 | 구현 위치 | 상태 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **System / GPU Monitor MCP** | 6단계 | `server/mcp/gpu_monitor.py` | **구현 완료** | 6단계 핫스왑 제어 신호로 즉시 필요 |
| **MCPManager (공통 기반)** | 공통 | `server/mcp/manager.py` | **구현 완료** | 6종 MCP 공통 Redis Streams 컨슈머 + SSE 브로드캐스트 백본 |
| **Slack Notification MCP** | 공통 | `scripts/slack_publisher.py` (standalone) | **부분 구현** | 일반 발행 스크립트로 도입, `server/mcp/` 통합 미완 |
| **LangSmith Trace MCP** | 6단계 | - | 미구현 | `LANGCHAIN_API_KEY` 필수, 설계상 "선택적" 명시 |
| **Audio Validator MCP** | 7단계 | - | 미구현 | 7단계 TTS 미구현, base64 MP3 검증 대상 없음 |
| **Redis Cache Monitor MCP** | 7단계 | - | 미구현 | 7단계 `suppress:alert_id` 캐시 미생성 |
| **Accessibility Simulator MCP** | 7단계 | - | 미구현 | 7단계 `announceForAccessibility` 텍스트 미생성 |

2. **단계적 착수 원칙**
   - **6단계 완료 시점**: 6단계 전용 MCP(GPU Monitor) + 공통 인프라(MCPManager) 우선 구현 완료.
   - **7단계 착수 시점**: Audio Validator, Redis Cache Monitor, Accessibility Simulator 3종 동시 구현 권장. 검증 입력 데이터가 7단계 TTS 출력에 의존.
   - **즉시 구현 가능**: Slack Notification MCP는 단계 의존성 없으므로 `scripts/slack_publisher.py`를 `server/mcp/slack_notifier.py`로 통합하여 즉시 구현 가능.

3. **검증 상태**
   - 구현 완료 2종 + 공통 기반 1종에 대해 `tests/test_mcp_gpu.py`(2 케이스) 및 `tests/test_mcp_integration.py`(1 케이스) pytest 통과 완료 (2026-06-27, **3 passed in 21.60s**).
   - 상세 검증 항목은 [`docs/test_specification.md`](test_specification.md) 5.8절을 참조.
