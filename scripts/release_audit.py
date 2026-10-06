"""Fail a public release if source files or built archives contain private artifacts."""

from __future__ import annotations

import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__",
             "node_modules", "target", "build", "dist", ".aws", ".codex", ".agents"}
PRIVATE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pdf", ".zip", ".7z", ".pem",
                    ".key", ".csv", ".jsonl", ".docx", ".xlsx", ".odt", ".txt",
                    ".tif", ".tiff", ".jpg", ".jpeg", ".webp"}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".js", ".css",
                 ".html", ".rs", ".sh", ".svg", ".txt", ".lock", ".gitignore"}
PATTERNS = {
    "personal home path": re.compile(r"/(?:ho" + r"me|Users)/[A-Za-z0-9_.-]+/"),
    "Windows home path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
    "private key": re.compile("-----BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "cloud access key": re.compile("AK" + "IA[0-9A-Z]{16}"),
    "API token": re.compile(r"\bsk" + r"-[A-Za-z0-9_-]{20,}\b"),
    "credential assignment": re.compile(r"(?im)^\s*(?:GEMINI|OPENAI|ANTHROPIC)_API_KEY\s*=\s*['\"]?[^\s'\"$]{12,}"),
    "email address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
}


def public_files() -> list[Path]:
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                             capture_output=True, check=False)
    if tracked.returncode == 0 and tracked.stdout:
        return [ROOT / name.decode() for name in tracked.stdout.split(b"\0") if name]
    return [path for path in ROOT.rglob("*") if path.is_file()
            and not set(path.relative_to(ROOT).parts) & SKIP_DIRS]


def check_file(name: str, payload: bytes) -> list[str]:
    path = Path(name)
    issues = []
    packaging_metadata = ".dist-info/" in name and path.name in {"entry_points.txt", "top_level.txt"}
    if (path.name == ".env" or path.name.startswith(".env.")
            or path.suffix.lower() in PRIVATE_SUFFIXES and not packaging_metadata):
        issues.append("private artifact")
    if path.suffix.lower() == ".png" and "desktop/src-tauri/icons/" not in name:
        issues.append("unreviewed image artifact")
    if path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE", "README", "AGENTS.md"}:
        body = payload.decode("utf-8", errors="replace")
        issues.extend(label for label, pattern in PATTERNS.items() if pattern.search(body))
    return issues


def scan_archive(path: Path) -> list[str]:
    issues = []
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                if not (name.startswith("vengine/") or ".dist-info/" in name):
                    issues.append(f"{path.name}:{name}: unexpected wheel path")
                issues.extend(f"{path.name}:{name}: {issue}"
                              for issue in check_file(name, archive.read(name)))
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                relative = member.name.partition("/")[2]
                allowed_root = {"README.md", "LICENSE", "pyproject.toml", "AGENTS.md",
                                ".gitignore", "PKG-INFO", "docs/AI_PROJECT_PLAYBOOK.md",
                                "docs/ORIGINAL_EXAMS.md"}
                if relative not in allowed_root and not relative.startswith("src/vengine/"):
                    issues.append(f"{path.name}:{member.name}: unexpected source archive path")
                content = archive.extractfile(member)
                if content:
                    issues.extend(f"{path.name}:{member.name}: {issue}"
                                  for issue in check_file(member.name, content.read()))
    return issues


def main() -> int:
    issues = []
    files = public_files()
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        issues.extend(f"{relative}: {issue}" for issue in check_file(relative, path.read_bytes()))
    archives = list((ROOT / "dist").glob("*.whl")) + list((ROOT / "dist").glob("*.tar.gz"))
    for archive in archives:
        issues.extend(scan_archive(archive))
    for issue in issues:
        print(issue, file=sys.stderr)
    print(f"Audited {len(files)} public files and {len(archives)} archives; {len(issues)} issue(s).")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
