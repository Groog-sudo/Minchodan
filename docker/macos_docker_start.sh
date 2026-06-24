#!/usr/bin/env bash

###############################################################################
# DoctorSkin Docker Build and Start - macOS
#
# 이 스크립트는 Windows용 docker_start_v03.bat와 같은 흐름으로 동작합니다.
#
# 실행 흐름:
# 1. 스크립트가 있는 프로젝트 루트로 이동합니다.
# 2. Docker 실행 여부와 .env 파일 존재 여부를 확인합니다.
# 3. docker compose 설정이 유효한지 검사합니다.
# 4. .env의 DOCKER_IMAGE_TAG를 읽어 patch 버전을 1 올린 다음,
#    그 값을 Docker Compose 환경변수로 넘겨 이미지를 빌드합니다.
# 5. 빌드가 성공한 경우에만 .env의 DOCKER_IMAGE_TAG를 새 값으로 저장합니다.
# 6. 컨테이너를 백그라운드로 시작하고, 웹 포트가 열릴 때까지 잠시 기다립니다.
# 7. macOS의 open 명령으로 브라우저를 엽니다.
#
# 사용 예:
#   chmod +x docker_start_v03_macos.sh
#   ./docker_start_v03_macos.sh
###############################################################################

# set -u:
# 정의되지 않은 변수를 사용하면 즉시 오류로 처리합니다.
# set -e는 사용하지 않습니다. 각 단계별로 Windows 배치 파일처럼
# 사용자 친화적인 오류 메시지를 직접 출력하기 위해서입니다.
set -u

# 스크립트 파일이 위치한 디렉터리를 계산합니다.
# 어디에서 실행하더라도 프로젝트 루트 기준으로 동작하게 하기 위함입니다.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

ENV_FILE=".env"
TAG_KEY="DOCKER_IMAGE_TAG"
DEFAULT_TAG="v1.0.0"

print_header() {
  echo
  echo "========================================"
  echo "DoctorSkin Docker Build and Start"
  echo "========================================"
  echo
}

pause_if_interactive() {
  # 배치 파일의 pause와 비슷한 역할입니다.
  # 단, 파이프/CI 환경에서 실행될 때는 입력 대기로 멈추지 않도록
  # 터미널이 연결된 경우에만 Enter 입력을 기다립니다.
  if [[ -t 0 ]]; then
    echo
    printf "Press Enter to close this window..."
    read -r _
  fi
}

trim() {
  # 문자열 앞뒤의 공백과 CR 문자를 제거합니다.
  # Windows에서 작성된 .env가 CRLF 줄바꿈을 가질 수 있어 CR도 함께 처리합니다.
  local value="$1"
  value="${value%$'\r'}"

  while [[ "$value" == [[:space:]]* ]]; do
    value="${value#?}"
  done

  while [[ "$value" == *[[:space:]] ]]; do
    value="${value%?}"
  done

  printf "%s" "$value"
}

