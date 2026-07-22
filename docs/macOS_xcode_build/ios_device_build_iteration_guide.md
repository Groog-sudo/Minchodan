# iOS 단말 빌드 및 수정 반복 가이드

> **작성일**: 2026-07-11
> **버전**: v0.1.0
> **원본**: `.vscode/ios_device_build_iteration_guide.md`
> **문서 목적**: 개인 단말명, 단말 식별자, bundle id, 로컬 경로를 placeholder로 치환한 팀 공유용 iOS 실기기 빌드 반복 가이드입니다.

---

## 1. 목적

이 문서는 Minchodan React Native iOS 앱을 실제 iPhone 단말에 빌드, 설치, 실행한 뒤 확인 결과를 바탕으로 코드를 수정하고 다시 검증하는 반복 작업 절차를 정리합니다.

Minchodan 클라이언트는 React Native thin client이지만 `react-native-vision-camera`, `react-native-fast-tflite`, Expo 네이티브 모듈, CoreML/TFLite 자산을 포함합니다. 따라서 변경 범위에 따라 Metro reload만으로 충분한 경우와 실제 iOS 재빌드가 필요한 경우를 분리해야 합니다.

---

## 2. 공유용 기준값

| **항목** | **공유 문서용 기준값** | **확인 방법** |
| :--- | :--- | :--- |
| **workspace** | `client/ios/Minchodan.xcworkspace` | `xcodebuild -list -workspace client/ios/Minchodan.xcworkspace` |
| **scheme** | `Minchodan` | `xcodebuild -list -workspace client/ios/Minchodan.xcworkspace` |
| **platform** | `iOS` | 실기기 빌드 시 `platform=iOS` |
| **bundleId** | `<IOS_BUNDLE_ID>` | `xcodebuild -showBuildSettings`의 `PRODUCT_BUNDLE_IDENTIFIER` |
| **앱 이름** | `Minchodan.app` | 빌드 산출물 또는 Xcode Products |
| **권장 Xcode 열기 대상** | `.xcworkspace` | CocoaPods 포함 빌드이므로 `.xcodeproj` 단독보다 workspace 우선 |

> [!WARNING]
> `.xcodebuildmcp/config.yaml`에는 개인 Mac 절대경로와 단말 식별자가 들어갈 수 있습니다. 팀 공유 커밋에는 `<PROJECT_ROOT>`, `<XCODEBUILD_DEVICE_UDID>`, `<COREDEVICE_IDENTIFIER>`, `<IOS_BUNDLE_ID>` 같은 placeholder를 사용합니다.

---

## 3. 전체 흐름

| **순서** | **단계** | **목적** | **성공 기준** |
| :--- | :--- | :--- | :--- |
| 1 | **환경 확인** | Xcode, workspace, scheme 확인 | Xcode 버전 출력, scheme 목록에 `Minchodan` 표시 |
| 2 | **단말 식별자 확인** | `xcodebuild`와 `devicectl`에서 사용할 값을 분리 확인 | 대상 iPhone이 connected 상태 |
| 3 | **Signing 설정** | Xcode가 개발 서명 프로파일을 만들 수 있게 설정 | Team 선택 완료, signing error 해소 |
| 4 | **로컬 기본값 확인** | MCP/CLI 자동화가 참조할 값을 확인 | YAML 파싱 성공, placeholder를 로컬값으로 교체 |
| 5 | **Metro 실행** | JS 번들 제공 및 React Native 런타임 연결 | Metro dev server 대기 |
| 6 | **빌드** | iOS 앱을 Debug 설정으로 실기기용 컴파일 | `Minchodan.app` 산출물 생성 |
| 7 | **설치 및 실행** | 빌드된 앱을 iPhone에 설치하고 전면 실행 | 단말 화면에서 앱 실행 |
| 8 | **앱 확인** | 카메라, 권한, WebSocket, 오디오, 햅틱 확인 | 기대 동작과 실제 동작 비교 가능 |
| 9 | **수정 및 재검증** | 문제를 코드에 반영하고 다시 검증 | 변경 범위에 맞는 reload 또는 재빌드 완료 |

---

## 4. 환경 확인

프로젝트 루트에서 실행합니다.

```bash
xcode-select -p
xcodebuild -version
test -d client/ios/Minchodan.xcworkspace && printf 'workspace exists\n'
xcodebuild -list -workspace client/ios/Minchodan.xcworkspace
```

