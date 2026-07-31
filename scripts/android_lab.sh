#!/usr/bin/env bash
# Android 실기기 통합 테스트 환경 오케스트레이터 (2026-07-29).
#
# 목적:
# - iOS 전용이던 통합 테스트 기동 경로(metro_tailscale.sh launch = devicectl)를
#   Android(adb) 쪽으로 대칭 구현한다.
# - Docker 스택(FastAPI/Redis/MariaDB/console) + Tailscale + Metro + adb 무선 디버깅 +
#   Dev Client 딥링크 실행 + 로그 수집을 한 진입점에서 처리한다.
#
# 사용:
#   bash scripts/android_lab.sh doctor              # 선행 의존성 점검
#   bash scripts/android_lab.sh pair <ip:port> <코드>  # 무선 디버깅 최초 페어링
#   bash scripts/android_lab.sh connect [ip:port]   # adb 연결(미지정 시 mDNS 자동 탐색)
#   bash scripts/android_lab.sh up                  # docker + metro + adb + 앱 실행 일괄
#   bash scripts/android_lab.sh launch              # Dev Client 딥링크 재실행(force-stop 선행)
#   bash scripts/android_lab.sh status              # 전 계층 상태 요약
#   bash scripts/android_lab.sh logs [초]           # logcat/fastapi/metro 세션 로그 수집
#   bash scripts/android_lab.sh down                # 컨테이너 정지(볼륨 보존) + Metro 정지
#
# 환경변수(선택):
#   ANDROID_SERIAL=100.x.x.x:PORT   # 대상 단말 지정(다중 transport 시 필수)
#   ANDROID_PACKAGE=com.minchodan.app
#   METRO_PORT=8081
#   COMPOSE_FILE=docker/docker-compose.macos.yml
#   NETWORK_ENV_FILE=.env.network.local
#   LAB_HOST=lan|tailscale                # 딥링크/서버 주소 기준 (기본 client/.env 추종)
#
# 주의:
# - `docker compose down -v` 는 절대 실행하지 않는다(로컬 MariaDB/Redis 볼륨 소실).
# - `.env` 전체를 출력하지 않는다. 필요한 키만 골라 확인한다.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLIENT_ENV="$PROJECT_ROOT/client/.env"
COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose.macos.yml}"
NETWORK_ENV_FILE="${NETWORK_ENV_FILE:-.env.network.local}"
PACKAGE="${ANDROID_PACKAGE:-com.minchodan.app}"
SCHEME="${METRO_SCHEME:-minchodan}"
METRO_PORT="${METRO_PORT:-8081}"
WS_PORT="${WS_PORT:-8000}"
CONSOLE_PORT="${CONSOLE_PORT:-5174}"
LOG_ROOT="$PROJECT_ROOT/logs/android_sessions"

