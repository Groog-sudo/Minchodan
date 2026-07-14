> **작성일**: 2026-07-13
> **버전**: v1.1.0
> **설명**: iOS/Android 실기기 서버 접속을 WiFi(평상시), USB(개발), Tailscale(외부망) 모드로 병행하는 현재 운영 상황 및 절차

# 모바일 WiFi / USB / Tailscale 접속 (평상시 vs 개발 vs 외부망)

## 1. 배경

실기기 테스트에서 서버 WebSocket(`:8000`) 접속 주소가 환경마다 달랐다.

| 상황 | 단말 → 서버 경로 | 쓰던 주소 | 한계 |
| :--- | :--- | :--- | :--- |
| USB + `adb reverse` | 케이블 터널 | `127.0.0.1` | 선 뽑으면 즉시 끊김 |
| 같은 Wi-Fi / PC 핫스팟 | LAN | PC의 LAN IP | IP가 네트워크마다 바뀜 |
| 노트북이 아이폰 핫스팟을 받고, 다시 모바일 핫스팟을 쏨 | 공기계 → 노트북 핫스팟 | **`192.168.137.1`** | Windows 모바일 핫스팟 기본 게이트웨이 |
| iOS/Android 외부망 | Tailscale VPN | `100.x` 또는 MagicDNS | 단말과 서버 모두 Tailscale Connected 필요 |

2026-07-13 th 실측: 노트북 Wi-Fi가 `172.20.10.2`(아이폰 핫스팟 수신)이어도, **공기계가 붙는 쪽은 노트북이 쏘는 핫스팟**이므로 앱이 써야 할 주소는 `172.20.10.2`가 아니라 **`192.168.137.1`** 이다.

코드/설정을 매번 고쳐 빌드하지 않도록, 앱에 **WiFi / USB 토글**을 두고 두 주소를 동시에 유지한다. 외부망 테스트는 `EXPO_PUBLIC_NETWORK_MODE=tailscale`로 토글보다 Tailscale 주소를 우선한다.

## 2. 역할 분리

| 모드 | 앱 버튼 | WS 주소 | 용도 |
| :--- | :--- | :--- | :--- |
| **WiFi** (기본) | `연결: WiFi` | `ws://{WIFI_HOST}:8000/ws/detect` | 평상시·시연·선 없이 사용 |
| **USB** | `연결: USB` | `ws://127.0.0.1:8000/ws/detect` | 기능 추가·수정·Metro 핫리로드 |
| **Tailscale** | `연결: Tailscale` | `ws://{TAILSCALE_HOST}:8000/ws/detect` | iOS/Android 실기기 외부망 속도 측정 |

- 기본값: **WiFi**
- 선택값은 `expo-file-system`으로 단말에 저장되어 앱 재시작 후에도 유지된다.
- STT·가이드·연락처 등도 동일 WS 세션을 쓰므로, 수송 모드만 맞으면 부가 기능도 같이 동작한다.
- `tailscale`/`ngrok` 모드에서는 앱 버튼이 현재 외부망 라벨만 표시하고 WiFi/USB 주소 전환은 수행하지 않는다.

## 3. 코드 위치

| 파일 | 역할 |
| :--- | :--- |
| `client/src/config/index.ts` | `WIFI_HOST` / `USB_HOST` / `TAILSCALE_HOST` / `buildWsUrl()` / `DEFAULT_SERVER_TRANSPORT` |
| `client/src/services/serverTransport.ts` | 모드 로드·저장, 외부망 라벨 |
| `client/src/hooks/useWebSocket.ts` | `wsBaseUrl` 인자, 모드 변경 시 재연결, `network_probe` RTT 계측 |
| `client/src/components/CameraView.tsx` | UI 라벨 `연결: WiFi` / `연결: USB` / `연결: Tailscale`, 디버그 RTT 표시 |

## 4. 평상시 (WiFi) 절차

1. PC에서 FastAPI(`:8000`) 기동.
2. 공기계를 **노트북 모바일 핫스팟**(또는 PC와 **같은 Wi-Fi**)에 연결.
3. 앱에서 **`연결: WiFi`** 확인 (디버그 줄: `WS: … / WiFi(192.168.137.1)`).
4. USB 케이블은 없어도 된다.

### 4.1 PC가 핫스팟을 쏘는 경우 (현재 th 홈 구성)

| 구간 | 대표 IP | 비고 |
| :--- | :--- | :--- |
| 업링크(예: 아이폰 → 노트북) | `172.20.10.2` | 노트북이 **받는** 쪽. 공기계 앱 주소로 쓰지 않음 |
| 다운링크(노트북 → 공기계) | **`192.168.137.1`** | Windows 모바일 핫스팟 게이트웨이. **앱 WiFi 모드 기본값** |

공기계에서 `http://192.168.137.1:8000/docs` 가 열리면 네트워크는 정상이다.

### 4.2 학원·공용 Wi-Fi (핫스팟이 아닌 경우)

PC의 그 네트워크 IPv4를 확인한 뒤, 빌드/Metro 환경에 주입한다.

