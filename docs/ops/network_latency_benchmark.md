# Tailscale 네트워크 지연 벤치마크 가이드

> **작성일**: 2026-07-13
> **버전**: v0.1.0
> **목적**: ngrok 대비 Tailscale 외부망 전환 후 WebSocket 왕복 지연(RTT) 개선 폭을 같은 기준으로 측정합니다.

---

## 1. 측정 범위

| 항목 | 측정 여부 | 설명 |
| :--- | :--- | :--- |
| **WebSocket 순수 RTT** | **측정** | `network_probe` → `network_probe_ack` 왕복 시간 |
| **핸드셰이크 시간** | **측정** | `welcome` 수신부터 `auth_ok` 수신까지 시간 |
| **프레임 디코딩/YOLO/TTS 지연** | 제외 | 네트워크 경로 비교와 섞이지 않도록 제외 |
| **단방향 지연** | 제외 | 단말과 서버 시계가 동기화되어 있지 않아 신뢰하지 않음 |

---

## 2. iOS 앱 외부망 설정

iPhone이 LTE/5G 등 외부망에 있고 Tailscale VPN으로 서버에 붙는 기준입니다.

| 파일 | 설정 |
| :--- | :--- |
| `client/.env` | 아래 예시처럼 Tailscale 모드와 서버 주소를 지정 |
| `client/src/config/index.ts` | `EXPO_PUBLIC_NETWORK_MODE=tailscale`이면 `ws://{TAILSCALE_HOST}:{SERVER_PORT}/ws/detect` 생성 |
| `client/src/hooks/useWebSocket.ts` | `EXPO_PUBLIC_NETWORK_BENCHMARK=true`이면 앱에서 `network_probe` 주기 전송 |
| `client/src/components/CameraView.tsx` | 디버그 줄에 `망RTT: ...ms (평균 ...ms)` 표시 |

```ini
EXPO_PUBLIC_NETWORK_MODE=tailscale
EXPO_PUBLIC_TAILSCALE_HOST=[SERVER_TAILSCALE_IP_OR_MAGICDNS]
EXPO_PUBLIC_SERVER_PORT=8000
EXPO_PUBLIC_NETWORK_BENCHMARK=true
EXPO_PUBLIC_NETWORK_BENCHMARK_INTERVAL_MS=1000
EXPO_PUBLIC_NETWORK_BENCHMARK_PAYLOAD_BYTES=256
EXPO_PUBLIC_DEVICE_ID=dev-001
EXPO_PUBLIC_DEVICE_TOKEN=[DEVICE_TOKEN]
```

> `EXPO_PUBLIC_*` 값은 iOS 앱 번들에 평문 포함됩니다. 비밀키를 넣지 말고, 디바이스 토큰도 운영용 장기 비밀로 취급하지 않습니다.

---

## 3. iOS 실기기 확인 순서

| 순서 | 작업 | 정상 기준 |
| :--- | :--- | :--- |
| 1 | 서버 PC와 iPhone에서 Tailscale Connected 확인 | 같은 tailnet 장비 목록 표시 |
| 2 | iPhone Safari에서 `http://[SERVER_TAILSCALE_HOST]:8000/health` 접속 | JSON 응답 반환 |
| 3 | `client/.env` 설정 후 Metro 캐시 초기화 | 새 환경 변수가 번들에 반영 |
| 4 | iOS 앱 실행 | 화면에 `연결: Tailscale` 표시 |
| 5 | 10초 이상 대기 | `망RTT: ...ms (평균 ...ms)` 값 갱신 |

```bash
cd client
npx expo start -c
```

릴리즈 또는 개발 빌드에 환경 변수가 이미 인라인된 상태라면 앱을 다시 빌드해야 합니다.

---

## 4. 터미널 비교 측정

서버가 `network_probe`를 지원하므로 같은 스크립트로 ngrok과 Tailscale을 나란히 측정할 수 있습니다.

```bash
python scripts/benchmark_ws_network.py \
  --target ngrok=wss://[NGROK_DOMAIN]/ws/detect \
  --target tailscale=ws://[SERVER_TAILSCALE_HOST]:8000/ws/detect \
  --device-id dev-001 \
  --token [DEVICE_TOKEN] \
  --count 50 \
  --warmup 5 \
  --json-out outputs/network_latency/ngrok_vs_tailscale.json \
  --csv-out outputs/network_latency/ngrok_vs_tailscale.csv
```

| 출력값 | 의미 |
| :--- | :--- |
| `handshake` | WS 접속 후 인증 완료까지 걸린 시간 |
| `avg` | 측정 샘플 평균 RTT |
| `p50` | 중앙값 RTT |
| `p95` | 상위 95퍼센트 지연 |
| `max` | 최악 샘플 RTT |
| `improve` | 첫 번째 `--target` 평균 RTT 대비 개선율 |

---

## 5. 권장 측정 조건

| 조건 | 권장값 |
| :--- | :--- |
| 샘플 수 | `--count 50` 이상 |
| 워밍업 | `--warmup 5` 이상 |
| 페이로드 | `256` bytes 기본 유지 |
| 측정 순서 | ngrok을 첫 번째 target, Tailscale을 두 번째 target |
| iOS 앱 측정 | 같은 장소에서 ngrok 빌드와 Tailscale 빌드를 각각 30초 이상 관찰 |

---

## 6. 해석 기준

| 결과 | 판단 |
| :--- | :--- |
| Tailscale `avg`와 `p95` 모두 감소 | 전환 효과가 안정적으로 있음 |
| `avg`만 감소하고 `p95`가 높음 | 순간 지연이 남아 있어 실기기 보행 테스트 추가 필요 |
| Tailscale 실패, ngrok 성공 | iPhone Tailscale VPN, 서버 방화벽, 포트 `8000` 열림 여부 확인 |
| 둘 다 실패 | FastAPI 서버 또는 디바이스 토큰 인증부터 확인 |

Tailscale은 공개 터널이 아니라 tailnet 사설망입니다. 단말과 서버가 모두 Tailscale에 연결되어 있어야 하며, 서버 OS 방화벽이 Tailscale 인터페이스의 TCP `8000`을 허용해야 합니다.
