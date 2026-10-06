# Changelog

## 0.3.0 — AI-guided project intake

- Added original-exam import, optional official answer keys, and a validated JSON transcript fallback for difficult layouts.
- Added shared text revisions, source-side practice, and atomic propagation of approved text corrections to linked questions.
- Reduced first-run setup to a project name and added an assistant playbook to the engine and generated starter.
- Restricted source distributions to an explicit file list, added a release privacy audit, and aligned package and desktop versions.
- Moved a historical subject-specific migration utility to its own project; public examples use synthetic data.

## 0.2.0 — framework candidate

- Added one-project configuration, Project view, package-backed starter templates, and parser, proposer, AI provider, and grader hooks.
- Project Subject now applies to new import drafts and is the default for manual creation.
- Moved the earlier subject-specific catalog and app into an independent project; the core generator now creates a neutral starter.
- Added background import jobs with cancellation, restart recovery, PDF page checkpoints, and AI request/token counts.
- Added source-adjacent review, batch discard of drafts, composite practice controls, and a quieter text navigation system.
- Added a database schema 3 checkpoint table and a backup before migration.
- Restricted host code execution to explicit developer mode; container runners now check image availability.
- Added CI and release workflows. The 1.0 release gates remain in `docs/RELEASE_CHECKLIST.md`.

## 0.1.0 — local prototype

- Source import, review, practice, spaced repetition, the browser interface, and the Linux desktop shell.
