# Minchodan 카메라-콘솔 연동 이슈 분석 및 복구 가이드 (dg)

> **작성일**: 2026-07-16
> **버전**: v1.0.0
> **대상**: Minchodan 개발팀 (dg 브랜치 개발자 및 AI 에이전트용)

이 문서는 실기기/에뮬레이터 연동 시 발생하는 카메라 프레임 전송 및 렌더링 중단 이슈의 근본 원인을 분석하고, 향후 유사 이슈 발생 시 AI 에이전트가 스스로 원인을 판별하고 조치할 수 있는 디버깅 워크플로우를 기술합니다.

---

## 1. 이슈 요약 및 조치 내용

| 구분 | 주요 이슈 사항 | 최종 조치 내용 |
| :--- | :--- | :--- |
| **단말 캡처 차단** | Expo Go의 네이티브 바인딩 제약 또는 VisionCamera 프록시 오감지로 인해 `useStreamCapture`가 **참(true)**으로 고정되어 프레임 루프가 기동되지 않음. | `client/src/hooks/useCamera.ts`에서 `useStreamCapture`를 강제로 **거짓(false)**으로 전환하여 `takePhoto` 기반의 폴백 캡처 루프가 동작하도록 복구. |
| **콘솔 디코딩 누락** | 백엔드로부터 웹소켓으로 유입되는 바이너리 타입이 `Blob` 대신 `ArrayBuffer` 형태로 흘러들어와 브라우저 렌더러가 이미지를 그리지 못함. | `console/src/api/useLiveFeed.ts`에 들어오는 데이터 형태를 점검하여, `ArrayBuffer`인 경우 즉석에서 `Blob`으로 변환하는 세이프가드 디코딩 로직 구축. |
| **경로/포트 루프백** | Windows 로컬 Port-Proxy 설정 및 Vite Proxy 규칙 혼선으로 웹소켓 및 데이터베이스 포트 바인딩 중단. | Port-Proxy 리셋 명령 실행 및 Docker 내부 원격 DB 브릿지 설정을 재정렬하여 앱-PC 웹소켓 채널을 즉각 개통. |
| **Android TFLite 오작동** | `frameCaptureProviderSelect.android.ts`가 `float32 = new Float32Array(0)`을 반환하여 `tfliteDetector.ts`가 빈 버퍼를 추론하고 `입력 shape 불일치` 경고가 발생 및 로컬 탐지가 중단됨. | Android `takePhoto` 완료 시점에 `decodeBase64JpegToHwc(base64)`를 사용하여 640x640x3 크기의 정규화 텐서 데이터를 정상적으로 디코딩 및 공급하도록 보정. |
| **Android AEC 미작동** | `audioSessionBridge.ts`에서 Android 환경일 경우 네이티브 모듈을 호출하지 않고 모조(Mock) 객체를 바로 리턴하여 하드웨어 에코 캔슬러 모드 연동이 누락됨. | Android 조건일 때도 네이티브 `AudioSessionBridgeModule.setVoiceProcessing`을 정상 대기 호출하도록 복원하여 녹음 시 에코 블리드 상쇄 활성화. |
| **프레임 프로세서 봉인 해제** | `useCamera.ts` 내부의 `useStreamCapture`가 `false`로 강제 고정되어 실기기 빌드에서도 고성능 프레임 프로세서 대신 느린 `takePhoto` 폴백만 강제 실행됨. | `useStreamCapture` 변수를 원래 설계된 `!isMockMode && captureProvider.supportsStream` 조건으로 복구하여 Expo Go와 실기기 빌드 간의 자동 분기를 완성. |
| **카메라 화면 회전 정합** | Android 기기 특성 및 촬영 방향에 따라 90도 회전 시 화면이 옆으로 누워 보이거나(기울어짐) 왜곡되는 현상이 실기기에서 발생. | 관제 콘솔 Live Feed 패널에 실시간 4방향(0°, 90°, 180°, 270°) 회전 선택 버튼을 배치하고, 선택된 각도에 맞게 BBox 복원 좌표와 이미지를 동적으로 리매핑하도록 보정. |

