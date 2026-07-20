# LiDAR 실시간 융합 설계서 v2 (온디맨드 유지 결정)

> **작성일**: 2026-07-19
> **버전**: v2.2.0 (2026-07-19 §4.4 신설 - 외부 문서(GPT 5.6 추론)의 근거리 정확도 제안을 §4.3 실측·현재 아키텍처와 교차 검증. LiDAR 프레이밍 정확도 목표를 area_ratio 휴리스틱 구역 분류 기준으로 재해석, 독립 도출된 Near/Medium 경계 일치 확인, 거리값 다중 프레임 평활화 미구현 갭 식별. §7에 후속 실기기 테스트 체크리스트 추가 + 기존 v2.1.0 이력 유지: §4.3 신설 - 팀원 현장 실측(0.3m/0.5m/1.0m) 캘리브레이션 결과 및 LiDAR ToF 센서 최소 유효 거리 가설 추가, §4.2에 고정 지점 캡처(fixed_point_probe_sample) 기능 반영)
> **상태**: 확정 (2단계 완료, 4단계 보류)
> **대체 대상**: `LiDAR_distanceMeters.md`(원 요청서, 저장소 미추적, `/Users/kwanbum/Downloads/`) - 본 문서가 정본이다.
> **선행 문서**: [`docs/research/lidar_fusion_sequencing_plan.md`](lidar_fusion_sequencing_plan.md) §4(2단계 실행 지시), [`docs/design/risk_ssot_contract.md`](../design/risk_ssot_contract.md) §2-C(거리 정책 SSOT 1단계)

---

## 1. 배경

원 요청서(`LiDAR_distanceMeters.md`)는 `distanceMeters`(LiDAR 실측)를 `<=0.5m/1.0m/1.5m/3.0m` 4단계로 Critical/High/Mid/Low 반사에 매핑하고, `DepthFusionCaptureBridge.swift`(상시 video+depth 동기화)로 실시간 융합을 구현할 것을 제안했다.

거리 정책 SSOT 1단계(`docs/research/lidar_fusion_sequencing_plan.md` §3)가 "일반 객체는 Near만 반사, Medium/Far는 인지"라는 불변식을 서버에 확정한 뒤, 이 문서는 그 불변식과 충돌하지 않도록 LiDAR의 역할을 재정의한다. 또한 네이티브 세션 충돌 스파이크(§5)를 실제로 수행해 실시간 융합의 기술적 실현 가능성을 검증했다.

**최종 결정**: 실시간 상시 융합(`DepthFusionCaptureBridge.swift`)은 보류하고, 기존 온디맨드 `거리측정` 토글(`DepthProbeBridge.swift`, vision-camera와 배타 실행)을 그대로 유지한다. 근거는 §5·§6 참조.

---

## 2. 폐기한 내용

| 원문 제안 | 폐기 사유 |
| :--- | :--- |
| `<=0.5m` Critical, `<=1.0m` High, `<=1.5m` Mid, `<=3.0m` Low 4단계 반사 매핑 | Near 전용 반사 원칙과 정면 충돌. 1단계에서 없앤 "Medium/Far도 비프"를 LiDAR로 재도입하게 됨 |
| Reflex Gate가 `distanceMeters` 유무로 판단 경로 자체를 분기 | 판단 정본이 area_ratio 기반 정책(`distance_policy.py`)에서 LiDAR 유무로 갈라져 이중 정본이 생김 - `reflex_gate.py`는 1단계에서 이미 `Detection.route`만 소비하도록 축소됨 |
| `DepthFusionCaptureBridge.swift`(상시 video+depth 동기화)를 즉시 구현 | §5 스파이크에서 vision-camera 세션 확장이 불가능함을 실측 확인. 세션 전체 재작성이 필요한 대규모 작업으로, "helper 함수 추가" 수준이라는 원 제안의 리스크 평가가 부정확했다 |

---

## 3. 유지·재설계한 내용

