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

---

### 2026-07-09 | 3단계 | DETECTOR_TYPE 환경변수 실제 연결

- **변경 내용**:
  - `server/detection/config.py`가 `.env`의 `DETECTOR_TYPE`를 실제로 읽도록 수정했습니다.
  - `DETECTOR_TYPE=mock`이면 노트북/데모 환경에서 `MockDetector`/`MockSegmentor`를 강제 사용하고, `DETECTOR_TYPE=yolo`이면 가중치 로드 경로로 진입하도록 분기했습니다.
  - 잘못된 값은 서버를 죽이지 않고 경고 로그 후 `mock`으로 안전 폴백하게 했습니다.
  - `docs/ops/environment_variables.md`의 기존 "죽은 변수" 설명을 현재 코드와 맞게 정정했습니다.
- **관련 파일**: `server/detection/config.py`, `docs/ops/environment_variables.md`

---

### 2026-07-09 | 공통 | docs 폴더 용도별 하위 분류 정리

- **변경 내용**:
  - `docs/dev-guides/` 아래에 `prompts/`, `templates/`, `integration/` 하위 폴더를 만들어 1회성 프롬프트, 설계 예시, 통합 지침서를 용도별로 분리했습니다.
  - `docs/ops/` 아래에 `reports/` 하위 폴더를 만들어 단발성 연동 보고서를 운영 기준 문서와 분리했습니다.
  - `README.md`, `SKILLS.md`, `docs/README.md`의 경로 안내를 현재 구조에 맞게 정정했습니다.
- **관련 파일**: `README.md`, `SKILLS.md`, `docs/README.md`, `docs/dev-guides/prompts/`, `docs/dev-guides/templates/`, `docs/dev-guides/integration/`, `docs/ops/reports/`
- **검증 결과**: 100개 이미지 샘플 변환 테스트 완료 (`training/datasets/segmentation/aihub_0820_26/`에 정상 생성 및 라벨 정규화 값 0~1 사이 검증)

---

### 2026-07-09 | 3단계 | YOLO 가중치 폴백 경로 및 surface-only 인지 발행 보강

- **변경 내용**:
  - `server/detection/config.py`에서 `DETECTOR_TYPE=yolo`일 때 우선 커스텀 경로(`det_best_20260705.pt`, `segbest.pt`)를 보고, 해당 파일이 없으면 현재 워크스페이스에 실제 존재하는 `object_detection.pt`, `segmentation.pt`로 한 번 더 폴백하도록 보강했습니다.
  - `server/detection/detection_pipeline.py`와 `server/bus/producer.py`에서 탐지 박스 없이 노면 분할 결과만 있는 `mid/low` 프레임도 Redis `risk.events`로 발행되게 연결했습니다.
  - `tests/test_detection.py`에 `surface-only mid` 이벤트 발행 회귀 테스트를 추가했습니다.
- **관련 파일**: `server/detection/config.py`, `server/detection/detection_pipeline.py`, `server/bus/producer.py`, `tests/test_detection.py`

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

---

### 2026-07-08 | 운영자 콘솔 | 1차 MVP 마감 정리

- **변경 내용**:
  - `console/README.md`의 1차 MVP 상태를 스캐폴드에서 구현 완료 기준으로 갱신했습니다.
  - 샘플 이벤트 버튼을 통해 SystemMetrics, SessionStatus, DetectionFeed, RiskEventLog, AI Pipeline Monitor 전 패널을 데모 화면에서 채울 수 있는 상태임을 문서화했습니다.
  - 1차 MVP는 화면 구성과 샘플 시연까지 마감하고, 실제 백엔드 SSE 이벤트명 및 payload 필드 정합은 후속 검증 단계로 분리했습니다.
  - TH 하드코딩 80% 원칙에 따라 `useMonitorStream.ts`의 이벤트 분기와 상태 설계는 직접 설명 가능 핵심 영역으로 유지한다는 기준을 명시했습니다.
  - `server/api/monitor.py`, `server/mcp/manager.py`, `server/api/ws_router.py`, `server/detection/consumer.py` 기준으로 실제 확인된 SSE 이벤트와 데모/확장 이벤트를 분리해 `console/README.md`에 정리했습니다.
