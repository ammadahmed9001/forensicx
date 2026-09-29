#!/usr/bin/env bash
# Launch Dissect shell for a target path
TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <image_or_directory>"
  echo "Example: $0 /cases/disk.img"
  exit 1
fi

if ! command -v dissect &>/dev/null; then
  echo "[ERROR] dissect not found. Run: pip install dissect"
  exit 1
fi

echo "[INFO] Opening Dissect target: $TARGET"
dissect "$TARGET"
