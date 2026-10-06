#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
target_triple="$(rustc -vV | sed -n 's/^host: //p')"
uv run --extra ai --with pyinstaller pyinstaller --noconfirm --clean --onefile \
  --name vengine-server --collect-all vengine --collect-all google.genai scripts/sidecar_entry.py
mkdir -p desktop/src-tauri/binaries
cp dist/vengine-server "desktop/src-tauri/binaries/vengine-server-${target_triple}"
printf 'Sidecar ready: %s\n' "desktop/src-tauri/binaries/vengine-server-${target_triple}"
