> **작성일**: 2026-07-06
> **버전**: v1.5.0 (2026-07-07 §1.6/1.7/1.8 후속 업데이트 - 이중화 파일 삭제, CPU 전용 재확정, 온디바이스 추론 재활성화 및 바이너리 전송 전환)
> **설계 기준**: docs/ops/wireless_test_guide.md (v1.1.0)

# Minchodan 모바일 네이티브 빌드 트러블슈팅 가이드

본 문서는 인공지능 코딩 에이전트와 인간 개발자가 React Native (Expo) 모바일 클라이언트를 iOS 및 Android 실기기/시뮬레이터용으로 빌드할 때 발생하는 컴파일 에러의 해결 시나리오를 집대성한 장애 대응 매뉴얼입니다.

---

## 1. iOS 빌드 및 컴파일 트러블슈팅 (Xcode)

### 1.1 `rsync: link_stat ... failed: No such file or directory` (Sandbox 권한 오류)

- **원인**: Xcode 15+ 버전부터 강화된 사용자 스크립트 샌드박싱(`ENABLE_USER_SCRIPT_SANDBOXING`) 규칙이 활성화되어 있어, 빌드 스크립트가 임시 디렉토리 바깥의 파일을 복사하거나 링크하지 못하도록 강제하기 때문입니다.
- **해결책**:
  1. Xcode(`Minchodan.xcworkspace`)를 실행합니다.
  2. **Build Settings** 탭으로 이동하여 `User Script Sandboxing` 설정을 검색합니다.
  3. 값을 **`NO`** 로 강제 변경한 후 Clean Build를 시도합니다.
  4. 또는 프로젝트 설정인 [Podfile](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/client/ios/Podfile) 최하단에 아래 설정을 주입하여 자동 해결합니다:
     ```ruby
     post_install do |installer|
       installer.pods_project.targets.each do |target|
         target.build_configurations.each do |config|
           config.build_settings['ENABLE_USER_SCRIPT_SANDBOXING'] = 'NO'
         end
       end
     end
     ```

### 1.2 M1/M2/M3 Apple Silicon Mac의 CocoaPods 아키텍처 충돌 (`ffi` 에러)

- **원인**: Apple Silicon Mac의 `arm64` 네이티브 환경과 CocoaPods 라이브러리 컴파일용 `x86_64` 로제타(Rosetta) 환경이 상호 충돌하여 `pod install`이 실패하기 때문입니다.
- **해결책**:
  1. 로컬 터미널에서 CocoaPods ffi 모듈을 x86 호환 모드로 다시 컴파일합니다:
     ```bash
     sudo arch -x86_64 gem install ffi
     ```
  2. `pod install` 실행 시 앞에 `arch -x86_64` 접두사를 동봉하여 실행합니다:
     ```bash
     cd client/ios
     arch -x86_64 pod install
     ```

### 1.3 `DerivedData` 빌드 캐시 오염으로 인한 원인 모를 링커 에러

- **원인**: 이전 컴파일의 리소스 및 객체 찌꺼기가 빌드 캐시 공간에 오염되어 잔존하여 링커 충돌을 일으키는 경우입니다.
- **해결책**:
  1. Xcode의 캐시 폴더(`DerivedData`)를 커맨드라인으로 통째로 삭제 청소합니다:
     ```bash
     rm -rf ~/Library/Developer/Xcode/DerivedData/*
     ```
  2. Expo 빌드 캐시도 함께 비워 줍니다:
     ```bash
     cd client
     npx expo start -c
     ```

### 1.4 `Object cannot be a Swift value type` (CoreML 브릿징 딕셔너리 예외)

- **원인**: React Native의 네이티브 모듈 브릿지(`RCTPromiseResolveBlock`)를 통해 Swift 클래스에서 딕셔너리(`[String: Any]`) 또는 배열(`[[String: Any]]`) 형태의 Swift Value Type 객체를 그대로 Objective-C 런타임으로 전달하려고 할 때, 아키텍처 브릿징 엔진이 이를 변환하지 못해 런타임 치명적 예외(EXC_BAD_ACCESS 및 크래시)를 유발하는 현상입니다.
- **해결책**:
  - Swift Bridge 파일([CoreMLInferenceBridge.swift](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/client/ios/Minchodan/CoreMLInferenceBridge.swift)) 내에서 반환되거나 중첩되는 모든 Swift Dictionary 및 Array 데이터에 대해 명시적으로 **`NSDictionary`** 및 **`NSArray`** 로 강제 타입 캐스팅(`as NSDictionary`, `as NSArray`)하여 브릿지 호환성을 완전하게 수립해 줍니다.