# adb/tailscale 은 PATH에 없을 수 있어(Android Studio 기본 설치) 후보 경로를 순회한다.
resolve_bin() {
  local name="$1"
  shift
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    return 0
  fi
  local cand
  for cand in "$@"; do
    if [[ -x "$cand" ]]; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

ADB="$(resolve_bin adb \
  "$HOME/Library/Android/sdk/platform-tools/adb" \
  "/opt/homebrew/bin/adb" \
  "/usr/local/bin/adb" || true)"
TS="$(resolve_bin tailscale \
  "/Applications/Tailscale.app/Contents/MacOS/Tailscale" \
  "/usr/local/bin/tailscale" || true)"

require_adb() {
  if [[ -z "${ADB:-}" ]]; then
    echo "ERROR: adb 를 찾지 못했습니다. Android SDK platform-tools 설치 후 재시도하세요." >&2
    exit 1
  fi
}

env_value() {
  # client/.env 의 공개(EXPO_PUBLIC_*) 값만 읽는다. 비밀값 조회에 쓰지 않는다.
  local key="$1"
  [[ -f "$CLIENT_ENV" ]] || return 0
  grep -m1 "^${key}=" "$CLIENT_ENV" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true
}

host_ip() {
  # 딥링크/서버 접속에 쓸 호스트 주소. client/.env 의 NETWORK_MODE 를 기본 추종한다.
  local mode="${LAB_HOST:-$(env_value EXPO_PUBLIC_NETWORK_MODE)}"
  if [[ "$mode" == "tailscale" ]]; then
    if [[ -n "${TS:-}" ]]; then
      "$TS" ip -4 2>/dev/null | head -1
      return
    fi
    env_value EXPO_PUBLIC_TAILSCALE_HOST
    return
  fi
  local lan
  lan="$(env_value EXPO_PUBLIC_LAN_IP)"
  if [[ -z "$lan" ]]; then
    lan="$(primary_lan_ip)"
  fi
  echo "$lan"
}

# 기본 경로 인터페이스의 IPv4. Mac mini/노트북에 따라 en0/en1 이 갈리므로 route 로 판별한다.
primary_lan_ip() {
  local iface
  iface="$(route -n get default 2>/dev/null | awk '/interface:/ {print $2; exit}')"
  if [[ -n "$iface" ]]; then
    ipconfig getifaddr "$iface" 2>/dev/null || true
  fi
}

# 단말 지정. ANDROID_SERIAL 이 없으면 device 상태인 첫 transport 를 쓴다.
device_serial() {
  if [[ -n "${ANDROID_SERIAL:-}" ]]; then
    echo "$ANDROID_SERIAL"
    return
  fi
  "$ADB" devices 2>/dev/null | awk '$2=="device" {print $1; exit}'
}

adb_dev() {
  local serial
  serial="$(device_serial)"
  if [[ -z "$serial" ]]; then
    echo "ERROR: 연결된 Android 단말이 없습니다. 'connect' 를 먼저 실행하세요." >&2
    exit 1
  fi
  "$ADB" -s "$serial" "$@"
}

http_code() {
  curl -sf -o /dev/null -w "%{http_code}" --max-time 4 "$1" 2>/dev/null || echo "000"
}

# ---------------------------------------------------------------- doctor

cmd_doctor() {
  echo "== 선행 의존성 =="
  printf "adb        : %s\n" "${ADB:-미설치}"
  printf "tailscale  : %s\n" "${TS:-미설치}"
  printf "docker     : %s\n" "$(docker compose version 2>/dev/null | head -1 || echo '미기동/미설치')"
  printf "node       : %s\n" "$(node -v 2>/dev/null || echo '미설치')"
  echo
  echo "== 네트워크 프로필 (client/.env, 공개 변수만) =="
  printf "NETWORK_MODE=%s\n" "$(env_value EXPO_PUBLIC_NETWORK_MODE)"
  printf "LAN_IP=%s TAILSCALE_HOST=%s SERVER_PORT=%s\n" \
    "$(env_value EXPO_PUBLIC_LAN_IP)" \
    "$(env_value EXPO_PUBLIC_TAILSCALE_HOST)" \
    "$(env_value EXPO_PUBLIC_SERVER_PORT)"
  printf "선택된 호스트 주소: %s\n" "$(host_ip)"
  # LAN 모드에서 가장 흔한 함정: 다른 장소로 이동해 호스트 IP가 바뀌었는데 client/.env 가 그대로다.
  # 이 경우 단말은 옛 주소로 붙으려다 흰 화면/WS 연결 실패로 끝난다.
  local env_lan cur_lan
  env_lan="$(env_value EXPO_PUBLIC_LAN_IP)"
  cur_lan="$(primary_lan_ip)"
  if [[ -n "$cur_lan" && -n "$env_lan" && "$env_lan" != "$cur_lan" ]]; then
    echo "WARN: client/.env 의 LAN_IP(${env_lan}) 와 현재 호스트 IP(${cur_lan}) 가 다릅니다."
    echo "      같은 WiFi 테스트라면 .env 를 ${cur_lan} 로 갱신하고, 단말이 외부망이면 LAB_HOST=tailscale 을 쓰세요."
  fi
  echo
  if [[ -n "${TS:-}" ]]; then
    echo "== Tailscale =="
    # tailscale 이 정지 상태면 비정상 종료 코드를 반환한다. 점검 명령이므로 삼키고 계속한다.
    { "$TS" status 2>&1 || true; } | head -10
  fi
}

# ------------------------------------------------------- adb 무선 디버깅

# 무선 디버깅 페어링/접속 포트는 화면을 닫거나 재부팅하면 회전한다.
# 사용자가 읽어준 포트가 이미 만료된 경우가 잦아 mDNS 실측을 우선한다.
mdns_port() {
  local kind="$1" # pairing | connect
  local svc
  case "$kind" in
    pairing) svc="adb-tls-pairing" ;;
    connect) svc="adb-tls-connect" ;;
    *) return 1 ;;
  esac
  "$ADB" mdns services 2>/dev/null | awk -v s="$svc" '$2 ~ s {print $3; exit}'
}

