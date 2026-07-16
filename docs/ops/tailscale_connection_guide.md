> **작성일**: 2026-07-13
> **버전**: v1.0.0
> **작성 목적**: ngrok 프록시망 우회 및 Tailscale P2P VPN 기반 초고속 보행보조 실시간 스트리밍 환경 구축 가이드

---

# Tailscale 기반 고속 무선 개발 연결 가이드

## 1. 개요

Minchodan 보행보조 플랫폼은 즉각적인 장애물 반응(반사 경로) 및 실시간 가이드(인지 경로)를 위해 극도의 초저지연(Ultra-low Latency)이 요구됩니다. 기존의 `ngrok` 터널링 기술은 클라우드 프록시 서버를 거쳐 통신하므로 외부망 테스트가 가능하지만 지연이 크게 누적됩니다.

본 가이드는 가상 사설망(VPN) 솔루션인 **Tailscale**을 도입하여 개발 PC(API 서버 및 Metro 번들러 호스트)와 물리 스마트폰 간에 직접 P2P 터널링을 구성하고, 외부망 및 LTE 환경에서도 내부 LAN 직결에 준하는 전송 속도를 확보하기 위한 설정 절차를 정의합니다.

---

## 2. 네트워크 아키텍처

아래 다이어그램은 Tailscale을 경유하는 PC와 단말 간의 암호화 터널 통신 구조입니다.

```mermaid
graph TD
    subgraph "Tailnet (100.64.0.0/10)"
        PC["개발 PC (desktop-hujuvss)<br/>IP: 100.92.150.34"]
        App["스마트폰 단말 (s25-ultra)<br/>IP: 100.112.79.15"]
    end

    subgraph "Services on PC"
        Metro["Metro Bundler (Port 8081)"]
        FastAPI["FastAPI WebSocket Server (Port 8000)"]
    end

    App -- "1. exp://100.92.150.34:8081<br/>자체 빌드 로드" --> Metro
    App -- "2. ws://100.92.150.34:8000/ws/detect<br/>실시간 프레임 전송" --> FastAPI

    linkStyle 0,1 stroke:#2ecd71,stroke-width:2px;
```

---

## 3. 기기별 사전 준비 작업

팀원 개개인이 소유한 PC와 테스트용 스마트폰에 아래의 공통 작업을 수행합니다.

| 분류 | 작업 항목 | 세부 수행 내용 |
| :--- | :--- | :--- |
| **공통** | **Tailscale 회원가입** | Tailscale 공식 웹사이트에서 조직 또는 개인 계정으로 가입합니다. |
| **PC** | **Tailscale 설치 및 로그인** | Windows/macOS용 Tailscale 클라이언트를 설치하고 로그인합니다. |
| **모바일** | **Tailscale 앱 설치 및 로그인** | Android/iOS 앱스토어에서 Tailscale을 내려받은 뒤 PC와 **동일한 계정**으로 로그인하고 VPN Profile 생성을 허용합니다. |
| **공통** | **장치 연결 상태 확인** | Tailscale 관리 콘솔(Admin Console)에서 PC와 스마트폰이 모두 Connected 상태인지 확인하고 각각의 가상 IP(100.x.y.z)를 메모합니다. |

---

## 4. 개발 환경 설정 (PC)

### 4.1 클라이언트 설정 수정
`client/src/config/index.ts` 파일에서 네트워크 접속 방식을 `lan`으로 전환하고, LAN_IP에 **PC의 Tailscale IP**를 입력합니다.

```typescript
// client/src/config/index.ts
const NETWORK_MODE = "lan"; // ngrok에서 lan으로 전환

const LAN_IP = "100.92.150.34"; // 본인 PC의 Tailscale IP 기입
```

또는 개발 환경 변수 파일(`.env`)을 통해 주입할 수도 있습니다.
```env
EXPO_PUBLIC_NETWORK_MODE=lan
EXPO_PUBLIC_LAN_IP=100.92.150.34
```

### 4.2 Metro Bundler 실행 방식 변경
이전의 외부망 테스트를 위해 추가했던 `--tunnel` 옵션을 제거하고 순수 LAN/로컬 모드로 번들러를 켭니다.

```bash
# client 폴더 내부에서 실행
npx expo start -c --scheme minchodan
```

---

## 5. 앱 실행 및 접속 방법 (단말)

> [!IMPORTANT]
> **Expo Go 범용 클라이언트 미지원 경고**
> `react-native-vision-camera` 등 네이티브 카메라 모듈을 사용하는 프로젝트 특성상 **일반 Expo Go 앱으로는 접속 시 'runtime not ready' 오류가 발생**하며 구동할 수 없습니다.

### 5.1 네이티브 개발 빌드 앱(Development Build) 설치가 되어 있는 경우
1. 스마트폰의 Tailscale 앱에서 커넥션 상태를 활성화(Active)합니다.
2. 기기에 미리 빌드된 `minchodan` 개발용 독립 앱을 실행합니다.
3. 연결 주소창이 나타나면 PC의 가상 IP와 포트를 조합한 주소를 기입하고 엔터를 누릅니다.
   - 예: `100.92.150.34:8081`

### 5.2 기기에 개발 빌드가 설치되어 있지 않은 경우 (최초 1회 필수)
1. 스마트폰을 PC에 USB 케이블로 연결하고 Android 개발자 모드(USB 디버깅)를 켭니다.
2. 다음 명령어로 스마트폰 기기에 네이티브 코드가 포함된 커스텀 개발 빌드 앱을 생성하여 직접 업로드 및 설치합니다.
   ```bash
   npm run android
   ```
3. 설치된 앱 아이콘을 터치하여 실행한 후 메트로 서버 주소(`100.92.150.34:8081`)로 연동을 완료합니다.

---

## 6. 문제 해결 및 문제 상황 진단 (Troubleshooting)

### 6.1 Windows 방화벽에 의한 포트 차단
Tailscale 인터페이스는 Windows 운영체제에서 공용 네트워크(Public Network)로 간주되어 인바운드 트래픽이 완전 차단되는 경우가 빈번합니다. 접속이 실패한다면 다음 조치를 취하십시오.
- **조치**: `고급 보안이 설정된 Windows Defender 방화벽` -> `인바운드 규칙`으로 진입하여 TCP `3306`(MariaDB), `8000`(FastAPI), `8081`(Metro) 포트에 대해 **모든 네트워크 연결 허용** 규칙을 수동 추가하십시오.

### 6.2 MagicDNS로 인한 ngrok 연동 실패
만약 Tailscale 콘솔에서 MagicDNS를 켜둔 상태로 다른 팀원이나 타 외부망 기기와의 ngrok 터널링 연동을 수행할 때 도메인 주소 해석 지연 혹은 연결 유실이 발생할 수 있습니다.
- **조치**: ngrok 터널을 일시 병행해야 하는 상황이 생긴다면 Tailscale 연결 상태를 일시 중지(Disconnect)하거나 시스템 DNS 설정을 점검하십시오.
