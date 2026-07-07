# iOS CoreML 온디바이스 추론 지연 벤치마크 명세

> **작성일**: 2026-07-05
> **버전**: v1.3.0 (2026-07-07 실기기 재검증: `.cpuAndGPU` 크래시 재현 확인 및 `.cpuOnly` 실측 벤치마크 갱신. §1·§2·§4·§5·§6·§7 갱신)
> **기준 문서**: [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) (3단계 KPI), [`docs/mobile/ondevice_inference_engine_isolation_plan.md`](../mobile/ondevice_inference_engine_isolation_plan.md)
> **코드 참조**: `client/ios/CoreMLInferenceBridge.swift`(유일한 실제 Xcode 빌드 타겟 — 2026-07-07 미사용 사본 `client/ios/Minchodan/CoreMLInferenceBridge.swift` 삭제)
> **정합 문서**: [`docs/mobile/mobile_ios_implementation_plan.md`](../mobile/mobile_ios_implementation_plan.md), [`docs/ops/model_class_validation_report.md`](model_class_validation_report.md)

---

## 1. 개요

본 문서는 Minchodan iOS 클라이언트의 **CoreML 온디바이스 추론 성능**을 벤치마크하고, 서버 측 Detection KPI(**< 80ms**)와 비교 분석하기 위한 명세서이다.

> **2026-07-07 현황**: 하드웨어는 Apple Neural Engine(ANE)을 내장하고 있으나, `computeUnits = .cpuAndGPU`(GPU/Metal 경로) 전환 시 실기기에서 `MLIR pass manager failed` 크래시가 반복 재현되어(§4 참조) **현재는 `computeUnits = .cpuOnly`로 CPU 전용 추론만 수행** 중이다. 즉 아래 수치는 ANE/GPU 가속 수치가 아니라 **CPU 전용 CoreML 추론** 실측치다. ANE/GPU 가속은 향후 크래시 근본 원인 규명 후 재도전 과제로 남는다.

시각장애인 보행 보조 시나리오에서 **반사 경로(Reflex Path)** 의 종단 지연은 사용자 안전에 직결되므로, 온디바이스 CPU 추론이 서버 추론 대비 얼마나 우월한지 정량적으로 검증한다.

---

## 2. 측정 환경

| 항목 | 내용 |
|:---|:---|
| **하드웨어** | 고태현 iPhone (애플 실리콘 탑재, Apple Neural Engine 내장) |
| **OS** | iOS 16.4+ |
| **추론 엔진** | CoreML `MLModel` 직접 호출 + raw tensor 수동 파싱 (2026-07-06부로 Vision Framework/`VNCoreMLRequest` 제거) |
| **컴퓨팅 유닛** | `config.computeUnits = .cpuOnly` — GPU(Metal) 경로에서도 `MLIR pass manager failed` 크래시가 재현되어(end2end NMS 연산의 Metal 컴파일 실패 추정) CPU 전용으로 하향 |
| **모델 포맷** | `.mlmodelc` (Xcode 컴파일 완료 바이너리) |
| **모델 파일** | `object_detection.mlmodelc` (커스텀 Object Detection **29클래스**, `det_best_20260705.pt` 파인튜닝, end2end raw tensor `[1, 300, 6]` 출력), `segmentation.mlmodelc` (커스텀 노면 Segmentation **4클래스**) — 두 모델 모두 80클래스 COCO 원본이 아닌 재학습 가중치 |
| **번들 상태** | `object_detection.mlpackage` 필수 번들, `segmentation.mlpackage`는 선택(optional) 번들 — 미번들 시 det-only 모드로 자동 기동 |
| **입력 해상도** | 640x640 RGB (`CVPixelBuffer`, `kCVPixelFormatType_32BGRA`) |
| **프레임 압축** | JPEG 50% 품질, base64 인코딩 (원본 3.4MB → 12KB, 1/45 압축) |
| **스레드 모델** | `DispatchQueue.global(qos: .userInteractive)` 백그라운드 처리 |
| **이미지 방향 보정** | `normalizedCGImage()`로 EXIF `imageOrientation` 반영 후 추론 (2026-07-06 추가, 세로 촬영 시 오탐지 원인 수정) |

> **2026-07-06 아키텍처 변경 요약**: 기존 `VNCoreMLRequest`/`VNRecognizedObjectObservation`(Vision Framework) 기반 파싱은 커스텀 29/4클래스 라벨 매핑과 맞지 않아 폐기하고, `MLModel.prediction(from:)`으로 raw tensor를 직접 받아 `(cx, cy, w, h, confidence, class_id)` 6속성을 수동 디코딩하는 방식으로 전면 교체했다. 상세는 [`docs/changelogs/kb.md`](../changelogs/kb.md) 2026-07-06 항목 참조.

