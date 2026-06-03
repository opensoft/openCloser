#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZIP_FILE="${1:-"$ROOT_DIR/solution/managed/openCloser.Dynamics365.managed.zip"}"
SETTINGS_FILE="${2:-}"

if ! command -v pac >/dev/null 2>&1; then
  echo "Power Platform CLI 'pac' is required." >&2
  exit 127
fi

if [[ ! -f "$ZIP_FILE" ]]; then
  echo "Solution zip not found: $ZIP_FILE" >&2
  exit 2
fi

args=(solution import --path "$ZIP_FILE" --publish-changes)

if [[ -n "$SETTINGS_FILE" ]]; then
  if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "Settings file not found: $SETTINGS_FILE" >&2
    exit 2
  fi
  args+=(--settings-file "$SETTINGS_FILE")
fi

pac "${args[@]}"

