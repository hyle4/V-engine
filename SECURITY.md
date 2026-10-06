# Security model

V-engine is a single-user local application. Its HTTP server binds to `127.0.0.1`, accepts only loopback hostnames, and blocks cross-origin writes. It is not an authenticated multi-user service and must not be exposed on a public network.

Imported documents and AI output are untrusted. Source text is escaped before browser insertion; AI proposals require a matching source quotation and human approval. Original-exam imports preserve supplied wording and key provenance; ambiguous items stay in review. Answer-key references are hidden from the pre-submit question response. Approved revisions and attempts are stored with their exact revision identities. Project plugins are trusted Python code and can access the user's files; inspect `project_plugins.py` before running a cloned project.

Submitted Python, JavaScript, and SQL require a checked container backend. The public application does not enable host execution. Host execution needs both `VENGINE_DEV_MODE=1` and `VENGINE_ALLOW_LOCAL_RUNNER=1` and is intended only for tests and trusted local development. Pull runner images explicitly and inspect them before use. `vengine doctor` reports backend readiness.

Keep API keys in environment variables or an external credential store, never in `vengine.toml` or Git. Keep exam files, transcripts, databases, and backups in the project's ignored `data/` directory. Run `python scripts/release_audit.py` on the repository and rebuilt archives before publishing engine artifacts. Back up `data/` before moving between engine versions; pre-v3 and pre-v4 backups are created on migration as applicable.

Report vulnerabilities through the repository's private GitHub vulnerability-reporting feature once enabled. If that feature is unavailable, open an issue requesting a private contact route without including exploit details.
