# Android 실기기 테스트 환경 오케스트레이션 가이드

> **작성일**: 2026-07-29
> **버전**: v1.0.0
> **대상**: macOS 개발 호스트에서 Android 실기기(Xiaomi 12 등) 통합 테스트를 수행하는 담당자 및 AI 에이전트
> **진입점 스크립트**: [`scripts/android_lab.sh`](../../scripts/android_lab.sh)
> **관련 문서**: [`docs/ops/android_wireless_test_guide_v2.md`](android_wireless_test_guide_v2.md)(입문자용 Windows 절차), [`.agents/skills/integration-test-orchestrator/SKILL.md`](../../.agents/skills/integration-test-orchestrator/SKILL.md)(iOS 경로)

---

## 1. 배경

기존 통합 테스트 오케스트레이션(`integration-test-orchestrator` 스킬, `scripts/metro_tailscale.sh`)은 **iOS 전용**이었습니다. 실기기 실행 경로가 `xcrun devicectl` 에 고정되어 있어 Android 단말에는 그대로 적용할 수 없었고, adb 무선 디버깅·Tailscale 경유 접속·logcat 수집은 매 세션 수작업으로 재구성해야 했습니다.

`scripts/android_lab.sh` 는 그 대칭 구현입니다. Docker 스택·Tailscale·Metro·adb·Dev Client 딥링크·로그 수집을 하나의 진입점으로 묶습니다.

| 계층 | iOS 경로 | Android 경로(본 문서) |
| :--- | :--- | :--- |
| 백엔드 | `docker compose --env-file .env -f docker/docker-compose.macos.yml up -d` | 동일 (`android_lab.sh up` 이 내부 호출) |
| 번들러 | `scripts/metro_tailscale.sh start` | 동일 (재사용, packager host 만 주입) |
| 단말 연결 | USB / `devicectl list devices` | `adb pair` + `adb connect` (무선 디버깅, Tailscale 가능) |
| 앱 실행 | `devicectl device process launch --payload-url` | `adb shell am start -a VIEW -d <딥링크>` |
| 단말 로그 | `devicectl ... --console` | `adb logcat` |

---

## 2. 선행 의존성

| 구분 | 요구사항 | 확인 |
| :--- | :--- | :--- |
| **adb** | Android SDK platform-tools | `bash scripts/android_lab.sh doctor` |
| **Docker** | Docker Desktop + Compose v2 | 동일 |
| **Tailscale** | 단말이 개발 호스트와 다른 망일 때 필수 | 동일 |
| **Node.js** | Expo/Metro 실행 | 동일 |
| **단말** | 개발자 옵션 + **무선 디버깅** 활성화, 화면 잠금 해제 | 단말 설정 |

`adb` 가 `PATH` 에 없어도 스크립트가 `~/Library/Android/sdk/platform-tools/adb` 등 표준 설치 경로를 자동 탐색합니다.

---

## 3. 표준 실행 절차

```bash
# 0) 환경 점검 (adb/tailscale/docker/node + 네트워크 프로필)
bash scripts/android_lab.sh doctor

# 1) 단말 무선 디버깅 최초 페어링 (단말: 개발자 옵션 > 무선 디버깅 > 페어링 코드로 기기 페어링)
bash scripts/android_lab.sh pair <단말_IP>:<페어링_포트> <6자리_코드>

# 2) 이후 세션에서는 접속만 (무선 디버깅 화면의 'IP 주소 및 포트')
bash scripts/android_lab.sh connect <단말_IP>:<접속_포트>

# 3) 전 계층 일괄 기동 (docker -> metro -> adb -> Dev Client 실행)
bash scripts/android_lab.sh up

# 4) 상태 확인
bash scripts/android_lab.sh status

# 5) 로그 수집 (기본 60초, logs/android_sessions/<타임스탬프>/)
bash scripts/android_lab.sh logs 120

# 6) 정리 (볼륨 보존)
bash scripts/android_lab.sh down
```

---

## 4. 네트워크 모드 선택 (LAN vs Tailscale)

`client/.env` 의 `EXPO_PUBLIC_NETWORK_MODE` 를 기본 추종하며, `LAB_HOST=lan|tailscale` 로 일회성 재정의할 수 있습니다.

| 모드 | 조건 | 특성 |
| :--- | :--- | :--- |
| **lan** (기본) | 단말과 호스트가 같은 WiFi | 번들·TFLite 에셋 로딩 빠름. **권장** |
| **tailscale** | 단말이 LTE/핫스팟/외부 WiFi | 어디서나 연결되지만, **직결(direct) 실패 시 DERP 릴레이로 떨어지며 Metro 에셋 로딩이 극단적으로 느려짐**(2026-07-24 실측: seg/det 모델 각 수십 초, JS 스레드·WS 동반 지연) |

