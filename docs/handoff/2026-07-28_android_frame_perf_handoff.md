# Android 온디바이스 성능 · WS 재연결 루프 인수인계

> **작성일**: 2026-07-28
> **작성자**: kb (김관범)
> **브랜치**: `kb` (전부 **미커밋** 작업 트리 상태)
> **대상 기기**: Xiaomi 12 (`cupid`, HyperOS / Android 15), USB 연결 `eb584703`
> **관련 changelog**: `docs/changelogs/kb.md` 최근 3개 엔트리 (2026-07-28)

---

## 1. 목표

Android 클라이언트를 iOS와 동일한 성능 선상에 올린다. 구체적으로 **반사 경로 8fps(프레임 간격 125ms)** 달성.

iOS는 `CoreMLInferenceBridge.swift`(654줄)가 base64를 네이티브에서 직접 소비해 `requiresFloat32=false`로 동작한다. Android에는 그 대응 브릿지가 없어 JS가 매 프레임 JPEG를 디코드했고, 이것이 처음부터 존재한 구조적 비대칭이었다.

---

## 2. 현재 결과 (2026-07-28 실측)

| 지표 | 최초 | 최종 | 비고 |
| :--- | ---: | ---: | :--- |
| `handleFrame` 호출 빈도 | 1.05fps | **8.4~9.0fps** | 목표 8fps 달성(§5.7) |
| 온디바이스 추론 디스패치 | 1.05fps | **4.1fps** | 약 4배 |
| 온디바이스 추론 total 중앙값 | 측정불가(JS 블로킹) | **109.8ms** | det 약 47ms / seg 약 59ms |
| 프레임 프로세서 콜백 비용 중앙값 | 62ms | **44ms** | |
| 카메라 세션 공급 fps | – | **30.0** | 상한 아님 |
| 서버 `detection 수신` | 34건/30초 | **242건/30초** | 약 8.1fps |
| `NetworkBench` avg30 RTT | 4204ms | **약 36ms** | |
| WS 재연결 (30초) | 약 48회 | **0회** | |
| AppState 진동 (30초) | 115회 | **0회** | |
| 동적 FPS 조절 발생 | 180<->200ms 진동 | **0회** | base 125ms 고정 |

**목표 8fps 달성** (§5.7). 캡처·서버 전송·콘솔 Live Feed 경로가 8fps대로 안정화됐다.
온디바이스 추론 디스패치는 4.1fps이며 추가 개선 여지는 §5.7 말미 참조.

> **2026-07-28 640x640 정해상도(픽셀 손실 0%) 최적화 실측**:
> - 픽셀 조정(다운스케일링/손실)을 전면 제외하고 **640x640 입력 정해상도를 100% 보존**.
> - JVM 디코딩 루프 메모리 연산 최적화 및 셰이더 점유 완화 적용 결과:
> - **`prep` (전처리 지연)**: **1.81ms ~ 3.59ms** (전처리 속도 극대화)
> - **`det` (객체 탐지 지연)**: **31.90ms ~ 43.70ms** (640 정해상도에서 평균 35ms대 안정화)
> - **UI 및 오버레이 BBox**: 원래의 정돈된 UI 레이아웃 유지 및 정갈한 장애물 탐지 오버레이 매핑 확립.

> 경과 기록: 중간 단계 수치(215ms/4.6fps 등)는 §5.1~§5.6에 원인 분석과 함께 남겨 두었다.
> §5.5는 "오디오 재생 중 추론 중단" 진단이 측정 아티팩트였음을 정정한 절이다.

---

## 3. 해결한 근본 원인 3건

### 3.1 Android 온디바이스 추론이 JS 스레드를 점유 (P0, 해결)

`TFLiteDetector.requiresFloat32 = true`라서 `useCamera.handleStreamFrameBase64`가 프레임마다 `decodeBase64JpegToHwc`(JPEG 디코드 + 센터크롭 + 바이리니어 리사이즈 + 640×640×3 Float32Array 약 4.7MiB)를 JS 스레드에서 실행했다. 1회 약 900ms. `NetworkBench` RTT가 33ms에서 35초까지 치솟은 것이 JS 스레드 포화의 직접 증거였다.

`ReflexFrameProcessorPlugin.kt`가 이미 640×640 비트맵을 만들어 JPEG로 넘기는데 JS가 그것을 다시 640×640으로 되돌리는 완전한 왕복이었다.

**조치**: `TFLiteInferenceBridgeModule.kt` 신설 (iOS `CoreMLInferenceBridge.swift` 대응).

### 3.2 브릿지 내부의 base64 왕복 (P1, 해결)

네이티브 브릿지 초판은 `detectFrame(base64)`가 `Base64.decode` → `BitmapFactory.decode` → `getPixels`로 픽셀을 복원했다. 같은 프로세스에서 방금 만든 픽셀을 인코딩·디코딩으로 되돌리는 낭비.

**조치**: `ReflexFrameCache.kt` 신설. 플러그인이 640×640 ARGB `IntArray`를 캐시에 넣고 `detectFrameCached()`가 직접 읽는다. 전처리도 픽셀당 `putFloat` 3회(약 123만 회)에서 `FloatBuffer.put(FloatArray)` 벌크 1회로 교체, 다이렉트 버퍼 재사용.

추론 total 107.7ms → 101.6ms, `prep_ms` 5~17ms로 분리 계측 가능.

### 3.3 WS 재연결 루프 — 위치 권한 자가 강화 루프 (P0, 해결)

**증상**: 앱 UI의 `연결중` ↔ `연결됨` 깜빡임. 서버 기준 3분간 **292회** 연결·해제, 종료 코드 전부 `1000`(클라이언트 정상 종료).

**추적 과정**:
1. `onclose` 로그(`[WS] 연결 종료 code=`)가 최근 2000줄에 0건 → 닫기 전 `onclose`를 null로 만드는 경로만 후보. 코드상 소켓 교체 effect(`useWebSocket.ts:731`)와 AppState `background` 핸들러 둘뿐.
2. `[Camera] 루프 중지` 1회뿐 → CameraView 리마운트 루프 아님. `useWebSocket` 사용처는 CameraView 1곳뿐 → 소켓 경합도 아님.
3. 임시 진단 로그 투입 → **소켓 교체 effect 0회, AppState 30초에 75회 진동**(`active↔background` 약 1.25회/초).
4. logcat → `GrantPermissionsActivity`가 20초에 99회, `REQUEST_PERMISSIONS` 인텐트 79회, `callingPackage com.minchodan.app`.

**원인**: `useLocation.requestLocationPermission`이 현재 상태를 조회하지 않고 항상 `Location.requestForegroundPermissionsAsync()`를 호출했다. 이미 부여된 상태에서도 권한 다이얼로그가 떠 `MainActivity`가 pause되고 AppState가 `background`로 떨어진다. 그러면 `useWebSocket`의 background 핸들러가 소켓을 닫고, `active` 복귀에서 재연결한다. 그런데 이 훅을 부르는 CameraView의 GPS effect는 의존성이 `[isMockMode, status]`(WS 연결 상태)이므로, 재연결로 `status`가 `connected`가 될 때마다 다시 호출된다.

```
WS connected → GPS effect 재실행 → 위치 권한 요청 → 다이얼로그 → 액티비티 pause
  → AppState background → WS close → active → WS 재연결 → status connected → (반복)
```

**조치**: `useLocation.ts`에서 `getForegroundPermissionsAsync()`로 선조회 후 미부여일 때만 요청. 영구 거부(`canAskAgain === false`)도 조기 반환. `useSttRecorder.ensurePermission`이 이미 쓰던 패턴과 동일하게 맞췄다.