### 1.5 `Installing...` 단계에서 멈추며 실기기 화면이 흰색(White Screen)으로 대기하는 현상 (USB 포트 터널링 꼬임)

- **원인**:
  1. 기기가 잠겨(Lock) 있거나 개발자 신뢰 승인 팝업이 홀드되어 있어 `ios-deploy` 프로세스가 전송을 마치지 못했을 때.
  2. 별개 터미널에서 메트로 번들러(`npm run start`)와 `npx expo run:ios --device`를 따로 구동할 경우, USB 포트 포워딩(`usbmuxd`) 및 8081번 포트 리버스 바인딩 소유권이 서로 충돌하여 실기기가 맥북의 메트로 번들러 서버를 찾지 못해 자바스크립트 소스를 불러오지 못하고 흰 화면(Splash 대기 상태)에 영구 멈추는 경우.
- **해결책**:
  1. 기기의 암호 잠금을 해제하고, '이 컴퓨터를 신뢰하겠습니까?' 팝업을 수락하여 활성화 상태를 유지합니다.
  2. 실행 중인 개별 메트로 서버와 꼬인 빌드 프로세스를 완전히 종료(`kill`)한 뒤, **`npx expo run:ios --device "장치UDID"` 단일 세션 통합 명령어**로 기동하여 메트로 번들러 서버와 기기 간의 터널을 깔끔하게 단독 매핑해 줍니다.
  3. 또는, 실기기 빌드 렉과 네트워크 꼬임 문제를 원천 차단하기 위해 **`client/src/config/mock.ts` 에서 `MOCK_CAMERA = true`, `MOCK_HAPTIC = true`** 설정을 켠 후, 맥북의 **iOS 시뮬레이터(Simulator)** 환경에서 테스트하여 화면 렌더링 및 웹소켓 전송을 쾌적하고 신속하게 검증합니다.

### 1.6 iOS Xcode 프로젝트 소스 파일 이중화 꼬임 현상

- **원인**: Xcode 프로젝트 내부에서 실제로 참조하여 컴파일하는 Swift Bridge 파일의 물리적 경로가 이중화되어 있어, 엉뚱한 껍데기 파일만 정합 및 캐시 소거를 진행했을 때 수정 사항이 반영되지 않는 꼬임 현상입니다.
  - 껍데기 파일 경로: `client/ios/Minchodan/CoreMLInferenceBridge.swift`
  - 실제 Xcode 링킹 컴파일 대상 파일 경로: `client/ios/CoreMLInferenceBridge.swift`
- **해결책**:
  - 실제 Xcode 타깃에 등록되어 빌드되는 원본 소스 파일(`client/ios/CoreMLInferenceBridge.swift`)을 명확히 색출하여 해당 파일에 브릿징 가드레일 및 타입 캐스팅 조치를 적용해 주어야 합니다.

> **2026-07-07 후속 업데이트**: 임시 우회(원본 파일만 수정)에서 한 걸음 더 나아가, pbxproj를 직접 분석해 껍데기 파일이 프로젝트에 전혀 연결되어 있지 않음을 완전히 확정했다(`AppDelegate.swift`는 `path = Minchodan/AppDelegate.swift`로 명시된 반면 `CoreMLInferenceBridge.swift`는 그룹 자체에 `path` 속성이 없어 `client/ios/`로 resolve됨). 이에 따라 `client/ios/Minchodan/CoreMLInferenceBridge.swift`를 **완전히 삭제**하여 혼동 위험 자체를 제거했다. 이제 `client/ios/CoreMLInferenceBridge.swift`가 유일한 소스이므로 이 문제는 재발하지 않는다.

