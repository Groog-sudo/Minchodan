# Changelog - th (태현)

> 이 파일은 **th(태현)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-06-30 | 공통 | 프로젝트 스캔 분석 스크립트 추가

- **커밋**: `feat: 프로젝트 스캔 분석 스크립트 추가`
- **변경 내용**:
  - 프로젝트 루트 구조, 핵심 파일, 문서, Python 파일, 기술 키워드 매칭 결과를 수집하는 `scripts/project_scan.py`를 추가했습니다.
  - 스캔 결과 산출물 `project_scan_report.md`, `project_scan_summary.json`을 생성했습니다.
- **관련 파일**: `scripts/project_scan.py`, `project_scan_report.md`, `project_scan_summary.json`, `project_scan_verification.md`
- **검증 결과**: `python scripts\project_scan.py`, `python -m py_compile scripts\project_scan.py` 통과

---

### 2026-06-30 | 3단계 | AI Hub 인도보행 데이터셋 스캔 스크립트 추가

- **커밋**: `3단계: AI Hub 인도보행 데이터셋 스캔 스크립트 추가`
- **변경 내용**:
  - 원천데이터를 복사하지 않고 외부 경로를 읽어 폴더별 파일 수, 용량, 확장자, 샘플 경로를 정리하는 `scripts/scan_aihub_walk_dataset.py`를 추가했습니다.
  - `.env.example`에 `AIHUB_WALK_DATASET_ROOT` 예시 경로를 추가했습니다.
  - 실제 데이터셋 `C:\Users\USER\Desktop\dataset\인도보행 영상`을 스캔하여 `outputs/aihub_walk_dataset_scan/`에 보고서를 생성했습니다.
- **관련 파일**: `scripts/scan_aihub_walk_dataset.py`, `.env.example`, `outputs/aihub_walk_dataset_scan/aihub_walk_dataset_report.md`
- **검증 결과**: `python -m py_compile scripts\scan_aihub_walk_dataset.py`, `python scripts\scan_aihub_walk_dataset.py --dataset-root "C:\Users\USER\Desktop\dataset\인도보행 영상"` 통과

---

### 2026-06-30 | 7단계 | 이번 주 단말 TTS 데모 계약 고정

- **커밋**: `7단계: 단말 TTS 데모 계약 고정`
- **변경 내용**:
  - 이번 주 TTS는 단말 `react-native-tts`를 데모 스탠드인으로 사용하도록 `client/src/services/ttsPlayer.ts`를 추가했습니다.
  - 운영 반사 경로는 추후 사전 합성 클립으로 교체 예정이며, `message_hint = {id, type, text}` 계약을 고정했습니다.
  - 기존 탐지 스키마 위에 얹는 서버 message_hint 빌더 `server/detection/risk_rules.py`를 추가했습니다.
- **관련 파일**: `client/src/services/ttsPlayer.ts`, `server/detection/risk_rules.py`
- **검증 결과**: `python -m py_compile server\detection\risk_rules.py` 통과

---

### 2026-06-30 | 3단계 | AI Hub 바운딩박스 XML 구조 검증

- **커밋**: `3단계: AI Hub 바운딩박스 XML 구조 검증`
- **변경 내용**:
  - CVAT 형식 XML을 읽어 이미지 수, 박스 수, 라벨 분포, 데모 후보 이미지를 요약하는 `scripts/inspect_aihub_bbox_xml.py`를 추가했습니다.
  - `0820_26.xml` 기준 이미지 99장, 박스 887개, 데모 후보 이미지 98장을 확인했습니다.
  - 데모 후보로 `MP_SEL_B026975.jpg`, `MP_SEL_B027003.jpg`, `MP_SEL_B026972.jpg` 등을 확인했습니다.
- **관련 파일**: `scripts/inspect_aihub_bbox_xml.py`, `outputs/aihub_walk_dataset_scan/bbox_0820_26_report.md`
- **검증 결과**: `python -m py_compile scripts\inspect_aihub_bbox_xml.py`, `python scripts\inspect_aihub_bbox_xml.py --xml-path "C:\Users\USER\Desktop\dataset\인도보행 영상\바운딩박스\Bbox_10_new\Bbox_0691\0820_26.xml"` 통과

