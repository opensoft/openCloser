#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/solution/src"
PACKAGE_TYPE="${1:-Managed}"

if ! command -v pac >/dev/null 2>&1; then
  echo "Power Platform CLI 'pac' is required." >&2
  exit 127
fi

if [[ ! -f "$SRC_DIR/Other/Solution.xml" && ! -f "$SRC_DIR/Solution.xml" ]]; then
  echo "No unpacked solution source found in $SRC_DIR." >&2
  echo "Initialize with: cd $SRC_DIR && pac solution init --publisher-name openCloser --publisher-prefix oc" >&2
  exit 2
fi

pack_one() {
  local type="$1"
  local lower
  lower="$(printf '%s' "$type" | tr '[:upper:]' '[:lower:]')"
  local out_dir="$ROOT_DIR/solution/$lower"
  local out_zip="$out_dir/openCloser.Dynamics365.$lower.zip"

  mkdir -p "$out_dir"
  pac solution pack --folder "$SRC_DIR" --zipfile "$out_zip" --packagetype "$type"
  echo "Wrote $out_zip"
}

case "$PACKAGE_TYPE" in
  Managed)
    pack_one Managed
    ;;
  Unmanaged)
    pack_one Unmanaged
    ;;
  Both)
    pack_one Unmanaged
    pack_one Managed
    ;;
  *)
    echo "Usage: $0 [Managed|Unmanaged|Both]" >&2
    exit 2
    ;;
esac