### 1.7 iOS CoreML Neural Engine (ANE) 가속 컴파일 크래시 (MLIR pass manager failed)

- **원인**: YOLO v26N 모델 그래프의 특정 커스텀 레이어 구성이 iOS 17 이하 구버전 기기들의 Neural Engine(ANE) 가속 드라이버 단독 가속(`computeUnits = .all`) 컴파일 도중 MLIR 그래프 컴파일러 예외를 발생시켜 앱이 구동 즉시 강제 종료되는 하드웨어 버그입니다.
- **해결책**:
  - Swift Bridge 파일 내에서 모델 적재 환경설정 파라미터인 `computeUnits` 지정을 **`.cpuAndGPU`** 로 완화 및 우회 설정하여 Neural Engine 하드웨어 컴파일 락을 안전하게 비껴가도록 보정해 줍니다.

> **2026-07-07 후속 업데이트**: `.cpuAndGPU` 완화만으로는 충분하지 않음이 실기기 재검증에서 확인됐다. raw tensor 파싱 아키텍처로 전환한 뒤에도 `.cpuAndGPU`에서 첫 프레임 추론 직후 크래시(백색 화면 후 프로세스 종료)가 3회 연속 재현되어, 현재는 **`computeUnits = .cpuOnly`(CPU 전용)** 로 완전히 하향 고정했다. 509프레임 연속 무크래시를 확인했으며(평균 det 24.11ms, seg 18.86ms, total 42.97ms — 서버 KPI 80ms 대비 여전히 여유), ANE/GPU 재도전은 근본 원인(Metal 컴파일러의 end2end NMS 연산 미지원 추정) 규명 후의 별도 과제로 보류한다. 상세는 [`docs/ops/ondevice_coreml_benchmark.md`](ondevice_coreml_benchmark.md) 참조.

### 1.8 JS 스레드 연산 과부하로 인한 iOS Watchdog 강제 종료 (Debug session ended with code 9: killed)

- **원인**: 카메라로부터 매 초당 4~10회 촬영 유입되는 고용량 이미지를 온디바이스 추론 텐서로 변환하기 위해 자바스크립트 메인 스레드 상에서 순수 JS 디코더(`jpeg-js`) 및 Bilinear 리사이즈 중첩 루프(매 프레임당 약 122만 번 연산)를 직접 수행함에 따라 UI 메인 스레드가 100% 점유되어 데드락 상태로 굳어지고, iOS 커널 Watchdog 가디언이 이를 오류로 판단하여 즉각 SIGKILL(code 9)로 프로세스를 강제 종료하는 현상입니다.
- **해결책**:
  - 1. 실기기 구동 모드(`!isMockMode`)일 때는 발열 및 Watchdog 차단을 위해 무거운 로컬 온디바이스 CoreML 추론 및 JS 이미지 디코딩 루프를 과감히 건너뛰도록 **바이패스(Bypass)** 처리하고, 640x640 base64 원본 프레임만 WebSocket을 통해 GPU 서버로 고속 송신하여 서버에서 추론을 전담하도록 Thin Client 구조를 수립합니다.
  - 2. 단말기 UI 컴포넌트(`CameraView.tsx`)에 서버의 디코딩 및 추론 연산 수락 응답 이벤트인 **`ack` 타입의 메시지 리스너 훅**을 보강 이식하여, 수신 즉시 화면 상태 텍스트를 `서버추론: 안전` 등으로 갱신해 주어 "추론 대기..." 상태에서 정상 해제되도록 UI 연동성을 완비합니다.

> **2026-07-07 후속 업데이트**: 위 크래시의 진짜 원인이 (a) Vision Framework 기반 파싱과 커스텀 클래스 라벨 불일치, (b) `.cpuAndGPU`/`.all` GPU 컴파일 실패였음이 밝혀져 raw tensor 파싱 재구성 + `.cpuOnly` 고정으로 해결됨에 따라, **① 온디바이스 추론 바이패스를 제거**하고 실기기에서도 CoreML 추론을 재활성화했다(509프레임 연속 무크래시 확인). **② 서버 전송 방식도 base64에서 raw JPEG 바이트 바이너리 WS 프레임으로 전환**했다(`expo-file-system`의 `File(uri).bytes()` + `WebSocket.send(Uint8Array)`, 33% 페이로드 절감). 즉 "온디바이스 추론 스킵 + base64 서버 전송"이라는 이 절의 우회책은 더 이상 현재 코드 상태가 아니며, `docs/design/api_specification.md` §3.1(바이너리, 기본)/§3.2(base64, 구버전 호환)를 최신 기준으로 삼는다.

