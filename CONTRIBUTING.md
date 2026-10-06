# Contributing

V-engine accepts fixes to the source → proposal → review → practice pipeline, project adapters, accessibility, and release tooling. Open an issue describing the user-facing behavior before a large change.

1. Use Python 3.12 and run `uv sync --extra dev`.
2. Keep project data under `data/` or a temporary directory. Do not commit source documents, credentials, or generated attempts.
3. Run `uv run pytest -q`, `uv run ruff check src tests`, and `node --check src/vengine/web/app.js`.
4. Include a small portable fixture for behavior that depends on a document format or platform. Do not use files from a maintainer's home directory as required test inputs.
5. Document changes to `vengine.toml`, the plugin API, database migrations, and the browser API.
6. Keep imported and generated content in review. Answer keys and hidden cases must stay out of pre-submit responses.

The visual direction is quiet and task-focused: no filler captions or persistent system copy. Menu labels remain readable and use subtle accent glyphs; keyboard focus and error messages remain visible when needed.
