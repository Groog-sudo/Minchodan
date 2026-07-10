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
