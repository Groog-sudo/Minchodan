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

### 2026-07-12 | Android 실기기 | Redis 및 STT 런타임 복구

- **커밋**: `이번 커밋에 포함`
- **변경 내용**:
  - Docker Desktop을 기동하고 `docker compose -f docker/docker-compose.yml up -d redis`로 `minchodan-redis` 컨테이너를 복구했습니다.
  - FastAPI 서버를 재시작해 `/ws/detect` 재접속, `auth_ok`, `realtime_gps`, 프레임 수신을 다시 확인했습니다.
  - 서버 로그 기준 `RedisBus 연결 성공`과 Android 실기기 프레임 디코딩, YOLO 추론, LLM guide 전송을 확인했습니다.
  - `server/stt/stt_config.py`의 `MODEL_NAME_MAP`에 `small`, `medium` 내부 별칭을 추가해 WebSocket 경로에서 `model=small`이 전달되어도 STT 서비스가 처리하도록 보강했습니다.
  - 현재 `venv`에 누락되어 있던 `faster-whisper==1.2.1`을 설치했고, `SttService.get_model("small")` 단독 로딩이 `ok`로 통과하는 것을 확인했습니다.
- **오류 및 후속 수정 필요**:
  - RAG 임베딩 모델 `nomic-embed-text`가 Ollama에 없어 `/api/embed`가 404를 반환합니다. `ollama pull nomic-embed-text`가 필요합니다.
  - TTS 경로에서 `No module named 'piper'`가 발생합니다. 현재 서버는 guide 텍스트 전송은 수행하지만 Piper 음성 합성은 실패합니다.
  - DB 자동 등록 및 탐지 로그 저장에서 `root@localhost` 인증 실패가 발생합니다. `.env`의 DB 계정 또는 로컬 MariaDB 상태 정합화가 필요합니다.
  - `StreamSplitter` 일부 Redis 발행 경로는 서버 재기동 직후에도 `연결 끊김` 경고가 남아 있습니다. `redis_bus` 재연결 처리와 splitter 싱글턴 상태를 추가 점검해야 합니다.
- **관련 파일**: `server/stt/stt_config.py`, `docs/changelogs/th.md`
- **검증 결과**:
  - `docker compose -f docker/docker-compose.yml ps redis` 기준 `minchodan-redis` Up 확인
  - `.\venv\Scripts\python.exe -c "from server.stt.stt_service import SttService; SttService.get_model('small'); print('ok')"` 통과
  - `/health` 응답에서 `detector_type="yolo"` 및 최근 detection consumer 상태 확인
  - 서버 로그에서 `탐지 객체: [pole, stroller] -> LLM 응답`, `guide 전송` 확인

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

---

### 2026-07-12 | STT 브리지+클라이언트 | 음성 편의기능 3종 추가 (긴급전화/연락처 저장·전화걸기/문자 읽어주기)

- **커밋**: `feat(stt,client): 음성 편의기능 3종(긴급전화/연락처/SMS읽어주기) 및 dial_action`
- **선행 커밋**: `9f194da`에 `server/stt/contact_store.py`(ContactStore)와 Whisper CPU
  compute_type 폴백이 먼저 들어감. 본 커밋은 브리지 인텐트·WS·단말·문서·테스트를 연결
- **변경 내용**:
  - `server/stt/contact_store.py` - (선행) 음성 연락처 저장/조회. 정규식으로
    전화번호를 추출하고 조사/어미를 트리밍해 이름 후보를 정리하는 휴리스틱
    (`ContactStore`는 device_id별 프로세스 메모리 저장소, **TH HARDCODE**: 별도
    Contact 테이블이 없어 서버 재시작 시 소실되는 데모 시연 범위 한계)
  - `server/stt/stt_to_llm_bridge.py` - 3개 신규 인텐트 추가
    - 긴급전화(`_is_emergency_call_trigger` + `_handle_emergency_call`): "긴급전화"/
      "SOS"/"보호자한테 전화해줘" 등 인식 시 `AppUser.guardian_phone`(실제 DB 컬럼,
      `device_registry_service.get_cached_device_ids` -> `UserRepository.get_by_id`
      경로로 조회)로 다이얼. 다른 모든 대화 상태(목적지 대기/질문 대기 등)보다
      최우선 처리. 미등록 시 고정 폴백 번호(`119`, **TH HARDCODE**)로 연결
    - 연락처 저장(`"<이름> 번호 <전화번호> 저장해줘"`): `ContactStore.save` 호출
    - 이름으로 전화걸기(`"<이름>한테 전화 걸어줘"`): `ContactStore.lookup` 후
      `dial_action` 결과 필드 반환
  - `server/api/ws_router.py` - `bridge_result["dial_action"]`을 감지해 신규 WS
    메시지 타입 `dial_action`(`contact_name`, `phone_number`)으로 전송하는 분기 추가
  - `client/src/types/detection.ts` - `MessageType`에 `"dial_action"` 추가, `WSMessage`에
    `contact_name`/`phone_number` 필드 추가
  - `client/src/hooks/useWebSocket.ts` - `dial_action` 수신 시 `Linking.openURL("tel:" +
    phone_number)`로 실제 다이얼 실행
  - `client/android/app/src/main/java/com/minchodan/app/SmsReaderModule.kt` 신규
    추가 - 문자 메시지 읽어주기(Android 전용) 네이티브 브릿지. `SMS_RECEIVED`
    브로드캐스트를 동적 등록(정적 매니페스트 리시버 대신 JS 생명주기에 맞춰
    `startListening`/`stopListening`)으로 수신해 `onSmsReceived` 이벤트로 전달
  - `client/android/.../MinchodanCustomPackage.kt` - `SmsReaderModule` 등록
  - `client/android/app/src/main/AndroidManifest.xml` - `RECEIVE_SMS` 권한 추가
    (**TH HARDCODE 아님 - 플랫폼 제약 메모**: Google Play 정책상 "기본 문자 앱"이
    아니면 상시 허용되지 않는 민감 권한이라 데모/사이드로드 범위로 한정)
  - `client/src/hooks/useSmsReader.ts` 신규 추가 - Android 권한 요청 +
    `onSmsReceived` 구독 + 기존 `audioEngine.speakFallback`(expo-speech 기반)으로
    발신자/본문 읽어주기. iOS는 공개 SMS 콘텐츠 API가 없어 미지원(플랫폼 제약)
  - `client/src/components/CameraView.tsx` - `useSmsReader()` 훅 마운트
  - `docs/design/api_specification.md` §6.3 명령어 표에 긴급전화/연락처 저장/전화걸기
    행 추가, §6.7 `dial_action` 계약 신설
  - `server/stt/stt_config.py` - MODEL_NAME_MAP에 `"small"`/`"medium"` 별칭 추가
    (WS 경로에서 faster-whisper 접두사 없이 내부 별칭이 전달되는 경우 허용)
  - `scripts/dev_redis_stub.py` 신규 - 로컬에서 Redis 미기동 시 Streams 의존을
    완화하기 위한 최소 RESP 스텁(인식 리포트 I-2 대응용 개발 보조)
  - `tests/test_stt_convenience_features.py` 신규 추가 - 기존
    `test_stt_to_llm_bridge_template.py`와 동일한 픽스처 패턴(`_make_stt_result`,
    `_FakeNavManager`, `monkeypatch`)으로 연락처 저장/전화걸기, 긴급전화
    guardian_phone 성공/미등록 폴백, 긴급전화가 nav 대기 상태를 무시하고
    최우선 처리되는지까지 6개 케이스 검증
