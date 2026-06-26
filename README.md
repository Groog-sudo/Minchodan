> [!IMPORTANT]
> **이 저장소에서 작업할 때는 먼저 [`docs/AGENTS.md`](docs/AGENTS.md), [`docs/README.md`](docs/README.md), [`skills.md`](skills.md)를 읽고 프로젝트 규칙과 문서 기준선을 확인합니다.

# Minchodan (민초단)

**Minchodan**은 시각장애인 보행 보조를 위한 스마트 가이드독 AI 플랫폼입니다. 스마트폰 카메라로 주변을 인식하고, GPU 서버에서 실시간으로 장애물·노면 상태를 탐지한 뒤, 음성과 햅틱으로 즉시 안내합니다. 안전 대응은 **반사 경로**(즉시 경보)와 **인지 경로**(상세 가이드) 두 갈래로 물리 분리하는 것이 핵심 원칙입니다.

> **작성일**: 2026-06-24
> **버전**: v0.1.0 (MVP 골격 기준선)
> **설계 기준**: `docs/minchodan_design_note.md` (7단계 골격, 비전 설계서 v1.1 반영)

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
| 3    | AI 장애물 실시간 인식 (듀얼헤드)  | Yolo 26N - Object Detection, Yolo 26N - Segmentation, ByteTrack | 킥보드 conf≈0.87, **Detection < 80ms**     |
| 4    | 위험 대처 수칙 DB 구축 (RAG 시드) | Ollama(Llava), ChromaDB, nomic-embed                            | collection ≥ 100, **Top-5 hit-rate ≥ 0.6** |
| 5    | 실시간 대처 수칙 검색 (RAG)       | ChromaDB                                                        | kickboard 쿼리 정합, **검색 < 50ms**       |
| 6    | 종합 회피 가이드 생성 (계층 LLM)  | LangGraph, ChatOllama(Gemma2)                                   | bollard 주입 시 20자 내·방향 포함          |
| 7    | 음성 안내 출력 (이중 채널)        | Kokoro/Coqui, Web Audio, Haptics                                | 반사 클립 선점 재생, 햅틱 동시 출력        |

상세 설계는 [`docs/minchodan_design_note.md`](docs/minchodan_design_note.md)와 [`docs/architecture.md`](docs/architecture.md)를 참조합니다.

---

## 기술 스택

### 서버 (GPU 추론)

- Python 3.13, FastAPI, uvicorn
- Ultralytics Yolo 26N - Object Detection, Yolo 26N - Segmentation
- ByteTrack (객체 추적)
- Redis (Streams 이벤트 버스 + 컨텍스트 TTL)
- LangGraph + LangChain (L1/L2/L3 오케스트레이션)
- Ollama (Llava 캡셔닝, Gemma2 가이드 생성, nomic-embed-text 임베딩)
- ChromaDB (로컬 벡터 저장소)
- Kokoro-82M / Coqui (로컬 TTS)
- OpenCV (프레임 디코딩)

### 클라이언트 (단말)

- React Native (iOS/Android 동시 대응)
- react-native-vision-camera (후면 카메라, 이중 캡처 타이머)
- Web Audio API (인지 음성 재생)
- react-native-tts (예비 TTS)
- Haptics + announceForAccessibility (접근성)

### 운영 콘솔

- React (운영자 모니터링용)
- SSE/WebSocket 구독 (탐지 피드, RiskEvent 로그, 세션 상태)

### 인프라

- Docker (Redis + Ollama + FastAPI 컨테이너 구성)
- CUDA 12.8 + cu128 PyTorch 휠 (Blackwell sm_120 전제)

---

## 디렉토리 구조