| 항목 | 상태 |
| :--- | :--- |
| `DetectionResult.distanceMeters`/`distanceSource`/`depthSampleCount`/`depthAccuracy` 등 4개 필드 | `client/src/types/detection.ts`에 이미 선언되어 있으므로 타입 변경 불필요. 온디맨드 검증 캡처(`거리측정` 모드)에서만 채워짐 |
| bbox 내부 샘플링 정책(중앙 50%, 7x7 grid, 25 percentile, 유효 샘플 8개 미만이면 null) | 그대로 유지 - `DepthProbeBridge.swift:probeBoxes()`. 순수 계측 로직이라 정책과 충돌하지 않음 |
| UI 표시(`car 0.52m LiDAR (87%)`) | 유지 - 표시 형식은 라우팅 정책과 무관 |
| 클라이언트 로컬 폴백에서 LiDAR 우선 사용 | 유지하되 범위 축소 - `CameraView.tsx`의 `applyLocalAreaReflex()`가 LiDAR 값이 있으면 area_ratio보다 우선 사용하는 구조는 유지하되, Near 경계(0.7m) 밖은 무출력으로 축소(1단계 커밋 `c3fd286` 참조) |

---

## 4. LiDAR의 역할: 실시간 라우팅 관여 없는 자문(advisory) 신호

### 4.1 서버 - 온디맨드 검증 캡처 전용

LiDAR 값은 서버의 반사/인지 실시간 라우팅(`server/detection/gates/reflex_gate.py`, `detection_pipeline.py`)에 **전혀 관여하지 않는다.** 관여하는 유일한 지점은 온디맨드 "거리측정 → 검증 캡처" 흐름이다.

```mermaid
flowchart LR
    A["거리측정 모드 ON<br/>(vision-camera OFF)"] --> B["검증 캡처 버튼"]
    B --> C["정지 프레임을 detection 경로로 전송"]
    C --> D["서버 YOLO 추론<br/>(server_detection 응답)"]
    D --> E["단말이 같은 bbox로<br/>probeBoxes() 호출"]
    E --> F["distance_probe_sample 전송<br/>(LiDAR meters만)"]
    F --> G["서버: heuristic_distance_class<br/>(area_ratio 기반, 정본)"]
    F --> H["서버: lidar_distance_zone<br/>(zone_from_lidar_meters, 자문)"]
    G --> I["lidar_distance_validation_samples 저장"]
    H --> I
    I --> J["scripts/analyze_lidar_validation.py<br/>구역 혼동 행렬"]
```

`server/detection/distance_policy.py:zone_from_lidar_meters()`가 area_ratio 경계값(0.10/0.08/0.03/0.025)을 `heuristic_distance_m` 공식의 역산으로 미터 경계(약 0.696m/0.778m/1.270m/1.391m)로 변환해 LiDAR 실측을 같은 스케일의 구역으로 매핑한다. 상태(히스테리시스)가 없는 단발 캡처이므로 진입 경계만 사용한다.

`server/services/lidar_validation_service.py:persist_distance_probe_samples()`가 `heuristic_distance_class`(area_ratio 정본)와 `lidar_distance_zone`(LiDAR 자문)을 나란히 `lidar_distance_validation_samples` 테이블에 저장하고, `scripts/analyze_lidar_validation.py`가 둘의 혼동 행렬을 출력한다(원 계획서 §13.4 "구역 혼동 행렬" 요구사항 충족). 임곗값 해석과 정책 조정 여부는 담당자가 직접 판단한다 - 스크립트는 집계만 수행한다.

### 4.2 클라이언트 - 서버 연결 끊김 시 로컬 폴백에서만 사용

`CameraView.tsx`의 `applyLocalAreaReflex()`(서버 타임아웃 시에만 활성화되는 온디바이스 폴백)는 LiDAR 값이 있으면 area_ratio보다 우선 사용하되, Near 경계(`LOCAL_NEAR_LIDAR_METERS=0.7m`, `LOCAL_NEAR_CRITICAL_LIDAR_METERS=0.5m`) 밖은 무출력이다. 이 우선순위는 "거리측정" 모드가 아니라 평소 반사 프레임 처리 중 `resolveDetectionDistance()`가 온디바이스 탐지 결과에 LiDAR 필드가 채워져 있을 때만 동작하며, 현재 온디바이스 추론 경로에는 LiDAR 값이 채워지지 않으므로(§5 참조) 사실상 area_ratio 경로만 실행된다.

