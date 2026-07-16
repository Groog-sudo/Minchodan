# 반사 위험도 SSOT 계약

> **작성일**: 2026-07-14
> **버전**: v0.3.0 (2026-07-16 Option A: 서버 게이트는 class-agnostic 실행. `HIGH_RISK_CLASSES`는 단말 confidence SSOT 참조용으로 유지)
> **근거**: [`docs/ops/dev_8b2f606_improvement_plan.md`](../ops/dev_8b2f606_improvement_plan.md) §2, [`docs/research/outdoor_guidance_refinement_roadmap.md`](../research/outdoor_guidance_refinement_roadmap.md) Option A
> **적용 대상**: 서버 반사 게이트(`server/detection/gates/reflex_gate.py`)와 단말 온디바이스 게이트(`client/src/components/CameraView.tsx`)

---

## 1. 문제 정의

서버와 단말이 위험 판정 규칙을 **각자 하드코딩으로 복제**하면 동일 프레임에 대한 판정이 어긋납니다. 본 문서는 (1) 단말 온디바이스용 클래스·confidence SSOT와 (2) 서버 class-agnostic 게이트 실행 상수를 구분해 계약으로 고정합니다.

---

## 2. SSOT 대상 A: 고위험 클래스와 최소 confidence (단말 온디바이스 + 서버 참조 테이블)

아래 29종은 서버 `HIGH_RISK_CLASSES`(참조 테이블)와 단말 `CLASS_MIN_CONFIDENCE`가 **항상 동일한 값**을 가져야 합니다. 변경 시 같은 커밋에서 양쪽을 함께 수정합니다.

> **중요 (2026-07-16)**: 서버 `reflex_gate()` **본문은 이 표로 분기하지 않습니다.** 서버 실행 경로는 §2-B입니다. 본 표는 단말 온디바이스 필터·회귀 테스트·향후 Option B 재도입 시 복원 지점으로 유지합니다.

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

## 2-B. SSOT 대상 B: 서버 class-agnostic 게이트 (Option A 실행 경로)

| 상수 | 값 | 설명 |
| --- | --- | --- |
| `AGNOSTIC_MIN_CONFIDENCE` | 0.35 | 존재 신뢰도 하한 |
| `CENTER_X_MIN` / `CENTER_X_MAX` | 0.30 / 0.70 | 가로 중앙 40% |
| `MIN_AREA_RATIO` | 0.10 | bbox/프레임 면적 하한 |
| `MIN_HIT_COUNT` | 3 | ByteTrack 연속 프레임 |
| `SUPPRESS_ALERT_ID` | `high_obstacle` | 억제 키 (방향 제외) |
| `class_name` (경보) | `obstacle` | 반사 페이로드 고정명 |

변경 시 `reflex_gate.py`와 본 절·`tests/test_detection.py`를 같은 커밋에서 갱신합니다.

---

## 3. 플랫폼별 확장 허용 영역 (일치 불요, 명시 필수)

| 영역 | 현황 | 계약 |
| --- | --- | --- |
| 단말 전용 추가 confidence 하한 | `roadway` (0.35), `fire_hydrant`, `parking_meter`, `traffic_light`, `traffic_light_controller`, `traffic_sign`, `stop` (각 0.55) | 단말 실내 오탐 완화 전용 확장으로 허용. 단, **§2의 29종 값과 충돌하는 항목을 추가할 수 없다** |
| 거리 추정 산식 | 서버: bbox 하단 y 기반 의사 거리(`1.5 - ratio*1.1`, `reflex_gate.py`) / 단말: `distanceMeters`가 있으면 LiDAR 실거리 우선, 없으면 면적 기반 `0.22/sqrt(areaRatio)`(`CameraView.tsx`) 및 기존 면적 기반 반사 게이트로 fallback | **현재 불일치 상태를 인지된 기술 부채로 명시**. 단말은 LiDAR 값이 들어오는 경우 0.5/1.0/1.5/3.0m 임계값으로 우선 판정한다. 계측용 `거리측정` 버튼은 자체 `DepthProbeBridge` 세션 안에서 video+depth를 동기화하고, 동기화된 `cameraCalibrationData`의 렌즈 왜곡 LUT와 `intrinsicMatrix`를 이용해 원본 z축 depth를 카메라-표면 광선 거리로 보정한다. 정식 수렴 조건은 탐지 video frame과 depth map의 동일 세션·동일 타임스탬프·동일 640x640 crop 좌표계 및 보정 거리의 실기기 줄자 검증이다. 그 전까지 서버/단말 발동 거리 동등성은 시나리오로 검증한다 |
| 방향 판정 | 서버 `direction.py` FRONT_BAND / 단말 자체 판정 | 좌표계 기준(카메라 프레임)이 동일하므로 허용. 착용 방식 확정 시 재검토 |
| 단말-서버 디듀프 | 서버 연결 시 단말 로컬 반사 억제(`isServerTimeout`) + 서버 `AlertSuppressor` | architecture 포스트 D 잔여(통일 억제키 문서화) |

---

## 4. 변경 절차

1. §2 표의 값 변경은 서버 참조 테이블·단말 코드를 **같은 커밋**에서 수정하고 본 문서 §2 표를 함께 갱신합니다.
2. §2-B 상수 변경은 `reflex_gate.py`와 본 절·게이트 단위 테스트를 함께 갱신합니다.
3. 커밋 전 회귀 테스트 `tests/test_risk_ssot.py`(§5)가 §2 양측 일치 여부를 자동 검증합니다.
4. 파일 소유권은 [`docs/mobile/ios_android_bifurcation_contract.md`](../mobile/ios_android_bifurcation_contract.md) §3을 따릅니다.

---

## 5. 자동 검증

`tests/test_risk_ssot.py`가 다음을 검증합니다.

| 검증 항목 | 방법 |
| --- | --- |
| 서버 29종 클래스·confidence == 본 문서 §2 | `reflex_gate.HIGH_RISK_CLASSES` import 대조 |
| 단말 29종 클래스·confidence == 본 문서 §2 | `CameraView.tsx`의 `CLASS_MIN_CONFIDENCE` 텍스트 파싱 대조 |
| 단말 확장 목록이 §2와 충돌하지 않음 | 교집합 값 비교 |

> **한계**: 본 테스트는 confidence 문턱값의 복제 불일치만 잡습니다. §2-B 지오메트리·hit_count 동등성은 `tests/test_detection.py`와 실기기 시나리오로 검증합니다.

---

## 6. 후속 로드맵

| 단계 | 내용 |
| --- | --- |
| 1 (본 계약) | §2 단말 SSOT + §2-B 서버 class-agnostic 실행 계약 |
| 2 | 기계가독 단일 소스(예: `shared/risk_rules.json`)를 서버 import·단말 codegen으로 소비 |
| 3 | LiDAR/depth 기반 거리 단일화, 포스트 D 억제키 완전 정렬 |
| 대안 | Option B(T1/T2/T3) 재도입 시 §2를 게이트 분기에 다시 연결하고 §2-B를 대체 |