---

### 2026-06-30 | 3단계+7단계 | YOLO 샘플 추론과 단말 TTS 메시지 연결

- **커밋**: `3단계: YOLO 샘플 추론 TTS 메시지 연결`
- **변경 내용**:
  - AI Hub 바운딩박스 샘플 이미지 3장을 `data/raw/aihub_walk_sample/`에 복사해 데모 입력으로 준비했습니다.
  - `scripts/run_yolo_tts_demo.py`를 추가해 YOLO 추론 결과를 `direction`, `distance`, `risk_level`, `message_hint`가 포함된 JSON으로 저장하도록 했습니다.
  - `server/detection/direction.py`를 추가해 bbox 기반 방향과 거리 계산을 분리했습니다.
  - `server/detection/risk_rules.py`에 데모용 결정적 위험도 계산 함수를 추가했습니다.
  - `server/detection/yolo_detector.py`에 ByteTrack 의존성 누락 시 `predict()` 폴백과 데모용 tracking 비활성 옵션을 추가했습니다.
  - `server/detection/__init__.py`를 lazy import 구조로 바꿔 후처리 모듈 import 시 Redis/YOLO 선택 의존성이 즉시 로드되지 않게 했습니다.
- **관련 파일**: `scripts/run_yolo_tts_demo.py`, `server/detection/direction.py`, `server/detection/risk_rules.py`, `server/detection/yolo_detector.py`, `server/detection/__init__.py`
- **검증 결과**: `python -m py_compile server\detection\yolo_detector.py scripts\run_yolo_tts_demo.py`, `python scripts\run_yolo_tts_demo.py --input data\raw\aihub_walk_sample --model server\models\yolo26n\object_detection.pt --device cpu` 통과
- **샘플 결과**:
  - `MP_SEL_B026972.jpg`: `detections=6`, `오른쪽 앞 차량 주의`
  - `MP_SEL_B026975.jpg`: `detections=6`, `왼쪽 앞 차량 주의`
  - `MP_SEL_B027003.jpg`: `detections=1`, `정면 보행자 주의`

---

### 2026-06-30 | 공통 | 담당자 학습형 LLM 협업 규칙 문서화

- **커밋**: `docs: 담당자 학습형 LLM 협업 규칙 추가`
- **변경 내용**:
  - LLM이 모든 코드를 대신 작성하지 않고, 담당자가 발표에서 설명해야 하는 핵심 로직을 직접 작성하도록 작업 분담 기준을 문서화했습니다.
  - `docs/llm_collaboration_workflow.md`를 추가해 담당자 직접 작성 영역과 LLM 보조 영역을 구분했습니다.
  - `AGENTS.md`, `SKILLS.md`, `docs/README.md`에서 해당 문서를 참조하도록 업데이트했습니다.
- **관련 파일**: `docs/llm_collaboration_workflow.md`, `AGENTS.md`, `SKILLS.md`, `docs/README.md`
- **검증 결과**: 문서 링크와 changelog 반영 확인

---

### 2026-06-30 | 3단계+7단계 | YOLO/TTS MVP 다음 작업 계획 문서화

- **커밋**: `docs: YOLO TTS MVP 다음 작업 계획 추가`
- **변경 내용**:
  - `docs/yolo_tts_mvp_next_steps.md`를 추가해 2026-07-01 이후 작업 순서와 직접 코딩 항목을 정리했습니다.
  - 내일부터는 `direction.py`, `risk_rules.py`, 데모 실행 명령어를 담당자가 직접 입력하고 LLM은 연결·검증·문서화를 맡도록 명시했습니다.
  - `docs/llm_collaboration_workflow.md`에 다음 세션 시작 규칙을 추가했습니다.
  - `docs/README.md` 문서 인덱스에 다음 작업 계획 문서를 등록했습니다.
- **관련 파일**: `docs/yolo_tts_mvp_next_steps.md`, `docs/llm_collaboration_workflow.md`, `docs/README.md`
- **검증 결과**: 다음 작업 문서 생성 및 문서 인덱스 링크 반영 확인

---

### 2026-06-30 | 3단계+7단계 | Reflex Path 방향/거리/위험도 판정 온디바이스 로직 고도화

