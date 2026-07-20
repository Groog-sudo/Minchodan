#!/usr/bin/env bash
# MinchodanDial 단축어를 서명하고 연결된 iPhone Downloads로 복사한다.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYMOBILE="${PYMOBILE:-$HOME/Library/Python/3.9/bin/pymobiledevice3}"

python3 "$ROOT/scripts/create_minchodan_dial_shortcut.py"

if [[ ! -x "$PYMOBILE" ]]; then
  echo "pymobiledevice3 없음. pip3 install pymobiledevice3 후 재실행하세요." >&2
  exit 1
fi

SIGNED="$ROOT/client/assets/shortcuts/MinchodanDial_signed.shortcut"
"$PYMOBILE" afc push "$SIGNED" "/Downloads/MinchodanDial.shortcut"
echo "iPhone Downloads에 MinchodanDial.shortcut 복사 완료"
echo "단말에서 파일 앱 > 다운로드 > MinchodanDial.shortcut 탭 > 단축어 추가"
