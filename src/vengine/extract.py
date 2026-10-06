import json
import re

from .models import (
    ChoiceSpec,
    CodeCase,
    CodeSpec,
    ContentBlock,
    DocumentIR,
    ExerciseRevision,
    Option,
    RubricSpec,
)

QUESTION = re.compile(r"^(?:quest(?:ã|a)o|question|exercise|exerc[ií]cio|item)\s*[#.:\- ]*\d+", re.IGNORECASE)
OPTION = re.compile(r"^\s*([A-Ha-h])\s*[).:-]\s*(.+)", re.DOTALL)


def propose(document: DocumentIR, collection_id: str) -> list[ExerciseRevision]:
    """Segment known question patterns or structured code JSON; otherwise propose manual review exercises.

    Every proposal needs human review.
    """
    proposals: list[ExerciseRevision] = []
    for page in document.pages:
        for block in page.blocks:
            # Check for structured code exercises in JSON.
            raw = block.text.strip()
            if raw.startswith(("[", "{")):
                try:
                    data = json.loads(raw)
                    items = data if isinstance(data, list) else [data]
                    is_code_batch = any(isinstance(x, dict) and "entrypoint" in x and "cases" in x for x in items)
                    if is_code_batch:
                        for item_data in items:
                            if not (isinstance(item_data, dict) and "entrypoint" in item_data and "cases" in item_data):
                                continue
                            parsed_cases = [
                                CodeCase(input=c["input"], expected=c["expected"],
                                         visible=c.get("visible", i < 2), name=c.get("name", f"Case {i+1}"))
                                for i, c in enumerate(item_data.get("cases", [])) if "input" in c and "expected" in c
                            ]
                            prompt_text = item_data.get("prompt") or item_data.get("description") or item_data.get("title", "")
                            spec = CodeSpec(
                                language=item_data.get("language", "python"),
                                protocol=item_data.get("protocol", "function"),
                                entrypoint=item_data["entrypoint"],
                                entrypoint_type=item_data.get("entrypoint_type", "method"),
                                class_name=item_data.get("class_name", "Solution"),
                                starter_code=item_data.get("starter_code", ""),
                                solution_code=item_data.get("solution_code", ""),
                                cases=parsed_cases,
                                difficulty=item_data.get("difficulty"),
                                constraints=item_data.get("constraints", []),
                                tags=item_data.get("tags", []),
                            )
                            proposals.append(ExerciseRevision(
                                collection_id=collection_id,
                                label=str(len(proposals) + 1),
                                title=item_data.get("title", prompt_text.splitlines()[0][:100]),
                                subject=item_data.get("subject", "General"),
                                topics=item_data.get("tags", []),
                                prompt=[ContentBlock(text=prompt_text, source=block.source)],
                                interaction=spec,
                                sources=[block.source] if block.source else [],
                                status="needs_review",
                                review_notes=["Imported code exercise: verify test cases before approval."]
                            ))
                        continue
                except Exception:
                    pass
            sections = re.split(r"(?=^(?:Quest(?:ã|a)o|Question|Exercise|Exerc[ií]cio|Item)\s*\d+)",
                                block.text, flags=re.IGNORECASE | re.MULTILINE)
            for section in sections:
                section = section.strip()
                if len(section) < 12:
                    continue
                lines = section.splitlines()
                option_lines = []
                prompt_lines = []
                for line in lines:
                    found = OPTION.match(line)
                    if found:
                        option_lines.append((found.group(1).upper(), found.group(2).strip()))
                    else:
                        prompt_lines.append(line)
                if len(option_lines) >= 2 and len({x[0] for x in option_lines}) == len(option_lines):
                    interaction = ChoiceSpec(options=[Option(id=key, blocks=[ContentBlock(text=value)])
                                                       for key, value in option_lines])
                    prompt = "\n".join(prompt_lines).strip()
                else:
                    interaction = RubricSpec(criteria=["Review response against the source and rubric."])
                    prompt = section
                if not prompt:
                    continue
                proposals.append(ExerciseRevision(
                    collection_id=collection_id, label=str(len(proposals) + 1),
                    title=prompt.splitlines()[0][:100], prompt=[ContentBlock(
                        text=prompt, source=block.source)], interaction=interaction,
                    sources=[block.source] if block.source else [],
                    status="needs_review", review_notes=["Verify the prompt, answer, and source before approval."]
                ))
    return proposals
