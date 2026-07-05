> **작성일**: 2026-07-05
> **버전**: v1.0.0
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
