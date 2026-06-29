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
