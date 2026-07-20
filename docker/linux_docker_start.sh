#!/usr/bin/env bash

###############################################################################
# Minchodan Docker Build and Start - Linux
# Redis + MariaDB + FastAPI 3컨테이너 구성 + 호스트 로컬 Ollama 연동
# 상세 명세: docs/ops/deployment_guide.md
###############################################################################

set -u

# 스크립트가 위치한 디렉터리에서 프로젝트 루트로 이동
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

ENV_FILE=".env"
COMPOSE_FILE="docker/docker-compose.yml"
DEFAULT_WS_PORT="8000"
OLLAMA_LOCAL_URL="http://127.0.0.1:11434"
OLLAMA_LOG_FILE="logs/ollama.log"

print_header() {
  echo
  echo "========================================"
  echo "Minchodan Docker Build and Start"
  echo "========================================"
  echo
}

pause_if_interactive() {
  if [[ -t 0 ]]; then
    echo
    printf "Press Enter to close this window..."
    read -r _
  fi
}

read_env_value_first() {
  local wanted_key="$1"
  local ignore_case="${2:-0}"
  local wanted_compare="$wanted_key"
  local line key value key_compare

  if [[ "$ignore_case" == "1" ]]; then
    wanted_compare="$(printf "%s" "$wanted_key" | tr "[:lower:]" "[:upper:]")"
  fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    case "$line" in
      *=*)
        key="$(trim "${line%%=*}")"
        value="${line#*=}"
        if [[ "$ignore_case" == "1" ]]; then
          key_compare="$(printf "%s" "$key" | tr "[:lower:]" "[:upper:]")"
        else
          key_compare="$key"
        fi
        if [[ "$key_compare" == "$wanted_compare" ]]; then
          strip_wrapping_quotes "$value"
          return 0
        fi
        ;;
    esac
  done < "$ENV_FILE"
  return 1
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

