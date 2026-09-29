#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOOL="$ROOT/tools/mobile/ALEAPP"
[[ -d "$TOOL/.venv" ]] && PY="$TOOL/.venv/bin/python3" || PY=python3
exec "$PY" "$TOOL/aleappGUI.py" "$@"
