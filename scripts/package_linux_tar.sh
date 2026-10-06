#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
triple="$(rustc -vV | sed -n 's/^host: //p')"
desktop_bin="$repo_dir/desktop/src-tauri/target/release/vengine-desktop"
sidecar_bin="$repo_dir/desktop/src-tauri/binaries/vengine-server-$triple"
if [[ ! -x "$desktop_bin" || ! -x "$sidecar_bin" ]]; then
  printf 'Build the sidecar and desktop app first.\n' >&2
  exit 1
fi
stage_dir="$(mktemp -d)"
trap 'rm -rf "$stage_dir"' EXIT
mkdir -p "$stage_dir/V-engine" "$repo_dir/dist"
cp "$desktop_bin" "$stage_dir/V-engine/vengine-desktop"
cp "$sidecar_bin" "$stage_dir/V-engine/vengine-server"
cat > "$stage_dir/V-engine/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec ./vengine-desktop
EOF
chmod +x "$stage_dir/V-engine/run.sh"
printf 'V-engine Linux native build. Run ./run.sh; data is stored under ~/.local/share/vengine/default.\n' > "$stage_dir/V-engine/README.txt"
tar -C "$stage_dir" -czf "$repo_dir/dist/V-engine-linux-${triple}.tar.gz" V-engine
printf '%s\n' "$repo_dir/dist/V-engine-linux-${triple}.tar.gz"