- **커밋**: `refactor: Reflex Path 온디바이스 기하 로직 고도화`
- **변경 내용**:
  - `server/detection/direction.py`의 `estimate_direction`을 중심점 3등분에서 BBox 회랑 띠(Corridor) 침범 기반으로 변경하고, 거리에 따라 정면 판정 폭을 동적으로 조정하도록 개선했습니다.
  - `estimate_distance`에 클래스별 면적 임계값 차등 로직(MVP 패치)을 적용하여, 작은 객체(볼라드, 킥보드 등)에 대해서도 적절한 타이밍에 경고가 발생하도록 수정했습니다.
  - `server/detection/risk_rules.py`의 `build_message_hint` 및 `estimate_risk_level`을 수정하여, 측면이거나 멀리 있는 객체는 Reflex를 침묵시키고(Cognitive 위임), 정면의 근접 객체에 대해서만 긴급 정지("STOP") 힌트를 생성하도록 고도화했습니다.
  - `server/detection/gates/reflex_gate.py` 내부 중복 방향 판정 로직을 통합했습니다.
  - `scripts/run_yolo_tts_demo.py` 호출부를 변경된 시그니처에 맞게 수정했습니다.
- **관련 파일**: `server/detection/direction.py`, `server/detection/risk_rules.py`, `server/detection/gates/reflex_gate.py`, `scripts/run_yolo_tts_demo.py`
- **검증 결과**: `python -m pytest tests/test_detection.py` (21개 통과)

---

### 2026-06-30 | 3단계 | YOLO Segmentation 학습 데이터셋 변환 스크립트 추가

- **커밋**: `feat: YOLO Segmentation 학습 데이터셋 준비`
- **변경 내용**:
  - AI Hub 서피스마스킹 XML 폴리곤 데이터를 정규화된 YOLO Segmentation txt 포맷으로 변환하는 `scripts/convert_aihub_seg_to_yolo.py` 스크립트를 추가했습니다.
  - 6개의 원본 라벨(`sidewalk`, `caution_zone`, `roadway` 등)을 YOLO 학습용 4개 라벨(`sidewalk_normal`, `caution`, `roadway`, `braille_normal`)로 통합 매핑했습니다.
  - train/val 분할 및 하드링크 복사를 지원하며, 학습을 위한 `training/configs/aihub_yolo_segmentation.yaml` 설정 파일을 생성했습니다.
- **관련 파일**: `scripts/convert_aihub_seg_to_yolo.py`, `training/configs/aihub_yolo_segmentation.yaml`
- **검증 결과**: 100개 이미지 샘플 변환 테스트 완료 (`training/datasets/segmentation/aihub_0820_26/`에 정상 생성 및 라벨 정규화 값 0~1 사이 검증)

---

### 2026-07-01 | 3단계 | YOLO Segmentation 모델 학습(RTX 5090) 백그라운드 실행

- **상태**: `진행 중`
- **변경 내용**:
  - `convert_aihub_seg_to_yolo.py`를 실행하여 전체 46,000장의 데이터를 YOLO Segmentation 포맷으로 변환을 완료했습니다.
  - `yolov8n-seg.pt` 가중치를 다운로드하고 `batch=-1`(자동) 설정으로 RTX 5090(GPU 0)에서 100 Epoch 백그라운드 학습을 시작했습니다 (`project=training/runs`, `name=seg_exp1`).

---

### 2026-07-01 | 1단계 | WebSocket Gateway 실시간 통신망 구현

- **커밋**: `feat: 1단계 WebSocket Gateway 뼈대 및 라우팅 구현`
- **변경 내용**:
  - `server/api/` 하위에 FastAPI WebSocket 통신을 위한 스캐폴딩(설정, 스키마, 인증, 세션 관리, 하트비트)을 구성했습니다.
  - Pydantic v2 `BaseSettings`의 `extra="ignore"` 옵션을 적용하여 `.env` 파싱 유연성을 확보했습니다.
  - 담당자가 직접 핵심 라우팅 로직(`ws_router.py`)을 타이핑하여 완성했습니다 (탐지 프레임 수신 및 Redis Streams `risk.events` 발행).
  - 테스트 코드 `tests/test_api_ws.py`를 작성하여 인증(hello/welcome)과 ping-pong 하트비트, detection ack 반환이 정상 작동함을 검증했습니다.
