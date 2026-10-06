# Interface audit · 2026-10-03

The browser interface serves one local practice project. Its persistent objects are sources, collections, exercise revisions, attempts, and due cards. The Project view holds only settings a project owner can act on. Import proposals stay in Review until approved.

## Current visual contract

- Primary navigation is plain text with a small accent glyph on the active or focused item. Menu controls have no button background, border, or radius.
- The reading view uses one quiet column; code practice expands into a source and editor split. Review places source evidence beside the editable exercise on wide screens.
- Routine status is announced in the live region without occupying the page. Visible text is reserved for the task, actions, errors, and outcomes.
- Selection, approval, due mode, and result feedback use words as well as color. Keyboard focus remains visible.

## Current evidence

The implementation lives in `src/vengine/web/`. A 1360×900 headless Chromium capture of the clean setup and populated code practice views was inspected on Linux. The JavaScript syntax check passes. The API and data behavior are exercised by the Python suite. The UI now loads registered source formats and proposal adapters from the project API rather than assuming built-in lists.

## Release checks still needed

Desktop and narrow viewports in both themes, keyboard traversal, a screen-reader walkthrough, 200% zoom, reduced motion, long review queues, and live import recovery need manual verification. The release gate is [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). Automated checks do not establish accessibility conformance.
