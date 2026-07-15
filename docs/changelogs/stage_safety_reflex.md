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
