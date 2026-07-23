> **작성일**: 2026-07-09
> **버전**: v1.1.2 (2026-07-24 macOS/Linux Gradle 경로 정리 반영)
> **설명**: Android 온디바이스 TFLite 추론 패키징 설정 및 Tailscale 기반 실기기 연동 테스트 종합 지침서

---

## 0. 호스트 OS별 Gradle 주의사항 (macOS / Windows / Linux)

- `client/android/gradle.properties`에 `org.gradle.java.home`을 두지 않는다. JDK가 필요하면 `~/.gradle/gradle.properties`(Windows: `%USERPROFILE%\.gradle\gradle.properties`)에 개인 경로만 설정한다.
- CMake staging을 `C:/AndroidCxx/...`로 옮기는 로직은 **Windows 전용**이다(`client/android/build.gradle`의 `Os.isFamily(WINDOWS)`). macOS/Linux는 기본 staging을 사용한다.
- `local.properties`(SDK 경로)는 Git 추적하지 않으며, Android Studio/Gradle이 호스트별로 생성한다.

---

## 1. Android 온디바이스 TFLite 빌드 구성

Android 환경에서는 `react-native-fast-tflite` 모듈을 사용하여 세그멘테이션 및 객체 탐지 온디바이스 추론을 수행합니다. TFLite 모델 파일(`.tflite`)이 정상적으로 로드되기 위해서는 빌드 시 압축 패키징을 제어하는 설정이 필수적입니다.

### 1.1 aaptOptions 설정 적용 이유
텐서플로우 라이트(`.tflite`) 파일이 APK 빌드 시 기본 옵션에 의해 압축(Compression)되면, C++ 네이티브 레벨에서 메모리 맵(`mmap`) 또는 파일 디스크립터 방식으로 파일을 읽을 수 없어 런타임 오류가 발생합니다. 이를 방지하고자 `aaptOptions` 블록을 추가하여 `.tflite` 확장자를 무압축 상태로 저장하도록 설정합니다.

### 1.2 설정 파일 및 코드 수정 내역
수정된 Android 앱 빌드 설정 세부 정보입니다.

- **설정 파일**: [client/android/app/build.gradle](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/client/android/app/build.gradle)
- **추가된 구성**:
  ```groovy
  android {
      ...
      androidResources {
          ignoreAssetsPattern '!.svn:!.git:!.ds_store:!*.scc:!CVS:!thumbs.db:!picasa.ini:!*~'
      }

      aaptOptions {
          noCompress "tflite"
      }
  }
  ```

---

## 2. Tailscale 기반 실기기 무선 테스트 및 실행 절차

PC와 Android 실기기를 같은 Tailscale tailnet에 연결하여 LTE/5G 환경에서도 서버의 사설망 주소로 통신합니다.

### 2.1 단계별 연동 가이드

#### 1단계: 안드로이드폰 개발자 옵션 및 USB 디버깅 활성화
- 스마트폰의 **설정 > 휴대전화 정보 > 소프트웨어 정보** 메뉴로 이동합니다.
- **빌드 번호** 항목을 연속으로 **7번** 빠르게 터치하여 개발자 모드를 켭니다.
- **설정 > 개발자 옵션**으로 진입한 뒤, **USB 디버깅** 스위치를 켭니다.
- USB 케이블로 PC와 폰을 연결하고, 디바이스 화면에서 **USB 디버깅 허용** 팝업 창을 승인합니다.

#### 2단계: Tailscale 연결 및 서버 주소 확인
- PC와 Android 단말에 Tailscale을 설치하고 같은 tailnet에 로그인합니다.
- PC에서 연결 상태와 Tailscale IPv4를 확인합니다.
  ```bash
  tailscale status
  tailscale ip -4
  ```

#### 3단계: 모바일 앱 설정 변경
- `client/.env`에 Tailscale Serve 인증서와 일치하는 서버 MagicDNS 이름을 설정합니다.
  ```ini
  EXPO_PUBLIC_NETWORK_MODE=tailscale
  EXPO_PUBLIC_TAILSCALE_HOST=[SERVER_MAGICDNS_NAME].ts.net
  EXPO_PUBLIC_SERVER_PORT=443
  EXPO_PUBLIC_WS_SCHEME=wss
  ```

#### 4단계: GPU 백엔드 서버 구동
- 프로젝트 루트 경로에서 파이썬 가상환경을 활성화하고 서버를 구동합니다.
  ```powershell
  .\venv\Scripts\Activate.ps1
  python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
  ```

#### 5단계: 안드로이드폰에 앱 빌드 및 설치
- 디바이스의 연결 상태를 먼저 확인합니다.
  ```bash
  adb devices
  ```
  *(목록에 기기가 `device` 상태로 표시되어야 합니다.)*
- `client` 폴더로 이동하여 메트로 번들러 기동 및 안드로이드 컴파일 설치 명령을 실행합니다.
  ```bash
  npm run android
  ```

#### 6단계: 실시간 연동 테스트 검증
- 스마트폰에 설치된 앱이 실행되고 카메라가 활성화되면 실시간으로 서버에 캡처된 프레임 데이터가 전송됩니다.
- 서버 측 로그에 `수신 640x640` 정보가 정상적으로 들어오는지 관찰합니다.
- 스마트폰 화면 오버레이에 노면 분할 결과와 사물 탐지 BBox가 그려지고, 장애물 근접 시 비프음(오디오) 및 진동(햅틱) 피드백이 실시간으로 작동하는지 검증합니다.

---

## 3. WiFi / USB 이중 접속 (2026-07-13)

**평상시(WiFi)** 와 **개발(USB + adb reverse)** 를 앱 토글로 전환하는 현재 운영 절차는 별도 문서에 정리했다.

- 절차·IP 실측·환경 변수: [android_wifi_usb_transport.md](android_wifi_usb_transport.md)
- 앱 버튼: `연결: WiFi` (기본, `192.168.137.1`) / `연결: USB` (`127.0.0.1`)