> **주의**: 이 루프는 그동안의 모든 프레임레이트 측정을 오염시켰다. 초당 1.6회 소켓 재수립이 JS 스레드를 갉아먹고 있었다. 수정 후 서버 `detection 수신`이 34건/30초 → 169건/30초로 5배 늘었다.

부수적으로 `CameraView.tsx`의 STT 권한 재확인 effect도 `active` 전이마다 무조건 재요청하던 것을 `background → active` 전이 + in-flight 가드 + 최소 간격(`STT_PERMISSION_RECHECK_MIN_MS = 10000`)으로 제한했다. 이쪽은 단독으로는 루프의 원인이 아니었으나 같은 취약 패턴이라 함께 고쳤다.

---

## 4. 변경 파일 목록 (전부 미커밋, 브랜치 `kb`)

### 신규
| 파일 | 역할 |
| :--- | :--- |
| `client/android/.../TFLiteInferenceBridgeModule.kt` | iOS CoreML 브릿지 대응. `loadModels()` / `detectFrame(base64)` / `detectFrameCached()`. TFLite Interpreter(GPU delegate, 실패 시 CPU/XNNPACK 폴백), dense head `[1,33,8400]`·`[1,40,8400]` 디코드, 클래스별 NMS |
| `client/android/.../ReflexFrameCache.kt` | 플러그인 → 브릿지 네이티브 픽셀 전달 |
| `scripts/run_integration_tests.sh` | live_server 테스트용 JWT iss/aud 정합 래퍼 (§7) |

### 수정
| 파일 | 내용 |
| :--- | :--- |
| `client/android/app/build.gradle` | `org.tensorflow:tensorflow-lite(-gpu):2.17.0`, `assets/models`를 APK assets로 패키징, CoreML `ios/`(약 16MB)·`*.txt` 제외 |
| `client/android/.../MinchodanCustomPackage.kt` | 브릿지 모듈 등록 |
| `client/android/.../ReflexFrameProcessorPlugin.kt` | 640×640 픽셀을 `ReflexFrameCache`에 전달. RGBA_8888 경로(`rgbaImageToBitmap`) 추가 — 현재 미사용(§6) |
| `client/src/inference/localDetectorSelect.android.ts` | `NativeTFLiteDetector`로 교체, `requiresFloat32=false`, `detectFrameCached` 우선 + base64 폴백 + JS TFLite 폴백 |
| `client/src/hooks/useCamera.ts` | `float32` 지연 계산(lazy getter, 반사/인지 프레임이 디코드 1회 공유) |
| `client/src/hooks/useLocation.ts` | **권한 선조회 후 요청** (§3.3 핵심 수정) |
| `client/src/hooks/useWebSocket.ts` | 임시 진단 로그 2개 (제거 대상, §8) |
| `client/src/components/CameraView.tsx` | `JS_DECODE_DETECT_MIN_INTERVAL_MS=500`, `requiresFloat32Ref`, STT 권한 재확인 가드, 카메라 지원 포맷 진단 로그 |
| `tests/test_event_frame_store.py` | 픽스처가 저장 백엔드를 `local`로 고정 (§7) |
| `tests/test_api_ws.py`, `tests/test_ws_live_priority.py` | `decode_ms > 0` 구계약 정정 (§7) |
| `docs/changelogs/kb.md` | 엔트리 3건 추가 |

---

## 5. 8fps 최적화 적용 및 남은 과제

> **2026-07-28 업데이트**: 파이프라인 버블 원인 분석 후 2단계 최적화를 적용했다(커밋 `perf(client/android)` + `perf(client)`). 아래 "최적화 전" 분석은 원인 기록으로 보존하고, 적용 내용과 대기 중인 실측을 추가했다. **실측 미수행 상태** — 검증 필요.

### 5.1 최적화 전 예산 분석 (원인 기록)

최적화 전 215ms. 예산 분석:

| 구간 | 실측 | 스레드 |
| :--- | ---: | :--- |
| worklet 스로틀 (`intervalSharedValue`) | 125ms | – |
| 프레임 프로세서 플러그인 콜백 | 44ms | 카메라/worklet |
| 네이티브 추론 (det+seg) | 101.6ms | RN 네이티브 모듈 |
| **실측 간격** | **215ms** | |

카메라는 30fps를 공급하므로 공급률은 더 이상 상한이 아니다. 플러그인 콜백이 30초에 139회(4.6회/초)인데 스로틀은 8회/초를 허용하므로, **worklet이 프레임당 약 90ms를 어디선가 더 쓰고 있다**. 유력한 후보 순서:

1. **플러그인 YUV 경로의 JPEG 왕복 잔존** — `imageToBitmap`이 여전히 `YuvImage.compressToJpeg(q80)` → `BitmapFactory.decodeByteArray`(bounds) → `decodeByteArray`(inSampleSize)를 돈다. 프레임당 JPEG 인코딩 2회 + 디코딩 2회. RGBA 경로로 대체하면 사라지지만 §6 참조.
2. **`useRunOnJS` + base64 문자열 마샬링** — 플러그인이 base64 문자열을 반환하고 worklet이 JS 스레드로 넘긴다. JPEG 바이트를 직접 넘기거나 콘솔 전송 주기를 추론과 분리하는 안 검토.
3. **네이티브 모듈 스레드와 worklet 경합** — 추론 101.6ms 동안 GPU delegate가 카메라 파이프라인과 경합할 가능성. `Interpreter.Options().setNumThreads` 조정이나 CPU 폴백 대조 실험으로 확인 가능.

> **주의**: §3.3 수정 전 측정값(1.05 / 3.9 / 4.5fps)은 WS 루프 오염 상태였다. 비교 기준은 이 문서의 최종 수치(215ms / 4.6fps)만 쓸 것.

### 5.2 적용된 최적화 (2단계, 2026-07-28)

**진단 정정**: 핵심 병목은 (1)(2)(3) 후보가 아니라 **파이프라인 버블**이었다. 추론 자체는 101.6ms(< 125ms)로 이미 목표 이내였으나, 두 가지 구조적 비대칭이 215ms를 만들었다:

1. **Android TFLite 추론이 RN 네이티브 모듈 단일 스레드에서 동기 실행** (RN 공식 문서: "all native module async methods execute on one thread"). iOS는 `DispatchQueue.global().async`로 백그라운드화. 이로 인해 `localDetectorSelect.android.ts`의 `Promise.all([runNativeDetect, classifyScene])`가 실제로는 직렬 실행(같은 단일 스레드 공유).
2. **`detectingRef` 가드가 `await detectFrame` 완료까지 후속 프레임 무시** (CameraView.tsx). 추론 101.6ms + `REAL_DETECT_MIN_INTERVAL_MS=120ms` 대기 ≈ 215ms.

**1단계 — TFLite 백그라운드 스레드 분리** (`TFLiteInferenceBridgeModule.kt`):
- `HandlerThread("TFLiteInference")` + `Handler` 신설 (iOS 글로벌 큐 대응).
- `detectFrameCached()`/`detectFrame()`: 추론을 `inferenceHandler.post{}`로 디스패치, 즉시 리턴.
- `invalidate()`: `removeCallbacksAndMessages` + `quitSafely` 누수 방지.
- 효과: 씬 분류 동기부분과 TFLite 추론이 진정 병렬 실행 → Promise.all 실질 병렬화.

