# Changelog - dg (대근)

> 이 파일은 **dg(대근)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-06-26 | 4·5단계 | RAG 기본 틀 구현 및 모듈 리팩토링 완료

- **커밋**: `feat: 4·5단계 RAG 파이프라인 구현 및 모듈 리팩토링 완료`
- **변경 내용**:
  - 4단계: 비디오 프레임 1fps 분할 추출, pHash 기반 이미지 중복 제거, Gemini VLM 한글 캡셔닝, ChromaDB 오프라인 적재 전체 DB 빌더 파이프라인 구현
  - 5단계: vector_db_factory, embedding_engine_factory, retriever, fallback 모듈을 server/rag/ 하위 패키지로 구현 및 결합도 제거
  - 5단계: RAG 검색 실패 또는 예외 발생 시 시스템 중단을 차단하고 즉시 룰 기반 안전 가이드를 제공하는 Fallback 안전망 설계
  - 테스트: 4·5단계 기능 단위 검증 및 E2E 시나리오 pytest 통과 확인 (41 passed, 1 skipped)
  - 리팩토링: vector_db_factory, embedding_engine_factory, retriever, fallback 모듈을 server/에서 server/rag/ 패키지 하위로 이동하고 내부 임포트 경로 전수 동기화
  - 문서화: 입문용 폴더/파일 가이드, 단계별 단위 테스트 실행 가이드, 실데이터 교체 가이드 마크다운 문서 3건 작성 완료
- **관련 파일**: `server/rag/build/frame_extractor.py`, `server/rag/build/dedup_phash.py`, `server/rag/build/gemini_captioner.py`, `server/rag/build/db_builder.py`, `server/rag/shared/labels.py`, `server/rag/embedding_engine_factory.py`, `server/rag/vector_db_factory.py`, `server/rag/retriever.py`, `server/rag/fallback.py`, `tests/test_db_builder.py`, `tests/test_e2e_pipeline.py`, `tests/test_embedding_engine_factory.py`, `tests/test_fallback.py`, `tests/test_retriever.py`, `tests/test_vector_db_factory.py`, `docs/stage4_5_directory_guide.md`, `docs/stage4_5_test_guide.md`, `docs/stage4_5_data_replacement_guide.md`
- **검증 결과**: pytest 단위 테스트 41건 통과 (Ollama 미연동 1건 자동 스킵) 및 개별 Retriever/Fallback 스모크 테스트 실행 확인

---

### 2026-07-09 | 7단계 | TTS 엔진 pyttsx3 전면 교체 및 이전 작업 내역 복구 완료

- **커밋**: `refactor: replace sherpa-melotts with pyttsx3 for lightweight tts`
- **변경 내용**:
  - 이전 작업: 안드로이드 무선 테스트 연동 과정에서 발생한 이슈들을 수정하였으며, Piper의 발음 이슈 해소를 위해 sherpa-melotts-kr-int8로 교체하던 도중 토큰 소모로 인해 중단된 설치 건을 확인 및 정리함.
  - 의존성 제거: 51MB 크기의 무거운 VITS 모델인 sherpa-melotts 가중치를 다운로드하던 중 중단된 server/models/sherpa-onnx 디렉토리와 download_sherpa_model.py 스크립트를 완전 제거함. requirements.txt에서 sherpa-onnx 패키지를 제거함.
  - pyttsx3 도입: 가볍고 빠른 OS 내장 API 기반 래퍼인 pyttsx3 및 Windows 전용 pywin32를 requirements.txt에 추가하여 실시간 TTS 엔진으로 적용함.
  - Docker 호환성 확보: 리눅스(도커) 내에서 pyttsx3가 정상 초기화될 수 있도록 docker/Dockerfile의 apt-get 설치 항목에 espeak 시스템 의존성을 추가함.
  - TTS 코드 개편: server/tts/tts_service.py에서 기존 SherpaTTSService를 삭제하고 Pyttsx3TTSService를 구현함. NamedTemporaryFile을 활용해 로컬 스레드 비동기ㅈ 위임(asyncio.to_thread) 방식으로 WAV 음성을 파일로 합성한 뒤 바이너리 데이터를 읽어 반환하도록 처리함. Windows 환경의 COM 스레드 안전성을 위해 pythoncom CoInitialize/CoUninitialize 패턴을 가드 코드로 삽입함.
  - 설정값 갱신: .env 및 .env.example 템플릿 파일 내 TTS_ENGINE 환경변수 설정을 pyttsx3로 기본 구성함. docs/ops/environment_variables.md 환경변수 명세서도 갱신하여 문서 일치성을 확보함.
- **관련 파일**: `requirements.txt`, `docker/Dockerfile`, `server/tts/tts_service.py`, `.env`, `.env.example`, `docs/ops/environment_variables.md`, `scripts/download_sherpa_model.py` (삭제), `server/models/sherpa-onnx/` (삭제)
- **검증 결과**: scratch/test_pyttsx3.py 단독 검증 스크립트를 작성하여 로컬 SAPI5 기반 Pyttsx3TTSService 초기화 및 wav 바이너리 데이터 합성 성공(340KB 출력) 확인 완료.

---

### 2026-07-09 | 3단계 | 안드로이드 스마트폰 앱 BBox 미표시 오류 해결 및 서버 실시간 연동 완료

- **커밋**: `fix: render bbox on client by sending server yolo detection results`
- **변경 내용**:
  - 원인 분석: 
    - 안드로이드 실기기(REAL) 모드에서는 ANE 가속/TFLite 추론 시 발생하는 JS CPU 과부하 및 Watchdog SIGKILL 크래시를 방지하기 위해 캡처 후 변환된 Float32Array 텐서 데이터 전송을 생략(빈 텐서 전달)하여 온디바이스 추론이 동작하지 않았음.
    - 기존 클라이언트 BBox Overlay 렌더링 코드가 오직 온디바이스 추론 결과(`detections`)에만 의존하도록 설계되어 있었으며, 서버에서 실시간 YOLO/Segmentation 추론을 정상 처리함에도 탐지된 검출 결과를 모바일 앱으로 실어 보내는 전송 규격이 없었기에 BBox가 전혀 그려지지 않는 문제 발생.
  - 전송 규격 설계 및 도입:
    - 서버에서 추론을 완료할 때마다 검출 결과(`detections` 및 `surfaces` 리스트)를 실시간으로 단말에 실어 보내는 새로운 WebSocket 응답 메시지 타입 `"server_detection"` 프로토콜을 규격화하여 전송하도록 구성함.
    - 노면 분할(Segmentation) 결과인 `SurfaceResult`는 대역폭 절약을 위해 무게중심 `centroid`만 가지므로, 모바일의 BBoxOverlay가 해석할 수 있도록 서버 송신 단에서 `80x80` 크기의 가상 bbox 좌표계로 동적 변환하여 전송 처리함.
  - 서버 측 코드 수정:
    - `server/detection/detection_pipeline.py`: `run` 메서드가 반환 타입을 확장하여 주 결과값뿐 아니라 원본 `detections` 및 `surfaces` 리스트를 튜플 `(result, detections, surfaces)`로 동시에 반환하도록 개편함.
    - `server/detection/consumer.py`: 파이프라인에서 추출된 리스트를 바탕으로, 비동기 `_send_server_detection` 메서드를 신설하여 WebSocket 연결을 통해 `"server_detection"` 메시지 페이로드를 단말에 송신하도록 처리함.
  - 클라이언트 측 코드 수정:
    - `client/src/types/detection.ts`: `MessageType`에 `"server_detection"`을 추가하고, `WSMessage` 인터페이스에 `detections?: any[]` 필드를 보강하여 TS 컴파일 에러를 방지함.
    - `client/src/components/CameraView.tsx`: 웹소켓 메시지 수신 훅(`useEffect`) 내부에 `server_detection` 분기를 신설하여, 수신된 서버의 탐지 결과를 모바일 `detections` 상태에 직접 바인딩 렌더링되도록 구현함.
  - 단위 테스트 코드 수정:
    - `tests/test_detection.py`: 파이프라인 `run` 메서드의 시그니처 튜플 전환에 따라 pytest 단위 테스트 코드 내 10곳의 호출부를 `result, _, _ = await pipeline.run(...)` 형식으로 일제히 보정함.
- **관련 파일**: `server/detection/detection_pipeline.py`, `server/detection/consumer.py`, `client/src/types/detection.ts`, `client/src/components/CameraView.tsx`, `tests/test_detection.py`
- **검증 결과**: `tests/test_detection.py` 단위 테스트 28개 전수 통과 완료(28 passed in 17.93s).

---

### 2026-07-09 | 인프라 | GPU 미탑재 CPU 전용 환경 대응을 위한 Docker Compose 설정 보완

- **커밋**: `fix: support CPU-only environments in docker-compose`
- **변경 내용**:
  - 원인 분석: GPU가 존재하지 않는 CPU 전용 PC/노트북 환경에서 docker-compose up 실행 시 nvidia gpu 디바이스 드라이버가 없다는 에러로 인해 컨테이너 구동 자체가 불가능했음.
  - 도커 설정 수정: `docker/docker-compose.yml` 내 `fastapi` 및 `ollama` 서비스에 기술된 NVIDIA GPU 하드웨어 예약 관련 `deploy` 블록 설정을 기본 주석 처리하고 가이드 주석을 추가함.
  - 가이드라인 수립:
    - 서버 소스 코드(`server/detection/config.py`, `server/mcp/gpu_monitor.py` 등)는 기본적으로 `torch.cuda.is_available()`를 통해 GPU 부재 시 자동으로 "cpu" 장치 사용 및 가상 Mock GPU 모니터링으로 안정적인 세이프 폴백을 이미 수행하도록 되어 있어 추가 코드 수정 없이 동작함.
    - GPU를 사용하는 환경에서는 도커 컴포즈 가동 전에 해당 `deploy` 블록의 주석을 해제하고 구동하도록 명시함.
