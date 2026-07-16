# 반사 경로 OOD 오탐 디버깅 및 완화 조치 핸드오프

> **작성일**: 2026-07-15
> **버전**: v1.0.0
> **대상**: 반사 경로(Reflex Gate, 즉시 위험 경보) 및 실내 OOD(Out-of-Distribution, 학습 데이터셋 분포 외 환경) 오탐 완화 작업

---

## 오늘 작업 요약

오늘 작업은 네트워크 지연 시 오작동하는 단말기 자체 반사 경로를 안정화하고, 실내 환경에서 차량/오토바이 등으로 인식되는 환각 오탐을 억제하는 데 주력했습니다.

| 작업 항목 | 커밋 해시 | 상세 이력 링크 | 변경 내용 및 상세 설명 |
| :--- | :--- | :--- | :--- |
| **온디바이스 폴백 구현 및 중복 경보 방지** | `1c92d0f` | [stage_safety_reflex.md#a-300ms-초과-타임아웃-감지-및-fail-safe-분기](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#a-300ms-초과-타임아웃-감지-및-fail-safe-분기) | 네트워크 장애 또는 300ms 초과 지연 발생 시 단말기가 자체 비프음/햅틱 경보로 안전하게 **폴백(Fallback, 대체 작동)**하도록 구현했습니다. 서버 복구 시에는 즉각 단말기 경보를 **Suppress(억제, 차단)**하여 중복 경보를 방어했습니다. |
| **반사 경보 연속 발화 개선 및 디바운스 필터 추가** | `d91be14` | [stage_safety_reflex.md#a-반사-경보reflex-clip-연속-발화-원인-분석-및-해결-쿨다운-도입](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#a-반사-경보reflex-clip-연속-발화-원인-분석-및-해결-쿨다운-도입) | 동일 방향 경보 시 최소 3초의 **디바운스/쿨다운(Debounce/Cooldown, 재발화 대기시간)**을 보장하여 사전합성 음성이 겹치지 않게 했습니다. 또한 연속 2프레임 이상 검출될 때만 알림이 작동하는 안정화 필터를 추가했습니다. |
| **TFLite 야외 객체 오탐 원인 분석 및 진단** | `37f6215` | [stage_safety_reflex.md#5-탐지-오류-진단-2026-07-15](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#5-탐지-오류-진단-2026-07-15) | 실내 복도에서 차량/오토바이가 빈발하는 오탐을 역추적하여 TFLite 입력 채널 레이아웃이 모델 요구 사항인 **NHWC(가로-세로-색상 순서)**가 아닌 **CHW(색상-가로-세로 순서)**로 주입되는 채널 불일치 버그를 진단했습니다. |
| **NHWC 전처리 버그 수정 및 class-agnostic 반사 경로 단순화** | `d4d9532` | [stage_safety_reflex.md#7-class-agnostic-반사-경로-판단-로직-단순화](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#7-class-agnostic-반사-경로-판단-로직-단순화) | 전처리 레이아웃을 **NHWC**로 전면 수정하여 이미지 왜곡을 교정했습니다. 또한 특정 사물 분류 명칭을 배제하고 BBox(바운딩 박스)의 중앙 정면 영역(가로 40% 내) 및 면적 비율(8% 이상 근접)만을 확인해 비프/햅틱을 울리는 **class-agnostic(클래스 무관)** 로직으로 판단식을 축소했습니다. |
| **OOD 실내 환경 환각 오탐 완화 대책 적용** | `5ab06c4` | [stage_safety_reflex.md#8-ood-오탐-완화-실내-공간-씬-배제](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#8-ood-오탐-완화-실내-공간-씬-배제) | BBox 면적 내 3x3 점을 샘플링하여 노면 세그멘테이션(인도/차도 등) 폴리곤과 30% 이상 겹치지 않으면 벽이나 천장 등 허공에 나타난 환각으로 판단하여 차단하는 공간 교차검증 게이트를 추가했습니다. 시간적 지속성 필터(4프레임 누적 유지 시 통과) 및 신뢰도 임계값 상향(0.35 → 0.50)을 최종 적용했습니다. |

---

## 미해결 문제

| 미해결 항목 | 현상 및 원인 분석 | 향후 영향 및 조치 필요 사항 |
| :--- | :--- | :--- |
| **구석 물체의 지속적인 환각 및 고신뢰 오탐** | 실내 복도/교실 구석의 책상이나 노트북 등 미학습/애매한 객체들이 여전히 `CAR 93%` 등으로 오탐되어 비프음이 간헐적으로 오발화하는 문제가 남아있습니다. | 모델이 실외 인도 보행용 데이터셋으로만 학습되어 실내 환경이 **OOD(Out-of-Distribution, 분포 외 데이터)**로 분류되기 때문입니다. |
| **정면 외 방향 오발화 현상** | Detection Guidance Log상 "1~2시 방향"으로 판단되는 구석 물체임에도 반사 경보(사전합성 클립)가 발화되는 현상이 있습니다. | `reflex_gate.py` 및 `CameraView.tsx` 내의 BBox 가로 40% 필터(정면 영역) 및 **center_x_norm/area_ratio** 조건 로직에 대한 상세 재검증 및 수정이 필요합니다. |
| **노면 교차검증 게이트의 실내 한계** | 실내에서는 인도(sidewalk), 차도(roadway), 점자블록(braille_normal) 등 노면 세그멘테이션 자체가 전혀 감지되지 않아 `surfaces` 리스트가 완전히 비어 있는 경우가 흔합니다. | 이 경우 공간 교차검증 게이트가 오탐을 차단하지 못하고 **fail-open(실패 시 열림, 게이트가 무력화되어 통과)**으로 우회 작동할 가능성이 있으므로 추가 가드레일 보완이 요구됩니다. |

---

## 내일 진행 방향 (확정)

| 추진 단계 | 핵심 작업 내용 | 기대 효과 및 설계 제안 |
| :--- | :--- | :--- |
| **1단계: 정면 외 방향 오발화 원인 수정** | 현재 class-agnostic 반사 게이트에서 정면(가로 중앙 40% 이내)을 벗어난 외곽 탐지가 경보를 트리거하는 로직 오류를 먼저 진단 및 해결합니다. | 씬게이트 도입 전에 정면 영역 및 거리/방향 필터의 오동작 조건을 수정하여 1단계 안정성을 선확보합니다. |
| **2단계: Android/iOS 씬게이트 도입** | 모바일 온디바이스에서 **Scene Classification(장면 분류, 실내/실외 구분)** 결과 데이터를 서버에 공유하고, `is_outdoor` 상태에 따라 실내/실외 프로파일(Profile)을 완전 분리합니다. | 실내 환경일 경우 차량, 오토바이 등 실외 특정 고위험 클래스의 탐지를 강제로 스킵하거나 신뢰도 기준을 극단적으로 상향하는 프로파일 분기가 가능합니다. |
| **3단계: 프로파일별 게이트 로직 분기 적용** | 실내/실외 프로파일에 따라 `reflex_gate.py`와 `detection_pipeline.py`의 임계값 및 판단 규칙을 차별화합니다. | 실내에서는 차량 탐지 제외 및 임계값 0.70 상향, 실외에서는 기존 3중 가드레일 규격을 그대로 사용하는 등 동적으로 가드레일 강도를 자동 제어합니다. |

---

## 참고 문서

* [stage_safety_reflex.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md): 오늘 적용된 상세 아키텍처 및 세부 로직 기술서
* [dg.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/dg.md): 개발 진척 전체 요약 이력서

---

## 재현 방법 / 테스트 환경

* **테스트 콘솔**: 운영자 데모 웹 콘솔 혹은 디버그 환경의 `Detection Guidance Log` 패널 화면을 기준으로 테스트를 진행합니다.
* **재현 스크린샷**: 실내 복도 책상 위 노트북이 `CAR 93%`로 오탐되는 디버그 캡처 스크린샷은 팀 공유 드라이브의 `/share/screenshots/reflex_ood_desk_car.png` 에 보관 중입니다. (본 핸드오프 문서에는 마크다운 로컬 경로 기재 형태로만 위치를 명시합니다)
