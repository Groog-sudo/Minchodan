---
name: rpi-network-profile-switcher
description: 시연(demo)·테스트(test) 환경에서 Raspberry Pi MariaDB·미디어 API, Mac mini Ollama LLM, Windows GPU FastAPI/Redis/운영 콘솔, Metro 번들러를 역할별로 기동·점검하고, DB_HOST·IMAGE_SERVER_BASE_URL·COMPOSE_OLLAMA_BASE_URL 네트워크 프로필을 Docker 이미지 재빌드 없이 전환·검증한다. Minchodan에서 .env.network.demo/test, NETWORK_ENV_FILE, ssh minchodan-rpi-db, metro_tailscale.sh, ollama_demo_keepalive.sh, socat DB 프록시, UFW, 또는 실기기-서버-LLM-DB 시연 백엔드 기동·연결을 설정·복구할 때 사용한다.
---

# 시연/테스트 환경 기동·네트워크 프로필 전환 (Raspberry Pi DB·Mac mini LLM·GPU 서버)

> **작성일**: 2026-07-20
> **버전**: v1.2.0 (2026-07-21: 시연용 서버 기동(역할별 Docker·Ollama·Metro·console·Pi) 체크리스트를 스킬 본범위에 편입. 이전 v1.1.1: `ollama_demo_keepalive.sh` 등재. 이전 v1.1.0: LLM LAN을 demo 프로필에 통합)
> **관련 문서**: `docs/ops/deployment_guide.md`, `docs/ops/environment_variables.md`, `docs/db_tailscale_guide/README.md`, [`docs/ops/demo_test_device_inventory.md`](../../../docs/ops/demo_test_device_inventory.md)(시연 장비 제원·네트워크 토폴로지)
> **관련 스킬**: iOS 실기기 **빌드·설치·실행**과 세션 로그 오케스트레이션 세부 절차는 [`integration-test-orchestrator`](../integration-test-orchestrator/SKILL.md)·[`xcode-build-management`](../xcode-build-management/SKILL.md)를 이어서 사용한다. **시연에 필요한 서버 프로세스 기동·헬스·네트워크 전환은 본 스킬이 1차 담당**한다.
> **지원 에이전트**: Claude Code 등은 본 `SKILL.md`를 직접 읽어 호출한다. OpenAI Codex 계열은 `agents/openai.yaml`을 통해 동일 스킬을 인식·호출한다.

---

## 목적과 실행 경계

시연/테스트 때 아래를 한 스킬에서 다룬다.

1. **시연용 서버 기동**: 역할별(Pi / Mac mini / GPU 서버 / Metro·콘솔 호스트)로 필요한 프로세스를 올리고 헬스 확인
2. **네트워크 프로필 전환**: Raspberry Pi DB·미디어, Mac mini Ollama 접속 경로를 `demo`(시연 LAN) / `test`(Tailscale)로 전환·검증

이미지 생성은 네트워크 설정과 분리하고, 전환 시에는 기존 `minchodan-server:latest`를 재사용한다(`docker compose build` 금지). 최초 이미지가 없을 때만 서버 담당자가 별도 빌드한다(기동 섹션 참고).

| 프로필 | DB·미디어(Raspberry Pi) | LLM(Mac mini) | 로컬 설정 파일 | 실행 명령 |
| :--- | :--- | :--- | :--- | :--- |
| **`demo`** | 시연 장소 내부망(LAN) | 시연 장소 내부망(LAN, `COMPOSE_OLLAMA_BASE_URL`) | `.env.network.demo` | `bash scripts/switch_rpi_network.sh demo` |
| **`test`** | Tailscale 외부망 | 동일 호스트(Docker 컨테이너 기본값, `host.docker.internal`) | `.env.network.test` | `bash scripts/switch_rpi_network.sh test` |

**프로필 전환 실행 위치**: FastAPI/Docker가 도는 서버에서 실행한다. 시연 구성은 서버=Windows(GPU)이므로 **WSL2 안(bash)** 에서 실행한다(Windows 네이티브 cmd/PowerShell/Git Bash는 `unsupported OS`). macOS에서 FastAPI를 띄우는 개발 환경이면 Darwin 분기(`docker-compose.macos.yml` + `socat`)를 쓴다.

**시연 토폴로지 요약** ([`demo_test_device_inventory.md`](../../../docs/ops/demo_test_device_inventory.md) §2):

