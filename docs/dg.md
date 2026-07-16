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

---

## 2. 근본 원인 분석 (Deep Dive)

### 2.1 단말 스트림 감지 버그 (supportsStream)
원래 실기기(Development Build)가 아닌 Expo Go 쉘 환경에서는 네이티브 프레임 프로세서 플러그인(`reflexFrameCapture`)이 로드되지 않아 `supportsStream` 판정이 `false`가 되어야 합니다.
그러나 `VisionCameraProxy.initFrameProcessorPlugin`의 래퍼 구조 특성상, 에뮬레이터나 특정 개발 모드에서 더미 플러그인을 null이 아닌 값으로 뱉어내는 현상이 있어 `supportsStream=true`로 오작동하게 되었습니다.
그 결과, 프레임이 자동으로 흘러들어올 것으로 잘못 기대하고 타이머 캡처 루프(`tick()`)의 시작을 스킵하여 카메라 캡처 자체가 완전히 중단된 상태였습니다.

### 2.2 콘솔 ArrayBuffer 렌더러 누수
단말이 정상적으로 base64 또는 binary 바이트 어레이를 서버로 송출해도, 브라우저 수신 스레드로 도달할 때 데이터 스트림 형식이 `Blob` 대신 브라우저 세션 상태에 따라 `ArrayBuffer` 형태로 캐스팅되는 변칙이 발생했습니다. 
이로 인해 기존 `Blob` 객체를 기대하던 리액트 훅이 데이터 처리를 조용히 스킵하고 GPS 텍스트 정보만 렌더링하고 있었습니다.

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
