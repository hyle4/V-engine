# V-engine

V-engine is a local practice framework for original exam questions and source-linked study exercises. Each subject has its own project, source files, review queue, and attempt history. Imported and generated questions require human approval before practice.

Give your coding assistant this repository, the subject you want to study, and your source files. [The AI project playbook](docs/AI_PROJECT_PLAYBOOK.md) tells the assistant how to create a separate project, import material, repair ambiguous extraction, and hand it back for review. [Original exam intake](docs/ORIGINAL_EXAMS.md) covers shared reading texts and official answer keys. The public repository contains no exam corpus or personal project data.

## Create a project from a clone

Python 3.12 and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync --extra dev
uv run vengine new diplomacy-practice --target /path/to/projects
cd /path/to/projects/diplomacy-practice
uv venv
uv pip install -e /path/to/V-engine
uv run --no-sync python app.py
```

Open `http://127.0.0.1:8765`. The assistant sets subject and technical options in the new project's `vengine.toml`; the learner sees a name-only setup if that manifest is absent. Private data lives in ignored `data/`. The browser service binds to loopback for one local user.

Once the package is published, generated projects can pin its release and use `uv sync` instead of the editable local install. To inspect the engine itself, run `uv run vengine --project . serve`; a root-level preview manifest and data directory are ignored. The previous data-directory command remains available: `uv run vengine --data /path/to/data serve`.

## Create an independent practice app

The generated app depends on a versioned V-engine package and keeps only its own configuration, plugins, and data. Keep local absolute dependency paths out of committed files.

## Pipeline

1. Import an original exam or a study source in PDF, image, text, Markdown, JSON, or CSV through the UI or CLI. Original bytes are stored by SHA-256.
2. PDF text uses PDFium; scanned pages and images require Tesseract. Each PDF page is checkpointed so a failed import can resume.
3. Originals mode extracts numbered questions, options, explicit shared-text ranges, and a supplied answer key. For difficult layouts, the assistant can provide a validated `vengine-exam.v1` transcript. Study mode retains conservative or AI generation; AI citations must appear in the parsed source.
4. Review the source, any shared text, prompt, interaction, and answer. Approval is explicit and creates a published revision.
5. Practice stores immutable attempts against the exact revision answered; FSRS schedules due review.

`GET /api/capabilities` and `vengine doctor` report configured providers, OCR, formats, and runners. Imports run in a background queue; the UI can cancel them, and unfinished jobs resume when the server restarts.

## Extensions

Place trusted Python hooks in `project_plugins.py`. The framework supports `register_parser`, `register_proposer`, `register_ai_provider`, and `register_grader`. See [Plugin API](docs/PLUGIN_API.md) for signatures and an example. The `plugin` interaction type keeps private answer payloads out of the pre-submit browser response. Project plugins are executable local code and should be reviewed before running a cloned project.

The built-in interaction contract covers choice, boolean, text, numeric, cloze, matching, ordering, rubric, Python, JavaScript, SQL, composite, and plugin exercises. Advanced code and SQL answers require a container runner. Host execution is restricted to explicit developer mode with both `VENGINE_DEV_MODE=1` and `VENGINE_ALLOW_LOCAL_RUNNER=1`.

## Optional prerequisites

- AI: install the `ai` extra and set `GEMINI_API_KEY`, or install and configure `agy`.
- OCR: install Tesseract and the language data needed by `VENGINE_OCR_LANG`.
- Code and SQL: install rootless Podman with `runsc`, or Docker; pull the configured Python and Node runner images. `vengine doctor` checks readiness.
- Linux desktop: build the Tauri shell using [desktop instructions](desktop/README.md). The browser app is the primary cross-platform interface.

## Develop and release

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests scripts
node --check src/vengine/web/app.js
uv build
```

See [Architecture](ARCHITECTURE.md), [twelve-route status](ROADMAP.md), [migration](docs/MIGRATION.md), [changelog](CHANGELOG.md), [contributing](CONTRIBUTING.md), [security](SECURITY.md), and the [release checklist](docs/RELEASE_CHECKLIST.md). The first public 1.0 release remains gated on cross-platform feature validation, live provider checks, container isolation tests, accessibility review, privacy audit, and publishing credentials.
