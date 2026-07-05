> **작성일**: 2026-07-05
> **버전**: v1.0.0
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

로컬 개발 환경에서는 macOS CPU Fallback을 고려하여 최적화된 [docker-compose.macos.yml](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/docker/docker-compose.macos.yml) 설정에 따라 총 3개의 컨테이너가 긴밀하게 맞물려 구동됩니다.

| 컨테이너 이름 | 이미지 / 포트 | 주요 기능 및 역할 | 데이터 볼륨 마운트 |
| :--- | :--- | :--- | :--- |
| **`minchodan-fastapi`** | `minchodan-server:latest`<br/>**`8000:8000`** | **WebSocket Gateway** (/ws/detect)<br/>**YOLOv8 Detection / Segmentation** 추론<br/>ByteTrack 객체 추적기 탑재<br/>Kokoro-82M TTS 한글 음성 합성 | `./server:/app/server`<br/>`./data:/app/data`<br/>`./.env:/app/.env` |
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
1. **프레임 캡처**: 단말의 카메라 모듈이 10fps 속도로 도로/실내 환경을 촬영하여 base64 JPEG 텍스트로 인코딩합니다.
2. **데이터 송신**: 단말이 서버로 `detection` 타입 패킷을 전송합니다:
   - 필드 키: **`thumbnail_jpeg_b64`** 에 base64 텍스트를 적재하여 전송합니다.
3. **디코딩 및 리사이즈**: 서버의 OpenCV 모듈이 base64 바이너리를 메모리 버퍼로 디코딩하고, YOLO 입력 포맷인 **`640x640`** 크기로 정규화 리사이즈를 단 수십 밀리초(ms) 내로 완료합니다.
4. **듀얼헤드 YOLO 추론**:
   - **Object Detection**: 볼라드, 킥보드, 계단 등 시각장애인 위협 장애물을 바운딩 박스로 탐지합니다.
   - **Segmentation**: 보행 가능 안전 구역 및 점자블록 노면을 픽셀 단위로 분할 분석합니다.
5. **ByteTrack 객체 추적**: 탐지된 객체의 프레임 간 궤적을 실시간으로 식적 추적하며 고유 ID를 부여합니다.
6. **응답 송신**: 서버가 디코딩 및 탐지 완료 통계를 동봉하여 단말에 즉각 `ack` 응답을 리턴합니다.

---

## 5. 장애 대응 및 핵심 트러블슈팅

### 5.1 base64 데이터 없음 에러
- **현상**: 서버 로그에 `[FrameDecoder] base64 데이터 없음` 경고가 반복하여 발생하고 추론이 생략되는 경우.
- **원인**: 단말 측에서 쏘는 JSON 페이로드의 이미지 데이터 필드 키가 서버가 요구하는 **`thumbnail_jpeg_b64`**가 아닌 `base64` 등의 다른 키로 매핑되어 전달되었기 때문입니다.
- **해결**: [CameraView.tsx](file:///Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan/client/src/components/CameraView.tsx)의 `sendRef.current` 호출 부 payload 키를 `thumbnail_jpeg_b64`로 명확하게 지정하여 재빌드 및 재배포해야 합니다.

### 5.2 lap 트래킹 라이브러리 부재 에러
- **현상**: `requirements: Ultralytics requirement ['lap>=0.5.12'] not found` 로그가 출력되는 경우.
- **원인**: YOLOv8 객체 추적기(ByteTrack) 구동을 위한 선형 할당(Linear Assignment) 패키지가 Docker 이미지에 누락되어 있기 때문입니다.
- **해결**: 컨테이너가 자동으로 pip AutoUpdate를 통해 `lap`을 수집하므로, 성공 메시지 확인 후 `docker restart minchodan-fastapi` 명령어로 컨테이너를 가볍게 1회 재기동해주면 정상 바인딩됩니다.
