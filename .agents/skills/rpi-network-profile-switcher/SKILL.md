---
name: rpi-network-profile-switcher
description: Raspberry Pi의 MariaDB·미디어 API 접속 경로를 시연 내부망(demo)과 Tailscale 테스트망(test) 사이에서 Docker 이미지 재빌드 없이 전환하고 검증한다. Minchodan에서 DB_HOST, IMAGE_SERVER_BASE_URL, .env.network.demo/test, NETWORK_ENV_FILE, ssh minchodan-rpi-db, socat DB 프록시, UFW 또는 양쪽 네트워크 연결을 설정·점검·복구하거나 네트워크 프로필 전환을 자동화할 때 사용한다.
---

# Raspberry Pi 네트워크 프로필 전환

> **작성일**: 2026-07-20
> **버전**: v1.0.1 (2026-07-21 지원 에이전트 매니페스트 존재 명시)
> **관련 문서**: `docs/ops/deployment_guide.md`, `docs/ops/environment_variables.md`, `docs/db_tailscale_guide/README.md`
> **관련 스킬**: 전체 Docker·iOS 실기기 통합 검증은 [`integration-test-orchestrator`](../integration-test-orchestrator/SKILL.md)를 이어서 사용한다.
> **지원 에이전트**: Claude Code 등은 본 `SKILL.md`를 직접 읽어 호출한다. OpenAI Codex 계열은 `agents/openai.yaml`(스킬 인터페이스 정의: `display_name`/`short_description`/`default_prompt`)을 통해 동일 스킬을 먼저 인식·호출한다. 다른 스킬 폴더에는 `agents/` 서브폴더가 없으며, 이는 본 스킬만의 예외다.

---

## 목적과 실행 경계

같은 Raspberry Pi의 MariaDB와 미디어 API를 아래 두 런타임 프로필로 전환한다. 이미지 생성은 네트워크 설정과 분리하고 기존 `minchodan-server:latest`를 재사용한다.

| 프로필 | 접속 경로 | 로컬 설정 파일 | 실행 명령 |
| :--- | :--- | :--- | :--- |
| **`demo`** | 시연 장소 내부망 | `.env.network.demo` | `bash scripts/switch_rpi_network.sh demo` |
| **`test`** | Tailscale 외부망 | `.env.network.test` | `bash scripts/switch_rpi_network.sh test` |

사용자가 상태 확인이나 진단만 요청하면 읽기 전용 검사까지만 수행한다. 설정·전환·복구를 요청한 경우에만 해당 범위의 변경을 수행한다. 커밋·푸시는 별도 요청이 있을 때만 수행한다.

---

## 정본과 보안 규칙

| 대상 | 역할 |
| :--- | :--- |
| 루트 `.env` | DB 계정·비밀번호, 미디어 토큰 등 공통 비밀값과 기본 `NETWORK_ENV_FILE` |
| `.env.network.demo` | 내부망의 `DB_HOST`, `DB_PORT`, `IMAGE_SERVER_BASE_URL` |
| `.env.network.test` | Tailscale의 `DB_HOST`, `DB_PORT`, `IMAGE_SERVER_BASE_URL` |
| `scripts/switch_rpi_network.sh` | 사전검사, Compose 전환, 런타임 검증 정본 |
| `docker/scripts/db_tailscale_proxy.sh` | macOS Docker에서 Raspberry Pi DB로 연결하는 `socat` 프록시 |

다음 규칙을 항상 지킨다.

1. `.env` 전체 또는 Compose 렌더링 결과 전체를 출력하지 않는다. 필요한 키의 존재 여부와 분류만 확인한다.
2. DB 비밀번호, 미디어 토큰과 실제 IP를 Git 추적 파일에 기록하지 않는다.
3. `.env`, `.env.network.demo`, `.env.network.test`가 Git-ignore 상태인지 확인한다.
4. 기존 사용자 변경을 보존하고, 네트워크 전환 파일만 명시적으로 스테이징한다.
5. `docker compose down -v`, DB DDL, `DROP`, `TRUNCATE`, 볼륨 삭제를 실행하지 않는다.
6. 네트워크 전환에 `docker compose build`를 실행하지 않는다.
7. `tailscale ping` 성공만으로 완료 판정하지 않는다. DB `SELECT 1`과 미디어 `/health`까지 확인한다.

---

## 실행 워크플로우

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
```

주소는 사용자 지시 또는 기존 로컬 프로필에서 가져온다. 루트 `.env`의 기본 프로필을 변경해 달라는 요청이 있으면 중복 키를 확인하고 `NETWORK_ENV_FILE` 한 줄만 최소 수정한다.

### 2. Raspberry Pi 도달성과 서비스 상태 확인

SSH 별칭을 사용하고 비밀 환경 파일의 전체 내용을 출력하지 않는다.

```bash
ssh minchodan-rpi-db 'hostname; systemctl is-active mariadb minchodan-image-server tailscaled'
ssh minchodan-rpi-db 'sudo ss -lntup | awk '\''NR==1 || /:22 |:3306 |:8081 /'\''; sudo ufw status'
tailscale ping -c 1 minchodan-rpi-db
```

정상 기준은 MariaDB·미디어 API·Tailscale이 `active`이고, MariaDB와 미디어 API가 필요한 두 인터페이스에서 접근 가능하며, UFW가 내부망 대역과 `tailscale0`의 서비스 포트만 허용하는 상태다.

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
| `socat not installed` | macOS에서 `brew install socat` |
| `FastAPI health timeout` | 컨테이너 로그와 컨테이너 내부 `/health`; 호스트 포트 충돌을 분리 확인 |

### 4. 선택 프로필 적용

```bash
bash scripts/switch_rpi_network.sh <demo|test>
```

스크립트가 다음 작업을 수행하도록 유지한다.

1. DB TCP와 미디어 `/health` 사전검사
2. Linux 또는 macOS Compose 선택과 구성 검증
3. macOS `socat` 프록시의 DB 목적지 교체
4. `--no-build --no-deps --force-recreate fastapi`로 FastAPI만 재생성
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
| 프로필 | `demo`, `test` check-only 모두 통과 |
| DB | 선택 프로필에서 `SELECT 1=True` |
| 미디어 | 선택 프로필에서 `/health` HTTP 200 |
| Docker | 기존 이미지 재사용, MariaDB·Redis 보존 |
| 보안 | 프로필·비밀값 Git-ignore, UFW 최소 허용 |
| 원격 관리 | 새 `ssh minchodan-rpi-db` 세션 성공 |

최종 보고에는 활성 프로필, 실제 검증 결과, 이미지 재사용 여부, Pi 설정 변경과 백업 경로, 남은 외부 작업을 구분한다. 서비스 도달성 검증 없이 전체 통합 성공으로 확대 해석하지 않는다.
