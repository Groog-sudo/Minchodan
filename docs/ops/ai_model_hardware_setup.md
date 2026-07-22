> **작성일**: 2026-07-05
> **수정일**: 2026-07-19
> **버전**: v1.4.0 (RTX 5090 최대 사양 및 Ubuntu·Windows·macOS PyTorch 2.13 호환성 반영)
> **설계 기준**: docs/ops/deployment_guide.md (v0.5.6)

# Minchodan AI 모델 및 하드웨어 구성 지침

본 문서는 인공지능 코딩 에이전트와 팀원들이 GPU/CPU 추론 서버 인프라를 셋업할 때 참조할 하드웨어 사양 요건 및 호스트 로컬 Ollama 모델 구성 지침서입니다.

---

## 1. 하드웨어 요건 및 드라이버 스펙

### 1.1 팀 지원 운영체제 및 가속 경로

| 운영체제 | 팀 사용 범위 | PyTorch 의존성 | 가속기·드라이버 기준 |
| :--- | :--- | :--- | :--- |
| **Ubuntu x86_64** | 운영 GPU 서버·학습 | `torch==2.13.0+cu130`, `torchvision==0.28.0+cu130` | 팀 최대 RTX 5090(Blackwell sm_120), NVIDIA R580 이상 드라이버 |
| **Windows amd64** | 운영 GPU 서버·학습·개발 | `torch==2.13.0+cu130`, `torchvision==0.28.0+cu130` | 팀 최대 RTX 5090(Blackwell sm_120), NVIDIA R580 이상 드라이버를 별도 설치 |
| **macOS Apple Silicon** | 로컬 개발·기능 검증 | `torch==2.13.0`, `torchvision==0.28.0` | Apple MPS 우선, 미지원 시 CPU 폴백. CUDA 서버로 분류하지 않음 |

> `requirements.txt`의 환경 마커가 위 세 경로를 자동 선택합니다. Ubuntu·Windows의 cu130 휠은 CUDA 런타임을 포함하므로 일반 실행에 호스트 CUDA Toolkit 전체 설치가 필수는 아니지만, NVIDIA 드라이버는 R580 이상이어야 합니다. 커스텀 CUDA 확장이나 TensorRT 엔진을 빌드할 때는 호환 CUDA 13.x Toolkit을 별도로 설치합니다. RAM은 16GB 이상을 기본으로 하고, GPU 서버 VRAM은 모델·배치 크기에 맞추되 팀 최대 사양은 RTX 5090 32GB입니다.

### 1.2 GPU 가속 연결 검증
개발자는 컨테이너 기동 전 호스트 OS에서 다음 스크립트로 실제 가속 연산을 검증해야 합니다:
```bash
python scripts/verify_gpu.py
```
이 스크립트는 Ubuntu·Windows에서 CUDA 13 이상과 GPU 1 step 연산을 필수 확인합니다. RTX 5090의 sm_120보다 낮은 이전 세대 GPU는 경고 후 개발용 실행을 허용합니다. macOS에서는 MPS 1 step 연산을 우선 검증하고, MPS를 사용할 수 없을 때만 CPU 폴백을 검증합니다.

---

## 2. Ollama 로컬 모델 구성 및 풀링 (Pull)

추론 서버의 LangGraph 오케스트레이터 및 RAG 검색을 위해 호스트 로컬 Ollama에 모델 패키지를 내려받아야 합니다. Docker Compose는 Ollama 컨테이너를 만들지 않으며, FastAPI 컨테이너가 `COMPOSE_OLLAMA_BASE_URL`을 통해 호스트 Ollama에 접속합니다.

WSL2처럼 `systemd`가 실행되지 않는 환경에서는 서비스 등록이 되더라도 자동 기동되지 않을 수 있습니다. 이 경우 Linux 시작 스크립트가 `ollama serve`를 백그라운드로 실행합니다. 기본 바인딩은 안전한 루프백(`127.0.0.1:11434`)이며, Docker 컨테이너에서 호스트 Ollama에 직접 접근해야 할 때만 `MINCHODAN_EXPOSE_OLLAMA=1`과 `OLLAMA_HOST=0.0.0.0:11434`를 함께 설정합니다.

### 2.1 모델 패킹 정보 및 용량 명세

| 모델 식별자 (Model Tag) | 모델 계열 및 성격 | 메모리상 로드 용량 | 용도 및 역할 |
| :--- | :--- | :--- | :--- |
| **`gemma4:e4b`** | Google Gemma 4세대 Edge 최적화 LLM | **약 9.6 GB** | 6단계 LangGraph의 L2 노드 한국어 가이드 문장 생성 |
| **`nomic-embed-text`** | 로컬 768차원 텍스트 임베딩 모델 | **약 274 MB** | 5단계 실기기 RAG 검색 수칙의 벡터 차원 변환 및 정밀도 수치 연산 |

> 현재 4단계 오프라인 캡셔닝은 Gemini API(`gemini-2.5-flash-lite`) 기준입니다. `llava`는 구 로컬 VLM 계획 또는 별도 실험 경로에서만 선택적으로 내려받습니다.

### 2.2 모델 풀링 및 다운로드 명령어
호스트 터미널에서 최초 1회 각각 실행하여 다운로드합니다:
```bash
# WSL/Linux에서 수동으로 안전하게 띄울 때
OLLAMA_HOST=127.0.0.1:11434 ollama serve

# 신뢰할 수 있는 로컬망에서 전체 인터페이스 바인딩이 꼭 필요할 때만
MINCHODAN_EXPOSE_OLLAMA=1 OLLAMA_HOST=0.0.0.0:11434 ollama serve

# gemma4:e4b 모델 (9.6GB) 수신
ollama pull gemma4:e4b

# nomic-embed-text 모델 (274MB) 수신
ollama pull nomic-embed-text
```

---

## 3. Ollama 서버 환경 최적화 설정

서버 기동 시 `.env` 환경 변수를 바탕으로 Ollama 서버의 동시 모델 적재 정책을 튜닝하여 메모리 부족(OOM) 오류를 예방합니다:

- **`OLLAMA_MAX_LOADED_MODELS=2`**: 메모리(VRAM) 내에 생성 모델(`gemma4:e4b`)과 임베딩 모델(`nomic-embed-text`) 두 개가 스왑 지연 없이 동시에 상주하도록 허용합니다. (VRAM이 6GB 이하로 부족한 환경에서는 `1`로 낮추어 설정합니다.)
- **`OLLAMA_KEEP_ALIVE=30m`**: 한 번 VRAM에 로드된 모델을 30분간 유지시켜, 첫 캡처 수신 시의 스타트 지연을 최소화합니다.
- **`OLLAMA_HOST=127.0.0.1:11434`**: 기본값입니다. 호스트 로컬 CLI와 서버 직접 실행에 사용합니다.
- **`MINCHODAN_EXPOSE_OLLAMA=1` + `OLLAMA_HOST=0.0.0.0:11434`**: Docker 컨테이너가 호스트 Ollama에 접속해야 할 때만 명시적으로 사용합니다. 개인 개발망에서만 사용하고, 외부망 노출 환경에서는 방화벽으로 포트 `11434` 접근을 제한합니다.
