#!/usr/bin/env bash
# Launch DFIR-IRIS (Docker Compose)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IRIS_DIR="$ROOT/tools/case_mgmt/dfir-iris"

if [[ ! -d "$IRIS_DIR" ]]; then
  echo "[ERROR] DFIR-IRIS not found at $IRIS_DIR"
  echo "Run: bash scripts/install_tools.sh"
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "[ERROR] Docker is required for DFIR-IRIS"
  echo "Install Docker: https://docs.docker.com/get-docker/"
  exit 1
fi

echo "[INFO] Starting DFIR-IRIS via Docker Compose..."
cd "$IRIS_DIR" && docker compose up -d
echo "[INFO] DFIR-IRIS running at http://localhost:4433"
echo "       Default credentials: administrator / irisadmin"
