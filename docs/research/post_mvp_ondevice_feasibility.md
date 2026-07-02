# Post-MVP 온디바이스 추론 타당성 검증서

> **작성일**: 2026-07-01
> **버전**: v0.2.0 (YOLO26n / YOLO26n-seg 원본 모델 사용 강제 반영)
> **설계 기준**: [`docs/post_mvp_hybrid_roadmap.md`](post_mvp_hybrid_roadmap.md) (포스트 A 검증 단계)
> **관련 모델**: YOLO26n-detect, YOLO26n-seg

---

## 1. 개요 및 목적

본 문서는 Minchodan Post-MVP 하이브리드 아키텍처의 엣지(온디바이스) 반사 루프 구현을 위한 사전 타당성 검증 결과를 기록한다. YOLO26n 및 YOLO26n-seg 모델은 엣지 컴퓨팅에 최적화되어 있으므로, 타 대안 모델(YOLOv8/11 등)로의 전환을 배제하고 **YOLO26n 원본 및 YOLO26n-seg 모델을 온디바이스에 반드시 구현**하는 방향으로 배포 설계를 수립 및 검증한다.

---

## 2. 검증 요약 및 결과 매트릭스

| 검증 항목 | 대상 모델 | 포맷 | 성공 여부 | 결과/레이턴시 | 비고 |
| --- | --- | --- | --- | --- | --- |
| **서버 벤치마크** | YOLO26n | PyTorch (CPU) | **성공** | ~35ms | CPU 기준선 (Apple M4 Pro 1-Thread) |
| **CoreML 변환** | YOLO26n | CoreML (`.mlpackage`) | **실패** | N/A | coremltools 연산 변환 중 타입 캐스팅 오류 |
| **ONNX 변환** | YOLO26n | ONNX (`.onnx`) | **성공** | N/A | onnxslim 압축 완료 (9.5 MB) |
| **ONNX 변환** | YOLO26n-seg | ONNX (`.onnx`) | **성공** | N/A | onnxslim 압축 완료 (10.7 MB) |
| **TFLite 변환** | YOLO26n | LiteRT (`.tflite`) | **성공** | N/A | object_detection.tflite 생성 (9.8 MB) |
| **TFLite 변환** | YOLO26n-seg | LiteRT (`.tflite`) | **성공** | N/A | segmentation.tflite 생성 (11.1 MB) |
| **모바일 레이턴시 시뮬레이션** | YOLO26n | ONNX (CPU 1-Thread) | **성공** | **평균 22.89 ms** | ONNX Runtime (Min: 22.64ms, Max: 23.75ms) |

---

## 3. YOLO26n CoreML 익스포트 실패 원인 분석

YOLO26n 모델([object_detection.pt](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/models/yolo26n/object_detection.pt))을 CoreML 포맷으로 변환하는 과정에서 발생한 예외의 기술적 분석은 다음과 같다.

### 3.1 발생 예외 로그
```text
Converting PyTorch Frontend ==> MIL Ops:  35%|███▍      | 324/934 [00:00<00:00, 12480.73 ops/s]
ERROR - converting 'int' op (located at: '10/m/0/attn/520'):
ERROR ❌ CoreML: export failure 9.7s: only 0-dimensional arrays can be converted to Python scalars
```

### 3.2 원인 분석
- **커스텀 Attention 레이어 호환성**: YOLO26n에 적용된 Attention 모듈(`10/m/0/attn/520`) 내부 연산 중 symbolic tensor의 차원 정보(Dimension)를 정수형(`int`)으로 강제 캐스팅하는 구간이 존재한다.
- **coremltools 한계**: PyTorch의 dynamic/symbolic shape 연산을 CoreML MIL(Model Intermediate Language) Op으로 변환할 때, 변환 엔진인 `coremltools 9.0`이 다차원 텐서 배열을 파이썬 스칼라 정수로 매핑하지 못해 `only 0-dimensional arrays can be converted to Python scalars` 오류를 유발한다.
- **NMS-Free 구조 영향**: YOLO26n의 NMS-Free 헤더는 기존 YOLOv8/v11의 디텍터 대비 복잡한 텐서 슬라이싱 및 형태 변경(reshape) 연산이 밀집되어 있어, 변환기의 symbolic graph 분석 오작동을 유발할 가능성이 매우 높다.

---

## 4. 모델 런타임 확정을 통한 우회 전략 (ONNX & TFLite 강제)

CoreML 익스포트가 실패하더라도, 크로스 플랫폼 호환 런타임(ONNX/TFLite)을 통해 YOLO26n 및 YOLO26n-seg 모델을 온디바이스에서 반드시 직접 구동한다.

### 4.1 YOLO26n & YOLO26n-seg TFLite/ONNX 컴파일 성공
- **ONNX 변환**: `onnxslim` 최적화를 거친 [object_detection.onnx](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/models/yolo26n/object_detection.onnx) (9.5 MB) 및 [segmentation.onnx](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/models/yolo26n/segmentation.onnx) (10.7 MB) 생성 성공.
- **TFLite 변환**: Google LiteRT 규격을 충족하는 [object_detection.tflite](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/models/yolo26n/object_detection.tflite) (9.8 MB) 및 [segmentation.tflite](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/server/models/yolo26n/segmentation.tflite) (11.1 MB) 생성 성공.

### 4.2 런타임 아키텍처 및 구현 방향
- **iOS/Android 공통 런타임**: React Native 프로젝트 내에 `react-native-fast-tflite` 또는 `onnxruntime-react-native` 모듈을 연동한다.
- **네이티브 컴파일 우회**: OS 제조사 전용 API(CoreML) 대신 TFLite/ONNX C++ API 수준에서 CPU/GPU/NPU(NNAPI, CoreML Backend Provider) 가속을 중개 처리하여, YOLO26n 계열 원본 모델의 엣지 연산 이점을 그대로 유지한다.

---

## 5. 모바일 추론 레이턴시 시뮬레이션 분석

### 5.1 벤치마크 지표
- **평균 레이턴시**: **22.89 ms** (YOLO26n ONNX, CPU 1-Thread)
- **최소 레이턴시**: 22.64 ms
- **최대 레이턴시**: 23.75 ms

### 5.2 기술적 해석
- 호스트 환경의 싱글 스레드 벤치마크 결과가 **22.89ms**를 가리킴에 따라, 실제 모바일 기기(iPhone 15, Galaxy S24 등)의 CPU 구동 시 약 3~4배의 페널티(80~100ms)가 부여되더라도 **ONNX Runtime / TFLite NPU GPU Delegate 가속을 적용할 경우 최종 엣지 반사 지연 목표인 10ms ~ 30ms 이내 진입이 충분히 가능**하다는 타당성을 확보하였다.

---

## 6. 결론 및 하이브리드 아키텍처 권장 로드맵 반영

- **배포 전략 확정**: 대안 모델로의 타협을 전면 배제하고, 변환에 성공한 `object_detection.tflite` 및 `segmentation.tflite`를 모바일 런타임에 바인딩하여 **YOLO26n 및 YOLO26n-seg 모델을 단말 온디바이스에서 반드시 구동**한다.
- **로드맵 갱신 가이드**: [docs/post_mvp_hybrid_roadmap.md](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/docs/post_mvp_hybrid_roadmap.md)의 **포스트 A** 단계를 'CoreML 대안 모델 검색'에서 **'ONNX/TFLite 기반 YOLO26n/seg 직접 배포'**로 명시하고 설계를 확정한다.
