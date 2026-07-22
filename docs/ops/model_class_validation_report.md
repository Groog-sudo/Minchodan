# YOLO26n 학습 모델 클래스별 검증 보고서

> **작성일**: 2026-07-06
> **버전**: v1.0.1 (2026-07-20 헤더 표기 정정: "33클래스"를 "탐지 29 + 분할 4 = 33클래스"로 명시. 본문은 정합. 기존 v1.0.0 이력: 33클래스 샘플 검증 최초 실행)
> **기준 문서**: [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) (3단계 KPI), [`docs/ops/ondevice_coreml_benchmark.md`](ondevice_coreml_benchmark.md)
> **코드 참조**: `scripts/validate_class_samples.py`, `server/detection/yolo_detector.py`
> **모델 파일**: `server/models/yolo26n/det_best_20260705.pt` (Object Detection 29클래스), `server/models/yolo26n/segbest.pt` (Segmentation 4클래스)

---

## 1. 개요

본 문서는 Minchodan의 두 파인튜닝 완료 모델(**Object Detection 29클래스**, **Segmentation 4클래스**)이 실제로 각 클래스를 탐지하는지 클래스별 샘플 이미지로 검증한 결과를 기록한다.

검증 방식은 클래스당 실사 이미지 3장씩(총 99장, 인터넷에서 한국 인도·도로 맥락 우선으로 수집)을 입력하여 추론을 실행하고, bbox와 confidence(신뢰도) 스코어를 이미지 위에 시각화하여 저장하는 방식으로 진행했다.

---

## 2. 검증 환경

| 항목 | 내용 |
|:---|:---|
| **Object Detection 모델** | `server/models/yolo26n/det_best_20260705.pt` (29클래스, `ultralytics==8.4.82`) |
| **Segmentation 모델** | `server/models/yolo26n/segbest.pt` (4클래스) |
| **추론 스크립트** | `scripts/validate_class_samples.py` (ultralytics `YOLO.predict()` 직접 호출, `result.plot(conf=True, labels=True)`로 시각화) |
| **입력 데이터** | `data/validation_samples/raw/<class_name>/` — 클래스별 3장, 총 99장 |
| **출력 데이터** | `data/validation_samples/results/detection/<class_name>/`, `data/validation_samples/results/segmentation/<class_name>/` — bbox+신뢰도 오버레이 이미지 |
| **confidence threshold** | 0.25 |
| **이미지 출처** | Wikimedia Commons 등 인터넷 공개 이미지, 한국 인도·도로 맥락 우선 검색 (일부 클래스는 한국 특정 사진 미확보로 해외 사진 대체, 3.3절 참조) |

> **참고**: `server/detection/yolo_detector.py`의 `_parse_result`는 담당자 학습형 협업 규칙(`SKILLS.md`)에 따라 파싱 루프가 비어 있는 학습용 스텁 상태였다. 이번 검증에서 해당 스텁을 채워 서버 파이프라인이 실제 `list[Detection]`을 반환하도록 수정했다(사용자 직접 지시에 따른 반영). 단, 이번 검증 스크립트 자체는 `YoloDetector` 래퍼를 거치지 않고 ultralytics 모델을 직접 호출한다.

---

## 3. 검증 결과

### 3.1 Object Detection (29클래스)

| 클래스 | 검증 이미지 | 탐지 성공 이미지 | 총 박스 수 | 최고 신뢰도 |
|:---|:---:|:---:|:---:|:---:|
| person | 3 | 3/3 | 69 | 0.961 |
| tree_trunk | 3 | 3/3 | 43 | 0.944 |
| barricade | 3 | 2/3 | 42 | 0.940 |
| bollard | 3 | 3/3 | 28 | 0.945 |
| pole | 3 | 3/3 | 26 | 0.822 |
| scooter | 3 | 3/3 | 26 | 0.939 |
| parking_meter | 3 | 3/3 | 25 | 0.946 |
| traffic_light | 3 | 3/3 | 22 | 0.943 |
| table | 3 | 3/3 | 21 | 0.943 |
| bench | 3 | 2/3 | 20 | 0.939 |
| bicycle | 3 | 3/3 | 19 | 0.934 |
| car | 3 | 3/3 | 18 | 0.961 |
| bus | 3 | 3/3 | 17 | 0.922 |
| power_controller | 3 | 3/3 | 15 | 0.871 |
| dog | 3 | 3/3 | 14 | 0.884 |
| motorcycle | 3 | 2/3 | 12 | 0.823 |
| fire_hydrant | 3 | 3/3 | 11 | 0.929 |
| truck | 3 | 3/3 | 8 | 0.947 |
| kiosk | 3 | 2/3 | 8 | 0.882 |
| stroller | 3 | 3/3 | 7 | 0.921 |
| movable_signage | 3 | 2/3 | 6 | 0.939 |
| carrier | 3 | 3/3 | 5 | 0.663 |
| potted_plant | 3 | 2/3 | 5 | 0.951 |
| chair | 3 | 1/3 | 4 | 0.900 |
| traffic_sign | 3 | 2/3 | 4 | 0.976 |
| wheelchair | 3 | 2/3 | 3 | 0.632 |
| cat | 3 | 1/3 | 2 | 0.818 |
| traffic_light_controller | 3 | 2/3 | 2 | 0.732 |
| **stop** | 3 | **0/3** | **0** | **탐지 없음** |

