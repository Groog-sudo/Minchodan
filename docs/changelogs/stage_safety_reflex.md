# 온디바이스 폴백 강화 및 반사 경로 안정화 명세

> **작성일**: 2026-07-15
> **버전**: v1.0.0

## 1. 개요
서버 미응답, 타임아웃(300ms 초과) 및 네트워크 연결 유실(Disconnect/Fallback) 상태에서도 단말이 독자적으로 위험을 탐지하고 시각장애인에게 비프음, 햅틱 및 사전합성 경고 음성(Reflex Clip)을 제공할 수 있도록 온디바이스 반사 경로를 강화했습니다. 또한 서버와 온디바이스 반사 경로가 동시에 동작할 때의 중복 경보를 방어했습니다.

---

## 2. 반사 경보(Reflex Alert) 자체 유도 조건 명세
서버 `reflex_gate.py`의 실시간 위험 분석 로직을 분석하여 온디바이스 TFLite 탐지 결과에 대해 동일한 규칙을 성립시켰습니다.

| 검증 항목 | 임계 조건 | 비고 |
| :--- | :--- | :--- |
| **대상 장애물** | `HIGH_RISK_CLASSES` (인물, 자전거, 차량, 볼라드 등) | 29종 보행 사물 특화 목록 적용 |
| **근접성 (Y축)** | 사물 하단 `bottom_y > FRAME_SIZE * 0.82` (640px 기준) | 발밑 근접 영역 진입 여부 |
| **중앙 정렬 (X축)** | `FRAME_SIZE * 0.2 <= center_x <= FRAME_SIZE * 0.8` | 좌우 20% 마진을 제외한 중앙 60% 영역 |

---

## 3. 구현 내용 요약

### A. 300ms 초과 타임아웃 감지 및 Fail-safe 분기
* `CameraView.tsx` 내부에서 매 프레임 송신 시점(`lastFrameSentTsRef`)과 최근 서버 수신 시점(`lastServerResponseTsRef`)을 기록합니다.
* 송신 후 `300ms` 동안 어떠한 서버 응답(Ack, reflex_alert, guide, server_detection 등)도 수신되지 않거나, 소켓이 연결 유실 상태인 경우 즉시 `isServerTimeout = true`로 전환합니다.
* 이 상태가 되면 서버 대신 단말의 로컬 TFLite 추론 결과(`allDetections`, `reflexDetections`)를 신뢰하여 즉각 경보를 발생시키는 로컬 Fail-safe 루프를 가동합니다.

### B. 온디바이스 TFLite 추론 결과와 사전합성 음성(Reflex Clip) 재생 연동
* 로컬 탐지 장애물 중 가장 위험한 사물(LiDAR 검출체 또는 최대 면적 점유체)의 BBox 좌표를 기준으로 충돌 회랑 방향(`front`, `front-left`, `front-right`)을 실시간 계산합니다.
* 비프 주기(`beep_interval_ms`)가 100ms를 초과하는 중·원거리 위험 상황인 경우, 해당 방향에 부합하는 사전합성 고정 클립(`high_front.wav`, `high_front-left.wav`, `high_front-right.wav`) 재생을 트리거합니다.

### C. 서버-로컬 이중 경보 방어 (우선순위 단일화)
* **서버 정상 반응 시 (`!isServerTimeout`)**: 중복 피드백을 완전 방지하기 위해 로컬 측 `pathObstacleDetector` 연산 및 `applyLocalAreaReflex`에 의한 햅틱/비프/로컬 음성 제어를 완전히 억제(Suppress)합니다.
* **서버 비정상/지연 시 (`isServerTimeout`)**: 로컬 반사 경로를 즉시 독점적으로 가동하여 빈틈없는 보행 보조를 보장합니다.

---

## 4. 버그 조치 내역 (2026-07-15)

### A. 반사 경보(Reflex Clip) 연속 발화 원인 분석 및 해결 (쿨다운 도입)
* **원인**: 온디바이스 TFLite 추론이 120ms(8~10fps) 간격으로 동작할 때, 위험 감지 조건이 참일 경우 매 프레임마다 `playLocalReflexClip`이 호출되어 사전합성 음성이 엄청나게 겹쳐 연속 발화하는 오류가 있었습니다.
* **해결**: 방향별로 마지막 발화 시점(`lastLocalVoiceClipTsRef`)을 매핑하여, **동일 방향 경고에 대해 최소 3초의 쿨다운 간격**을 두도록 디바운스 설정을 추가했습니다.

### B. 온디바이스 저신뢰 오탐 제어 (안정화 필터 및 신뢰도 통일)
* **원인**: 단일 프레임에서 발생하는 TFLite 오탐지 노이즈와 서버 대비 낮게 잡혀있던 기본 임계치(`0.20~0.25`)로 인해 저신뢰 오탐이 햅틱/비프음으로 즉각 직결되었습니다.
* **해결**:
  * TFLite 내부 임계값(`CONF_THRESHOLD`) 및 `CameraView` 기본값(`confThreshold`)을 **서버 기본인 `0.35`로 통일**하여 저신뢰 노이즈 유입을 차단했습니다.
  * `localReflexStreakRef`를 추가하여, 감지된 위험 객체가 최소 **연속 2프레임 이상 유지될 때만** 비프음 및 햅틱 경보를 활성화하는 시간적 스무딩 필터를 결합했습니다.

### C. 서버-로컬 Suppress 로직 무음화 오류 해결
* **원인**: 이전 `isServerTimeout` 계산 시 `now - lastFrameSentTsRef.current` 구조로 되어 있어 프레임이 120ms 간격으로 계속 가동되는 동안 `lastFrameSentTsRef`도 실시간 갱신되어 300ms 초과 타임아웃을 감지하지 못했습니다. 또한, 서버 정상화 전환 시 이미 돌고 있던 로컬 햅틱/비프음 루프가 묵음화되지 않는 버그가 있었습니다.
* **해결**:
  * 타임아웃 감지 기준을 `now - lastServerResponseTsRef.current`로 변경하여, 서버 응답이 300ms 이상 끊기는 시점을 정확히 추적하도록 개선했습니다.
  * 서버 정상 상태(`!isServerTimeout`)로 복구 시, 로컬에서 기동된 햅틱과 비프음 자원을 즉시 해제하도록 `hapticEngine.stopContinuous()` 및 `audioEngine.stopBeep()` 호출을 명시적으로 추가했습니다.
