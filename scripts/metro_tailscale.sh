#!/usr/bin/env bash
# Metro(Tailscale) 고정 운영 스크립트.
#
# 목적:
# - Metro를 "한 인스턴스"로만 유지 (이미 떠 있으면 start가 재기동하지 않음)
# - 재기동은 명시적 restart/stop 에서만 kill
# - 앱은 Tailscale 딥링크로만 열어 Bonjour 미검색 문제를 우회
#
# 사용:
#   bash scripts/metro_tailscale.sh start
#   bash scripts/metro_tailscale.sh status
#   bash scripts/metro_tailscale.sh launch          # 실기기 Dev Client 딥링크
#   bash scripts/metro_tailscale.sh restart
#   bash scripts/metro_tailscale.sh stop
#   bash scripts/metro_tailscale.sh url             # 딥링크 문자열만 출력
#
# 환경변수(선택):
#   METRO_PORT=8081
#   METRO_DEVICE_UDID=...
#   METRO_BUNDLE_ID=com.minchodan.app.kb.dev
#   REACT_NATIVE_PACKAGER_HOSTNAME=<Tailscale IPv4>  (미설정 시 tailscale ip -4)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLIENT_DIR="$PROJECT_ROOT/client"
RUN_DIR="$PROJECT_ROOT/logs/metro"
PID_FILE="$RUN_DIR/metro.pid"
LOG_FILE="$RUN_DIR/metro.log"
PORT="${METRO_PORT:-8081}"
BUNDLE_ID="${METRO_BUNDLE_ID:-com.minchodan.app.kb.dev}"
SCHEME="${METRO_SCHEME:-minchodan}"
DEVICE_UDID="${METRO_DEVICE_UDID:-7C12D347-0486-5BC2-B7B7-35C6E715B47C}"

mkdir -p "$RUN_DIR"

ts_ip() {
  if [[ -n "${REACT_NATIVE_PACKAGER_HOSTNAME:-}" ]]; then
    echo "$REACT_NATIVE_PACKAGER_HOSTNAME"
    return
  fi
  if command -v tailscale >/dev/null 2>&1; then
    tailscale ip -4 2>/dev/null | head -1
    return
  fi
  echo ""
}

metro_ok() {
  local host="$1"
  curl -sf -o /dev/null --max-time 2 "http://${host}:${PORT}/status" 2>/dev/null
}

listening_pids() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true
}

deeplink_url() {
  local host
  host="$(ts_ip)"
  if [[ -z "$host" ]]; then
    echo "ERROR: Tailscale IP를 알 수 없습니다. REACT_NATIVE_PACKAGER_HOSTNAME을 설정하세요." >&2
    exit 1
  fi
  local encoded
  encoded="$(python3 -c "import urllib.parse; print(urllib.parse.quote('http://${host}:${PORT}', safe=''))")"
  echo "${SCHEME}://expo-development-client/?url=${encoded}"
}

cmd_status() {
  local host
  host="$(ts_ip)"
  local pids
  pids="$(listening_pids | tr '\n' ' ')"
  echo "port=${PORT}"
  echo "pids=${pids:-none}"
  if metro_ok "127.0.0.1"; then
    echo "localhost: OK"
  else
    echo "localhost: DOWN"
  fi
  if [[ -n "$host" ]]; then
    if metro_ok "$host"; then
      echo "tailscale(${host}): OK"
    else
      echo "tailscale(${host}): DOWN"
    fi
    echo "deeplink: $(deeplink_url)"
  else
    echo "tailscale: UNKNOWN (no IP)"
  fi
}

cmd_start() {
  if metro_ok "127.0.0.1"; then
    echo "[metro] already running on :${PORT} (skip start)"
    cmd_status
    return 0
  fi

  local host
  host="$(ts_ip)"
  if [[ -z "$host" ]]; then
    echo "ERROR: Tailscale IP 없음. REACT_NATIVE_PACKAGER_HOSTNAME을 지정하세요." >&2
    exit 1
  fi

  echo "[metro] starting (host=lan packager=${host} port=${PORT})"
  (
    cd "$CLIENT_DIR"
    export REACT_NATIVE_PACKAGER_HOSTNAME="$host"
    unset CI
    # macOS: setsid 없음. nohup으로 터미널/에이전트 세션과 분리.
    exec nohup npx expo start --host lan --port "$PORT" --scheme "$SCHEME"
  ) >>"$LOG_FILE" 2>&1 &
  local wrap_pid=$!
  echo "$wrap_pid" >"$PID_FILE"
  disown "$wrap_pid" 2>/dev/null || true

  local i code
  for i in $(seq 1 40); do
    if metro_ok "127.0.0.1"; then
      # 실제 LISTEN PID로 pid 파일 갱신 (래퍼 셸이 죽은 뒤에도 추적 가능)
      listening_pids | head -1 >"$PID_FILE" || true
      echo "[metro] ready (try=${i})"
      if ! metro_ok "$host"; then
        echo "[metro] WARN: localhost OK but Tailscale ${host}:${PORT} DOWN"
      fi
      cmd_status
      return 0
    fi
    if ! kill -0 "$wrap_pid" 2>/dev/null && [[ -z "$(listening_pids)" ]]; then
      echo "[metro] process died early. tail log:"
      tail -40 "$LOG_FILE" || true
      exit 1
    fi
    sleep 1
  done
  echo "[metro] timeout waiting for :${PORT}"
  tail -40 "$LOG_FILE" || true
  exit 1
}

cmd_stop() {
  local pids
  pids="$(listening_pids)"
  if [[ -z "$pids" ]]; then
    echo "[metro] not running"
    rm -f "$PID_FILE"
    return 0
  fi
  echo "[metro] stopping pids: $(echo "$pids" | tr '\n' ' ')"
  # 명시적 stop에서만 kill. 다른 스크립트는 start 전 무조건 kill 하지 말 것.
  echo "$pids" | xargs kill 2>/dev/null || true
  sleep 1
  pids="$(listening_pids)"
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  echo "[metro] stopped"
}

cmd_restart() {
  cmd_stop
  sleep 1
  cmd_start
}

cmd_launch() {
  if ! metro_ok "127.0.0.1"; then
    echo "[metro] not running — start first"
    cmd_start
  fi
  local url
  url="$(deeplink_url)"
  echo "[metro] launch ${BUNDLE_ID}"
  echo "[metro] url=${url}"
  xcrun devicectl device process launch \
    --device "$DEVICE_UDID" \
    --terminate-existing \
    --payload-url "$url" \
    "$BUNDLE_ID"
}

cmd_url() {
  deeplink_url
}

usage() {
  cat <<EOF
Usage: bash scripts/metro_tailscale.sh <start|stop|restart|status|launch|url>

  start    Metro가 없으면 Tailscale용으로 기동 (이미 있으면 유지)
  stop     명시적으로만 종료
  restart  stop + start
  status   localhost/Tailscale 헬스 + 딥링크
  launch   Dev Client를 Tailscale 딥링크로 실기기 실행
  url      딥링크 문자열만 출력
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_restart ;;
    status) cmd_status ;;
    launch) cmd_launch ;;
    url) cmd_url ;;
    ""|-h|--help|help) usage ;;
    *) echo "unknown: $cmd"; usage; exit 1 ;;
  esac
}

main "${1:-}"
