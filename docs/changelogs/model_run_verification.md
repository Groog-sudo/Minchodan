# YOLO 모델 추론 엔진 구동 정밀 검증 보고서

> **작성일**: 2026-07-12
> **버전**: v1.0.0
> **상태**: 검증 완료

본 문서는 Minchodan GPU 서버 내 객체 탐지 및 노면 분할 YOLO 모델의 로드 상태, 가중치 매핑, 실제 동작 여부를 추적 조사한 결과 보고서입니다.

---

## 1. 모델 구동 정밀 검증표

| 구분 | 검증 항목 | 세부 내용 |
| :--- | :--- | :--- |
| **모델 유형** | **Object Detection** | **Semantic Segmentation** |
| **목표 가중치 파일명** | `best_20260705.pt` | `best.pt` |
| **실제 파일 물리 경로** | `server/models/yolo26n/best_20260705.pt` | `server/models/yolo26n/best.pt` |
| **물리 파일 존재 여부** | 존재함 (15.5MB) | 존재함 (6.5MB) |
| **클래스 개수** | 29개 클래스 (scooter, bollard, person 등) | 4개 클래스 (sidewalk_normal, caution 등) |
| **환경변수 설정값** | `YOLO26N_OBJECT_DET=server/models/yolo26n/best_20260705.pt` | `YOLO26N_SEG=server/models/yolo26n/best.pt` |
| **DETECTOR_TYPE 설정값** | `DETECTOR_TYPE=mock` | `DETECTOR_TYPE=mock` |
| **실제 인스턴스 로드 결과** | **MockDetector** (폴백 모드) | **MockSegmentor** (폴백 모드) |
| **진단 결과 및 원인** | 가중치 파일은 물리적으로 존재하나, `.env` 설정에 `DETECTOR_TYPE=mock`으로 지정되어 있어 실제 GPU/YOLO 추론을 생략하고 Mock 인스턴스로 폴백하여 구동 중입니다. | 가중치 파일은 물리적으로 존재하나, `.env` 설정에 `DETECTOR_TYPE=mock`으로 지정되어 있어 실제 GPU/YOLO 추론을 생략하고 Mock 인스턴스로 폴백하여 구동 중입니다. |

---

## 2. 해결 방안 및 조치 가이드
* **실제 YOLO 추론 기동 방법:**
  1. 프로젝트 루트의 `.env` 파일을 엽니다.
  2. `DETECTOR_TYPE=mock` 라인을 `DETECTOR_TYPE=yolo`로 수정합니다.
  3. FastAPI 백엔드 서버를 재시작하면 실제 물리 가중치를 로드하여 실시간 추론을 개시합니다.