- **하드코딩/데모 한계 (TH HARDCODE, 발표 시 설명 필요)**:
  - 일반 연락처 저장은 DB가 아닌 프로세스 메모리(`ContactStore`) - 서버 재시작 시 소실
  - 이름/전화번호 추출은 형태소 분석기 없이 정규식+문자열 트리밍 휴리스틱
  - 긴급전화 미등록 시 폴백 번호(`119`)는 고정값, 지역/상황별 라우팅 없음
  - 문자 읽어주기는 앱이 열려 있는 동안(포그라운드)만 동작 - 백그라운드/종료 상태 미지원
- **미검증 항목**:
  - 문자 읽어주기(`SmsReaderModule`)는 실제 SMS 수신 테스트가 아직 완료되지
    않았다. Android 에뮬레이터 Extended Controls > Phone > SMS(또는 `adb emu
    sms send`)로 실기기 SIM 없이도 검증 가능 - 테스트 후 이 항목을 갱신할 것
  - 긴급전화/연락처 저장/전화걸기 음성 명령의 실기기 종단 테스트(STT 인식률 포함)
    미완료 - 아래 pytest는 텍스트 인텐트 분기 로직만 검증하며 실제 Whisper 인식은
    거치지 않는다
- **관련 파일**: `server/stt/contact_store.py`, `server/stt/stt_to_llm_bridge.py`,
  `server/stt/stt_config.py`, `server/api/ws_router.py`,
  `client/src/types/detection.ts`, `client/src/hooks/useWebSocket.ts`,
  `client/src/hooks/useSmsReader.ts`, `client/src/components/CameraView.tsx`,
  `client/android/app/src/main/java/com/minchodan/app/SmsReaderModule.kt`,
  `client/android/app/src/main/java/com/minchodan/app/MinchodanCustomPackage.kt`,
  `client/android/app/src/main/AndroidManifest.xml`,
  `docs/design/api_specification.md`, `scripts/dev_redis_stub.py`,
  `tests/test_stt_convenience_features.py`, `docs/changelogs/th.md`
- **검증 결과**:
  - `python -m pytest tests/test_stt_convenience_features.py -v` 6개 전부 통과
    (연락처 저장/전화걸기 성공·실패, 긴급전화 guardian_phone 성공/119 폴백,
    긴급전화의 nav 상태 우선순위 무시까지 커버)
  - `python -m pytest tests/test_stt_to_llm_bridge_template.py tests/test_ws_router_stt.py`
    13개 전부 통과(기존 STT 브리지/WS 라우터 회귀 없음 확인)
  - `python -m py_compile` 통과, `npx tsc --noEmit` 통과
  - 실기기/에뮬레이터 통합 테스트(STT 음성 인식, SMS 실수신, tel: 다이얼러 실행)는
    미수행 - 위 미검증 항목 참조

---

### 2026-07-12 | 문서 | Android STT/실내 탐지 인식 문제 종합 리포트

- **커밋**: `docs: Android STT 및 실내 탐지 인식 저하 종합 리포트`
- **변경 내용**:
  - `docs/ops/android_stt_recognition_issue_report.md` v1.2.0 작성/갱신
  - STT 인식 실패뿐 아니라 **실내 장애물 탐지 체감 저하**를 명시
  - 원인을 인프라(I) / STT(S) / 비전·실내탐지(D) / UX(U) 4축으로 종합 분석
  - P0~중기 개선 방향(Python 3.13 venv, seg 가중치, VAD, 실내 데이터·conf, UX 구분) 정리
  - `docs/README.md` 문서 인덱스에 리포트 링크 추가
- **관련 파일**: `docs/ops/android_stt_recognition_issue_report.md`, `docs/README.md`, `docs/changelogs/th.md`

---

### 2026-07-13 | 부가(STT) | 연락처 저장 트리거 - 한글 숫자 전사 폴백 추가

- **커밋**: (본 세션 통합 커밋에 포함)
- **배경(실기기 실측)**: 음성 편의기능 3종(2026-07-12, `311eb4a`) 배포 후 실기기로
  "번호 저장해줘" 편의기능을 테스트했으나, STT 인식 자체는 정상인데도 연락처 저장이
  되지 않고 일반 대화 경로로 새서 LLM이 "직접 저장하세요" 류의 엉뚱한 문장을
  생성하는 현상을 확인했다.
- **원인 분석**:
  - `contact_store.py`의 `PHONE_NUMBER_PATTERN`(`01[0-9][-\s]?\d{3,4}[-\s]?\d{4}`)은
    아라비아 숫자 전사만 전제한다.
  - Whisper가 전화번호를 "공일공일이삼사오육칠팔"처럼 한글 숫자로 전사하면 정규식이
    매칭에 실패해 `extract_save_command`가 `None`을 반환한다.
  - `is_contact_save_trigger`가 꺼지므로 발화가 저장 분기를 타지 못하고
    `stt_to_llm_bridge.py`의 일반 `run_orchestrator` 경로(장애물 회피용 L1/L2/L3)로
    흘러가, 맥락에 안 맞는 LLM 생성 문장이 반환된 것이었다(RAG 미스는 아니었음 -
    애초에 RAG를 거치지도 않는 경로).
- **변경 내용**:
  - `server/stt/contact_store.py`에 `_KOREAN_DIGIT_MAP`/`_find_korean_spoken_phone`
    추가. 한글 숫자 문자가 9~12자 연속으로 이어진 구간만 후보로 보고, 변환 후
    11자리 + "01" 시작 조건까지 만족해야 전화번호로 인정한다(오탐 방지).
  - `extract_save_command`가 아라비아 숫자 매칭 실패 시 위 폴백을 시도하도록 분기
    추가.
  - `tests/test_stt_convenience_features.py`에
    `test_contact_save_accepts_korean_spoken_digits` 회귀 테스트 추가.