---

## 2. Android 빌드 및 컴파일 트러블슈팅 (Gradle)

### 2.1 `SDK location not found` (Android SDK 경로 설정 누락)

- **원인**: 프로젝트 루트에 Android SDK의 설치 절대경로를 가리키는 `local.properties` 환경 파일이 유실되었기 때문입니다.
- **해결책**:
  - `client/android/` 디렉토리 아래에 **`local.properties`** 파일을 새로 만들고 자신의 OS 환경에 맞는 SDK 경로를 주입합니다:
    - **macOS 예시**:
      ```properties
      sdk.dir=/Users/사용자계정/Library/Android/sdk
      ```
    - **Windows 예시**:
      ```properties
      sdk.dir=C\:\\Users\\사용자계정\\AppData\\Local\\Android\\Sdk
      ```

### 2.2 `Unsupported class file major version` (JDK 버젼 불일치)

- **원인**: Gradle 빌드 엔진 버전이 지원하지 않는 구버전 혹은 너무 최신 버전의 Java(JDK)가 호스트 OS 상에 바인딩되어 동작 중이기 때문입니다. (Expo SDK 51+ 환경은 **JDK 17**을 타겟으로 합니다.)
- **해결책**:
  1. 현재 터미널의 JDK 버전을 확인합니다: `java -version`
  2. JDK 17로 자바 런타임을 변경한 후 환경변수를 주입합니다.
     - **macOS**: `export JAVA_HOME=$(/usr/libexec/java_home -v 17)`
     - **Windows**: 제어판 -> 시스템 환경 변수에서 `JAVA_HOME` 경로를 JDK 17 설치 폴더로 정정합니다.

---

## 3. iOS 오디오 및 햅틱 런타임 트러블슈팅 (실기기 및 에뮬레이터)

실기기 런타임 환경에서 카메라 영상 스트리밍과 실시간 반사 경로(Reflex Gate) 비프음 및 진동 출력이 맞물릴 때 일어나는 하드웨어 잠금 현상과 해결 시나리오의 요약입니다.

| 장애 현상 | 원인 | 해결책 |
| :--- | :--- | :--- |
| **오디오 세션 활성화 실패**<br/>(UnexpectedException) | 카메라 촬영 루프와 런타임 오디오 세션 셋업(`setAudioModeAsync`)의 동시 점유 마찰 | 앱 최상단 진입점(`App.tsx`)에서 오디오 카테고리를 **선제 등록**하고 런타임 루프에서는 중복 호출을 제거함 |
| **비프 경보 드롭 및 무음**<br/>(비동기 레이스 컨디션) | 리소스 로딩이 완료되기 전 `play()`가 호출되어 유실된 후, 중복 방지 가드레일에 의해 재생 루프 차단 | 플레이어 인스턴스를 매번 소멸시키지 않고 메모리에 **싱글톤으로 영속 유지**하며 `pause()`/`play()`로만 제어 |
| **이중 신호 난사로 드라이버 마비**<br/>(오버랩 충돌) | 로컬 추론 훅과 상위 UI 컴포넌트 양측에서 햅틱/오디오 끔과 켬 명령을 거의 0ms 간격으로 교차 수행 | 피드백 제어 로직을 UI 오케스트레이터인 **`CameraView.tsx` 단 한 곳으로 통합 및 일원화**하여 교통정리 |
| **로컬 require 에셋 로드 실패** | `require()`는 컴파일 후 정수 리소스 ID를 리턴하므로 네이티브 플레이어가 경로를 인지하지 못함 | `expo-asset`의 **`Asset.fromModule`**을 사용하여 샌드박스 내부의 물리 로컬 URI(`file://...`)로 변환 후 로드 |
| **유선 분리 시 비프음 정지** | 디버그 빌드가 컴퓨터의 Metro 개발 서버로부터 번들을 동적으로 로드하여 케이블 차단 시 렉 유실 | **`--configuration Release`** 옵션으로 빌드하여 모든 번들과 사운드 에셋을 기기에 **100% 내장 배포** |
| **실시간 널뛰기로 오디오 중단**<br/>(채터링 락업) | 120ms 주기로 탐지 결과가 튀어 `stop`과 `play`가 번갈아 난사되어 네이티브 오디오 스레드 마비 | **슈미트 트리거 방식의 600ms 쿨다운 버퍼**를 두어 일시적 탐지 유실에 대한 즉시 정지를 지연 흡수함 |

