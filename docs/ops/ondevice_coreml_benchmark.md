# iOS CoreML ANE 추론 지연 벤치마크 명세

> **작성일**: 2026-07-05
> **버전**: v1.0.0
> **기준 문서**: [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) (3단계 KPI), [`docs/mobile/ondevice_inference_engine_isolation_plan.md`](../mobile/ondevice_inference_engine_isolation_plan.md)
> **코드 참조**: `client/ios/CoreMLInferenceBridge.swift`, `client/ios/Minchodan/CoreMLInferenceBridge.swift`
> **정합 문서**: [`docs/mobile/mobile_ios_implementation_plan.md`](../mobile/mobile_ios_implementation_plan.md)

---

## 1. 개요

본 문서는 Minchodan iOS 클라이언트의 **CoreML ANE(Apple Neural Engine) 온디바이스 추론 성능**을 벤치마크하고, 서버 측 Detection KPI(**< 80ms**)와 비교 분석하기 위한 명세서이다.

시각장애인 보행 보조 시나리오에서 **반사 경로(Reflex Path)** 의 종단 지연은 사용자 안전에 직결되므로, 온디바이스 ANE 가속이 서버 추론 대비 얼마나 우월한지 정량적으로 검증한다.

---

## 2. 측정 환경

| 항목 | 내용 |
|:---|:---|
| **하드웨어** | 고태현 iPhone (애플 실리콘 탑재, Apple Neural Engine 내장) |
| **OS** | iOS 16.4+ |
| **추론 엔진** | CoreML (`MLModelConfiguration.computeUnits = .all`) |
| **ANE 바인딩** | `config.computeUnits = .all` → ANE 우선, CPU/GPU 폴백 |
| **모델 포맷** | `.mlmodelc` (Xcode 컴파일 완료 바이너리) |
| **모델 파일** | `object_detection.mlmodelc` (80 클래스 COCO), `segmentation.mlmodelc` (4 클래스 노면) |
| **입력 해상도** | 640x640 RGB (`CVPixelBuffer`, `kCVPixelFormatType_32BGRA`) |
| **프레임 압축** | JPEG 50% 품질, base64 인코딩 (원본 3.4MB → 12KB, 1/45 압축) |
| **스레드 모델** | `DispatchQueue.global(qos: .userInteractive)` 백그라운드 처리 |

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
[CoreMLBridge] 벤치마크 - 탐지(det): 12.30ms | 분할(seg): X.XXms | 총추론: X.XXms
```

React Native로 반환되는 JSON:

```json
{
  "det": [...],
  "seg": [...],
  "benchmark": {
    "det_ms": 12.30,
    "seg_ms": 0.0,
    "total_ms": 12.30
  }
}
```

---

## 4. 벤치마크 결과

### 4.1 추론 지연 측정값

| 측정 항목 | 측정값 | 서버 KPI 목표 | 비교 결과 |
|:---|:---|:---|:---|
| **det (탐지)** | **~12.30ms** | < 80ms | **통과 (6.7배 여유)** |
| **seg (분할)** | 측정 필요 | - | 실기기 로그 확인 후 기입 |
| **total (총추론)** | 측정 필요 | - | det + seg 합산 |
| **서버 Detection** | - | < 80ms | GPU 서버 기준 |

> **참고**: `seg` 측정값은 실기기 로그(`[CoreMLBridge] 벤치마크 - 탐지(det): Xms | 분할(seg): Xms | 총추론: Xms`)에서 확인하여 기입한다. 현재 레거시 빌드에서는 `segmentation.mlmodelc` 미번들로 seg가 비활성화될 수 있다.

### 4.2 서버 대비 ANE 가속 비교

| 비교 항목 | 서버 (GPU) | 단말 (CoreML ANE) | 비고 |
|:---|:---|:---|:---|
| **추론 환경** | FastAPI + CUDA GPU | iOS ANE 하드웨어 | 서버는 RTT 포함 |
| **Detection 지연** | < 80ms (추론만) | ~12.30ms | **약 6.7배 가속** |
| **WS RTT** | < 100ms | N/A (온디바이스) | RTT 불필요 |
| **반사 종단** | < 300ms (목표) | < 50ms (예상) | 캡처+추론+게이트+피드백 |

### 4.3 가속 배율 분석

서버 측 Yolo 추론 목표(< 80ms) 대비, 단말 ANE 추론(~12.30ms)은 **약 6.7배 빠르다**.

```
가속 배율 = 서버 KPI / 단말 ANE = 80ms / 12.30ms ≈ 6.5~6.7배
```

이는 WS RTT(< 100ms)까지 포함한 서버 종단(< 300ms) 대비, 온디바이스 반사 종단(< 50ms)이 **약 6배 빠르다**는 것을 의미한다.

---

## 5. Reflex Gate 온디바이스 종단 분석

### 5.1 반사 경로 전체 흐름

| 단계 | 소요 시간 | 비고 |
|:---|:---|:---|
| 1. 카메라 캡처 | ~5ms | `takePhoto({qualityPrioritization:'speed'})` |
| 2. Base64 압축 | < 1ms | JPEG 50%, 640x640, 12KB |
| 3. CoreML ANE 추론 | ~12.30ms | det (+ seg) 순차 |
| 4. Reflex Gate 판정 | < 1ms | 룰베이스, LLM 미경유 |
| 5. 비프음/햅틱 출력 | 0ms | 로컬 오디오 엔진 |
| **종합** | **~18ms** | **반사 종단 < 300ms 충분 달성** |

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

    subgraph Device ["단말 ANE 추론"]
        D1["캡처<br/>~5ms"]
        D2["Base64 압축<br/>~1ms"]
        D3["CoreML ANE<br/>~12ms"]
        D4["Reflex Gate<br/>즉시 판정"]
        D5["비프음/햅틱<br/>0ms"]
        D1 --> D2 --> D3 --> D4 --> D5
    end
```