- **하드코딩 설계 판단 (TH HARDCODE, 발표 시 설명 필요)**:
  - 정규식 자체를 한글 숫자까지 매칭하도록 합치지 않고 별도 폴백 함수로 분리했다.
    이유: "일/이/오" 같은 한글 숫자 문자는 그 자체로 흔한 한국어 단어/조사이기도 해서
    (예: "일하다", "오늘"), 짧은 매칭을 허용하면 일반 문장에서 오탐 저장이 발생할
    위험이 있다. 최소 길이(9자 이상 연속)와 변환 후 자릿수 검증(11자리, "01" 시작)
    2중 조건으로 위험을 낮췄다.
  - 형태소 분석기/LLM 개체명 추출을 쓰지 않고 규칙 기반을 유지한 이유는 기존
    `extract_save_command` 주석(LLM 환각으로 엉뚱한 번호가 저장될 위험) 참조.
  - **면접 대비 포인트**: "왜 이 버그를 RAG가 아니라 STT 브리지 쪽에서 고쳤나"라는
    질문에는 "STT 일반 편의기능 인텐트(연락처 저장 등)는 애초에 RAG/LLM을 거치지
    않는 규칙 기반 분기이고, 실패 시에만 장애물 회피용 오케스트레이터로 새는
    구조였다 - 증상은 '이상한 LLM 답변'으로 보였지만 원인은 RAG가 아니라 정규식이
    한글 숫자 전사를 못 받아준 것"이라고 설명하면 된다.
- **미검증 항목**: 10자리(지역번호/구내전화 등 010 외 형식) 한글 숫자 전사는 폴백
  대상에서 제외했다 - 실사용 빈도가 낮다고 판단해 스코프에서 뺐다(필요 시 재검토).
- **관련 파일**: `server/stt/contact_store.py`, `tests/test_stt_convenience_features.py`,
  `docs/changelogs/th.md`
- **검증 결과**: `python -m py_compile server/stt/contact_store.py` 통과,
  `python -m pytest tests/test_stt_convenience_features.py -v` 7개 전부 통과
  (신규 회귀 테스트 `test_contact_save_accepts_korean_spoken_digits` 포함)
- **검증 결과**: 문서 교차 링크 및 섹션 구조 점검 완료

---

### 2026-07-13 | 운영(단말) | WiFi/USB 이중 접속 문서화 및 앱 토글

- **커밋**: (본 세션 통합 커밋에 포함)
- **배경**: 공기계 테스트 시 USB(`adb reverse` + `127.0.0.1`)와 노트북 모바일 핫스팟
  (`192.168.137.1`)을 번갈아 쓰게 되어, 설정을 매번 고쳐 빌드하는 방식이 비효율적이었다.
  또한 PC가 아이폰 핫스팟을 받는 IP(`172.20.10.2`)와 공기계가 붙는 핫스팟 게이트웨이
  (`192.168.137.1`)를 혼동하기 쉬워 문서화가 필요했다.
- **변경 내용**:
  - 앱: `연결: WiFi` / `연결: USB` 토글 (`CameraView`), 선택값 단말 영속
    (`serverTransport.ts`), `buildWsUrl` / `WIFI_HOST` / `USB_HOST` (`config/index.ts`)
  - 문서: `docs/ops/android_wifi_usb_transport.md` 신설
  - 교차 반영: `docs/README.md`, `environment_variables.md` §2.14,
    `ios_android_bifurcation_contract.md` §7.3, `android_build_and_wireless_test_guide.md` §3
- **관련 파일**: 위 문서·클라이언트 경로
- **사용 요약**: 평상시 WiFi(선 없음) / 기능 수정 시 USB + `adb reverse tcp:8000|8081`

---

### 2026-07-13 | 부가(STT)+단말 | 연락처 단말 영속화·탐지 토글·오디오 UX·질문 라우팅·Edge TTS

- **커밋**: `feat(th): 연락처 영속화, 탐지/질문 라우팅, 긴급핑퐁, Edge TTS`
- **작업 범위 요약**: 2026-07-13 th 실기기 세션에서 보고된 UX/음성/STT 이슈를
  일괄 반영. (WiFi/USB·한글숫자 연락처는 위 항목과 동일 세션)

#### 1) 연락처: 서버 RAM만이 아니라 폰 주소록에 저장

- **문제**: 음성으로 번호 저장해도 폰 연락처 앱에 안 보임(서버 `ContactStore` RAM만).
- **변경**:
  - Android `ContactsBridgeModule.kt` + `contactsBridge.ts` (READ/WRITE_CONTACTS)
  - WS `contact_save` → 단말 `ContactsContract` INSERT
  - 전화 걸기: RAM 미스 시 `device_lookup`으로 단말 주소록 재조회
- **관련 파일**: `ContactsBridgeModule.kt`, `contactsBridge.ts`, `ws_router.py`,
  `stt_to_llm_bridge.py`, `CameraView`/`useWebSocket` 연동, `AndroidManifest.xml`

#### 2) 탐지 기본 OFF + 「탐지 시작/중지」

- **의도**: 상시 캡처/전송 과부하 완화. STT press-and-hold와 독립.
- **UX**: 탐지 OFF면 카메라 `isActive`도 OFF → 검은 화면(의도된 동작, 사용자 확인).
- **관련 파일**: `CameraView.tsx`

#### 3) 긴급=핑퐁 / 여유=음성 채널 분기

- **요청**: 긴급 위험은 핑퐁(비프), 여유 있으면 음성.
- **구현**: `beep_interval_ms <= 100`(Critical/High) → 비프+햅틱만,
  `>100`(Mid/Low) → 반사 음성 클립 허용. 인지 `guide` TTS는 mid/low 상세 안내.
- **관련 파일**: `useWebSocket.ts`, `audioEngine.ts`,
  `docs/design/reflex_audio_specification.md` v1.3.0

#### 4) 탐지 끈 뒤 질문이 네비/물체탐지로 새는 버그 수정

- **증상(실측)**: 거리(주차센서식) 탐지 중 탐지를 끄고 질문하면 질문 답이 안 나오고
  네비게이션·장애물 안내만 재생됨.
- **원인**:
  1. `WAITING_FOR_DESTINATION` 잔류 시 질문 문장이 목적지로 파싱됨
  2. 기본 STT 폴백이 `run_orchestrator`(물체탐지 안내)로 감
- **수정**:
  - WS `detection_control` + `NavigationSession.detection_enabled`
  - 탐지 OFF 시 목적지/인텐트 대기 해제, STT 일반 발화 → `_answer_free_question`
  - 목적지 대기 중 질문형 휴리스틱(`뭐/어디/몇` 등) → 자유 질문으로 탈출
- **관련 파일**: `manager.py`, `ws_router.py`, `stt_to_llm_bridge.py`, `CameraView.tsx`,
  `tests/test_stt_to_llm_bridge_template.py`

#### 5) TTS: 기계음 완화 → Edge Neural 핫스왑

- **피드백**: 장애우분들이 기계음을 싫어함.
- **1차**: Supertonic `F2` + steps `12` + speed `0.85`, 단말 `speakFallback`에
  Google Neural 계열 ko 음성 우선 선택.
- **2차(채택)**: `TTS_ENGINE=edge` (`edge-tts`, `ko-KR-SunHiNeural`).
  로컬 모델 없이 MS Neural, MP3→WAV는 `imageio-ffmpeg`.
  오프라인 시 `TTS_ENGINE=supertonic`으로 되돌림.
