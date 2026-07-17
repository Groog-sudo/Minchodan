#!/usr/bin/env bash
# iOS 실기기 + Docker(FastAPI/Redis/MariaDB) + DB(Tailscale/로컬) 통합 테스트 랩.
# 사용: bash scripts/dev_ios_lab.sh start|stop|status|logs|ios|health

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.macos.yml"
SESSION_ROOT="$PROJECT_ROOT/logs/dev-session"
PID_DIR="$SESSION_ROOT/.pids"
LATEST_LINK="$SESSION_ROOT/latest"

usage() {
  cat <<'EOF'
Usage: bash scripts/dev_ios_lab.sh <command>

Commands:
  start    Docker 스택 + DB 프록시 + 로그 수집기 기동
  stop     백그라운드 수집기/프록시 중지 (Docker는 유지)
  down     Docker compose down + stop
  status   헬스·포트·세션 manifest 출력
  logs     latest 세션 로그 tail (fastapi 기본)
  ios      Expo Metro + iOS 실기기 빌드/설치 (LAN WS URL 주입)
  health   /health 및 Redis/MariaDB/Ollama 점검

환경 변수 (선택):
  MINCHODAN_LAB_NETWORK_MODE   lan | tailscale (기본: lan)
  MINCHODAN_LAB_WIFI_HOST      LAN IP (미설정 시 en0/en1 자동)
  MINCHODAN_LAB_DEVICE_UDID    iOS 실기기 UDID (미설정 시 devicectl 자동)
EOF
}

detect_lan_ip() {
  ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true
}

read_env_val() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true
}

ensure_session() {
  mkdir -p "$SESSION_ROOT" "$PID_DIR"
  if [[ ! -L "$LATEST_LINK" ]] || [[ ! -d "$LATEST_LINK" ]]; then
    local ts
    ts="$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$SESSION_ROOT/$ts"
    ln -sfn "$ts" "$LATEST_LINK"
  fi
}

session_dir() {
  ensure_session
  echo "$SESSION_ROOT/$(readlink "$LATEST_LINK")"
}

write_manifest() {
  local dir
  dir="$(session_dir)"
  local lan_ip wifi_host network_mode ws_port db_host
  lan_ip="$(detect_lan_ip)"
  network_mode="${MINCHODAN_LAB_NETWORK_MODE:-lan}"
  wifi_host="${MINCHODAN_LAB_WIFI_HOST:-${lan_ip:-unknown}}"
  ws_port="$(read_env_val WS_PORT)"
  ws_port="${ws_port:-8000}"
  db_host="$(read_env_val DB_HOST)"

  cat >"$dir/manifest.json" <<EOF
{
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_root": "$PROJECT_ROOT",
  "lan_ip": "${lan_ip}",
  "wifi_host": "${wifi_host}",
  "network_mode": "${network_mode}",
  "ws_port": ${ws_port},
  "ws_url_lan": "ws://${wifi_host}:${ws_port}/ws/detect",
  "db_host": "${db_host}",
  "compose_file": "$COMPOSE_FILE",
  "logs": {
    "docker_fastapi": "$dir/docker-fastapi.log",
    "docker_all": "$dir/docker-all.log",
    "ollama": "$dir/ollama.log",
    "expo": "$dir/expo-metro.log",
    "ios_build": "$dir/ios-build.log"
  }
}
EOF
  echo "[lab] manifest: $dir/manifest.json"
}

start_log_collectors() {
  local dir
  dir="$(session_dir)"
  local pf="$PID_DIR/log_fastapi.pid"
  if [[ -f "$pf" ]] && kill -0 "$(cat "$pf")" 2>/dev/null; then
    echo "[lab] log collector already running (pid=$(cat "$pf"))"
    return 0
  fi
  (
    cd "$PROJECT_ROOT"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f --no-color fastapi
  ) >>"$dir/docker-fastapi.log" 2>&1 &
  echo $! >"$pf"
  echo "[lab] docker fastapi logs -> $dir/docker-fastapi.log (pid=$(cat "$pf"))"
}

