# 반사 위험도 SSOT 계약

> **작성일**: 2026-07-14
> **버전**: v0.4.0 (2026-07-18 거리 정책 SSOT 1단계 완료: `server/detection/distance_policy.py` 도입 - bbox 클리핑·area_ratio·Near/Medium/Far 히스테리시스·하단 override·route 결정을 순수 함수로 분리하고 §2-C로 신설. §2-B의 `MIN_AREA_RATIO`/`SMALL_OBJECT_MIN_AREA_RATIO`는 §2-C로 이관되어 `reflex_gate.py`가 더 이상 자체 계산하지 않음. 근거 문서: `docs/research/lidar_fusion_sequencing_plan.md` §3 + 기존 v0.3.0 이력 유지: 2026-07-16 Option A - 서버 게이트는 class-agnostic 실행. `HIGH_RISK_CLASSES`는 단말 confidence SSOT 참조용으로 유지)
> **근거**: [`docs/ops/dev_8b2f606_improvement_plan.md`](../ops/dev_8b2f606_improvement_plan.md) §2, [`docs/research/outdoor_guidance_refinement_roadmap.md`](../research/outdoor_guidance_refinement_roadmap.md) Option A, [`docs/research/lidar_fusion_sequencing_plan.md`](../research/lidar_fusion_sequencing_plan.md) §3(1단계)
> **적용 대상**: 서버 반사 게이트(`server/detection/gates/reflex_gate.py`), 거리 정책 SSOT(`server/detection/distance_policy.py`), 단말 온디바이스 게이트(`client/src/components/CameraView.tsx`)

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
| `MIN_HIT_COUNT` | 3 | ByteTrack 연속 프레임 |
| `SUPPRESS_ALERT_ID` | `high_obstacle` | 억제 키 (방향 제외) |
| `class_name` (경보) | `obstacle` | 반사 페이로드 고정명 |

> **2026-07-18**: 이전 버전의 `MIN_AREA_RATIO`/`SMALL_OBJECT_MIN_AREA_RATIO`(거리·하단 override 판정)는
> §2-C 거리 정책 SSOT(`distance_policy.py`)로 이관됐습니다. `reflex_gate.py`는 더 이상 자체 면적비를
> 계산하지 않고 `Detection.route == "reflex"`(= `effective_distance_zone == "near"`)만 소비합니다.

변경 시 `reflex_gate.py`와 본 절·`tests/test_detection.py`를 같은 커밋에서 갱신합니다.

---

## 2-C. SSOT 대상 C: 거리 정책 (Near/Medium/Far, route) — `distance_policy.py`

2026-07-18 도입. `server/detection/distance_policy.py`가 bbox 클리핑, area_ratio/bottom_ratio,
Near/Medium/Far 구역 판정(히스테리시스 포함), 하단 소형 장애물 override, route(reflex/cognitive)
결정을 순수 함수로 제공합니다. `ByteTrackTracker.update()`가 track별 이전 구역을 Redis에서
읽어 매 프레임 `Detection`에 결과를 부착하므로, 반사 게이트(§2-B)와 인지 거리 분류
(`direction.py::estimate_distance()`)가 **동일한 경계값**을 공유합니다.

| 상수 | 값 | 설명 |
| --- | --- | --- |
| `NEAR_ENTER_AREA_RATIO` | 0.10 | Medium→Near 진입 (신규 트랙 기본 판정에도 사용) |
| `NEAR_EXIT_AREA_RATIO` | 0.08 | Near→Medium 이탈 (히스테리시스) |
| `MEDIUM_ENTER_AREA_RATIO` | 0.03 | Far→Medium 진입 |
| `MEDIUM_EXIT_AREA_RATIO` | 0.025 | Medium→Far 이탈 (히스테리시스) |
| `BOTTOM_OVERRIDE_MIN_BOTTOM_RATIO` | 0.80 | 하단 소형 장애물 override 조건(위치) |
| `BOTTOM_OVERRIDE_MIN_AREA_RATIO` | 0.04 | 하단 소형 장애물 override 조건(최소 면적비) |
| `HEURISTIC_COEFFICIENT` / `HEURISTIC_MIN_M` / `HEURISTIC_MAX_M` | 0.22 / 0.3 / 3.0 | `heuristic_distance_m = clamp(0.22/sqrt(area_ratio), 0.3, 3.0)` |
| `POLICY_VERSION` | `distance-alert-v1` | 서버·클라이언트 정책 버전 로그 비교용 |

**route 불변식**: `effective_distance_zone == "near"`만 `route == "reflex"`이고, Medium/Far는
`route == "cognitive"`입니다. 일반 객체(§2-B)는 Near가 아니면 구조적으로 `reflex_gate()`가
`None`을 반환하므로 Medium/Far 일반 객체 반사가 발생하지 않습니다(안전 예외 `head_level`/
`surface`는 §2-B와 별도로 자체 조건으로 발동하며 이 route 불변식의 대상이 아닙니다).

**단말 대응값**: `client/src/components/CameraView.tsx`의 `URGENT_AREA_RATIO`(0.10)와
`LOCAL_NEAR_LIDAR_METERS`(0.7m)가 위 `NEAR_ENTER_AREA_RATIO`와 동일 경계를 수동으로 동기화해
사용합니다(코드 생성기 없이 §4 변경 절차로 동기화 - §6 로드맵 2단계 참조).

