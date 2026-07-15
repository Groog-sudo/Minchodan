# YOLO26n 커스텀 가중치 · 데이터셋 출처

> **작성일**: 2026-07-14
> **버전**: v0.1.0
> **대상 가중치**: `server/models/yolo26n/object_detection.pt`, `server/models/yolo26n/segmentation.pt`

---

## 1. 가중치 성격

| 항목 | 내용 |
| --- | --- |
| **유형** | **커스텀 YOLO** (COCO 80클래스 스톡 아님) |
| **탐지 클래스** | AI Hub 보행 장애물 **29종** (`barricade` … `wheelchair`) |
| **분할 클래스** | 노면 **4종** (`sidewalk_normal`, `caution`, `roadway`, `braille_normal`) |
| **확인 방법** | `YOLO(...).names`로 클래스 사전 실측 |

---

## 2. 데이터셋 출처

학습·보강에 사용한 외부/국내 데이터는 **우리 29/4 클래스 taxonomy로 필터·매핑**한 뒤 투입한다. 출처 이름에 COCO가 있어도 최종 라벨은 커스텀 클래스다.

| 구분 | 출처 | 용도 |
| --- | --- | --- |
| **국내** | AI Hub dataSetSn=513 (도로 시설물 BBox) | 볼라드·키오스크 등 한국형 시설물 |
| **국내** | AI Hub dataSetSn=189 (인도보행 영상, CVAT XML) | 보행 장면 BBox |
| **해외** | COCO 2017 (FiftyOne) | `bench`/`chair`/`table`/`person`/`car` 등 약클래스 보강 → 29종으로 리맵 |
| **해외** | Open Images V7 (FiftyOne) | 위와 동일, 약클래스 보강 → 29종으로 리맵 |
| **해외** | ScooterDet (Zenodo) | `scooter` 보강 |
| **수집 도구** | `scripts/obstacle_data_miner/` | 수집·매핑·YOLO txt 변환 CLI |

세부 매핑·검증은 [`scripts/obstacle_data_miner/docs/report/object_detection/object_detection_report.md`](../scripts/obstacle_data_miner/docs/report/object_detection/object_detection_report.md)를 참조한다.

---

## 3. 과거 혼동 메모

`data/test_100_samples/`에 있던 COCO 환각 보고는 **옛 실험/출처 데이터셋 이름과 커스텀 가중치를 혼동**한 기록이다. 현재 Git 추적 가중치의 `names`는 29클래스이므로 스톡 COCO로 해석하지 않는다.