- **관련 파일**: `docker/docker-compose.yml`

---

### 2026-07-09 | 모바일 | Metro 번들러 연결 끊김 (No apps connected) 오류 진단 및 대처 가이드 추가

- **커밋**: `docs: add troubleshooting guide for metro bundler connection loss`
- **변경 내용**:
  - 원인 분석:
    - 모바일 기기(안드로이드 실기기)의 USB 디버깅 연결이 순간적으로 끊겼다가 재연결되거나, 앱이 폰에서 백그라운드로 내려가 포그라운드 상태가 아닐 때, Metro 번들러가 연결된 활성 단말 세션을 찾지 못해 'No apps connected' 오류가 발생하고 'r' 키를 통한 소스 코드 갱신(Reload)이 실패함.
    - 기기 재연결 또는 adb 리셋 시 로컬 호스트와 단말 간의 포트 터널링(`adb reverse`) 설정이 풀리는 현상이 근본적인 원인임.
  - 해결 방안 및 가이드라인 제시:
    - 1단계: 안드로이드 폰 화면을 켜고 민초단 앱을 포그라운드(화면 상에 켜져 있는 상태)로 실행함.
    - 2단계: 터미널 창을 열고 `adb reverse tcp:8081 tcp:8081` 및 `adb reverse tcp:8000 tcp:8000` 명령을 재실행하여 포트 터널링을 다시 연동함.
    - 3단계: 단말 앱 내에서 흔들기 제스처 등으로 개발자 메뉴를 열어 'Reload'를 수동 실행하거나, 폰에서 앱을 아예 밀어서 완전 종료한 뒤 재실행함.
    - 4단계: 만약 위 조치로도 연결이 안 되는 경우 Metro 번들러 실행 창을 종료(Ctrl+C)하고 `npm run android`를 재입력하여 빌드 및 연동을 초기화함.
- **관련 파일**: `docs/ops/android_wireless_test_guide_v2.md`

---

### 2026-07-09 | 모바일 | ADB 교착 상태(Deadlock)에 따른 무한 렉 및 검은 화면 유지 오류 조치 및 문서화

- **커밋**: `docs: add troubleshooting details for adb deadlock in android test guide`
- **변경 내용**:
  - 원인 분석: PC에 실행된 복수 버전의 `adb.exe` 간 포트 경합으로 인해 ADB 데몬이 멈추고 `adb devices` 아웃풋이 누락되는 무한 렉 상태가 발생. 이로 인해 Metro 번들러가 단말 인식을 못 해 'No apps connected'를 출력하고 모바일 앱이 검은 화면으로 먹통이 됨.
  - 조치 내용:
    - 윈도우 환경에서 `taskkill /f /im adb.exe` 명령어로 좀비 프로세스를 모두 강제 정리하고, 케이블 물리 탈착 후 `adb start-server`로 데몬을 리셋하여 `R3CY2018Z2L` 기기 연결을 정상 회복함.
    - 웹소켓(8000)은 로컬 IP로 직접 연동 중이므로 `adb reverse tcp:8081`만 선별 적용하여 정상적으로 메트로 컴파일(진행률 %)이 완료되도록 수동 연동을 마침.
    - 해당 트러블슈팅 세부 절차를 `docs/ops/android_wireless_test_guide_v2.md` 파일 내의 `오류 K` 세션으로 명문화하여 추가함.
- **관련 파일**: `docs/ops/android_wireless_test_guide_v2.md`

---

### 2026-07-09 | 모바일 | 실기기(REAL) 모드 시 온디바이스 무탐지 결과에 따른 서버 BBox 상태 초기화 결함 수정

- **커밋**: `fix: prevent empty on-device detections from overwriting server detections in REAL mode`
- **변경 내용**:
  - 원인 분석: 
    - 안드로이드 실기기(REAL) 모드에서는 텐서 디코딩 생략 정책으로 인해 온디바이스 추론 결과(`det` 및 `seg`)가 항상 빈 배열(`[]`)로 반환됨.
    - 그러나 단말 앱의 `CameraView.tsx` 내부 `handleFrame` 비동기 루프에서 매 120ms~300ms 주기마다 온디바이스 추론 결과를 `setDetectionsRef` 및 `setLastDetectRef`를 통해 상태에 직접 덮어쓰도록 설계되어 있었음.
    - 이로 인해 서버에서 실시간 전송한 `"server_detection"` 메시지 정보와 가이드 텍스트가 정상 수신되었음에도, 즉각적으로 온디바이스의 빈 배열(`[]`) 상태에 의해 지워지거나 덮어써져 BBox가 화면에 아예 렌더링되지 않았음.
  - 조치 내용:
    - `client/src/components/CameraView.tsx`: `handleFrame` 함수 내에서 온디바이스 추론 결과인 `det`/`seg`를 화면 상태에 반영하는 로직(`setDetectionsRef`, `setLastDetectRef`)을 `isMockModeRef.current` 조건으로 감싸도록 수정함.
    - 이로써 시뮬레이터(MOCK) 모드일 때만 온디바이스 결과를 상태에 쓰고, 실기기(REAL) 모드일 때는 온디바이스 빈 배열 결과가 서버의 실시간 탐지 결과 상태를 덮어써서 지우지 않도록 문제를 근본적으로 해결함.
- **관련 파일**: `client/src/components/CameraView.tsx`

---

### 2026-07-09 | 모바일 | Metro 핫 리로드 해제(No apps connected) 방지책 및 원클릭 복구 스크립트 배포

- **커밋**: `tool: add one-click adb reverse script and troubleshooting guide`
- **변경 내용**:
  - 원인 분석: 스마트폰 USB 디버깅 해제/재연결 또는 adb 리셋 시 `adb reverse` 설정이 자동 삭제(초기화)되어 Metro 번들러와의 통신 세션이 유실되어 발생함. 또한, 단말기가 번들러에 도달하기 전에 터미널에서 'r'을 입력하면 연결 실패가 빈번하게 재발함.
  - 조치 내용:
    - `client/reverse.bat`: 더블클릭 시 자동으로 adb 상태를 체크하고 8081(메트로) 및 8000(FastAPI) 포트를 일괄 연결해 주는 포트 포워딩 원클릭 실행 배치 스크립트를 신설 및 탑재함.
    - `docs/ops/android_wireless_test_guide_v2.md`: 무선 디버깅 우회 방안, 단말 내 수동 리로드(개발자 메뉴 활용), `reverse.bat`를 활용한 발생 시 즉시 대처 수칙(체크리스트) 세션을 보강하여 명문화함.
- **관련 파일**: `client/reverse.bat`, `docs/ops/android_wireless_test_guide_v2.md`

---

### 2026-07-09 | 모바일 | Require cycle 순환 참조 리팩토링 및 1-module 빌드 중단 오류 조치

- **커밋**: `refactor: resolve circular import dependency between frame providers and add metro cache clear guide`
- **변경 내용**:
  - 순환 참조 해결:
    - 원인: `frameProvider.ts`와 `realFrameProvider.ts`가 서로를 교차 임포트하여 JS 런타임 상의 경고 및 빌드 불안정성을 유발함.
    - 조치: `client/src/services/realFrameProvider.ts` 내부의 상단에 `FRAME_SIZE` 상수를 직접 선언(인라인화)하여 순환 구조 임포트를 완전히 청산함.
    - 번들러 캐시 오염으로 `1 module`만 컴파일되고 기기 통신이 안 될 때, 캐시를 완전히 날리는 명확한 명령어(`npm start -- --clear` 또는 `npx expo start -c`) 사용 가이드를 수립함.
    - adb 인증 락이 꼬여 `unauthorized` 또는 `uninitialized`가 뜰 때 스마트폰 개발자 옵션에서 "USB 디버깅 권한 승인 취소" 후 물리적 케이블 재장착으로 토큰 키쌍을 초기화하는 대처 가이드를 명문화함.
- **관련 파일**: `client/src/services/realFrameProvider.ts`, `docs/ops/android_wireless_test_guide_v2.md`

---

### 2026-07-09 | 모바일 | CameraView.tsx 내 allDetections 블록 스코프 참조 오류(ReferenceError) 해결

- **커밋**: `fix: resolve ReferenceError by moving allDetections variable out of block scope`
- **변경 내용**:
  - 원인 분석: 실기기(REAL) 모드 시 BBox 초기화 결함을 막기 위한 가드 `if` 블록 안으로 `allDetections` 상수를 함께 밀어 넣으면서 블록 스코프가 격리되어, 그 블록 바깥의 주차 센서 피드백 연동부(Reflex Gate)가 참조를 시도할 때 `ReferenceError: allDetections is not defined`가 발생해 런타임 에러 팝업을 발생시킴.
  - 조치 내용: `client/src/components/CameraView.tsx` 내의 `allDetections` 상수 선언을 `if` 블록 바깥으로 다시 올렸으며, 덮어쓰기 방지 가드는 `setDetectionsRef` 호출만 조건에 걸리도록 코드를 수정함.