2026-07-19 추가: 객체 탐지 결과와 무관하게, 거리측정 화면에 항상 표시되는 고정 3지점(중앙/전방 하단/발밑, `DEPTH_PROBE_POINTS`)의 LiDAR 실측도 "검증 캡처" 버튼 한 번으로 함께 저장한다(`fixed_point_probe_sample` 메시지 → `lidar_fixed_point_samples` 테이블). YOLO 탐지가 필요 없어 서버 왕복 없이 클라이언트가 이미 보유한 `probeDepth()` 결과를 그대로 보고하며, 줄자 대조가 객체 탐지 성공 여부에 좌우되지 않는다.

### 4.3 실측 캘리브레이션 결과 (2026-07-19 현장 테스트)

팀원이 카메라 렌즈에서 벽면(중앙 마커 지점)까지의 직선 거리를 줄자로 실측하며 0.3m/0.5m/1.0m 세 구간에서 검증 캡처를 진행했다. `lidar_fixed_point_samples`/`lidar_distance_validation_samples`에 저장된 실제 값은 다음과 같다.

| 실측(줄자) | LiDAR 읽음값 | 오차 |
| :---: | :--- | :--- |
| **0.3m** | 1.43 ~ 1.58m | **약 +377 ~ +427%** (4.8 ~ 5.3배) |
| **0.5m** | 0.554 ~ 0.640m | +11 ~ +28% |
| **1.0m** | 0.975 ~ 1.073m | -2.5 ~ +7.3% (거의 정확) |

0.5m·1.0m 구간은 §7(재검토 조건 이전 가설)에서 예상한 "근거리일수록 RGB-LiDAR 시차가 커진다"는 패턴과 방향이 일치하지만, 0.3m 구간의 4.8~5.3배 오차는 단순 시차로는 설명할 수 없는 규모다. 가장 유력한 설명은 **LiDAR ToF 센서의 최소 유효 측정 거리 미만 진입**이다 - 스마트폰 LiDAR/ToF 센서는 일반적으로 약 0.3~0.5m 아래로 내려가면 위상 기반 거리 계산이 랩어라운드(위상 겹침)를 일으켜, 실제로는 가까운데 오히려 훨씬 먼 값으로 튀는 현상이 알려져 있다. 이는 `DepthProbeBridge.swift`의 소프트웨어 계산 결함이 아니라 센서 하드웨어 자체의 근접 한계일 가능성이 크다.

**실무적 함의**: 서버 반사 게이트는 이미 §4.1대로 LiDAR가 아닌 area_ratio 휴리스틱만 실시간 판단에 사용하므로, 이 근접 구간(<0.5m) 오류가 실제 안전 판단에는 영향을 주지 않는다. 오히려 이 실측 결과는 §5~§6의 "LiDAR를 실시간 근접 판단(4단계)에 쓰지 않는다"는 결정을 추가로 뒷받침한다 - 안전이 가장 중요한 최근접 구간에서 LiDAR 원시값 자체가 가장 신뢰할 수 없다는 것이 실측으로 확인됐기 때문이다.

**한계**: 표본이 각 구간 1~7건으로 적어 통계적으로 확정하기는 이르다. 정식 보정 계수 도입 전 각 구간(특히 0.3~0.5m 경계)에서 추가 표본 확보가 필요하다.

### 4.4 안전 기준 검토 - 외부 문서(GPT 5.6 추론) 정확도 제안 대조 (2026-07-19)

사용자가 외부 LLM(GPT 5.6)이 작성한 "근거리 오차 허용 기준" 제안 문서를 전달했다. 실제 코드·§4.3 실측 데이터와 교차 검증한 결과를 기록한다.

