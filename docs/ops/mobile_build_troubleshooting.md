> **작성일**: 2026-07-06
> **버전**: v1.2.0 (로컬 개발 환경 동기화 패키지 및 복제 절차 신설)
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
