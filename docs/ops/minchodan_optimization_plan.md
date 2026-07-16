# 민초단 전체 최적화 계획

> **작성일**: 2026-07-09
> **버전**: v1.0
> **목표**: 커스텀 YOLO 탐지 + 자연스러운 TTS, 갤럭시 S25 Ultra 실기기 정상 구동

---

## 현황 진단

### PC 환경 제약

| 항목 | 사양 | 영향 |
| :--- | :--- | :--- |
| CPU | i7-8700 (6코어/12스레드) | YOLO CPU 추론 가능 |
| RAM | 16GB (실가용 719MB) | **심각** - Ollama가 6.26GB 단독 점유 |
| GPU | 없음 | 모든 추론 CPU 전담 |
| OS | Windows 10 Pro | Docker Desktop 사용 |

### Docker 메모리 현황

| 컨테이너 | 메모리 사용 | 비율 |
| :--- | :--- | :--- |
| minchodan-ollama | **6.26 GiB** | 81.4% |
| minchodan-fastapi | 312 MiB | 4.0% |
| minchodan-redis | 3.3 MiB | 0.04% |
| **Docker 총합** | **~6.6 GiB** | ~86% |
| **호스트 잔여** | **~719 MB** | 위험 수준 |

### 핵심 문제

1. **검은 화면**: `npx expo start` 실행 시 Metro 번들러가 즉시 종료(`Stopped server`)됨. 연결할 Metro 서버가 없으므로 앱이 JS 번들을 로드하지 못해 검은 화면.
2. **Expo 모드**: `npx expo start`가 Expo Go 모드로 시작했다가 dev-client 전환 시 URI scheme 경고 발생. `scheme: "minchodan"` 추가 완료했지만 네이티브 재빌드 없이는 반영 안 됨.
3. **TTS 고정 문구**: Ollama가 메모리를 거의 다 차지해 불안정 → LLM 응답 실패 → L3 폴백 문구 반복.
4. **YOLO 모델 적용 완료**: `.env` 수정 + `docker compose up` 으로 `best_20260705.pt` / `best.pt` 로드 성공.

---

## 근본 원인 분석

### Metro Stopped Server 원인

`npx expo start`가 `Stopped server`를 출력하고 종료되는 것은 아래 중 하나:
- `--dev-client` 모드에서 android 네이티브 디렉토리에 scheme이 없어 즉시 에러 처리
- 이전 Metro 포트(8081)가 아직 점유 중이어서 포트 충돌

### TTS 고정 문구 원인

- `minchodan-ollama` 컨테이너가 6.26GB RAM 사용 → 호스트 가용 RAM 719MB
- Metro 번들러 + Windows 프로세스들이 남은 메모리 경합
- Ollama가 메모리 부족으로 불안정 → LLM 타임아웃 → L3 폴백

---

## 개선 전략: Ollama 대신 Gemini API로 전환

> [!IMPORTANT]
> **핵심 결정**: 로컬 Ollama(`gemma4:e4b`, 6.26GB RAM)를 **Gemini API**로 교체.
> `.env`에 이미 `GOOGLE_API_KEY`가 있고, `LLMClientFactory`에 핫스왑 지원이 구현되어 있음.
> 이렇게 하면 Docker 메모리 사용량이 ~6.6GB → ~320MB로 급감하고 Metro/앱 안정성이 크게 향상됨.

### 예상 효과

| 항목 | 변경 전 | 변경 후 |
| :--- | :--- | :--- |
| Docker 메모리 | 6.6 GB | ~320 MB |
| 호스트 가용 RAM | 719 MB | ~6.5 GB |
| LLM 응답 시간 | 30~120초 (CPU) | 1~3초 (API) |
| TTS 다양성 | 폴백 고정 | 실제 문서 기반 |
| Metro 안정성 | 불안정 | 안정 |

---

## 수정 계획 (우선순위 순)

---

### 1단계: Ollama 컨테이너 중지 + Gemini API 전환

#### [MODIFY] `.env`
- `LLM_PROVIDER=gemini` 로 변경
- `GEMINI_MODEL=gemini-2.0-flash-lite` 추가

#### [MODIFY] `server/orchestration/llm_client_factory.py`
- `gemini` provider 분기 추가 (langchain-google-genai 사용)
- `GeminiClient` 클래스 구현

#### [MODIFY] `docker/docker-compose.yml`
- `ollama` 서비스 주석 처리 또는 `depends_on` 제거
- `fastapi` 서비스에서 `ollama` 의존성 제거

---

### 2단계: Metro 번들러 안정화 (검은 화면 해결)

#### 원인
Metro가 `Stopped server`를 출력하는 이유: Android 네이티브 디렉토리에 URI scheme이 없는 상태에서 dev-client 모드를 강제 전환하면 expo가 오류를 감지하고 즉시 종료.

#### 해결책
`npx expo start --scheme minchodan` 옵션으로 scheme을 명령줄에서 직접 지정.

또는 `package.json`의 `scripts`에 `"start:android": "expo start --scheme minchodan"` 추가.

> [!NOTE]
> `app.json`에 `scheme` 추가는 완료됐음. `--scheme` 옵션은 네이티브 디렉토리 scheme이 없어도 expo가 강제로 인식하게 하는 임시 우회책.

---

### 3단계: TTS 안정성 확보

#### [MODIFY] `server/tts/realtime_tts.py`
- Gemini API 전환 후 LLM 응답 속도 향상 → TTS 생성 타임아웃 여유 있음
- 현재 타임아웃 15초는 유지 (안전망)

#### RAG 지식 베이스 활용 확인
- `data/reflex_guidelines.json` / `data/safety_guidelines.json` 이미 존재
- ChromaDB 빌드 상태 확인 필요

---

### 4단계: `requirements.txt`에 langchain-google-genai 추가

FastAPI 컨테이너에 Gemini 라이브러리 설치 필요.

---

## 검증 계획

### 자동 검증
```bash
docker logs minchodan-fastapi --follow
# "GeminiClient 로드 성공" 로그 확인
# "YoloDetector 로드 성공: best_20260705.pt" 유지 확인
```

### 수동 검증 (스마트폰)
1. Ollama 컨테이너 중지 후 Docker 메모리 확인
2. `reverse.bat` 더블클릭 → ADB reverse 포트 포워딩
3. `npx expo start --scheme minchodan` 실행 (Metro 안정 유지 확인)
4. 스마트폰 Minchodan 앱 직접 터치 → 카메라 화면 + BBox 표시 확인
5. 실제 물체(사람, 의자, 병)를 카메라 앞에 세우고 TTS 안내 문구 확인

---

## 오픈 질문

없음. 진행 가능.