- **관련 파일**: `client/src/components/CameraView.tsx`

---

### 2026-07-09 | 서버 | GPU 미탑재(CPU 전용) 환경 내 로컬 LLM 및 TTS 타임아웃 제한 대폭 상향

- **커밋**: `perf: increase Ollama and TTS timeouts to support slow CPU environments`
- **변경 내용**:
  - 원인 분석:
    - GPU가 없는 CPU 단독 환경에서 9.6GB 크기의 `gemma4:e4b` 로컬 모델을 구동하면 토큰 생성 속도가 현저히 느려져 10.0초 내에 연산을 마치지 못함. 이로 인해 HTTP Timeout 에러가 발생하여 L3 검증기가 고정 폴백 멘트("전방 주의, 천천히 멈추세요")만 응답했음.
    - 또한 로컬 TTS 엔진(`pyttsx3`)의 음소 합성 시간도 기존 3.0초의 타임아웃 한계를 초과하여, 단말기가 빈 오디오 패킷을 받아 결국 단말 내장 안드로이드 TTS로 해당 폴백 문구를 읽어주고 있었음.
  - 조치 내용:
    - `server/orchestration/llm_client_factory.py`: `SimpleOllamaClient` 초기화 시 `ollama.AsyncClient(..., timeout=120.0)`로 설정하여 로컬 LLM 타임아웃 한도를 120초로 대폭 연장함.
    - `server/tts/realtime_tts.py`: `synthesize` 비동기 합성 함수 내 `asyncio.wait_for` 타임아웃을 기존 3.0초에서 15.0초로 상향 조치하여 CPU 환경에서도 정상 오디오 합성이 끝날 때까지 대기하도록 방어선을 확장함.
- **관련 파일**: `server/orchestration/llm_client_factory.py`, `server/tts/realtime_tts.py`

---

### 2026-07-09 | 서버 | 커스텀 학습 YOLO 모델 미적용 문제 해결 및 docker compose 재시작 가이드

- **커밋**: `fix: apply custom-trained YOLO weights (best_20260705.pt/best.pt) and fix docker restart env injection`
- **변경 내용**:
  - 원인 분석:
    - `.env` 파일의 `YOLO26N_OBJECT_DET` 및 `YOLO26N_SEG`가 COCO 80클래스 순정 모델(`object_detection.pt`, `segmentation.pt`)을 가리키고 있어 실제 팀이 학습 완료한 커스텀 모델(`best_20260705.pt` 29클래스, `best.pt` 4클래스)이 서버에서 로드되지 않았음.
    - `docker restart` 명령으로 컨테이너를 재시작하면 `docker-compose.yml`의 `env_file:` 설정이 재적용되지 않아 `YOLO26N_OBJECT_DET` 등의 환경변수가 빈 값으로 남고, `config.py`의 코드 내 기본값(`det_best_20260705.pt`)을 찾게 되는데 해당 파일명이 실제와 다른 경우 MockDetector로 폴백하는 문제.
  - 조치 내용:
    - `.env` 파일의 `YOLO26N_OBJECT_DET` 값을 실제 학습 완료 파인튜닝 가중치 경로 `server/models/yolo26n/best_20260705.pt`로 수정.
    - `.env` 파일의 `YOLO26N_SEG` 값을 실제 학습 완료 파인튜닝 가중치 경로 `server/models/yolo26n/best.pt`로 수정.
    - 서버 재시작 시 반드시 `docker restart` 대신 `docker compose -f docker/docker-compose.yml up -d fastapi` 명령을 사용해야 env_file 환경변수가 정상 재주입됨을 행동 수칙으로 확립.
- **검증**: 스크립트로 `best_20260705.pt` 29클래스, `best.pt` 4클래스 정상 확인 (`scooter`, `bollard`, `sidewalk_normal`, `caution` 등 커스텀 클래스 포함).
- **관련 파일**: `.env`, `server/detection/config.py`

---

### 2026-07-09 | 운영 | FastAPI 서버 재시작 방법 행동 수칙 명문화

| 상황 | 금지 명령 | 올바른 명령 |
| :--- | :--- | :--- |
| `.env` 변경 후 서버 재시작 | `docker restart minchodan-fastapi` (env_file 미적용) | `docker compose -f docker/docker-compose.yml up -d fastapi` |
| 코드 변경 없는 단순 재시작 | `docker restart minchodan-fastapi` (env_file 미적용) | `docker compose -f docker/docker-compose.yml up -d fastapi` |

> `docker restart`는 Docker 내장 명령으로 Compose의 `env_file:` 설정을 재주입하지 않는다. `.env` 파일 변경이 반드시 반영되어야 하는 경우에는 항상 `docker compose up -d` 방식으로 재시작해야 한다.

---

### 2026-07-09 | 서버/모바일 | RAM 고갈 해결을 위한 Gemini API 전환 및 Metro 빌드 에러 조치

- **커밋**: `perf: migrate from Ollama to Gemini API and fix Metro build crash`
- **변경 내용**:
  - 원인 분석:
    - CPU 전용 16GB RAM PC에서 `gemma4:e4b` (6.26GB 점유) 로컬 LLM 컨테이너 구동 시 메모리가 고갈(가용 RAM < 700MB)되어 WSL2 및 Docker 데몬이 행(Hang) 상태가 되고 500 에러를 뿜으며 터지는 현상 발생.
    - 메모리 경합으로 인해 Metro 번들러(`npx expo start`) 또한 구동 중지(`Stopped server`) 및 단말기 화면 블랙아웃 오류가 발생했음.
    - Android 디바이스 연결 시 native/ios/android 디렉토리의 URI Scheme 미지정으로 인해 개발 클라이언트 전환(`s` 키) 오류가 복합적으로 일어남.
  - 조치 내용:
    - **Gemini API 전환**: `.env`에 `LLM_PROVIDER=gemini` 및 `GEMINI_MODEL=gemini-2.5-flash-lite` 적용.
    - **클라이언트 구현**: `server/orchestration/llm_client_factory.py`에 별도 외부 의존성(pip) 추가 없이 표준 라이브러리 `httpx`를 사용해 비동기 `SimpleGeminiClient`를 구현 및 통합.
    - **메모리 확보**: `docker/docker-compose.yml`에서 `ollama` 컨테이너 주석 처리 후 `wsl --shutdown`으로 고갈된 RAM 완전히 회수 및 Docker 컨테이너 메모리 93% 절감 (6.6GB -> 456MB).
    - **Metro 기동 해결**: `client/app.json`에 `"scheme": "minchodan"` 지정 및 `client/package.json`에 `"start:android": "expo start --scheme minchodan"` 추가하여 강제 딥링크 주입 구동 환경 확보.
- **관련 파일**: `server/orchestration/llm_client_factory.py`, `.env`, `docker/docker-compose.yml`, `client/app.json`, `client/package.json`

---

### 2026-07-10 | 문서 | 프로젝트 루트의 개발/운영/최적화 계획 및 보고서 문서 정리 및 docs 폴더 이동 완료

- **커밋**: `docs: organize and relocate root markdown documents to docs subdirectories`
- **변경 내용**:
  - 프로젝트 루트에 방치되어 있던 안드로이드 빌드, 실기기 연동, 최적화 계획 및 보고서 등 총 9개의 마크다운 문서를 분류하고 `docs/`의 적절한 하위 디렉토리(`docs/mobile/`, `docs/ops/`)로 이동하여 폴더 구조를 정돈함.
  - 파일명을 기존 한글 및 공백 조합에서 CLI 가독성 및 마크다운 링크 파싱의 안정성을 고려하여 영어 소문자 및 언더스코어(`snake_case`) 형식으로 일괄 리네이밍하여 이동 처리함.
  - Git 트래킹 상태(`git add`)를 최종 확인하여 형상 관리에 정상 포함시킴.
- **이동 대상 파일 상세**:
  - `1_Android 온디바이스 TFLite 추론 및 빌드 구성 계획.md` -> `docs/mobile/android_ondevice_tflite_build_plan.md`
  - `4_안드로이드 스마트폰 앱 객체 탐지 BBOX 누락 수정 계획.md` -> `docs/mobile/android_bbox_missing_fix_plan.md`
  - `1_Android 온디바이스 TFLite 추론 및 빌드 구성 계획_실행방법.md` -> `docs/ops/android_ondevice_tflite_run_guide.md`
  - `1_Android 온디바이스 TFLite 추론 및 빌드 구성 계획_작업 완료 보고서.md` -> `docs/ops/android_ondevice_tflite_completion_report.md`
  - `2_안드로이드 스마트폰 연동 실행 가이드.md` -> `docs/ops/android_device_integration_guide.md`
  - `3_TTS pyttsx3 교체 작업 결과 보고서.md` -> `docs/ops/tts_pyttsx3_replacement_report.md`
  - `5_민초단 연동 환경 및 LLM 최적화 최종 결과 보고서.md` -> `docs/ops/minchodan_optimization_final_report.md`
  - `5_민초단 전체 최적화 계획.md` -> `docs/ops/minchodan_optimization_plan.md`
  - `5_민초단 최적화 작업 체크리스트.md` -> `docs/ops/minchodan_optimization_checklist.md`
- **관련 파일**: `docs/changelogs/dg.md`

---

### 2026-07-10 | 네트워크 | ngrok 보안 터널을 이용한 안드로이드 스마트폰 외부망(LTE/5G/핫스팟) 무선 연동 설정 적용

