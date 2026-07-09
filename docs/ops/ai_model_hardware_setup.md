> **작성일**: 2026-07-05
> **버전**: v1.2.0 (2026-07-09 Ollama를 Docker 컨테이너가 아닌 호스트 로컬 프로세스로 실행하도록 정정)
> **설계 기준**: docs/ops/deployment_guide.md (v0.5.0)

# Minchodan AI 모델 및 하드웨어 구성 지침

본 문서는 인공지능 코딩 에이전트와 팀원들이 GPU/CPU 추론 서버 인프라를 셋업할 때 참조할 하드웨어 사양 요건 및 호스트 로컬 Ollama 모델 구성 지침서입니다.

---

## 1. 하드웨어 요건 및 드라이버 스펙

### 1.1 GPU 권장 및 필수 하위 한계선

| 분류 | 권장사양 (GPU 가속) | 최소사양 (CPU Fallback) |
| :--- | :--- | :--- |
| **장치 (Device)** | **NVIDIA RTX 3060 / 4080** 이상<br/>(Blackwell sm_120 아키텍처 지원 권장) | macOS (Apple Silicon M1/M2/M3)<br/>또는 외장 GPU 없는 Windows 데스크톱 |
| **CUDA 버전** | **CUDA 12.8** 이상 필수 (권장 사양) | N/A (CPU 구동) |
| **NVIDIA Driver** | **v550.x** 이상 필수 | N/A |
| **VRAM / RAM** | **VRAM 8GB** 이상 / RAM 16GB 이상 | RAM 16GB 이상 (Ollama 모델 로드 전제) |

> **2026-07-07 참고**: `requirements.txt`는 `torch==2.12.1`/`torchvision==0.27.1`을 `+cu128` 태그나 `--extra-index-url` 없이 순정 PyPI 패키지로 설치하며, `docker/Dockerfile`도 `pip install -r requirements.txt`만 실행한다. 즉 cu128 빌드가 코드로 강제되어 있지 않으므로, 실제 CUDA 12.8 가속을 쓰려면 설치 환경에서 별도로 cu128 wheel을 지정해야 한다.

### 1.2 GPU 가속 연결 검증
개발자는 컨테이너 기동 전 호스트 OS 상에서 파이썬 스크립트를 통해 GPU 연계 가능 여부를 사전 검증해야 합니다:
```bash
python scripts/verify_gpu.py
```
*이 스크립트는 PyTorch의 CUDA 바인딩 여부와 BlackwellCapability 검사를 거쳐 1 step 가속 연산 통과 여부를 검증합니다.*

---

## 2. Ollama 로컬 모델 구성 및 풀링 (Pull)

추론 서버의 LangGraph 오케스트레이터 및 RAG 검색을 위해 호스트 로컬 Ollama에 모델 패키지를 내려받아야 합니다. Docker Compose는 Ollama 컨테이너를 만들지 않으며, FastAPI 컨테이너가 `COMPOSE_OLLAMA_BASE_URL`을 통해 호스트 Ollama에 접속합니다.

### 2.1 모델 패킹 정보 및 용량 명세

| 모델 식별자 (Model Tag) | 모델 계열 및 성격 | 메모리상 로드 용량 | 용도 및 역할 |
| :--- | :--- | :--- | :--- |
| **`gemma4:e4b`** | Google Gemma 4세대 Edge 최적화 LLM | **약 9.6 GB** | 6단계 LangGraph의 L2 노드 한국어 가이드 문장 생성 |
| **`nomic-embed-text`** | 로컬 768차원 텍스트 임베딩 모델 | **약 274 MB** | 5단계 실기기 RAG 검색 수칙의 벡터 차원 변환 및 정밀도 수치 연산 |

> 현재 4단계 오프라인 캡셔닝은 Gemini API(`gemini-2.5-flash-lite`) 기준입니다. `llava`는 구 로컬 VLM 계획 또는 별도 실험 경로에서만 선택적으로 내려받습니다.

### 2.2 모델 풀링 및 다운로드 명령어
호스트 터미널에서 최초 1회 각각 실행하여 다운로드합니다:
```bash
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
