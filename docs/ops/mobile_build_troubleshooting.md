> **작성일**: 2026-07-05
> **버전**: v1.1.0
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

### 3.2 비동기 생성 레이스 컨디션에 따른 사운드 유실 및 무음 루프

- **원인**: `createAudioPlayer`는 비동기로 사운드 버퍼를 RAM에 적재합니다. 파일 로딩이 완료되기 전 찰나(수 ms)에 `play()`를 호출하면 명령이 묵살되며, 이후 등속 경보 필터(`currentBeepInterval === intervalMs`)에 막혀 더 이상의 플레이 명령이 주입되지 않아 평생 묵음이 되는 버그입니다.
- **해결책**:
  - 오디오 정지 신호가 수신될 때 플레이어 인스턴스를 `release()`하여 소멸시키는 정책을 버리고, **단순 `pause()` 만 수행하여 메모리에 싱글톤으로 유지**합니다.
  - 최초 1회만 lazy-load된 이후에는 메모리에 적재 완료된 플레이어 인스턴스가 `play()`/`pause()` 명령에 0ms 반응성으로 즉시 연동됩니다.

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