### 3.1 AVAudioSession Activation Failed (카메라 세션과의 우선권 마찰)

- **원인**: `react-native-vision-camera`가 구동되어 카메라 하드웨어를 선점한 뒤, 런타임 검출 루프 내부에서 `setAudioModeAsync`를 임의로 재호출하여 오디오 카테고리 정책을 교정하려고 할 때 iOS AVFoundation 드라이버 레벨에서 세션 잠금이 걸려 실패를 뱉고 사운드 파이프가 먹통이 되는 현상입니다.
- **해결책**:
  - `CameraView`가 기동되기 전, 앱의 최상단 엔트리 포인트인 **`App.tsx`** 마운트(`useEffect`) 시점에 세션 설정을 단 1회 선제 호출하여 등록합니다:
    ```typescript
    useEffect(() => {
      void setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true, // 무음 스위치를 무시하고 출력하는 세션 정책 선등록
        shouldPlayInBackground: false,
        interruptionMode: "duckOthers",
      });
    }, []);
    ```
  - 런타임 `audioEngine.ts` 내부의 비프음 구동 루프에서는 `setAudioModeAsync`를 절대 중복 실행하지 않도록 차단합니다.

### 3.2 비동기 생성 레이스 컨디션 및 AVPlayer 비동기 큐 락업

- **원인**:
  1. `createAudioPlayer`는 비동기로 사운드 버퍼를 RAM에 적재하여, 파일 로딩 완료 전 `play()`를 호출하면 명령이 유실되고 등속 경보 필터에 걸려 무음이 됨.
  2. 비프음을 연속적(핑퐁식)으로 강제 재생하기 위해 매 주기마다 `player.pause(); player.seekTo(0); player.play();`를 연이어 쏘면, `seekTo`의 비동기 스레드 작업이 누적되어 iOS AVPlayer 내부 재생 상태 머신이 엉켜 영구 음소거 상태로 락(Lock-up)이 걸림.
  3. 한편, 단일 플레이어 인스턴스에 고주파수(예: 100ms~200ms)의 `play()`가 지속 반복 실행될 경우, iOS 내부 오디오 렌더러가 비동기 재생 큐의 고갈로 인해 강제로 출력을 차단(Mute)하는 현상이 일어남.
- **해결책**:
  - 플레이어가 최초 기동될 때 `loop = true; volume = 0.0;` 설정 하에 **`play()` 명령을 단 1회만 백그라운드로 실행**하여 오디오 스트림을 항시 기동 상태로 둡니다.
  - 비프 점멸 핑퐁을 렌더링할 때는 `play()` / `pause()` / `seekTo()` 등의 네이티브 하드웨어 스레드를 건드리는 명령을 100% 버리고, 자바스크립트 타이머에 의해 **`player.volume = 1.0;` (소리 켬)과 `player.volume = 0.0;` (소리 끔)만 주입하는 볼륨 변조(Volume Modulation) 방식**으로 동작을 대체합니다.
  - 이를 통해 네이티브 드라이버에 가해지는 재생 피로도가 0이 되어, iOS/iPhone 고유의 소음 차단(Hearing Protection) 장치를 완벽히 우회하고 영구적으로 안전한 피드백을 유지합니다.

### 3.3 로컬 `require()` 번들 에셋 로딩 렉 및 파일 유실

