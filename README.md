> [!IMPORTANT]
> **이 저장소에서 작업할 때는 먼저 [`AGENTS.md`](AGENTS.md), [`docs/README.md`](docs/README.md), [`SKILLS.md`](SKILLS.md)를 읽고 프로젝트 규칙과 문서 기준선을 확인합니다.

# Minchodan (민초단)

**Minchodan**은 시각장애인 보행 보조를 위한 스마트 가이드독 AI 플랫폼입니다. 스마트폰 카메라로 주변을 인식하고, GPU 서버에서 실시간으로 장애물·노면 상태를 탐지한 뒤, 음성과 햅틱으로 즉시 안내합니다. 안전 대응은 **반사 경로**(즉시 경보)와 **인지 경로**(상세 가이드) 두 갈래로 물리 분리하는 것이 핵심 원칙입니다.

> **작성일**: 2026-06-24
> **버전**: v0.2.7 (2026-07-19 전면 보안 강화 기준과 팀 반영 가이드 문서 연결)
> **설계 기준**: `docs/design/minchodan_design_note.md` (7단계 골격, 비전 설계서 v1.1 반영)

---

## 프로젝트 개요

스마트폰은 **thin client**(카메라 캡처 + 음성/햅틱 재생만)이며, 모든 추론은 데스크톱/노트북 GPU 서버에서 수행합니다. 종단 사용자는 음성으로만 상호작용하며, React 콘솔은 운영자 모니터링용입니다.

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

> 로컬 WiFi MVP에서는 즉시 경보도 서버 추론에 의존합니다. 네트워크 왕복까지 0으로 만드는 **단말 on-device 반사 레이어는 셀룰러/실환경용 post-MVP**입니다.

---

## 7단계 파이프라인 요약

| 단계 | 주제                              | 핵심 스택                                                       | 완료 기준 (KPI)                            |
| ---- | --------------------------------- | --------------------------------------------------------------- | ------------------------------------------ |
| 1    | 서버-앱 실시간 통신 (WebSocket)   | FastAPI, uvicorn, asyncio                                       | 양방향 echo, **RTT < 100ms**               |
| 2    | 카메라 화면 전송 (이중 캡처)      | react-native-vision-camera, OpenCV                              | 640x640 수신, **캡처수신 < 50ms**          |
| 3    | AI 장애물 실시간 인식 (듀얼헤드)  | Object Detection 29클래스, Segmentation 4클래스, ByteTrack (반사는 온디바이스) | scooter conf≈0.87, **Detection < 80ms**    |
| 4    | 위험 대처 수칙 DB 구축 (RAG 시드) | Gemini 캡셔닝, ChromaDB, nomic-embed                            | collection ≥ 100, **Top-5 hit-rate ≥ 0.6** |
| 5    | 실시간 대처 수칙 검색 (RAG)       | ChromaDB                                                        | 장애물 쿼리 정합, **검색 < 50ms**          |
| 6    | 종합 회피 가이드 생성 (계층 LLM)  | LangGraph, SimpleOllamaClient(gemma4:e4b)                       | bollard 주입 시 20자 내·방향 포함          |
| 7    | 음성 안내 출력 (이중 채널)        | Supertonic(기본)/Piper(핫스왑), expo-audio, Haptics             | 반사 클립 선점 재생, 햅틱 동시 출력        |

상세 설계는 [`docs/design/minchodan_design_note.md`](docs/design/minchodan_design_note.md)와 [`docs/design/architecture.md`](docs/design/architecture.md)를 참조합니다.

---

## 기술 스택

### 서버 (GPU 추론)