변경 시 `distance_policy.py`, `tests/test_distance_policy.py`, `reflex_gate.py`,
`CameraView.tsx`의 대응 상수, 본 절을 같은 커밋에서 갱신합니다.

---

## 3. 플랫폼별 확장 허용 영역 (일치 불요, 명시 필수)

| 영역 | 현황 | 계약 |
| --- | --- | --- |
| 단말 전용 추가 confidence 하한 | `roadway` (0.35), `fire_hydrant`, `parking_meter`, `traffic_light`, `traffic_light_controller`, `traffic_sign`, `stop` (각 0.55) | 단말 실내 오탐 완화 전용 확장으로 허용. 단, **§2의 29종 값과 충돌하는 항목을 추가할 수 없다** |
| 거리 추정 산식 | 서버: §2-C `distance_policy.py`의 `heuristic_distance_m`(`0.22/sqrt(area_ratio)` clamp) / 단말: `distanceMeters`가 있으면 LiDAR 실거리 우선(Near 경계 0.7m), 없으면 면적 기반 Near 전용 폴백(`URGENT_AREA_RATIO=0.10`, `CameraView.tsx`) | 2026-07-18: 서버 반사 게이트의 자체 의사거리 공식(`1.5 - ratio*1.1`)을 폐기하고 §2-C `heuristic_distance_m`으로 통합했다. 단말 로컬 폴백도 Medium/Far 단계를 제거해 Near 경계를 §2-C와 맞췄다. **다만 LiDAR 실시간 bbox 융합(상시 fusion)은 여전히 별도 2단계 과제**이며, 계측용 `거리측정` 버튼은 자체 `DepthProbeBridge` 세션에서만 동작한다(`docs/research/lidar_fusion_sequencing_plan.md` §4 참조) |
| 방향 판정 | 서버 `direction.py` FRONT_BAND / 단말 자체 판정 | 좌표계 기준(카메라 프레임)이 동일하므로 허용. 착용 방식 확정 시 재검토 |
| 단말-서버 디듀프 | 서버 연결 시 단말 로컬 반사 억제(`isServerTimeout`) + 서버 `AlertSuppressor`(2026-07-18: 억제 키에 `alert_source` 포함) | architecture 포스트 D 잔여(통일 억제키 문서화) |

---

## 4. 변경 절차

1. §2 표의 값 변경은 서버 참조 테이블·단말 코드를 **같은 커밋**에서 수정하고 본 문서 §2 표를 함께 갱신합니다.
2. §2-B 상수 변경은 `reflex_gate.py`와 본 절·게이트 단위 테스트를 함께 갱신합니다.
3. §2-C 상수(거리 경계값) 변경은 `distance_policy.py`, `tests/test_distance_policy.py`,
   `CameraView.tsx`의 대응 상수, 본 절을 같은 커밋에서 갱신합니다.
4. 커밋 전 회귀 테스트 `tests/test_risk_ssot.py`(§5)가 §2 양측 일치 여부를 자동 검증합니다.
5. 파일 소유권은 [`docs/mobile/ios_android_bifurcation_contract.md`](../mobile/ios_android_bifurcation_contract.md) §3을 따릅니다.

---

## 5. 자동 검증

`tests/test_risk_ssot.py`가 다음을 검증합니다.

| 검증 항목 | 방법 |
| --- | --- |
| 서버 29종 클래스·confidence == 본 문서 §2 | `reflex_gate.HIGH_RISK_CLASSES` import 대조 |
| 단말 29종 클래스·confidence == 본 문서 §2 | `CameraView.tsx`의 `CLASS_MIN_CONFIDENCE` 텍스트 파싱 대조 |
| 단말 확장 목록이 §2와 충돌하지 않음 | 교집합 값 비교 |

> **한계**: 본 테스트는 confidence 문턱값의 복제 불일치만 잡습니다. §2-B 지오메트리·hit_count 동등성은 `tests/test_detection.py`와 실기기 시나리오로, §2-C 거리 정책 순수 함수(히스테리시스·override·route)는 `tests/test_distance_policy.py`로 검증합니다.

---

## 6. 후속 로드맵

| 단계 | 내용 | 상태 |
| --- | --- | --- |
| 1 (본 계약) | §2 단말 SSOT + §2-B 서버 class-agnostic 실행 계약 | 완료 |
| 2 | 기계가독 단일 소스를 서버 import·단말 codegen으로 소비 | **부분 완료(2026-07-18)**: 서버 측 순수 함수 SSOT(`distance_policy.py`, §2-C)는 완료. 단, JSON 정본(`shared/risk_rules.json`)과 TS 자동 생성기는 아직 없고, §2 방식(수동 값 동기화 + 텍스트 파싱 회귀 테스트)을 그대로 따른다 - `tests/test_distance_policy.py`가 서버 측 경계값만 검증하며, 단말 `URGENT_AREA_RATIO`/`LOCAL_NEAR_LIDAR_METERS`와의 자동 교차검증은 아직 없다(§5 한계와 동일 성격의 후속 과제) |
| 3 | LiDAR/depth 기반 거리 단일화, 포스트 D 억제키 완전 정렬 | 미착수 - `docs/research/lidar_fusion_sequencing_plan.md` §4(2단계)에서 별도 재설계 예정 |
| 대안 | Option B(T1/T2/T3) 재도입 시 §2를 게이트 분기에 다시 연결하고 §2-B를 대체 | - |