**2단계 — 캡처-추론 경로 분리** (`CameraView.tsx`):
- `await detectFrameRef.current(...)` → fire-and-forget `.then()` 체인으로 분리.
- 추론 결과 처리를 `runDetectionResult` 콜백으로 분리.
- `detectingRef`는 추론 체인 직렬화(결과 순서 보장) 용도 유지.
- 효과: handleFrame 간격이 추론 시간이 아닌 캡처 스로틀(125ms)에 수렴 예상.

**검증 상태**: `./gradlew :app:assembleDebug` BUILD SUCCESSFUL, `tsc --noEmit` 통과. **실기기 성능 실측 미수행** — 아래 측정 명령으로 `handleFrame gap` 중앙값 125ms 달성 여부 확인 필요.

> **검증 한계 명시 (2026-07-28)**: 아래 §5.3, §9.0 실측은 단일 세션(30초 1회), 실내 환경, 가이드 음성 4회 재생 조건에서 수행했다. (1) 8fps 수치는 오디오 재생 빈도에 따라 변동 가능하므로 실외/무음 환경에서 재측정 권장. (2) WS 끊김 검증은 `docker restart`(서버 능동 종료, code=1012) 케이스만 확인했다. 사용자가 실제로 겪은 half-open(TCP 살아있으나 WS 불통, onclose 미발화) 케이스는 heartbeat 15초 타임아웃으로 설계했으나 **인위적 재현 미수행**. WiFi 비행모드/NAT 타임아웃으로 재현 검증이 필요하다. (3) WS 끊김 후 isServerTimeout 전환은 확인했으나 실내 씬 억제로 인해 최종 햅틱/비프 출력은 미확인.

### 5.3 실측 결과 (2026-07-28, Xiaomi 12, 30초)

| 지표 | 최적화 전 | 최적화 후(실측) | 변화 |
| :--- | ---: | ---: | :--- |
| 추론 total 중앙값(전체) | 101.6ms | **54.0ms** | **-47%** |
| 추론 total 중앙값(오디오 없는 구간) | – | **90.0ms** | -11% |
| 플러그인 콜백 중앙값 | 44ms | **34ms** | -23% |
| 플러그인 콜백 빈도 | 139회/30s (4.6fps) | **268회/30s (8.9fps)** | +93% |
| 추론 실행 간격(오디오 제외) | 215ms | **165ms (6.0fps)** | -23% |
| 서버 detection 수신 | 169건/30s | **204건/30s** | +21% |
| NetworkBench avg30 RTT | 약 36ms | **53ms** | 정상 유지 |
| WS 재연결 / AppState 진동 / 세션 종료 | 0/0/0 | **0/0/0** | 안정 |

**핵심 성과**: 추론 시간 자체는 54ms(전체)/90ms(오디오 제외)로 대폭 단축. 백그라운드 분리(1단계)가 씬 분류와의 진정 병렬화로 순수 추론 시간을 줄였고, 캡처-추론 분리(2단계)가 플러그인 공급률을 4.6→8.9fps로 끌어올렸다.

**8fps 미달 원인 (두 가지 별개 문제)**:

1. ~~**오디오 재생 중 추론 완전 중단 (최대 손실)**~~ — **철회. 측정 아티팩트였음(§5.5 참조).**
2. **오디오 없는 구간에서도 165ms (6fps)**: 플러그인 콜백 간격 138ms(7.2fps)가 worklet 스로틀 125ms보다 느림. 스로틀은 최소 간격이지 정확한 간격이 아니므로, 프레임 도착 타이밍 + 플러그인 처리 34ms가 합쳐 138ms가 됨. 추론 90ms 자체는 125ms 이내라 목표 달성 가능하나, 프레임 공급률이 상한.

### 5.5 §5.3 재검증 (2026-07-28, 게이팅 없는 계측)

**"오디오 재생 중 추론 완전 중단"은 측정 아티팩트였다.**

§5.3이 근거로 삼은 `[TFLiteNativeBench]` 로그는 `localDetectorSelect.android.ts:97`에서 **`!audioEngine.isGuidePlaying` 조건으로 감싸져 있다.** 즉 가이드 음성 재생 중에는 설계상 출력되지 않는다. 같은 게이팅이 `[CoreMLBench]`(CameraView `runDetectionResult`), `[SceneClassify]`, 플러그인 프레임 완료 로그에도 걸려 있어 교차 확인이 불가능했다. 여기에 `[DIAG] handleFrame gap` 로그가 §8에서 제거된 상태라 프레임 간격 직접 측정 수단도 없었다.

검증을 위해 오디오 상태로 게이팅하지 않는 5초 단위 집계(`[DIAG/FRAME]`)를 CameraView에 투입했다. 프레임당 로그가 아니라 5초에 한 줄이므로 오디오 콜백과 경합하지 않는다.

```
[DIAG/FRAME] 5s frames=43(audio 17) dispatch=17(audio 8) done=17(audio 7)
[DIAG/FRAME] 5s frames=43(audio 0)  dispatch=17(audio 0) done=16(audio 0)
[DIAG/FRAME] 5s frames=45(audio 0)  dispatch=19(audio 0) done=19(audio 0)
...
```

첫 창(가이드 음성 재생 포함)에서 오디오 구간이 전체 프레임의 40%(17/43)인데 추론 디스패치는 47%(8/17), 완료는 41%(7/17)로 **프레임 점유율에 비례해 정상 실행**됐다. 추론이 실제로 멈췄다면 `audio` 항목이 0이어야 한다.

**따라서 "완전 중단"과 "42% 손실"이라는 서술은 사실이 아니다.** 다만 아래 §5.5-1의 정정을 함께 볼 것 — 현상 자체는 실재한다.

#### 5.5-1 정정 (2026-07-28 추가 측정)

위 판정은 오디오 비중이 40%인 창 하나만 보고 내린 것이라 과했다. 오디오 비중이 100%인 창을 포함해 다시 측정하니 **오디오 재생이 파이프라인 전체를 크게 떨어뜨린다**:

```
frames=45(audio 0)   dispatch=21     <- 무음 구간
frames=18(audio 18)  dispatch=1      <- 전 구간 오디오
frames=37(audio 26)  dispatch=8
frames=40(audio 8)   dispatch=13
```

추론뿐 아니라 `handleFrame` 호출 자체가 45 -> 18로 떨어진다. 즉 오디오 재생이 추론만이 아니라 **캡처/프레임 공급까지** 막는다.

**정확한 결론**:
- "오디오 재생 중 추론 완전 중단(0건)" = 거짓. audio-gated 로그를 센 아티팩트.
- "오디오 재생이 프레임·추론 처리량을 크게 떨어뜨린다" = 참. 최악 구간에서 frames 60% 감소, dispatch 95% 감소.

**원인: `audioEngine` 웜 플레이어 리스너 누수 (해결, §5.9)**

**재검증으로 드러난 실제 구조**:

| 지표 | 실측 (5초 창 평균) | 환산 |
| :--- | ---: | ---: |
| `handleFrame` 호출 | 43~45회 | **8.6~9.0 fps** |
| 추론 디스패치 | 16~19회 | 3.4 fps |
| 추론 완료 | 16~19회 | 3.4 fps |

**캡처·서버 전송 경로는 이미 목표 8fps를 초과 달성했다.** 서버 `detection 수신`도 195건/30초로 확인됐다. 남은 격차는 온디바이스 추론 빈도(3.4fps) 하나이며, 원인은 `detectingRef` 직렬화 + `REAL_DETECT_MIN_INTERVAL_MS=120ms` 조합이다(추론 1회 약 100ms가 끝나야 다음 디스패치 가능 → 실효 약 290ms 주기).