```shell
Minchodan/
│
├── server/                          # GPU 서버 (FastAPI)
│   ├── api/                         # WebSocket /ws/detect, 세션, 하트비트
│   ├── capture/                     # 프레임 디코딩, 이중 스트림 분기
│   ├── detection/                   # Yolo 26N - Object Detection, Yolo 26N - Segmentation, ByteTrack, Gates
│   │   └── gates/                   # Reflex Gate, Surface Gate
│   ├── rag/                         # Vector DB 구축·검색
│   │   └── build/                   # 오프라인 배치 (캡셔닝, 임베딩)
│   ├── orchestration/               # LangGraph L1/L2/L3
│   │   └── nodes/                   # 분류, 생성, 검증, fallback
│   ├── tts/                         # 실시간 TTS, 반사 클립 전송, 억제
│   ├── bus/                         # Redis Streams 인터페이스
│   └── models/                      # 모델 가중치 (git-ignore)
│       └── yolo26n/
│
├── client/                          # React Native 앱 (thin client)
│   └── src/
│       ├── hooks/                   # useWebSocket, useCamera
│       ├── services/                # frameCapture, audioPlayer, reflexClipPlayer
│       ├── components/              # CameraView
│       └── utils/                   # haptics
│
├── console/                         # React 운영자 모니터링 콘솔
│   └── src/
│       ├── components/              # DetectionFeed, RiskEventLog, SessionStatus
│       └── hooks/                   # useSSE
│
├── data/                            # 학습·RAG 데이터
│   ├── raw/                         # AI Hub 보행자 데이터셋 원본
│   ├── frames/                      # 1fps 추출 프레임
│   ├── deduped/                     # pHash 중복 제거 후 프레임
│   ├── captions/                    # Llava 캡셔닝 결과 JSON
│   ├── chroma_db/                   # ChromaDB persist 디렉토리
│   └── reflex_clips/                # 사전합성 반사 음성 클립
│
├── training/                        # 모델 학습 (오프라인)
│   ├── datasets/                    # detection, segmentation
│   ├── configs/                     # yolo26n_detection.yaml, yolo26n_segmentation.yaml
│   ├── train_detection.py
│   ├── train_segmentation.py
│   └── export_tensorrt.py
│
├── scripts/                         # 유틸리티 스크립트
├── tests/                           # 7단계별 검증 테스트
├── docker/                          # Docker Build & Setting
├── docs/                            # 설계 문서 및 가이드
├── .env.example                     # 환경변수 템플릿
├── requirements.txt                 # 파이썬 의존성
└── README.md
```

상세 구조는 [`directory_Structure.md`](directory_Structure.md)를 참조합니다.

---

## 빠른 시작

### 1. 환경 변수 설정

#### Windows (PowerShell)

```powershell
Copy-Item .env.example .env
# LLM_PROVIDER, REDIS_URL, CHROMA_PATH, OLLAMA_BASE_URL 등을 설정합니다.
```

#### macOS / Linux (bash 또는 zsh)

```bash
cp .env.example .env
# LLM_PROVIDER, REDIS_URL, CHROMA_PATH, OLLAMA_BASE_URL 등을 설정합니다.
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

### 3. GPU 환경 검증 (Blackwell sm_120 / CUDA 12.8)

#### Windows (PowerShell)

```powershell
python scripts\verify_gpu.py
# device_capability >= (12, 0) 및 GPU 1 step 연산 검증
```

#### macOS / Linux (bash 또는 zsh)

```bash
python scripts/verify_gpu.py
# device_capability >= (12, 0) 및 GPU 1 step 연산 검증
```

> CUDA 12.8 + cu128 PyTorch 휠이 필요합니다. 11.8/12.1 휠은 silent CPU 폴백이 발생합니다.

### 4. Docker 구성 (Redis + Ollama + FastAPI)

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

#### Windows (PowerShell, Git Bash 또는 WSL bash 필요)

```powershell
bash scripts/build_chroma.sh
# 영상  1fps 프레임 추출  pHash 중복 제거  Llava 캡셔닝  임베딩  ChromaDB persist
```

#### macOS / Linux (bash 또는 zsh)

```bash
bash scripts/build_chroma.sh
# 영상  1fps 프레임 추출  pHash 중복 제거  Llava 캡셔닝  임베딩  ChromaDB persist
```

---

## 환경 변수

| 변수                | 설명                                      | 기본값                   |
| ------------------- | ----------------------------------------- | ------------------------ |
| `LLM_PROVIDER`      | LLM 공급자 (`ollama` 또는 `openai`)       | `ollama`                 |
| `OLLAMA_BASE_URL`   | Ollama 서버 주소                          | `http://localhost:11434` |
| `GEMMA_MODEL`       | L2 가이드 생성 모델                       | `gemma2:9b`              |
| `LLAVA_MODEL`       | 4단계 캡셔닝 모델                         | `llava`                  |
| `EMBEDDING_MODEL`   | 임베딩 모델                               | `nomic-embed-text`       |
| `REDIS_URL`         | Redis 연결 URL                            | `redis://localhost:6379` |
| `CHROMA_PATH`       | ChromaDB persist 디렉토리                 | `data/chroma_db`         |
| `CHROMA_COLLECTION` | ChromaDB 컬렉션명                         | `bidding_kb`             |
| `WS_PORT`           | WebSocket 서버 포트                       | `8000`                   |
| `TTS_ENGINE`        | TTS 엔진 (`kokoro` 또는 `coqui`)          | `kokoro`                 |
| `YOLO_CONF`         | Yolo 26N - Object Detection 신뢰도 임계값 | `0.35`                   |
| `FRAME_SIZE`        | 프레임 리사이즈 크기                      | `640`                    |
| `REFLEX_FPS`        | 반사 캡처 목표 fps                        | `10`                     |
| `COGNITIVE_FPS`     | 인지 캡처 목표 fps                        | `2`                      |

