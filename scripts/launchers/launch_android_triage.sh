#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOOL="$ROOT/tools/mobile/android_triage"
exec bash "$TOOL/android_triage.sh" "$@"
