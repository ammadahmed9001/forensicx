#!/usr/bin/env bash
# Launch TheHive (Docker Compose)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HIVE_DIR="$ROOT/tools/case_mgmt/TheHive"

if [[ ! -d "$HIVE_DIR" ]]; then
  echo "[ERROR] TheHive not found at $HIVE_DIR"
  echo "Run: bash scripts/install_tools.sh"
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "[ERROR] Docker is required for TheHive"
  echo "Install Docker: https://docs.docker.com/get-docker/"
  exit 1
fi

echo "[INFO] Starting TheHive via Docker Compose..."
cd "$HIVE_DIR" && docker compose up -d
echo "[INFO] TheHive running at http://localhost:9000"
echo "       Default credentials: admin@thehive.local / secret"
