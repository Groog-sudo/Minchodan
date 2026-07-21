# Android 작업 인수인계서 (kb → Android 담당)

> **작성일**: 2026-07-21
> **버전**: v1.0.0
> **작성**: kb (관범) / **인수**: Android 담당 (dg 계열 권장)
> **기준 브랜치**: `kb` (로컬 tip `239d5b0`, `origin/kb` 대비 **ahead 2 · 미푸시**)
> **관련 문서**: [`android_ios_parity_checklist.md`](android_ios_parity_checklist.md), [`ios_android_bifurcation_contract.md`](ios_android_bifurcation_contract.md), [`../ops/wireless_test_guide.md`](../ops/wireless_test_guide.md)
> **목적**: Gemini/Android 정합 시도·실기기 검증 결과를 바탕으로, Android 담당자가 바로 이어서 종단 P0를 닫을 수 있게 상태·위험·잔여 작업을 인수인계한다.

---

## 0. 한 줄 요약

| 항목 | 상태 |
| :--- | :--- |
| Android **코드 골격** (FP·TFLite·AEC 모듈) | 이미 저장소에 존재. 제미나이가 “처음부터 구현”한 것은 아님 |
| 제미나이 추가 작업 | 주석 정정 + `CameraView` 로컬 반사 정책 **공통화** (로컬 커밋 2개, **미푸시**) |
| **P0 실기기 통과 주장** | **기각**. Samsung SM-S938N 연결까지는 됐으나 Metro/서버 종단 미연결 |
| **iOS 영향** | `CameraView` 통일 커밋은 **iOS 런타임을 변경함**. 푸시·merge 전 팀 승인 필요 |

**인수자 최우선**: (1) 단말 네트워크(Tailscale 또는 동일 Wi‑Fi) 복구 → (2) Dev Client + Metro 번들 로드 → (3) A-S1~S7 실측 → (4) `CameraView` iOS 영향 승인/롤백 결정 후 push.

---

## 1. 인수 범위와 비범위

### 1.1 인수 범위

- Android 실기기 종단 검증 (캡처·TFLite·WS·오디오·STT)
- [`android_ios_parity_checklist.md`](android_ios_parity_checklist.md) P0 잔여 항목 마감
- 제미나이 로컬 커밋 2개의 코드 리뷰·승인·푸시(또는 수정/롤백)
- `docs/changelogs/dg.md` 과대 주장(“P0 전수 통과”) 정정

### 1.2 비범위 / 건드리지 말 것

- `server/detection/gates/`에 LLM/RAG/TTS import
- `.env` 실값 커밋, `docker compose down -v`, 원격 DB DDL
- iOS 전용 네이티브(`CoreMLInferenceBridge`, `DepthProbeBridge` 등) 임의 수정
- 공유 인프라(`.env.example` 기본값, `docker-compose*.yml` 서비스 삭제, `requirements.txt` 마커 없는 OS 패키지)

파일 소유권은 [`ios_android_bifurcation_contract.md`](ios_android_bifurcation_contract.md) §2~§3을 따른다.

---

## 2. 현재 Git / 코드 상태

### 2.1 브랜치

| ref | tip (작성 시점) | 비고 |
| :--- | :--- | :--- |
| `origin/kb` | `68c4a30` | 정합 체크리스트 문서 등재까지 푸시됨 |
| 로컬 `kb` | `239d5b0` | **ahead 2, 미푸시** |
| `origin/dev` | 문서 등재 이전/동기화 필요 시 pull 후 재확인 | Android 작업 전 `origin/dev` 동기화 권장 |
| `origin/dg2` | stale (dev 대비 behind 다수) | **이 위에 신규 작업하지 말 것** |

### 2.2 미푸시 커밋 (제미나이/에이전트)

| 해시 | 메시지 | 실체 | 인수자 조치 |
| :--- | :--- | :--- | :--- |
| `959c256` | `refactor: update audioSessionBridge header comment for android parity` | JSDoc만. Android no-op stale 주석 제거 | 수용 가능 (런타임 무영향) |
| `239d5b0` | `refactor: unify local reflex suppression and fallback policy in CameraView` | `Platform.OS === "android"` 분기 제거, 정책을 **iOS+Android 공통**으로 통합 | **정책 승인 후 푸시** 또는 **롤백 후 Android-only 유지** |

변경 파일 요약:

- `client/src/services/audioSessionBridge.ts` (주석)
- `client/src/components/CameraView.tsx` (**공유 컴포넌트, iOS 영향**)
- `docs/changelogs/dg.md` (P0 통과 주장 포함 — **문구 과대, 정정 필요**)

### 2.3 이미 저장소에 있던 Android 구현 (제미나이 이전)

인수자가 “미구현”으로 착각하지 않도록 명시한다.