---

## 2. 근본 원인 분석 (Deep Dive)

### 2.1 단말 스트림 감지 버그 (supportsStream) 및 useStreamCapture 복구
원래 실기기(Development Build)가 아닌 Expo Go 쉘 환경에서는 네이티브 프레임 프로세서 플러그인(`reflexFrameCapture`)이 로드되지 않아 `supportsStream` 판정이 `false`가 되어야 합니다.
그러나 `VisionCameraProxy.initFrameProcessorPlugin`의 래퍼 구조 특성상, 에뮬레이터나 특정 개발 모드에서 더미 플러그인을 null이 아닌 값으로 뱉어내는 현상이 있어 `supportsStream=true`로 오작동하게 되었습니다.
그 결과, 프레임이 자동으로 흘러들어올 것으로 잘못 기대하고 타이머 캡처 루프(`tick()`)의 시작을 스킵하여 카메라 캡처 자체가 완전히 중단된 상태였습니다.
이를 우회하기 위해 `useStreamCapture`를 `false`로 임시 하드코딩하여 작동시켰으나, 이는 실기기 빌드에서도 고성능 프레임 프로세서를 활용하지 못하는 부작용을 낳았습니다. 2026-07-17부로 `useStreamCapture`를 원래의 동적 판정 조건(`!isMockMode && captureProvider.supportsStream`)으로 복구하여, Expo Go에서는 폴백 루프가 돌고 실기기 빌드에서는 고성능 프레임 프로세서가 구동되도록 자동 결합을 마쳤습니다.

### 2.2 콘솔 ArrayBuffer 렌더러 누수
단말이 정상적으로 base64 또는 binary 바이트 어레이를 서버로 송출해도, 브라우저 수신 스레드로 도달할 때 데이터 스트림 형식이 `Blob` 대신 브라우저 세션 상태에 따라 `ArrayBuffer` 형태로 캐스팅되는 변칙이 발생했습니다. 
이로 인해 기존 `Blob` 객체를 기대하던 리액트 훅이 데이터 처리를 조용히 스킵하고 GPS 텍스트 정보만 렌더링하고 있었습니다.

### 2.3 Android TFLite 입력 shape 누락 (0바이트 버퍼 추론)
Android용 TFLite 추론기(`tfliteDetector.ts`)는 JS 레이어 상에서 `react-native-fast-tflite`를 실행하므로 반드시 이미지 픽셀이 정규화된 텐서 버퍼(`Float32Array`)를 받아야 합니다.
기존 코드에서는 iOS의 메모리/Watchdog 최적화 로직(CoreML이 네이티브로 base64를 파싱하므로 `Float32Array(0)` 반환)을 Android에도 그대로 이식해 두어 Android TFLite에 항상 빈 버퍼가 공급되었습니다. 이로 인해 온디바이스 탐지 기능이 완전 마비되는 오류가 있었으며, Android `takePhoto` 시점에 `decodeBase64JpegToHwc(base64)`를 연동해 유효한 1228800 바이트의 HWC 정규화 float32 데이터를 공급하도록 수정했습니다.

### 2.4 Android 네이티브 AEC(음향 에코 상쇄) 누락
Android 네이티브 `AudioSessionBridgeModule.kt`에 `MODE_IN_COMMUNICATION` 통화 모드를 활용한 하드웨어 에코 캔슬레이션 기능이 완벽히 구축되어 있었음에도, React Native JS 브릿지인 `audioSessionBridge.ts`에서 Android 플랫폼일 때 early return Mock 처리를 하여 네이티브 모듈이 호출되지 않고 있었습니다. 이를 대기 비동기 호출(`await mod.setVoiceProcessing(enabled)`)하도록 변경하여 Android 실기기에서도 하드웨어 에코 제거기가 완벽히 작동하도록 연동했습니다.