- **관련 파일**: `console/README.md`, `docs/changelogs/th.md`
- **검증 결과**:
  - 기존 `cd console && npm run build` 통과 상태 유지
  - 문서 정리 작업으로 추가 빌드는 생략

---

### 2026-07-10 | 문서 | th 최신 반영 후 문서 인덱스 누락 항목 정합화

- **변경 내용**:
  - `origin/th` 최신 fast-forward 반영 후 `docs/README.md`를 재점검했습니다.
  - 이번에 추가된 Android 무선 테스트 문서 2건과 STT 통합 가이드 1건이 인덱스에 빠져 있어 링크를 보강했습니다.
  - 문서 본문 내용은 유지하고 인덱스·버전 표기만 현재 저장소 상태에 맞게 정리했습니다.
- **관련 파일**: `docs/README.md`, `docs/changelogs/th.md`
- **검증 결과**:
  - `docs/README.md` 내 신규 문서 링크 경로 존재 여부 확인 완료

---

### 2026-07-11 | 운영자 콘솔 | dev 사전 병합 정합성 보완

- **변경 내용**:
  - 로그인 응답과 앱 상태에서 JWT를 출력하던 디버그 로그를 제거했습니다.
  - SSE effect가 로그인 token 변경에 반응하도록 의존성을 보완하고 query parameter를 안전하게 인코딩했습니다.
  - 비밀번호 원문을 보존하고 관리자 사번에만 `trim()`을 적용했습니다.
  - 샘플 이벤트와 탐지 안내 mock 이력은 개발 환경의 `VITE_ENABLE_DEMO_DATA=true`에서만 활성화하도록 격리했습니다.
  - 최신 dev를 통합하면서 `docs/README.md`의 Mitos 기준선과 th 문서 인덱스를 모두 보존했습니다.
- **관련 파일**: `console/src/App.tsx`, `console/src/api/useMonitorStream.ts`, `console/src/components/Login.tsx`, `console/.env.example`, `console/README.md`, `docs/README.md`
- **검증 기준**: `npm run build`, 관리자 로그인 테스트, `git diff --check`

---

### 2026-07-11 | 문서 | dev 8b2f606 개선 실행 계획서 작성

- **변경 내용**:
  - 팀 제공 감사 결과를 바탕으로 P0 안전성, 인지 경로·RAG 정합성, 품질 게이트, 운영·문서 개선 순서를 정리했습니다.
  - 각 항목에 담당 영역, 검증 방법, 완료 기준을 명시했습니다.
  - 코드·환경변수·설정 파일은 수정하지 않았습니다.
- **관련 파일**: `docs/ops/dev_8b2f606_improvement_plan.md`, `docs/README.md`, `docs/changelogs/th.md`
- **검증 기준**: 문서 링크 경로 존재 여부 확인

---

### 2026-07-12 | 5단계 | RAG retriever 라벨 SSOT 임포트 크래시 수정

- **커밋**: `미커밋`
- **변경 내용**:
  - `server/rag/retriever.py`가 `shared/labels.py`에 존재하지 않는 구 라벨 심볼을 임포트하던 문제를 현재 SSOT 라벨인 `SCOOTER` 기준으로 정정했습니다.
  - retriever 스모크 테스트 블록의 더미 문서 메타데이터와 `detect_info["class_name"]`도 `SCOOTER` 기준으로 맞췄습니다.
  - `tests/test_retriever.py`의 수집 단계 ImportError를 해소하도록 동일 라벨을 정정했습니다.
  - 사용자 발화 문구는 내부 라벨과 분리하여 "전동킥보드 또는 스쿠터"로 표현하도록 `fallback.py`, retriever 스모크 데이터, RAG 원본 JSON을 보강했습니다.
  - 같은 구 라벨 import가 남아 있던 fallback/E2E 테스트와 mock 임베딩·DB 빌더 문구도 `SCOOTER` 기준으로 정리했습니다.
  - `braille_damaged`, `stairs`로 남아 있던 RAG 원본 메타데이터를 현재 SSOT 노면 위험 라벨인 `caution`으로 정리했습니다.
  - LangGraph 오케스트레이션 테스트 입력에 남아 있던 구 장애물 라벨을 `scooter`로 정리하고, 사용자 문구는 전동킥보드 기준으로 유지했습니다.
