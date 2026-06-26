# 3단계 탐지·분할·게이트 백엔드 구현

> **작성일**: 2026-06-25
> **작성자**: kb
> **단계**: 3 - AI 장애물 실시간 인식

---

## 작업 제목

Yolo 26N Object Detection / Segmentation + ByteTrack + 이중 게이트 백엔드 구현 및 단위 테스트 검증

---

## 변경 내용

- `server/detection/` 패키지 신규 구현: schemas, detector_interface, config, mock_detector, yolo_detector, yolo_segmentor, bytetrack_tracker, gates, detection_pipeline
- `server/bus/` 패키지 신규 구현: redis_client, producer
- `tests/test_detection.py` 신규 작성: 3단계 검증 21개 케이스, 21 passed
- `DetectionPipeline`에서 Detector/Segmentor 예외를 분리 처리하여 한쪽 실패 시에도 파이프라인 영속성 유지
- `ByteTrackTracker`에 Redis 예외 방어 처리 추가
- `requirements.txt` 재작성: `pytest`, `pytest-asyncio` 추가, Python 3.13 호환을 위해 `numpy>=2.1.0` 반영
- `.env.example` v1.1 기준 통일: `YOLO26N_OBJECT_DET`, `YOLO26N_SEG`, `DETECTOR_TYPE=mock` 추가
- `server/models/yolo26/`, `server/models/segformer/` 제거 및 `server/models/yolo26n/.gitkeep` 추가
- `docs/test_specification.md`, `docs/stage3_detection_design.md`, `docs/architecture.md` 상태 반영

---

## 관련 파일

| 파일 경로 | 변경 유형 | 설명 |
| --------- | --------- | ---- |
| `server/detection/schemas.py` | 신규 | Pydantic 데이터 모델 |
| `server/detection/detector_interface.py` | 신규 | Detector/Segmentor 추상 인터페이스 |
| `server/detection/config.py` | 신규 | 설정 및 모델 팩토리 |
| `server/detection/mock_detector.py` | 신규/수정 | Mock Detector/Segmentor, 기본 클래스를 `unknown`으로 변경 |
| `server/detection/yolo_detector.py` | 신규 | Yolo 26N Object Detection (`model.track()` 내장 ByteTrack) |
| `server/detection/yolo_segmentor.py` | 신규 | Yolo 26N Segmentation |
| `server/detection/bytetrack_tracker.py` | 신규/수정 | track_id 기반 속도/방향 계산, Redis 예외 방어 |
| `server/detection/gates/reflex_gate.py` | 신규 | 고위험 객체 반사 게이트 |
| `server/detection/gates/surface_gate.py` | 신규 | P0 노면 반사 게이트 |
| `server/detection/detection_pipeline.py` | 신규/수정 | 전체 파이프라인, Detector/Segmentor 예외 분리 |
| `server/detection/__init__.py` | 신규 | 패키지 export |
| `server/detection/gates/__init__.py` | 신규 | 게이트 패키지 export |
| `server/bus/redis_client.py` | 신규 | Redis Streams/hash 컨텍스트 클라이언트 |
| `server/bus/producer.py` | 신규 | mid/low 위험 이벤트 발행 |
| `server/bus/__init__.py` | 신규 | 패키지 export |
| `tests/test_detection.py` | 신규 | 3단계 단위 테스트 21개 |
| `.env.example` | 수정 | 모델 경로 및 `DETECTOR_TYPE` 통일 |
| `requirements.txt` | 수정 | pytest, numpy 2.x 반영 |
| `docs/test_specification.md` | 수정 | TC-DET/TC-PATH 상태 반영 |
| `docs/stage3_detection_design.md` | 수정 | 버전/상태/방어적 코딩 매트릭스 업데이트 |
| `docs/architecture.md` | 수정 | 3단계 방어적 처리 및 pytest 명령 반영 |

---

## 검증 결과

- [x] 단위 테스트 통과: `python -m pytest tests/test_detection.py -v` → 21 passed
- [ ] KPI 기준 달성: Detection < 80ms, conf≈0.87은 Yolo 26N 가중치 도착 후 측정 예정
- [ ] 코드 리뷰 완료

---

## 비고

- 팀원이 Yolo 26N Object Detection/Segmentation 가중치를 학습 중이므로, 현재는 `MockDetector`/`MockSegmentor`로 파이프라인 흐름을 검증합니다.
- 가중치 파일(`server/models/yolo26n/object_detection.pt`, `server/models/yolo26n/segmentation.pt`)이 배치되면 `config.py` 팩토리가 자동으로 `YoloDetector`/`YoloSegmentor`로 전환됩니다.
- 반사 경로는 LLM/RAG/실시간 TTS를 경유하지 않으며, `ReflexAlert`는 사전합성 클립 경로만 포함합니다.
