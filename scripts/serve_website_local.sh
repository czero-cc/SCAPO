#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")"/.. && pwd)"

echo "[1/3] Generating manifest..."
python3 "$repo_root/scripts/generate_models_manifest.py"

echo "[2/3] Syncing models into docs/models..."
mkdir -p "$repo_root/docs/models"
rsync -a --delete "$repo_root/models/" "$repo_root/docs/models/"

echo "[2.5/3] Copying docs assets..."
mkdir -p "$repo_root/docs/assets"
cp -f "$repo_root/assets/guy_freaking_out2.png" "$repo_root/docs/assets/" || true

echo "[3/3] Serving docs at http://localhost:8000 ... (Ctrl+C to stop)"
cd "$repo_root/docs"
python3 -m http.server 8000


