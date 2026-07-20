#!/usr/bin/env bash
# Metro(Tailscale) 고정 운영 스크립트.
#
# 목적:
# - Metro를 "한 인스턴스"로만 유지 (이미 떠 있으면 start가 재기동하지 않음)
# - 재기동은 명시적 restart/stop 에서만 kill
# - 앱은 Tailscale 딥링크로만 열어 Bonjour 미검색 문제를 우회
# - 기동 시 Python double-fork + setsid 로 에이전트/터미널 세션과 완전 분리
#   (macOS에 setsid CLI 없음. nohup만으로는 Cursor 에이전트 셸 종료 시 회수되는 실측)
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
#   METRO_CLEAR=1                 # start 시 expo --clear
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
METRO_CLEAR="${METRO_CLEAR:-0}"

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

# Cursor 에이전트 셸/nohup 회수를 피하기 위해 세션 리더를 분리한 뒤 orphan 시킨다.
# 성공 시 부모(호출 셸)는 즉시 반환하고, Metro 부모 PID는 launchd(1)이 된다.
daemonize_expo() {
  local host="$1"
  local npx_bin
  npx_bin="$(command -v npx)"
  if [[ -z "$npx_bin" ]]; then
    echo "ERROR: npx 를 PATH에서 찾지 못했습니다." >&2
    exit 1
  fi

  PATH_VALUE="$PATH" \
  NPX_BIN="$npx_bin" \
  CLIENT_DIR="$CLIENT_DIR" \
  LOG_FILE="$LOG_FILE" \
  PACKAGER_HOST="$host" \
  METRO_PORT="$PORT" \
  METRO_SCHEME="$SCHEME" \
  METRO_CLEAR_FLAG="$METRO_CLEAR" \
  python3 - <<'PY'
import os
import sys

def _daemonize() -> None:
    if os.fork() > 0:
        # 1차 부모: 호출자에게 즉시 반환
        sys.exit(0)
    os.setsid()
    if os.fork() > 0:
        # 세션 리더 중간 부모 종료 -> 손자는 orphan
        sys.exit(0)

    os.umask(0o022)
    os.chdir(os.environ["CLIENT_DIR"])

    devnull = os.open(os.devnull, os.O_RDONLY)
    log_fd = os.open(
        os.environ["LOG_FILE"],
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o644,
    )
    os.dup2(devnull, 0)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    if devnull > 2:
        os.close(devnull)
    if log_fd > 2:
        os.close(log_fd)

    env = os.environ.copy()
    env["PATH"] = os.environ.get("PATH_VALUE", env.get("PATH", ""))
    env["REACT_NATIVE_PACKAGER_HOSTNAME"] = os.environ["PACKAGER_HOST"]
    env.pop("CI", None)

    cmd = [
        os.environ["NPX_BIN"],
        "expo",
        "start",
        "--host",
        "lan",
        "--port",
        os.environ["METRO_PORT"],
        "--scheme",
        os.environ["METRO_SCHEME"],
    ]
    if os.environ.get("METRO_CLEAR_FLAG", "0") in ("1", "true", "TRUE", "yes"):
        cmd.insert(3, "--clear")

    os.execvpe(cmd[0], cmd, env)

_daemonize()
PY
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

  local listen_pid
  listen_pid="$(listening_pids | head -1 || true)"
  if [[ -n "${listen_pid:-}" ]]; then
    local cur parent_cmd chain agent_hit=0
    cur="$listen_pid"
    chain="$listen_pid"
    # zsh 예약 변수 PPID와 충돌하지 않도록 이름 분리
    for _ in 1 2 3 4 5 6 7 8; do
      local parent_pid
      parent_pid="$(ps -p "$cur" -o ppid= 2>/dev/null | tr -d ' ' || true)"
      if [[ -z "${parent_pid:-}" || "$parent_pid" == "0" ]]; then
        break
      fi
      parent_cmd="$(ps -p "$parent_pid" -o command= 2>/dev/null || true)"
      chain="${chain}->${parent_pid}"
      if echo "$parent_cmd" | grep -qiE 'cursor-agent|Cursor Agent|agent --use-system-ca'; then
        agent_hit=1
      fi
      if [[ "$parent_pid" == "1" ]]; then
        break
      fi
      cur="$parent_pid"
    done
    echo "listen_pid=${listen_pid} ancestry=${chain}"
    if [[ "$agent_hit" == "1" ]]; then
      echo "detach: WARN (ancestry에 cursor-agent — 세션 종료 시 죽을 수 있음. restart 권장)"
    elif [[ "$chain" == *'->1' ]]; then
      echo "detach: OK (session root=launchd/1, agent shell 독립)"
    else
      echo "detach: OK (ancestry=${chain})"
    fi
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

  echo "[metro] starting detached (host=lan packager=${host} port=${PORT} clear=${METRO_CLEAR})"
  : >>"$LOG_FILE"
  daemonize_expo "$host"

  local i
  for i in $(seq 1 45); do
    if metro_ok "127.0.0.1"; then
      listening_pids | head -1 >"$PID_FILE" || true
      echo "[metro] ready (try=${i})"
      if ! metro_ok "$host"; then
        echo "[metro] WARN: localhost OK but Tailscale ${host}:${PORT} DOWN"
      fi
      cmd_status
      return 0
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
  # expo/metro 잔여 프로세스 정리(포트 LISTEN 외 래퍼)
  pkill -f "expo start --host lan --port ${PORT}" 2>/dev/null || true
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

  start    Metro가 없으면 Tailscale용으로 기동 (이미 있으면 유지, agent 세션 분리)
  stop     명시적으로만 종료
  restart  stop + start
  status   localhost/Tailscale 헬스 + 딥링크 + detach 여부
  launch   Dev Client를 Tailscale 딥링크로 실기기 실행
  url      딥링크 문자열만 출력

  METRO_CLEAR=1 bash scripts/metro_tailscale.sh start   # 번들 캐시 클리어
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