- **관련 파일**: `server/rag/retriever.py`, `server/rag/fallback.py`, `server/rag/embedding_engine_factory.py`, `server/rag/build/db_builder.py`, `tests/test_retriever.py`, `tests/test_fallback.py`, `tests/test_e2e_pipeline.py`, `tests/test_langgraph.py`, `data/safety_guidelines.json`, `docs/changelogs/th.md`
- **검증 결과**: `.\venv\Scripts\python.exe -c "import server.rag.retriever"`, `.\venv\Scripts\python.exe -m py_compile server/rag/retriever.py`, `.\venv\Scripts\python.exe -m server.rag.retriever`, `.\venv\Scripts\python.exe -m pytest tests/test_retriever.py tests/test_fallback.py tests/test_e2e_pipeline.py -v`, `.\venv\Scripts\python.exe -m pytest tests/test_langgraph.py -v` 통과

---

### 2026-07-10 | 운영자 콘솔 | DetectionFeed 및 로그 테이블 UI 정리

- **커밋**: `feat(console): refine monitoring tables and detection feed`
- **변경 내용**:
  - `console/src/components/DetectionFeed.tsx`에서 `event_id` 제목 노출, `stream` 중복 출력, `confidence`/`inference_ms` 조건식 오류, placeholder 중복 노출 문제를 정리했습니다.
  - `console/src/types/monitor.ts`에 `DetectionGuidanceLogRow` 타입을 추가하고 `detection_guidance_logs` 테이블/응답 컬럼 구조와 맞추도록 최소 타입을 고정했습니다.
  - `console/src/components/DetectionGuidanceLogTable.tsx`를 신규 추가해 실시간 feed와 분리된 history/log table 골격을 구성했습니다.
  - `console/src/components/RiskEventLog.tsx`를 placeholder에서 실제 위험 로그 table 렌더 구조로 전환했습니다.
  - `console/src/App.tsx`에 mock `DetectionGuidanceLogRow[]`를 연결하고, DetectionFeed와 DB 로그 영역이 서로 다른 역할임을 설명하는 발표/면접 대응 주석을 보강했습니다.
- **관련 파일**: `console/src/App.tsx`, `console/src/types/monitor.ts`, `console/src/components/DetectionFeed.tsx`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/components/RiskEventLog.tsx`
- **검증 결과**:
  - `cd console && npm run build` 통과

---

### 2026-07-10 | 운영자 콘솔/로컬 실행 | 로그인 응답 처리 및 CORS/Redis 정리

- **커밋**: `fix(console): handle login response and local CORS`
- **변경 내용**:
  - `console/src/components/Login.tsx`에 `trim()` 적용, `detail` 우선 에러 표시, `access_token` 존재 검사, 하드코딩 구간 주석을 추가해 로그인 실패 원인을 프론트에서 더 분명히 확인할 수 있게 했습니다.
  - `server/api/config.py`의 `CORS_ORIGINS` 기본값에 `http://localhost:5174`를 추가해 Vite 개발 서버에서 관리자 로그인 요청이 CORS로 차단되던 문제를 정리했습니다.
  - `console/src/App.tsx`에서 `OperatorLiveMap`을 임시 비활성화해 `localhost:8001` 지도 서버 미실행 상태에서 iframe `load fail`이 대시보드 진입을 방해하지 않도록 처리했습니다.
  - macOS 로컬 환경에 `redis`를 설치하고 `brew services start redis`로 `6379` 리스닝 상태를 확인했습니다.
- **관련 파일**: `console/src/components/Login.tsx`, `console/src/App.tsx`, `server/api/config.py`, `docs/changelogs/th.md`
- **검증 결과**:
  - `POST /api/v1/admin/login` 200 OK 응답 확인
  - `brew install redis` 완료
  - `brew services start redis` 후 `lsof -i :6379` 리스닝 확인

---

### 2026-07-12 | Android 빌드 환경 | Windows 긴 경로 + JDK 17 + SDK 설치 및 빌드 안정화

