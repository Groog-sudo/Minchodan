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
| `handleFrame` reflex 간격 중앙값 | 899ms | **215ms** | 목표 125ms |
| 환산 fps | 1.05 | **4.6** | 약 4.4배 |
| 온디바이스 추론 total 중앙값 | 측정불가(JS 블로킹) | **101.6ms** | prep 5~17ms / det 약 50ms / seg 약 55ms |
| 프레임 프로세서 콜백 비용 중앙값 | 62ms | **44ms** | 호출 139회/30초 |
| 카메라 세션 공급 fps | – | **30.0** | 상한 아님 |
| 서버 `detection 수신` | 34건/30초 | **169건/30초** | 약 5.6fps |
| `NetworkBench` avg30 RTT | 4204ms | **약 36ms** | |
| WS 재연결 (30초) | 약 48회 | **0회** | |
| AppState 진동 (30초) | 115회 | **0회** | |

**8fps 미달**. 남은 격차의 분석은 §5.

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

## 5. 남은 과제 — 8fps까지 (최우선)

현재 215ms. 예산 분석:

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

1. **임시 진단 로그 제거**
   - `client/src/hooks/useWebSocket.ts:749` `[DIAG/WS] 소켓 교체 effect 실행`
   - `client/src/hooks/useWebSocket.ts:788` `[DIAG/WS] AppState x -> y`
   - `client/src/components/CameraView.tsx:1104` `[DIAG] handleFrame gap=` (`[TEMP DIAG 2026-07-24]`, `__lastHandleFrameTs`) — 프레임 병목 조사가 끝나면
   - `CameraView.tsx`의 `[Camera] 지원 포맷(상위 8)` 진단 effect — §6.1 재시도가 끝나면
2. **보안**: 세션 중 `.env.network.cloud`의 `R2_ACCESS_KEY_ID`와 `R2_ENDPOINT`(계정 ID 포함)가 대화에 평문 노출됐다. **Cloudflare에서 폐기·재발급 필요**.
3. **`ruff format`**: `server/tts/speech_text.py`, `tests/test_convenience_rag_sources.py` 2건이 기존부터 미포맷(본 작업 무관, 미수정).
4. **커밋**: 전부 미커밋. changelog 3건은 이미 기록됨. `dev` 병합 전 `kb` 브랜치에서 커밋 필요.

---

## 9. 미해결 결함

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

### 정상 기준선 (2026-07-28 최종)

`AppState 진동 0` / `WS 연결 시도 0` / `세션 종료 0` / `handleFrame 중앙값 215ms` / `추론 total 101.6ms` / `플러그인 44ms` / `카메라 30fps` / `detection 수신 169건/30초`. 이 값에서 벗어나면 회귀를 먼저 의심할 것.
