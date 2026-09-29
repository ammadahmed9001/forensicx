#!/usr/bin/env bash
# Launch MobSF (Mobile Security Framework)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MOBSF_DIR="$ROOT/tools/mobile_re/MobSF"

if [[ ! -d "$MOBSF_DIR" ]]; then
  echo "[ERROR] MobSF not found at $MOBSF_DIR"
  echo "Run: bash scripts/install_tools.sh"
  exit 1
fi

PY="$MOBSF_DIR/.venv/bin/python3"
if [[ ! -x "$PY" ]]; then PY=python3; fi

echo "[INFO] Starting MobSF..."
cd "$MOBSF_DIR"

# Install if not set up
if [[ ! -f "MobSF/settings.py" ]] && [[ -f "setup.py" ]]; then
  echo "[INFO] Running MobSF setup..."
  bash setup.sh
fi

"$PY" manage.py runserver 0.0.0.0:8000 &
echo "[INFO] MobSF running at http://localhost:8000"
