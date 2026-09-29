#!/usr/bin/env bash
# Launch the ForensicX Hub GUI
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 -m forensicx_hub "$@"
