#!/usr/bin/env bash

###############################################################################
# Minchodan Docker Build and Start - macOS
# Redis + Ollama + FastAPI 3컨테이너 구성
# 상세 명세: docs/deployment_guide.md
#
# 주의: macOS는 Apple Silicon(M1/M2/M3) 또는 Intel 칩셋을 사용합니다.
# GPU 가속(Blackwell sm_120)은 지원되지 않으므로, 로컬 개발·테스트 용도로만
# 사용하십시오. 실제 추론 환경은 Linux + NVIDIA GPU 서버를 사용해야 합니다.
###############################################################################

set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

ENV_FILE=".env"
COMPOSE_FILE="docker/docker-compose.yml"
DEFAULT_WS_PORT="8000"

print_header() {
  echo
  echo "========================================"
  echo "Minchodan Docker Build and Start (macOS)"
  echo "========================================"
  echo
  echo "[NOTE] macOS does not support Blackwell GPU (sm_120)."
  echo "       Use for local development/testing only."
  echo "       Production inference requires Linux + NVIDIA GPU."
  echo
}

pause_if_interactive() {
  if [[ -t 0 ]]; then
    echo
    printf "Press Enter to close this window..."
    read -r _
  fi
}

trim() {
  local value="$1"
  value="${value%$'\r'}"
  while [[ "$value" == [[:space:]]* ]]; do value="${value#?}"; done
  while [[ "$value" == *[[:space:]] ]]; do value="${value%?}"; done
  printf "%s" "$value"
}

strip_wrapping_quotes() {
  local value
  value="$(trim "$1")"
  if [[ ${#value} -ge 2 ]]; then
    local first="${value:0:1}"
    local last="${value:$((${#value} - 1)):1}"
    if { [[ "$first" == "\"" ]] && [[ "$last" == "\"" ]]; } ||
       { [[ "$first" == "'" ]] && [[ "$last" == "'" ]]; }; then
      value="${value:1:$((${#value} - 2))}"
    fi
  fi
  printf "%s" "$value"
}

read_env_value_first() {
  local wanted_key="$1"
  local line key value
  local wanted_upper="$(printf "%s" "$wanted_key" | tr "[:lower:]" "[:upper:]")"

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    case "$line" in
      *=*)
        key="$(trim "${line%%=*}")"
        value="${line#*=}"
        local key_upper="$(printf "%s" "$key" | tr "[:lower:]" "[:upper:]")"
        if [[ "$key_upper" == "$wanted_upper" ]]; then
          strip_wrapping_quotes "$value"
          return 0
        fi
        ;;
    esac
  done < "$ENV_FILE"
  return 1
}

is_web_port_open() {
  local port="$1"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$port" <<'PY' >/dev/null 2>&1
import socket, sys
port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2.0)
try:
    sock.connect(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
    return $?
  fi
  ( : > "/dev/tcp/127.0.0.1/${port}" ) >/dev/null 2>&1
}

open_url() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 &
  fi
}

print_header

# 1. Docker 데몬 실행 여부 확인
if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker is not running."
  echo "Please start Docker Desktop and try again."
  pause_if_interactive
  exit 1
fi

# 2. .env 파일 존재 여부 확인
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] .env file not found."
  echo
  echo "Please copy .env.example to .env, then edit environment values."
  echo "See docs/environment_variables.md for variable details."
  echo
  echo "Command: cp .env.example .env"
  pause_if_interactive
  exit 1
fi

# WS_PORT 읽기
WS_PORT="$DEFAULT_WS_PORT"
if env_port="$(read_env_value_first "WS_PORT")"; then
  if [[ -n "$(trim "$env_port")" ]]; then
    WS_PORT="$(trim "$env_port")"
  fi
fi

# 3. docker compose 설정 유효성 검사
echo "[1/4] Checking Docker Compose config..."
if ! docker compose -f "$COMPOSE_FILE" config --quiet; then
  echo
  echo "[ERROR] docker-compose.yml or .env has a configuration problem."
  pause_if_interactive
  exit 1
fi

# 4. Docker 이미지 빌드
echo
echo "[2/4] Building Docker image (FastAPI)..."
if ! docker compose -f "$COMPOSE_FILE" build fastapi; then
  echo
  echo "[ERROR] Docker image build failed."
  pause_if_interactive
  exit 1
fi

# 5. 컨테이너 시작
echo
echo "[3/4] Starting containers (Redis + Ollama + FastAPI)..."
if ! docker compose -f "$COMPOSE_FILE" up -d; then
  echo
  echo "[ERROR] Failed to start containers."
  pause_if_interactive
  exit 1
fi

# 6. FastAPI 포트 대기 (최대 60초)
echo
echo "[4/4] Waiting for FastAPI server (port $WS_PORT)..."
web_ready=0
for _ in {1..30}; do
  if is_web_port_open "$WS_PORT"; then
    web_ready=1
    break
  fi
  sleep 2
done

if [[ "$web_ready" -eq 0 ]]; then
  echo "[WARN] FastAPI server is still starting. Continuing anyway."
fi

echo
echo "========================================"
echo "Done!"
echo "========================================"
echo
echo "FastAPI URL: http://127.0.0.1:${WS_PORT}/docs"
echo "Ollama URL:  http://127.0.0.1:11434/api/tags"
echo

URL="http://127.0.0.1:${WS_PORT}/docs"
open_url "$URL"

echo "Next steps (first run only):"
echo "  docker exec -it minchodan-ollama ollama pull gemma2:9b"
echo "  docker exec -it minchodan-ollama ollama pull llava"
echo "  docker exec -it minchodan-ollama ollama pull nomic-embed-text"
echo
echo "Logs:"
echo "  docker compose -f $COMPOSE_FILE logs -f fastapi"
echo
echo "Stop:"
echo "  docker compose -f $COMPOSE_FILE down"
echo

pause_if_interactive
