#!/usr/bin/env bash
# Mac Docker -> Tailscale MariaDB TCP 프록시.
# Docker NAT IP(172.x)는 원격 DB 화이트리스트에 없을 수 있어 호스트 Tailscale IP로 중계한다.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
PROXY_PORT="${COMPOSE_DB_PROXY_PORT:-13306}"
PID_FILE="${ROOT_DIR}/.db_tailscale_proxy.pid"

read_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r'
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[db-proxy] .env not found, skip"
  exit 0
fi

DB_HOST="$(read_env DB_HOST)"
DB_PORT="$(read_env DB_PORT)"
DB_PORT="${DB_PORT:-3306}"

# 로컬 compose mariadb 사용 시 프록시 불필요
if [[ "$DB_HOST" == "mariadb" || "$DB_HOST" == "127.0.0.1" || "$DB_HOST" == "localhost" ]]; then
  echo "[db-proxy] local DB (${DB_HOST}), proxy not needed"
  exit 0
fi

if ! command -v socat >/dev/null 2>&1; then
  echo "[db-proxy] socat not installed. Run: brew install socat"
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "[db-proxy] already running (pid=$old_pid, port=$PROXY_PORT)"
    exit 0
  fi
fi

socat "TCP-LISTEN:${PROXY_PORT},fork,reuseaddr,bind=0.0.0.0" "TCP:${DB_HOST}:${DB_PORT}" >/dev/null 2>&1 &
proxy_pid=$!
echo "$proxy_pid" > "$PID_FILE"
sleep 0.3
if kill -0 "$proxy_pid" 2>/dev/null; then
  echo "[db-proxy] started pid=$proxy_pid listen=127.0.0.1:${PROXY_PORT} -> ${DB_HOST}:${DB_PORT}"
else
  echo "[db-proxy] failed to start"
  rm -f "$PID_FILE"
  exit 1
fi
