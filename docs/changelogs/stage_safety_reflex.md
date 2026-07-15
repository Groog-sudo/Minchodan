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

---

## 5. 탐지 오류 진단 (2026-07-15)

실내(복도) 환경에서 자동차, 오토바이, 이동형 간판 등 야외용 고위험군 클래스가 오탐되는 버그에 대해 5개 진단 항목을 점검한 결과는 다음과 같습니다.

### 1. 가중치 버전 일치성 확인
* **점검 결과**: 모바일 에셋의 `object_detection.tflite` (10.2MB)와 서버 측 PyTorch 가중치 `object_detection260714.pt` (6.2MB)의 파일 크기 및 변환 내역을 대조해 볼 때, `scripts/export_mobile.py`를 통해 내보낸 FP16/FP32 정밀도의 가중치 파일로 정합함을 확인했습니다.

### 2. 온디바이스 TFLite 추론 가동 여부 및 폴백 유무
* **점검 결과**: `localDetectorSelect.android.ts`는 예외 없이 `new TFLiteDetector()`를 생성하여 반환하며, 초기화 실패 시 NNAPI 가속을 끄고 CPU로 안전 폴백할 뿐, 임의의 더미/목업 데이터로 조용히 가로채어 대체하는 폴백 경로는 존재하지 않습니다. 즉, 실제 온디바이스 상에서 TFLite 엔진이 정상 로드되어 연산을 수행 중입니다.

### 3. 클래스 매핑(SSOT) 인덱스 정합성 비교
* **점검 결과**: 서버 측 YOLO 모델 내장 `names` 딕셔너리와 클라이언트 `tfliteDetector.ts` 내부 `AIHUB_CLASS_NAMES` 배열의 클래스 순서를 전수 대조했습니다.
  * *서버 실제*: `{0: 'barricade', 1: 'bench', 2: 'bicycle', 3: 'bollard', ..., 12: 'motorcycle', 13: 'movable_signage', ..., 19: 'scooter', 20: 'stop', ...}`
  * *클라이언트 실제*: `["barricade", "bench", "bicycle", "bollard", ..., "motorcycle", "movable_signage", ..., "scooter", "stop", ...]`
  * 클래스 매핑 순서는 **100% 동일**하므로 인덱스 꼬임으로 인한 오탐은 아닙니다.

### 4. 전처리 파이프라인(RGB/BGR, CHW/HWC) 정합성 분석
* **점검 결과**: **가장 유력한 오탐의 원인**으로 판단됩니다.
  * 클라이언트의 `realFrameProvider.ts`의 `bilinearResizeCHW()`는 이미지를 `CHW` (RGB 평면별 분리, `[3, 640, 640]`) 순서로 가공하여 텐서를 모델에 전달하고 있습니다.
  * 하지만 YOLO를 TFLite로 내보내면 텐서플로우 모델의 표준 스펙에 따라 **NHWC** (RGB 인터리브드, `[640, 640, 3]`) 구조의 입력 텐서를 요구합니다.
  * 모델이 `NHWC` 형태의 채널 배치를 예상하고 있는데 `CHW` 버퍼를 주입받을 경우, 화소 데이터가 채널 단위로 전부 뒤엉켜 깨지게 되며, 이로 인해 모델이 이미지 내 특징점을 인식하지 못하고 노이즈 상에서 무작위 고위험 객체를 고신뢰도로 인식하는 도메인 시프트 오작동이 유발됩니다.

### 5. 임시 디버그 로그 추가 및 TFLite 입출력 텐서 스펙
* **raw 로그 샘플 (TFLite 로드 시점)**:
  ```
  [TFLiteDetector DEBUG] segmentation inputs: [{"name":"images","dataType":"float32","shape":[1,640,640,3]}], outputs: [{"name":"output0","dataType":"float32","shape":[1,1000,38]}]
  [TFLiteDetector DEBUG] object_detection inputs: [{"name":"images","dataType":"float32","shape":[1,640,640,3]}], outputs: [{"name":"output0","dataType":"float32","shape":[1,300,6]}]
  ```
  *(입력 shape가 `[1, 640, 640, 3]`(NHWC)으로 찍힘에 따라, 현재 주입 중인 CHW 텐서와의 포맷 불일치가 명백한 오탐의 원인임을 규명함)*
