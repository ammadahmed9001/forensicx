#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOOL="$ROOT/tools/osint/spiderfoot"
[[ -d "$TOOL/.venv" ]] && PY="$TOOL/.venv/bin/python3" || PY=python3
echo "SpiderFoot will be available at http://127.0.0.1:5001"
exec "$PY" "$TOOL/sf.py" -l 127.0.0.1:5001 "$@"