| 구성 | 경로 |
| :--- | :--- |
| Frame Processor | `client/android/.../ReflexFrameProcessorPlugin.kt` |
| 캡처 select | `client/src/services/frameCaptureProviderSelect.android.ts` |
| TFLite 추론 | `client/src/inference/localDetectorSelect.android.ts`, `tfliteDetector.ts` |
| AEC | `AudioSessionBridgeModule.kt` + `audioSessionBridge.ts` Android 분기 |
| 모델 자산 | `client/assets/models/yolo26n/*.tflite` (`EXPORT_SOURCE_260714.txt`: det `[1,300,6]`, seg `[1,40,8400]`) |
| 패키지 | `com.minchodan.app` (`client/app.json`) |

계약서 §4.5의 “미착수”는 2026-07-21에 **코드 구현됨**으로 정정됨. 잔여는 **실기기 검증**.

---

## 3. 실기기 검증 결과 (2026-07-21 kb 세션)

로그: `logs/test_sessions/20260721_093640_android_verify/` (로컬, gitignore).

### 3.1 단말

| 항목 | 값 |
| :--- | :--- |
| 모델 | Samsung SM-S938N |
| 시리얼 | R3CY2018Z2L |
| OS | Android 16 (API 36) |
| adb | USB `device` (허용 완료) |
| 앱 | `com.minchodan.app` 설치됨, lastUpdate **2026-07-20** |
| Secure Folder | user 150 존재 → `pm list packages` 일부 SecurityException 가능 (user 0 기준 확인) |

### 3.2 온디바이스

| 항목 | 결과 |
| :--- | :--- |
| `NitroTflite` / `libNitroTflite.so` | **로드 성공** |
| TFLite 런타임 / XNNPACK | 초기화 로그 확인 |
| JS에서 모델 shape·추론·경보 | **미확인** (번들 미로드) |

### 3.3 네트워크·Metro·서버 (실패)

| 검사 | 결과 |
| :--- | :--- |
| 단말 활성 NIC | **셀룰러(rmnet)만**. Wi‑Fi 미연결 |
| Tailscale 앱 | `com.tailscale.ipn` 설치됨 |
| `ping/tcp 100.121.247.4:8000/8081` | **FAIL** (VPN 미활성 또는 미도달) |
| Mac LAN `192.168.0.227` | **FAIL** |
| `client/.env` | `EXPO_PUBLIC_NETWORK_MODE=tailscale` |
| Metro (호스트) | localhost + Tailscale IP **200** (호스트는 정상) |
| Dev Client 번들 | `Unable to load script` → DevLauncher 에러 화면 |
| `adb reverse tcp:8081/8000` | 터널 OK, 기기 `127.0.0.1:8081` nc 성공. 그래도 asset 로드 경로로 실패하는 사례 확인 → **Dev Client에서 bundler URL 재지정 필요** |
| FastAPI `device_id=dev-001` 프레임 | 세션 중 관측됐으나 **iPhone과 device_id 공유 가능**. Android 단독 종단으로 단정 금지 |

### 3.3.1 호스트 측 (인수 시 참고)

작성 시점 Mac 통합 테스트 환경:

- Compose: `docker/docker-compose.macos.yml`
- FastAPI YOLO: `object_detection260714.pt` / `segmentation260714.pt` (로컬 `.env`)
- Metro: `scripts/metro_tailscale.sh` (detach OK)
- iPhone도 동일 LAN/Tailscale에 붙어 있을 수 있음 → **Android 검증 시 device_id를 Android 전용으로 분리**할 것

---

## 4. iOS 영향 분석 (필수 확인)

### 4.1 `239d5b0` 전후 차이

| 상황 | 이전 iOS | 통일 후 (현재 로컬) |
| :--- | :--- | :--- |
| 서버 정상 (`!isServerTimeout`) | 로컬 반사 억제·비프 회수 | **동일** (공통 억제) |
| 서버 타임아웃 + 실내 씬 | (별도 실내 억제 없음, area reflex 가능) | **실내면 로컬 경보 억제** (신규) |
| 서버 타임아웃 + 실외 | `applyLocalAreaReflex`만 | `pathObstacleDetector` STOP/BLOCKED/CAUTION + area fallback + **`speakFallback` TTS** (Android 정책 이식) |

결론: **서버 끊김/지연 시 iOS 사용자 체감이 바뀐다.** 이중 경로의 반사 게이트 코드를 깨지는 않지만, 공유 클라이언트 정책 변경이다.

### 4.2 인수자 결정 옵션 (R-00)

| 옵션 | 내용 | 권장 조건 |
| :--- | :--- | :--- |
| **A. 승인 후 푸시** | 공통 정책 유지. iOS 실기기에서 타임아웃 백업 경로 회귀 테스트 | 팀(kb)이 iOS 체감 변경에 합의 |
| **B. 롤백 후 Android만** | `CameraView`를 플랫폼 분기 복구하거나 `.android` 쪽으로 정책 이동 | iOS 변경을 당장 원하지 않을 때 |
| **C. 계약 위반 회피 리팩터** | 공유 파일 내부 `Platform.OS` 확대를 피하고, 정책을 공통 함수 + 얇은 플랫폼 진입으로 재배치 | 중기 권장 (계약서 §2 원칙 1) |

제미나이 changelog의 “이원화 계약서 §2 준수”는 **공유 파일에서 분기를 없앤 것**이지, “iOS 무영향”이 아니다.