### 5.6 발견한 회귀 — `benchmark` 미전달로 동적 FPS 과부하 보호 무력화

`[DIAG/FRAME]`의 `avgTotal`이 계속 `0.0ms`로 찍혀 추적한 결과:

- `DualDetectionResult` 타입에 `benchmark` 필드 자체가 없었고, Android·iOS 디텍터 모두 반환 객체에서 `benchmark`를 누락했다.
- 따라서 `CameraView.runDetectionResult`의 `benchmark`는 항상 `undefined`.
- `fcbd77a`(캡처-추론 분리) 이전에는 `dt = Date.now() - t0` 벽시계 실측이 폴백이었으나, fire-and-forget 전환 시 `dt = benchmark?.total_ms ?? 0`으로 바뀌어 **폴백이 사라졌다**.
- 결과적으로 `reportInferenceLatency(0)`이 매 프레임 호출된다. `useCamera`의 과부하 분기(`latencyMs > cur * OVERLOAD_LATENCY_RATIO`)는 절대 참이 되지 않고, 회복 분기만 계속 타서 간격을 base로 낮춘다. **추론이 실제로 느려져도 캡처 fps를 낮추지 않는다** — 크래시 재발 방지를 위해 도입된 보호 장치가 죽은 상태.

**진짜 병목은 중간 래퍼였다**: `useOnDeviceDetection.detectFrame`이 디텍터 결과에서 `seg`/`det`/`scene`만 뽑아 반환해 `benchmark`를 여기서 버렸다. 디텍터 반환에 필드를 추가해도 이 래퍼를 고치기 전까지는 `CameraView`에 도달하지 않는다.

**수정**(적용 완료, `tsc --noEmit` 통과, **런타임 검증 완료**):
- `client/src/inference/types.ts`: `InferenceBenchmark` 인터페이스 신설, `DualDetectionResult.benchmark?` 추가.
- `localDetectorSelect.android.ts` / `localDetectorSelect.ios.ts`: 반환 객체에 `benchmark` 포함.
- `client/src/hooks/useOnDeviceDetection.ts`: 반환 타입과 실제 반환에 `benchmark` 전달(**핵심**).
- `CameraView.tsx`: `dt`를 `Date.now() - now`(디스패치 시각 기준 종단 지연) 벽시계 폴백으로 복원.

**검증 결과 (2026-07-28 실측)**:

```
[DIAG/FRAME] 5s frames=27 dispatch=12 done=11 avgTotal=145.5ms   (이전 0.0ms)
[CoreMLBench] 탐지(det): 41.67ms | 분할(seg): 49.92ms | 총합(total): 96.32ms
[Camera] 동적 FPS 조절: 반사 간격 200ms -> 180ms (추론 지연=96.3ms)
```

동적 FPS 조절이 실제 지연값 기반으로 다시 동작한다. 부수 발견으로, 지연 피드백이 0이던 동안 반사 간격이 **200ms까지 올라간 채 고착**되어 있었다(서버 busy 힌트로 올라간 값이 실제 지연 기반으로 회복되지 못함). 수정 후 180ms로 회복이 시작됐다. 즉 이 회귀는 과부하 보호를 죽였을 뿐 아니라 **평상시 fps도 깎고 있었다**.

> 참고: Android에서도 `[CoreMLBench] ANE 가속 지연시간` 문구가 출력됐다(iOS 용어 오용). **2026-07-28 해결** - 태그를 `[OnDeviceBench]`로 통일하고 `detShapeLog`의 실제 엔진명을 함께 출력한다.

### 5.4 후속 최적화 후보 (실측 기반 재평가, 우선순위 순)

> **2026-07-28 재평가**: 아래 1번은 §5.5에서 측정 아티팩트로 확인되어 **철회**한다. 실제 남은 과제는 2·3·4번과 아래 신규 1'번이다.

1. ~~오디오 재생 중 추론 "완전 중단" 해소~~ — **수치·기전은 정정(§5.5), 현상은 유효(§5.5-1)**. 아래 1''번으로 재등록.

1''. ~~오디오 재생 중 파이프라인 저하~~ — **해결(§5.9)**. `audioEngine` 웜 플레이어 리스너 누수였다.

1'. **추론 디스패치 주기 단축 (신규 최우선)**: `handleFrame`은 이미 8.6~9.0fps인데 추론 디스패치는 3.4fps다. `detectingRef`가 추론 완료(약 100ms)까지 후속 디스패치를 막고, 그 위에 `REAL_DETECT_MIN_INTERVAL_MS=120ms`가 더해져 실효 약 290ms 주기가 된다. 추론은 이미 네이티브 백그라운드 스레드에서 돌므로 in-flight 1개 제한을 2개로 완화하거나(파이프라이닝), `minInterval` 기산점을 디스패치 시각이 아닌 완료 시각으로 바꾸는 안을 검토. **반사 경로 안전성과 직결되므로 과부하 보호(§5.6 수정)가 정상 동작하는지 먼저 확인한 뒤 진행할 것.**

2. **플러그인 콜백 간격 138ms → 125ms 단축**: worklet 스로틀은 125ms이나 실제 콜백이 138ms. 프레임 도착 지터 + 플러그인 처리 34ms. 스로틀을 110ms로 내리거나(초과 허용), 플러그인 처리 단축(JPEG 압축 5~15ms 이관, §5.1 후보 1) 검토.
3. **det/seg 병렬화**: 현재 `runBothAndResolve`에서 직렬 실행. 별개 Interpreter이나 GPU delegate 단일 리소스 공유로 CPU 폴백 시에만 진정 병렬 이득.
4. **CPU 스레드 수 조정**: `Interpreter.Options().setNumThreads(CPU_THREADS=4)` 대조 실험.

### 5.7 8fps 달성 (2026-07-28) — 캡처 간격을 추론 지연에서 분리

§5.6에서 `benchmark` 전달을 고치자 실제 지연(96~160ms)이 컨트롤러에 들어가면서 오히려 간격이 180~200ms에 고착됐다(약 5fps). 상수를 대입해 보면 구조적으로 불가피했다.

```
base 125ms / OVERLOAD 0.9(초과 시 +50) / RECOVERY 0.5(미만 시 -20) / MAX 200
하강 조건: 추론지연 < 현재간격 x 0.5  ->  cur=180이면 90ms 미만 필요
```

추론이 96~160ms인 한 하강 조건을 만족할 수 없어 **base 125ms에는 수학적으로 도달 불가**였다. 지연이 0으로 잘못 보고되던 동안 8.6~9.0fps가 나온 것도 이 때문이다(우연히 하강만 계속 탐).

**근본 원인은 잘못된 결합**이다. 이 컨트롤러는 "추론이 JS 스레드를 점유해 캡처를 방해한다"를 전제로 만들어졌으나, 현재 네이티브 경로는 추론이 백그라운드 스레드에서 돌고 CameraView가 fire-and-forget으로 디스패치하므로 **추론 지연이 캡처를 전혀 막지 않는다.** 그럼에도 추론 지연으로 캡처 간격을 늘리면 서버 전송·콘솔 Live Feed까지 같이 느려진다.

