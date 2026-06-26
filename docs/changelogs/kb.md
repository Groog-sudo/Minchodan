# Changelog - kb (관범)

> 이 파일은 **kb(관범)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-06-24 | 전체 | 문서 기준선 구축

- **커밋**: `docs: 프로젝트 문서 기준선 구축 및 초기 디렉토리 골격 생성`
- **변경 내용**:
  - `minchodan_design_note.md` 7단계 골격을 기반으로 루트 README 작성.
  - 스킬 문서(`skills.md`)와 docs 문서 세트 전체 작성 (AGENTS, architecture, api_specification, test_specification, git_branching_strategy, pipeline_stage_design).
  - `.env.example` 환경변수 템플릿과 `requirements.txt` 파이썬 의존성 초기화.
  - 개인 문서 폴더(`docs/{dg,jh,jy,kb,th}/`)를 제거하고, 모든 설계 문서를 `docs/` 폴더에서 공유로 관리하도록 통일.
  - 디렉토리 골격(`.gitkeep`)을 유지하며, 코드 구현은 각 단계별로 진행 예정.
- **관련 파일**: `README.md`, `skills.md`, `docs/README.md`, `docs/AGENTS.md`, `docs/architecture.md`, `docs/api_specification.md`, `docs/test_specification.md`, `docs/git_branching_strategy.md`, `docs/pipeline_stage_design.md`, `.env.example`, `requirements.txt`
- **검증 결과**: 문서 구조 확인, 링크 정합성 확인
- **비고**: 초기 커밋 기준선. 코드 구현은 1단계(WebSocket Gateway)부터 순차 진행.

---

### 2026-06-25 | 3단계 | 3단계 탐지·분할·게이트 백엔드 구현

- **커밋**: `feat(3단계): Yolo 26N 탐지·분할·게이트 백엔드 및 테스트 구현`
- **변경 내용**:
  - `server/detection/` 패키지 신규 구현: schemas, detector_interface, config, mock_detector, yolo_detector, yolo_segmentor, bytetrack_tracker, gates, detection_pipeline
  - `server/bus/` 패키지 신규 구현: redis_client, producer
  - `tests/test_detection.py` 신규 작성: 3단계 검증 21개 케이스
  - `DetectionPipeline`에서 Detector/Segmentor 예외를 분리 처리하여 한쪽 실패 시에도 파이프라인 영속성 유지
  - `ByteTrackTracker`에 Redis 예외 방어 처리 추가
- **관련 파일**: `server/detection/`, `server/bus/`, `tests/test_detection.py`
- **검증 결과**: pytest 테스트 21 Passed 통과
- **비고**: 가중치 미제공 시 MockDetector/MockSegmentor로 자동 폴백 및 팩토리 연동 완료

---

### 2026-06-26 | 3단계 | 보행이론 보고서 추가 및 YOLO26n 통합 테스트 환경 구축

- **커밋**: `docs: 실제 YOLO26n 모델 가중치 다운로드 및 연산 검증 스크립트 추가`, `docs: 보행이론 기반 행동 패턴 및 위험도 정의 보고서 추가`
- **변경 내용**:
  - 보행지도사 이론에 근거하여 시각장애인 행동 패턴 및 위험도 게이트 정의 분석 보고서 작성
  - 공식 `yolo26n.pt` 및 `yolo26n-seg.pt` 모델의 가중치를 자동 배치하는 다운로드 스크립트 구축 및 로드 검증 완수
  - 실제 YOLO26n 모델 연산, ByteTrack 추적, 이중 게이트 작동 및 Redis 연결 예외 바이패스를 검증하는 통합 테스트 스크립트 구축 및 테스트 통과
- **관련 파일**: `docs/behavior_and_risk_insight.md`, `scripts/download_pretrained_weights.py`, `scripts/verify_pretrained_weights.py`, `scripts/integration_test_pipeline.py`
- **검증 결과**: verify_pretrained_weights.py 및 integration_test_pipeline.py 추론 및 분기 PASS
- **비고**: 실제 YOLO26n 사전 학습 가중치 pt 파일 2종(총 약 12MB)을 Git 추적 파일로 등록 및 푸시 완료