---

## 5. 인수 직후 체크리스트 (실행 순서)

### 5.1 환경 준비 (30분)

1. `git fetch` 후 작업 브랜치: `dg` 권장. **`origin/dev`를 최신으로 merge**.
2. 제미나이 커밋이 `kb`에만 있으면: cherry-pick `959c256` `239d5b0` **또는** kb에서 PR 후 정책 승인.
3. Mac: Docker macos compose + Metro (`bash scripts/metro_tailscale.sh status` → UP).
4. Android: **Tailscale ON** 또는 Mac과 **동일 Wi‑Fi**. 셀룰러만으로는 실패 재현됨.
5. `adb devices` → `device`. 필요 시 `adb reverse tcp:8081 tcp:8081` + `tcp:8000`.
6. Dev Client에서 Metro URL을 `127.0.0.1:8081`(USB) 또는 Tailscale/LAN 호스트로 **명시 지정** 후 Reload.

### 5.2 P0 실측 (체크리스트 §10)

| ID | 시나리오 | Pass |
| :--- | :--- | :--- |
| A-S1 | 기동 → 번들 → WS auth_ok | 60s 내. **Android 전용 device_id** |
| A-S2 | 탐지 ON → reflex/cognitive 프레임 | 서버 decode 에러 0 |
| A-S3 | Near 비프+햅틱 | 이중 경보 없음 |
| A-S4 | Medium TTS | 대기열 정상 |
| A-S5 | 서버 강제 종료 → 로컬 폴백 | R-00 결정 정책과 일치 |
| A-S6 | STT | 에코 오탐 없음 (AEC) |
| A-S7 | 노면 라벨 | 서버·로컬 정합 |

상세 ID(M-01~, C-01~, …)는 [`android_ios_parity_checklist.md`](android_ios_parity_checklist.md) §3~§9.

### 5.3 문서 정리

- `docs/changelogs/dg.md`에서 “P0 전수 검증 통과” 문구를 **실측 표 기준으로 축소·정정**
- 실측 결과 표를 dg changelog 또는 PR 본문에 첨부
- 필요 시 본 인수인계서 버전을 bump하며 “인수 완료일 / 담당자” 기입

### 5.4 Gemini 복붙 지시

정합 체크리스트 §0 블록을 계속 사용하되, **첫 보고에 본 인수인계서 §3 실측 실패 원인(네트워크)을 인용**하고, “이미 P0 마감”으로 단정하지 말 것.

---

## 6. 알려진 함정

| 함정 | 대응 |
| :--- | :--- |
| iPhone과 `device_id=dev-001` 공유 | Android `.env` / 설정에서 고유 device_id 사용 |
| Secure Folder (user 150) | `adb shell pm ... --user 0` |
| `NETWORK_MODE=tailscale`인데 VPN OFF | Tailscale 연결 또는 일시 LAN 모드 + 동일 Wi‑Fi |
| Dev Client가 asset 번들만 로드 | bundler URL 재설정, `adb reverse`, Metro status 200 확인 |
| `dg2` stale | `dev` 최신에서 분기 |
| changelog 과대 주장 | 실측 전 “통과” 문구 금지 |
| `lastAndroidTtsTsRef` 이름 | 공통화 후에도 변수명 Android 잔존 — 리네임은 선택(P2) |

---

## 7. 연락·산출물 템플릿

인수 완료 시 Android 담당자 PR/슬랙에 아래를 채운다.

```text
[Android 인수 보고]
- 작업 브랜치 / tip:
- 네트워크 모드 (tailscale|lan) / 단말 IP:
- Metro 번들: OK|FAIL
- WS auth_ok + device_id:
- A-S1~S7 표:
- CameraView R-00 결정: A승인|B롤백|C리팩터
- iOS 회귀(타임아웃 백업): OK|FAIL|미실시
- 푸시/PR URL:
```

---

## 8. 참고 명령 (Mac)

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:/opt/homebrew/opt/openjdk@17/bin:$PATH"

adb devices -l
adb reverse tcp:8081 tcp:8081
adb reverse tcp:8000 tcp:8000

bash scripts/metro_tailscale.sh status
curl -sf -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/status

# 앱 기동 (Dev Client + localhost Metro)
adb shell am start -a android.intent.action.VIEW \
  -d 'minchodan://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8081' \
  com.minchodan.app

adb logcat --pid="$(adb shell pidof com.minchodan.app | tr -d '\r')" | rg -i 'ReactNativeJS|TFLite|LocalReflex|WebSocket|error'
```

서버 YOLO 경로 확인 (비밀 제외):

```bash
docker compose --env-file .env -f docker/docker-compose.macos.yml exec -T fastapi \
  sh -c 'echo DET=$YOLO26N_OBJECT_DET SEG=$YOLO26N_SEG'
```

---

## 9. 변경 이력

| 버전 | 일자 | 내용 |
| :--- | :--- | :--- |
| v1.0.0 | 2026-07-21 | 초판. kb 세션 실기기 검증·제미나이 미푸시 커밋·iOS 영향·인수 체크리스트 정리 |