- **관련 파일**: `tts_service.py`(`EdgeTTSService`), `realtime_tts.py`,
  `requirements.txt`, `.env.example`, `environment_variables.md`

#### 6) 기타

- Android 거리측정(LiDAR): Pro 전용 안내 강화, 미지원 시 버튼 숨김
  (`depthProbe.ts` / `isDepthProbeSupported`)
- Supertonic 기본 속도 env: `TTS_DEFAULT_SPEED`

---

### 2026-07-13 | 실기기 테스트 로그 (th, Android 공기계)

- **환경**:
  - 기기: Android (`R3CX70EB6QH`)
  - 네트워크: 노트북이 아이폰 핫스팟 수신(`172.20.10.x`) + Windows 모바일 핫스팟
    송신 → 공기계는 **`192.168.137.1:8000`** 로 서버 접속 (WiFi 모드)
  - 서버: FastAPI `:8000` + Redis stub `:6379` + (개발 시) Metro `:8081`
  - STT: faster-whisper-small, CPU 폴백
  - TTS: 세션 후반 `edge` / `ko-KR-SunHiNeural` (그 전 Supertonic F2 시도)

#### 테스트한 시나리오와 결과

| # | 시나리오 | 결과 / 관찰 | 후속 조치 |
|---|----------|-------------|-----------|
| T1 | WiFi로 서버 접속 (`연결: WiFi`) | `192.168.137.1` 사용 시 연결 가능. `172.20.10.2`는 PC 업링크라 공기계에 부적합 | 토글·문서화 |
| T2 | USB + `adb reverse` 개발 접속 | 핫리로드·디버그에 유용, 선 뽑으면 끊김 | USB 모드 유지 |
| T3 | 탐지 기본 OFF → 「탐지 시작」 | OFF 시 검은 화면(카메라 inactive). 시작 후 프리뷰·탐지 | 의도 UX로 확정 |
| T4 | 장애물 근접 시 비프(핑퐁) | 거리 가까울수록 간격 짧아짐(주차센서식) | 유지 |
| T5 | 긴급 시 음성+비프 동시 | 기계음 클립이 긴급 반응을 방해한다는 피드백 | 긴급(≤100ms)은 비프만 |
| T6 | 여유 거리 / 인지 안내 | 음성 안내 필요 | Mid/Low·guide TTS |
| T7 | 탐지 중 끄고 바로 질문 | **실패**: 질문 답 없음, 네비/물체탐지 멘트만 | `detection_control`+자유질문 라우팅 |
| T8 | 목적지 대기 중 일반 질문 | 목적지로 오인될 수 있음 | 질문형 휴리스틱 탈출 |
| T9 | 음성 연락처 저장 | 아라비아 숫자 OK. 한글 숫자("공일공…")는 예전 실패 → 폴백 추가 | `contact_store` 폴백 |
| T10 | 저장 후 폰 주소록 확인 | RAM만이면 앱에 안 보임 → ContactsBridge로 영속 | 단말 INSERT |
| T11 | TTS 청취(Supertonic) | 여전히 기계음 체감, 장애우 피드백 부정적 | Edge Neural로 전환 |
| T12 | TTS 청취(edge SunHi) | 로컬 대비 자연스러움↑, **인터넷 필요** | `.env` `TTS_ENGINE=edge` |
| T13 | 거리측정 버튼(Android) | LiDAR 미지원 → 안내/버튼 숨김 | `isDepthProbeSupported` |
| T14 | STT press-and-hold | 서버 기동·Whisper 프리로드 후 전사 가능. 탐지와 동시 시 네이티브 크래시 로그(3221225477) 간헐 관찰 | 후속 안정화 과제 |
| T15 | 단위 테스트 | `test_stt_to_llm_bridge_template` / `test_stt_convenience_features` 통과 (탐지OFF→질문, 목적지대기 탈출, 한글숫자 저장 포함) | CI 로컬 확인 |

#### 테스트 시 유의점 (다음 시연용)

1. 앱 **연결: WiFi**, 디버그에 `WiFi(192.168.137.1)` 확인
2. 폰 브라우저 `http://192.168.137.1:8000/docs` 열리면 네트워크 OK
3. 질문만 할 때는 **탐지 중지** 후 화면 누르고 말하기 (이제 자유 질문으로 감)
4. 길안내는 `길댕아` → `길찾아줘` → 목적지 순서
5. Edge TTS는 PC/서버에 인터넷이 있어야 함. 오프라인이면 `TTS_ENGINE=supertonic`

#### 미해결 / 후속

- STT+YOLO 동시 부하 시 Windows Whisper 네이티브 크래시 간헐
- YOLO seg 가중치 부재 → MockSegmentor
- Edge TTS 네트워크 의존(오프라인 시연 시 Supertonic 폴백 안내 필요)
- 반사 클립 WAV 자체는 여전히 사전합성(기계음 가능) — 긴급 구간에서는 재생 안 함

- **관련 파일**: 본 세션 변경 전부 + `docs/changelogs/th.md`
- **검증 결과**: 위 표 T1~T15. 서버 `/docs` 200, Edge 합성 스모크(WAV RIFF) 확인,
  pytest 브리지/편의기능 통과


### 2026-07-14 | 부가(STT)+단말 | th 음성 편의기능 3종 제거 (jh 생활지원 RAG 유지)

- **변경 내용**:
  - th 담당 음성 편의기능(긴급전화 / 연락처 저장·전화걸기 / SMS 읽어주기) 및 dial_action/contact_save WS 계약을 제거했다.
  - 삭제: contact_store/contact_service/contact_rag, contactsBridge, useSmsReader, Android SmsReader/ContactsBridge 모듈, 관련 pytest
  - 유지: jh convenience_rag / convenience_guidelines / looks_like_convenience_query 분기, KB guardian_phone DB 컬럼
  - 온보딩·API 명세서(§6.3/§6.7) 정합화
- **관련 파일**: server/stt/stt_to_llm_bridge.py, server/api/ws_router.py, client hooks/types/App/CameraView, docs/design/api_specification.md, docs/changelogs/th.md

---

### 2026-07-15 | 동기화 | dev 병합 2건 및 push 이력