| **확인 항목** | **정상 기준** | **실패 시 우선 조치** |
| :--- | :--- | :--- |
| **developer path** | Xcode Developer 경로 출력 | `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` |
| **Xcode 버전** | 설치된 Xcode 버전 출력 | Xcode 설치 또는 Command Line Tools 확인 |
| **workspace** | `workspace exists` 출력 | `client/ios`와 CocoaPods 설치 상태 확인 |
| **scheme** | `Minchodan` 표시 | Xcode에서 scheme 공유 설정 확인 |

---

## 5. 단말 연결 확인

실기기는 케이블 연결, 단말 잠금 해제, "이 컴퓨터를 신뢰" 승인, 개발자 모드 활성화가 필요합니다.

```bash
xcrun devicectl list devices
xcrun xctrace list devices
xcodebuild -showdestinations \
  -workspace client/ios/Minchodan.xcworkspace \
  -scheme Minchodan
```

| **구분** | **주로 쓰는 위치** | **공유 문서용 표기** |
| :--- | :--- | :--- |
| **CoreDevice identifier** | `xcrun devicectl list devices` | `<COREDEVICE_IDENTIFIER>` |
| **실기기 UDID** | `xcrun xctrace list devices`, `xcodebuild -showdestinations` | `<XCODEBUILD_DEVICE_UDID>` |
| **단말 이름** | Xcode UI, `devicectl`, `xctrace` | `<IOS_DEVICE_NAME>` |

---

## 6. Apple 계정 및 Signing Team 설정

실기기 빌드는 앱을 iPhone에 설치할 수 있도록 Apple 개발 서명이 필요합니다. `No Accounts`, `No profiles`, `provisioning profiles matching ... were found` 같은 에러가 나오면 이 단계를 먼저 확인합니다.

### 6.1 Apple 계정 로그인

| **순서** | **화면 조작** | **확인할 내용** |
| :--- | :--- | :--- |
| 1 | Xcode 활성화 후 상단 메뉴 **Xcode** 선택 | Xcode가 전면 앱이어야 함 |
| 2 | **Settings...** 선택 | Xcode 설정 화면 열림 |
| 3 | **Apple Accounts** 선택 | 계정 목록 표시 |
| 4 | **Add Apple Account...** 선택 | Apple ID 로그인 창 표시 |
| 5 | 계정 로그인 진행 | Apple ID가 계정 목록에 표시됨 |

### 6.2 Minchodan Target에 Team 선택

| **순서** | **화면 조작** | **확인할 내용** |
| :--- | :--- | :--- |
| 1 | Xcode에서 `client/ios/Minchodan.xcworkspace` 열기 | Pods 포함 workspace 기준 |
| 2 | 왼쪽 탐색기에서 프로젝트 **Minchodan** 선택 | 프로젝트 설정 화면 표시 |
| 3 | `TARGETS > Minchodan` 선택 | `PROJECT`가 아니라 `TARGETS` 기준 |
| 4 | **Signing & Capabilities** 클릭 | signing 설정 화면 표시 |
| 5 | **Automatically manage signing** 체크 | Xcode가 profile 자동 생성 가능 |
| 6 | **Team** 드롭다운에서 로컬 Apple 계정 팀 선택 | 실제 팀명은 문서에 기록하지 않음 |
| 7 | **Bundle Identifier**가 `<IOS_BUNDLE_ID>`와 일치하는지 확인 | CLI 실행값과 일치 필요 |
| 8 | iPhone 잠금 해제 상태로 대기 | 단말 등록 및 profile 생성 |

Signing 자동 생성을 허용한 CLI 빌드는 다음 형태입니다.

```bash
xcodebuild \
  -workspace client/ios/Minchodan.xcworkspace \
  -scheme Minchodan \
  -destination "platform=iOS,id=<XCODEBUILD_DEVICE_UDID>" \
  -configuration Debug \
  -derivedDataPath client/ios/build \
  -allowProvisioningUpdates \
  -allowProvisioningDeviceRegistration \
  build
```

---

## 7. `.xcodebuildmcp/config.yaml` 확인

로컬 자동화나 MCP가 이 파일을 참고하는 경우, 다음 항목을 현재 Mac과 단말에 맞게 로컬에서만 채웁니다.

```yaml
schemaVersion: 1

sessionDefaults:
  workspacePath: "<PROJECT_ROOT>/client/ios/Minchodan.xcworkspace"
  scheme: Minchodan
  deviceId: "<LOCAL_DEVICE_IDENTIFIER>"
  platform: iOS
  bundleId: "<IOS_BUNDLE_ID>"
```

YAML 문법 확인은 다음 명령으로 합니다.