전체 목록은 [`.env.example`](.env.example)을 참조합니다.

---

## 팀 분업 (5인 MVP)

개인 문서 폴더는 사용하지 않으며, 모든 설계 문서는 `docs/` 폴더에서 공유로 관리합니다.

| 이니셜 | 담당 영역 (할당 가능)              |
| ------ | ---------------------------------- |
| `dg`   | (할당 가능)                        |
| `jh`   | (할당 가능)                        |
| `jy`   | (할당 가능)                        |
| `kb`   | 3단계 AI 장애물 실시간 인식        |
| `th`   | (할당 가능)                        |

단계별 분업 인원수 제안은 [`docs/minchodan_design_note.md`](docs/minchodan_design_note.md) 각 단계의 **분업** 필드를 참조합니다. 브랜치 전략은 [`docs/git_branching_strategy.md`](docs/git_branching_strategy.md)를 따릅니다.

---

## 문서 인덱스

| 문서                 | 파일                                                               | 설명                                           |
| -------------------- | ------------------------------------------------------------------ | ---------------------------------------------- |
| 설계 노트 (원본)     | [`docs/minchodan_design_note.md`](docs/minchodan_design_note.md)   | 7단계 골격, 비전 v1.1 반영                     |
| 문서 인덱스          | [`docs/README.md`](docs/README.md)                                 | 문서 목록 및 권장 독해 순서                    |
| 에이전트 가이드      | [`docs/AGENTS.md`](docs/AGENTS.md)                                 | 코딩·커뮤니케이션 규칙, 기술 스택              |
| 시스템 아키텍처      | [`docs/architecture.md`](docs/architecture.md)                     | 이중 경로 구조, 컴포넌트 상세, 데이터 계약     |
| API 명세서           | [`docs/api_specification.md`](docs/api_specification.md)           | WebSocket `/ws/detect` 계약, 이벤트 타입       |
| 테스트 명세서        | [`docs/test_specification.md`](docs/test_specification.md)         | 7단계별 완료 기준, 검증 매트릭스               |
| Git 브랜칭 전략      | [`docs/git_branching_strategy.md`](docs/git_branching_strategy.md) | 3계층 브랜치 구조, 작업 규칙                   |
| 파이프라인 단계 설계 | [`docs/pipeline_stage_design.md`](docs/pipeline_stage_design.md)   | 7단계 run mode, 종단 지연 목표                 |
| 에이전트 스킬 가이드 | [`skills.md`](skills.md)                                           | 시작 시퀀스, 문서 규칙, 금지 행위, 스킬 인덱스 |
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
python tests\test_rag_retrieval.py    # 5단계: kickboard 쿼리 < 50ms
python tests\test_langgraph.py        # 6단계: bollard  20자/방향 포함
python tests\test_tts_reflex.py       # 7단계: 반사 클립 선점 재생
python scripts\eval_hitrate.py        # 4단계: Top-5 hit-rate >= 0.6
python scripts\verify_gpu.py          # GPU: sm_120 + CUDA 12.8 검증
```

### macOS / Linux (bash 또는 zsh)

```bash
python tests/test_ws_echo.py          # 1단계: RTT < 100ms
python tests/test_frame_decode.py     # 2단계: 캡처수신 < 50ms
python tests/test_detection.py        # 3단계: conf≈0.87, < 80ms
python tests/test_rag_retrieval.py    # 5단계: kickboard 쿼리 < 50ms
python tests/test_langgraph.py        # 6단계: bollard  20자/방향 포함
python tests/test_tts_reflex.py       # 7단계: 반사 클립 선점 재생
python scripts/eval_hitrate.py        # 4단계: Top-5 hit-rate >= 0.6
python scripts/verify_gpu.py          # GPU: sm_120 + CUDA 12.8 검증
```

상세 검증 기준은 [`docs/test_specification.md`](docs/test_specification.md)를 참조합니다.