```powershell
$env:EXPO_PUBLIC_WIFI_HOST = "192.168.x.x"   # PC의 해당 Wi-Fi IP
# 하위 호환: EXPO_PUBLIC_LAN_IP 도 WIFI_HOST 폴백으로 읽힌다
```

기본값 `192.168.137.1`은 노트북 핫스팟 전제다. 공용 AP에서는 반드시 IP를 바꿔야 한다.

## 5. 외부망 (Tailscale) 절차

iOS 실기기를 LTE/5G 등 외부망에서 테스트할 때 사용한다.

```ini
EXPO_PUBLIC_NETWORK_MODE=tailscale
EXPO_PUBLIC_TAILSCALE_HOST=[SERVER_TAILSCALE_IP_OR_MAGICDNS]
EXPO_PUBLIC_SERVER_PORT=8000
EXPO_PUBLIC_NETWORK_BENCHMARK=true
```

1. 서버 PC와 iPhone 모두 Tailscale 앱을 켜고 같은 tailnet에 로그인한다.
2. 서버 PC에서 FastAPI(`:8000`)를 `0.0.0.0` 바인드로 기동한다.
3. iPhone Safari에서 `http://[SERVER_TAILSCALE_IP_OR_MAGICDNS]:8000/health`가 열리는지 먼저 확인한다.
4. iOS 앱을 재빌드 또는 Metro 캐시 초기화 후 실행한다.
5. 앱 화면 디버그 줄에서 **`연결: Tailscale`**, **`망RTT: ...ms`** 가 표시되는지 확인한다.

Tailscale은 공인 터널이 아니라 VPN 사설망이다. 단말의 Tailscale VPN이 꺼져 있으면 같은 URL이라도 접속되지 않는다.

## 6. 개발 (USB) 절차

기능 추가·수정·JS 핫리로드할 때 사용한다.

```powershell
adb reverse tcp:8000 tcp:8000
adb reverse tcp:8081 tcp:8081
adb reverse --list
```

1. 앱에서 **`연결: USB`** 로 전환.
2. Metro(`:8081`) + FastAPI(`:8000`)가 PC에서 떠 있어야 한다.
3. 케이블을 뽑으면 `127.0.0.1` 경로가 끊기므로, 평상시 테스트로 돌아갈 때는 **`연결: WiFi`** 로 되돌린다.

`adb reverse`는 USB 재연결·adb 재시작 시 자주 풀린다. 끊기면 위 명령을 다시 실행한다. 상세 복구는 [android_wireless_test_guide_v2.md](android_wireless_test_guide_v2.md) 참조.

## 7. 환경 변수

| 변수 | 기본 | 설명 |
| :--- | :--- | :--- |
| `EXPO_PUBLIC_WIFI_HOST` | `192.168.137.1` | WiFi 모드 PC 호스트 |
| `EXPO_PUBLIC_LAN_IP` | (WIFI_HOST 폴백) | 구 명칭. 있으면면 WIFI_HOST로도 사용 |
| `EXPO_PUBLIC_USB_HOST` | `127.0.0.1` | USB + adb reverse 호스트 |
| `EXPO_PUBLIC_TAILSCALE_HOST` | (WIFI_HOST 폴백) | Tailscale 외부망 서버 호스트 |
| `EXPO_PUBLIC_SERVER_PORT` | `8000` | FastAPI/WebSocket 포트 |
| `EXPO_PUBLIC_DEFAULT_TRANSPORT` | `wifi` | 최초 기동 기본 모드 (`wifi` \| `usb`) |
| `EXPO_PUBLIC_NETWORK_MODE` | `lan` | `ngrok` 또는 `tailscale`이면 WiFi/USB 토글보다 외부망 주소 우선 |
| `EXPO_PUBLIC_NETWORK_BENCHMARK` | `false` | `true`이면 앱에서 `network_probe` RTT 표시 |

명세 표: [environment_variables.md](environment_variables.md) §2.14.

## 8. 방화벽

WiFi 모드에서 단말이 PC의 `:8000`(및 Metro 사용 시 `:8081`)에 닿지 않으면 Windows 방화벽 인바운드를 연다. **관리자 권한**이 필요하다.

```text
TCP 8000  (FastAPI / WebSocket)
TCP 8081  (Metro, 개발 번들 로드 시)
```

같은 PC에서 `http://192.168.137.1:8000/docs` 가 200이어도, 단말만 막히는 경우가 있으니 단말 브라우저로 한 번 확인한다.

## 9. 관련 문서

| 문서 | 용도 |
| :--- | :--- |
| [android_wireless_test_guide_v2.md](android_wireless_test_guide_v2.md) | adb reverse 끊김·데드락 복구 |
| [android_build_and_wireless_test_guide.md](android_build_and_wireless_test_guide.md) | 빌드·ngrok 기본 절차 |
| [wireless_test_guide.md](wireless_test_guide.md) | LTE/ngrok 외부망 |
| [ios_android_bifurcation_contract.md](../mobile/ios_android_bifurcation_contract.md) §7.3 | 네트워크 상수 보존 계약 |
