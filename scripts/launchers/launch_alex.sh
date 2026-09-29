#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOOL="$ROOT/tools/mobile/ALEX"
[[ -d "$TOOL/.venv" ]] && PY="$TOOL/.venv/bin/python3" || PY=python3
exec "$PY" "$TOOL/alex.py" "$@"
