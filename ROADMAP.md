# Twelve routes to a public V-engine framework

This roadmap tracks release work for a local-first practice framework that can be configured for one learning project per clone. Status is based on this checkout; a route is complete only after its acceptance gate is verified.

| Route | Acceptance gate | Current status |
| --- | --- | --- |
| 1. Framework contract | Document one-project scope, supported surfaces, and advertised capabilities. | Core contract documented; complete release capability matrix remains. |
| 2. Project setup | A coding assistant can create a separate project; the learner sees a name-only setup. | Assistant playbook, generated project instructions, manifest, CLI, and simplified UI added; fresh-clone trial remains. |
| 3. Package boundary | Generated projects depend on a versioned package; old copied projects migrate safely. | Neutral starter depends on `vengine[ai]`; subject-specific applications and migration tools live outside core. Other copied projects still need validation. |
| 4. Extension API | Stable parser, proposer, AI provider, grader, and custom interaction contracts with examples. | Python hooks and docs added; browser renderer extension remains. |
| 5. Source ingestion | Portable format corpus and provenance checks across supported platforms. | Existing parsers and original-exam mode retained; synthetic shared-text/key tests added. Layout, table, formula, and OCR evaluation remain. |
| 6. Durable pipeline | Background, cancel, restart, page resume, and no duplicate proposals. | Background queue and page checkpoints added; crash and cancellation stress tests remain. |
| 7. AI providers | Typed, cited, bounded generation with live provider and usage checks. | Provider registry, request/token counters, and a custom-provider citation/usage test added; live credential tests remain. |
| 8. Human review | Source-adjacent review, shared-text correction, and safe bulk triage. | Source page API, adjacent review pane, passage revision approval, and batch discard added; large-corpus audit remains. |
| 9. Practice | All advertised interactions render and grade consistently, with immutable attempts. | Composite grading and UI added; full interaction browser matrix remains. |
| 10. Execution safety | Container isolation verified for Python, JavaScript, and SQL on supported platforms. | Host execution now requires two developer flags; image readiness checks added. Container integration is unverified. |
| 11. Hygienic interface | No filler/status copy or menu geometry; accessible keyboard and zoom behavior. | Name-only setup and source-text side pane added; manual accessibility and responsive review remain. |
| 12. Public release | MIT, CI, docs, privacy, cross-platform validation, GitHub and PyPI matching artifacts. | AI handoff docs, source archive allowlist, and privacy audit added; external platform and provider validation remain. |

The public 1.0 tag is blocked until every item in [the release checklist](docs/RELEASE_CHECKLIST.md) passes.