**원문서 핵심 제안**:

| 실제 거리 | 목표 오차 | 용도 |
| :--- | ---: | :--- |
| 0~0.6m | ±5~10cm | 즉시 정지·강한 햅틱 |
| 0.6~1.2m | ±10~15cm | 긴급 회피 안내 |
| 1.2~2.0m | ±20cm 또는 10% | 방향 변경 준비 |
| 2m 이상 | ±30cm 또는 15% | 사전 인지 안내 |

보행 속도(1.0~1.2m/s)와 시스템 지연(300ms)을 곱하면 지연 시간 동안 사용자가 30~36cm 이동하므로, 근거리 반사 경보에는 ±30cm급 오차가 너무 크다는 논리로 "즉시 정지 ~0.6m, 회피 안내 시작 1.2~1.5m"를 도출했다. 위험 방향 비대칭(멀게 오판 > 가깝게 오판), 다중 프레임 평활화, 불확실 시 보수적(가깝게) 판정, 경보 경계 안전 여유, 검정 표면·유리·역광·카메라 기울기 등 다중 조건 검증, 최종 배포 전 시각장애인 당사자·보행지도사 감독 하 사용자 시험을 권고했다.

**핵심 불일치**: 원문서의 정확도 표는 "LiDAR 연속 거리값이 반사 경보를 직접 구동한다"는 전제다. Minchodan의 반사 게이트는 §4.1대로 **LiDAR를 실시간 판단에 전혀 쓰지 않고 area_ratio 휴리스틱만 사용**하며, LiDAR는 온디맨드 검증 캡처의 자문 신호로 한정된다(§5~§6 3단계 스파이크로 확정). 게다가 §4.3 실측으로 **LiDAR 자체가 0~0.6m 구간에서 가장 신뢰할 수 없다**는 것이 확인됐다. 따라서 "LiDAR ±5~10cm" 기준을 그대로 우리 반사 경로의 합격 기준으로 채택할 수 없다 - 검증 대상을 **area_ratio 휴리스틱의 구역(Near/Medium/Far) 분류 정확도**로 재해석해야 실질적이다.

**독립 교차검증(긍정적 일치)**: 원문서가 지연시간 계산으로 도출한 "즉시 정지 ~0.6m / 회피 안내 시작 1.2~1.5m"는, `docs/design/risk_ssot_contract.md` §2-C가 완전히 다른 근거(원 감사 문서의 알림 피로 분석)로 이미 확정한 `distance_policy.py`의 Near 진입(area_ratio 0.10 ≈ 0.696m)·Medium 진입(area_ratio 0.03 ≈ 1.27m) 경계와 상당히 근접한다. 서로 독립적으로 도출된 두 기준이 방향이 일치한다는 것은 기존 경계값 선택이 안전공학적으로도 합리적이라는 교차검증으로 볼 수 있다.

**이미 반영된 안전 설계**:
- **위험 방향 비대칭**: `DepthProbeBridge.swift:probeBoxes()`가 유효 depth 샘플의 중앙값이 아니라 **25퍼센타일**(더 가까운 쪽)을 쓴다 - "멀게 오판하지 않는다"는 원칙과 이미 같은 방향.
- **불확실 시 보수적 처리**: `minimumValidSamples=8` 미만이면 거리값을 아예 `null` 처리(불확실한 근접값을 함부로 내지 않음).
- **다중 프레임 존재-지속성 필터**: `MIN_HIT_COUNT`(정적 4프레임/접근 2프레임) + `apply_hysteresis()`의 진입·이탈 경계 분리가 원문서의 "다중 프레임 확인" 취지와 유사하게 단일 프레임 노이즈로 인한 반사 깜빡임을 억제한다.

