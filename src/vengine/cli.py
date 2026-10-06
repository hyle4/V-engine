"""Command line lifecycle for standalone practice projects."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

from .api import create_app
from .jobs import import_source
from .project import ProjectConfig, load_project, save_project
from .runner import available
from .store import Store


def default_data() -> Path:
    return Path(os.environ.get("VENGINE_DATA", Path.home() / ".local/share/vengine/default"))


def main() -> None:
    parser = argparse.ArgumentParser(prog="vengine", description="Build and run source-linked practice apps")
    parser.add_argument("--data", type=Path, default=default_data(), help="project data directory")
    parser.add_argument("--project", type=Path, help="project directory containing vengine.toml")
    sub = parser.add_subparsers(dest="command", required=True)
    initialize = sub.add_parser("init", help="configure a project in the current directory")
    initialize.add_argument("--name", help="project name (defaults to directory name)")
    initialize.add_argument("--subject", default="General")
    server = sub.add_parser("serve", help="serve the local interface")
    server.add_argument("--port", type=int, default=8765)
    server.add_argument("--allow-local-runner", action="store_true",
                        help="allow host runner only when VENGINE_DEV_MODE=1")
    create = sub.add_parser("new", help="create an independent starter project")
    create.add_argument("name")
    create.add_argument("--target", type=Path, default=Path.cwd())
    importer = sub.add_parser("import", help="import a document for review")
    importer.add_argument("path", type=Path)
    importer.add_argument("--mode", choices=["study", "originals"], default="study")
    importer.add_argument("--answers", type=Path, help="official answer key for originals mode")
    importer.add_argument("--title", help="collection title")
    ai_mode = importer.add_mutually_exclusive_group()
    ai_mode.add_argument("--ai", dest="ai", action="store_true", default=None,
                         help="generate exercises with cloud AI")
    ai_mode.add_argument("--no-ai", dest="ai", action="store_false",
                         help="use conservative extraction only")
    importer.add_argument("--provider", help="AI provider name, including a registered project provider")
    importer.add_argument("--count", type=int, default=8)
    structured = sub.add_parser("import-exam-json", help="ingest a reviewed original-exam transcript")
    structured.add_argument("bundle", type=Path)
    structured.add_argument("--source", type=Path, required=True)
    structured.add_argument("--answers", type=Path)
    sub.add_parser("accept-official", help="approve review drafts that already have an official answer")
    sub.add_parser("doctor", help="check optional integrations")
    sub.add_parser("stats", help="show project counts")
    resume = sub.add_parser("resume", help="retry a failed import job")
    resume.add_argument("job_id")
    organize = sub.add_parser("organize", help="segment mixed exam prompts without rewriting them")
    organize.add_argument("--apply", action="store_true",
                          help="store exact partitions on the current revision")
    organize.add_argument("--provider", choices=["agy", "protocol"], default="agy",
                          help="agy reads each mixed prompt on its own")
    args = parser.parse_args()
    data_root = args.project.resolve() / "data" if args.project else args.data
    if args.project and (args.project / "project_plugins.py").is_file():
        sys.path.insert(0, str(args.project.resolve()))
        os.environ.setdefault("VENGINE_PLUGIN_MODULES", "project_plugins")
    if args.command == "new":
        if not re.fullmatch(r"[a-z][a-z0-9-]*", args.name):
            parser.error("project name must contain lowercase letters, digits, and hyphens")
        target = args.target / args.name
        if target.exists():
            parser.error(f"target already exists: {target}")
        template = Path(__file__).parent / "templates" / "starter"
        shutil.copytree(template, target)
        for file in target.rglob("*"):
            if file.is_file() and file.suffix in {".toml", ".md", ".py"}:
                file.write_text(file.read_text().replace("{{project_name}}", args.name))
        print(target)
    elif args.command == "init":
        project_root = (args.project or Path.cwd()).resolve()
        if load_project(project_root) is not None:
            parser.error(f"project already configured: {project_root}")
        config = ProjectConfig(name=args.name or project_root.name, subject=args.subject)
        print(save_project(project_root, config))
    elif args.command == "serve":
        import uvicorn
        if args.allow_local_runner:
            os.environ["VENGINE_ALLOW_LOCAL_RUNNER"] = "1"
        project_root = args.project.resolve() if args.project else None
        uvicorn.run(create_app(data_root, project_root=project_root), host="127.0.0.1", port=args.port)
    elif args.command == "import":
        config = load_project(args.project) if args.project else None
        preferred = config.ai_provider if config else "auto"
        provider = args.provider or (preferred if preferred not in {"auto", "none"} else
                                     "gemini" if os.getenv("GEMINI_API_KEY") else "agy")
        from .plugins import ai_provider_names
        configured = bool(os.getenv("GEMINI_API_KEY")) if provider == "gemini" else \
            bool(shutil.which("agy")) if provider == "agy" else provider in ai_provider_names()
        generate_ai = False if args.mode == "originals" else args.ai if args.ai is not None else bool(
            (args.provider or preferred != "none") and configured)
        from .project import refuses_import
        sample = ""
        if args.path.suffix.lower() in {".json", ".txt", ".md", ".markdown", ".csv"}:
            sample = args.path.read_text(encoding="utf-8", errors="replace")[:32768]
        if refuses_import(config, f"{args.path.name} {args.title or ''}", sample):
            parser.error("This project does not import that file")
        job = import_source(Store(data_root), args.path, generate_ai=generate_ai,
                            provider=provider, count=config.ai_count if config else args.count,
                            proposer=config.proposer if config else "builtin",
                            subject=config.subject if config else "General", mode=args.mode,
                            answer_path=args.answers, title=args.title)
        print(job.model_dump_json(indent=2))
    elif args.command == "import-exam-json":
        from .exam import ingest_structured
        config = load_project(args.project) if args.project else None
        result = ingest_structured(Store(data_root), args.bundle, args.source,
                                   answer_path=args.answers,
                                   subject=config.subject if config else "General")
        print(json.dumps(result, indent=2))
    elif args.command == "accept-official":
        print(json.dumps(Store(data_root).accept_official(), indent=2))
    elif args.command == "doctor":
        from .documents import supported_formats
        from .runner import available_runners
        ok, reason = available()
        print(json.dumps({"code_runner": {"ready": ok, "message": reason, "runners": available_runners()},
                          "project": str(args.project.resolve()) if args.project else None,
                          "formats": sorted(supported_formats()),
                          "ocr": bool(shutil.which("tesseract")),
                          "agy": bool(shutil.which("agy")),
                          "gemini_api_key": bool(os.getenv("GEMINI_API_KEY"))}, indent=2))
    elif args.command == "stats":
        print(json.dumps(Store(data_root).stats(), indent=2))
    elif args.command == "resume":
        from .jobs import run_job
        print(run_job(Store(data_root), args.job_id).model_dump_json(indent=2))
    elif args.command == "organize":
        from .organize import ask_agy, organize_store
        if args.provider == "agy" and not shutil.which("agy"):
            parser.error("agy CLI is not installed")
        seen = {"n": 0}

        def _progress(entry: dict) -> None:
            if args.provider != "agy" or not entry.get("consulted"):
                return
            seen["n"] += 1
            print(f"{seen['n']}\t{entry['label']}\t{entry['confidence']}\t{entry['reason']}",
                  file=sys.stderr, flush=True)

        report = organize_store(
            Store(data_root), apply=args.apply,
            resolve=ask_agy if args.provider == "agy" else None,
            every_marked=args.provider == "agy", on_item=_progress)
        staging = data_root / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        path = staging / "organize.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"path": str(path), "organized": report["organized"],
                          "unchanged": report["unchanged"], "uncertain": report["uncertain"],
                          "applied": report["applied"]}, indent=2))



if __name__ == "__main__":
    main()