- **커밋**: `build(android): Windows 긴 경로 환경에서 네이티브 빌드 안정화` (이미 origin/th에 반영됨, 커밋 `85e9503`)
- **변경 내용**:
  - Android SDK/Studio/JDK 17 전체 신규 설치 (winget + sdkmanager) — `C:\Users\rhxoc\AppData\Local\Android\Sdk`, build-tools 35.0.0, platform-tools, NDK 27.1.12297006
  - `client/android/local.properties`에 `sdk.dir` 지정 (머신별, gitignore)
  - `client/android/gradle.properties`에 `org.gradle.java.home=C:/Program Files/Java/jdk-17` 고정
  - `client/android/build.gradle`에 `subprojects afterEvaluate` 훅 추가 — CMake 사용 모듈의 `buildStagingDirectory`를 `C:/AndroidCxx/{모듈경로}`로 분리
- **오류와 해결**:
  - `expo-audio plugin resolve 실패` → `client`에서 `npm install` 누락, 의존성 설치로 해결
  - `JAVA_HOME이 .exe 파일 경로로 잘못 지정` → `gradle.properties`에 `org.gradle.java.home` 고정으로 세션 환경변수 의존도 제거
  - `CMake Warning: object file directory has 193 chars, max 250` + `ninja: error: manifest 'build.ninja' still dirty after 100 tries` → 깊은 프로젝트 경로(`D:\home_coding_task\...`)가 Windows 250자 한도 초과, `buildStagingDirectory` 우회로 네이티브 캐시만 `C:/AndroidCxx`로 분리
  - `subst M:\client` 우회 시도 → `react-native-vision-camera generateCodegenSchemaFromJavaScript`에서 `M:`와 `D:` 루트 충돌로 실패, subst 방식 폐기
  - `No Android connected device found` → USB 디버깅 승인 팝업 대기/케이블 재연결로 해결
- **관련 파일**: `client/android/build.gradle`, `client/android/gradle.properties`, `client/android/local.properties`, `docs/changelogs/th.md`
- **검증 결과**:
  - `.\gradlew.bat -v` Gradle 9.3.1 정상 기동
  - `adb version` 1.0.41 정상
  - `expo run:android`가 디바이스 미연결 오류 전까지 Gradle 설정 단계 통과

---

### 2026-07-12 | Android 실기기 | 내부 서버 및 LAN Metro 연결 전환

- **커밋**: `이번 커밋에 포함`
- **변경 내용**:
  - Android 실기기 로그에서 카메라 reflex 프레임 생성과 STT 녹음은 정상이나, `wss://partake-primer-surround.ngrok-free.dev/ws/detect` WebSocket 연결이 반복 실패하는 것을 확인했습니다.
  - 로컬 모델 파일 `client/assets/models/yolo26n/object_detection.tflite`, `client/assets/models/yolo26n/segmentation.tflite`, `server/models/yolo26n/object_detection.pt` 존재를 확인해 1차 원인은 모델 파일 부재가 아니라 네트워크 연결 실패로 분리했습니다.
  - 내부 FastAPI 서버를 프로젝트 `venv`로 기동해 `0.0.0.0:8000` Listen 상태를 확인했습니다.
  - React Native Metro 프론트를 LAN 모드로 기동해 `8081` Listen 상태를 확인했습니다.
  - 현재 노트북 Wi-Fi IP가 `192.168.1.103`으로 확인되어 `client/src/config/index.ts`를 `NETWORK_MODE="lan"`, `LAN_IP="192.168.1.103"` 기준으로 전환했습니다.
  - Android 실기기에서 카메라 권한을 허용하고 앱을 재설치한 뒤 `Camera 0 ... ACTIVE`, `PreviewView Stream State changed to STREAMING`, `Camera/Real-Android reflex 프레임 완료`, `TFLiteDetector 듀얼 TFLite 모델 로드 성공` 로그를 확인했습니다.
  - 경로가 없는 상태에서도 지도 placeholder가 표시되어 카메라 확인을 방해할 수 있어, `nav_route` 수신 전에는 지도 패널과 토글을 숨기고 경로 해제 시 자동으로 닫히도록 수정했습니다.