- **관련 파일**: `server/api/*.py`, `server/main.py`, `tests/test_api_ws.py`
- **검증 결과**: `python -m pytest tests/test_api_ws.py -v` (2개 테스트 모두 통과)

---

### 2026-07-01 | 2단계 | 모바일 카메라 이중 스트림 캡처

- **커밋**: `feat: 2단계 모바일 카메라 이중 스트림(Reflex/Cognitive) 캡처 로직`
- **변경 내용**:
  - `docs/llm_collaboration_workflow.md` 업데이트: 취업 포트폴리오를 위한 **LLM 60 : 담당자 40** 하드코드 원칙 상향 적용.
  - `client/src/services/frameCapture.ts`: Base64 변환 프레임에 Event ID 및 stream 타입 메타데이터 추가하여 WebSocket 전송 (담당자 하드코딩).
  - `client/src/hooks/useCamera.ts`: UI 스레드를 방해하지 않는 `setInterval` 기반 이중 타이머(8fps 반사 / 2fps 인지) 구현. `clearInterval`의 정확한 클린업 위치 수정 (모의 면접 진행).
  - 기존 레포지토리에 구현된 서버 측 프레임 디코더(`frame_decoder.py`) 및 스트림 분기 라우터(`stream_splitter.py`) 연동.
- **관련 파일**: `client/src/hooks/useCamera.ts`, `client/src/services/frameCapture.ts`
- **검증 결과**: `python -m pytest tests/test_frame_decode.py -v` (21개 서버 테스트 모두 통과)

---

### 2026-07-02 | 3단계 | YOLO 대규모 풀 학습 파이프라인 리팩토링 및 5090 세그멘테이션 학습 완료

- **커밋**: `refactor: YOLO 학습 파이프라인 리팩토링 및 train_common AttributeError 해결`
- **변경 내용**:
  - `scripts/run_desktop_full_training.py` 의 `run_detection` / `run_segmentation` `NameError` 버그를 정의 순서 조정을 통해 해결했습니다.
  - `training/train_common.py` 에서 YOLO 모델 학습 후 결과 경로 반환 시 발생하던 `AttributeError: 'YOLO' object has no attribute 'path'` 에러를 수정했습니다. 존재하지 않는 YOLO 인스턴스의 `.path` 속성에 접근하는 대신, 파라미터로 제공된 `project_path` 변수를 활용하여 `best.pt` 경로를 정확히 반환하도록 우회 구현했습니다.
  - `training/train_detection.py` 와 `training/train_segmentation.py` 내부의 수십 줄에 달하는 명시적 파라미터 인자 매핑을 제거하고, `**vars(args)` 딕셔너리 언패킹 방식을 적용하여 단 한 줄의 코드로 통일하였습니다.
  - `training/train_common.py`에 학습 경로 혹은 데이터셋 경로에 `segmentation`이 포함될 경우, 데스크탑 RTX 5090 VRAM 32GB 투트랙 최적화(가속)를 위한 `amp=True`, `cache='disk'`가 자동 업데이트되도록 방어 로직을 주입했습니다.
  - `.env` 파일 맨 앞에 유니코드 쓰기 작업 시 인코딩 오류로 붙었던 BOM(Byte Order Mark) 특수문자(`\xef\xbb\xbf`)를 제거하여, `python-dotenv` 라이브러리가 데이터셋 경로(`AIHUB_WALK_DATASET_ROOT`)를 인식하지 못하던 경로 파싱 실패 오류를 원천 차단했습니다.
  - 데스크탑에서 35만 장 기반 `Segmentation` 100 Epoch 풀 학습이 정상 완료되고 `best.pt` 및 `last.pt` 가중치 파일(약 6.5MB)이 `training/runs/seg_exp1/weights/` 디렉토리에 이상 없이 저장되었음을 최종 검증했습니다.
- **관련 파일**: `scripts/run_desktop_full_training.py`, `training/train_common.py`, `training/train_detection.py`, `training/train_segmentation.py`, `.env` (git-ignored), `training/configs/aihub_yolo_segmentation.yaml`
- **검증 결과**: `py_compile` 문법 검사 통과 및 학습 완료 결과물(`best.pt`) 물리 파일 존재 여부 확인 완료