stop_log_collectors() {
  local pf="$PID_DIR/log_fastapi.pid"
  if [[ -f "$pf" ]]; then
    kill "$(cat "$pf")" 2>/dev/null || true
    rm -f "$pf"
  fi
}

cmd_start() {
  cd "$PROJECT_ROOT"
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "[lab] ERROR: .env missing. cp .env.example .env"
    exit 1
  fi

  local ts dir
  ts="$(date +%Y%m%d_%H%M%S)"
  dir="$SESSION_ROOT/$ts"
  mkdir -p "$dir"
  ln -sfn "$ts" "$LATEST_LINK"

  if ! docker info >/dev/null 2>&1; then
    echo "[lab] Docker not running. Starting Docker Desktop..."
    open -a Docker
    for _ in $(seq 1 30); do
      docker info >/dev/null 2>&1 && break
      sleep 2
    done
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "[lab] ERROR: Docker daemon unavailable"
    exit 1
  fi

  echo "[lab] starting Docker stack (macOS compose)..."
  MINCHODAN_OPEN_BROWSER=0 bash "$PROJECT_ROOT/docker/macos_docker_start.sh" \
    >"$dir/docker-startup.log" 2>&1 || {
    echo "[lab] docker start failed. see $dir/docker-startup.log"
    tail -30 "$dir/docker-startup.log"
    exit 1
  }

  write_manifest
  start_log_collectors

  echo "[lab] snapshot container status"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps \
    >"$dir/docker-ps.txt" 2>&1 || true

  cmd_health | tee "$dir/health-check.txt"
  echo "[lab] start complete. run: bash scripts/dev_ios_lab.sh ios"
}

cmd_stop() {
  stop_log_collectors
  if [[ -x "$PROJECT_ROOT/docker/scripts/db_tailscale_proxy.sh" ]]; then
    local pid_file="$PROJECT_ROOT/.db_tailscale_proxy.pid"
    if [[ -f "$pid_file" ]]; then
      kill "$(cat "$pid_file")" 2>/dev/null || true
      rm -f "$pid_file"
      echo "[lab] db tailscale proxy stopped"
    fi
  fi
  echo "[lab] log collectors stopped (docker still running)"
}

cmd_down() {
  cmd_stop
  cd "$PROJECT_ROOT"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
  echo "[lab] docker compose down"
}

cmd_status() {
  ensure_session
  local dir
  dir="$(session_dir)"
  echo "=== Minchodan iOS Lab Status ==="
  echo "session: $dir"
  if [[ -f "$dir/manifest.json" ]]; then
    cat "$dir/manifest.json"
  fi
  echo "--- docker ps ---"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps 2>/dev/null || docker ps --filter name=minchodan
  echo "--- devices ---"
  xcrun devicectl list devices 2>/dev/null | head -8 || true
}

cmd_logs() {
  local dir target
  dir="$(session_dir)"
  target="${1:-fastapi}"
  case "$target" in
    fastapi) tail -n 80 -f "$dir/docker-fastapi.log" ;;
    expo) tail -n 80 -f "$dir/expo-metro.log" ;;
    ios) tail -n 80 -f "$dir/ios-build.log" ;;
    all) tail -n 80 -f "$dir/docker-all.log" ;;
    *) echo "unknown log: $target"; exit 1 ;;
  esac
}

cmd_health() {
  local ws_port health_code
  ws_port="$(read_env_val WS_PORT)"
  ws_port="${ws_port:-8000}"
  health_code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${ws_port}/health" 2>/dev/null || echo "000")"
  echo "FastAPI /health: HTTP $health_code (port $ws_port)"
  redis-cli -h 127.0.0.1 ping 2>/dev/null || echo "Redis: ping skipped (redis-cli 없음 또는 미기동)"
  curl -s -o /dev/null -w "Ollama tags: HTTP %{http_code}\n" http://127.0.0.1:11434/api/tags 2>/dev/null || echo "Ollama: unavailable"
  local gemma
  gemma="$(read_env_val GEMMA_MODEL)"
  if [[ -n "$gemma" ]] && command -v ollama >/dev/null 2>&1; then
    if ollama list 2>/dev/null | grep -q "${gemma%%:*}"; then
      echo "Ollama model: $gemma (present or partial match)"
    else
      echo "WARN: GEMMA_MODEL=$gemma not in ollama list. run: ollama pull $gemma"
    fi
  fi
}

