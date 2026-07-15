# 반사 경로 OOD 오탐 디버깅 및 완화 조치 핸드오프

> **작성일**: 2026-07-15
> **버전**: v1.0.0
> **대상**: 반사 경로(Reflex Gate, 즉시 위험 경보) 및 실내 OOD(Out-of-Distribution, 학습 데이터셋 분포 외 환경) 오탐 완화 작업

---

## 오늘 작업 요약

오늘 작업은 네트워크 지연 시 오작동하는 단말기 자체 반사 경보를 안정화하고, 실내 환경에서 차량/오토바이 등으로 인식되는 환각 오탐을 억제하는 데 주력했습니다.

1. **반사 경로 온디바이스 폴백 강화 및 중복 경보 방지 이중화**
   * **설명**: 네트워크 연결 장애나 300ms 초과 지연 발생 시 단말기가 자체 비프음/햅틱 경보로 안전하게 폴백(대체 작동)하고, 서버 복구 시 즉각 단말기 경보를 해제하도록 결합했습니다.
   * **커밋**: `1c92d0f`
   * **이력 링크**: [stage_safety_reflex.md#1-서버-미응답-시-클라이언트-자체-경보-폴백](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#L1-L25)

2. **반사 경보 연속 발화 개선 및 저신뢰 오탐 안정화 필터 추가**
   * **설명**: 동일 방향 경보 시 최소 3초(3000ms)의 재생 쿨다운(재발화 대기시간)을 보장하고, 2프레임 연속으로 검출될 때만 알람이 가동하도록 개선했습니다.
   * **커밋**: `d91be14`
   * **이력 링크**: [stage_safety_reflex.md#2-쿨다운디바운스-및-스무딩-필터-적용](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#L26-L55)

3. **온디바이스 TFLite 야외 객체 오탐 원인 분석 (진단)**
   * **설명**: 실내 복도에서 차량/오토바이가 빈발하는 오탐을 역추적하여 TFLite 입력 채널 레이아웃이 모델이 요구하는 NHWC(RGB 순서 결합형)가 아닌 CHW(RGB 채널 분리형)로 주입되는 데이터 오차(스크램블링)임을 규명하고 진단 로그를 심었습니다.
   * **커밋**: `37f6215`
   * **이력 링크**: [stage_safety_reflex.md#5-탐지-오류-진단](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#L56-L95)

4. **TFLite NHWC 전처리 버그 수정 및 class-agnostic 반사 경로 단순화**
   * **설명**: 전처리 레이아웃을 NHWC로 정형화하여 오탐을 잡았으며, 특정 클래스명 구분을 배제하고 BBox(가로 40% 내 정면) 및 면적 비율(8% 이상 근접)만을 확인해 비프/햅틱을 울리는 class-agnostic(클래스 무관) 로직으로 판단식을 축소했습니다.
   * **커밋**: `d4d9532`
   * **이력 링크**: [stage_safety_reflex.md#7-class-agnostic-반사-경로-판단-로직-단순화](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#L96-L130)

5. **OOD 실내 환경 환각 오탐 완화 대책 (3중 가드레일) 적용**
   * **설명**: BBox 면적 내 3x3 점을 샘플링하여 노면 세그멘테이션과 30% 이상 겹치지 않으면 벽/천장 환각으로 판단하여 차단하는 공간 교차검증 게이트를 추가하고, 시간적 필터(4프레임 누적) 및 신뢰도 임계값 상향(0.35 → 0.50)을 최종 적용했습니다.
   * **커밋**: `5ab06c4`
   * **이력 링크**: [stage_safety_reflex.md#8-ood-오탐-완화-실내-공간-씬-배제](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md#L131-L161)

---

## 미해결 문제

* **구석 물체의 지속적인 환각 및 고신뢰 오탐**:
  * 실내 복도/교실 구석의 책상이나 노트북 등 미학습/애매한 객체들이 여전히 `CAR 93%` 등으로 오탐되어 비프음이 간헐적으로 오발화하는 문제가 남아있습니다.
* **정면(12시) 외 방향 오발화 현상**:
  * "1~2시 방향"으로 판단되는 구석 물체임에도 반사 경보(사전합성 클립)가 발화되고 있습니다. `reflex_gate.py` 및 `CameraView.tsx` 내의 BBox 가로 40% 필터(정면 영역) 및 판단 로직이 올바르게 차단/작동하는지 상세 재검토가 필요합니다.
* **노면 교차검증 게이트의 실내 한계 (Fail-Open 우려)**:
  * 실내에서는 노면 세그멘테이션(sidewalk, roadway 등) 자체가 전혀 감지되지 않아 `surfaces` 리스트가 완전히 비어 있는 경우가 흔합니다. 이 경우 실내 OOD 환각이 교차검증 게이트를 우회(Fail-Open)해 그대로 통과하고 있을 가능성이 있으므로 검증 및 보완이 요구됩니다.
* **근본 원인**:
  * 객체/노면 모델 가중치가 실외 인도 보행용 데이터셋으로만 학습되어 실내 사물과 노면 형태를 OOD(분포 외 데이터)로 인식해 엉뚱한 클래스로 무작위 매핑하는 현상입니다.

---

## 내일 진행 방향 (확정)

1. **정면 외 방향 오발화 원인 진단 및 수정**:
   * OOD 씬게이트 도입 전에, 현재 class-agnostic 반사 게이트에서 정면(가로 중앙 40% 이내)을 벗어난 외곽 탐지가 경보를 트리거하는 로직 오류(BBox 크기 판정 범위 및 estimateDirection과의 간섭)를 먼저 진단 및 해결해야 합니다.
2. **Android/iOS 씬게이트(Scene Gate) 분류 조기 활성화**:
   * 모바일 온디바이스에서 Scene Classification(실내/실외 씬 분류 모듈) 결과 데이터를 서버에 공유하고, `is_outdoor=False` 상태를 활용해 실내/실외 프로파일(Profile)을 완전 분리합니다.
3. **프로파일별 임계값 및 게이트 로직 차별 적용**:
   * **실외 Profile**: 기존 3중 가드레일과 기본 임계값 적용.
   * **실내 Profile**: 차량/오토바이/신호등 등 실외 사물 탐지를 강제로 Skip하거나, 신뢰도 임계값을 극단적으로 상향(예: 0.70 이상만 통과)하는 별도 가드레일 설계 적용.

---

## 참고 문서

* [stage_safety_reflex.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/stage_safety_reflex.md): 오늘 적용된 상세 아키텍처 및 세부 로직 기술서
* [dg.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/dg.md): 개발 진척 전체 요약 이력서

---

## 재현 방법 / 테스트 환경

* **테스트 콘솔**: 운영자 데모 웹 콘솔 혹은 디버그 환경의 `Detection Guidance Log` 패널 화면 기준.
* **재현 스크린샷**: 
  * *실내 복도 책상 위 노트북이 `CAR 93%`로 오탐되는 디버그 캡처 스크린샷*은 팀 공유 드라이브의 `/share/screenshots/reflex_ood_desk_car.png` 에 보관 중입니다. (이 핸드오프 문서에는 로컬 마크다운 경로만 명시함)
