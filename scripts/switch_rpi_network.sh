#!/usr/bin/env bash

# Raspberry Pi MariaDB·미디어 API 네트워크 프로필 전환.
# demo=내부망, test=Tailscale. Docker 이미지는 재빌드하지 않는다.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PROFILE="${1:-}"
BASE_ENV_FILE=".env"
PROFILE_ENV_FILE=".env.network.${PROFILE}"
DB_PROXY_SCRIPT="$PROJECT_ROOT/docker/scripts/db_tailscale_proxy.sh"
DEFAULT_DB_PORT="3306"

usage() {
  echo "Usage: bash scripts/switch_rpi_network.sh <demo|test>"
  echo "  demo: Raspberry Pi LAN profile"
  echo "  test: Raspberry Pi Tailscale profile"
}

trim() {
  local value="$1"
  value="${value%$'\r'}"
  while [[ "$value" == [[:space:]]* ]]; do value="${value#?}"; done
  while [[ "$value" == *[[:space:]] ]]; do value="${value%?}"; done
  printf "%s" "$value"
}

read_env_value() {
  local file="$1"
  local wanted_key="$2"
  local line key value

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    case "$line" in
      *=*)
        key="$(trim "${line%%=*}")"
        value="${line#*=}"
        if [[ "$key" == "$wanted_key" ]]; then
          trim "$value"
          return 0
        fi
        ;;
    esac
  done < "$file"
  return 1
}

check_tcp() {
  local host="$1"
  local port="$2"
  if command -v nc >/dev/null 2>&1; then
    nc -z -w 3 "$host" "$port" >/dev/null 2>&1
    return $?
  fi
  python3 - "$host" "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

with socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=3):
    pass
PY
}

if [[ "$PROFILE" != "demo" && "$PROFILE" != "test" ]]; then
  usage
  exit 2
fi

if [[ ! -f "$BASE_ENV_FILE" ]]; then
  echo "[switch] ERROR: $BASE_ENV_FILE not found"
  exit 1
fi

if [[ ! -f "$PROFILE_ENV_FILE" ]]; then
  echo "[switch] ERROR: $PROFILE_ENV_FILE not found"
  exit 1
fi

db_host="$(read_env_value "$PROFILE_ENV_FILE" DB_HOST || true)"
db_port="$(read_env_value "$PROFILE_ENV_FILE" DB_PORT || true)"
db_port="${db_port:-$DEFAULT_DB_PORT}"
media_base_url="$(read_env_value "$PROFILE_ENV_FILE" IMAGE_SERVER_BASE_URL || true)"
network_env_file="$(read_env_value "$PROFILE_ENV_FILE" NETWORK_ENV_FILE || true)"
if [[ -z "$db_host" || -z "$media_base_url" || -z "$network_env_file" ]]; then
  echo "[switch] ERROR: profile requires NETWORK_ENV_FILE, DB_HOST, IMAGE_SERVER_BASE_URL"
  exit 1
fi

expected_network_env_file="../${PROFILE_ENV_FILE}"
if [[ "$network_env_file" != "$expected_network_env_file" ]]; then
  echo "[switch] ERROR: NETWORK_ENV_FILE must be $expected_network_env_file"
  exit 1
fi

if [[ ! "$db_port" =~ ^[0-9]+$ ]]; then
  echo "[switch] ERROR: invalid DB_PORT"
  exit 1
fi

case "$(uname -s)" in
  Darwin)
    compose_file="docker/docker-compose.macos.yml"
    export COMPOSE_DB_HOST="host.docker.internal"
    export COMPOSE_DB_PORT="${COMPOSE_DB_PROXY_PORT:-13306}"
    ;;
  Linux)
    compose_file="docker/docker-compose.yml"
    unset COMPOSE_DB_HOST COMPOSE_DB_PORT
    ;;
  *)
    echo "[switch] ERROR: unsupported OS: $(uname -s)"
    exit 1
    ;;
esac

compose_args=(
  docker compose
  --env-file "$BASE_ENV_FILE"
  --env-file "$PROFILE_ENV_FILE"
  -f "$compose_file"
)

echo "[switch] profile=$PROFILE"
echo "[switch] DB target=${db_host}:${db_port}"
echo "[switch] media target=$media_base_url"

if ! check_tcp "$db_host" "$db_port"; then
  echo "[switch] ERROR: DB TCP preflight failed"
  exit 1
fi

if ! curl -fsS --max-time 5 "$media_base_url/health" >/dev/null; then
  echo "[switch] ERROR: media health preflight failed"
  exit 1
fi

"${compose_args[@]}" config --quiet

if [[ "${MINCHODAN_SWITCH_CHECK_ONLY:-0}" == "1" ]]; then
  echo "[switch] check-only passed"
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "[switch] ERROR: Docker daemon is not running"
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  DB_PROXY_TARGET_HOST="$db_host" \
    DB_PROXY_TARGET_PORT="$db_port" \
    "$DB_PROXY_SCRIPT"
fi

if ! "${compose_args[@]}" up -d --no-build --no-deps --force-recreate fastapi; then
  echo "[switch] ERROR: FastAPI recreate failed; verify that minchodan-server:latest exists"
  exit 1
fi

fastapi_ready=0
for _ in {1..120}; do
  if "${compose_args[@]}" exec -T fastapi python -c \
    'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)' \
    >/dev/null 2>&1; then
    fastapi_ready=1
    break
  fi
  sleep 1
done

if [[ "$fastapi_ready" -ne 1 ]]; then
  echo "[switch] ERROR: FastAPI health timeout"
  exit 1
fi

"${compose_args[@]}" exec -T fastapi sh -lc \
  'printf "DB_HOST=%s\nDB_PORT=%s\nIMAGE_SERVER_BASE_URL=%s\n" "$DB_HOST" "$DB_PORT" "$IMAGE_SERVER_BASE_URL"'

"${compose_args[@]}" exec -T fastapi python -c '
import asyncio

from sqlalchemy import text

from server.db.connection import engine


async def main() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        print(f"db_select_1={result.scalar_one() == 1}")
    await engine.dispose()


asyncio.run(main())
'

"${compose_args[@]}" exec -T fastapi python -c '
import os
import urllib.request

url = os.environ["IMAGE_SERVER_BASE_URL"].rstrip("/") + "/health"
with urllib.request.urlopen(url, timeout=5) as response:
    print(f"media_health={response.status}")
'

echo "[switch] complete: $PROFILE"