```bash
ruby -e 'require "yaml"; c=YAML.load_file(".xcodebuildmcp/config.yaml"); d=c.fetch("sessionDefaults"); abort("missing workspacePath") unless d["workspacePath"]; abort("missing scheme") unless d["scheme"]; abort("missing deviceId") unless d["deviceId"]; abort("missing platform") unless d["platform"]; abort("missing bundleId") unless d["bundleId"]; puts "config yaml ok"'
```

---

## 8. Metro 실행

앱이 JS 번들을 가져와야 하므로 빌드 또는 실행 전에 별도 터미널에서 Metro를 실행합니다.

```bash
cd client
npm run start -- --clear
```

| **변경 범위** | **Metro만 재시작** | **iOS 재빌드** |
| :--- | :--- | :--- |
| **JS/TS 화면 로직 수정** | 필요할 수 있음 | 보통 불필요 |
| **React hook, 서비스 함수 수정** | 보통 충분 | 네이티브 연결부 변경 시 필요 |
| **Swift/Objective-C 수정** | 불충분 | 필요 |
| **Podfile, native module, Info.plist 수정** | 불충분 | 필요 |
| **권한, entitlements, bundle 설정 수정** | 불충분 | 필요 |
| **앱 번들 모델/오디오 파일 수정** | 대체로 불충분 | 필요 |

---

## 9. CLI로 빌드

먼저 `xcodebuild -showdestinations`에서 실기기 `id`를 확인합니다.

```bash
xcodebuild -showdestinations \
  -workspace client/ios/Minchodan.xcworkspace \
  -scheme Minchodan
```

실기기용 Debug 빌드는 다음처럼 실행합니다.

```bash
xcodebuild \
  -workspace client/ios/Minchodan.xcworkspace \
  -scheme Minchodan \
  -destination "platform=iOS,id=<XCODEBUILD_DEVICE_UDID>" \
  -configuration Debug \
  -derivedDataPath client/ios/build \
  build
```

| **확인 항목** | **정상 기준** |
| :--- | :--- |
| **빌드 결과** | `** BUILD SUCCEEDED **` |
| **산출물 경로** | `client/ios/build/Build/Products/Debug-iphoneos/Minchodan.app` |
| **bundle id** | `<IOS_BUNDLE_ID>` |
| **대상 SDK** | `iphoneos` |

빌드 로그를 파일로 남길 때는 개인 단말명이나 계정 정보가 포함될 수 있으므로 커밋 전에 정리합니다.

```bash
mkdir -p .vscode/xcode_logs
xcodebuild \
  -workspace client/ios/Minchodan.xcworkspace \
  -scheme Minchodan \
  -destination "platform=iOS,id=<XCODEBUILD_DEVICE_UDID>" \
  -configuration Debug \
  -derivedDataPath client/ios/build \
  build 2>&1 | tee .vscode/xcode_logs/ios_device_build.log
```

---

## 10. 단말에 설치 및 실행

빌드 산출물 경로를 찾습니다.

```bash
APP_PATH="$(find client/ios/build/Build/Products/Debug-iphoneos -name 'Minchodan.app' -type d | head -1)"
printf '%s\n' "$APP_PATH"
```

앱 설치와 실행은 다음처럼 합니다.

```bash
xcrun devicectl device install app \
  --device <COREDEVICE_IDENTIFIER> \
  "$APP_PATH"

xcrun devicectl device process launch \
  --device <COREDEVICE_IDENTIFIER> \
  --terminate-existing \
  <IOS_BUNDLE_ID>
```

앱을 콘솔에 붙여 실행하려면 다음 명령을 사용합니다.

```bash
xcrun devicectl device process launch \
  --device <COREDEVICE_IDENTIFIER> \
  --terminate-existing \
  --console \
  <IOS_BUNDLE_ID>
```

---

## 11. Xcode UI 또는 Codex MCP로 확인

Xcode를 사용할 때는 `client/ios/Minchodan.xcworkspace`를 여는 것을 권장합니다.

```bash
open client/ios/Minchodan.xcworkspace
```

| **위치** | **확인할 내용** |
| :--- | :--- |
| **상단 Scheme** | `Minchodan` |
| **상단 Destination** | 연결된 실제 iPhone 또는 대상 시뮬레이터 |
| **Issue Navigator** | error 우선, warning은 빌드 차단 여부만 구분 |
| **Report Navigator** | 최근 빌드 실패 단계와 원문 로그 |
| **Devices and Simulators** | 단말 연결, trust, installed app, console |

에이전트에게 이어서 맡길 때는 다음처럼 요청합니다.