cmd_pair() {
  require_adb
  local target="${1:-}"
  local code="${2:-}"
  if [[ -z "$code" ]]; then
    echo "Usage: bash scripts/android_lab.sh pair <ip:port> <6자리 코드>" >&2
    echo "  단말: 개발자 옵션 > 무선 디버깅 > 페어링 코드로 기기 페어링" >&2
    exit 1
  fi
  "$ADB" start-server >/dev/null 2>&1 || true
  if ! "$ADB" pair "$target" "$code"; then
    echo "[pair] 실패 - 포트 회전 가능성. mDNS 로 재탐색합니다."
    local live
    live="$(mdns_port pairing || true)"
    if [[ -z "$live" ]]; then
      echo "ERROR: mDNS 에서 adb-tls-pairing 서비스를 찾지 못했습니다." >&2
      echo "  단말의 '페어링 코드로 기기 페어링' 다이얼로그를 연 상태로 다시 시도하세요." >&2
      exit 1
    fi
    echo "[pair] mDNS 실측 대상: $live"
    "$ADB" pair "$live" "$code"
  fi
  cmd_connect
}

cmd_connect() {
  require_adb
  "$ADB" start-server >/dev/null 2>&1 || true
  local target="${1:-${ANDROID_SERIAL:-}}"
  if [[ -z "$target" ]]; then
    target="$(mdns_port connect || true)"
  fi
  if [[ -z "$target" ]]; then
    echo "ERROR: 접속 대상을 찾지 못했습니다." >&2
    echo "  단말 무선 디버깅 화면의 'IP 주소 및 포트' 를 인자로 넘기거나 ANDROID_SERIAL 을 지정하세요." >&2
    "$ADB" mdns services 2>/dev/null || true
    # up 흐름에서 호출될 수 있으므로 exit 대신 return 으로 물러난다(나머지 계층은 계속 기동).
    return 1
  fi
  echo "[adb] connect $target"
  "$ADB" connect "$target" || true
  # mDNS 자동 등록 transport 와 수동 connect transport 가 중복되면 -s 없이는 명령이 실패한다.
  local count
  count="$("$ADB" devices | awk '$2=="device"' | wc -l | tr -d ' ')"
  if [[ "$count" -gt 1 ]]; then
    echo "[adb] WARN: transport ${count}개 감지 - ANDROID_SERIAL=${target} 로 고정 사용을 권장합니다."
  fi
  "$ADB" devices
}

# ------------------------------------------------------------ docker/metro

compose() {
  local args=(--env-file "$PROJECT_ROOT/.env")
  if [[ -f "$PROJECT_ROOT/$NETWORK_ENV_FILE" ]]; then
    args+=(--env-file "$PROJECT_ROOT/$NETWORK_ENV_FILE")
  fi
  (cd "$PROJECT_ROOT" && docker compose "${args[@]}" -f "$COMPOSE_FILE" "$@")
}

