# Project plugin API

`project_plugins.py` is trusted project code. The generated `app.py` loads it through `VENGINE_PLUGIN_MODULES=project_plugins`. The CLI also loads that file when started with `--project`.

```python
from pathlib import Path

from vengine.models import ContentBlock, DocumentIR, DocumentPage, ExerciseRevision, RubricSpec
from vengine.plugins import register_ai_provider, register_parser, register_proposer


def parse_cards(path: Path, source_id: str, filename: str) -> DocumentIR:
    return DocumentIR(
        source_id=source_id, title=filename, parser="cards", parser_version="1",
        pages=[DocumentPage(number=1, blocks=[ContentBlock(text=path.read_text())])],
    )


def propose_cards(document: DocumentIR, collection_id: str) -> list[ExerciseRevision]:
    return [ExerciseRevision(
        collection_id=collection_id,
        prompt=[ContentBlock(text=document.pages[0].blocks[0].text)],
        interaction=RubricSpec(), status="needs_review",
    )]


def register(register_grader):
    register_parser(".cards", parse_cards)
    register_proposer("cards", propose_cards)
    # register_grader("my-kind", grader) keeps private payloads server-side.
    # register_ai_provider("my-provider", generate_typed_proposal_batch)
```

Set `proposer = "cards"` in the Project view. A registered parser is selected by file suffix. Proposal adapters return review drafts; the engine does not auto-approve them. A custom AI provider receives a bounded source prompt and returns a `ProposalBatch` compatible value. The engine rejects proposals with citations absent from the parsed source.

The v0.3 interfaces are `register_parser(suffix, callable)`, `register_proposer(name, callable)`, `register_ai_provider(name, callable)`, and `register_grader(name, callable)`. Parsers return `DocumentIR`; proposers return `list[ExerciseRevision]`; graders return `GradeResult`. The core validates these values at its boundaries. Keep plugins small and test them against the core version pinned by the project. Original-exam corrections should use the structured transcript contract in [Original exams](ORIGINAL_EXAMS.md) before introducing a new parser.

Plugin interaction specifications may include `public_payload` and `private_payload`. Only the public payload reaches the browser before submission. For new browser controls, use a built-in interaction kind until the renderer extension contract is published; do not inject arbitrary HTML from source documents or plugin payloads.
