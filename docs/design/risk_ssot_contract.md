# 반사 위험도 SSOT 계약 (초안)

> **작성일**: 2026-07-11
> **버전**: v0.1.2 (2026-07-13 계측용 `거리측정` 버튼의 자체 세션 video+depth 동기화 프리뷰 개선 상태를 거리 산식 기술 부채 항목에 추가 + 이전 v0.1.1 이력 유지: 단말 LiDAR `distanceMeters` 우선, bbox 휴리스틱 fallback 구조와 실기기 동기화 검증 잔여 조건 반영)
> **근거**: [`docs/ops/dev_8b2f606_improvement_plan.md`](../ops/dev_8b2f606_improvement_plan.md) §2 "반사 위험도 SSOT", [`docs/research/mitos_improvement_roadmap.md`](../research/mitos_improvement_roadmap.md) §2
> **적용 대상**: 서버 반사 게이트(`server/detection/gates/reflex_gate.py`)와 단말 온디바이스 게이트(`client/src/components/CameraView.tsx`)

---

## 1. 문제 정의

서버와 단말이 고위험 클래스·confidence·거리 규칙을 **각자 하드코딩으로 복제**하고 있어, 한쪽만 수정하면 동일 프레임에 대한 위험 판정이 조용히 어긋납니다. 본 문서는 두 구현이 반드시 일치시켜야 하는 값(SSOT)과 플랫폼별 확장이 허용되는 값을 구분해 계약으로 고정합니다.

---

## 2. SSOT 대상: 고위험 클래스와 최소 confidence (양측 일치 필수)

아래 5종은 서버 `HIGH_RISK_CLASSES`와 단말 `CLASS_MIN_CONFIDENCE`가 **항상 동일한 값**을 가져야 합니다. 변경 시 반드시 같은 커밋에서 양쪽을 함께 수정합니다.

| 클래스 | 최소 confidence | 근거 |
| --- | --- | --- |
| `car` | 0.6 | 실내 오탐 완화 (실외 전용 클래스, 문턱 상향) |
| `truck` | 0.6 | 동일 |
| `bus` | 0.6 | 동일 |
| `motorcycle` | 0.55 | 동일 |
| `scooter` | 0.5 | 동적/돌발 최고 위험, 상대적으로 낮은 문턱 유지 |

---

## 3. 플랫폼별 확장 허용 영역 (일치 불요, 명시 필수)

| 영역 | 현황 | 계약 |
| --- | --- | --- |
| 단말 전용 추가 confidence 하한 | `fire_hydrant`, `parking_meter`, `traffic_light`, `traffic_light_controller`, `traffic_sign`, `stop`, `roadway` (각 0.55) | 단말 실내 오탐 완화 전용 확장으로 허용. 단, **§2의 5종 값과 충돌하는 항목을 추가할 수 없다** |
| 거리 추정 산식 | 서버: bbox 하단 y 기반 의사 거리(`1.5 - ratio*1.1`, `reflex_gate.py`) / 단말: `distanceMeters`가 있으면 LiDAR 실거리 우선, 없으면 면적 기반 `0.22/sqrt(areaRatio)`(`CameraView.tsx`) 및 기존 면적 기반 반사 게이트로 fallback | **현재 불일치 상태를 인지된 기술 부채로 명시**. 단말은 LiDAR 값이 들어오는 경우 0.5/1.0/1.5/3.0m 임계값으로 우선 판정한다. 계측용 `거리측정` 버튼은 자체 `DepthProbeBridge` 세션 안에서 video+depth를 동기화한 1:1 프리뷰와 crop 좌표 샘플링으로 개선됐지만, 정식 수렴 조건은 탐지 video frame과 depth map의 동일 세션·동일 타임스탬프·동일 640x640 crop 좌표계 실기기 검증이다. 그 전까지 서버/단말 발동 거리 동등성은 시나리오로 검증한다 |
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
| 서버 5종 클래스·confidence == 본 문서 §2 | `reflex_gate.HIGH_RISK_CLASSES` import 대조 |
| 단말 5종 클래스·confidence == 본 문서 §2 | `CameraView.tsx`의 `CLASS_MIN_CONFIDENCE` 텍스트 파싱 대조 |
| 단말 확장 목록이 §2와 충돌하지 않음 | 교집합 값 비교 |

> **한계**: 본 테스트는 confidence 문턱값의 복제 불일치만 잡습니다. 거리 산식·연속 프레임 조건 등 동작 수준의 동등성은 실기기 시나리오 검증(dev 개선 계획서 §2 "동일 입력 프레임에서 서버/단말 위험 등급 비교")이 필요합니다.

---

## 6. 후속 로드맵

| 단계 | 내용 |
| --- | --- |
| 1 (본 초안) | 문서 계약 + 회귀 테스트로 복제 불일치 차단 |
| 2 | 기계가독 단일 소스(예: `shared/risk_rules.json`)를 서버 import·단말 codegen으로 소비 (TH·Mobile 합의 필요) |
| 3 | LiDAR/depth 기반 거리 단일화, 반사 억제 재설계(debounce·재진입 재경보)와 통합. 2026-07-13 단말 `distanceMeters` 우선 계약과 fallback 구조는 적용됐고, 계측용 `거리측정` 버튼은 자체 세션 내부 동기화 프리뷰로 개선됐다. 남은 조건은 객체 탐지 프레임 기준 video+depth 동기화 검증이다 |
