#!/usr/bin/env bash
# Mac Docker -> Raspberry Pi MariaDB TCP 프록시.
# Docker NAT IP는 원격 DB 화이트리스트에 없을 수 있어 macOS 호스트를 통해 중계한다.
# DB_PROXY_TARGET_HOST/PORT를 지정하면 시연(LAN)·테스트(Tailscale) 대상을 전환한다.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${DB_PROXY_ENV_FILE:-${ROOT_DIR}/.env}"
PROXY_PORT="${COMPOSE_DB_PROXY_PORT:-13306}"
PID_FILE="${ROOT_DIR}/.db_tailscale_proxy.pid"
LAUNCHD_LABEL="com.minchodan.dbproxy"

read_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r'
}

if [[ ! -f "$ENV_FILE" && -z "${DB_PROXY_TARGET_HOST:-}" ]]; then
  echo "[db-proxy] .env not found, skip"
  exit 0
fi

DB_HOST="${DB_PROXY_TARGET_HOST:-$(read_env DB_HOST || true)}"
DB_PORT="${DB_PROXY_TARGET_PORT:-$(read_env DB_PORT || true)}"
DB_PORT="${DB_PORT:-3306}"

if [[ -z "$DB_HOST" ]]; then
  echo "[db-proxy] DB target host is empty"
  exit 1
fi

if [[ ! "$DB_PORT" =~ ^[0-9]+$ ]]; then
  echo "[db-proxy] invalid DB target port: $DB_PORT"
  exit 1
fi

stop_existing_proxy() {
  local old_pid old_command
  if [[ "$(uname -s)" == "Darwin" ]] &&
     launchctl list "$LAUNCHD_LABEL" >/dev/null 2>&1; then
    launchctl remove "$LAUNCHD_LABEL"
  fi
  [[ -f "$PID_FILE" ]] || return 0
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    old_command="$(ps -p "$old_pid" -o command= 2>/dev/null || true)"
    if [[ "$old_command" == *"socat "* ]] &&
       [[ "$old_command" == *"TCP-LISTEN:${PROXY_PORT},"* ]]; then
      kill "$old_pid"
      for _ in {1..20}; do
        kill -0 "$old_pid" 2>/dev/null || break
        sleep 0.1
      done
    else
      echo "[db-proxy] stale pid file points to non-socat process; process preserved"
    fi
  fi
  rm -f "$PID_FILE"
}

# 로컬 compose mariadb 사용 시 프록시 불필요
if [[ "$DB_HOST" == "mariadb" || "$DB_HOST" == "127.0.0.1" || "$DB_HOST" == "localhost" ]]; then
  stop_existing_proxy
  echo "[db-proxy] local DB (${DB_HOST}), proxy not needed"
  exit 0
fi

if ! command -v socat >/dev/null 2>&1; then
  echo "[db-proxy] socat not installed. Run: brew install socat"
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" ]] && ! command -v python3 >/dev/null 2>&1; then
  echo "[db-proxy] python3 not installed; detached proxy cannot start"
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    old_command="$(ps -p "$old_pid" -o command= 2>/dev/null || true)"
    if [[ "$old_command" == *"TCP-LISTEN:${PROXY_PORT},"* ]] &&
       [[ "$old_command" == *"TCP:${DB_HOST}:${DB_PORT}"* ]]; then
      echo "[db-proxy] already running (pid=$old_pid, port=$PROXY_PORT, target=${DB_HOST}:${DB_PORT})"
      exit 0
    fi
    echo "[db-proxy] target changed; restarting proxy"
    stop_existing_proxy
  else
    rm -f "$PID_FILE"
  fi
fi

SOCAT_BIN="$(command -v socat)"

if [[ "$(uname -s)" == "Darwin" ]]; then
  # macOS 에이전트 셸 종료 후에도 프록시가 유지되도록 launchd에 작업을 위임한다.
  launchctl remove "$LAUNCHD_LABEL" >/dev/null 2>&1 || true
  launchctl submit -l "$LAUNCHD_LABEL" -- \
    "$SOCAT_BIN" \
    "TCP-LISTEN:${PROXY_PORT},fork,reuseaddr,bind=0.0.0.0" \
    "TCP:${DB_HOST}:${DB_PORT}"
  proxy_pid="$(launchctl list "$LAUNCHD_LABEL" | sed -n 's/.*"PID" = \([0-9][0-9]*\);/\1/p')"
  printf "%s" "$proxy_pid" > "$PID_FILE"
else
  PYTHON_BIN="$(command -v python3)"
  # Linux 셸 종료 후에도 프록시가 유지되도록 double-fork + setsid로 분리한다.
  "$PYTHON_BIN" - "$PID_FILE" "$SOCAT_BIN" "$PROXY_PORT" "$DB_HOST" "$DB_PORT" <<'PY'
import os
import sys

pid_file, socat_bin, proxy_port, db_host, db_port = sys.argv[1:]

first_pid = os.fork()
if first_pid > 0:
    _, status = os.waitpid(first_pid, 0)
    raise SystemExit(os.waitstatus_to_exitcode(status))

os.setsid()
second_pid = os.fork()
if second_pid > 0:
    with open(pid_file, "w", encoding="utf-8") as file:
        file.write(str(second_pid))
    os._exit(0)

devnull_fd = os.open(os.devnull, os.O_RDWR)
for file_descriptor in (0, 1, 2):
    os.dup2(devnull_fd, file_descriptor)
if devnull_fd > 2:
    os.close(devnull_fd)

os.execv(
    socat_bin,
    [
        socat_bin,
        f"TCP-LISTEN:{proxy_port},fork,reuseaddr,bind=0.0.0.0",
        f"TCP:{db_host}:{db_port}",
    ],
)
PY
fi

proxy_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
sleep 0.5
if kill -0 "$proxy_pid" 2>/dev/null; then
  echo "[db-proxy] started pid=$proxy_pid listen=0.0.0.0:${PROXY_PORT} -> ${DB_HOST}:${DB_PORT}"
else
  echo "[db-proxy] failed to start"
  rm -f "$PID_FILE"
  exit 1
fi