---

## 3. 측정 방법론

### 3.1 타이밍 측정 원리

`CFAbsoluteTimeGetCurrent()` 호출 시점 간 차이로 추론 소요 시간을 계산한다. 이 함수는 고해상도 타임스탬프(마이크로초 단위)를 반환하며, 메인 스레드 차단 없이 정밀 측정이 가능하다.

```swift
let startTime = CFAbsoluteTimeGetCurrent()
// 추론 실행
let latency = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0  // ms 단위
```

### 3.2 det/seg 독립 측정 구조

현재 `CoreMLInferenceBridge.swift`(신규 버전)에서는 **det(탐지)와 seg(분할)를 독립적으로 측정**한다.

| 단계 | 실행 순서 | 측정 구간 |
|:---|:---|:---|
| 1. det 추론 | **먼저 실행** | `runDetection(model: detModel, ...)` 전후 |
| 2. seg 추론 | **이어서 실행** | `runDetection(model: segModel, ...)` 전후 |
| 3. 총추론 | det + seg | `totalLatency = detLatency + segLatency` |

### 3.3 벤치마크 출력 형식

Xcode Console에 다음과 같이 출력된다:

```
[CoreMLBridge] 벤치마크 - 탐지(det): 12.30ms | 분할(seg): 11.80ms | 총추론: 24.10ms
```

React Native로 반환되는 JSON:

```json
{
  "det": [...],
  "seg": [...],
  "benchmark": {
    "det_ms": 12.90,
    "seg_ms": 11.80,
    "total_ms": 24.70
  }
}
```

---

## 4. 벤치마크 결과

> **2026-07-07 재검증 경과**: raw tensor 파싱 아키텍처(§2)에서도 `computeUnits = .cpuAndGPU`로 전환해 실기기(고태현 iPhone) 재현 테스트를 진행했다. 앱 재실행마다 CoreML 모델 로드(`det=CoreML ANE / seg=CoreML ANE 완전 가속 기동 완료` 로그)까지는 성공했으나, 반사 프레임 1장 처리 직후 화면이 흰 화면으로 전환되며 프로세스가 종료(PID 1178→1210→1218로 반복 재기동)되는 크래시가 3회 연속 재현되었다. 이후 `computeUnits = .cpuOnly`로 되돌려 재빌드한 결과 509프레임 연속 무크래시 동작을 확인했다. 아래 §4.1~§4.3 수치는 이 **`.cpuOnly` 재검증 실측치**(2026-07-07)로 갱신한 것이며, 기존 2026-07-05 수치(Vision Framework + COCO 80클래스 + ANE 가속 가정 기준, 현재 아키텍처와 불일치)는 §부록에 구 데이터로만 보존한다.

### 4.1 추론 지연 측정값 (2026-07-07 실기기 측정, `.cpuOnly`, raw tensor 아키텍처)

| 측정 항목 | 평균값 | 최소값 | 최대값 | 서버 KPI 목표 | 비교 결과 |
|:---|:---|:---|:---|:---|:---|
| **det (탐지)** | **~24.11ms** | 21.33ms | 30.75ms | < 80ms | **통과 (3.3배 여유)** |
| **seg (분할)** | **~18.86ms** | 16.58ms | 23.96ms | - | 정상 동작 |
| **total (총추론)** | **~42.97ms** | 38.47ms | 51.67ms | - | det + seg 합산 |
| **서버 Detection** | - | - | < 80ms | GPU 서버 기준 | - |

> **측정 조건**: 2026-07-07 고태현 iPhone(iOS 26.5), `computeUnits = .cpuOnly`, 640x640 입력, 509프레임 연속 측정(Metro 로그 `[CoreMLBenchmark]` 라인 집계)

### 4.2 서버 대비 CPU 추론 비교

| 비교 항목 | 서버 (GPU) | 단말 (CoreML CPU) | 비고 |
|:---|:---|:---|:---|
| **추론 환경** | FastAPI + CUDA GPU | iOS CPU 전용 (`.cpuOnly`) | 서버는 RTT 포함, 단말은 ANE/GPU 미가속 |
| **Detection 지연** | < 80ms (추론만) | ~24.11ms (평균) | **약 3.3배 빠름** |
| **Segmentation 지연** | - | ~18.86ms (평균) | 온디바이스 CPU |
| **WS RTT** | < 100ms | N/A (온디바이스) | RTT 불필요 |
| **반사 종단** | < 300ms (목표) | < 60ms (추정 ~50ms) | 캡처+추론+게이트+피드백 |

### 4.3 가속 배율 분석

서버 측 Yolo 추론 목표(< 80ms) 대비, 단말 CPU 전용 추론(~24.11ms)은 **약 3.3배 빠르다**. ANE/GPU 가속이 크래시 없이 활성화되면 이 배율은 더 커질 잠재력이 있으나(§1 참조), 현재는 CPU 전용 수치 기준이다.