- **원인**: 자바스크립트의 `require('./path.wav')` 구문은 React Native 번들러 빌드 완료 시 물리 경로가 아닌 **정수 리소스 식별자(Resource ID)**를 반환합니다. `expo-audio`의 플레이어 소스 인자에 이를 다이렉트로 대입하면 네이티브 단에서 에셋 파일을 찾지 못해 로딩에 실패합니다.
- **해결책**:
  - `expo-asset` 라이브러리를 경유하여 정수 ID를 기기 내부의 절대 물리 경로로 다운로드 및 정합하여 로드합니다:
    ```typescript
    import { Asset } from "expo-asset";
    ...
    const asset = Asset.fromModule(require("../../assets/sounds/beep.wav"));
    if (!asset.localUri) {
      await asset.downloadAsync();
    }
    const sourceUri = asset.localUri || asset.uri;
    this.player = createAudioPlayer(sourceUri); // 물리 URI 명시 전달
    ```

### 3.4 이중 피드백 트리거 간섭에 의한 오디오 세션 크래시

- **원인**: 하위 연산 계층인 `useOnDeviceDetection.ts`와 최상단 화면 계층인 `CameraView.tsx` 두 곳에서 각각 탐지 객체 리스트를 가공하여 오디오와 햅틱 명령을 독립적으로 전송할 경우, 한쪽에서 끄고 한쪽에서 켜는 명령이 0ms 간격으로 교차 입력되어 디바이스 드라이버 오동작을 초래합니다.
- **해결책**:
  - `useOnDeviceDetection.ts` 내부의 피드백 발화 코드를 완전히 배제하고 순수 연산 데이터만 리턴하게 분리합니다.
  - 최상위 **`CameraView.tsx` 한 곳에서만 비프/햅틱 규칙을 통합 계산하고 독점 제어**하도록 통제권을 일원화합니다.

### 3.5 Development Client와 독립 실행의 번들 로드 병목

- **원인**: USB 유선 케이블을 뽑았을 때 앱이 켜지지 않거나 소리가 안 나는 현상은, 개발용 디버그 빌드가 컴퓨터의 Metro 개발 서버로부터 번들과 에셋 데이터를 실시간 스트리밍하기 때문입니다. 케이블이 뽑혀 연결 대역이 상실되면 번들 소스가 차단되어 앱 내부 기능이 마비됩니다.
- **해결책**:
  - 모든 JS 코드와 리소스 파일(`beep.wav`)을 앱 바이너리 파일 내에 압축 내장시키는 **Release(프로덕션) 구성으로 컴파일하여 기기에 고정 주입**해야 합니다:
    ```bash
    npx expo run:ios --device "장치UDID" --configuration Release
    ```
  - 반드시 최초 1회는 유선을 결선하여 릴리즈 설치가 100% 마칠 때까지 유지하고, 이후에는 케이블을 완전히 분리하여도 단독 구동이 보장됩니다.

### 3.6 실시간 추론 Chattering 노이즈에 의한 런타임 음소거 (Hysteresis)

- **원인**: 전방 장애물과의 임계 거리 경계선상이나 confidence 40% 부근에서 탐지와 무탐지가 120ms(10fps) 단위로 널뛰기(Chattering)를 할 때, `stopBeep()`과 `playBeep()`이 0.1초 단위로 빠르게 교차 난사되면서 네이티브 오디오 드라이버 스레드의 컨텍스트 스위칭 한계를 초과하여 무음 락업이 걸리는 현상입니다.
- **해결책**:
  - 오디오 엔진 내부에 **슈미트 트리거(Schmitt Trigger) 형태의 쿨다운 버퍼**를 설계합니다.
  - 사물이 감지 해제(`stopBeep`)되었을 때 즉시 오디오 스레드를 정지하지 않고, **600ms의 쿨다운 타임아웃**을 두어 지연 정지시킵니다.
  - 600ms 이내에 새로운 검출(`playBeep`) 신호가 다시 유입되면 펜딩 중이던 정지 타임아웃을 즉시 `clearTimeout` 하여 취소하고 오디오 재생 흐름을 부드럽게 계속 이어갑니다.

---

## 4. 팀원 간 로컬 개발 환경 동기화 및 복제 가이드

