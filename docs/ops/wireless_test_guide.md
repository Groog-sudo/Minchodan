> **작성일**: 2026-07-05
> **버전**: v1.1.2 (2026-07-18 §5.4 Tailscale Metro 팀 표준·개발 PC IP 각자 덮어쓰기 안내 + 이전 v1.1.1: lap 고정 + 이전 v1.1.0: 바이너리 전송)
> **설계 기준**: docs/design/minchodan_design_note.md (비전 설계서 v1.1)

# 실기기 무선 연동 테스트 및 Docker 환경 가이드

이 문서는 Minchodan 프로젝트의 보행 보조 스마트 가이드독 시스템을 실기기(iPhone)와 로컬 GPU/CPU 추론 서버 간에 **외부 이동통신망(LTE/5G)**을 경유하여 무선으로 연동 테스트하기 위한 Docker 인프라 구성 및 네트워크 터널링 명세를 다룹니다.

---

## 1. 전체 연동 아키텍처

실기기 단말과 로컬 서버는 퍼블릭 인터넷 망을 통해 통신하며, 방화벽 및 사설 IP 제약을 극복하기 위해 **Ngrok 터널링 프록시**를 중계 계층으로 활용합니다.

```mermaid
graph TD
    subgraph Client ["iPhone 14 Max (실기기 LTE/5G)"]
        App["Minchodan App<br/>(Release Build / JS 내장)"]
    end

    subgraph Internet ["공용 인터넷 및 중계 계층 (Ngrok)"]
        Tunnel["Ngrok Secure Tunnel<br/>(partake-primer-surround.ngrok-free.dev)"]
    end

    subgraph Host ["개발용 호스트 (macOS MacBook)"]
        subgraph Docker ["Docker Compose (docker-compose.macos.yml)"]
            FastAPI["FastAPI Container<br/>(minchodan-fastapi)"]
            Redis["Redis Container<br/>(minchodan-redis)"]
            Ollama["Ollama Container<br/>(minchodan-ollama)"]
        end
    end

    App -->|1. wss WebSocket 접속| Tunnel
    Tunnel -->|2. TCP 포트 포워딩 (8000)| FastAPI
    FastAPI -->|3. 프레임 버스 XADD| Redis
    FastAPI -->|4. L2/RAG 추론 요청| Ollama
```

---

## 2. Docker 컨테이너 구성 및 역할

로컬 개발 환경에서는 macOS CPU Fallback 및 Windows PC 환경(GPU 유무에 따른 분기)을 고려하여 컨테이너들을 띄웁니다.
- **NVIDIA GPU 탑재 PC (Windows/WSL2/Linux)**: [docker-compose.yml](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/docker/docker-compose.yml)을 참조하여 GPU 가속을 활용해 추론을 수행합니다.
- **GPU 미탑재 PC 및 macOS**: [docker-compose.macos.yml](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/docker/docker-compose.macos.yml)을 참조하여 CPU Fallback 모드로 추론을 수행합니다.
- **윈도우 실행 배치 스크립트**: [windows_docker_start.bat](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/docker/windows_docker_start.bat) 실행 시 터미널창에서 `[1] GPU Mode` 와 `[2] CPU Only Mode` 중 하드웨어에 맞게 선택하여 자동으로 기동할 수 있습니다.

설정에 따라 총 3개의 컨테이너가 긴밀하게 맞물려 구동됩니다.

| 컨테이너 이름 | 이미지 / 포트 | 주요 기능 및 역할 | 데이터 볼륨 마운트 |
| :--- | :--- | :--- | :--- |
| **`minchodan-fastapi`** | `minchodan-server:latest`<br/>**`8000:8000`** | **WebSocket Gateway** (/ws/detect)<br/>**YOLO26n Detection / Segmentation** 추론<br/>ByteTrack 객체 추적기 탑재<br/>Kokoro-82M TTS 한글 음성 합성 | `./server:/app/server`<br/>`./data:/app/data`<br/>`./.env:/app/.env` |
| **`minchodan-redis`** | `redis:7-alpine`<br/>**`6379:6379`** | **메시지 버스** (Redis Streams) 중계 계층<br/>`risk.events` 스트림 발행 및 컨텍스트 보존<br/>위험도 햅틱/비프 연산 TTL 세션 스토리지 | `redis_data:/data` |
| **`minchodan-ollama`** | `ollama/ollama:latest`<br/>**`11434:11434`** | **로컬 LLM 및 임베딩 추론 엔진**<br/>gemma4:e4b (L2 안내 문장 생성)<br/>llava (4단계 오프라인 이미지 캡셔닝)<br/>nomic-embed-text (RAG용 768차원 임베딩) | `ollama_data:/root/.ollama` |

