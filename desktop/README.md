# Native shell

The Tauri 2 shell starts the bundled Python sidecar on an available loopback port, waits for its health response, then opens the V-engine interface. Build the sidecar with `scripts/build_sidecar.sh`, then run `npm install` and `npm run tauri build` from this directory. For a portable Linux tarball, run `scripts/package_linux_tar.sh` from the repository root afterward.

The sidecar build requires PyInstaller, a Linux toolchain, and WebKitGTK development packages. Code grading additionally requires gVisor-enabled rootless Podman. The bundled server uses the user's `~/.local/share/vengine/default` data directory. The portable tarball expects the system WebKitGTK runtime; it is not a fully static binary.