- **커밋**: 병합 커밋 2건 (fast-forward, 신규 커밋 생성 없음)
- **변경 내용**:
  - **1차 병합·push 완료** (`ba7e7f3` → `550d7f7`): `origin/dev`에서 `fix: 콘솔 SystemMetrics SSE 버퍼 방지·연결 직후 스냅샷·401 안내 및 API 명세 반영` 1개 커밋을 fast-forward 병합. `git push origin th`로 즉시 push 완료(`ba7e7f3..550d7f7 th -> th`).
    - 내용: `server/api/monitor.py` SSE 응답에 `Cache-Control`/`X-Accel-Buffering: no`/`Connection: keep-alive` 헤더 추가, 연결 직후 `system_metrics` 스냅샷 1회 전송, keep-alive 주석 라인(`: keepalive`) 추가. 콘솔 `useMonitorStream.ts`는 `onerror` 시 동일 URL fetch 프로브로 401을 구별해 재로그인 안내. `SystemMetrics.tsx`/`DashboardPage.tsx`는 연결 상태별 빈 카드 안내 문구 분기. `api_specification.md` §8 v0.4.20 갱신.
  - **2차 병합 완료, push 미실행** (`550d7f7` → `321db62`): `origin/dev`에서 3개 커밋을 fast-forward 병합.
    - `9cb3548 feat(client): 앱 아이콘·Loading 스플래시 통일 및 CameraView 운영자 패널 분리` — iOS 앱 아이콘 회색 배경 제거(`scripts/generate_app_icons.py` 재작성), 로딩 화면 단일화(`expo-splash-screen` 연결), 스플래시 로고 비율 수정, `CameraView.tsx` 운영자 UI(연결상태·디버그·신뢰도 토글)를 카메라 프리뷰 아래 `ScrollView` 패널로 재배치, `DebugTriggerPanel`은 `__DEV__` 전용 마운트로 전환. 검증은 iOS 실기기만 확인(Android 실기기 검증 기록 없음).
    - `9f0267c`, `321db62` — `docs/changelogs/kb.md` 커밋 해시 보완(문서 정정, 코드 변경 없음)
    - 이 병합은 이후 `origin/th`에 함께 push됨(아래 WS 수정 커밋과 동일 push).
- **관련 파일**: `docs/changelogs/th.md` (이력 기록), 원본 변경 파일은 `docs/changelogs/kb.md` 해당 일자 항목 참조
- **검증 결과**: 두 병합 모두 `git merge origin/dev` 충돌 없이 fast-forward.

---

### 2026-07-15 | 수정 | WS Tailscale 폴백·Android Frame Processor·콘솔 표시

- **커밋**: (본 엔트리와 동일 커밋)
- **변경 내용**:
  - **클라이언트 WS**: `getWsUrlCandidates()` 추가. WiFi 실패 시 Tailscale 호스트로 후보 순환, 성공 URL 승격 유지, `wsBaseUrl` 변경 시에만 소켓 재연결해 1000/1001/1006 플래핑 완화 (`useWebSocket.ts`, `config/index.ts`, `serverTransport.ts`).
  - **Android Frame Processor**: worklet 내 모듈 `let` 대입 제거로 `invalid assignment left-hand side` 수정 (`frameCaptureProviderSelect.android.ts`).
  - **콘솔**: `DeviceTelemetryPanel` 모델 표시명을 `object_detection260714.pt` / `segmentation260714.pt`로 갱신, `LiveCameraFeed` 회전값 조정.
- **관련 파일**: `client/src/config/index.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/services/serverTransport.ts`, `client/src/services/frameCaptureProviderSelect.android.ts`, `console/src/components/DeviceTelemetryPanel.tsx`, `console/src/components/LiveCameraFeed.tsx`, `docs/changelogs/th.md`
- **검증 결과**: Android 실기기(`dev-001`) Tailscale(`100.89.91.40:8000`)로 `welcome`/`auth_ok`/`realtime_gps` 지속 수신 확인. `CONTRIBUTING.md`는 커밋·push 대상에서 제외.

---

### 2026-07-16 | 수정 | 260714 모바일 모델 정합 및 iOS 원근 통로 표시

- **변경 내용**:
  - Android·iOS 모바일 모델을 `object_detection260714.pt` / `segmentation260714.pt` 변환 산출물로 교체했다.
  - iOS CoreML 세그멘테이션의 channels-first 출력 `[1,40,8400]`을 파싱하고 640x640 화면 좌표로 환산하도록 수정했다.
  - TFLite 출력 파서와 모바일 변환 스크립트를 최신 모델 출력 계약에 맞췄다.
  - 고정 `skewX` ROI 선을 실제 카메라 픽셀 끝점 기반 원근 투영으로 교체하고, 소실점에서 촘촘해지는 깊이 눈금을 추가했다.
- **관련 파일**: `client/ios/CoreMLInferenceBridge.swift`, `client/src/inference/tfliteDetector.ts`, `client/src/components/CameraView.tsx`, 모바일 모델 산출물, `scripts/export_mobile.py`, `scripts/export_tflite.py`, `scripts/convert_yolo_to_coreml.py`
- **검증 결과**: `npx tsc --noEmit`, iOS Release `xcodebuild` 성공. iPhone 16 Pro Max 실기기에 `com.minchodan.app.th` 설치 및 실행 확인.

---

### 2026-07-16 | 수정 | 서울역 GPS 폴백 제거 및 Gemini LLM 폴백 정합

- **커밋**: (본 엔트리와 동일 커밋)
- **변경 내용**:
  1. **`server/navigation/index.html`**
     - 지도 초기 중심을 서울역(37.5560, 126.9722)에서 한반도 overview로 변경. 초기 시 가짜 사용자 마커를 찍지 않음.
     - `embed=true`(콘솔 iframe)에서는 브라우저 geolocation·8초 서울역 타임아웃 폴백을 비활성화하고, 앱 `realtime_gps` → `postMessage(inject_gps)`만 사용.
     - 단독 네비 페이지에서도 GPS 실패 시 서울역 좌표를 넣지 않고 "좌표 없음"으로 표시.
  2. **`console/src/components/LiveCameraFeed.tsx`**
     - `lastGpsRef` + `injectGpsToMap`로 HUD 미니맵에 GPS 주입.
     - iframe `onLoad`에서도 재주입해, 좌표가 iframe 로드 전에 도착해도 유실되지 않게 함.
  3. **`server/stt/stt_to_llm_bridge.py`**
     - 목적지 설정·근처 POI 검색 시 GPS 미수신이면 서울역 출발점 폴백 금지.
     - "현재 위치를 아직 받지 못했습니다..." 음성 안내 후 재입력을 유도 (`navigation-setup-no-gps`).
  4. **`server/orchestration/llm_client_factory.py`**
     - `LLM_PROVIDER=gemini`일 때 OpenAI 키 부재로 `get_client(openai)`가 조용히 Ollama로 내려가던 경로를 차단(예외 재발생).
  5. **`server/orchestration/nodes/l2_generator.py`**
     - 1차 호출 로그에 실제 provider명 출력. 주석을 Ollama 기본 가정에서 Gemini 시연 기본으로 정정.
- **관련 파일**: 위 5개 + `docs/changelogs/th.md`
- **비고**: `CONTRIBUTING.md`는 커밋 대상에서 제외.

---

### 2026-07-18 | 콘솔 | 만료 JWT 401 스팸 차단 및 자동 재로그인