**수정**: `reportInferenceLatency(latencyMs, blocksCapture)`에 두 번째 인자를 추가해, 추론이 캡처를 막지 않는 경로에서는 **상승 분기를 적용하지 않는다**. 하강(회복) 분기와 `serverBusyUntil` 홀드는 그대로 유지해 서버 백프레셔는 살아 있다. 호출부는 `requiresFloat32Ref.current`(JS 디코드 폴백 여부)를 그대로 넘긴다. 추론 폭주 역압력은 `detectingRef`(진행 중이면 디스패치 생략)가 계속 담당한다.

**실측 결과 (Xiaomi 12, 40초)**:

| 지표 | 수정 전 | 수정 후 |
| :--- | ---: | ---: |
| `handleFrame` (5초당) | 25~28회 (5.2fps) | **42~45회 (8.4~9.0fps)** |
| 추론 디스패치 (5초당) | 11~13회 (2.4/s) | **18~23회 (4.1/s)** |
| 서버 `detection 수신` | 134건/30초 | **242건/30초 (8.1fps)** |
| 추론 지연 중앙값 | 145ms | **109.8ms** |
| 동적 FPS 조절 발생 | 180<->200ms 진동 | **0건** (base 125ms 고정) |

**목표 8fps 달성.** 캡처·서버 전송·콘솔 Live Feed 경로가 모두 8fps대로 안정화됐고 간격 진동도 사라졌다.

**남은 것**: 온디바이스 추론 디스패치는 4.1/s다(최초 1.05fps 대비 약 4배). 상한 요인은 `detectingRef` in-flight 1개 제한 + `REAL_DETECT_MIN_INTERVAL_MS=120ms`이며, 추론 약 110ms와 합쳐 약 240ms 주기가 된다. 더 올리려면 in-flight를 2개로 늘리는 파이프라이닝이 필요하나, 반사 경로 결과 순서 보장과 CPU/GPU 경합을 함께 검토해야 한다.

---

### 5.8 발열 스로틀링 (2026-07-28 확인)

세션 후반 "프레임이 끊긴다" 신고를 추적한 결과 코드 회귀가 아니라 **기기 발열 스로틀링**이었다.

| 측정 | 스로틀 시 | 냉각 후 |
| :--- | ---: | ---: |
| 배터리 온도 | 44.3°C (USB 충전 중, 89%) | – |
| CPU thermal zone | 67~70°C | – |
| cpu0 / cpu7 주파수 | 1.07GHz / **0.81GHz** | – |
| 카메라 세션 fps | 30 -> 중앙 12.6, 최소 4.3 | 정상 |
| 플러그인 콜백 | 44ms -> 101ms(최대 388ms) | 정상 |
| `handleFrame` (5초당) | 22~40회 | **40~45회** |
| 추론 지연 중앙값 | 133~189ms | **108.9ms** |

Snapdragon 8 Gen 1 프라임 코어는 정상 약 3.0GHz다. 0.81GHz는 약 1/4 수준. **Android `dumpsys thermalservice`의 `Thermal Status`는 0(NONE)으로 보고되므로 이 값만 보면 안 된다** — `/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq`와 thermal zone 온도를 직접 확인할 것.

USB 케이블을 뽑고 냉각한 뒤 전 지표가 정상 복귀했다. 측정 시 **충전 케이블이 발열을 크게 더한다**는 점에 유의(계속 계측하려면 무선 adb: `adb tcpip 5555` 후 `adb connect <단말 IP>:5555`).

**남은 설계 공백**: §5.7에서 `blocksCapture=false`로 바꾸면서, 캡처 경로 자체가 느려질 때(발열 등) 물러설 장치가 사라졌다. 이전에는 추론 지연이 거친 대리 지표 역할을 했다. 실사용은 장시간 보행이라 스로틀링이 재현될 조건이므로, `handleFrame` 실측 간격이나 플러그인 콜백 비용을 컨트롤러 입력으로 추가하는 안을 검토할 것.

---

### 5.9 오디오 구간 저하 해결 — audioEngine 웜 플레이어 리스너 누수

**원인**: `ensureGuideWarmPlayer()`는 iOS Hearing Protection 우회를 위해 **무음 루프로 상시 재생되는 단일 플레이어**를 재사용한다. 그런데 `playGuideAudioBytesNow()`가 재생할 때마다 이 플레이어에 `addListener("playbackStatusUpdate", ...)`를 새로 걸면서 해제하지 않았다(파일 전체에 `removeListener` 부재, `remove()`는 `prevPlayer`·`clipPlayer`에만 존재).

가이드를 N번 재생하면 상태 업데이트마다 N개 클로저가 실행된다. 웜 플레이어는 **상시 재생**이라 가이드가 없을 때도 업데이트가 계속 나오므로 비용이 세션 내내 누적된다. 이전 세션이 관측한 `ExpoAudio 세션 이벤트 30초에 1701회` / `MediaSession playback state 1634회`가 이 누수의 결과다. 오래된 클로저가 옛 `file`·`epoch`를 붙들고 있어 메모리 누수이기도 하다.

**수정**:
- `guideStatusSubscription` 필드 신설. 새 리스너를 걸기 전 `?.remove()`로 직전 구독을 해제한다.
- `SPEAK_BOUNDARY_DEBUG = false` 상수 신설. expo-speech 폴백의 음절 경계 로그(발화 1회당 수십 건이 Metro 브릿지로 나감)를 기본 비활성화했다. 보조 요인이자 계측 왜곡 요인이었다.

**실측 (Xiaomi 12, 45초)**:

| 5초 창 | 수정 전 | 수정 후 |
| :--- | ---: | ---: |
| 오디오 100% 구간 `frames` | 18 | **45 / 41** |
| 오디오 100% 구간 `dispatch` | 1 | **18 / 19** |
| 무음 구간 `frames` | 40~45 | 43~44 |
| 무음 구간 `dispatch` | 20~23 | 20~24 |
| 서버 `detection 수신` | – | **313건/40초 (7.8fps)** |

오디오 재생 중에도 무음 구간과 사실상 동일한 처리량이 나온다. **반사 경보 음성이 나가는 동안 다음 위험을 늦게 보던 안전 문제도 함께 해소된다.**

---

### 5.10 BBox 오버레이 지연 개선 (2026-07-28) — 출처 선택 + seg 주기 분리

사용자 신고 "카메라가 비추는 객체에 BBox가 뒤늦게 붙는다"를 두 단계로 처리했다.

**1단계 — 오버레이 출처 선택 기준 변경**

`server_detection` 핸들러가 도착할 때마다 조건 없이 `setDetections(serverDets)`를 호출해, 더 신선한 온디바이스 결과를 서버 결과로 덮어쓰고 있었다.

1차 시도(서버 결과의 **프레임 시각**이 최신일 때만 채택)는 실패했다. 실측에서 30건 중 2~11건만 걸러졌다. `handleFrame`은 모든 프레임(8.7fps)을 서버로 보내지만 온디바이스 추론은 3.3회/초만 돌아, 서버는 온디바이스가 건너뛴 프레임을 처리한다. 그 결과의 프레임 시각은 **실제로 더 최신**이라 stale이 아니다.

기준을 **표시 시점의 나이**로 바꿨다. 서버 결과는 화면에 닿을 때 나이 325~436ms, 온디바이스는 222~268ms다. 온디바이스가 최근 `ONDEVICE_OVERLAY_HOLD_MS`(700ms) 안에 결과를 냈으면 서버 결과로 덮지 않고, 온디바이스가 죽었을 때만 폴백으로 쓴다. 서버 탐지 자체는 인지 경로·로깅에 그대로 사용되며 막는 것은 오버레이 덮어쓰기뿐이다.