```txt
단말 연결 확인하고 Minchodan iOS 앱을 실기기에 빌드해줘.
빌드 실패하면 에러 원인 파일과 최소 수정안을 먼저 설명하고, 필요한 수정까지 진행해줘.
빌드 성공하면 앱 실행까지 확인하고 Xcode issue navigator에 남은 에러/경고를 정리해줘.
```

---

## 12. 앱 확인 체크리스트

| **영역** | **확인할 내용** | **실패 시 보는 위치** |
| :--- | :--- | :--- |
| **앱 실행** | 앱이 크래시 없이 전면 실행되는지 | Xcode console, device console |
| **권한** | 카메라, 마이크, 위치 권한 요청이 자연스러운지 | `Info.plist`, 권한 hook |
| **카메라** | 후면 카메라 preview 또는 캡처 경로가 동작하는지 | `client/src`, VisionCamera 설정 |
| **WebSocket** | 서버 주소, hello 메시지, ping/pong 흐름이 맞는지 | `client/src/hooks/useWebSocket.ts`, 서버 로그 |
| **프레임 전송** | reflex/cognitive stream 구분과 frame id가 유지되는지 | `client/src/services/frameCaptureProvider*.ts`, `useCamera`/`CameraView`, 서버 `/ws/detect` 로그 |
| **오디오** | 반사 경보가 인지 음성을 선점하는지 | `audioEngine`, `expo-audio` 관련 코드 |
| **햅틱** | high risk 수신 시 햅틱이 같이 울리는지 | `hapticEngine`, event handler |
| **접근성** | 음성 안내와 접근성 알림이 충돌하지 않는지 | 접근성 API 호출부 |

확인 결과는 다음 형식으로 남깁니다.

```txt
검증 일시:
단말: <IOS_DEVICE_NAME>
iOS 버전: <IOS_VERSION>
빌드 방식:
앱 실행 여부:
재현 절차:
기대 동작:
실제 동작:
관련 로그:
수정 필요 파일 추정:
```

---

## 13. 수정 후 재빌드 판단 기준

| **변경 범위** | **권장 검증** |
| :--- | :--- |
| **문구, 화면 상태, JS 로직만 수정** | Metro reload 후 단말 확인 |
| **TypeScript 타입 또는 hook 로직 수정** | Metro reload, 필요 시 타입 검사 |
| **카메라 캡처 서비스 수정** | 단말 확인 필수, 네이티브 연결부 변경 시 재빌드 |
| **Swift/Objective-C 수정** | `xcodebuild` 재빌드 후 설치/실행 |
| **Podfile 또는 native dependency 수정** | `pod install` 후 재빌드 |
| **Info.plist, entitlements, 권한 수정** | 재빌드 후 단말에서 권한 흐름 재확인 |
| **앱 번들 모델/오디오 파일 수정** | 재빌드 후 실제 단말에서 자산 로드 확인 |

---

## 14. 반복 작업 루프

| **순서** | **작업** | **판단 기준** |
| :--- | :--- | :--- |
| 1 | **증상 재현** | 단말에서 같은 문제가 반복되는지 확인 |
| 2 | **로그 확보** | Xcode issue, Metro 로그, 서버 로그를 분리 |
| 3 | **수정 범위 결정** | JS만 수정할지, native 재빌드가 필요한지 결정 |
| 4 | **작게 수정** | 한 번에 여러 원인을 섞지 않음 |
| 5 | **빠른 검증** | JS reload 또는 단일 빌드로 먼저 확인 |
| 6 | **실기기 확인** | 카메라, 오디오, 햅틱처럼 실제 단말 의존 기능 확인 |
| 7 | **문서/로그 정리** | 재현 절차와 해결 내용을 changelog 필요 여부와 분리 |

---

## 15. 자주 나는 문제와 우선 조치