---

## 3. 네트워크 터널링 및 포트 바인딩 명세

실외 LTE망 테스트 환경에서는 단말이 맥북의 로컬 IP(`192.168.x.x`)에 직접 접근할 수 없으므로, 로컬 포트를 외부 퍼블릭 도메인으로 중계해 줍니다.

### 3.1 터널 바인딩 테이블

| 서비스 구분 | 로컬 포트 | 중계 터널링 주소 | 목적 및 사용처 |
| :--- | :--- | :--- | :--- |
| **FastAPI API/WebSocket** | `8000` | `https://partake-primer-surround.ngrok-free.dev` | 실기기 카메라 base64 프레임 전송 및 TTS 합성 MP3 수신 채널 (**wss** 통신) |
| **Metro Bundler** | `8081` | `https://g7dc9jg-anonymous-8081.exp.direct` | 개발(Development) 빌드 기동 시 무선으로 JS 번들을 가져오기 위한 터널 (릴리즈 빌드 기동 시 사용 안 함) |

---

## 4. 실기기 양방향 프로토콜 상세 흐름

단말(iPhone)이 켜진 후 서버와 체결되는 양방향 통신 규격 흐름은 다음과 같습니다.

### 4.1 핸드셰이크 및 검증 단계
1. **WebSocket 연결 수립**: 단말이 `wss://partake-primer-surround.ngrok-free.dev/ws/detect?device_id=dev-001` 경로로 소켓 연결을 요청하고 서버가 이를 승인(`accepted`)합니다.
2. **Welcome 송신**: 서버가 단말로 환영 메시지(`{"type": "welcome", "session_id": "dev-001"}`)를 보냅니다.
3. **Hello 송신**: 단말이 서버로 디바이스 식별 토큰을 동봉하여 `hello` 패킷(`{"type": "hello", "token": "token-abc-001"}`)을 응답합니다.
4. **인증 통과**: 서버가 토큰 무결성을 대조 및 검증한 뒤, `auth_ok` 패킷을 전송하고 Redis 메시지 버스를 바인딩하여 메인 루프에 진입합니다.

### 4.2 실시간 추론 스트리밍 단계
1. **프레임 캡처**: 단말의 카메라 모듈이 동적 fps(추론 지연에 따라 최대 반사 기본값~1fps 조절, `docs/changelogs/kb.md` 2026-07-07 참조)로 도로/실내 환경을 촬영하고, `expo-image-manipulator`로 JPEG 압축 후 `expo-file-system`의 `File(uri).bytes()`로 raw 바이트를 획득합니다(**2026-07-07부로 base64 인코딩 미경유**).
2. **데이터 송신**: 단말이 서버로 `detection` 타입 패킷을 전송합니다:
   - **바이너리 전송(기본)**: JSON 메타에 `transport: "binary"`만 담아 먼저 보내고, 곧바로 raw JPEG 바이트를 WS **바이너리 프레임**으로 전송합니다.
   - **base64 전송(구버전 호환)**: 필드 키 **`thumbnail_jpeg_b64`** 에 base64 텍스트를 적재한 단일 JSON 메시지로 전송합니다(Mock 모드 등).
3. **디코딩 및 리사이즈**: 서버가 바이너리 프레임은 `decode_frame_binary`(base64 디코딩 단계 없이 바로 처리)로, base64 메시지는 기존 `decode_frame`으로 처리합니다. 두 경로 모두 OpenCV로 메모리 버퍼 디코딩 후 YOLO 입력 포맷인 **`640x640`** 크기로 정규화 리사이즈를 단 수십 밀리초(ms) 내로 완료합니다.
4. **듀얼헤드 YOLO 추론**:
   - **Object Detection**: 볼라드, 킥보드, 계단 등 시각장애인 위협 장애물을 바운딩 박스로 탐지합니다.
   - **Segmentation**: 보행 가능 안전 구역 및 점자블록 노면을 픽셀 단위로 분할 분석합니다.