- Python 3.13, FastAPI, uvicorn
- Ultralytics Yolo 26N - Object Detection, Yolo 26N - Segmentation
- ByteTrack (객체 추적)
- Redis (Streams 이벤트 버스 + 컨텍스트 TTL)
- LangGraph (L1/L2/L3 오케스트레이션, raw SimpleOllamaClient/SimpleOpenAIClient)
- Ollama (gemma4:e4b 가이드 생성, nomic-embed-text 보행 안전 수칙 임베딩, bge-m3 생활지원 RAG 임베딩)
- Gemini API (gemini-2.5-flash-lite, 오프라인 RAG 빌드 캡셔닝; 최초 계획 로컬 Llava에서 전환)
- ChromaDB (로컬 벡터 저장소)
- Supertonic 3 (로컬 TTS, ONNX, MIT, 99M 파라미터; 기본 엔진, 2026-07-09 Piper에서 교체). Piper(piper-kss-korean.onnx)는 핫스왑 폴백으로 보존
- OpenCV (프레임 디코딩)

### 클라이언트 (단말)

- React Native (iOS/Android 동시 대응)
- react-native-vision-camera (후면 카메라, Frame Processor 기반 연속 캡처 + 스트림 분할; 2026-07-09 takePhoto()에서 전환 - AVCapturePhotoOutput의 오디오 세션 인터럽션 회피)
- 온디바이스 추론: CoreML(iOS) / react-native-fast-tflite(Android)
- expo-audio (단말 오디오 재생 계층, createAudioPlayer)
- expo-speech (한글 음성 합성, Voice 선택; react-native-tts 미사용)
- expo-haptics (반사 햅틱)
- Haptics + announceForAccessibility (접근성)

### 운영 콘솔

- React (운영자 모니터링용)
- SSE/WebSocket 구독 (탐지 피드, RiskEvent 로그, 세션 상태)

### 인프라

- Docker (Redis + MariaDB + FastAPI 컨테이너 구성, Ollama는 호스트 로컬 프로세스로 실행)
- 팀 GPU 서버 최대 사양 RTX 5090(Blackwell sm_120): Ubuntu x86_64/Windows amd64는 PyTorch 2.13 + CUDA 13.0(cu130), macOS는 PyTorch 2.13 MPS/CPU

---

## 디렉토리 구조

```shell
Minchodan/
│
├── server/                          # GPU 서버 (FastAPI)
│   ├── api/                         # WebSocket /ws/detect, 세션, 하트비트, REST 라우터
│   ├── capture/                     # 프레임 디코딩, 이중 스트림 분기
│   ├── detection/                   # Yolo 26N - Object Detection, Yolo 26N - Segmentation, ByteTrack, Gates
│   │   └── gates/                   # Reflex Gate, Surface Gate
│   ├── rag/                         # Vector DB 구축·검색
│   │   └── build/                   # 오프라인 배치 (캡셔닝, 임베딩)
│   ├── orchestration/               # LangGraph L1/L2/L3
│   │   └── nodes/                   # 분류, 생성, 검증, fallback
│   ├── tts/                         # 실시간 TTS, 반사 클립 전송, 억제
│   ├── bus/                         # Redis Streams 인터페이스
│   ├── db/                          # RDB ORM/DTO/DDL (사용자, 단말, 관리자, 감사 로그)
│   ├── models/                      # 사전학습 가중치 Git 추적, 커스텀 학습 가중치 git-ignore
│   │   └── yolo26n/
│   ├── services/                    # 비즈니스 로직 Service 계층 (Router-Service-Repository)
│   ├── stt/                         # faster-whisper STT 서비스, 음성 명령-LLM 브릿지
│   ├── navigation/                  # TMAP 보행자 경로 API, NavigationManager
│   └── mcp/                         # MCP 연동 모듈 (GPU 모니터, Slack, LangSmith, 접근성 시뮬레이터 등)
│
├── console/                         # React 운영자 모니터링 콘솔
│
├── client/                          # React Native 앱 (thin client)
│   ├── assets/sounds/reflex_clips/  # 사전합성 반사 음성 클립 (WAV 5종, 단말 번들)
│   └── src/
│       ├── hooks/                   # useWebSocket, useCamera, useLocation(GPS)
│       ├── services/                # frameCaptureProvider(iOS/Android 이원화), audioEngine, hapticEngine
│       ├── components/              # CameraView
│
├── data/                            # 학습·RAG 데이터
│   ├── raw/                         # AI Hub 보행자 데이터셋 원본
│   ├── frames/                      # 1fps 추출 프레임
│   ├── deduped/                     # pHash 중복 제거 후 프레임
│   ├── captions/                    # Gemini VLM 캡셔닝 결과 JSON
│   └── chroma_db/                   # ChromaDB persist 디렉토리
│
├── training/                        # 모델 학습 (오프라인)
│   ├── datasets/                    # detection, segmentation
│   ├── configs/                     # aihub_merged_detection.yaml, aihub_yolo_segmentation.yaml
│   ├── train_detection.py
│   └── train_segmentation.py
│
├── scripts/                         # 유틸리티 스크립트
│   ├── build_safety_db.py           # 4단계 RAG (safety_guidelines.json → ChromaDB)
│   ├── build_convenience_db.py      # 편의 RAG 빌드
│   └── build_guide_clips.py         # 반사 안내 클립 합성
├── tests/                           # 7단계별 검증 테스트
├── docker/                          # Docker Build & Setting
├── docs/                            # 설계 문서 및 가이드
├── .env.example                     # 환경변수 템플릿
├── requirements.txt                 # 파이썬 의존성
└── README.md
```