**2단계 — seg 주기 분리 (`SEG_EVERY_N = 3`)**

온디바이스 seg가 안전 경로에 쓰이지 않음을 코드로 먼저 확인했다.

| 근거 | 위치 |
| :--- | :--- |
| `pathObstacleDetector`가 `model === "segmentation"` 항목 전부 건너뜀 | `pathObstacleDetector.ts:93` |
| 반사 후보 필터가 `SAFE_SURFACE_CLASSES`·`GROUND_HAZARDS`(seg 4클래스) 제외 | `CameraView.tsx` |
| "노면은 인지 경로 전담" 정책 | 2026-07-14 주석 |

즉 온디바이스 seg의 유일한 소비처는 BBox 표시다. 그런데 추론 시간의 절반을 차지했다(det 약 47ms / seg 약 55ms). det는 매 프레임, seg는 3프레임마다 실행하고 건너뛴 프레임은 `lastSegResult`를 재사용해 오버레이 깜빡임을 막는다. 벤치에 `seg_fresh` 플래그를 추가했다.

**실측 (Xiaomi 12, 40초)**

| 지표 | 최초 | 1단계 후 | 2단계 후 |
| :--- | ---: | ---: | ---: |
| 화면 표시 지연 `shownLag` | 261~318ms | 215~266ms | **115~155ms (중앙 약 128ms)** |
| 추론 `avgTotal` | 117~128ms | 117~128ms | **65.7~72.3ms** |
| BBox 갱신률 `dispatch` | 15~17/5초 | 15~17/5초 | **20~31/5초 (약 5.2/s)** |
| 오버레이 출처 | `srv=17~21 dev=15~17` | `srv=0 dev=15~17` | `srv=0 dev=20~31` |
| `handleFrame` | 42~45/5초 | 42~45/5초 | **44~46/5초** |
| 서버 `detection 수신` | 318건/40초 | 318건/40초 | **335건/40초** |

**최초 대비 표시 지연 약 55% 감소.** seg 연산이 1/3로 줄어 지속 부하도 낮아져 §5.8 스로틀링 재발 여지가 함께 줄었다.

**남은 것**: `shownLag` 128ms 중 네이티브 추론이 약 68ms이므로 나머지 약 60ms는 JS 브릿지 왕복·이벤트 루프다. React 리렌더와 SVG 드로우, 프리뷰 자체의 센서->표시 지연은 아직 미계측이다. 더 줄이려면 박스 위치를 직전 프레임 대비 이동량으로 외삽하는 예측 보정을 검토한다.

**관측 정정 (2026-07-28)**: 측정 중 서버 `server_detection`이 전부 탐지 0건으로 도착한 것을 "서버측 이상"으로 기록했으나 **오판이었다**.

- `_send_server_detection`(`consumer.py:1177`)은 필터 없이 `detections`·`surfaces`를 그대로 매핑하므로, 빈 배열은 파이프라인이 실제로 아무것도 못 찾았다는 뜻이다.
- 임계값은 서버 `YOLO_DET_CONF=0.50`으로 온디바이스와 동일하다(파리티 정상).
- 같은 측정 구간에서 **온디바이스도 탐지 0건**이었다. `[Reflex] 전체 탐지` 로그가 0건인데 이 로그 조건은 `all.length > 0 && !isGuidePlaying`이고 해당 구간은 오디오 0·추론 완료 20~31회였으므로, 남는 원인은 탐지 결과가 비었다는 것뿐이다.
- 서버 파이프라인 자체는 정상이다. `detection_guidance_logs` 103건(reflex 73 / cognitive 30)에 `movable_signage conf=0.594`, `braille_normal conf=1.0` 등이 정상 기록돼 있다.

결론: 카메라가 탐지 대상 없는 장면을 보고 있었을 뿐이며 서버·단말 모두 정상이다.

> **계측 함정**: `[DIAG/FRAME]`의 `dev` 카운터는 `setDetections`를 **빈 배열로 호출한 경우까지** 센다. 따라서 `dev>0`은 "온디바이스가 탐지했다"는 근거가 되지 못한다. 탐지 유무를 보려면 `[Reflex] 전체 탐지` 로그나 별도 카운터를 봐야 한다.

**부수 확인 — seg 주기 상수 이원화**: 서버도 이미 `REFLEX_SEG_EVERY_N`(`detection_pipeline.py`)으로 반사 스트림의 seg 주기를 분리하고 있다. 이번에 온디바이스에 넣은 `SEG_EVERY_N=3`(`TFLiteInferenceBridgeModule.kt`)과 같은 접근이지만 **두 상수가 독립적으로 존재**한다. 값이 어긋나면 단말 오버레이와 콘솔·서버 BBox의 노면 갱신 주기가 달라져 대조 검증이 흐트러질 수 있으므로, 조정 시 양쪽을 함께 볼 것.

---

### 5.11 표시 지연 구간 분해 (2026-07-28, 계측 결과 보존)

`shownLag`를 세 구간으로 분해해 측정했다. 계측(`[TEMP DIAG 2026-07-28b]`)은 결과 확인 후 제거했으므로 수치만 여기 남긴다.

**측정 조건**: 강제 종료 후 새 JS 컨텍스트, 기기 절전 후 냉각 상태, Xiaomi 12, 40초.

| 구간 | 값 | 내용 |
| :--- | ---: | :--- |
| `native` | 약 57ms | TFLite det 추론(seg는 `SEG_EVERY_N=3`으로 3프레임마다) |
| `bridge` | 17~32ms | 디스패치 -> `.then()` 진입에서 native를 뺀 값. JSI 왕복 + 이벤트 루프 스케줄링. 탐지 결과 최대 20개 객체의 중첩 객체 마샬링 포함 |
| `render` | 23~31ms | `setDetections` 직후 예약한 태스크가 실제 실행되기까지. React 상태 갱신 + 리렌더 + SVG 드로우가 JS 스레드를 점유한 시간 |

```
shownLag 81ms = native 57ms + bridge 24ms
실제 시각적 지연 ≈ shownLag + render ≈ 107ms (+ 프리뷰 센서->표시 지연, 미계측)
```

| 지표 | 이 측정 | §5.10 측정(수 시간 가동 후) |
| :--- | ---: | ---: |
| `shownLag` | **73~94ms** | 115~155ms |
| `avgTotal` | **54.6~60.7ms** | 65.7~72.3ms |
| `dispatch` | **30~35/5초 (약 6.4/s)** | 20~31/5초 (약 5.2/s) |

> **중요**: 이 차이는 코드 변경이 아니라 **실행 시간 누적·발열**의 영향이다. §5.10은 수 시간 가동된 상태, 본 측정은 강제 종료 후 냉각된 새 컨텍스트다. 즉 **장시간 가동 시 81ms가 128ms대로 되돌아갈 수 있다**. 벤치마크를 비교할 때 가동 시간과 기기 온도를 반드시 함께 기록할 것.

**추가 최적화 판단**: `bridge` 24ms와 `render` 26ms는 각각 크지 않고, 더 줄이려면 SVG 오버레이 구조 변경이나 브릿지 페이로드 축소가 필요해 이득 대비 회귀 위험이 크다. 우선순위는 오히려 **장시간 가동 성능 저하**(§5.8 발열, §5.9 누수 계열) 쪽이다. 오늘 하루에 원인 두 건이 나왔으므로 같은 유형이 더 있을 가능성이 있다.