strip_wrapping_quotes() {
  # .env 값이 "v1.0.3" 또는 'v1.0.3'처럼 따옴표로 감싸져 있으면
  # 실제 태그 계산에는 따옴표를 제외한 값만 사용합니다.
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
  # .env 파일에서 특정 key의 첫 번째 값을 읽습니다.
  # 두 번째 인자로 1을 넘기면 key 비교를 대소문자 구분 없이 수행합니다.
  # HOST_PORT는 Windows 배치 파일에서도 대소문자 구분 없이 읽으므로 1을 사용합니다.
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

calculate_docker_image_tag() {
  # bump_docker_tag.ps1의 핵심 로직을 Bash로 옮긴 함수입니다.
  #
  # 인자가 비어 있으면:
  #   .env의 DOCKER_IMAGE_TAG를 읽고 patch 버전을 1 증가시킵니다.
  #
  # 인자가 있으면:
  #   해당 값을 최종 태그로 간주하고 증가시키지 않습니다.
  #   배치 파일의 -SetTag 동작과 같은 의미입니다.
  local set_tag="${1:-}"
  local set_tag_trimmed current_tag major minor patch next_tag

  set_tag_trimmed="$(trim "$set_tag")"

  if [[ -n "$set_tag_trimmed" ]]; then
    current_tag="$(strip_wrapping_quotes "$set_tag_trimmed")"
  else
    if ! current_tag="$(read_env_value_first "$TAG_KEY" 0)"; then
      current_tag="$DEFAULT_TAG"
    fi

    if [[ -z "$(trim "$current_tag")" ]]; then
      current_tag="$DEFAULT_TAG"
    fi
  fi

  # 허용 형식:
  #   v1.0.3, 1.0.3, v1.0, 1.0
  # patch가 없으면 0으로 간주한 뒤 필요 시 1 증가시킵니다.
  if [[ ! "$current_tag" =~ ^v?([0-9]+)\.([0-9]+)(\.([0-9]+))?$ ]]; then
    echo "[ERROR] Invalid ${TAG_KEY} value '${current_tag}'. Use vMAJOR.MINOR.PATCH, for example v1.0.1." >&2
    return 1
  fi

  major="${BASH_REMATCH[1]}"
  minor="${BASH_REMATCH[2]}"
  patch="${BASH_REMATCH[4]:-0}"

  if [[ -z "$set_tag_trimmed" ]]; then
    patch=$((patch + 1))
  fi

  next_tag="v$((10#$major)).$((10#$minor)).$((10#$patch))"
  printf "%s\n" "$next_tag"
}

save_docker_image_tag() {
  # 빌드가 성공한 뒤 새 이미지 태그를 .env에 저장합니다.
  # 기존 DOCKER_IMAGE_TAG 줄은 첫 번째 줄만 유지하고,
  # 중복된 DOCKER_IMAGE_TAG 줄은 제거합니다.
  local requested_tag="$1"
  local next_tag tmp_file found line key

  if ! next_tag="$(calculate_docker_image_tag "$requested_tag")"; then
    return 1
  fi

  tmp_file="$(mktemp "${ENV_FILE}.tmp.XXXXXX")" || return 1
  found=0

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"

    if [[ "$line" == *=* ]]; then
      key="$(trim "${line%%=*}")"
    else
      key=""
    fi

    if [[ "$key" == "$TAG_KEY" ]]; then
      if [[ "$found" -eq 0 ]]; then
        printf "%s=%s\n" "$TAG_KEY" "$next_tag" >> "$tmp_file"
        found=1
      fi
    else
      printf "%s\n" "$line" >> "$tmp_file"
    fi
  done < "$ENV_FILE"

  if [[ "$found" -eq 0 ]]; then
    printf "%s=%s\n" "$TAG_KEY" "$next_tag" >> "$tmp_file"
  fi

  if ! mv "$tmp_file" "$ENV_FILE"; then
    rm -f "$tmp_file"
    return 1
  fi

  printf "%s\n" "$next_tag"
}

is_web_port_open() {
  # 웹 서버가 준비됐는지 TCP 포트 연결로 확인합니다.
  # macOS 환경마다 설치된 도구가 다를 수 있으므로 python3, nc, curl 순서로 시도합니다.
  local port="$1"

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(1.0)

try:
    sock.connect(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
    return $?
  fi

  if command -v nc >/dev/null 2>&1; then
    nc -z -w 1 127.0.0.1 "$port" >/dev/null 2>&1
    return $?
  fi

  if command -v curl >/dev/null 2>&1; then
    curl --silent --output /dev/null --max-time 1 "http://127.0.0.1:${port}/"
    return $?
  fi

  # 마지막 fallback입니다. Bash의 /dev/tcp 기능을 사용합니다.
  ( : > "/dev/tcp/127.0.0.1/${port}" ) >/dev/null 2>&1
}

open_url() {
  # macOS에서는 open 명령이 기본 브라우저를 실행합니다.
  local url="$1"

  if ! open "$url" >/dev/null 2>&1; then
    echo "[WARN] Failed to open the browser automatically."
  fi
}

print_header

if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker is not running."
  echo "Please start Docker Desktop and try again."
  pause_if_interactive
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] .env file not found."
  echo
  echo "Please copy .env.example to .env, then edit DB password,"
  echo "SECRET_KEY, API keys, and other environment values."
  echo
  echo "Command:"
  echo "cp .env.example .env"
  pause_if_interactive
  exit 1
fi

HOST_PORT="8100"
if env_host_port="$(read_env_value_first "HOST_PORT" 1)"; then
  if [[ -n "$(trim "$env_host_port")" ]]; then
    HOST_PORT="$(trim "$env_host_port")"
  fi
fi

echo "[1/4] Checking Docker Compose config..."
if ! docker compose config --quiet; then
  echo
  echo "[ERROR] docker-compose.yml or .env has a configuration problem."
  echo "Please check the error message above."
  pause_if_interactive
  exit 1
fi

echo
echo "[2/4] Preparing Docker image version..."
if ! DOCKER_IMAGE_TAG="$(calculate_docker_image_tag "")"; then
  echo
  echo "[ERROR] Failed to prepare Docker image version."
  pause_if_interactive
  exit 1
fi

# Docker Compose는 .env보다 현재 셸의 환경변수를 우선합니다.
# 따라서 .env를 아직 저장하지 않아도 이번 빌드는 새 태그로 수행됩니다.
export DOCKER_IMAGE_TAG
echo "Image tag: doctorskin:${DOCKER_IMAGE_TAG}"

echo
echo "[3/4] Building Docker image..."
if ! docker compose build; then
  echo
  echo "[ERROR] Docker image build failed."
  pause_if_interactive
  exit 1
fi

echo
echo "Saving Docker image version..."
if ! saved_tag="$(save_docker_image_tag "$DOCKER_IMAGE_TAG")"; then
  echo
  echo "[ERROR] Failed to save Docker image version."
  pause_if_interactive
  exit 1
fi
DOCKER_IMAGE_TAG="$saved_tag"
export DOCKER_IMAGE_TAG

echo
echo "[4/4] Starting containers..."
if ! docker compose up -d; then
  echo
  echo "[ERROR] Failed to start containers."
  pause_if_interactive
  exit 1
fi

echo
echo "========================================"
echo "Done!"
echo "========================================"
echo
echo "Waiting for web server..."

web_ready=0
for _ in {1..30}; do
  if is_web_port_open "$HOST_PORT"; then
    web_ready=1
    break
  fi
  sleep 2
done

if [[ "$web_ready" -eq 0 ]]; then
  echo "[WARN] Web server is still starting. Opening the URL anyway."
fi

URL="http://127.0.0.1:${HOST_PORT}"
echo "URL:"
echo "$URL"
echo
open_url "$URL"

echo "Logs:"
echo "docker compose logs -f web"
echo
echo "Stop:"
echo "docker compose down"
echo

pause_if_interactive