상세 구조는 [`docs/Directory_Structure.md`](docs/Directory_Structure.md)를 참조합니다.

---

## 빠른 시작

### 1. 환경 변수 설정

#### Windows (PowerShell)

```powershell
Copy-Item .env.example .env
# LLM_PROVIDER, REDIS_URL, CHROMA_PATH, OLLAMA_BASE_URL, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD 등을 설정합니다.
```

#### macOS / Linux (bash 또는 zsh)

```bash
cp .env.example .env
# LLM_PROVIDER, REDIS_URL, CHROMA_PATH, OLLAMA_BASE_URL, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD 등을 설정합니다.
```

### 2. 서버 의존성 설치 및 실행

#### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

#### macOS / Linux (bash 또는 zsh)

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 가속 환경 검증 (RTX 5090 최대 / CUDA 13.0 / macOS MPS)

#### Windows (PowerShell)

```powershell
python scripts\verify_gpu.py
# CUDA 13.0, RTX 5090 sm_120 호환성 및 GPU 1 step 연산 검증
```

#### macOS / Linux (bash 또는 zsh)

```bash
python scripts/verify_gpu.py
# Ubuntu는 CUDA 13.0 GPU, macOS는 MPS/CPU 1 step 연산 검증
```

> Ubuntu x86_64와 Windows amd64 GPU 서버는 공식 `torch==2.13.0+cu130` 휠과 NVIDIA R580 이상 드라이버를 사용합니다. macOS는 CUDA가 아니라 같은 PyTorch 2.13의 MPS를 우선 사용하고, MPS가 없으면 CPU로 폴백합니다.

### 4. Docker 구성 (Redis + MariaDB + FastAPI + 호스트 로컬 Ollama)

> 상세 배포 절차는 [`docs/ops/deployment_guide.md`](docs/ops/deployment_guide.md)를 참조하십시오.
> Ollama는 Docker 컨테이너에 포함하지 않고 호스트에서 `ollama serve`로 실행합니다.

#### Windows (PowerShell)

```powershell
docker\windows_docker_start.bat
```

#### macOS (bash 또는 zsh)

```bash
bash docker/macos_docker_start.sh
```

#### Linux (bash)

```bash
bash docker/linux_docker_start.sh
```

### 5. RAG 지식베이스 빌드 (오프라인)

#### Windows (PowerShell)