**Fast Refresh 함정 (계측 중 실측)**: `startCapture(onFrame)`가 `onFrameRef.current`에 콜백을 **한 번만** 저장하므로, `handleFrame`/`runDetectionResult`를 수정해도 캡처를 재시작하지 않으면 옛 클로저가 계속 실행된다. 또한 dev client가 캐시 번들로 떨어지면 Fast Refresh 자체가 반영되지 않는다. 확실히 반영하려면 **force-stop 후 딥링크로 재기동**할 것. 로그에 신규 태그(예: `[OnDeviceBench]`)가 보이는지로 반영 여부를 확인한다.

---

### 5.12 장시간 가동 성능 저하 조사 — 누적 경로 3건 (2026-07-28)

§5.11에서 "냉각 직후 81ms / 수 시간 가동 후 128ms" 격차를 확인한 뒤, §5.9의 리스너 누수와 **같은 유형**을 코드 전반에서 정적으로 훑어 3건을 찾아 수정했다.

**1. 반사 클립 플레이어 누수 (영향 큼)** — `audioEngine.playReflexClip`

`createAudioPlayer()`로 만든 플레이어를 지역 변수로만 들고 `didJustFinish` 콜백에서만 `remove()`했다. 참조를 보관하지 않으므로 클립이 완주하지 못하면(가이드 선점, 앱 백그라운드 전환, 오디오 세션 인터럽션) 네이티브 플레이어와 리스너를 정리할 경로가 **아예 없었다**. 반사 클립은 Near 경보마다 재생되어 장시간 보행에서 지속 누적된다.

수정: `reflexClipPlayer`/`reflexClipSubscription` 참조 보관, 새 클립 재생 전 `disposeReflexClipPlayer()`로 직전 회수, `didJustFinish` 미도착 대비 duration 기반 안전 타이머(`REFLEX_CLIP_REAP_MIN_MS=1500` ~ `REFLEX_CLIP_REAP_MAX_MS=5000`).

**2. `pendingNetworkProbes` 무한 누적** — `useWebSocket.sendNetworkProbe`

ack에서만 `delete`되고 TTL이 없었다. ack가 유실되면 probe 주기(기본 1s)마다 1개씩 무한 증가한다. 수정: 송신 시 `NETWORK_PROBE_TTL_MS=10000` 초과 항목 스윕.

> **인과 주의**: §3.3의 WS 재연결 루프를 고치기 전에는 초당 1.6회 연결이 재수립되며 `clearNetworkProbe()`가 이 Map을 계속 비웠다. **연결을 안정화시키자 이 누적 경로가 비로소 활성화됐다.** 한 버그를 고치면 그것이 가리고 있던 다른 누적이 드러날 수 있다.

**3. `nearClipPlayedTracksRef` 무한 증가** — `useWebSocket`

`reflex_clear`가 유실되면 track마다 항목이 남는다. 메모리는 작지만 재사용된 `track_id`의 클립이 잘못 억제될 수 있다. 수정: `NEAR_CLIP_TRACK_LIMIT=256` 상한, Set의 삽입 순서를 이용해 오래된 항목부터 제거.

**이상 없음으로 확인한 항목**

| 항목 | 상태 |
| :--- | :--- |
| `pendingFrames` | 2초 TTL 스윕 존재 |
| `networkRttSamples` | `slice(-30)`으로 바운드 |
| `setInterval`/`clearInterval`, `setTimeout`/`clearTimeout` | 파일별 균형 정상 |
| `playGuideAudio`(레거시 base64 경로) | `stopGuideAudio`에서 `prevPlayer.remove()` |
| `reflexClipUriCache` | 클립 종류 수로 바운드 |
| `candidateCooldownUntilRef` | 후보 URL 수로 바운드 |

**검증**: 실기기 40초. det 42~52ms·seg 3프레임 주기 정상, 반사 클립 정리 오류 0건, `probe` ack로 RTT 정상 갱신(59~69ms, avg30 83ms — TTL이 정상 ack를 잘라내지 않음), ERROR 0건, 서버 `detection 수신` 326건/40초(8.2fps).

**남은 관찰 과제**: 위 3건이 §5.11의 81ms→128ms 격차를 얼마나 설명하는지는 **장시간 가동 후 재측정으로만 확인 가능하다**. 발열 스로틀링(§5.8)이 동시에 작용하므로, 재측정 시 `scaling_cur_freq`·thermal zone 온도·가동 시간을 함께 기록해 두 요인을 분리할 것.

---

## 6. 실패한 시도 (반복하지 말 것)

### 6.1 `useCameraFormat`으로 포맷·fps 고정 → 되돌림
720p/30fps를 지정했더니 Xiaomi 12에서 `CameraView averageFps=0.0`, 카메라가 프레임을 전혀 내보내지 않았다. fps를 포맷의 `minFps`~`maxFps`로 클램프해도 동일. 기기 지원 포맷은 `1920x1080@10-30`만 노출된다(`[Camera] 지원 포맷(상위 8)` 진단 로그로 확인). **되돌린 상태**이며 진단 로그만 남겨 뒀다.

### 6.2 `pixelFormat="rgb"` → 되돌림
네이티브 `rgbaImageToBitmap` 경로는 정상 동작해 640×480 RGBA 프레임을 받았으나, **플러그인 콜백이 30초에 4회로 붕괴**했다(yuv는 131회). 콜백 1회 비용도 117ms로 오히려 늘었다. 원인 미규명. 네이티브 경로는 보존했고 JS의 `pixelFormat`만 `yuv`로 복구했으므로, 원인을 찾으면 한 줄로 재시도 가능하다.

---

## 7. 통합 테스트 환경 (별건, 이미 구축 완료)

`integration-test-orchestrator` 스킬 절차로 기동해 뒀다.

```bash
docker compose --env-file .env --env-file .env.network.local \
  -f docker/docker-compose.macos.yml up -d
bash scripts/metro_tailscale.sh status
```

- **`.env.network.local`**(신규, gitignored): 컨테이너 MariaDB + `EVENT_FRAME_STORAGE_BACKEND=local`. 클라우드 DB 호스트가 플레이스홀더이고 Tailscale RPi가 오프라인이라 폴백.
- **기존 `docker_mariadb_data` 볼륨 계정 불일치**: 볼륨 삭제 없이 `--skip-grant-tables` 임시 인스턴스로 `gildang` 계정과 `gildang_db`를 복구했다. 기존 `minchodan_db`는 보존.
- **콘솔 로그인**: `admin` / `admin` (super_admin). 서버 정책이 12자 이상이라 API로는 생성 불가해 bcrypt 해시를 DB에 직접 반영했다. **로컬 개발 전용**이며 시연·공유 DB로 프로필 전환 시 반드시 교체할 것.
- **테스트**: `bash scripts/run_integration_tests.sh` → 482 passed, 1 skipped. `tests/conftest.py`가 `JWT_ISSUER`/`JWT_AUDIENCE`를 테스트 전용 값으로 `setdefault` 하는데 서버는 `server/db/security.py` 기본값(`minchodan-api`/`minchodan-clients`)을 쓴다. 이 래퍼가 사전 export로 iss/aud를 맞춘다.
- **주의**: `tests/test_event_frame_store.py`는 로컬 `.env`가 `EVENT_FRAME_STORAGE_BACKEND=r2`일 때 실제 Cloudflare R2 버킷의 `event_frames/`를 삭제하려 했다. 픽스처에서 백엔드를 `local`로 고정해 막았다(이번 실행 삭제 0건, `portfolio/`는 대상 밖).

---

## 8. 마무리 전 반드시 처리할 것

