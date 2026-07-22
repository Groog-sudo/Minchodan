#!/usr/bin/env bash
# 시연용: Mac mini Ollama를 LAN에 열고 gemma4/nomic을 메모리 상주(keep_alive=-1)시킨다.
# 사용: bash scripts/ollama_demo_keepalive.sh
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
GEMMA_MODEL="${GEMMA_MODEL:-gemma4:e4b}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

launchctl setenv OLLAMA_HOST 0.0.0.0
launchctl setenv OLLAMA_KEEP_ALIVE -1

if ! curl -sf --max-time 2 "${OLLAMA_URL}/api/tags" >/dev/null; then
  echo "[keepalive] Ollama not up; launching app..."
  open -a Ollama
  for _ in $(seq 1 30); do
    curl -sf --max-time 1 "${OLLAMA_URL}/api/tags" >/dev/null && break
    sleep 1
  done
fi

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