DERP 폴백 여부는 아래로 확인합니다. `direct connection not established` 가 보이면 릴레이 경유입니다.

```bash
tailscale ping -c 3 <단말_TAILSCALE_IP>
```

### 4.1 가장 흔한 함정: 호스트 IP 변경

장소를 옮겨 호스트 LAN IP 가 바뀌었는데 `client/.env` 의 `EXPO_PUBLIC_LAN_IP` 가 예전 값으로 남아 있으면, 단말은 옛 주소로 붙으려다 흰 화면 또는 WS 연결 실패로 끝납니다. `doctor` 가 현재 기본 경로 인터페이스 IP 와 대조해 경고합니다.

```text
WARN: client/.env 의 LAN_IP(192.168.0.227) 와 현재 호스트 IP(172.30.26.142) 가 다릅니다.
```

Metro 도 packager hostname 이 기동 시점에 고정되므로, `.env` 를 고쳤다면 반드시 재기동합니다.

```bash
REACT_NATIVE_PACKAGER_HOSTNAME=<현재 호스트 IP> bash scripts/metro_tailscale.sh restart
```

---

## 5. adb 무선 디버깅 실무 주의사항

| 항목 | 내용 |
| :--- | :--- |
| **포트 회전** | 페어링 포트와 접속 포트는 무선 디버깅 화면을 닫거나 재부팅하면 바뀝니다. 사용자가 읽어준 포트가 이미 만료되어 `protocol fault` 가 나는 경우가 잦습니다. 스크립트는 실패 시 `adb mdns services` 로 실측 포트를 재탐색합니다. |
| **mDNS 미도달** | mDNS 는 Tailscale 을 넘지 못합니다. 단말이 다른 망이면 자동 탐색이 실패하므로 `IP:PORT` 를 직접 넘겨야 합니다. |
| **5555 미개방** | 재부팅 후 adbd 는 TCP/IP 모드가 아닙니다. `adb connect <ip>:5555` 는 `Connection refused` 로 끝나며, Android 11+ 무선 디버깅 페어링을 써야 합니다. |
| **transport 중복** | mDNS 자동 등록 + 수동 connect 로 transport 가 2개 이상이면 `-s` 없이 실행되는 adb 명령이 실패합니다. `ANDROID_SERIAL` 로 고정하십시오. |
| **자동 잠금** | HyperOS 는 `settings put system screen_off_timeout` 을 무시하고 잠급니다. 장시간 측정 시 개발자 옵션의 **충전 중 화면 켜짐 유지** 를 켜십시오. |

---

## 6. MIUI/HyperOS 카메라 제한 회피

Fast Refresh 이후나 프로세스를 남긴 채 재진입하면 `camera-is-restricted` 로 카메라가 차단됩니다. 반드시 **force-stop 후 딥링크 재실행** 해야 합니다. `android_lab.sh launch` 가 이 순서를 강제합니다.

```bash
adb -s <serial> shell am force-stop com.minchodan.app
adb -s <serial> shell am start -a android.intent.action.VIEW -d "minchodan://expo-development-client/?url=http%3A%2F%2F<host>%3A8081"
```

런처 아이콘으로 앱을 직접 띄우면 Metro 로그 파이프라인이 끊겨 측정 로그를 놓칩니다(2026-07-29 실측). 성능 측정 세션에서는 항상 딥링크 실행을 사용하십시오.

---

## 7. 로그 수집 체계

`bash scripts/android_lab.sh logs <초>` 는 `logs/android_sessions/<타임스탬프>/` 에 아래를 남깁니다(`logs/` 는 gitignore 대상).

| 파일 | 내용 |
| :--- | :--- |
| `logcat.log` | 단말 전체 logcat (`-v time`, 수집 직전 버퍼 clear) |
| `fastapi.log` | FastAPI 컨테이너 로그 |
| `metro_tail.log` | Metro 로그 마지막 500행 |

장애 진단 시에는 세 파일을 시각 기준으로 대조해 **단말 / 네트워크 / 서버** 중 어느 계층에서 끊겼는지 먼저 분리합니다.

---

## 8. 안전 가드레일

`integration-test-orchestrator` 스킬의 금지 사항을 그대로 계승합니다.

- `docker compose down -v` 금지 (로컬 MariaDB/Redis 볼륨 소실). `android_lab.sh down` 은 `stop` 만 수행합니다.
- `.env` 전체 출력 금지. 스크립트는 `EXPO_PUBLIC_*` 공개 변수만 읽습니다.
- 공동 원격 DB 에 DDL/DROP/TRUNCATE 금지.
- 단말 식별자(시리얼, Tailscale IP)를 공유 문서·커밋에 남기지 않습니다. 본 문서의 IP 는 예시 형식 설명용입니다.