---

### 2026-07-02 | 2단계+7단계 | 모바일 클라이언트 의존성 설치 및 타입 정합 수정

- **커밋**: `fix: 클라이언트 설치 의존성 타입 정합`
- **변경 내용**:
  - `client/`에서 누락된 Expo/React Native 의존성을 설치하고 `expo-file-system/legacy`, `expo-av`, `react-native-fast-tflite` 모듈 로딩 상태를 확인했습니다.
  - `react-native-fast-tflite` v3 API에 맞춰 모델 로딩 시 delegate 배열을 전달하고, 입력/출력 텐서를 `ArrayBuffer` 기반으로 처리하도록 수정했습니다.
  - 서버와 API 명세의 최신 계약에 맞춰 반사 경보 타입을 `reflex_alert`로 정리하고, `panning`, `beep_interval_ms`, `haptic_pattern` 필드를 클라이언트 타입에 반영했습니다.
  - `expo-av` v16의 `setVolumeAsync(volume, audioPan)` 시그니처에 맞춰 반사 비프음 좌우 지향 설정을 수정했습니다.
- **관련 파일**: `client/src/hooks/useOnDeviceDetection.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/services/audioEngine.ts`, `client/src/types/detection.ts`
- **검증 결과**: `npm ls expo-file-system react-native-fast-tflite expo-av --depth=0`, `npx tsc --noEmit` 통과

---

### 2026-07-05 | 3단계 | YOLO 탐지 및 반사 경로 게이트 하드코딩 구현 완료

- **커밋**: eat: YOLO 탐지 및 Reflex Gate 하드코딩 구현 완성
- **변경 내용**:
  - server/detection/gates/reflex_gate.py 파일에 시각장애인에게 치명적인 5대 돌발/동적 장애물(car, 	ruck, us, motorcycle, scooter)을 식별하는 하드코딩 로직을 추가했습니다. 면접 대비용 주석(💡 [면접 대비 주석])을 통해 Panning 및 Distance 결정 로직의 배경을 꼼꼼하게 문서화했습니다.
  - server/detection/yolo_detector.py에 불필요하게 중복 선언되어 있던 load() 메서드를 정리하고, BBox 파싱과 관련하여 발생했던 Python 문법적 오류(제너레이터 표현식 오류, f-string 포맷팅 괄호 등)를 수정했습니다.
  - scripts/run_desktop_full_training.py의 subprocess.run 파싱 오류를 리스트 확장(extend) 방식으로 교정했습니다.
  - 담당자가 직접 작성한 반사 게이트 로직 및 탐지 결과 파서를 기반으로 전체 파이프라인 검증용 유닛 테스트 21개를 100% Passed로 완벽히 통과했습니다.
- **관련 파일**: server/detection/gates/reflex_gate.py, server/detection/yolo_detector.py, scripts/run_desktop_full_training.py
- **검증 결과**: python -m pytest tests/test_detection.py -v 21개 통과 완료

---

### 2026-07-06 | 3단계 | YOLO 학습 결과물 자동 네이밍 최적화

- **커밋**: eat: YOLO 학습 파이프라인 가중치 자동 네이밍 최적화
- **변경 내용**:
  - 	raining/train_common.py에 학습 완료 후 생성되는 est.pt 가중치 파일을 자동으로 복사하여 당일 날짜(YYYYMMDD)가 포함된 형태(예: est_20260706.pt)로 백업하도록 후처리 로직을 추가했습니다.
  - scripts/run_desktop_full_training.py의 결과 요약 출력부에서도 갱신된 날짜 포함 파일명을 .env에 설정하도록 가이드를 개선했습니다.
  - 서버 재부팅 직전까지 완료되었던 3단계 탐지/세그멘테이션 풀 학습의 est.pt 가중치 결과물을 물리적으로 복사하여 성공적으로 보존했습니다.
- **관련 파일**: 	raining/train_common.py, scripts/run_desktop_full_training.py

---

### 2026-07-06 | 프로젝트 종합 평가 및 최신 dev 병합 동기화

