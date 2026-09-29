#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOOL="$ROOT/tools/artifacts/hindsight"
[[ -d "$TOOL/.venv" ]] && PY="$TOOL/.venv/bin/python3" || PY=python3
exec "$PY" "$TOOL/hindsight.py" "$@"