### 3.2 Segmentation (4클래스)

| 클래스 | 검증 이미지 | 탐지 성공 이미지 | 총 박스 수 | 최고 신뢰도 |
|:---|:---:|:---:|:---:|:---:|
| braille_normal | 3 | 3/3 | 9 | 0.785 |
| sidewalk_normal | 3 | 3/3 | 5 | 0.850 |
| caution | 3 | 3/3 | 5 | 0.908 |
| roadway | 3 | 3/3 | 5 | 0.684 |

### 3.3 클래스별 탐지 실패/저조 사례 분석

| 클래스 | 증상 | 원인 추정 |
|:---|:---|:---|
| **stop** | 3장 전부 탐지 0건 (conf 0.01까지 낮춰도 top 클래스로 단 한 번도 등장하지 않음) | 명확한 한국 정지(STOP) 표지판 실사임에도 미탐지 — 학습 데이터 부족 또는 `traffic_sign`과의 클래스 혼동 가능성. 재학습 데이터 보강이 필요한 것으로 판단됨 |
| **cat, chair** | 1/3만 탐지 | 샘플 이미지에서 대상이 작게 나오거나 배경에 가려진 구도. 클래스 자체보다 샘플 구도 영향으로 추정 |
| **traffic_light_controller** | 2/3 탐지, 최고 신뢰도 0.732로 낮은 편 | 검증 샘플 자체가 한국 특정 사진을 구하지 못해 해외(호주/미국) 제어함 사진으로 대체됨(아래 참고) — 클래스 정의상 매우 희소한 시설물이라 학습 데이터도 적을 가능성 |
| **wheelchair, carrier** | 탐지는 되나 최고 신뢰도가 0.6대로 낮음 | 클래스 자체 신뢰도가 다른 클래스 대비 낮게 형성됨 — 학습 데이터 다양성 보강 여지 |

> **샘플 이미지 출처 참고**: `traffic_light_controller`(전량 해외), `stroller`/`wheelchair`/`braille_normal`/`caution`/`roadway`/`sidewalk_normal`(한국 특정 사진 일부 미확보로 해외 사진 혼재) 등은 한국 실사 확보에 실패해 대체 이미지를 사용했다. 해당 클래스의 결과는 국내 실제 환경 재현성이 다른 클래스보다 낮을 수 있다.

---

## 4. 종합 판정

| 검증 항목 | 판정 기준 | 결과 |
|:---|:---|:---|
| **모델 로드** | 두 모델 모두 정상 로드 | **통과** |
| **클래스 정의 정합성** | 코드(`useOnDeviceDetection.ts`, `CoreMLInferenceBridge.swift`)와 모델 실제 클래스 수·순서 일치 | **통과** (Detection 29클래스, Segmentation 4클래스 전부 일치) |
| **bbox 및 신뢰도 시각화** | 참고 스타일(클래스명+신뢰도 라벨 오버레이)과 동일한 형식으로 출력 | **통과** |
| **클래스별 최소 탐지 재현율** | 29개 Detection 클래스 중 28개 클래스에서 최소 1장 이상 탐지 성공 | **부분 통과** (`stop` 클래스 0/3으로 미달) |
| **Segmentation 4클래스 전체 탐지** | 4클래스 전부 최소 1장 이상 탐지 | **통과** |

---

## 5. 후속 조치 제안

1. `stop` 클래스는 3장 모두(다른 각도·거리) 탐지 실패했으므로, 학습 데이터셋에서 `stop` 라벨 분포와 `traffic_sign`과의 혼동 여부를 우선 점검한다.
2. `traffic_light_controller`, `stroller` 등 한국 실사 샘플 확보에 실패한 클래스는 국내 실사 이미지를 추가로 확보해 재검증하는 것을 권장한다.
3. `cat`, `chair`, `wheelchair`, `carrier`처럼 탐지율·신뢰도가 낮은 클래스는 샘플 수를 늘려(클래스당 3장 → 10장 이상) 재검증하면 학습 데이터 부족과 샘플 구도 문제를 구분할 수 있다.

---

## 6. 재현 절차

```bash
source venv/bin/activate  # 또는 .venv
python scripts/validate_class_samples.py
```

- 입력: `data/validation_samples/raw/<class_name>/*.jpg`
- 출력: `data/validation_samples/results/{detection,segmentation}/<class_name>/*_result.jpg`
- 클래스별 샘플이 없는 경우 해당 클래스는 자동으로 건너뛰고 콘솔에 안내 로그를 출력한다.

---

## 7. 참고

| 항목 | 내용 |
|:---|:---|
| **검증 스크립트** | `scripts/validate_class_samples.py` |
| **서버 탐지 래퍼 수정** | `server/detection/yolo_detector.py` — `_parse_result` 파싱 루프 활성화 |
| **iOS 온디바이스 벤치마크** | [`docs/ops/ondevice_coreml_benchmark.md`](ondevice_coreml_benchmark.md) |
| **파이프라인 KPI 기준** | [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) |