cmd_docker_up() {
  if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker 데몬이 꺼져 있습니다. Docker Desktop 을 먼저 실행하세요." >&2
    exit 1
  fi
  echo "[docker] up -d ($COMPOSE_FILE)"
  compose up -d
  local i
  for i in $(seq 1 30); do
    if [[ "$(http_code "http://127.0.0.1:${WS_PORT}/")" != "000" ]]; then
      echo "[docker] fastapi ready (try=${i})"
      break
    fi
    sleep 2
  done
  compose ps
}

cmd_metro_up() {
  # Metro 는 단일 인스턴스 정책(metro_tailscale.sh)을 그대로 재사용한다.
  # Android LAN 모드에서도 packager hostname 만 다를 뿐 기동 절차는 동일하다.
  local host
  host="$(host_ip)"
  if [[ -z "$host" ]]; then
    echo "ERROR: 호스트 주소를 확정하지 못했습니다(client/.env 확인)." >&2
    exit 1
  fi
  REACT_NATIVE_PACKAGER_HOSTNAME="$host" METRO_PORT="$METRO_PORT" \
    bash "$PROJECT_ROOT/scripts/metro_tailscale.sh" start
}

# --------------------------------------------------------------- 앱 실행

deeplink_url() {
  local host
  host="$(host_ip)"
  local encoded
  encoded="$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" \
    "http://${host}:${METRO_PORT}")"
  echo "${SCHEME}://expo-development-client/?url=${encoded}"
}

cmd_launch() {
  require_adb
  local url
  url="$(deeplink_url)"
  echo "[app] force-stop $PACKAGE"
  # MIUI/HyperOS 는 프로세스를 남긴 채 재진입하면 camera-is-restricted 로 카메라를 막는다.
  # Fast Refresh 후 재실행 시에도 반드시 force-stop 을 선행한다.
  adb_dev shell am force-stop "$PACKAGE" || true
  sleep 1
  echo "[app] launch $url"
  adb_dev shell am start -a android.intent.action.VIEW -d "$url" >/dev/null
  echo "[app] 실행 요청 완료 (단말 잠금 해제 상태여야 카메라 권한 흐름이 진행됩니다)"
}

# ----------------------------------------------------------------- status

cmd_status() {
  local host
  host="$(host_ip)"
  echo "== 호스트 =="
  printf "network_mode=%s host=%s\n" "${LAB_HOST:-$(env_value EXPO_PUBLIC_NETWORK_MODE)}" "$host"
  echo
  echo "== 서비스 =="
  printf "fastapi  127.0.0.1:%s -> %s\n" "$WS_PORT" "$(http_code "http://127.0.0.1:${WS_PORT}/")"
  printf "console  127.0.0.1:%s -> %s\n" "$CONSOLE_PORT" "$(http_code "http://127.0.0.1:${CONSOLE_PORT}/")"
  printf "metro    127.0.0.1:%s -> %s\n" "$METRO_PORT" "$(http_code "http://127.0.0.1:${METRO_PORT}/status")"
  if [[ -n "$host" ]]; then
    printf "fastapi  %s:%s -> %s (단말 관점)\n" "$host" "$WS_PORT" "$(http_code "http://${host}:${WS_PORT}/")"
    printf "metro    %s:%s -> %s (단말 관점)\n" "$host" "$METRO_PORT" "$(http_code "http://${host}:${METRO_PORT}/status")"
  fi
  echo
  if docker info >/dev/null 2>&1; then
    echo "== 컨테이너 =="
    compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}" 2>/dev/null || compose ps
    echo
  fi
  if [[ -n "${ADB:-}" ]]; then
    echo "== 단말 =="
    "$ADB" devices
    local serial
    serial="$(device_serial)"
    if [[ -n "$serial" ]]; then
      printf "model=%s android=%s\n" \
        "$("$ADB" -s "$serial" shell getprop ro.product.model 2>/dev/null | tr -d '\r')" \
        "$("$ADB" -s "$serial" shell getprop ro.build.version.release 2>/dev/null | tr -d '\r')"
      local pid
      pid="$("$ADB" -s "$serial" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r')"
      printf "%s pid=%s\n" "$PACKAGE" "${pid:-없음(미실행)}"
    fi
  fi
}

