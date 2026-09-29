#!/usr/bin/env bash
# Check ADB device status
set -euo pipefail
echo "=== ADB devices ==="
adb devices -l 2>&1 || echo "adb not found — install: apt install android-tools-adb"
echo
echo "=== ADB version ==="
adb version 2>&1 || true