- **커밋**: `6f4c5da`
- **배경**:
  - 콘솔이 `localStorage`에 남은 만료/무효 JWT로 `/api/v1/admin/detection-logs` 등을 반복 호출해 서버에 `401 Unauthorized` 경고가 쌓였다.
  - SSE 모니터도 동일 토큰으로 실패해도 로그인 화면으로 돌아가지 않아, 화면상 "로그인된 것처럼" 보이면서 API만 실패하는 상태가 지속됐다.
- **변경 내용**:
  1. **`console/src/api/adminAuth.ts` (신규)**
     - `ADMIN_TOKEN_KEY`, `isAdminTokenExpired`, `readAdminToken`, `forceAdminRelogin`, `subscribeAdminAuthExpired` 제공.
     - JWT payload의 `exp`만 클라이언트에서 읽어 만료를 선제 판정(서명 검증은 서버). 경계 레이스 완화를 위해 30초 여유.
     - 만료/401 시 `localStorage` 토큰 제거 후 `minchodan:admin-auth-expired` 커스텀 이벤트로 App에 알림.
  2. **`console/src/App.tsx`**
     - 초기 시 `readAdminToken()`으로 만료 토큰을 즉시 폐기.
     - `subscribeAdminAuthExpired`로 401 이벤트 수신 시 `setToken(null)` → 로그인 화면 복귀.
  3. **`console/src/api/useDetectionLogs.ts`**
     - 로그 목록 조회·오탐 업데이트 응답이 `401`이면 `forceAdminRelogin` 후 폴링 중단.
  4. **`console/src/api/useMembers.ts`**
     - 회원 목록 조회·등록 응답이 `401`이면 동일하게 재로그인 유도.
  5. **`console/src/api/useMonitorStream.ts`**
     - SSE `onerror` 프로브가 `401`일 때 상태 메시지만 남기던 동작을 `forceAdminRelogin`으로 교체.
- **관련 파일**: `console/src/api/adminAuth.ts`, `console/src/App.tsx`, `console/src/api/useDetectionLogs.ts`, `console/src/api/useMembers.ts`, `console/src/api/useMonitorStream.ts`, `docs/changelogs/th.md`
- **비고**: 원격 MariaDB(`Tailscale`) 미연결 시 재로그인 자체는 DB 인증이 필요하므로 Tailscale 로그인 후 사용.
- **검증 결과**: 콘솔 관련 파일 IDE 린트 오류 없음.

---

### 2026-07-18 | 7단계+부가(STT/RAG) | 문자 TTS 실험·생활지원 RAG 음성 안정화·Ollama/Gemini 폴백

- **커밋**: `5ece424`
- **배경 / 실기기 이슈**:
  1. 문자·안내문을 PC에서만 WAV로 듣는 실험에서, **모바일 앱으로도 읽어줄 수 있는지** 요구.
  2. STT 음성 RAG 테스트 시 `"음성 인식에 실패했습니다"` 반복 — 원인: 시스템 Python(3.14)으로 uvicorn을 띄워 `faster_whisper`/`WhisperModel` 초기화 실패. **venv**로 재기동 후 해소.
  3. 생활지원 RAG가 벡터DB 근거 없이 일반 LLM 답(`주변에 지도 보세요` 등)만 반환 — 원인: Ollama에 `bge-m3` 미설치로 Convenience RAG 예외 → STT 브릿지가 자유 LLM으로 폴백. `ollama pull bge-m3` + `build_convenience_db.py`(41문서)로 해소.
  4. Gemini `gemini-2.5-flash-lite` 404 및 `maxOutputTokens=100/512`로 답이 길거나 중간 절단·`**` 마크다운이 TTS에 그대로 읽힘.
- **변경 내용**:
  1. **개발용 디버그 TTS 푸시 API**
     - `server/api/debug_router.py` 신규: `POST /api/v1/debug/speak-to-device`, `GET /api/v1/debug/connected-devices`.
     - 서버 TTS로 합성한 WAV를 연결 단말에 `guide` JSON + binary로 전송. `APP_ENV=production`이면 404.
     - `server/api/session_manager.py`에 `list_connected_device_ids()` 추가.
     - `server/main.py`에 debug 라우터 마운트.
  2. **실험 스크립트 / 앱 DEBUG**
     - `scripts/tts_read_text_experiment.py`: `--to-device`로 위 API에 푸시, `--play`로 로컬 WAV 재생.
     - `client/src/components/DebugTriggerPanel.tsx`: **문자 TTS 읽기** 버튼(`speakFallback` 샘플 문자).
  3. **생활지원 Convenience RAG 음성 품질**
     - `server/rag/convenience_rag.py`:
       - 시스템/유저 프롬프트를 **최대 2문장·핵심만·마크다운 금지**로 강화.
       - `_sanitize_spoken_answer()`로 `**`, 목록 기호 제거 후 TTS 전달.
       - 답변 LLM 정책: **기본 Ollama → 실패 시 Gemini API 폴백** (`CONVENIENCE_LLM_PROVIDER`, 기본 `ollama`).
       - `ollama_only` / `gemini_only` / `gemini`(API 우선) 모드 지원.
  4. **Gemini 출력 길이 env화**
     - `server/orchestration/llm_client_factory.py`: `GEMINI_MAX_OUTPUT_TOKENS`(기본 180). 입력 컨텍스트가 아니라 생성 상한임을 주석으로 명시.
  5. **문서·템플릿**
     - `docs/ops/environment_variables.md`, `.env.example`에 `CONVENIENCE_LLM_PROVIDER`, `GEMINI_MAX_OUTPUT_TOKENS`, convenience chroma 경로 등재.
- **실기기 음성 RAG 검증(요약)**:
  - Pass: 복지카드/한빛 보행훈련/안내견 출입거부/안과·보조기기·푸른나무 직업재활 → DB 기관명·가상 전화 적중.
  - 환각 방지: `동사무소 몇 시까지` 계열 → 운영시간 지어내지 않음.
  - STT 오인식(`한비센터`, `침착해`, `동산무소`)에도 키워드 매칭으로 대체로 적중.
- **관련 파일**:
  - `server/api/debug_router.py`, `server/api/session_manager.py`, `server/main.py`
  - `server/rag/convenience_rag.py`, `server/orchestration/llm_client_factory.py`
  - `scripts/tts_read_text_experiment.py`, `client/src/components/DebugTriggerPanel.tsx`
  - `docs/ops/environment_variables.md`, `.env.example`, `docs/changelogs/th.md`
- **비고**: `.env`·API 키·로컬 ChromaDB 바이너리는 커밋하지 않음. 백엔드는 `venv\\Scripts\\python.exe -m uvicorn ...`로 기동할 것.
- **검증 결과**: Convenience RAG 스모크(`복지카드 어디서 신청해?` → Ollama 단문 + 기관/전화), debug 라우터 마운트 및 `/health` 정상.

---

### 2026-07-18 | 문서화 | 생활지원 RAG·디버그 TTS 면접 대비/하드코딩 주석

