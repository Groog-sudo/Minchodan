#!/usr/bin/env bash
# 통합 테스트 실행 래퍼 (integration-test-orchestrator 스킬 §8)
#
# tests/conftest.py는 fresh clone에서도 import가 깨지지 않도록 JWT_SECRET_KEY /
# JWT_ISSUER / JWT_AUDIENCE에 테스트 전용 기본값을 os.environ.setdefault로 주입한다.
# 그런데 live_server 마커 테스트(test_ws_echo.py, test_ws_live_priority.py)는 이미
# 기동된 FastAPI 컨테이너에 실제로 접속하므로, 서버가 쓰는 값과 iss/aud가 어긋나면
# 토큰 검증이 항상 실패한다(서버 기본값은 server/db/security.py의
# minchodan-api / minchodan-clients).
#
# 이 스크립트는 서버와 동일한 클레임을 미리 export해 conftest의 setdefault가
# 덮어쓰지 못하게 한 뒤 pytest를 실행한다.
#
# 사용법 (저장소 루트):
#   bash scripts/run_integration_tests.sh                 # 전체
#   bash scripts/run_integration_tests.sh tests/test_ws_echo.py -q
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f .env ]]; then
  echo "ERROR: 루트 .env가 없습니다." >&2
  exit 1
fi

PY="$PROJECT_ROOT/.venv/bin/python"
[[ -x "$PY" ]] || PY="python3"

# 비밀값은 셸 변수로만 전달하고 화면에 출력하지 않는다.
JWT_SECRET_KEY="$(grep -m1 '^JWT_SECRET_KEY=' .env | cut -d= -f2-)"
export JWT_SECRET_KEY
export JWT_ISSUER="${JWT_ISSUER:-minchodan-api}"
export JWT_AUDIENCE="${JWT_AUDIENCE:-minchodan-clients}"

if [[ -z "$JWT_SECRET_KEY" ]]; then
  echo "ERROR: .env에 JWT_SECRET_KEY가 없습니다." >&2
  exit 1
fi

echo "[tests] iss=$JWT_ISSUER aud=$JWT_AUDIENCE (secret 주입 완료)"
if ! curl -sf -o /dev/null --max-time 5 http://localhost:8000/; then
  echo "[tests] 경고: localhost:8000 미응답. live_server 마커 테스트는 실패합니다." >&2
fi

exec "$PY" -m pytest "${@:-tests/}" -p no:cacheprovider