- **오류 및 후속 수정 필요**:
  - 시스템 Python 3.14에는 `uvicorn`이 없어 서버 기동이 실패했습니다. 프로젝트 서버 실행은 반드시 `venv\Scripts\python.exe -m uvicorn server.main:app --host 0.0.0.0 --port 8000` 기준으로 수행해야 합니다.
  - 서버 로그에서 Redis `localhost:6379` 연결 거부가 반복됩니다. Redis 또는 Docker Redis 컨테이너를 기동해야 Streams/MCP 경로가 정상화됩니다.
  - 서버 로그에서 Whisper small 프리로드가 실패해 STT는 지연 로딩으로 폴백 중입니다. 네비게이션 음성 명령 종단 테스트 전 faster-whisper 모델 로딩 환경을 재검증해야 합니다.
  - 서버 segmentation 기본 경로(`YOLO26N_SEG=server/models/yolo26n/segbest.pt`)와 실제 파일 존재 여부는 추가 확인이 필요합니다.
  - 폰에서 `http://192.168.1.103:8000/health` 접근은 성공했으나 `http://192.168.1.103:8081/status`는 타임아웃이 발생했습니다. Metro LAN 포트는 방화벽 또는 Expo dev server 바인딩 문제로 별도 조치가 필요하며, 임시로 `adb reverse tcp:8081 tcp:8081`을 적용했습니다.
  - 다음 단계는 WebSocket 실기기 재접속 확인 후 `TMAP_APP_KEY`, `realtime_gps`, `nav_route` 기반 네비게이션 경로 안내를 검증하는 것입니다.
- **관련 파일**: `client/src/config/index.ts`, `client/src/components/CameraView.tsx`, `docs/changelogs/th.md`, `server_start_th.log`
- **검증 결과**:
  - `Get-NetTCPConnection -LocalPort 8000,8081` 기준 `8000` FastAPI, `8081` Metro Listen 확인
  - `server.main` import 정상 확인

---

### 2026-07-12 | Android 실기기 | 탐지 및 지도 미표시 원인 분리

- **커밋**: `fix(stt): CPU Whisper compute_type 폴백 및 연락처 음성 명령 저장소 추가`
- **변경 내용**:
  - 연결 이후 앱 프레임은 서버 `/ws/detect`로 정상 수신되고 있음을 확인했습니다. 서버 로그 기준 `FrameDecoder`가 640x640 프레임을 2~6ms 내외로 디코딩하고 있습니다.
  - 탐지가 안 보이던 1차 원인은 `.env`의 `DETECTOR_TYPE=mock` 설정이었습니다. 실제 서버 탐지를 위해 `DETECTOR_TYPE=yolo`로 전환했습니다. (`.env`는 gitignore라 커밋 제외)
  - `.env`의 `YOLO26N_OBJECT_DET`가 존재하지 않는 `server/models/yolo26n/det_best_20260705.pt`를 가리켜, 실제 존재하는 `server/models/yolo26n/object_detection.pt`로 정정했습니다.
  - 서버 재시작 후 `YoloDetector` 로드 성공과 `stroller`, `bicycle` 등 실제 탐지 클래스가 LLM/RAG 경로로 들어가는 것을 확인했습니다.
  - `YOLO26N_SEG=server/models/yolo26n/segbest.pt`는 실파일이 없어 `MockSegmentor`로 폴백 중입니다. segmentation 결과가 필요한 지도/노면 계층 검증 전 가중치 파일 보강이 필요합니다.
  - 지도는 단순히 `지도 켜기`를 누르면 바로 TMap을 여는 구조가 아니라, STT 목적지 설정 성공 후 서버가 `nav_route`와 `TMAP_APP_KEY`를 앱으로 보내야 표시됩니다.
  - `stt_audio`는 서버에 수신되지만 Whisper small 초기화가 실패해 목적지 설정과 `nav_route` 생성이 막히는 것을 확인했습니다. CPU 환경에서 `int8` 실패 시 `int8_float32`, `float32`로 재시도하도록 `SttService.get_model()`을 보강했습니다.
  - `server/stt/contact_store.py`를 신규 추가해 음성 명령 기반 연락처 저장/조회 데모용 메모리 저장소를 분리했습니다. (세션 범위 dict, DB 영속화는 후속)
- **오류 및 후속 수정 필요**:
  - 현재 venv가 Python 3.14 계열로 동작하고 있어 faster-whisper/ctranslate2 호환성 문제가 남아 있을 수 있습니다. STT 네비게이션 검증은 Python 3.13 호환 venv 재구성 또는 faster-whisper 런타임 재설치가 필요합니다.
  - Redis `localhost:6379` 연결 실패가 반복되어 Redis Streams 기반 부가 경로는 아직 정상화되지 않았습니다.
  - Ollama `nomic-embed-text`가 없어 RAG 검색이 fallback으로 동작합니다. `ollama pull nomic-embed-text`가 필요합니다.