- **커밋**: `502b420`
- **변경 내용**:
  - `convenience_rag.py`: 키워드·프롬프트·sanitize·Ollama→Gemini 폴백·이중 KB에 `# 💡 [면접 대비 주석]` 및 `[하드 코딩]/[바이브 코딩]` 표기.
  - `stt_to_llm_bridge.py`: STT→Convenience RAG miss/예외 시 일반 LLM 폴백 이유를 면접 Q&A로 기록, POI/RAG/자유LLM 단계 구분.
  - `debug_router.py`: REST TTS 푸시가 기존 guide+binary 계약을 재사용하는 이유, production 404 가드레일.
  - `llm_client_factory.py`: `maxOutputTokens`가 입력 컨텍스트가 아님을 명시.
  - `session_manager.py`: CONNECTED 상태 필터 이유.
  - `DebugTriggerPanel.tsx` / `tts_read_text_experiment.py`: 단말 speakFallback vs 서버 푸시 검증 포인트.
- **관련 파일**: 위 7개 + `docs/changelogs/th.md`

---

### 2026-07-19 | 문서화 | 발표 대본 템플릿 캐시 서술 코드 검토 보고서 작성

- **배경**: 발표 대본(PDF)에 "RAG 설정: 고정 프롬프트 템플릿을 캐시에 저장하고 탐지 객체로 동적 치환(예: 전방에 {클래스명}이 있으니 주의하세요)" 서술을 추가하자는 제안이 있어, 코드 수정 없이 실제 구현과의 일치 여부를 검증했다.
- **변경 내용**:
  - `docs/ops/reports/presentation_template_cache_code_review.md` 신규: 저장소 내 템플릿·치환·캐시 메커니즘 8종 전수 매핑(파일·라인 근거), 제안 서술 판정표, 발표 반영 시 정정 5개 항목, 슬라이드 10 말미 반영 권장 문안 수록.
  - 핵심 판정: 기능 실체는 6단계 패스트 레인(`fast_lane.py` 거리 밴드 템플릿 + `graph.py` LLM 생략 분기) + 7단계 사전합성 클립 캐시(`build_guide_clips.py` 최대 210조합, `realtime_tts.py` 디스크+메모리 캐시)이며, "프롬프트 캐시"·"RAG 설정" 표현은 부정확. `server/rag/fallback.py`의 유사 문구는 실시간 경로 미배선으로 인용 부적합.
  - `docs/README.md` §7 ops/reports 표에 보고서 등재 및 버전 v0.13.13 갱신.
- **관련 파일**: `docs/ops/reports/presentation_template_cache_code_review.md`, `docs/README.md`, `docs/changelogs/th.md`
- **검증 결과**: 서버 코드 무수정(읽기 전용 검토). 근거 라인 전부 현행 코드 대조 확인.

---

### 2026-07-19 | 문서화 | 발표 대본 18개 슬라이드 전면 정합성 검사 보고서 작성

- **배경**: 템플릿 캐시 검토(직전 엔트리)에 이어, 발표 대본 PDF 전체(18슬라이드+Q&A 부록)의 기술 주장을 최신 코드·문서와 슬라이드별로 전수 대조하는 전면 정합성 검사를 진행했다.
- **변경 내용**:
  - `docs/ops/reports/presentation_script_consistency_check.md` 신규: 슬라이드별 판정표(일치 12건, 부분 불일치 4개 슬라이드 9건), 불일치 상세와 권고 문안, 일치 근거 파일·라인 매핑, 발표 전 체크리스트 7항목 수록.
  - 주요 불일치: (1) 슬라이드 10 "ChatOllama·로컬 LLM 기본" — 실제는 raw SimpleOllamaClient + 시연 기본 `LLM_PROVIDER=gemini`, 폴백도 동적 문장으로 진화. (2) 슬라이드 9 "미적중 시 룰 폴백" — `rag/fallback.py` 미배선, 실제는 "관련 수칙 없음" L2 직행. (3) 슬라이드 11 "60초 억제" — 반사 재무장 TTL 5초로 교체, 긴급은 비프 전용. (4) 슬라이드 17 "셀룰러 미검증·온디바이스 부재" 단정 — LTE 터널링 가이드·CoreML/TFLite 실기기 배포 이력과 상충.
  - `docs/README.md` §7 표 등재 및 버전 v0.13.14 갱신.
- **관련 파일**: `docs/ops/reports/presentation_script_consistency_check.md`, `docs/README.md`, `docs/changelogs/th.md`
- **검증 결과**: 서버·클라이언트 코드 무수정(읽기 전용). 대조 근거: suppressor/llm_client_factory/graph/gates/direction/risk_rules/stt_config/tts_service/stream_splitter/distance_policy/audioEngine/config 및 pipeline_stage_design·model_class_validation_report·wireless_test_guide.

---

### 2026-07-21 | 문서화 | YOLO26n 듀얼헤드 탐지·분할 종합 정리 문서 작성

- **배경**: 발표·정합성 reports와 클래스 검증 보고서에 흩어진 Object Detection 29 / Segmentation 4 관련 사실을 한 문서로 재정리해 달라는 요청.
- **변경 내용**:
  - `docs/ops/reports/yolo_segmentation_overview.md` 신규: 듀얼헤드 구조, 29+4 클래스표, 게이트·실측 KPI, 패스트 레인 연결, 온디바이스 서술 정정, 발표·면접 멘트, 코드 맵 수록.
  - `.gitignore`에 해당 보고서 Git 추적 예외(`!docs/ops/reports/yolo_segmentation_overview.md`) 추가.
  - `docs/README.md` §8 ops/reports 표 등재 및 버전 v0.14.6→v0.14.7 갱신.
- **관련 파일**: `docs/ops/reports/yolo_segmentation_overview.md`, `.gitignore`, `docs/README.md`, `docs/changelogs/th.md`
- **검증 결과**: 서버·클라이언트 코드 무수정. 소스: presentation_final_script_30min / presentation_script_consistency_check / presentation_template_cache_code_review / model_class_validation_report.

---

### 2026-07-21 | 인프라/시연 | Windows GPU 서버 demo 프로필 기동·로컬 아티팩트 gitignore 보강

- **배경**: 시연 토폴로지(LAN: LLM–FastAPI–DB, Tailscale: 실기기)로 Windows GPU 서버를 기동하면서, 로컬 전용 설정·토큰 맵이 커밋되지 않도록 ignore를 보강.
- **변경 내용**:
  - `.gitignore`에 로컬 전용 항목 추가: `.device_tokens_local.txt`, `docker/docker-compose.subnet-override.local.yml`, `.env.network.demo`, `.env.network.test`(명시적 보강, `.env.*`와 중복이어도 가독성 목적).
  - 런타임(커밋 제외)에서 수행·검증한 시연 기동 요약:
    - Tailscale Serve: MagicDNS `443` → FastAPI `127.0.0.1:8000`
    - demo 프로필: DB/미디어 Pi LAN `192.168.0.174`, LLM Mac mini `192.168.0.227:11434`
    - `DEVICE_STATIC_TOKENS`에 아이폰용 `dev-001`/`dev-002` 등록(원문은 로컬만)
    - FastAPI Docker 이미지 `minchodan-server:latest` 재빌드(`lap==0.5.13` 포함), ByteTrack `lap` 폴백 해소
    - 검증: FastAPI `/health`, DB `SELECT 1`, 미디어 `/health`, Ollama `/api/tags`