깃 이그노어(`.gitignore`) 규칙에 의해 형상 관리 대상에서 제외된 보안 및 개별 로컬 설정 파일들은, 신규로 깃 풀(git pull)을 받은 팀원이 빌드를 정상 수행하기 위해 수동으로 환경을 정합해주어야 합니다.

이를 자동화하기 위해 프로젝트 루트에 환경 구성 2종 파일을 패키징한 **`ios_env_setup.zip`**이 구성되어 있습니다.

### 4.1 수동 공유 대상 환경 변수 및 설정 파일

아래 파일들은 개인별 메신저 혹은 공유 드라이브를 통해 수동으로 압축하여 인수 인계합니다.

| 파일/폴더명 | 로컬 저장 위치 | 설명 | 압축 패키지 내 포함 여부 |
| :--- | :--- | :--- | :--- |
| **`.env`** | 프로젝트 루트 및 `client/` | 백엔드 API 주소 및 WebSocket 접속 정보 | **포함 (`ios_env_setup.zip`)** |
| **`.xcode.env.local`** | `client/ios/.xcode.env.local` | 로컬 Node.js 바이너리 런타임 바인딩 경로 | **포함 (`ios_env_setup.zip`)** |
| **`*.p12`** | macOS 키체인 접근 앱 | Apple Developer 개인 개발/배포용 서명 인증서 | 제외 (키체인에서 직접 내보내기) |
| **`*.mobileprovision`** | `~/Library/MobileDevice/Provisioning Profiles/` | 테스트 기기 UDID 정보가 포함된 프로비저닝 프로파일 | 제외 (개발자 포털에서 다운로드) |

### 4.2 압축 파일 생성 및 전달 시 배제해야 하는 빌드 캐시 파일

아래 대상들은 이전 로컬 빌드 컴파일 찌꺼기이므로 다른 Mac에 공유될 경우 **링커 에러 및 의존성 충돌을 야기하므로 절대 압축하지 마십시오.**

| 제외 대상 폴더 | 파일 경로 | 배제 사유 |
| :--- | :--- | :--- |
| **`DerivedData/`** | `~/Library/Developer/Xcode/DerivedData/` | Xcode 내에서 빌드 시 실시간으로 생성하는 임시 바이너리 캐시 |
| **`build/`** | `client/ios/build/` | 이전 컴파일의 최종 아웃풋 임시 바이너리 공간 |
| **`xcuserdata/`** | `client/ios/*.xcodeproj/xcuserdata/` | 이전 편집기의 창 레이아웃 및 개인 UI 상태 세션 값 |
| **`node_modules/`** | `client/node_modules/` | 수신 측에서 `npm install`을 통해 최신화 재구축 권장 |
| **`Pods/`** | `client/ios/Pods/` | 수신 측에서 `pod install`을 통해 최신화 재구축 권장 |

### 4.3 신규 팀원 환경 구축 및 복원 가이드

수신 팀원은 전달받은 압축 파일 및 개발 서명 파일을 활용해 아래 순서로 로컬 환경을 복원합니다.

1. **인증서 서명 등록**:
   - 전달받은 개발 인증서(`.p12`)를 더블 클릭하여 macOS 키체인에 등록합니다.
   - 프로비저닝 프로파일(`.mobileprovision`)을 실행하여 Xcode 프로파일 캐시 경로에 저장합니다.
2. **설정 파일 압축 해제**:
   - `ios_env_setup.zip`을 프로젝트 루트 디렉토리에 압축 해제하여 `.env` 및 `client/ios/.xcode.env.local` 파일을 제자리에 위치시킵니다.
3. **로컬 컴파일 의존성 재구축**:
   - 로컬 환경에 꼬임이 없도록 패키지를 재설치합니다.
   ```bash
   # 1) Node 모듈 의존성 재배포
   cd client
   npm install

   # 2) iOS 네이티브 라이브러리 및 브릿지 재링크
   cd ios
   pod install
   ```
4. **Clean Build 실행**:
   - Xcode 또는 터미널에서 기존 캐시와 마찰이 생기지 않도록 `Clean Build Folder`를 수행한 후, `npx expo run:ios --device`를 통해 실기기 컴파일 및 런칭을 완료합니다.
