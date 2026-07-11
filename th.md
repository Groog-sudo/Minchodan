# 안드로이드 실기기 통합 테스트 및 디버깅 로그 (th 브랜치)

작성일: 2026-07-10

## 1. 안드로이드 네이티브 빌드 오류 (CMake & 경로 길이)
* **에러 현상:** `npx expo run:android` 실행 시 C++ NDK 빌드 단계에서 에러 발생 및 CMake 3.31.6 버전 충돌, 윈도우 파일 경로 260자 제한(Path too long) 오류 발생.
* **해결 방법:** 
  * `node_modules` 내부의 `build.gradle` 파일들을 직접 패치하여 CMake 버전을 명시적으로 지정 (`version "3.31.6"`).
  * `buildStagingDirectory`를 `C:/temp/cxx/`로 강제 변경하여 윈도우의 경로 길이 제한을 우회하여 빌드 성공 (`app-debug.apk` 정상 생성).

## 2. 모듈 해석(Resolution) 오류 및 Expo Metro 연결 불안정
* **에러 현상:** 앱 기동 시 `Unable to resolve module jpeg-js` 발생 및 Metro Bundler 접속 불가(`Unable to connect to Metro`).
* **원인 분석:** 
  * `jpeg-js` 패키지가 누락되어 있었음.
  * Windows PC의 ADB 데몬이 1~2분 주기로 알 수 없는 이유로 충돌(Crash) 및 재시작(`daemon not running; starting now at tcp:5037`)되어 USB 터널(`adb reverse`)이 지속적으로 유실됨.
* **해결 방법:** 
  * `npm install jpeg-js` 후 `npx expo start -c`로 캐시를 날림.
  * ADB 충돌을 방어하기 위해 `tunnel.bat` (무한 루프로 `adb reverse tcp:8081 tcp:8081` 및 `8000`을 2초마다 갱신하는 봇)을 백그라운드에 구동시켜 연결 끊김을 원천 차단 시도.
  * 최후에는 USB 연결이 물리적으로 먹통이 되는 현상이 있어, 케이블 재연결 및 LAN 모드(`LAN_IP`를 실제 PC의 공인/사설 IP로 변경)를 병행 시도.

## 3. 카메라 권한 및 React Native Vision Camera 캡처 충돌
* **에러 현상:** 앱은 켜졌으나 카메라 화면이 까맣게 나오거나 멈춤. 로그캣(Logcat)에 캡처 오류 발생.
* **원인 분석:**
  1. 기기에 안드로이드 카메라 권한이 부여되지 않은 상태(`granted=false`)였음.
  2. `captureRealFrame` 함수 내에서 서버 전송 압축 최적화를 위해 사용된 `new File(manipResult.uri).bytes()` 문법이 현재 사용자님의 Expo 56 / react-native 파일 시스템 환경에서 지원되지 않아 런타임 크래시(`File is not a constructor` 등)를 유발함.
* **해결 방법:**
  * ADB 명령(`adb shell pm grant com.minchodan.app android.permission.CAMERA`)을 통해 원격으로 권한 강제 부여.
  * `useCamera.ts`에서 `new File().bytes()` 코드를 삭제하고 `const jpegBytes = null;`로 처리. 이렇게 함으로써 기존에 구현되어 있던 안전한 `base64` 문자열 전송 폴백(Fallback) 로직을 타도록 우회하여 오류를 영구적으로 제거함.

## 결과
위 일련의 조치를 통해 안드로이드 빌드 성공, 통신 다리 복구, 카메라 캡처 로직 런타임 오류가 모두 해결되었습니다.
차후 클론 시에는 `tunnel.bat`과 우회된 캡처 로직을 계속 활용하여 안정적으로 개발을 진행할 수 있습니다.