| **증상** | **흔한 원인** | **우선 조치** |
| :--- | :--- | :--- |
| **단말이 목록에 안 보임** | 잠금, 신뢰 승인 미완료, 케이블 문제, 개발자 모드 비활성 | 단말 잠금 해제, Trust 승인, 케이블 교체, Developer Mode 확인 |
| **`No Accounts` signing 에러** | Xcode에 Apple 계정이 추가되지 않음 | `Xcode > Settings... > Apple Accounts > Add Apple Account...`에서 로그인 |
| **`No profiles` signing 에러** | Target Team 미선택 또는 provisioning profile 미생성 | `TARGETS > Minchodan > Signing & Capabilities`에서 Team 선택 |
| **`xcodebuild` destination을 못 찾음** | `devicectl` ID와 `xcodebuild` UDID 혼동 | `xcodebuild -showdestinations`의 `id` 사용 |
| **MCP 설정은 맞는데 Xcode UI 빌드가 다름** | Xcode가 `.xcodeproj`를 열고 있음 | `client/ios/Minchodan.xcworkspace` 열기 |
| **빌드는 되는데 앱 실행 실패** | 단말 잠금, bundle id 불일치, 설치 실패 | 단말 잠금 해제, `<IOS_BUNDLE_ID>` 확인, `devicectl install` 재실행 |
| **Metro 연결 실패** | Metro 미실행, 네트워크 또는 캐시 문제 | `npm run start -- --clear` 재실행 |
| **네이티브 모듈 관련 빌드 실패** | Pods 미동기화, native dependency 변경 | `cd client/ios && pod install` 후 재빌드 |
| **카메라 권한 또는 preview 실패** | 권한 문자열, VisionCamera 설정, 실제 단말 권한 상태 | 단말 설정에서 권한 초기화 후 재확인 |
| **실기기에서는 되는데 시뮬레이터에서 안 됨** | 카메라, CoreML, 하드웨어 의존 기능 차이 | 실기기 결과를 기준으로 판단 |

---

## 16. 커밋 전 확인

단말 빌드 작업 후 커밋 전에 다음을 확인합니다.

```bash
git status --short
git diff --check
```

개인 로컬 값이 섞였는지 확인합니다.

```bash
rg -n "/Users/|file:///|deviceId:|DEVELOPMENT_TEAM|Apple Development|CoreDevice|UDID|<실제 단말명>" .xcodebuildmcp docs client/ios
```

| **파일 유형** | **커밋 판단** |
| :--- | :--- |
| **공유 설정 템플릿** | 개인 경로와 단말 ID를 placeholder로 복구한 뒤 커밋 |
| **로컬 검증 노트** | 팀 공유 필요성이 있으면 개인 ID 제거 후 커밋 |
| **실제 코드 수정** | 변경 이유, 검증 명령, 실기기 확인 결과를 함께 정리 |
| **changelog** | 주요 구현/설정 변경일 때만 해당 담당자 changelog에 반영 |

---

## 17. 빠른 명령 모음

```bash
# 1. Xcode 환경
xcode-select -p
xcodebuild -version

# 2. workspace / scheme
xcodebuild -list -workspace client/ios/Minchodan.xcworkspace

# 3. 단말 확인
xcrun devicectl list devices
xcrun xctrace list devices
xcodebuild -showdestinations -workspace client/ios/Minchodan.xcworkspace -scheme Minchodan

# 4. Signing 자동 생성까지 허용한 실기기 빌드
xcodebuild \
  -workspace client/ios/Minchodan.xcworkspace \
  -scheme Minchodan \
  -destination "platform=iOS,id=<XCODEBUILD_DEVICE_UDID>" \
  -configuration Debug \
  -derivedDataPath client/ios/build \
  -allowProvisioningUpdates \
  -allowProvisioningDeviceRegistration \
  build

# 5. Metro
cd client
npm run start -- --clear

# 6. 실기기 빌드
xcodebuild \
  -workspace client/ios/Minchodan.xcworkspace \
  -scheme Minchodan \
  -destination "platform=iOS,id=<XCODEBUILD_DEVICE_UDID>" \
  -configuration Debug \
  -derivedDataPath client/ios/build \
  build

# 7. 설치 및 실행
APP_PATH="$(find client/ios/build/Build/Products/Debug-iphoneos -name 'Minchodan.app' -type d | head -1)"
xcrun devicectl device install app --device <COREDEVICE_IDENTIFIER> "$APP_PATH"
xcrun devicectl device process launch --device <COREDEVICE_IDENTIFIER> --terminate-existing <IOS_BUNDLE_ID>
```

---

## 18. 운영 원칙

| **원칙** | **설명** |
| :--- | :--- |
| **실기기 기준 검증** | 카메라, 햅틱, 오디오, CoreML/TFLite는 실제 iPhone 결과를 우선합니다. |
| **workspace 우선** | Pods가 포함된 React Native iOS 프로젝트이므로 `.xcworkspace` 기준으로 빌드합니다. |
| **식별자 분리** | `xcodebuild` destination ID와 `devicectl` identifier를 혼동하지 않습니다. |
| **작은 수정, 빠른 재검증** | 한 번에 큰 변경을 넣기보다 단말에서 재현 가능한 단위로 수정합니다. |
| **개인값 보호** | 단말 UDID, CoreDevice ID, 개인 절대경로는 공유 커밋에 남기지 않습니다. |
| **반사 경로 원칙 유지** | 반사 경보에는 LLM/RAG/실시간 TTS를 연결하지 않습니다. |