### 2.5 카메라 화면 각도 수동 보정 (0°, 90°, 180°, 270°)
Android 단말의 제조사별 카메라 드라이버 특성, 센서 배치 방향, 그리고 촬영 방식(가속도 센서 활성 여부)에 따라 획득된 프레임 이미지의 EXIF가 실제 물리적 수직 상태와 일치하지 않고 왼쪽/오른쪽으로 꺾여서 전송되는 경우가 발생합니다.
이를 콘솔에서 무조건 고정된 각도로 렌더링하면 화면이 누워 보이고 이에 따라 BBox 검출 영역도 엇갈리게 됩니다.
이 문제를 해결하기 위해 관제 콘솔 UI의 Live Feed 영역 상단에 수동 4방향 회전 버튼을 추가했습니다.
* **동작 원리**: 
  - 기본값은 iOS=0°, Android=90°로 자동 셋업됩니다.
  - 화면이 옆으로 누워 보일 경우 운영자가 0°, 90°, 180°, 270° 버튼을 클릭해 실시간으로 알맞은 각도를 선택할 수 있습니다.
  - 변경 시 CSS `transform: rotate(...)`뿐 아니라 바운딩 박스를 렌더링 영역 크기와 일치하도록 재계산하는 `getDisplayBBox` 수학식에도 해당 각도를 동적으로 주입하여 탐지 박스가 정확한 피사체 위에 일치하도록 보정합니다.

---

## 3. 재발 방지를 위한 AI 에이전트 자율 디버깅 가이드

향후 카메라 연동 이슈 발생 시, AI 에이전트는 독립된 추론을 기반으로 아래 **3단계 진단 루틴**을 반드시 수행해야 합니다.

### 1단계: 웹소켓 물리 채널 수신 검증
* **확인 대상**: 콘솔 브라우저 개발자 도구 (F12)
* **검증 방법**: `useLiveFeed.ts`에서 웹소켓으로 데이터가 정상 수신되는지 콘솔 로그를 파악한다.
* **진단 결론**:
  * GPS 데이터 등 텍스트 메시지가 주기적으로 들어오고 있다면 **물리적 네트워크 채널은 정상**이다.
  * 텍스트만 들어오고 영상 바이너리가 유실되었다면 **2단계(단말 송출부)**로 진입한다.

### 2단계: 단말 handleFrame 발화 검증
* **확인 대상**: React Native (Metro) 터미널 콘솔 로그
* **검증 방법**: `client/src/components/CameraView.tsx` 내 `handleFrame` 초입에 로그를 임시 삽입하여 유효한 프레임 이벤트가 호출되는지 판별한다.
* **진단 결론**:
  * `[CameraView 디버그] handleFrame` 로그가 한 번도 찍히지 않는다면 ** supportsStream 감지 오작동**이다. `useStreamCapture`를 `false`로 우회하여 `takePhoto` 루프가 돌게 만든다.
  * 로그는 찍히나 `base64` 및 `jpegBytes`가 모두 `false`인 경우 **폰의 카메라 세션 오작동**이다. 앱 재부팅 또는 `npm run android`로 네이티브 모듈 빌드를 재지정해야 한다.

### 3단계: 콘솔 데이터 바인딩 검증
* **확인 대상**: `console/src/api/useLiveFeed.ts`
* **검증 방법**: 들어오는 메시지의 `event.data` 프로토타입을 검사하여 바이너리가 `ArrayBuffer`나 문자열 등으로 가공되어 들어오지 않는지 체크한다.
* **진단 결론**:
  * 데이터 타입 불일치가 발견되면 즉시 `new Blob([event.data], { type: "image/jpeg" })` 등으로 캐스팅하는 세이프가드 처리를 적용한다.