- **커밋**: chore: dev 브랜치 병합 동기화 및 프로젝트 스캔 보고서 갱신
- **변경 내용**:
  - dev 브랜치에 반영된 170여 개 이상의 최신 팀원 작업물(React Native iOS/Android 클라이언트 연동, CoreML/TFLite 추론 구조, TTS 실시간 오디오 서비스 등)을 	h 브랜치로 병합(Merge)하여 동기화 완료했습니다.
  - 최신 코드를 기반으로 scripts/project_scan.py를 실행하여 전체 파일 통계 및 핵심 기술 스택(yolo, langchain, fastapi) 사용 현황을 종합한 project_scan_report.md와 project_scan_summary.json을 갱신 및 커밋했습니다.
  - 해당 스캔 결과와 병합된 server/tts/tts_service.py 코드를 바탕으로 전체 MVP 7단계 중 1~3단계 완성도 평가 및 방어적 코딩(I/O 예외처리 보강) 관점의 코드 리뷰를 수행했습니다.
- **관련 파일**: project_scan_report.md, project_scan_summary.json, docs/changelogs/th.md

---

### 2026-07-07 | 운영자 콘솔 | React SSE 관제 콘솔 학습형 스캐폴드 추가

- **커밋**: `feat: React SSE 운영자 콘솔 학습형 스캐폴드 추가`
- **변경 내용**:
  - `console/` 디렉토리에 Vite + React + TypeScript 기반 운영자 관제 콘솔 스캐폴드를 신규 구성했습니다.
  - TH 하드코딩 비중을 80%로 높이기 위해 `useMonitorStream.ts`의 `EventSource` 연결, `event_type` 분기, 상태 갱신 로직은 직접 작성 영역으로 비워두었습니다.
  - SystemMetrics, RiskEventLog, SessionStatus, DetectionFeed, AI Pipeline Monitor 컴포넌트는 최소 placeholder와 직접 구현 지시만 남겼습니다.
  - AI는 프로젝트 설정, 폴더 구조, 빌드 가능한 최소 레이아웃까지만 보조하도록 범위를 축소했습니다.
- **관련 파일**: `console/package.json`, `console/src/api/useMonitorStream.ts`, `console/src/App.tsx`, `console/src/components/*.tsx`, `console/src/types/monitor.ts`, `console/src/styles.css`, `console/README.md`
- **검증 결과**:
  - `npm install` 완료
  - `npm run build` 통과

---

### 2026-07-08 | 운영자 콘솔 | SSE 이벤트 렌더링 및 발표 대응 주석 보강

- **커밋**: `feat: 운영자 콘솔 SSE 상태 렌더링 보강`
- **변경 내용**:
  - `useMonitorStream.ts`에 `session_status`, `detection_event`, `llm_status`, `rag_result`, `tts_status`, `stt_status` 이벤트 분기와 상태 갱신 로직을 보강했습니다.
  - `SessionStatus` 컴포넌트에서 단말 `device_id`, 플랫폼, 연결 상태, RTT, 마지막 수신 시간을 실제 목록으로 표시하도록 수정했습니다.
  - `SystemMetrics` 컴포넌트에서 GPU 사용률, 메모리, provider, RTT, queue, dropped frame, 에러 상태를 카드 형태로 표시하도록 수정했습니다.
  - `AiPipelineMonitor` 컴포넌트에서 LLM, RAG, TTS, STT 상태와 최근 안내문을 표시하도록 수정했습니다.
  - 화면에 노출되던 내부 작업 문구(`TH 직접 구현`)를 운영자 관제 용어(`시스템 상태`, `단말 연결`, `탐지 메타데이터`, `AI 상태`, `위험 로그`)로 교체했습니다.
  - 발표/면접 대응을 위해 SSE 단방향 구독, device_id 기준 upsert, 최신 상태성 데이터와 누적 로그성 데이터의 차이, AI 상태 보존 방식에 대한 주석을 보강했습니다.
- **관련 파일**: `console/src/api/useMonitorStream.ts`, `console/src/components/AiPipelineMonitor.tsx`, `console/src/components/DetectionFeed.tsx`, `console/src/components/RiskEventLog.tsx`, `console/src/components/SessionStatus.tsx`, `console/src/components/SystemMetrics.tsx`
- **검증 결과**:
  - `cd console && npm run build` 통과