- **관련 파일**: `server/stt/stt_service.py`, `server/stt/contact_store.py`, `docs/changelogs/th.md`
- **검증 결과**:
  - 서버 재시작 후 `YoloDetector 로드 성공: server/models/yolo26n/object_detection.pt` 확인
  - 서버 로그에서 `/ws/detect` 연결, `detection 수신`, 실제 클래스 기반 LLM 호출 확인
  - Android 실기기 카메라 ACTIVE + TFLite 듀얼 모델 로드 성공 로그 확인

---

### 2026-07-12 | Android 클라이언트 | VisionCamera Frame Processor 등록 및 TFLite NMS 출력 정합

- **커밋**: `이번 커밋에 포함`
- **변경 내용**:
  - `client/android/app/src/main/java/com/minchodan/app/ReflexFrameProcessorPlugin.kt` 신규 추가 — VisionCamera Frame Processor 플러그인 `reflexFrameCapture` 구현체
  - `client/android/app/src/main/java/com/minchodan/app/MinchodanCustomPackage.kt` 신규 추가 — 커스텀 네이티브 모듈 패키지 래퍼
  - `client/android/app/src/main/java/com/minchodan/app/AudioSessionBridgeModule.kt` 신규 추가 — STT 녹음 구간 AEC용 AudioSession 브릿지(Android 측 대응)
  - `client/android/app/src/main/java/com/minchodan/app/MainApplication.kt` — `MinchodanCustomPackage` 등록 및 `FrameProcessorPluginRegistry.addFrameProcessorPlugin("reflexFrameCapture")` 호출 추가
  - `client/src/inference/tfliteDetector.ts` — YOLO 26N 출력 포맷 33(NMS-free 4+29)에서 6(NMS-enabled 4+score+classId)로 정정. 커스텀 학습 가중치가 NMS를 포함한 형태로 export되었기 때문에 출력 채널 수를 맞춤
  - `client/src/components/CameraView.tsx` — `navRoute`가 없을 때 지도 패널과 토글 버튼을 렌더링하지 않도록 가드 추가
- **오류와 해결**:
  - `Frame Processor Plugin "reflexFrameCapture" not registered` → `MainApplication.onCreate`에 `FrameProcessorPluginRegistry.addFrameProcessorPlugin` 등록으로 해결
  - TFLite 탐지 결과가 전부 0점/빈 배열로 떨어짐 → 모델 출력 채널 수(33 vs 6) 불일치, NMS-enabled export 형태에 맞춰 6으로 정정
- **관련 파일**: `client/android/app/src/main/java/com/minchodan/app/ReflexFrameProcessorPlugin.kt`, `client/android/app/src/main/java/com/minchodan/app/MinchodanCustomPackage.kt`, `client/android/app/src/main/java/com/minchodan/app/AudioSessionBridgeModule.kt`, `client/android/app/src/main/java/com/minchodan/app/MainApplication.kt`, `client/src/inference/tfliteDetector.ts`, `client/src/components/CameraView.tsx`
- **검증 결과**:
  - `npx tsc --noEmit` 통과
  - Android 빌드 Gradle 설정 단계 통과 (디바이스 미연결로 설치 단계는 대기 중)

---

### 2026-07-12 | 동기화 | kb 브랜치 통합

- **커밋**: `이번 커밋에 포함 (merge commit)`
- **변경 내용**:
  - `origin/kb` 최신 9개 커밋을 `th`에 병합 — 파이프라인 레이턴시 계측, 실시간 브로드캐스트 확장, 관리자 회원 등록 페이지, 오탐 판정(false_positive) 컬럼 추가, iOS 카메라 180도 방향 반전 수정, 이벤트 프레임 보존(frame_path), LiDAR 실거리 프로브 프로토타입, SSE 이벤트 계약 고정 및 인증 기본값 환경 분리(fail-closed), 콘솔 지도 연동 복구 등
- **관련 파일**: `docs/changelogs/th.md` (이력 기록)
- **검증 결과**:
  - `git merge origin/kb` 충돌 없이 병합 완료