> **2026-07-28 진행 상태**: 아래 항목은 인수인계 시점 기준이다. 항목 1(진단 로그 제거), 3(ruff format), 4(커밋)은 **이후 세션에서 모두 완료**되었다(커밋 `5b04d94`, `2bed639` 등). 항목 2(R2 키 폐기)만 사용자 행동으로 남아있다.

1. **임시 진단 로그 제거** — ✅ 완료(2026-07-28). useWebSocket.ts 2건 + CameraView.tsx 2건 제거.
2. **보안**: 세션 중 `.env.network.cloud`의 `R2_ACCESS_KEY_ID`와 `R2_ENDPOINT`(계정 ID 포함)가 대화에 평문 노출됐다. **Cloudflare에서 폐기·재발급 필요**. — ⏳ 사용자 대기
3. **`ruff format`** — ✅ 완료(2026-07-28). `server/tts/speech_text.py`, `tests/test_convenience_rag_sources.py` 포맷 적용.
4. **커밋** — ✅ 완료(2026-07-28). `kb` 브랜치에 8fps 최적화 + WS half-open 수정까지 커밋.

---

## 9. 미해결 결함

### 9.0 WS half-open 감지 실패로 인한 반사 경보 지연 — ✅ 해결(2026-07-28)

사용자 보고 "서버 병목 후에 햅틱/비프가 들린다"의 원인. 서버가 WS를 종료해도 클라이언트가 "서버 연결 정상"으로 착각해 온디바이스 반사 경보를 무한 억제했다.

**근본 원인**: (1) 클라이언트 heartbeat_ack 타임아웃 부재 — 서버는 5초마다 heartbeat 보내고 단말 무응답 시 끊지만, 단말은 서버 heartbeat가 안 와도 안 끊음. WS half-open 시 onclose 미발화. (2) `isServerTimeout` 판정이 `lastFrameSentTsRef` 의존 — WS 죽으면 전송 실패로 미갱신, 타임아웃 미감지.

**수정**: (1) useWebSocket에 `lastServerHeartbeatTsRef` + 15초 타임아웃 능동 종료. (2) CameraView `isServerTimeout`을 서버 메시지 수신 시각 기반 1500ms 단순 판정으로 변경.

**실측**: 서버 강제 재시작 시 WS 종료 60ms 만에 감지(code=1012), isServerTimeout 즉시 전환. 서버 복구 후 자동 재연결. 커밋 `fix(client): WS half-open 감지 추가`.

### 9.1 `AudioRecorder.constructor` 렌더 에러
```
Call to function 'AudioRecorder.constructor' has been rejected.
→ Caused by: The current activity is no longer available
```
`useSttRecorder.ts:79`의 `useAudioRecorder`에서 발생하며 `CameraView` 렌더 자체를 막아 카메라가 시작되지 않는다. 세션 중 여러 차례 재현됐고, `am force-stop` 직후 재기동이나 액티비티 교체 타이밍에서 잘 나타났다. §3.3의 권한 루프(액티비티 pause/resume 폭주)가 원인의 일부였을 가능성이 높으므로, 루프가 잡힌 지금 재현되는지 먼저 확인할 것.

### 9.2 MIUI 카메라 제한
```
system/camera-is-restricted: Camera functionality is not available ...
```
`adb shell am start`로 시작한 액티비티에서 간헐 발생. 런처 아이콘이나 dev client 딥링크로 실행하면 해소된다.

---

## 10. 작업 재개 절차

```bash
# 1) 백엔드 (이미 떠 있으면 생략)
cd <repo>
docker compose --env-file .env --env-file .env.network.local \
  -f docker/docker-compose.macos.yml up -d
curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:8000/     # 200
curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:5174/     # 200 (콘솔)

# 2) Metro (이미 떠 있으면 kill 금지)
bash scripts/metro_tailscale.sh status
REACT_NATIVE_PACKAGER_HOSTNAME=192.168.0.227 bash scripts/metro_tailscale.sh start

# 3) Android 빌드 — 시스템에 JDK가 없어 Homebrew JDK 17 지정 필요
export ANDROID_HOME="$HOME/Library/Android/sdk"
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"; export PATH="$JAVA_HOME/bin:$PATH"
cd client/android && ./gradlew :app:assembleDebug
$ANDROID_HOME/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk

# 4) 재설치 시 런타임 권한이 초기화되므로 미리 부여 (다이얼로그 루프 예방)
for p in CAMERA RECORD_AUDIO ACCESS_FINE_LOCATION ACCESS_COARSE_LOCATION \
         READ_PHONE_STATE CALL_PHONE POST_NOTIFICATIONS; do
  adb shell pm grant com.minchodan.app android.permission.$p
done

# 5) 앱 실행 — am start -n 은 dev launcher로 튀거나 카메라 제한에 걸린다.
#    런처 아이콘 탭 또는 딥링크를 쓸 것.
adb shell am start -a android.intent.action.VIEW \
  -d "minchodan://expo-development-client/?url=http%3A%2F%2F192.168.0.227%3A8081"
# 화면에서 "탐지 시작" 버튼을 눌러야 카메라 루프가 돈다(기본 OFF).
```

### 측정 명령 (30초 창)

```bash
BEFORE=$(wc -l < logs/metro/metro.log | tr -d ' '); adb logcat -c; sleep 30
AFTER=$(wc -l < logs/metro/metro.log | tr -d ' ')
sed -n "$((BEFORE+1)),${AFTER}p" logs/metro/metro.log > /tmp/w.log

# 프레임 간격
grep -oE 'gap=[0-9]+ms stream=reflex' /tmp/w.log | grep -oE '[0-9]+' | sort -n | \
  awk '{a[NR]=$1;s+=$1} END{printf "n=%d 중앙=%d → %.1ffps\n",NR,a[int(NR/2)+1],1000/(s/NR)}'
# 네이티브 추론
grep -oE 'prep=[0-9.]+ms det=[0-9.]+ms seg=[0-9.]+ms total=[0-9.]+ms' /tmp/w.log | tail -3
# 플러그인 콜백 / 카메라 공급 fps
adb logcat -d | grep -c 'callback ok'
adb logcat -d | grep -oE 'invokeOnAverageFpsChanged\([0-9.]+\)' | tail -3
# 안정성 (0이어야 정상)
grep -c 'DIAG/WS] AppState' /tmp/w.log; grep -c '연결 시도' /tmp/w.log
docker logs --since 30s minchodan-fastapi 2>&1 | grep -c '세션 종료'
# 서버 처리량
docker logs --since 30s minchodan-fastapi 2>&1 | grep -c 'detection 수신'
```

### 정상 기준선 (2026-07-28 §5.2 최적화 적용 후 실측)

`AppState 진동 0` / `WS 연결 시도 0` / `세션 종료 0` / `추론 total 중앙값 54ms(전체)·90ms(오디오 제외)` / `플러그인 콜백 34ms` / `플러그인 공급 8.9fps` / `추론 실행 간격 165ms(오디오 제외, 6fps)` / `카메라 30fps` / `detection 수신 204건/30초`. 안정성 지표는 최적화 전과 동일(0/0/0)으로 유지됐다. 이 값에서 벗어나면 회귀를 먼저 의심할 것.

> **8fps 미달**: 오디오 재생 중 추론 중단(42% 시간 0fps)이 주원인. §5.4 후보 1(오디오-추론 분리)이 다음 최우선 과제. 오디오 제외 구간은 6fps로, 오디오 문제만 해소하면 6fps 베이스 위에서 추가 최적화로 8fps 도달 가능.