- **관련 파일**: `.gitignore`, `docs/changelogs/th.md`
- **검증 결과**: 비밀값·실 IP 프로필 파일은 Git 미추적. 이미지 빌드 `exit=0`, demo 전환 후 컨테이너 env가 LAN DB/LLM을 가리킴을 확인.

---

### 2026-07-21 | 7단계 | 콘솔 live-feed WS 조기 close 경고 및 오디오 미러 재생 안정화

- **배경**: 관제 콘솔에서 `useLiveFeed` WebSocket이 CONNECTING 중 `close()`되어 Chrome 경고가 발생하고, 단말 오디오 미러가 자동재생 정책·AbortError로 unlock이 풀려 무음이 되는 문제를 시연 중 확인.
- **변경 내용**:
  - `console/src/api/useLiveFeed.ts`: `safeCloseWebSocket` 추가. CONNECTING 상태에서는 open 이후에만 닫아 "closed before established" 경고를 제거.
  - `console/src/components/ConsoleAudioMirror.tsx`: 첫 pointerdown/keydown으로 오디오 unlock, `loadeddata` 이후 재생, `AbortError`는 unlock 유지·`NotAllowedError`만 재잠금.
- **관련 파일**: `console/src/api/useLiveFeed.ts`, `console/src/components/ConsoleAudioMirror.tsx`, `docs/changelogs/th.md`
- **검증 결과**: 이중 경로·금지 파일 가드레일 통과. API/설계 문서 계약 변경 없음(콘솔 UX 수정). 서버 guide WAV 송신 로그(`transport=binary`)와 콘솔 클립 `200` 확인 후 재생 경로만 수정.


---

### 2026-07-21 | 3단계 | Medium→Near 반사 누락·중복 안내·추적기 스트림 공유 3종 수정

- **배경**: 실기기에서 (1) Medium으로 탐지되던 객체가 Near로 접근하면 비프·햅틱이 나오지 않고, (2) 안내 메시지가 2번 나오며, (3) "탐지 데이터가 쌓여 생기는 문제 아니냐"는 제보를 분석. iOS 반사 경보는 서버 연결 중에는 서버 `reflex_alert`에만 의존하므로(온디바이스 반사는 `CameraView.tsx`에서 억제), 원인은 서버 반사 발동 조건에 있었다.
- **원인 분석**:
  - **근본 원인(Fix 1)**: 반사(8~10fps)·인지(1~2fps) 두 스트림이 단일 `DetectionPipeline`의 detector(`model.track(persist=True)`)와 tracker를 공유해, 서로 다른 fps의 프레임이 같은 ByteTrack 상태에 뒤섞여(추론 스레드풀에서 동시 실행 포함) track_id가 튀었다. track_id가 바뀌면 Redis hit_count가 1로 리셋되어 `reflex_gate`(hit_count>=3)가 Near에서 발동하지 못하고, prev_zone 히스테리시스도 풀려 near↔medium이 깜빡이며 `reflex_clear` 채터가 나 비프가 끊겼다.
  - **사각지대(Fix 2)**: Near 진입 경계는 area_ratio 0.10(≈0.70m)인데 `_send_reflex_alert`의 `is_near`가 0.6m 컷이라, 0.6~0.70m 구간에서 near 진입 반사가 non-near device 갭(1.5s)+TTL(5s) 경로로 빠져 진입 직후 비프 1회 뒤 침묵했다.
  - **중복 안내(Fix 3)**: 2026-07-21 Near/Medium 쿨다운 슬롯 분리 이후, 전환 구간에서 인지 스트림의 Medium 안내와 반사 후속 post_reflex Near 안내가 서로 다른 밴드라 상호 억제되지 않아 한 접근에 안내가 두 번 나갔다.
  - **데이터 누적 가설**: 큐·Redis·DB는 모두 TTL(트랙 컨텍스트 30s)·백프레셔(in-flight 상한, stale 드롭)로 제한되어 원인이 아니며, 실제 "누적"은 추적기 track_id 튐(세션 경과에 따른 연관 악화)이었다.
- **변경 내용**:
  - **Fix 1** `server/detection/consumer.py`: 단일 `_pipeline`을 스트림별 독립 파이프라인(`_pipelines`)으로 분리. 반사·인지가 각자 detector(독립 `model.track` 상태)와 tracker를 가져 서로의 추적 상태를 오염시키지 않는다. 주입 파이프라인(테스트)은 기존처럼 공유해 하위호환 유지.
  - **Fix 1** `server/detection/bytetrack_tracker.py`: `ByteTrackTracker(context_ns=...)` 추가. 스트림별 detector가 같은 "T-0001"을 내도 Redis 트랙 컨텍스트 키를 `ctx:{stream}:{track_id}`로 네임스페이스해 hit_count·prev_zone 교차 오염을 차단. `context_ns=""` 기본값으로 기존 호출부·테스트 호환.
  - **Fix 2** `server/detection/consumer.py`: `_send_reflex_alert`의 `is_near` 판정을 raw 0.6m 컷에서 거리 정책 SSOT의 `distance_band == "near"`로 정합(object 반사는 route=="reflex"로만 생성되므로 밴드 기준과 일치, head_level/surface 무영향).
  - **Fix 3** `server/detection/consumer.py`: `_send_cognitive_guide`에 Near 반사 에피소드 활성 중 Medium 존재/접근 안내를 억제하는 가드 추가(`Alert_suppressor.peek_active_near_track`). preset(post_reflex)·보도 이탈·노면 전용은 예외. Near 우선 원칙과 정합하며 억제는 Near episode 생명주기 동안만 유지.
- **관련 파일**: `server/detection/consumer.py`, `server/detection/bytetrack_tracker.py`, `docs/changelogs/th.md`
- **검증 결과**: 비라이브 전체 테스트 460 passed(관련 detection/distance/reflex/suppressor/near/track 스위트 포함). 잔여 3건(`test_frame_decode.py::test_singleton_queue_maxsize`, `test_mcp_gpu.py` 2건)은 본 변경 이전부터 실패하는 환경 의존(splitter maxsize/GPU/ollama) 케이스로 stash 대조 확인. 이중 경로 가드레일 준수(반사 게이트 `server/detection/gates/` 무수정), 금지 파일 스테이징 없음, `py_compile`·import 정상. ruff는 로컬 미설치로 스킬 규격에 따라 생략.