**실제 갭 - 미반영**: 원문서가 말하는 "최근 3~5프레임 중앙값" 평활화는 위 `MIN_HIT_COUNT`(객체의 존재 지속성 필터)와는 다른 것이다 - **area_ratio 또는 heuristic_distance_m 값 자체를 여러 프레임에 걸쳐 평활화하는 로직은 현재 없다.** 단일 프레임의 순간적인 bbox 크기 변동(세그멘테이션/탐지 경계 노이즈)이 area_ratio를 그대로 흔들 수 있다는 뜻이다. 도입한다면 `ByteTrackTracker`가 이미 track별 상태(Redis 컨텍스트)를 관리하고 있으므로 그 계층에 최근 N프레임 area_ratio 이동중앙값을 추가하는 것이 아키텍처상 자연스러운 위치다.

**재해석한 Minchodan 합격 기준(제안, 미확정)**:

```text
0.5~1.0m 벽 실측(area_ratio 기반 구역 분류 기준):
  - 실측 0.5~0.7m 구간에서 effective_distance_zone == "near" 판정 비율 95% 이상
  - 실측이 Near 경계(약 0.7m)보다 먼데 near로 오분류(위험 방향 아님, 과잉 경보) < 허용
  - 실측이 Near 경계보다 가까운데 near로 미분류(위험 방향, 반사 누락) 0%에 근접해야 함
  - 탐지 실패 시 즉시 정지가 아니라 무경보로 빠지지 않는지 별도 확인(안전 게이트 fallback)
```

이는 §4.3의 LiDAR 캘리브레이션 표와는 별개로, **area_ratio 휴리스틱 자체를 줄자와 직접 대조**하는 새로운 검증 축이 필요함을 의미한다(§8 재검토 조건에 반영).

**채택 - 향후 실기기 테스트 체크리스트에 반영**: 벽 단일 표면 테스트로는 불충분하다는 지적은 타당하다. 검정 표면(저반사), 유리(투과/반사 혼입), 얇은 기둥(작은 area_ratio), 사람(비정형 형태), 야외 직사광(온디바이스 카메라 노출), 카메라 기울기(비수직 촬영 각도)를 별도 조건으로 검증해야 한다는 점을 후속 테스트 계획에 반영한다.

**보류 - 이번 범위 밖**: 시각장애인 당사자·보행지도사 감독 하 통제 환경 사용자 시험은 실제 배포 전 반드시 필요한 게이트이나, 현재 세션의 기술 검증 범위를 벗어난다(별도 프로젝트 단계로 명시).

---

## 5. 네이티브 세션 충돌 스파이크 (완료, 2026-07-19)

### 5.1 조사 방법

`client/node_modules/react-native-vision-camera`(v4.7.3) Swift 소스를 직접 열람해 세션 소유권과 확장 가능 지점을 확인했다.

### 5.2 결론

| 확인 항목 | 결과 |
| :--- | :--- |
| `CameraSession.captureSession`(`ios/Core/CameraSession.swift:22`) | `let captureSession = AVCaptureSession()` - 접근제어자 없음(`internal`). VisionCamera 모듈 밖에서 접근 불가 |
| `CameraView.cameraSession`(`ios/React/CameraView.swift:101`) | `var cameraSession = CameraSession()` - 동일하게 `internal` |
| `ReflexFrameProcessorPlugin`이 상속하는 `FrameProcessorPlugin` | Objective-C 기반(`ios/FrameProcessors/FrameProcessorPlugin.h/.m`), 이미 캡처된 `Frame`을 콜백으로만 받음. 세션 구성 API 없음 |
| `VisionCameraProxyHolder` | 순수 JS 워클릿 호스트 브릿지. 카메라 세션과 무관 |

**"vision-camera가 이미 쓰는 세션에 depth output만 추가"하는 저위험 경로는 실현 불가능하다.** 이는 설계 판단이 아니라 Swift 접근제어자로 막힌 하드 제약이다.

### 5.3 영향 범위

세션을 실제로 공유하려면 vision-camera의 세션 관리(`CameraSession`, `CameraView` 전체)를 대체하는 자체 `AVCaptureSession` 구현이 필요하다. 이는 다음을 모두 포함하는 대규모 재작업이다.