5. **ByteTrack 객체 추적**: 탐지된 객체의 프레임 간 궤적을 실시간으로 식적 추적하며 고유 ID를 부여합니다.
6. **응답 송신**: 서버가 디코딩 및 탐지 완료 통계를 동봉하여 단말에 즉각 `ack` 응답을 리턴합니다.

---

## 5. 장애 대응 및 핵심 트러블슈팅

### 5.1 base64 데이터 없음 에러 (구버전 호환 경로 한정)
- **현상**: 서버 로그에 `[FrameDecoder] base64 데이터 없음` 경고가 반복하여 발생하고 추론이 생략되는 경우.
- **원인**: 단말 측에서 쏘는 JSON 페이로드의 이미지 데이터 필드 키가 서버가 요구하는 **`thumbnail_jpeg_b64`**가 아닌 `base64` 등의 다른 키로 매핑되어 전달되었기 때문입니다.
- **해결**: [CameraView.tsx](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/client/src/components/CameraView.tsx)의 `sendRef.current` 호출 부 payload 키를 `thumbnail_jpeg_b64`로 명확하게 지정하여 재빌드 및 재배포해야 합니다.
- **참고 (2026-07-07)**: 실기기 기본 전송 경로는 base64가 아닌 바이너리 프레임이므로, 이 에러는 `payload.transport`가 `"binary"`로 설정되지 않은 구버전 호환 경로(Mock 등)에서만 발생한다. 바이너리 경로 관련 이슈는 `[WS] 대기 중인 메타데이터 없이 바이너리 프레임 수신` 경고 로그를 확인한다(메타-바이너리 프레임 순서가 어긋난 경우).

### 5.2 lap 트래킹 라이브러리 부재 에러
- **현상**: `requirements: Ultralytics requirement ['lap>=0.5.12'] not found` 로그가 출력되거나, ByteTrack `track()`이 실패하는 경우.
- **원인**: YOLO26n 객체 추적기(ByteTrack) 구동을 위한 선형 할당(Linear Assignment) 패키지 `lap`이 이미지/컨테이너에 없었기 때문입니다.
- **해결 (2026-07-18 정정)**: `requirements.txt`에 `lap==0.5.13`을 명시해 이미지 빌드·`pip install` 시점에 고정 설치합니다. 런타임 Ultralytics AutoUpdate에 의존하지 마십시오(`YOLO_AUTOINSTALL=False` 기본). 이미 기동 중인 컨테이너면 이미지 재빌드 또는 `pip install lap==0.5.13` 후 재기동합니다.
- **폴백**: `yolo_detector.py`는 `track()` 실패 시(`lap` 미설치·`'Conv' object has no attribute 'bn'` 등) `predict()`로 폴백해 빈 BBox를 피합니다(추적은 해당 프레임에서 비활성).

### 5.4 Tailscale Metro가 다른 PC / Finding Dev Servers에 붙는 경우
- **현상**: iOS Debug 앱이 Metro를 못 찾거나, 본인 Mac이 아닌 다른 팀원 호스트로 붙는다.
- **원인**: 저장소 기본값(`100.121.247.4:8081`)은 Tailscale Metro **팀 공유 표준(예시 폴백)** 이며, 각 개발자 PC의 Tailscale IP와 다를 수 있다.
- **해결**: **개발 PC IP는 각자 덮어쓰기**. `METRO_BUNDLER_HOST`·`DEV_CLIENT_DEFAULT_LAUNCHER_URL`·`client/.env`의 `EXPO_PUBLIC_TAILSCALE_HOST`를 `tailscale ip -4` 결과로 교체한다. 상세 표는 [`environment_variables.md`](environment_variables.md) §2.11.