ollama_url_from_host() {
  local host_value="$1"
  if [[ "$host_value" == http://* ]] || [[ "$host_value" == https://* ]]; then
    printf "%s" "$host_value"
    return 0
  fi
  if [[ "$host_value" == 0.0.0.0:* ]]; then
    printf "http://127.0.0.1:%s" "${host_value##*:}"
    return 0
  fi
  printf "http://%s" "$host_value"
}

is_ollama_ready() {
  curl -fsS "${OLLAMA_LOCAL_URL}/api/version" >/dev/null 2>&1
}

wait_for_ollama() {
  local ready=0
  for _ in {1..30}; do
    if is_ollama_ready; then
      ready=1
      break
    fi
    sleep 1
  done
  [[ "$ready" -eq 1 ]]
}

ensure_ollama_server() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "[ERROR] Ollama CLI is not installed."
    echo "Install it first: curl -fsSL https://ollama.com/install.sh | sh"
    pause_if_interactive
    exit 1
  fi

  if is_ollama_ready; then
    echo "[OK] Host Ollama is already running."
    return 0
  fi

  mkdir -p "$(dirname "$OLLAMA_LOG_FILE")"
  local ollama_host="${OLLAMA_HOST:-127.0.0.1:11434}"
  local keep_alive="${OLLAMA_KEEP_ALIVE:-30m}"
  local max_loaded="${OLLAMA_MAX_LOADED_MODELS:-2}"

  if [[ "$ollama_host" == "0.0.0.0:11434" ]] &&
     [[ "${MINCHODAN_EXPOSE_OLLAMA:-0}" != "1" ]]; then
    echo "[WARN] OLLAMA_HOST=0.0.0.0:11434 exposes the Ollama API on all host interfaces."
    echo "       Keeping the safer loopback default. To expose it intentionally, set:"
    echo "       MINCHODAN_EXPOSE_OLLAMA=1"
    ollama_host="127.0.0.1:11434"
  fi

  export OLLAMA_HOST="$ollama_host"
  OLLAMA_LOCAL_URL="$(ollama_url_from_host "$ollama_host")"

  echo "[INFO] Starting host Ollama without systemd..."
  echo "       OLLAMA_HOST=${ollama_host}"
  echo "       Log: ${OLLAMA_LOG_FILE}"
  env \
    OLLAMA_HOST="$OLLAMA_HOST" \
    OLLAMA_KEEP_ALIVE="$keep_alive" \
    OLLAMA_MAX_LOADED_MODELS="$max_loaded" \
    nohup ollama serve > "$OLLAMA_LOG_FILE" 2>&1 &

  if ! wait_for_ollama; then
    echo "[ERROR] Ollama did not become ready at ${OLLAMA_LOCAL_URL}."
    echo "Check the log: tail -n 80 ${OLLAMA_LOG_FILE}"
    pause_if_interactive
    exit 1
  fi
  echo "[OK] Host Ollama is running."
}

ensure_ollama_model() {
  local model="$1"
  if [[ -z "$(trim "$model")" ]]; then
    return 0
  fi

  if ollama show "$model" >/dev/null 2>&1; then
    echo "[OK] Ollama model available: ${model}"
    return 0
  fi

  echo "[INFO] Pulling Ollama model: ${model}"
  echo "       This can take a while on first run."
  if ! ollama pull "$model"; then
    echo "[ERROR] Failed to pull Ollama model: ${model}"
    pause_if_interactive
    exit 1
  fi
}

print_header

# 1. Docker 데몬 실행 여부 확인
if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker is not running."
  echo "Please start Docker daemon and try again."
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
if env_port="$(read_env_value_first "WS_PORT" 1)"; then
  if [[ -n "$(trim "$env_port")" ]]; then
    WS_PORT="$(trim "$env_port")"
  fi
fi

# Docker 컨테이너에서 호스트 로컬 Ollama로 접속할 주소 결정
if env_ollama_url="$(read_env_value_first "COMPOSE_OLLAMA_BASE_URL" 1)"; then
  if [[ -n "$(trim "$env_ollama_url")" ]]; then
    export COMPOSE_OLLAMA_BASE_URL="$(trim "$env_ollama_url")"
  fi
fi

if [[ -z "${COMPOSE_OLLAMA_BASE_URL:-}" ]]; then
  export COMPOSE_OLLAMA_BASE_URL="http://host.docker.internal:11434"
fi

# Ollama 서버 및 모델 준비
echo "[1/5] Preparing host Ollama..."
ensure_ollama_server

GEMMA_MODEL_VALUE="gemma4:e4b"
if env_gemma_model="$(read_env_value_first "GEMMA_MODEL" 1)"; then
  if [[ -n "$(trim "$env_gemma_model")" ]]; then
    GEMMA_MODEL_VALUE="$(trim "$env_gemma_model")"
  fi
fi

EMBEDDING_MODEL_VALUE="nomic-embed-text"
if env_embedding_model="$(read_env_value_first "EMBEDDING_MODEL" 1)"; then
  if [[ -n "$(trim "$env_embedding_model")" ]]; then
    EMBEDDING_MODEL_VALUE="$(trim "$env_embedding_model")"
  fi
fi

ensure_ollama_model "$GEMMA_MODEL_VALUE"
ensure_ollama_model "$EMBEDDING_MODEL_VALUE"

# 3. docker compose 설정 유효성 검사
echo "[2/5] Checking Docker Compose config..."
if ! docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet; then
  echo
  echo "[ERROR] docker-compose.yml or .env has a configuration problem."
  pause_if_interactive
  exit 1
fi

# 4. Docker 이미지 빌드
echo
echo "[3/5] Building Docker image (FastAPI)..."
if ! docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build fastapi; then
  echo
  echo "[ERROR] Docker image build failed."
  pause_if_interactive
  exit 1
fi

# 5. 컨테이너 시작
echo
echo "[4/5] Starting containers (Redis + MariaDB + FastAPI)..."
if ! docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d; then
  echo
  echo "[ERROR] Failed to start containers."
  pause_if_interactive
  exit 1
fi

# 6. FastAPI 포트 대기 (최대 60초)
echo
echo "[5/5] Waiting for FastAPI server (port $WS_PORT)..."
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
echo "Ollama URL:  ${OLLAMA_LOCAL_URL}/api/tags"
echo "FastAPI -> Ollama: ${COMPOSE_OLLAMA_BASE_URL}"
if [[ "${MINCHODAN_EXPOSE_OLLAMA:-0}" != "1" ]]; then
  echo
  echo "[NOTE] Ollama is bound to loopback by default."
  echo "       If FastAPI inside Docker cannot reach it, set MINCHODAN_EXPOSE_OLLAMA=1"
  echo "       and OLLAMA_HOST=0.0.0.0:11434 only on a trusted local network."
else
  echo
  echo "[SECURITY] Allow only the fixed Compose subnet to reach host Ollama:"
  echo "  sudo ufw allow from 172.18.0.0/16 to 172.18.0.1 port 11434 proto tcp"
fi
echo
echo "Ollama log:"
echo "  tail -f $OLLAMA_LOG_FILE"
echo
echo "Logs:"
echo "  docker compose --env-file $ENV_FILE -f $COMPOSE_FILE logs -f fastapi"
echo
echo "Stop:"
echo "  docker compose --env-file $ENV_FILE -f $COMPOSE_FILE down"
echo

pause_if_interactive