- `ReflexFrameProcessorPlugin.swift`가 의존하는 프레임 캡처 파이프라인 전체 교체
- 카메라 프리뷰 렌더링, 줌/포커스/오리엔테이션 등 vision-camera가 현재 제공하는 기능의 재구현 또는 포기
- 반사 경로 목표 지연(p95 300ms, 이미 실측 검증됨)에 대한 회귀 위험

### 5.4 성능 영향

세션 재작성 없이는 측정 자체가 불가능하므로 미실시. `DepthProbeBridge.swift` 자체 주석이 이미 "계측 전용이므로 VGA 프리셋으로 충분(전력/발열 최소화)"라고 명시한 점을 볼 때, LiDAR 심도 캡처를 반사 fps(8~10fps)로 상시 구동하는 것은 별도의 열/전력 검증이 필요하다.

---

## 6. 4단계 결정: 보류

| 스파이크 결과 | 진행 방향 |
| :--- | :--- |
| 세션 공존 불가 (확인됨) | ~~반사 경로 재설계 포함 대규모 작업으로 재분류~~ → **온디맨드 토글 유지로 최종 결정** (사용자 확정, 2026-07-19) |

`DepthFusionCaptureBridge.swift`는 구현하지 않는다. 기존 `DepthProbeBridge.swift`(거리측정 버튼, vision-camera와 배타 실행)를 정본으로 유지하고, LiDAR는 §4의 온디맨드 검증·자문 역할로 한정한다.

---

## 7. 재검토 조건

아래 조건 중 하나가 충족되면 이 결정을 재검토한다.

| 조건 | 재검토 내용 |
| :--- | :--- |
| vision-camera가 향후 버전에서 세션 확장 공개 API를 제공 | §5 스파이크를 새 버전 기준으로 재실행 |
| 팀이 vision-camera를 포기하고 자체 카메라 파이프라인으로 전환하기로 별도 결정 | 4단계를 별도 우선순위 프로젝트로 재개 |
| `scripts/analyze_lidar_validation.py` 혼동 행렬에서 area_ratio 휴리스틱의 오분류율이 실사용에 위험한 수준으로 확인 | 온디맨드 자문 신호를 넘어선 보정 계수 적용(예: 클래스별 계수) 검토 - 세션 재작성 없이도 가능한 범위 우선 |

**§4.4 후속 실기기 테스트 체크리스트(미착수)**:

| 항목 | 내용 |
| :--- | :--- |
| area_ratio 대 줄자 직접 대조 | §4.3은 LiDAR 대 줄자만 비교했다. 반사 게이트가 실제로 쓰는 area_ratio 구역 판정(`effective_distance_zone`)을 줄자 실측과 직접 대조하는 별도 테스트가 필요(§4.4 "재해석한 합격 기준" 참조) |
| 다중 표면·조건 검증 | 벽 단일 표면 테스트로는 불충분. 검정 표면(저반사), 유리, 얇은 기둥, 사람, 야외 직사광, 카메라 기울기를 각각 별도로 확인 |
| 거리값 다중 프레임 평활화 | 현재 미구현(§4.4 "실제 갭" 참조). 도입 시 `ByteTrackTracker`의 track 컨텍스트에 최근 N프레임 area_ratio 이동중앙값 추가를 우선 검토 |
| 감독 하 사용자 시험 | 배포 전 필수 게이트이나 별도 프로젝트 단계(§4.4 "보류" 참조) |

---

## 8. 참고 문서

| 문서 | 위치 |
| :--- | :--- |
| `docs/research/lidar_fusion_sequencing_plan.md` | 1~4단계 실행 순서 총괄, §6 최종 결정 반영 |
| `docs/design/risk_ssot_contract.md` | §2-C 거리 정책 SSOT(1단계 산출물) |
| `docs/research/mitos_improvement_roadmap.md` | §2 거리 추정 항목 최신 상태 |
| `server/detection/distance_policy.py` | `zone_from_lidar_meters()`, LiDAR 미터 경계 상수 |
| `LiDAR_distanceMeters.md` | 원 요청서(저장소 미추적). 본 문서로 대체됨 |