cmd_ios() {
  cd "$PROJECT_ROOT"
  ensure_session
  local dir lan_ip wifi_host network_mode ws_port device_udid
  dir="$(session_dir)"
  lan_ip="$(detect_lan_ip)"
  network_mode="${MINCHODAN_LAB_NETWORK_MODE:-lan}"
  wifi_host="${MINCHODAN_LAB_WIFI_HOST:-${lan_ip:-127.0.0.1}}"
  ws_port="$(read_env_val WS_PORT)"
  ws_port="${ws_port:-8000}"
  device_udid="${MINCHODAN_LAB_DEVICE_UDID:-}"

  if [[ -z "$device_udid" ]]; then
    device_udid="$(xcrun devicectl list devices 2>/dev/null | awk '/iPhone/ && /available/ {print $3; exit}')"
  fi

  export EXPO_PUBLIC_NETWORK_MODE="$network_mode"
  export EXPO_PUBLIC_SERVER_PORT="$ws_port"
  export EXPO_PUBLIC_WIFI_HOST="$wifi_host"
  export EXPO_PUBLIC_LAN_IP="$wifi_host"
  export EXPO_PUBLIC_DEVICE_ID="${EXPO_PUBLIC_DEVICE_ID:-dev-001}"
  export EXPO_PUBLIC_DEVICE_TOKEN="${EXPO_PUBLIC_DEVICE_TOKEN:-token-abc-001}"

  echo "[lab] iOS build env:"
  echo "  NETWORK_MODE=$EXPO_PUBLIC_NETWORK_MODE"
  echo "  WIFI_HOST=$EXPO_PUBLIC_WIFI_HOST"
  echo "  WS_URL=ws://${wifi_host}:${ws_port}/ws/detect"
  echo "  DEVICE_UDID=${device_udid:-auto}"

  if [[ ! -d "$PROJECT_ROOT/client/node_modules" ]]; then
    echo "[lab] npm install in client/"
    (cd "$PROJECT_ROOT/client" && npm install) >>"$dir/expo-metro.log" 2>&1
  fi

  if [[ ! -d "$PROJECT_ROOT/client/ios/Pods" ]]; then
    echo "[lab] pod install"
    (cd "$PROJECT_ROOT/client/ios" && pod install) >>"$dir/ios-build.log" 2>&1
  fi

  echo "[lab] starting Metro (background)..."
  (
    cd "$PROJECT_ROOT/client"
    npx expo start --lan --port 8081
  ) >>"$dir/expo-metro.log" 2>&1 &
  echo $! >"$PID_DIR/expo_metro.pid"
  sleep 4

  echo "[lab] expo run:ios --device (see $dir/ios-build.log)"
  (
    cd "$PROJECT_ROOT/client"
    if [[ -n "$device_udid" ]]; then
      npx expo run:ios --device "$device_udid"
    else
      npx expo run:ios --device
    fi
  ) >>"$dir/ios-build.log" 2>&1 &
  echo $! >"$PID_DIR/ios_build.pid"
  echo "[lab] ios build pid=$(cat "$PID_DIR/ios_build.pid")"
  echo "[lab] tail logs: bash scripts/dev_ios_lab.sh logs ios"
}

main() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    down) cmd_down ;;
    status) cmd_status ;;
    logs) cmd_logs "${1:-fastapi}" ;;
    ios) cmd_ios ;;
    health) cmd_health ;;
    ""|-h|--help|help) usage ;;
    *) echo "unknown command: $cmd"; usage; exit 1 ;;
  esac
}

main "$@"