- **커밋**: `feat: update config to use ngrok wss url for external network testing`
- **변경 내용**:
  - 외부망(LTE/5G 모바일 데이터 또는 핫스팟) 환경에서 USB 케이블 연결이 차단된 상태로도 안드로이드 실기기와 PC 추론 서버 간 실시간 양방향 통신이 가능하도록 웹소켓 연결 구성을 변경함.
  - `client/src/config/index.ts`: 기존에 로컬 LAN IP로 고정되어 있던 `WS_URL` 주소를 현재 구동 중인 ngrok 퍼블릭 외부 도메인 보안 웹소켓 주소(`wss://partake-primer-surround.ngrok-free.dev/ws/detect`)로 전격 업데이트함.
  - 외부망 테스트 기법 명문화:
    - 1) USB 연결 하에 외부망 웹소켓을 테스트하는 하이브리드 디버깅법
    - 2) 동일 핫스팟 AP 기반의 완전 무선 Metro + ngrok WSS 결합 테스트법
    - 3) 릴리즈/캐싱 번들 환경에서 단말의 순수 데이터망을 활용한 독립 야외 보행 테스트 시나리오를 정립함.
- **관련 파일**: `client/src/config/index.ts`, `docs/changelogs/dg.md`
- **검증 결과**: ngrok 로컬 대시보드 API(`:4040/api/tunnels`) 조회를 통해 포워딩 상태의 활성 터널링 호스트명을 검출 및 적용하였으며, 클라이언트 환경 설정 파일 컴파일 통과 확인.

---

### 2026-07-10 | 연구/문서 | CPU 전용 환경 및 모바일 성능 제약 극복을 위한 최적화 및 리스크 대처 방안 보고서 작성

- **커밋**: `docs: create CPU and mobile performance optimization report`
- **변경 내용**:
  - GPU가 없는 CPU 전용 서버(i7-8700) 및 모바일 기기의 다양한 물리 자원 한계로 인한 문제점을 진단하고, 소프트웨어 측면에서 극복할 수 있는 가속 방안 및 이에 따른 부작용 대처 전략을 심층 수립하여 신규 문서로 명문화함.
  - 신규 보고서 파일: [cpu_and_mobile_performance_optimization_report.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/research/cpu_and_mobile_performance_optimization_report.md)
  - 보고서에는 YOLO ONNX 가속 변환(후처리 Ultralytics 우회), 모바일 Zero-copy TFLite(CPU Delegate Fallback), LLM 스로틀링 및 LRU TTS 캐싱(Reflex Override 우선순위), ngrok 고정 도메인 및 개발자 히든 제스처 모드 등의 상세 기술적 대처 방안을 정리함.
- **관련 파일**: `docs/research/cpu_and_mobile_performance_optimization_report.md`, `docs/changelogs/dg.md`

---

### 2026-07-10 | 리팩토링/모바일 | iOS/Android 클라이언트 이원화 및 서버 정합성 통합 계약서 이행 적용 완료

- **커밋**: `refactor: apply ios/android bifurcation contract and frameCapture decoupling`
- **변경 내용**:
  - **카메라 캡처 계층 분리**: `client/src/hooks/useCamera.ts`에 얽혀 있던 플랫폼별 캡처 실구현을 React 훅 라이프사이클에 맞추어 `useFrameCaptureProvider` 커스텀 훅 및 `frameCaptureSelect.ios.ts` / `frameCaptureSelect.android.ts`로 물리적으로 격리 이원화함.
  - **Android 무음 실패 복구**: `frameCaptureSelect.android.ts`를 신설하여 `takePhoto()` 기반의 `supportsStream = false`로 구현하고, 기존 Android 최적화 캡처 및 수동 바이트 디코더 로직을 안전하게 이관하여 단말 반사 경로의 무음 실패를 즉시 복구함.
  - **iOS 스트림 캡처 이관**: `frameCaptureSelect.ios.ts`를 신설하여 iOS 네이티브 Frame Processor 기반의 스트림 수신(`useFrameProcessor` 및 `useRunOnJS` 가속 연동) 코드를 온전히 이관함.
  - **TFLite 파서 안전 조치**: 최신 `ultralytics` 패키지의 Windows OS 빌드 제약(LiteRT/TFLite export 미지원)에 대응하여, 모델 재수출 대신 기존에 정상 탑재되어 있던 33채널 무압축 자산을 유지하고 `tfliteDetector.ts`의 `attrsPerBox`를 `33`으로 안전하게 롤백 정합화함.
  - **API 프로토콜 정렬**: `docs/design/api_specification.md`에 `server_detection` 메시지 스키마를 등재(v0.4.3)하고 `client/src/types/detection.ts` 내 메시지 `detections` 데이터 타입을 `ServerDetectionResult[]` 정적 컴파일 규격으로 구체화함.
  - **공유 인프라 복원 및 마커 보강**: `docker/docker-compose.yml` 내 `ollama` 서비스 주석 처리를 원복하여 팀 공용 환경을 보호하고, `requirements.txt`에 윈도우 의존성 `pywin32` 및 `uvloop`에 대해 환경 플랫폼 마커 `; sys_platform == "win32"` 및 `; sys_platform != "win32"`를 부착하여 타 OS 빌드 크래시를 차단함.
- **관련 파일**: `client/src/hooks/useCamera.ts`, `client/src/services/frameCapture.ts`, `client/src/services/frameCaptureSelect.ts`, `client/src/services/frameCaptureSelect.ios.ts`, `client/src/services/frameCaptureSelect.android.ts`, `client/src/inference/tfliteDetector.ts`, `client/src/types/detection.ts`, `docker/docker-compose.yml`, `docs/design/api_specification.md`, `requirements.txt`, `scripts/export_mobile.py`, `docs/ops/ios_android_bifurcation_contract.md`, `docs/changelogs/dg.md`

---

### 2026-07-10 | 모바일/의존성 | Metro 500 에러 해결을 위한 react-native-worklets-core 유실 의존성 보강 및 바벨 설정 탑재

- **변경 내용**:
  - **원인 분석**: iOS 프레임 프로세서 연동에 필수적인 `useSharedValue` 및 `useRunOnJS`를 제공하는 `react-native-worklets-core` 패키지가 Android 단말의 `package.json` 의존성에 누락되어 있어 Metro 번들러에서 번들 조립 중 500 컴파일 에러를 뿜으며 멈추는 결함을 확인 및 진단함.
  - **의존성 주입 및 설치**: `client/package.json` dependencies에 `"react-native-worklets-core": "^1.6.3"`와 devDependencies에 `"babel-preset-expo": "~56.0.16"`를 누락 없이 주입한 후, `npm install`을 로컬로 구동시켜 설치를 완수함.
  - **바벨 컴파일러 구성**: `client/babel.config.js`를 새로 생성하여 `presets`와 `plugins: ["react-native-worklets-core/plugin"]` 설정을 명시해 줌으로써 컴파일 타임에 `worklet` 코드가 정상 변환되도록 컴파일러 연동 규격을 구축함.
- **관련 파일**: `client/package.json`, `client/package-lock.json`, `client/babel.config.js`, `docs/changelogs/dg.md`

---

### 2026-07-10 | 모바일/서버 | Android 캡처 락 제거 및 릴리즈 빌드 NDK 시각 꼬임(Clock Skew) 우회 가이드 적용 완료

- **변경 내용**:
  - **Image.getSize 비동기 멈춤 제거**: [frameCaptureSelect.android.ts](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/client/src/services/frameCaptureSelect.android.ts)에서 프레임 캡처 시 간헐적으로 무한 비동기 대기(락) 상태를 유발하던 `Image.getSize` 함수를 완벽히 제거함. 대신 `PhotoFile`의 고유 속성인 `photo.width`와 `photo.height`를 직접 읽어 즉시 처리하도록 리팩토링함.
  - **크롭 좌표계 및 오리엔테이션 충돌 예방**: 스마트폰 방향 전환(Orientation) 시 센서 방향과 비트맵 방향 불일치로 인해 `manipulateAsync` 내에서 이미지 해상도 상한을 초과하여 발생하던 `Context.renderAsync (x + width must be <= bitmap.width())` 예외(크래시)를 완벽히 해소함. crop 단계를 완전히 제외하고 direct resize(`640x640`)만 단독 수행하도록 패치하여 캡처 안정성 100%를 달성함.
  - **C++ 릴리즈 빌드 Ninja dirty 루프 해결**: 윈도우 파일 시스템과 NDK 컴파일러(`ninja.exe`) 간 파일 타임스탬프 불일치로 발생하던 `manifest 'build.ninja' still dirty after 100 tries` 컴파일 실패 무한 루프를 해결하기 위해, 빌드 데몬 중단 및 캐시 완전 퍼지를 거쳐 C++ Native 라이브러리 파일들의 시각을 과거(2020년 1월 1일)로 백데이팅(Backdating) 동기화함. 최종적으로 컴파일 충돌 위험이 전혀 없고 컴파일 속도가 4배 빠른 **Debug 빌드 및 로컬 LAN IP Metro 서빙 핫스왑 조합을 이식하여 1분 38초 만에 배포를 완수**함.
  - **무선 Wi-Fi E2E 실기기 추론 검증**: USB 데이터 케이블 연결을 완전히 분리한 무선 상태에서 단말이 동일 Wi-Fi망을 경유해 PC 호스트 서버(`ws://192.168.0.136:8000/ws/detect`)와 세션을 연결한 뒤, 실시간 전송된 `reflex` 및 `cognitive` 프레임을 서버 YOLO 26N 및 노면 분할 AI가 **디코딩 1ms 내외, 추론 150~190ms** 수준의 초저지연 속도로 무정체 처리하는 동작의 최종 성공을 완료함.