| 연결 | 방식 |
| :--- | :--- |
| iPhone ↔ GPU 서버(FastAPI) | Tailscale |
| GPU 서버 ↔ Mac mini(Ollama) | LAN |
| GPU 서버 ↔ Raspberry Pi(DB·미디어) | LAN (`demo` 프로필) |

사용자가 상태 확인·진단만 요청하면 읽기 전용 검사까지만 수행한다. 기동·전환·복구를 요청한 경우에만 해당 범위의 변경을 수행한다. 커밋·푸시는 별도 요청이 있을 때만 수행한다.

---

## 시연 전 서버 기동 (역할별)

에이전트는 사용자 요청이 "시연 준비", "서버 올려", "LLM 서버 역할", "demo 기동" 등이면 **아래 순서로 기동·검증**한다. 이미 정상인 서비스는 재시작하지 않는다. `docker compose down -v`, DB DDL/DROP/TRUNCATE는 금지.

### 0. 역할 매핑 (어느 머신에서 무엇을)

| 역할 | 장비 | 기동 대상 | 담당 에이전트/사람 |
| :--- | :--- | :--- | :--- |
| DB·미디어 | Raspberry Pi | `mariadb`, `minchodan-image-server` (systemd) | Pi 도달 가능 호스트에서 SSH |
| LLM | Mac mini | Ollama `0.0.0.0:11434` + `gemma4:e4b`/`nomic-embed-text` 상주 | Mac mini 세션 |
| GPU 추론·API·콘솔 | Windows (WSL2) | Docker `fastapi` + `redis` + `console`, 이어서 `demo` 프로필 전환 | GPU 서버 세션 |
| Metro (RN 번들) | `client/.env`의 Tailscale/LAN 번들 호스트(시연에선 보통 Mac mini 또는 GPU 서버) | `scripts/metro_tailscale.sh` | 해당 호스트 세션 |
| iOS 앱 빌드·설치 | Mac + 실기기 | Xcode/`devicectl` | [`integration-test-orchestrator`](../integration-test-orchestrator/SKILL.md)에 위임(본 스킬은 Metro 기동까지만 필수) |

권장 기동 순서: **Pi → Mac mini(Ollama) → GPU Docker → demo 프로필 전환 → Metro → (선택) iOS 실행**.

### 1. Raspberry Pi (MariaDB·미디어)

```bash
ssh minchodan-rpi-db 'hostname; systemctl is-active mariadb minchodan-image-server tailscaled'
```

`inactive`/`failed`이고 사용자가 기동을 요청한 경우에만:

```bash
ssh minchodan-rpi-db 'sudo systemctl start mariadb minchodan-image-server'
ssh minchodan-rpi-db 'systemctl is-active mariadb minchodan-image-server'
```

통과: 두 서비스 `active`, (필요 시) LAN에서 DB TCP·미디어 `/health` 응답.

### 2. Mac mini (Ollama LLM)

`demo` 프로필은 Mac mini Ollama가 LAN에 열려 있어야 한다. GUI 앱만 켜면 `127.0.0.1`에만 바인딩되는 경우가 많다. 실패 시 `OLLAMA_HOST=0.0.0.0`으로 `ollama serve`를 재기동한다.

```bash
# Mac mini에서만
bash scripts/ollama_demo_keepalive.sh
# LAN 검증(실 IP는 출력·Git에 남기지 말고 로컬만 확인)
lsof -nP -iTCP:11434 -sTCP:LISTEN   # *:11434 또는 0.0.0.0 이어야 함
curl -sf --max-time 3 "http://127.0.0.1:11434/api/tags" >/dev/null
curl -sf --max-time 3 "http://127.0.0.1:11434/api/ps"   # gemma4:e4b, nomic-embed-text 상주
```

통과: LAN에서 `/api/tags` 200, 두 모델 `keep_alive=-1` 상주. Ollama 종료·Mac 재부팅 후 재실행.

### 3. GPU 서버 (Windows WSL2) — FastAPI·Redis·운영 콘솔

저장소 루트, WSL2 bash:

```bash
# 스택이 없으면 기동(이미지 있으면 --no-build 권장). 최초 이미지가 없을 때만 build.
docker compose --env-file .env -f docker/docker-compose.yml up -d --no-build

# redis / fastapi / console 상태
docker compose --env-file .env -f docker/docker-compose.yml ps
curl -sf --max-time 5 "http://127.0.0.1:${WS_PORT:-8000}/" >/dev/null
curl -sf --max-time 5 -o /dev/null -w "console %{http_code}\n" "http://127.0.0.1:${CONSOLE_PORT:-5174}/"
```