```powershell
python scripts/build_safety_db.py
# data/safety_guidelines.json → data/chroma_db (보행 안전 수칙)
python scripts/build_convenience_db.py
# data/convenience_guidelines.json → data/chroma_db/convenience_guidelines (생활지원 RAG)
# 사전 요건: ollama pull bge-m3 (생활지원 RAG 임베딩 전용)
# 선택: python scripts/build_guide_clips.py
```

#### macOS / Linux (bash 또는 zsh)

```bash
python scripts/build_safety_db.py
# data/safety_guidelines.json → data/chroma_db (보행 안전 수칙)
python scripts/build_convenience_db.py
# data/convenience_guidelines.json → data/chroma_db/convenience_guidelines (생활지원 RAG)
# 사전 요건: ollama pull bge-m3 (생활지원 RAG 임베딩 전용)
# 선택: python scripts/build_guide_clips.py
```

---

## 환경 변수

> **단일 명세**: 환경 변수의 전체 목록·타입·필수 여부·기본값·참조는 [`docs/ops/environment_variables.md`](docs/ops/environment_variables.md)를 기준으로 합니다. 본 표는 핵심 변수 요약만 제공합니다.

| 변수                | 설명                                      | 기본값                   |
| ------------------- | ----------------------------------------- | ------------------------ |
| `LLM_PROVIDER`      | LLM 공급자 (`ollama` 또는 `openai`)       | `ollama`                 |
| `OLLAMA_BASE_URL`   | Ollama 서버 주소                          | `http://localhost:11434` |
| `COMPOSE_OLLAMA_BASE_URL` | Docker FastAPI 컨테이너에서 호스트 Ollama로 접속할 주소 | `http://host.docker.internal:11434` |
| `GEMMA_MODEL`       | L2 가이드 생성 모델                       | `gemma4:e4b`             |
| `GOOGLE_API_KEY`    | 4단계 캡셔닝(Gemini) API 키               | (필수, 미설정 시 빌드 실패) |
| `EMBEDDING_MODEL`   | 임베딩 모델                               | `nomic-embed-text`       |
| `REDIS_URL`         | Redis 연결 URL                            | `redis://localhost:6379` |
| `CHROMA_PATH`       | ChromaDB persist 디렉토리                 | `data/chroma_db`         |
| `CHROMA_COLLECTION` | ChromaDB 콜렉션명                         | `safety_guidelines`      |
| `WS_HOST`           | WebSocket 서버 바인드 호스트              | `0.0.0.0`                |
| `WS_PORT`           | WebSocket 서버 포트                       | `8000`                   |
| `DETECTOR_TYPE`     | 탐지기 유형 (`mock` 또는 `yolo`)          | `mock`                   |
| `TTS_ENGINE`        | TTS 엔진 (`edge` 한국어 자연도/`supertonic` 로컬 기본/`piper`/`pyttsx3` 핫스왑) | `supertonic` |
| `HEARTBEAT_TIMEOUT` | WS 하트비트 유예 타임아웃(초)             | `15`                     |
| `TMAP_APP_KEY`      | TMAP 보행자 경로 안내 API 키(내비게이션)  | (미설정)                 |
| `DB_HOST`           | MariaDB 접속 호스트                       | (필수, IP 지정)          |
| `YOLO_CONF`         | Yolo 26N - Segmentation 신뢰도 임계값       | `0.35`                   |
| `YOLO_DET_CONF`     | Yolo 26N - Object Detection 신뢰도 임계값   | `0.50`                   |
| `FRAME_SIZE`        | 프레임 리사이즈 크기                      | `640`                    |
| `REFLEX_FPS`        | 반사 캡처 목표 fps                        | `10`                     |
| `COGNITIVE_FPS`     | 인지 캡처 목표 fps                        | `2`                      |
| `OPENAI_API_KEY`    | OpenAI 전환 시 필요                       | (미설정)                 |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL (경보 발행, 우선) | (미설정)                 |
| `SLACK_BOT_TOKEN`   | Slack Web API Bot Token (폴백)            | (미설정)                 |
| `SLACK_CHANNEL_ID`  | Slack Bot Token 발송 대상 채널 ID        | (코드 내 폴백값)         |