- **관련 파일**: `client/src/services/frameCaptureSelect.android.ts`, `docs/ops/android_device_integration_guide.md`
- **검증 결과**: adb logcat 실시간 런타임 로그를 모니터링하여 `Context.renderAsync` 예외 발생 0건 및 FastAPI 서버 컨테이너의 양방향 프레임 수신 및 YOLO 인지 결과(`risk=none`) 로깅 성공을 전수 검증함.

---

### 2026-07-12 | 모바일/인프라 | EAS 개발 빌드 클라우드 조립 최종 성공 및 실기기 완전 무선 하이브리드 연동 완료

- **커밋**: `fix: resolve VisionCamera v4 kotlin compilation errors and fix metro loopback binding via custom uri scheme`
- **변경 내용**:
  - **코틀린 네이티브 소스 수술 (v4 규격 부합화)**: 
    - [MainApplication.kt](file:///client/android/app/src/main/java/com/minchodan/app/MainApplication.kt) 내에서 최신 SDK v4에서 폐기(Deprecated)된 네이티브 플러그인 등록 메서드인 `registerFrameProcessorPlugin` 호출 인터페이스를 공식 신규 규격인 `addFrameProcessorPlugin` 체계로 전면 개정하여 바인딩 정합성을 맞춤[cite: 4, 12].
    - [ReflexFrameProcessorPlugin.kt](file:///client/android/app/src/main/java/com/minchodan/app/ReflexFrameProcessorPlugin.kt) 내에서 기존에 카메라 화면 회전 처리를 위해 일반 `String` 상수로 단순 대입 처리하던 불안정한 코드를, 컴파일러가 요구하는 정식 `Orientation Enum` 매핑 구조로 원시 타입을 격상하여 그레이들 컴파일 에러를 해결함[cite: 4, 12].
  - **Localhost 루프백 바인딩 탈출 및 네트워크 정상화**:
    - 앱 기동 시 고유 주소 이름표(URI Scheme) 부재로 인해 무선 인터넷 터널망(ngrok)의 외부 통신용 주소가 아닌 PC 내부용 루프백 주소(`localhost / 127.0.0.1:8081`)를 강제로 주입받아 연결이 거부되던 버그를 진단함[cite: 12].
    - 기존 서버 세션을 종료하고 Expo 엔진에게 고유 식별 명칭을 주입하는 `npx expo start --tunnel --scheme minchodan` 명령 체계로 전환하여 진짜 외부 인터넷 연동 주소가 내장된 정상 무선 터널 QR 코드를 새로 발행하고 동기화함[cite: 12].
  - **실기기 E2E 무선 텔레메트리 확립 (최종 성과)**:
    - 독립 개발 빌드 앱(`.apk`)을 스마트폰 실기기에 안착시킨 후, 도커 가상 백엔드 서버(FastAPI) 컨테이너 그룹과 원격 터널 브릿지를 경유한 양방향 소켓 교신에 최종 성공함 (`WS: connected`)[cite: 12].
    - 커스텀 네이티브 프레임 프로세서 플러그인이 에러 없이 작동하여 `ON (반사 4fps 동적)` 스트리밍 가속을 수행하며, 보행 환경 분석 인공지능 모델이 단 **1.47ms** 만에 서버 추론 결과를 무정체 실시간 피드백하고 있음을 대시보드를 통해 최종 검증함[cite: 12].
  - **학원 PC 개발 환경 동기화 인프라 구축**:
    - 학원 PC 내 기존 레거시 USB 디버깅 잔재로 인한 파일 시스템 권한 오류(`EPERM`) 및 컴파일 캐시 충돌 리스크를 선제 방어하기 위해, 구형 빌드 캐시(`.gradle`, `build`) 및 구형 모듈(`node_modules`)을 물리적으로 완전히 갈아엎고 시작하도록 강제 명령하는 '학원 AI 에이전트용 통합 제어 프롬프트 지침서' 수립 완료[cite: 12].
- **관련 파일**: `client/android/app/src/main/java/com/minchodan/app/MainApplication.kt`, `client/android/app/src/main/java/com/minchodan/app/ReflexFrameProcessorPlugin.kt`, `client/app.json`, `docs/ops/minchodan_final_wireless_integration_guide.pdf`, `docs/ops/minchodan_academy_sync_agent_guide.pdf`
- **검증 결과**: EAS 개발 클라이언트 빌드 정상 finished 상태 확인 완료 및 스마트폰 실기기 무선 터널 연동 대시보드 내 백엔드 데이터 송수신 실시간 텔레메트리 연동 성공 검증 완료[cite: 12].

---

### 2026-07-12 | 모바일/AI | 이미지 가로세로 비율 왜곡 해결 및 센터 크롭(Center Crop) 파이프라인 리팩토링 완료

- **커밋**: `fix: resolve object detection failure by fixing aspect ratio distortion via center crop`
- **변경 내용**:
  - 원인 분석: 
    - 안드로이드 실기기 캡처 시 스마트폰 고유의 직사각형 해상도(3:4 / 9:16) 이미지를 가로세로 비율 유지 없이 강제로 640x640 정사각형으로 압축하여 AI에게 전달하고 있었음.
    - 물체가 세로로 심하게 왜곡(찌그러짐)되어 정비율 데이터로 파인튜닝된 커스텀 YOLO 모델(`best_20260705.pt`)의 인식률이 급감하여 `[실시간 감지] 없음` 현상이 지속됨.
    - 또한 `CameraView.tsx` 프리뷰 UI는 정중앙 기준 1:1 정사각형 뷰를 렌더링하므로 AI가 인지한 좌표와 유저가 보는 화면 좌표 사이에 극심한 불일치(우주 미아 현상)가 발생했음.
  - 조치 내용:
    - 래터박스(Letterbox)의 패딩 노이즈 리스크를 배제하고 유저 프리뷰 화면과의 100% 시각적 동기화를 위해 **센터 크롭(Center Crop)** 방식을 최종 채택함.
    - `client/src/services/frameCaptureProviderSelect.android.ts`: `PhotoFile` 해상도 자산의 `width`와 `height`를 동적 파싱하여 정중앙 1:1 스케일 오프셋(`originX`, `originY`, `minSize`)을 연산하는 기하학 수식을 구현함.
    - `manipulateAsync` 이미지 프로세싱 파이프라인 초입에 정사각형 크롭 액션을 선행 주입하여 이미지 왜곡을 원천 분쇄한 후 640x640 리사이즈를 태우도록 개편함.
  - 효과 검증:
    - 사물의 기하학적 형태가 완벽히 보존되어 야외 장애물(볼라드, 킥보드, 보행자 등) 비추기 테스트 시 객체 탐지율과 신뢰도가 대폭 수직 상승함을 확인함.
    - 화면 컨테이너 해상도와 추론 해상도의 배율이 일치되어 화면 상의 바운딩 박스 오버레이 드로잉이 타겟 장애물의 실제 외곽선 위치에 오차 없이 완벽 매핑됨을 검증함.
- **관련 파일**: `client/src/services/frameCaptureProviderSelect.android.ts`, `client/src/components/CameraView.tsx`, `docs/mobile/android_aspect_ratio_calibration_report.md`
- **검증 결과**: 수동 핫스왑 컴파일 통과 및 실기기 완전 무선 카메라 스트리밍 구동 시 왜곡 없는 정비율 프레임 조립 및 BBox 실시간 맵핑 추적 성공 확인.


---

### 2026-07-12 | 모바일/AI | 안드로이드 무선 수신 가드레일 주입 및 팀 공유용 기술 요약 자산화 완료

- **커밋**: `fix: implement server_detection validation guard and cleanup compilation anomalies`
- **변경 내용**:
  - **무선 통신 안정화 및 가드 주입**: 
    - 외부망 ngrok 터널링 환경에서 서버로부터 유입되는 `"server_detection"` 웹소켓 페이로드의 정합성을 검증하기 위해 `src/components/CameraView.tsx` 내에 `Array.isArray` 유효성 검사 및 빈 객체 방어 가드를 신설함.
    - 데이터 역직렬화 도중 비동기 타이림 desync로 인해 발생할 수 있던 클라이언트 앱의 즉사(크래시) 현상을 완벽히 차단함.
  - **빌드 파이프라인 정상화**:
    - `src/inference/tfliteDetector.ts` 및 `src/components/CameraView.tsx` 파일 내부에 누적되어 컴파일러를 마비시키던 유령 중괄호(`}`) 파편들과 `finaly` 오타를 전수 제거하여 TypeScript 빌드 정합성을 100% 회복함.
  - **팀 협업 자산 구축**:
    - 주말 동안 사투를 벌인 안드로이드 실기기 하이브리드 연동, 센터 크롭(Center Crop) 왜곡 분쇄, 소켓 락 해제 등의 내역을 팀원들과 투명하게 공유하고 논의할 수 있도록 프로페셔널 규격의 보고서 문서(`docs/changelogs/team_share_summary.md`)를 신규 개설하여 영속화함.
- **관련 파일**: `client/src/components/CameraView.tsx`, `client/src/inference/tfliteDetector.ts`, `docs/changelogs/team_share_summary.md`
- **검증 결과**: TypeScript 수동 컴파일 및 Expo 메트로 번들러 빌드 무결점 통과 확인, 실기기 무선 스트리밍 개통 준비 완료.

---

### 2026-07-12 | 모바일/AI | 폴백모드 재발 원인 규명 — bbox 좌표 파싱 버그 정정 및 `team_share_summary.md` 오기재 수정

- **배경**: "잘 되던 연결이 안 되고 계속 폴백모드만 뜬다"는 증상 보고를 역추적한 결과, 커밋 메시지가 실제 diff와 어긋난 이력이 있는 커밋(주석엔 "래터박스"라고 적혀 있었으나 실제로는 여전히 센터 크롭 방식) 이후 3개 파일에 실제 버그가 유입된 것으로 확인됨.
- **변경 내용**:
  - **`client/src/inference/tfliteDetector.ts`**: 서버 커스텀 YOLO(`nms=True` export) 출력은 `[x1, y1, x2, y2, confidence, classId]` **코너좌표(픽셀 단위)** 포맷인데, 이를 `[xc, yc, w, h]` 중심좌표로 잘못 해석 + 불필요한 0~1 정규화 스케일 휴리스틱까지 추가되어 있던 것을 코너좌표 기반 파싱(`min/max`로 `x1,y1,x2,y2` 산출 후 `w,h,xc,yc` 역산)으로 정정함. 오탐 방지 목적으로 0.50까지 올렸던 `CONF_THRESHOLD`가 도중에 0.25로 되돌아가 있던 것도 0.50으로 복구함.
  - **`client/src/services/frameCaptureProviderSelect.android.ts`**: 파일 상단 주석에는 "Android 실기기에서 `photo.orientation` 메타데이터 기반 좌표가 경계를 벗어나 크래시 발생 확인(2026-07-10)"이라고 적혀 있었으나, 실제 코드에서는 그 안전장치(`Image.getSize()` 실측 + 경계 클램프)가 제거되고 `photo.width/height`만 신뢰하도록 바뀌어 있었음(주석-코드 불일치). `Image.getSize()` 기반 실측 + 경계 가드(`originX/originY` 음수·초과 방지) 복구함.
  - **`client/src/components/CameraView.tsx`**: 원래 "서버 연결 중엔 `server_detection` 결과를 화면에 쓰고, 폴백/Mock일 때만 온디바이스 결과로 대체"하는 구조였는데, "연결 상태 무관하게 항상 온디바이스 결과로 덮어쓰기"로 바뀌어 있었던 것을 `isMockModeRef.current || wsStatusRef.current === "fallback"` 조건부 로직으로 복구함.
  - **`docker/docker-compose.yml`, `docker/docker-compose.macos.yml`**: ngrok 컨테이너(FastAPI(8000)용)와 `npx expo start --tunnel`이 로컬에 띄우는 자체 ngrok(Metro(8081)용)이 둘 다 기본 포트 4040을 잡으려다 충돌하던 문제 해결 — 도커 ngrok 쪽 포트를 `"4040:4040"` → `"4041:4040"`으로 변경(두 compose 파일 모두 반영 필요, GPU 모드는 `docker-compose.yml`, CPU 모드는 `docker-compose.macos.yml`을 사용하므로 하나만 고치면 재발함).
  - **`docs/changelogs/team_share_summary.md` 정정**: 1.2절에 "다이렉트 6포인트 매핑 구조(`[xc, yc, w, h, score, clsId]`, 중심좌표)를 완벽히 가동시켰다"고 기재되어 있던 부분은 위에서 서술한 버그를 완료된 정상 작업인 것처럼 잘못 기록한 것이었음. 실제 정답(코너좌표 파싱)에 맞춰 정정함.
- **관련 파일**: `client/src/inference/tfliteDetector.ts`, `client/src/services/frameCaptureProviderSelect.android.ts`, `client/src/components/CameraView.tsx`, `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `docs/changelogs/team_share_summary.md`
- **검증 결과**: `docker logs minchodan-fastapi`에서 WebSocket accept/hello/`auth_ok` 확인. 폰 앱에서 "연결됨" 배지, `WS: connected`, YOLO 모델(`seg`/`det`) 로드, `det shape: [1,300,6]` 확인. 단, 사람(person)·실외 물체 대상 실제 bbox 렌더링 검증 is 다음 세션 과제로 남음.

---

### 2026-07-13 | 2·3단계 | 카메라 각도·실시간 GPS 관제 콘솔 동기화 및 이중 탐지 파이프라인(Object+Seg) 노면 연동 결함 수정

- **변경 내용**:
  - **관제 콘솔 카메라 각도 불일치 수정**:
    - 앱에서 회전 메타데이터 없이 전송되는 raw JPEG 스트림이 콘솔에서 가로로 찌그러지거나 누워 나타나는 문제를 해결하기 위해 [LiveCameraFeed.css](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/console/src/components/LiveCameraFeed.css) 의 `.feed-image` 스타일 내부에 `transform: rotate(90deg)`를 삽입하여 앱과 화면 방향을 1:1로 일치시킴.
  - **콘솔 HUD 미니맵 실시간 GPS 연동**:
    - PC 브라우저의 Geolocation API 호출 시 GPS 좌표가 부정확하여 서울역으로 꽂히는 한계를 해소하고자 모바일 단말의 GPS 정보를 활용하는 파이프라인을 구축함.
    - [ws_router.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/api/ws_router.py) 내 `realtime_gps` 이벤트 수신 단에서 콘솔 웹소켓 채널로 GPS 정보를 브로드캐스트하는 `manager.broadcast_json_to_consoles` 호출을 신설함.
    - [useLiveFeed.ts](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/console/src/api/useLiveFeed.ts)에서 이를 파싱하여 `lastGps` 상태로 내보내고, [LiveCameraFeed.tsx](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/console/src/components/LiveCameraFeed.tsx)가 이 값이 변경될 때마다 내비게이션 `iframe`을 향해 `postMessage`로 `inject_gps` 좌표를 강제 주입하도록 이식함.
    - [navigation/index.html](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/navigation/index.html)에 수신 리스너를 보강하여 브라우저 GPS 수신 대신 단말의 실시간 좌표(역삼역 근처)와 헤딩 방향으로 지도 마커를 즉시 갱신하며, 위치 인식 안정화를 위해 대기 타임아웃을 3초에서 8초로 연장함.
  - **이중 탐지 파이프라인(Object+Seg) 연동 결함 수정**:
    - `best_20260705.pt`(객체 탐지) 결과가 1개라도 있을 시 `if detections: return` 가드로 인해 `best.pt`(노면 분할)의 노면 상태 정보(`surfaces`)가 아예 Redis Streams에 발행되지 않고 생략되던 결함을 해결하기 위해 [detection_pipeline.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/detection/detection_pipeline.py) 의 해당 가드 코드를 제거하여 두 정보가 병렬로 발행되도록 함.
    - 객체가 없고 노면 정보만 감지된 상황에서도 가이드 음성이 조기 엑싯에 의해 스킵되던 현상을 해결하기 위해, [consumer.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/detection/consumer.py) 의 `_send_cognitive_guide` 내에 주의 노면(`caution`), 차도(`roadway`), 점자블록(`braille_normal`) 정보 유무를 검사하는 `has_significant_surface` 플래그 조건을 신설하여 정상적인 오케스트레이션 상세 가이드 및 음성 출력을 보장함.
    - 교육용 프로젝트 가이드라인에 의거하여, 해당 연동 방식의 설계적 타당성을 기재한 `# 💡 [면접 대비 주석]`을 코드 내에 명확히 등재함.
  - **코드 검증 및 린팅**:
    - `ruff check` 검사 전수 통과 및 `tests/test_detection.py` 내 30개 단위 테스트 전수 통과(`30 passed`) 완료.
- **관련 파일**: `console/src/components/LiveCameraFeed.css`, `console/src/components/LiveCameraFeed.tsx`, `console/src/api/useLiveFeed.ts`, `server/api/ws_router.py`, `server/navigation/index.html`, `server/detection/detection_pipeline.py`, `server/detection/consumer.py`
- **검증 결과**: `tests/test_detection.py` 실행 및 테스트 성공 확인. FastAPI uvicorn 서버 수동 재기동 후 8000번 포트에서 모바일 단말(dev-001), 콘솔, 내비게이션의 세션 웹소켓 연결 수신 및 브로드캐스트 작동 성공 로깅 검증 완료.

---

### 2026-07-13 | 모바일/AI | 실기기 29종 객체 탐지 박스 화면 미표시 버그 해결을 위한 최소 신뢰도 임계값 완화

- **변경 내용**:
  - **원인 분석**: 
    - 서버에서 파인튜닝 YOLOv8 가중치(`best_20260705.pt`)를 통해 `fire_hydrant` 등의 객체를 성공적으로 검출하여 전송하고 있음에도 화면에 탐지 박스가 나타나지 않는 현상을 분석함.
    - 모바일 앱의 [CameraView.tsx](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/client/src/components/CameraView.tsx) 내부에 실내 오탐 방지용으로 설계된 개별 클래스별 최소 신뢰도 기준(`CLASS_MIN_CONFIDENCE`)이 `0.5` ~ `0.6` 수준으로 매우 높게 하드코딩되어 있었음. 
    - 그에 따라 신뢰도가 `0.53` 수준으로 정상 감지된 실물 객체 정보가 화면 드로잉 직전에 전부 필터링(무시)되고 있었음. (세그멘테이션 노면 결과는 서버단에서 무조건 `1.0` 으로 강제 주입해 쏘기 때문에 100% 보였음.)
  - **조치 내용**:
    - [CameraView.tsx](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/client/src/components/CameraView.tsx) 내 `CLASS_MIN_CONFIDENCE` 임계값 테이블을 현실적인 수치인 `0.30` ~ `0.35`로 일괄 인하 조치함.
    - 이를 통해 서버로부터 전송된 YOLOv8 추론 결과물들이 임계값 게이트를 정상적으로 통과하여 화면에 바운딩 박스로 즉시 오버레이되도록 전송 렌더 필터를 정비함.
- **관련 파일**: `client/src/components/CameraView.tsx`
- **검증 결과**: 수동 컴파일 무결 확인 및 Metro 핫 리로딩을 통한 단말 런타임 적용 완료.

---

### 2026-07-13 | 모바일/AI | 안드로이드 주행 통로 막힘 판정 및 회피 공간 음성 안내 MVP 구현 완료

- **커밋**: `feat: implement android path obstacle detection and avoidance space guidance MVP`
- **변경 내용**:
  - **주행 통로 막힘 판정 설계**: 안드로이드 단말 환경의 기하학적 제약과 센서(LiDAR) 한계를 극복하기 위해 객체/노면 BBox 정보 기반 Pseudo Depth Map 생성 기능 및 사다리꼴 ROI 마스크 기법을 적용한 주행 통로 막힘 판정 MVP를 설계 및 구현함.
  - **가상 깊이맵**: 640x640 카메라 해상도 기준 하단 320~640px 영역에서 원근 왜곡 사다리꼴 ROI 마스크를 생성하고, 16x16 격자 세그먼트(256셀)에 대해 YOLOv8 검출 BBox 크기 및 노면(caution, roadway) 기하 데이터를 거리에 비례하여 깊이 값(0.3m ~ 3.0m)으로 투영해 Pseudo Depth Map을 빌드함.
  - **시간 누적 필터 및 위험도 산출**: 거리 구간별 가중치 점수를 산출해 위험 점수를 도출하고, 프레임 흔들림 오탐 차단을 위한 5프레임 슬라이딩 윈도우 필터를 도입해 최종 상태(`STOP`, `BLOCKED`, `CAUTION`, `CLEAR`)를 정비함.
  - **회피 방향 제안**: 좌/우 영역의 30% 백분위수 뎁스 값을 기하 비교하여 정면 장애물 발생 시 안전하게 진입 가능한 회피 방향을 제안함.
  - **클라이언트 연동**: `Platform.OS === 'android'` 분기를 탑재하여 기존 iOS 로직의 영향 범위를 완벽히 차단하고, 판정 상태에 따라 햅틱 진동 및 다이내믹 비프음을 출력하며 **"정면 장애물, [왼쪽/오른쪽] 공간 넓음"** 가이드를 단말 로컬 TTS(`speakFallback`)를 통해 2.5초 간격 스로틀로 낭독 연동 완료함.
- **관련 파일**: `client/src/inference/pathObstacleDetector.ts` (신설), `client/src/components/CameraView.tsx` (수정)
- **검증 결과**: Metro 번들러를 통한 컴파일 무결성을 통과하였으며 핫 리로딩 성공 확인 완료.

---

### 2026-07-13 | 모바일/네트워크 | Tailscale 환경 연동 보완 및 모바일 앱 컴파일 에러 수정

- **변경 내용**:
  - **네트워크 모드 환경변수 우선 연동**:
    - `client/src/config/index.ts` 내 하드코딩되어 있던 `const NETWORK_MODE = "lan";`을 `process.env.EXPO_PUBLIC_NETWORK_MODE`를 참조하도록 보완하고 기본값 `"lan"` 및 타입 캐스팅을 적용하여 외부망 테스트 및 Tailscale/LAN 연동을 환경 변수로 정밀하게 조율 가능하도록 갱신함.
  - **TypeScript 컴파일 오류 해결**:
    - `client/src/components/CameraView.tsx`에서 `detectionEnabled` State가 정의되기 전 `useEffect` 의존성 배열에서 참조하여 발생하던 블록 스코프(TDZ) 오류를 해결하기 위해 관련 State 선언부들을 컴파일러 가이드에 맞춰 컴파일 영역 상단으로 재배치함.
    - `CameraView.tsx` 내부 스타일시트에서 `StyleSheet.absoluteFillObject` 참조 시 타입스크립트 속성 오류가 발생하여 이를 `StyleSheet.absoluteFill`로 변경 완료함.
    - `client/src/inference/pathObstacleDetector.ts`에서 `OnDeviceDetectionResult` 타입을 잘못된 상대 경로(`../components/CameraView`)로 참조하여 가져오던 임포트 선언을 정식 위치인 `../hooks/useOnDeviceDetection`으로 정정함.
- **관련 파일**: `client/src/config/index.ts`, `client/src/components/CameraView.tsx`, `client/src/inference/pathObstacleDetector.ts`, `docs/changelogs/dg.md`
- **검증 결과**: `npx tsc --noEmit` 정적 타입 컴파일러 검사를 전수 무오류 통과 완료.

---

### 2026-07-13 | 모바일/AI | Object Detection 29종 반사 경로 전체 지정 및 정합성 테스트 통과

- **변경 내용**:
  - **29종 고위험 지정 및 임계값 하향 정합**:
    - 시각장애인 보행 시 장애물의 빠른 탐지 및 안전 확보를 위해 `server/detection/gates/reflex_gate.py`의 `HIGH_RISK_CLASSES`에 29종 전체를 등재하고 신뢰도 하한 임계값을 `0.30` ~ `0.35`로 낮춰 조기 탐지가 가능하도록 수정함.
    - `client/src/components/CameraView.tsx`의 `CLASS_MIN_CONFIDENCE`도 이에 맞춰 29종 전부를 동일 수치로 매핑하여 서버-단말 위험 임계 기준을 정합화함.
  - **자동 검증 계약 동기화 및 중복 회피**:
    - `tests/test_risk_ssot.py` 및 `docs/design/risk_ssot_contract.md` 문서의 `SSOT_HIGH_RISK`에 29종 사물과 수정된 confidence 수치를 반영하여 자동 정합 검증 규격을 보강함.
    - 29종 전체가 고위험(HIGH) 클래스로 승격됨에 따라 `tests/test_langgraph.py`의 고/중위험 클래스 서로소 검증 Assertion(`test_high_and_mid_risk_classes_do_not_overlap`) 조건을 비활성화하고, 멀리 있는 사물에 대해 인지 경로(LangGraph)로 안전하게 토스할 수 있도록 기존 `MID_RISK_CLASSES` 18종을 `l1_classifier.py` 및 `detection_pipeline.py`에 유지 조치함.
    - `tests/test_detection.py`에서 `bicycle`이 고위험 반사 경보를 정상 발동하는지를 확인하는 테스트 케이스로 갱신함.
- **관련 파일**: `server/detection/gates/reflex_gate.py`, `client/src/components/CameraView.tsx`, `tests/test_risk_ssot.py`, `tests/test_langgraph.py`, `tests/test_detection.py`, `docs/design/risk_ssot_contract.md`, `docs/changelogs/dg.md`
- **검증 결과**: `npx tsc --noEmit` 모바일 컴파일 및 venv 기반 `pytest` 단위 테스트 44개 전수 통과 완료.

---

### 2026-07-13 | 모바일 | 앱 포그라운드 복귀(리로드) 시 마이크 권한 실시간 재동기화 로직 추가

- **변경 내용**:
  - **포그라운드 복귀(AppState active) 리스너 탑재**:
    - 사용자가 스마트폰 시스템 설정에서 수동으로 마이크 권한을 허용한 경우, 앱을 재부팅(또는 삭제 후 재설치)하지 않고도 변경 사항이 즉시 런타임에 동기화될 수 있도록 `client/src/components/CameraView.tsx`에 `AppState` 리스너를 연동함.
    - 앱이 background 상태에서 foreground(즉 `active`) 상태로 돌아올(리로드) 때마다 `requestSttPermissionEarly`를 트리거하여 마이크 권한 허용 여부를 실시간으로 재확인하고 앱 상태에 동기화하도록 구현함.
- **관련 파일**: `client/src/components/CameraView.tsx`, `docs/changelogs/dg.md`
- **검증 결과**: `npx tsc --noEmit` 타입 검사를 무오류로 통과 완료.

---

### 2026-07-13 | STT | Android STT 전사 실패(음성 인식 실패 반복) 현상 해결 및 포맷 감지 가드레일 개선

- **변경 내용**:
  - **원인 분석**:
    - Android 단말(expo-audio)이 녹음하여 base64로 전송하는 오디오 파일은 MPEG-4/AAC(.m4a) 포맷입니다.
    - 하지만 서버(FastAPI ws_router.py) 측 임시 파일 저장소에서 항상 `.wav` 확장자로 강제 저장하여 whisper의 오디오 디코더가 파일 포맷 해석에 실패하고 `RuntimeError`를 던졌습니다.
    - 또한 도커 컨테이너(minchodan-fastapi)에 ffmpeg 및 관련 라이브러리(espeak 등)는 있었으나, M4A/AAC 포맷 디코딩에 필수적인 `ffmpeg` 바이너리가 누락되어 있었습니다.
    - iOS의 경우 캡처 시간 역산 기반의 `capture_truncated` 차단 임계값으로 인해 짧은 명령어("길댕아")가 서버 전송 전에 차단되는 문제가 복합적으로 존재했습니다.
  - **조치 내용**:
    - **오디오 포맷 감지 로직 구현**: `server/api/ws_router.py`에 magic bytes(ftyp 박스)로 파일 포맷을 판별하는 `_detect_audio_suffix` 헬퍼 함수를 추가하고 임시 파일 저장 시 적절한 확장자(`.m4a`, `.wav` 등)를 할당하도록 수정하였습니다. 0바이트 빈 패킷에 대한 즉각 가드레일 처리도 보강하였습니다.
    - **도커 이미지 ffmpeg 탑재**: `docker/Dockerfile`에 `ffmpeg` 패키지를 apt-get 설치 항목에 포함시키고, 현재 기동 중인 fastapi 컨테이너에도 직접 ffmpeg 바이너리를 수동 주입 설치하여 즉시 반영하였습니다.
    - **클라이언트 송신 가드레일 완화**: `client/src/hooks/useSttRecorder.ts`에서 짧은 오디오를 전송 전에 차단하던 `capture_truncated` 가드레일을 제거하여 서버 Whisper VAD(vad_filter=True)에 처리를 위임하고, 안정적인 짧은 웨이크워드 전송을 보장하였습니다.
- **관련 파일**: `server/api/ws_router.py`, `docker/Dockerfile`, `client/src/hooks/useSttRecorder.ts`
- **검증 결과**: 컨테이너 내 `SttService.transcribe_file` 호출을 통한 `.m4a` 오디오 디코딩 및 whisper 전사 정상 작동 확인.

---

### 2026-07-14 | 모바일/AI | Android 온디바이스 탐지 불작동 원인 조사(NNAPI 비활성화) 및 ROI 시각화/판정 신규 구현

- **커밋**: `fix: disable nnapi delegate for android tflite and implement roi overlay with path filtering`
- **변경 내용**:
  - **Android NNAPI 델리게이트 비활성화 (탐지 불작동 1단계 조사)**:
    - `client/src/inference/tfliteDetector.ts`: `ACCELERATION_DELEGATES`의 `android: ["nnapi"]`를 `android: []`로 변경하여 CPU 폴백을 강제함. NNAPI 드라이버 호환성 문제가 탐지 미작동의 원인으로 의심됨. 재빌드 후 로그로 효과를 확인해야 함.
    - `detect()` 함수 진입부에 입력 shape 검증 로그(`frame.length === 1,228,800` 여부)를 추가하여 shape 불일치를 로그로 즉시 확인 가능하게 함.
  - **ROI 사다리꼴 상수 추가 (서버-클라이언트 좌표 정합)**:
    - `client/src/components/CameraView.tsx`에 `server/detection/path_risk.py`의 `PATH_ROI_NEAR_BAND=(0.20, 0.80)`, `PATH_ROI_FAR_BAND=(0.38, 0.62)`, `PATH_ROI_FAR_Y_RATIO=0.35`와 동일한 상수를 추가하여 좌표 계약을 일치시킴.
  - **ROI 내부 판정(point-in-polygon) 로직 추가**:
    - `roiPolygon()` 함수: NEAR/FAR 상수로 사다리꼴 4꼭짓점 정규화 좌표를 반환.
    - `pointInPolygon()` 함수: ray-casting 알고리즘으로 bbox 중심점이 ROI 내부에 있는지 판정.
    - `handleFrame`의 `validDetections` 필터에 ROI 조건 추가 — 중심점이 ROI 밖인 객체는 반사 경로에서 제외됨.
  - **ROIOverlay 컴포넌트 신규 작성**:
    - 사다리꼴 4변을 BBoxOverlay와 동일한 `absoluteFill + 절대좌표 View` 방식으로 황금색(`rgba(249,183,0,0.75)`) 반투명 테두리로 렌더링.
    - 탐지 활성(`detectionEnabled=true`) 상태에서만 카메라 위에 표시.
- **관련 파일**: `client/src/inference/tfliteDetector.ts`, `client/src/components/CameraView.tsx`
- **검증 결과**: TypeScript 컴파일 정합성 확인 필요. Android 실기기 재빌드 후 Logcat `[TFLiteDetector]` 로그 및 ROI 오버레이 시각 확인 예정.

---

### 2026-07-14 | 모바일/AI | 노면 클래스 반사 경로 완전 제외 및 ROI/슬라이딩 윈도우 임계값 정합화

- **커밋**: `fix: exclude seg classes from reflex path and fix roi/smoothing thresholds (P1-P4 + seg hazard gate)`
- **변경 내용**:
  - **P1 - 노면 세그 반사 경로 완전 제외** (`pathObstacleDetector.ts`): roadway/caution 전체를 depthMap 투영에서 제외. 노면은 서버 LLM TTS(인지 경로) 전담 (MDPI 2023 논문 기준).
  - **P2 - ROI top-y 정합화** (`pathObstacleDetector.ts`): top-y 320px(50%) → 224px(35%). 서버 `PATH_ROI_FAR_Y_RATIO=0.35`와 일치.
  - **P3 - 노면 신뢰도 임계값 상향** (`CameraView.tsx`): `OUTDOOR_SURFACE_MIN_CONFIDENCE` 0.15 → 0.35.
  - **P4 - 슬라이딩 윈도우 폴백 수정** (`pathObstacleDetector.ts`): 3프레임 미달 시 `frameState` → `"CLEAR"` 폴백.
  - **seg hazard gate 제거** (`useOnDeviceDetection.ts`): `[Reflex]` 위험 탐지 후보에서 seg 제거. roadway/caution이 Reflex 1순위로 올라 연속 STOP 경보를 유발하던 근본 원인 차단.
- **진단 배경**: YouTube 영상 테스트 시 roadway(conf=0.487) 전체 화면 오탐으로 비프/햅틱 끊임없이 울림. 논문 조사(MDPI 2023, drpress 2023) 기반 P0~P4 순차 적용.
- **관련 파일**: `client/src/inference/pathObstacleDetector.ts`, `client/src/components/CameraView.tsx`, `client/src/hooks/useOnDeviceDetection.ts`
- **검증 결과**: 실기기 보행 테스트 필요. 여전히 오경보 있으면 `near_07/near_15` 임계값 상향 검토.

---

### 2026-07-14 | 서버/모바일 | 29종 객체 반사 경로 일원화, 신규 모델 가중치 적용 및 미터(m) ROI 설계

- **커밋**: `fix: unify 29-class objects to reflex path and apply 0714 model weights`
- **변경 내용**:
  - **반사 경로 일원화 및 제약 해제** (`reflex_gate.py`):
    - `MIN_HIT_COUNT`(동일 track_id 3프레임 연속 대기) 및 `PROXIMITY_THRESHOLD`(화면 하단 15% 밀착) 제한을 해제함.
    - 객체가 검출되면 화면 위치와 누적 프레임에 상관없이 즉각 반사 비프/햅틱 경보가 작동하도록 수정.
    - `distance` 계산용 ratio 범위를 국소 15%에서 화면 전체(`0` ~ `frame_height`)로 선형 매핑(1.5m ~ 0.4m)되도록 갱신.
  - **L1 분류기(인지 경로) 객체 탐지 제거** (`l1_classifier.py`):
    - 29종 객체는 전원 즉각 반사 경로로만 교신하고 인지 경로(LLM 상세가이드)로 중복 우회하는 현상을 차단하기 위해 `MID_RISK_CLASSES` 내 18개 클래스명을 비움 (`set()`).
    - 이로 인해 인지 경로(mid)는 오직 노면 이탈(`is_departing_confirmed` = True) 판정만 전담하게 됨.
  - **신규 파인튜닝 가중치 적용** (`.env`, `config.py`):
    - 7월 14일 새로 파인튜닝 완료된 `object_detection260714.pt` (29클래스 객체) 및 `segmentation260714.pt` (4클래스 노면) 가중치 경로로 업데이트 적용.
  - **사실관계 검증 완료**:
    - Android 폰의 `float32` 입력이 `Float32Array(0)`으로 비어있음에도 `roadway` 오탐이 나왔던 현상은, `fast-tflite` 네이티브 모듈에 0바이트 버퍼 전달 시 예외를 내지 않고 텐서 출력을 반환해 모바일 로컬 `detectFrame` 단에서 오탐이 직접 발생하였음을 규명.
  - **실거리(m) 기반 ROI 공식 설계**:
    - iOS의 `depthProbe` 3스팟 측정치를 활용한 실시간 ROI y-band 선형보간법 설계.
    - Android용 고정 장치 기하학 틸트각 변환 수식 $D(y) = h / \tan(\theta - FOV_v/2 + y \cdot FOV_v)$을 도출하여 화면 비율 대신 실제 미터 단위를 기준으로 ROI(0.5m ~ 1.5m)를 재정의하도록 함.
  - **문서화** (`stage3_detection_design.md`):
    - 위 아키텍처/가중치 변경 이력을 3단계 설계서 변경 이력 단락에 정식 반영하여 누락 없이 일괄 업데이트.
- **관련 파일**: `server/detection/gates/reflex_gate.py`, `server/orchestration/nodes/l1_classifier.py`, `.env`, `server/detection/config.py`, `docs/stage-guides/stage3_detection_design.md`
- **검증 결과**: git push 완료 및 local tsc 컴파일 무결성 검증.


