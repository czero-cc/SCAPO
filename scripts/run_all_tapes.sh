#!/usr/bin/env bash
set -euo pipefail

# Run all .tape files under scripts/tapes with vhs
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TAPES_DIR="$SCRIPT_DIR/tapes"

cd "$TAPES_DIR"

shopt -s nullglob
tapes=( *.tape )

if (( ${#tapes[@]} == 0 )); then
  echo "No .tape files found in $TAPES_DIR"
  exit 0
fi

for tape in "${tapes[@]}"; do
  echo "==> Running VHS: $tape"
  vhs "$tape"
done

echo "All tapes processed."