# ------------------------------------------------------------------- logs

cmd_logs() {
  require_adb
  local duration="${1:-60}"
  local session_dir="$LOG_ROOT/$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$session_dir"
  echo "[logs] ${duration}초 수집 -> $session_dir"

  adb_dev logcat -c || true
  adb_dev logcat -v time >"$session_dir/logcat.log" 2>&1 &
  local logcat_pid=$!
  # --tail 0 필수: 없으면 컨테이너 기동 이후 전체 로그를 재생해, 수집 구간 통계를 누적치로 오염시킨다
  # (2026-07-29 실측: 30초 수집인데 detection 수신이 1547건으로 집계됨).
  compose logs -f --no-color --tail 0 fastapi >"$session_dir/fastapi.log" 2>&1 &
  local docker_pid=$!

  sleep "$duration"
  kill "$logcat_pid" "$docker_pid" 2>/dev/null || true
  wait "$logcat_pid" "$docker_pid" 2>/dev/null || true

  if [[ -f "$PROJECT_ROOT/logs/metro/metro.log" ]]; then
    tail -500 "$PROJECT_ROOT/logs/metro/metro.log" >"$session_dir/metro_tail.log" || true
  fi
  echo "[logs] 수집 완료"
  wc -l "$session_dir"/*.log 2>/dev/null || true
}

# --------------------------------------------------------------- up / down

cmd_up() {
  cmd_docker_up
  cmd_metro_up
  if [[ -n "${ADB:-}" ]]; then
    if [[ -z "$(device_serial)" ]]; then
      echo "[adb] 연결된 단말 없음 - mDNS 자동 접속 시도"
      cmd_connect || true
    fi
    if [[ -n "$(device_serial)" ]]; then
      cmd_launch
    else
      echo "[adb] 단말 미연결 - 'pair' 또는 'connect' 를 수동 실행하세요."
    fi
  fi
  echo
  cmd_status
}

cmd_down() {
  bash "$PROJECT_ROOT/scripts/metro_tailscale.sh" stop || true
  if docker info >/dev/null 2>&1; then
    # 볼륨 보존. down -v 는 금지(스킬 가드레일).
    compose stop
  fi
  if [[ -n "${ADB:-}" && -n "$(device_serial)" ]]; then
    adb_dev shell am force-stop "$PACKAGE" || true
  fi
  echo "[down] 정지 완료 (볼륨/이미지 보존)"
}

usage() {
  cat <<EOF
Usage: bash scripts/android_lab.sh <command>

  doctor              선행 의존성(adb/tailscale/docker/node) 및 네트워크 프로필 점검
  pair <ip:port> <코드>  무선 디버깅 최초 페어링 (포트 만료 시 mDNS 자동 재탐색)
  connect [ip:port]   adb 연결 (미지정 시 mDNS 자동 탐색)
  up                  docker + metro + adb 연결 + Dev Client 실행 일괄
  launch              force-stop 후 Dev Client 딥링크 재실행
  status              호스트/서비스/컨테이너/단말 상태 요약
  logs [초]           logcat + fastapi + metro 로그 수집 (기본 60초)
  down                Metro 정지 + 컨테이너 stop(볼륨 보존) + 앱 force-stop

환경변수: ANDROID_SERIAL, ANDROID_PACKAGE, METRO_PORT, COMPOSE_FILE, LAB_HOST(lan|tailscale)
EOF
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    doctor) cmd_doctor ;;
    pair) cmd_pair "$@" ;;
    connect) cmd_connect "$@" ;;
    up) cmd_up ;;
    launch) cmd_launch ;;
    status) cmd_status ;;
    logs) cmd_logs "$@" ;;
    down) cmd_down ;;
    ""|-h|--help|help) usage ;;
    *) echo "unknown: $cmd" >&2; usage; exit 1 ;;
  esac
}

main "$@"
