# 반사 위험도 SSOT 계약 (초안)

> **작성일**: 2026-07-13
> **버전**: v0.2.0 (Object Detection 29종 전체 반사 경로 정합화)
> **근거**: [`docs/ops/dev_8b2f606_improvement_plan.md`](../ops/dev_8b2f606_improvement_plan.md) §2 "반사 위험도 SSOT", [`docs/research/mitos_improvement_roadmap.md`](../research/mitos_improvement_roadmap.md) §2
> **적용 대상**: 서버 반사 게이트(`server/detection/gates/reflex_gate.py`)와 단말 온디바이스 게이트(`client/src/components/CameraView.tsx`)

---

## 1. 문제 정의

서버와 단말이 고위험 클래스·confidence·거리 규칙을 **각자 하드코딩으로 복제**하고 있어, 한쪽만 수정하면 동일 프레임에 대한 위험 판정이 조용히 어긋납니다. 본 문서는 두 구현이 반드시 일치시켜야 하는 값(SSOT)과 플랫폼별 확장이 허용되는 값을 구분해 계약으로 고정합니다.

---

## 2. SSOT 대상: 고위험 클래스와 최소 confidence (양측 일치 필수)

아래 29종은 서버 `HIGH_RISK_CLASSES`와 단말 `CLASS_MIN_CONFIDENCE`가 **항상 동일한 값**을 가져야 합니다. 변경 시 반드시 같은 커밋에서 양쪽을 함께 수정합니다.

| 클래스 | 최소 confidence | 근거 |
| --- | --- | --- |
| `barricade` | 0.35 | 빠른 탐지를 위한 임계값 하향 |
| `bench` | 0.3 | 동일 |
| `bicycle` | 0.3 | 동일 |
| `bollard` | 0.3 | 동일 |
| `bus` | 0.35 | 동일 |
| `car` | 0.35 | 동일 |
| `carrier` | 0.3 | 동일 |
| `cat` | 0.3 | 동일 |
| `chair` | 0.3 | 동일 |
| `dog` | 0.3 | 동일 |
| `fire_hydrant` | 0.35 | 동일 |
| `kiosk` | 0.3 | 동일 |
| `motorcycle` | 0.35 | 동일 |
| `movable_signage` | 0.3 | 동일 |
| `parking_meter` | 0.35 | 동일 |
| `person` | 0.3 | 동일 |
| `pole` | 0.3 | 동일 |
| `potted_plant` | 0.3 | 동일 |
| `power_controller` | 0.3 | 동일 |
| `scooter` | 0.3 | 동일 |
| `stop` | 0.35 | 동일 |
| `stroller` | 0.3 | 동일 |
| `table` | 0.3 | 동일 |
| `traffic_light` | 0.35 | 동일 |
| `traffic_light_controller` | 0.35 | 동일 |
| `traffic_sign` | 0.35 | 동일 |
| `tree_trunk` | 0.3 | 동일 |
| `truck` | 0.35 | 동일 |
| `wheelchair` | 0.3 | 동일 |

---

## 3. 플랫폼별 확장 허용 영역 (일치 불요, 명시 필수)

| 영역 | 현황 | 계약 |
| --- | --- | --- |
| 단말 전용 추가 confidence 하한 | `roadway` (0.35) | 단말 전용 확장으로 허용. 단, **§2의 29종 값과 충돌하는 항목을 추가할 수 없다** |
| 거리 추정 산식 | 서버: bbox 하단 y 기반 의사 거리(`1.5 - ratio*1.1`, `reflex_gate.py`) / 단말: 면적 기반 `0.22/sqrt(areaRatio)`(`CameraView.tsx`) | **현재 불일치 상태를 인지된 기술 부채로 명시**. LiDAR/ARKit depth 도입(Mitos 로드맵 §2) 시 단일 산식으로 수렴하며, 그 전까지는 각 산식의 임계 동작(발동 거리)이 동등한지 실기기 시나리오로 검증한다 |
| 방향 판정 | 서버 `direction.py` FRONT_BAND / 단말 자체 판정 | 좌표계 기준(카메라 프레임)이 동일하므로 허용. 착용 방식 확정 시 재검토 |

---

## 4. 변경 절차

1. §2 표의 값 변경은 서버·단말 코드를 **같은 커밋**에서 수정하고 본 문서 §2 표를 함께 갱신합니다.
2. 커밋 전 회귀 테스트 `tests/test_risk_ssot.py`(§5)가 양측 코드에서 값을 추출해 일치 여부를 자동 검증합니다.
3. 파일 소유권은 [`docs/mobile/ios_android_bifurcation_contract.md`](../mobile/ios_android_bifurcation_contract.md) §3을 따릅니다(서버 게이트는 공유, 단말 게이트는 플랫폼 작업자).

---

## 5. 자동 검증

`tests/test_risk_ssot.py`가 다음을 검증합니다.

| 검증 항목 | 방법 |
| --- | --- |
| 서버 29종 클래스·confidence == 본 문서 §2 | `reflex_gate.HIGH_RISK_CLASSES` import 대조 |
| 단말 29종 클래스·confidence == 본 문서 §2 | `CameraView.tsx`의 `CLASS_MIN_CONFIDENCE` 텍스트 파싱 대조 |
| 단말 확장 목록이 §2와 충돌하지 않음 | 교집합 값 비교 |

> **한계**: 본 테스트는 confidence 문턱값의 복제 불일치만 잡습니다. 거리 산식·연속 프레임 조건 등 동작 수준의 동등성은 실기기 시나리오 검증(dev 개선 계획서 §2 "동일 입력 프레임에서 서버/단말 위험 등급 비교")이 필요합니다.

---

## 6. 후속 로드맵

| 단계 | 내용 |
| --- | --- |
| 1 (본 초안) | 문서 계약 + 회귀 테스트로 복제 불일치 차단 |
| 2 | 기계가독 단일 소스(예: `shared/risk_rules.json`)를 서버 import·단말 codegen으로 소비 (TH·Mobile 합의 필요) |
| 3 | LiDAR/depth 기반 거리 단일화, 반사 억제 재설계(debounce·재진입 재경보)와 통합 |