전체 목록은 [`.env.example`](.env.example) 및 [`docs/ops/environment_variables.md`](docs/ops/environment_variables.md)를 참조합니다.

---

## 팀 분업 (5인 MVP)

개인 문서 폴더는 사용하지 않으며, 모든 설계 문서는 `docs/` 폴더에서 공유로 관리합니다.

| 이니셜 | 담당 영역 (할당 가능)              |
| ------ | ---------------------------------- |
| `dg`   | (할당 가능)                        |
| `jh`   | (할당 가능)                        |
| `jy`   | (할당 가능)                        |
| kb   | 3단계 AI 장애물 실시간 인식, 6단계 종합 회피 가이드 생성 |
| `th`   | (할당 가능)                        |

단계별 분업 인원수 제안은 [`docs/design/minchodan_design_note.md`](docs/design/minchodan_design_note.md) 각 단계의 **분업** 필드를 참조합니다. 브랜치 전략은 [`docs/ops/git_branching_strategy.md`](docs/ops/git_branching_strategy.md)를 따릅니다.

---

## 문서 인덱스

| 문서                 | 파일                                                               | 설명                                           |
| -------------------- | ------------------------------------------------------------------ | ---------------------------------------------- |
| 설계 노트 (원본)     | [`docs/design/minchodan_design_note.md`](docs/design/minchodan_design_note.md)   | 7단계 골격, 비전 v1.1 반영                     |
| **코딩 패턴 기준**   | [`docs/dev-guides/course_codebase_guide.md`](docs/dev-guides/course_codebase_guide.md)   | **수업 전체 코딩 패턴·함수 시그니처 표준 (필수 준수)** |
| 문서 인덱스          | [`docs/README.md`](docs/README.md)                                 | 문서 목록 및 권장 독해 순서                    |
| **보안 강화 및 팀 반영 가이드** | [`docs/security/security_hardening_and_team_adoption_guide.md`](docs/security/security_hardening_and_team_adoption_guide.md) | **인증·전송·컨테이너·의존성 보안 조치와 팀 적용·검증 절차** |
| 에이전트 가이드      | [`AGENTS.md`](AGENTS.md)                                           | 코딩·커뮤니케이션 규칙, 기술 스택, 문서 인덱스 |
| 백엔드 DB 설계 원칙 | [`docs/design/backend_db_architecture.md`](docs/design/backend_db_architecture.md) | 백엔드 코어 비동기 SQLAlchemy 기반 3계층 아키텍처 및 에러 방어 로직 설계 |
| 시스템 아키텍처      | [`docs/design/architecture.md`](docs/design/architecture.md)                     | 이중 경로 구조, 컴포넌트 상세, 데이터 계약, MCP 연동 |
| API 명세서           | [`docs/design/api_specification.md`](docs/design/api_specification.md)           | WebSocket `/ws/detect` 계약, 이벤트 타입       |
| 테스트 명세서        | [`docs/ops/test_specification.md`](docs/ops/test_specification.md)         | 7단계별 완료 기준, 검증 매트릭스               |
| Git 브랜칭 전략      | [`docs/ops/git_branching_strategy.md`](docs/ops/git_branching_strategy.md) | 3계층 브랜치 구조, 작업 규칙                   |
| 파이프라인 단계 설계 | [`docs/design/pipeline_stage_design.md`](docs/design/pipeline_stage_design.md)   | 7단계 run mode, 종단 지연 목표                 |
| **환경 변수 명세서** | [`docs/ops/environment_variables.md`](docs/ops/environment_variables.md)   | **환경 변수 단일 명세 (3원화 해소)**           |
| **배포 가이드**      | [`docs/ops/deployment_guide.md`](docs/ops/deployment_guide.md)             | **Docker 컨테이너 구성·배포 절차·TC-SMOKE-004** |
| 2단계 캡처 설계서    | [`docs/stage-guides/stage2_capture_design.md`](docs/stage-guides/stage2_capture_design.md) | 2단계 백엔드 FastAPI 구현 설계 (이중 스트림, asyncio.Queue) |
| 3단계 탐지 설계서    | [`docs/stage-guides/stage3_detection_design.md`](docs/stage-guides/stage3_detection_design.md) | 3단계 백엔드 FastAPI 구현 설계                |
| 6단계 오케스트레이션 설계서 | [`docs/stage-guides/stage6_orchestration_design.md`](docs/stage-guides/stage6_orchestration_design.md) | 6단계 종합 회피 가이드 생성 설계       |
| 보행이론 인사이트    | [`docs/design/behavior_and_risk_insight.md`](docs/design/behavior_and_risk_insight.md) | 보행지도사 이론 기반 행동 패턴 및 위험도 게이트 정의 |
| 에이전트 스킬 가이드 | [`SKILLS.md`](SKILLS.md)                                           | 시작 시퀀스, 문서 규칙, 금지 행위, 스킬 인덱스 |
| 단계별 구현 스킬     | `.agents/skills/`                                                  | 1~7단계별 SKILL.md + references (7종)          |

