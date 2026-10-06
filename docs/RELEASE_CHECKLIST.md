# Public release gate

Release 1.0 only when all checks below have recorded evidence. A passing unit suite alone is insufficient.

- [ ] Fresh clone and UI setup on Linux, macOS, and Windows with Python 3.12.
- [ ] Wheel and source distribution install without this checkout; generated starter installs the tagged core package.
- [ ] `python scripts/release_audit.py` passes on repository files and rebuilt wheel/source archive; no personal paths, credentials, real exams, or legacy project migration files ship.
- [ ] A fresh assistant follows `AGENTS.md` and the playbook to create a separate project without editing SQLite or committing user files.
- [ ] Original exam import preserves question numbers, alternatives, shared text scopes, and answer-key provenance; ambiguous input remains reviewable.
- [ ] Shared-text correction updates linked current questions and keeps prior attempt revisions intact.
- [ ] PDF, scanned PDF, image, text, Markdown, JSON, and CSV fixtures preserve usable source references across all three platforms.
- [ ] Long import cancellation and restart resume from saved PDF pages without duplicate proposals.
- [ ] Live Gemini and `agy` calls with real credentials, citation rejection, and request/token accounting recorded.
- [ ] Review source view, edit, approval, and published revision continuity verified against a large collection.
- [ ] Every advertised interaction type renders and grades or requests explicit self-assessment, with hidden keys absent before submission.
- [ ] Container Python, JavaScript, and SQL tests verify no network, limits, no host writes, and unavailable-backend errors on supported platforms.
- [ ] Desktop and narrow screenshots in both themes, keyboard traversal, screen-reader walkthrough, 200% zoom, and reduced motion review.
- [ ] Linux Tauri bundle starts and stops its sidecar; desktop availability is described separately from the cross-platform browser app.
- [ ] MIT notice, dependency notices, security reporting, migration instructions, changelog, and release artifacts reviewed.
- [ ] PyPI project ownership and trusted publishing configured; GitHub release and PyPI artifacts correspond to the same tag.

Local evidence (2026-10-03): 34 tests pass, Ruff and browser JavaScript syntax pass, the 0.3.0 wheel and source archive build, and `release_audit.py` reports zero issues across 77 public files and both archives. A synthetic original-exam preview showed its shared text beside the question at desktop width. The official 2017 CACD morning booklet and definitive key were imported in a separate `/tmp` project: 34 groups, 136 assertions, four shared texts, 136 mapped key cells, five annulments, and 136 review drafts. The real-file review UI runs on port 8768. Cross-platform, live-provider, accessibility, large-corpus, and container-host checks remain unverified until run and documented.