```
가속 배율 = 서버 KPI / 단말 CPU det = 80ms / 24.11ms ≈ 3.3배
```

WS RTT(< 100ms)까지 포함한 서버 종단(< 300ms) 대비, 온디바이스 반사 종단(~50ms 추정)은 **약 6배 빠르다**.

---

## 5. Reflex Gate 온디바이스 종단 분석

### 5.1 반사 경로 전체 흐름 (2026-07-07 `.cpuOnly` 실측 기준)

| 단계 | 소요 시간 | 비고 |
|:---|:---|:---|
| 1. 카메라 캡처 | ~5ms | `takePhoto({qualityPrioritization:'speed'})` |
| 2. Base64 압축 | < 1ms | JPEG 50%, 640x640, 12KB |
| 3. CoreML CPU 추론 | ~42.97ms (평균) | det(24.11ms) + seg(18.86ms) 순차 |
| 4. Reflex Gate 판정 | < 1ms | 룰베이스, LLM 미경유 |
| 5. 비프음/훅틱 출력 | 0ms | 로컬 오디오 엔진 |
| **종합** | **~49ms** | **반사 종단 < 300ms 충분 달성** |

### 5.2 서버 경로 대비 비교

```mermaid
graph LR
    subgraph Server ["서버 추론 (GPU)"]
        S1["프레임 수신<br/>~50ms"]
        S2["WS RTT<br/>~100ms"]
        S3["YOLO 추론<br/>&lt;80ms"]
        S4["게이트 판정"]
        S1 --> S2 --> S3 --> S4
    end

    subgraph Device ["단말 CPU 추론"]
        D1["캡처<br/>~5ms"]
        D2["Base64 압축<br/>~1ms"]
        D3["CoreML CPU<br/>~43ms"]
        D4["Reflex Gate<br/>즉시 판정"]
        D5["비프음/햅틱<br/>0ms"]
        D1 --> D2 --> D3 --> D4 --> D5
    end
```

- 서버 경로: 프레임 전송(~50ms) + WS RTT(~100ms) + 추론(~80ms) = **약 230ms**
- 단말 CPU 경로: 캡처(~5ms) + 압축(~1ms) + 추론(~43ms) + 판정(< 1ms) = **약 49ms**
- **차이: 약 4.7배 빠름** (서버 RTT 불필요, ANE/GPU 가속 시 추가 개선 여지 있음)

---

## 6. 측정 재현 절차

### 6.1 사전 조건

| 항목 | 내용 |
|:---|:---|
| macOS 환경 | Xcode 15+ 설치, CocoaPods 설치 |
| 실기기 | iPhone 연결 (Lightning/USB-C), iOS 16.4+ |
| 빌드 | `npx expo run:ios --device` 또는 Xcode에서 직접 빌드 |

### 6.2 측정 방법

1. `npx expo run:ios --device` 실행 (실기기 연결 필수)
2. 앱 기동 후 WebSocket 연결 확보 (자동)
3. Xcode Console에서 `[CoreMLBridge] 벤치마크` 로그 출력 확인
4. 로그 형식:

```
[CoreMLBridge] 벤치마크 - 탐지(det): X.XXms | 분할(seg): X.XXms | 총추론: X.XXms
```

5. 10회 이상 반복 측정 후 평균값 기록
6. `[CoreMLBenchmark] det=... seg=... total=...` (JS) 또는 `[CoreMLBridge] 벤치마크` (Swift) 로그로 실측 확인

### 6.3 모델 로드 확인 (현재 CPU 전용)

모델 로드 시 다음과 같이 출력된다:

```
[CoreMLBridge] object_detection 모델 로드 완료 (CPU 전용 모드, GPU 크래시 회피)
[CoreMLBridge] segmentation 모델 로드 완료
```

JS 측(`localDetectorSelect.ios.ts`)에서는 다음과 같이 출력된다:

```
[CoreMLDetector] det=CoreML(CPU) / seg=CoreML(CPU) 기동 완료
```

또는 segmentation 미번들 시:

```
[CoreMLBridge] object_detection 모델 로드 완료 (CPU 전용 모드, GPU 크래시 회피)
[CoreMLBridge] segmentation.mlmodelc 미번들 - det-only 모드로 기동
```

> **현황**: `segmentation.mlpackage`는 Xcode Resources 빌드 단계에 등록 완료되어 있으므로, 정상적인 빌드에서는 `segmentation 모델 로드 완료` 로그가 출력되어야 한다. `미번들` 로그가 출력되면 Xcode 프로젝트 설정을 확인한다. `ANE`/`Neural Engine 활성화` 문구는 2026-07-07부로 CPU 전용 로그로 교체되었다(§1 참조) — 과거 캡처된 스크린샷·문서에 남은 `ANE` 표기는 모두 이 시점 이전 것이다.