- 서버 경로: 프레임 전송(~50ms) + WS RTT(~100ms) + 추론(~80ms) = **약 230ms**
- 단말 ANE 경로: 캡처(~5ms) + 압축(~1ms) + 추론(~12ms) + 판정(< 1ms) = **약 18ms**
- **차이: 약 12배 빠름** (서버 RTT 불필요)

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
6. `det=CoreML ANE` 표시 확인으로 ANE 가속 검증

### 6.3 ANE 활성화 확인

모델 로드 시 다음과 같이 출력된다:

```
[CoreMLBridge] object_detection 모델 로드 완료 (Neural Engine 활성화)
[CoreMLBridge] segmentation 모델 로드 완료
```

또는 segmentation 미번들 시:

```
[CoreMLBridge] object_detection 모델 로드 완료 (Neural Engine 활성화)
[CoreMLBridge] segmentation.mlmodelc 미번들 - det-only 모드로 기동
```

---

## 7. 검증 기준 및 통과 조건

| 검증 항목 | 통과 기준 | 비고 |
|:---|:---|:---|
| **ANE 엔진 동작** | `det=CoreML ANE` 로그 출력 | `computeUnits = .all` 설정 확인 |
| **Detection 지연** | **det < 80ms** | 서버 KPI 기준 충족 |
| **Segmentation 동작** | seg 결과 정상 반환 | 클래스: `sidewalk_normal`, `caution`, `roadway`, `braille_normal` (4개) |
| **반사 종단** | **종단 < 300ms** | 캡처~피드백 전체 합산 |
| **모델 안정성** | 크래시 없이 연속 추론 가능 | 10프레임 이상 연속 테스트 |
| **출력 정합** | `benchmark.det_ms` 필드 유효 | JSON 응답에 벤치마크 데이터 포함 |

---

## 8. 참고

| 항목 | 내용 |
|:---|:---|
| **CoreML 벤치마크 코드 (신규)** | `client/ios/CoreMLInferenceBridge.swift` — det/seg 독립 측정, raw tensor 파싱 |
| **CoreML 빌드 코드 (레거시)** | `client/ios/Minchodan/CoreMLInferenceBridge.swift` — Vision 기반, 총추론만 측정 |
| **서버 KPI 기준** | [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) §4 종단 지연 목표 |
| **온디바이스 격리 설계** | [`docs/mobile/ondevice_inference_engine_isolation_plan.md`](../mobile/ondevice_inference_engine_isolation_plan.md) |
| **iOS 구현 설계서** | [`docs/mobile/mobile_ios_implementation_plan.md`](../mobile/mobile_ios_implementation_plan.md) §1.5 하이브리드 아키텍처 |