---

## 최근 변경 사항

변경 사항은 가독성 및 관리 효율을 위해 [`docs/changelogs/`](docs/changelogs/) 폴더에서 **팀원별 단일 파일**로 관리합니다.

- 각 팀원은 본인 이니셜 파일(`[이니셜].md`)에 작업 로그를 **하단에 누적** 기록합니다.
- 작업 후 아래 명령을 실행하면 본인 changelog 파일에 자동으로 append됩니다.
- 전체 구조는 [`docs/changelogs/README.md`](docs/changelogs/README.md)에서 확인합니다.

| OS | 명령 |
| --- | --- |
| **Windows (PowerShell 또는 cmd)** | `scripts\postwork.bat` |
| **macOS / Linux (bash 또는 zsh)** | `bash scripts/postwork.sh` |

---

## 검증 기준선 (계획)

### Windows (PowerShell)

```powershell
python tests\test_ws_echo.py          # 1단계: RTT < 100ms
python tests\test_frame_decode.py     # 2단계: 캡처수신 < 50ms
python tests\test_detection.py        # 3단계: conf≈0.87, < 80ms
python tests\test_retriever.py        # 5단계: kickboard 쿼리 < 50ms
python tests\test_langgraph.py        # 6단계: bollard  20자/방향 포함
python tests\test_reflex_and_nav.py   # 7단계: 반사 클립 선점 재생
python scripts\eval_hitrate.py        # 4단계: Top-5 hit-rate >= 0.6
python scripts\verify_gpu.py          # Windows GPU: CUDA 13.0 + 실제 연산 검증
```

### macOS / Linux (bash 또는 zsh)

```bash
python tests/test_ws_echo.py          # 1단계: RTT < 100ms
python tests/test_frame_decode.py     # 2단계: 캡처수신 < 50ms
python tests/test_detection.py        # 3단계: conf≈0.87, < 80ms
python tests/test_retriever.py        # 5단계: kickboard 쿼리 < 50ms
python tests/test_langgraph.py        # 6단계: bollard  20자/방향 포함
python tests/test_reflex_and_nav.py   # 7단계: 반사 클립 선점 재생
python scripts/eval_hitrate.py        # 4단계: Top-5 hit-rate >= 0.6
python scripts/verify_gpu.py          # Ubuntu CUDA 13.0 또는 macOS MPS/CPU 검증
```

상세 검증 기준은 [`docs/ops/test_specification.md`](docs/ops/test_specification.md)를 참조합니다.