`console`는 compose의 Vite 운영자 콘솔(`:5174`, `VITE_PROXY_TARGET=http://fastapi:8000`)이다. compose `up`에 포함되므로 별도 `npm run dev`는 시연 기본 경로가 아니다.

이어서 **demo 프로필**로 DB/미디어/LLM URL을 붙인다(아래 [실행 워크플로우](#실행-워크플로우) §3~§4).

```bash
MINCHODAN_SWITCH_CHECK_ONLY=1 bash scripts/switch_rpi_network.sh demo
bash scripts/switch_rpi_network.sh demo
```

시연에서 아이폰이 Tailscale로 FastAPI에 붙는 경우, 서버 측 Tailscale(및 필요 시 Tailscale Serve → `127.0.0.1:8000`)이 살아 있는지 확인한다. 비밀값·실 IP는 Git에 기록하지 않는다.

macOS에서 FastAPI를 띄우는 개발/검증이면 `docker/docker-compose.macos.yml` + `socat` 경로를 쓴다.

### 4. Metro (React Native 번들러)

실기기 JS 번들용. **시연 스킬 범위에 포함**한다. iOS 네이티브 빌드·설치는 통합 스킬에 위임.

```bash
# 번들 호스트(client/.env의 EXPO_PUBLIC_NETWORK_MODE=tailscale 및 Tailscale 호스트와 일치하는 머신)에서
bash scripts/metro_tailscale.sh status
# DOWN일 때만
bash scripts/metro_tailscale.sh start
bash scripts/metro_tailscale.sh status
```

규칙:

- `:8081`이 이미 살아 있으면 kill하지 않는다.
- 에이전트는 세션마다 `lsof -ti:8081 | xargs kill`을 하지 않는다.
- 캐시 클리어가 필요할 때만 `METRO_CLEAR=1 bash scripts/metro_tailscale.sh restart`.
- Tailscale 모드면 localhost뿐 아니라 Tailscale IP로 `/status`가 200인지 확인한다.

### 5. 시연 기동 완료 기준 (서버)

| 계층 | 통과 기준 |
| :--- | :--- |
| Pi | `mariadb`, `minchodan-image-server` active |
| LLM | Mac mini `*:11434`, `/api/tags` 200, 모델 상주 |
| FastAPI | `127.0.0.1:8000`(또는 `WS_PORT`) 헬스 성공, demo 전환 후 DB `SELECT 1`·미디어 `/health`·Ollama `/api/tags` |
| Redis | 컨테이너 running (`redis-cli ping` optional) |
| console | `127.0.0.1:5174`(또는 `CONSOLE_PORT`) HTTP 200 |
| Metro | `metro_tailscale.sh status` UP, (Tailscale 모드) TS IP `:8081` 도달 |
| iPhone↔서버 | Tailscale로 FastAPI 도달(단말/서버 담당 확인). 앱 미설치면 통합 스킬로 빌드 |

최종 보고는 계층별로 통과/실패를 나누고, 미기동·외부 담당 작업을 명시한다. 한 계층 성공만으로 시연 전체 성공으로 확대 해석하지 않는다.

---

## 정본과 보안 규칙

| 대상 | 역할 |
| :--- | :--- |
| 루트 `.env` | DB 계정·비밀번호, 미디어 토큰 등 공통 비밀값과 기본 `NETWORK_ENV_FILE` |
| `.env.network.demo` | 내부망의 `DB_HOST`, `DB_PORT`, `IMAGE_SERVER_BASE_URL`, (선택) `COMPOSE_OLLAMA_BASE_URL=http://<Mac mini LAN IP>:11434` |
| `.env.network.test` | Tailscale의 `DB_HOST`, `DB_PORT`, `IMAGE_SERVER_BASE_URL` (`COMPOSE_OLLAMA_BASE_URL`은 보통 생략) |
| `scripts/switch_rpi_network.sh` | 사전검사, Compose 전환, 런타임 검증 정본 |
| `scripts/ollama_demo_keepalive.sh` | Mac mini Ollama LAN 개방·모델 상주 |
| `scripts/metro_tailscale.sh` | Metro 기동·상태·실기기 딥링크 |
| `docker/scripts/db_tailscale_proxy.sh` | macOS Docker에서 Raspberry Pi DB로 연결하는 `socat` 프록시 |

다음 규칙을 항상 지킨다.

1. `.env` 전체 또는 Compose 렌더링 결과 전체를 출력하지 않는다. 필요한 키의 존재 여부와 분류만 확인한다.
2. DB 비밀번호, 미디어 토큰과 실제 IP를 Git 추적 파일에 기록하지 않는다.
3. `.env`, `.env.network.demo`, `.env.network.test`가 Git-ignore 상태인지 확인한다.
4. 기존 사용자 변경을 보존하고, 네트워크 전환 파일만 명시적으로 스테이징한다.
5. `docker compose down -v`, DB DDL, `DROP`, `TRUNCATE`, 볼륨 삭제를 실행하지 않는다.
6. 네트워크 전환에 `docker compose build`를 실행하지 않는다.
7. `tailscale ping` 성공만으로 완료 판정하지 않는다. DB `SELECT 1`, 미디어 `/health`, (LLM을 분리한 프로필이면) Ollama `/api/tags`까지 확인한다.
8. Metro가 살아 있을 때 불필요하게 포트를 kill하지 않는다.

---

## 실행 워크플로우 (네트워크 프로필 전환)

시연이면 위 [시연 전 서버 기동](#시연-전-서버-기동-역할별)을 먼저 맞춘 뒤 진행한다.

### 1. 저장소와 로컬 프로필 확인

저장소 루트에서 다음을 수행한다.

```bash
git status --short
git check-ignore -v .env .env.network.demo .env.network.test
bash -n scripts/switch_rpi_network.sh docker/scripts/db_tailscale_proxy.sh
```

프로필 파일이 없을 때만 생성한다. 공통 비밀값은 복사하지 않고 아래 키만 둔다.

```dotenv
NETWORK_ENV_FILE=../.env.network.<demo-or-test>
DB_HOST=<PROFILE_DB_HOST>
DB_PORT=3306
IMAGE_SERVER_BASE_URL=http://<PROFILE_MEDIA_HOST>:<MEDIA_PORT>
# demo 프로필에서 LLM(Ollama)을 Mac mini로 분리했을 때만 추가(선택)
COMPOSE_OLLAMA_BASE_URL=http://<MAC_MINI_LAN_IP>:11434
```

주소는 사용자 지시 또는 기존 로컬 프로필에서 가져온다. 루트 `.env`의 기본 프로필을 변경해 달라는 요청이 있으면 중복 키를 확인하고 `NETWORK_ENV_FILE` 한 줄만 최소 수정한다. `COMPOSE_OLLAMA_BASE_URL`을 생략하면 기존처럼 동일 호스트 Ollama(`host.docker.internal:11434`)를 그대로 사용한다.

### 2. Raspberry Pi 도달성과 서비스 상태 확인

SSH 별칭을 사용하고 비밀 환경 파일의 전체 내용을 출력하지 않는다.

```bash
ssh minchodan-rpi-db 'hostname; systemctl is-active mariadb minchodan-image-server tailscaled'
ssh minchodan-rpi-db 'sudo ss -lntup | awk '\''NR==1 || /:22 |:3306 |:8081 /'\''; sudo ufw status'
tailscale ping -c 1 minchodan-rpi-db
```

정상 기준은 MariaDB·미디어 API·Tailscale이 `active`이고, MariaDB와 미디어 API가 필요한 두 인터페이스에서 접근 가능하며, UFW가 내부망 대역과 `tailscale0`의 서비스 포트만 허용하는 상태다. inactive면 [시연 전 서버 기동 §1](#1-raspberry-pi-mariadb미디어)을 적용한다.

### 3. 변경 전 사전검사

```bash
MINCHODAN_SWITCH_CHECK_ONLY=1 bash scripts/switch_rpi_network.sh demo
MINCHODAN_SWITCH_CHECK_ONLY=1 bash scripts/switch_rpi_network.sh test
```

선택한 프로필의 사전검사가 실패하면 컨테이너를 재생성하지 말고 실패 계층부터 고친다.

| 실패 메시지 | 우선 확인 |
| :--- | :--- |
| `DB TCP preflight failed` | 프로필 주소, MariaDB listen, UFW, Tailscale 상태 |
| `media health preflight failed` | 미디어 서비스, `0.0.0.0` 바인딩, UFW, `/health` |
| `Ollama LAN preflight failed` | Mac mini `OLLAMA_HOST=0.0.0.0` 바인딩, 방화벽 `11434/tcp`, 서버-Mac mini LAN |
| 시연 중 LLM만 간헐적으로 수 초 지연 | Mac mini에서 `bash scripts/ollama_demo_keepalive.sh` 미실행(콜드 로드) |
| `socat not installed` | macOS에서 `brew install socat` |
| `FastAPI health timeout` | 컨테이너 로그와 컨테이너 내부 `/health`; 호스트 포트 충돌을 분리 확인 |

### 4. 선택 프로필 적용

```bash
bash scripts/switch_rpi_network.sh <demo|test>
```

스크립트가 다음 작업을 수행하도록 유지한다.

1. DB TCP, 미디어 `/health`, (프로필에 `COMPOSE_OLLAMA_BASE_URL`이 있으면) Ollama `/api/tags` 사전검사
2. Linux 또는 macOS Compose 선택과 구성 검증
3. macOS `socat` 프록시의 DB 목적지 교체
4. `--no-build --no-deps --force-recreate fastapi`로 FastAPI만 재생성(`COMPOSE_OLLAMA_BASE_URL`이 있으면 `OLLAMA_BASE_URL`도 함께 갱신됨)
5. 컨테이너 내부 FastAPI `/health` 확인
6. 원격 DB `SELECT 1`과 미디어 `/health` 확인

### 5. 무빌드·무손실 증거 확인

필요하면 전환 전후에 다음 비식별 증거를 비교한다.

```bash
docker image inspect --format '{{.Id}}' minchodan-server:latest
docker inspect --format '{{.Name}} {{.Id}} {{.Image}}' minchodan-mariadb minchodan-redis minchodan-fastapi
docker compose --env-file .env -f docker/docker-compose.macos.yml config --quiet
docker compose --env-file .env -f docker/docker-compose.yml config --quiet
```

정상 전환은 이미지 ID가 동일하고 MariaDB·Redis 컨테이너 ID가 유지되며, FastAPI 환경만 선택 프로필로 바뀐 상태다.

---

## Raspberry Pi 설정 복구 가드레일

Pi 설정이 이미 정상이라면 재적용하지 않는다. 드리프트가 확인되고 사용자가 설정 또는 복구까지 요청한 경우에만 다음 순서를 지킨다.

1. `/etc/minchodan-image-server.env`를 타임스탬프가 포함된 별도 파일로 백업한다.
2. 미디어 API를 특정 인터페이스 하나가 아닌 `0.0.0.0`에 바인딩한다.
3. UFW를 바꾸기 전에 현재 SSH 세션을 유지하고 `tailscale0` SSH 및 내부망 SSH 허용 규칙을 먼저 추가한다.
4. MariaDB와 미디어 포트는 내부망 대역과 `tailscale0`만 허용한다.
5. 새 SSH 세션, DB TCP, 미디어 HTTP를 모두 확인한 뒤 중복된 광역 허용 규칙을 제거한다.
6. 서비스 실패 시 백업 파일로 복원하고 원래 서비스를 재시작한다.

내부망 주소가 DHCP라면 공유기 DHCP 예약은 라즈베리파이 내부 명령으로 해결할 수 없음을 보고한다.

---

## 완료 기준과 보고

| 검증 | 통과 기준 |
| :--- | :--- |
| 서버 기동 | [시연 기동 완료 기준](#5-시연-기동-완료-기준-서버) 표 충족(요청 범위에 해당하는 계층) |
| 프로필 | `demo`, `test` check-only 모두 통과(전환 작업 시) |
| DB | 선택 프로필에서 `SELECT 1=True` |
| 미디어 | 선택 프로필에서 `/health` HTTP 200 |
| LLM(Mac mini, demo) | `/api/tags` 정상 + keepalive 상주 |
| Docker | 전환 시 기존 이미지 재사용, MariaDB·Redis 보존 |
| console / Metro | 시연 요청 시 `:5174` / Metro UP |
| 보안 | 프로필·비밀값 Git-ignore, UFW 최소 허용 |
| 원격 관리 | 새 `ssh minchodan-rpi-db` 세션 성공 |

최종 보고에는 활성 프로필, 기동한 서버 계층, 실제 검증 결과, 이미지 재사용 여부, Pi 설정 변경과 백업 경로, 남은 외부 작업(예: 실기기 앱 설치)을 구분한다.