* **raw 로그 샘플 (추론 시점 - 오탐 발생 예시)**:
  ```
  [TFLiteDetector DEBUG] object_detection raw output length=1800, numBoxes=300
    Raw Box 0: coords=[124.5,45.2,512.0,635.4], score=0.8872, classId=5.0 (car)
    Raw Box 1: coords=[20.1,110.5,350.4,480.0], score=0.7543, classId=12.0 (motorcycle)
  ```

---

## 6. 전처리 버그 수정 및 검증 결과

* **수정 내용**: 
  * `realFrameProvider.ts` 및 `mockFrameProvider.ts` 내부의 이미지 디코딩 전처리를 기존 `CHW`(`[1, 3, 640, 640]`) 평면 순서에서 모델의 실제 요구 스펙인 **NHWC**(`[1, 640, 640, 3]`) 인터리브드 텐서 구조로 재정렬했습니다 (`bilinearResizeHWC` 및 `rgbaToHwc` 적용).
  * `frameProvider.ts` 및 `useCamera.ts` 내부의 임포트 명칭과 주석을 `decodeBase64JpegToHwc` 스펙에 맞춰 일치시켰습니다.
* **검증 로그 (정상 환류 확인)**:
  * 전처리 수정 후 TFLite 디버그 로그 상에서 raw bounding box의 예측이 다음과 같이 **실내 복도 기준 상식적인 클래스 및 정상 신뢰도**로 탐지됨을 확인했습니다:
    ```
    [TFLiteDetector DEBUG] object_detection raw output length=1800, numBoxes=300
      Raw Box 0: coords=[200.5,350.2,320.0,580.4], score=0.6842, classId=15.0 (person)
      Raw Box 1: coords=[110.1,400.5,190.4,520.0], score=0.4521, classId=8.0 (chair)
    ```
    *(기존의 뜬금없는 car, motorcycle 오탐이 사라지고, 복도 내 사람 및 의자 등이 실제 위치에 맞게 정상 매핑됨)*

---

## 7. Class-Agnostic 반사 경로 판단 로직 단순화

보행자 전방 장애물 회피 목적의 반사 경로에 대해 클래스 구분을 배제하고 **"진행 방향 정면 근접 영역 내 물체의 존재 여부"** 자체로만 경보를 가동하도록 단순화했습니다.

### A. 서버 측 판단 규칙 단순화 (`reflex_gate.py` 및 `direction.py`)
* **`estimate_distance` (`direction.py`)**: 작은 객체 여부 분기(`small_objects` 딕셔너리)를 완전히 제거하고, 오직 사물의 면적비(`area_ratio`)에 의해서만 거리를 반하도록 `class-agnostic`하게 재구성했습니다 (0.08 이상 near / 0.03 이상 medium).
* **`reflex_gate` (`reflex_gate.py`)**: 
  1. `HIGH_RISK_CLASSES` 및 클래스별 최소 신뢰도 대조 로직을 삭제하고, 전체 탐지 결과에 대해 baseline 신뢰도 `0.35` 이상인 물체를 대상으로 작동합니다.
  2. BBox 중심이 화면 중앙 영역 **가로 40% 이내**(`0.30 <= center_x_norm <= 0.70`)에 있는지 검증합니다.
  3. BBox 면적 비율이 **8% 이상**(`area_ratio >= 0.08`)인 경우에 한해 즉시 근접 반사 경보(`high_obstacle_[direction]`)를 트리거하도록 축소 조정했습니다.

### B. 모바일 클라이언트 판단 규칙 단순화 (`CameraView.tsx`)
* **`applyLocalAreaReflex`**: 기존의 `isHighClass` (HIGH/GROUND HAZARDS 포함 여부) 클래스별 임계값 분기들을 모두 제거하고, 오직 사물의 면적비(`maxAreaRatio`)와 `nearestLidarMeters` 물리적 거리만을 기준으로 햅틱/비프음 단계를 트리거하도록 리팩토링했습니다.
  * `maxAreaRatio > 0.20`: 초접근 (연속 비프, 0ms)
  * `maxAreaRatio > 0.08`: 근접 (이중 비프, 200ms)
  * `maxAreaRatio > 0.03`: 중거리 (단발 비프, 600ms)
  * 기타: 원거리 (점진 비프, 1200ms)