### 5.3 이미지 대용량으로 인한 무선 네트워크 병목 및 소켓 끊김 현상
- **현상**: 단말기 구동 중 화면에 연결 끊김 경보가 자주 표시되며, Metro 번들러 콘솔에 `[WS] 연결 종료`와 `연결 시도 주소` 로그가 무한 반복 출력되는 경우.
- **원인**: 단말 후면 카메라 원본 해상도를 가공 없이 base64로 전송할 경우, 장당 용량이 **1.3MB ~ 3.4MB**에 이르러 초당 10장(10fps) 전송 시 **초당 100Mbps 이상의 지속 업로드 대역폭**을 요구하게 됩니다. 이로 인해 무선 LTE/WiFi 망에서 전송 지연이 발생해 5초 주기 하트비트 세션이 끊어집니다.
- **해결**: 단말 측 `useCamera.ts`에 내장된 `expo-image-manipulator`를 활성화하여, 이미지 크기를 **640x640** 픽셀로 강제 리사이징하고 **50% 수준의 JPEG 압축(`compress: 0.5`)**을 적용해 전송 용량을 **30KB ~ 80KB(초당 1Mbps 이하)** 수준으로 크게 다이어트하여 병목을 원천 방지합니다. 또한, 촬영된 캐시용 임시 파일(`.jpg`)은 `FileSystem.deleteAsync`를 통해 즉각 강제 삭제 청소하여 네이티브 저장 공간 부족을 방지합니다.

---

## 6. 모바일 클라이언트 개발 환경 구축 및 의존성 복원

모바일 클라이언트(React Native / Expo)의 소스코드와 네이티브 설정이 깃허브에 정식 추적 대상(Tracked)으로 등재됨에 따라, 팀원들은 본인의 로컬 개발 환경(macOS/Windows)에 아래의 툴체인 및 패키지를 구성하여 즉시 빌드 및 가동할 수 있습니다.

### 6.1 필수 설치 툴체인 요건

| 플랫폼 | 필수 도구 및 라이브러리 | 권장 버전 / 설명 |
| :--- | :--- | :--- |
| **공통** | **Node.js** | **v18.x 또는 v20.x (LTS)** 권장<br/>자바스크립트/타입스크립트 실행 환경 |
| **공통** | **Yarn** 또는 **npm** | 패키지 매니저 (`npm` 기본 탑재 활용 가능) |
| **iOS 빌드 (macOS 전용)** | **Xcode** | **v15.0+** 및 **Command Line Tools** 필수 설치 |
| **iOS 빌드 (macOS 전용)** | **CocoaPods** | iOS 네이티브 라이브러리 매니저 (`pod` 명령어)<br/>설치: `sudo gem install cocoapods` 또는 Homebrew 사용 |
| **Android 빌드** | **Android Studio** | Android SDK 34(API 34) 이상 및 Build Tools 필수 설정 |
| **Android 빌드** | **JDK (Java SDK)** | **JDK 17** 설치 및 `JAVA_HOME` 환경변수 세팅 |

### 6.2 의존성 복원 및 실기기 빌드 실행 순서

프로젝트 루트 디렉토리(`./Minchodan`)에서 `client` 폴더로 이동한 뒤 순서대로 실행합니다.

#### 1단계. Node 패키지 의존성 복원
```bash
cd client
npm install
```
*`package.json`에 정의된 `react-native-vision-camera`, `expo-audio`, `expo-haptics` 등의 플러그인이 로컬에 설치됩니다.*

#### 2단계. 네이티브 프로젝트 동기화 (Prebuild)
```bash
npx expo prebuild
```
*로컬 환경에 맞춰 `ios/` 및 `android/` 폴더 내의 네이티브 프로젝트 파일을 최신화하고 플랫폼별 종속성을 생성합니다.*

#### 3단계. iOS 네이티브 라이브러리 설치 (macOS 전용)
```bash
cd ios
pod install
cd ..
```
*`Podfile`에 등록된 CoreMLInferenceBridge 네이티브 모듈 및 외부 라이브러리들을 Xcode 프로젝트에 링크시킵니다.*

#### 4단계. 실기기 컴파일 및 런칭

*   **iOS 실기기 빌드 (iPhone을 Mac에 케이블 연결 필수)**:
    ```bash
    npx expo run:ios --device
    ```
*   **Android 실기기/에뮬레이터 빌드 (Windows 및 macOS 공통)**:
    ```bash
    npx expo run:android
    ```

> [!IMPORTANT]
> **iOS 실기기 컴파일 최초 실행 시 주의사항**:
> 최초 빌드 시 Apple Developer 개인용 무료 계정의 팀 프로비저닝 서명이 필요합니다. Xcode(`client/ios/Minchodan.xcworkspace`)를 실행한 뒤 **Signing & Capabilities** 탭에서 본인의 Apple ID를 추가하고 개발자 팀을 선택한 후 빌드를 통과시켜야 합니다. 상세 단계는 [xcode-build-management 스킬 문서](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/.agents/skills/xcode-build-management/SKILL.md)를 참조하십시오.
