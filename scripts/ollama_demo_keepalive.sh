#!/usr/bin/env bash
# 시연용: Mac mini Ollama를 LAN에 열고 gemma4/nomic을 메모리 상주(keep_alive=-1)시킨다.
# 사용: bash scripts/ollama_demo_keepalive.sh
# GUI 앱(open -a Ollama)은 127.0.0.1만 바인딩하는 경우가 많아 CLI serve + OLLAMA_HOST=0.0.0.0 을 사용한다.
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
GEMMA_MODEL="${GEMMA_MODEL:-gemma4:e4b}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

launchctl setenv OLLAMA_HOST 0.0.0.0
launchctl setenv OLLAMA_KEEP_ALIVE -1
export OLLAMA_HOST=0.0.0.0
export OLLAMA_KEEP_ALIVE=-1

_is_lan_listen() {
  lsof -nP -iTCP:11434 -sTCP:LISTEN 2>/dev/null | grep -Eq '\*:11434|0\.0\.0\.0:11434'
}

_start_lan_serve() {
  echo "[keepalive] starting CLI ollama serve (OLLAMA_HOST=0.0.0.0)..."
  # GUI가 루프백만 잡으면 Windows Connection refused 가 난다. 앱/잔여 프로세스 정리 후 CLI만 기동.
  osascript -e 'quit app "Ollama"' 2>/dev/null || true
  pkill -x ollama 2>/dev/null || true
  sleep 1
  if lsof -nP -iTCP:11434 -sTCP:LISTEN >/dev/null 2>&1; then
    lsof -tiTCP:11434 -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
  # LaunchAgent가 있으면 그쪽을 우선 기동(재로그인 유지)
  if launchctl print "gui/$(id -u)/com.minchodan.ollama-lan" >/dev/null 2>&1; then
    launchctl kickstart -k "gui/$(id -u)/com.minchodan.ollama-lan" 2>/dev/null \
      || launchctl bootstrap "gui/$(id -u)" "${HOME}/Library/LaunchAgents/com.minchodan.ollama-lan.plist" 2>/dev/null \
      || true
  elif [[ -f "${HOME}/Library/LaunchAgents/com.minchodan.ollama-lan.plist" ]]; then
    launchctl bootstrap "gui/$(id -u)" "${HOME}/Library/LaunchAgents/com.minchodan.ollama-lan.plist" 2>/dev/null || true
  else
    nohup env OLLAMA_HOST=0.0.0.0 OLLAMA_KEEP_ALIVE=-1 /usr/local/bin/ollama serve \
      >/tmp/ollama-lan-serve.log 2>&1 &
  fi
  for _ in $(seq 1 40); do
    curl -sf --max-time 1 "${OLLAMA_URL}/api/tags" >/dev/null && break
    sleep 1
  done
}

if ! curl -sf --max-time 2 "${OLLAMA_URL}/api/tags" >/dev/null; then
  _start_lan_serve
fi

if ! _is_lan_listen; then
  echo "[keepalive] listen is loopback-only or missing; forcing LAN serve"
  _start_lan_serve
fi

if ! _is_lan_listen; then
  echo "[keepalive] FAIL: still not *:11434 / 0.0.0.0:11434" >&2
  lsof -nP -iTCP:11434 -sTCP:LISTEN >&2 || true
  exit 1
fi
echo "[keepalive] LAN listen OK"
lsof -nP -iTCP:11434 -sTCP:LISTEN | grep -E 'LISTEN|\*:11434|0\.0\.0\.0' || true

python3 - "$OLLAMA_URL" "$GEMMA_MODEL" "$EMBED_MODEL" <<'PY'
import json, sys, urllib.request

base, gemma, embed = sys.argv[1:4]

def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)

print(f"[keepalive] pin {gemma} keep_alive=-1")
post("/api/chat", {
    "model": gemma,
    "messages": [{"role": "user", "content": "ping"}],
    "stream": False,
    "keep_alive": -1,
    "think": False,
    "options": {"num_predict": 8, "temperature": 0},
})
print(f"[keepalive] pin {embed} keep_alive=-1")
post("/api/embeddings", {
    "model": embed,
    "prompt": "warmup",
    "keep_alive": -1,
})
print("[keepalive] OK (models resident until Ollama quit/reboot)")
PY