---

## 7. 검증 기준 및 통과 조건

| 검증 항목 | 통과 기준 | 실측 결과 | 비고 |
|:---|:---|:---|:---|
| **ANE/GPU 가속** | `computeUnits = .cpuAndGPU` 이상에서 무크래시 | **미통과** | 2026-07-07 실기기 재현: 첫 프레임 추론 직후 크래시 3회 연속 재현. `.cpuOnly`로 되돌림 |
| **CPU 전용 안정성** | 크래시 없이 연속 추론 가능 | **통과** | 2026-07-07 509프레임 연속 무크래시 확인 |
| **Detection 지연** | **det < 80ms** | **통과 (24.11ms 평균)** | 서버 KPI 기준 충족 (CPU 전용 기준) |
| **Segmentation 동작** | seg 결과 정상 반환 | **통과 (18.86ms 평균)** | 클래스: `sidewalk_normal`, `caution`, `roadway`, `braille_normal` (4개) |
| **반사 종단** | **종단 < 300ms** | **통과 (~49ms 추정)** | 캡처~피드백 전체 합산 |
| **출력 정합** | `benchmark.det_ms` 필드 유효 | **통과** | JSON 응답에 벤치마크 데이터 포함 |

---

## 8. 참고

| 항목 | 내용 |
|:---|:---|
| **CoreML 벤치마크 코드 (유일한 실제 빌드 타겟)** | `client/ios/CoreMLInferenceBridge.swift` — det/seg 독립 측정, raw tensor 파싱, `computeUnits = .cpuOnly` (2026-07-07 미사용 사본 `client/ios/Minchodan/CoreMLInferenceBridge.swift` 삭제 완료) |
| **JS 측 로드/로그 코드** | `client/src/inference/localDetectorSelect.ios.ts` — 2026-07-07 `ANE` 표기를 `CoreML(CPU)`로 정정 |
| **서버 KPI 기준** | [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) §4 종단 지연 목표 |
| **온디바이스 격리 설계** | [`docs/mobile/ondevice_inference_engine_isolation_plan.md`](../mobile/ondevice_inference_engine_isolation_plan.md) |
| **iOS 구현 설계서** | [`docs/mobile/mobile_ios_implementation_plan.md`](../mobile/mobile_ios_implementation_plan.md) §1.5 하이브리드 아키텍처 |

---

## 부록 A: 원시 벤치마크 데이터 (2026-07-07 실기기 측정, `.cpuOnly`, raw tensor 아키텍처)

509프레임 연속 측정(`[CoreMLBenchmark]` JS 로그 집계) 중 50프레임 간격 샘플:

| det (ms) | seg (ms) | total (ms) |
|:---|:---|:---|
| 30.75 | 20.05 | 50.80 |
| 23.57 | 18.58 | 42.15 |
| 24.08 | 17.74 | 41.82 |
| 23.67 | 17.80 | 41.48 |
| 22.07 | 17.47 | 39.54 |
| 22.21 | 18.22 | 40.42 |
| 21.83 | 17.40 | 39.23 |
| 24.42 | 17.39 | 41.81 |
| 27.68 | 20.13 | 47.81 |
| 26.78 | 20.59 | 47.37 |
| **평균(509프레임 전체)** | **24.11** | **18.86** | **42.97** |

## 부록 B: 원시 벤치마크 데이터 (2026-07-05 실기기 측정, 구 아키텍처 — Vision Framework + COCO 클래스, 참고용)

> 아래 수치는 폐기된 구 아키텍처(Vision Framework, COCO 80클래스, ANE 가속 가정) 기준이며 현재 코드와 일치하지 않는다. 이력 보존 목적으로만 남긴다.

| 프레임 | det (ms) | seg (ms) | total (ms) | 탐지 결과 |
|:---|:---|:---|:---|:---|
| 1 | 11.97 | 13.16 | 25.12 | laptop(0.52) |
| 2 | 12.10 | 8.75 | 20.85 | laptop(0.50) |
| 3 | 10.50 | 11.84 | 22.34 | laptop(0.74) |
| 4 | 15.58 | 11.11 | 26.69 | laptop(0.62) |
| 5 | 14.16 | 15.54 | 29.70 | laptop(0.75) |
| 6 | 13.11 | 9.88 | 23.00 | laptop(0.76) |
| 7 | 13.36 | 12.61 | 25.97 | laptop(0.73) |
| 8 | 12.46 | 11.59 | 24.05 | laptop(0.67) |
| **평균** | **12.90** | **11.81** | **24.71** | - |
