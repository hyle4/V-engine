"""Conservative original-exam extraction and validated assistant handoff."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import (
    BooleanSpec,
    ChoiceSpec,
    ContentBlock,
    DocumentIR,
    ExerciseRevision,
    Option,
    PassageRevision,
    RubricSpec,
    SourceRef,
)

QUESTION = re.compile(r"(?im)^\s*(?:quest(?:ã|a)o|question|item)\s*(\d{1,3})\s*[.):\-]?\s*")
OPTION = re.compile(r"(?im)^\s*([A-H])\s*[).:\-]\s*(.+)$")
RANGE = re.compile(r"(?i)(?:quest[õo]es|itens|questions)\s*(\d{1,3})\s*(?:a|até|to|through|-)\s*(\d{1,3})")
PASSAGE = re.compile(r"(?im)^\s*(?:(?:texto|text)\s+(?:[IVXLCDM]+|\d+|[A-Z0-9-]{3,})|leia\s+o\s+texto|read\s+the\s+text)\b")
KEY = re.compile(r"(?im)(?:^|\s)(?:quest(?:ã|a)o\s*)?(\d{1,3})\s*[-.:)]?\s*([A-H])(?=\s|$)")
GROUP_HEADING = re.compile(r"(?im)^\s*QUESTÃO\s+(\d{1,3})\s*$")
GROUP_ITEM = re.compile(r"(?m)^([1-4])\s+(?=\S)")
TEXT_HEADING = re.compile(r"(?im)^Texto\s+([IVXLCDM]+|\d+)\s*$")


class ExamPassage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1)
    title: str = ""
    text: str = Field(min_length=20)
    page: int = Field(ge=1)
    questions: list[int] = Field(default_factory=list)


class ExamQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: int = Field(ge=1)
    item: int | None = Field(default=None, ge=1, le=4)
    prompt: str = Field(min_length=5)
    page: int = Field(ge=1)
    options: dict[str, str] = Field(default_factory=dict)
    answer: str | None = None
    passage_key: str | None = None

    @model_validator(mode="after")
    def valid_options(self):
        if any(not re.fullmatch("[A-H]", key) or not value.strip()
               for key, value in self.options.items()):
            raise ValueError("options need distinct A-H letters and nonempty text")
        if self.item is not None and self.options:
            raise ValueError("C/E items cannot have lettered options")
        if self.item is not None and self.answer not in {None, "C", "E", "X"}:
            raise ValueError("C/E item answer must be C, E, or X")
        if self.item is None and self.answer and self.answer not in self.options:
            raise ValueError("answer must match one option")
        return self


class ExamBundle(BaseModel):
    """vengine-exam.v1: reviewable, original-only transcription."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1)
    passages: list[ExamPassage] = Field(default_factory=list)
    questions: list[ExamQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_bindings(self):
        numbers = [(q.number, q.item) for q in self.questions]
        keys = [p.key for p in self.passages]
        if len(numbers) != len(set(numbers)) or len(keys) != len(set(keys)):
            raise ValueError("question numbers and passage keys must be unique")
        known = set(keys)
        if any(q.passage_key and q.passage_key not in known for q in self.questions):
            raise ValueError("question cites unknown passage")
        if any(q.passage_key and q.number not in next(p.questions for p in self.passages
                                                       if p.key == q.passage_key)
               for q in self.questions):
            raise ValueError("question/passage binding disagrees with passage range")
        return self


def answer_key(document: DocumentIR | None) -> dict[int | tuple[int, int], str]:
    if document is None:
        return {}
    result: dict[int | tuple[int, int], str] = {}
    ambiguous: set[int] = set()
    for page in document.pages:
        raw = "\n".join(block.text for block in page.blocks)
        # Some official Cebraspe PDFs emit the 4-column answer grid before
        # the question headers in their text layer. Only accept a complete grid.
        if "GABARITOS OFICIAIS" in raw:
            before = raw.split("GABARITOS OFICIAIS", 1)[0]
            grid = re.findall(r"[CEX]", before)
            headings = [int(value) for value in re.findall(r"Questão\s+(\d+)", raw)]
            if (len(headings) > 1 and len(headings) == len(set(headings))
                    and len(grid) == len(headings) * 4):
                for offset, number in enumerate(headings):
                    for item in range(1, 5):
                        result[(number, item)] = grid[offset * 4 + item - 1]
                continue
        for match in KEY.finditer(raw):
            number, letter = int(match[1]), match[2].upper()
            if number in ambiguous:
                continue
            if number in result and result[number] != letter:
                result.pop(number, None)
                ambiguous.add(number)
            else:
                result[number] = letter
    return result


def extract_originals(document: DocumentIR) -> ExamBundle:
    """Extract clear numbered items only; uncertain material stays in the source file."""
    grouped = _extract_ce_groups(document)
    if grouped is not None:
        return grouped
    questions: list[ExamQuestion] = []
    passages: list[ExamPassage] = []
    pending: tuple[str, str, int, list[int]] | None = None
    for page in document.pages:
        body = "\n\n".join(block.text for block in page.blocks)
        matches = list(QUESTION.finditer(body))
        preface = body[:matches[0].start()] if matches else body
        def remember_passage(raw: str, page_number: int = page.number):
            marker = PASSAGE.search(raw)
            if not marker:
                return None
            passage_text = raw[marker.start():].strip()
            range_match = RANGE.search(passage_text)
            if not range_match or len(passage_text) < 20:
                return None
            start, end = int(range_match[1]), int(range_match[2])
            if not start <= end <= start + 100:
                return None
            scope = list(range(start, end + 1))
            key = f"page-{page_number}-{start}-{end}"
            passages.append(ExamPassage(key=key, title=passage_text.splitlines()[0][:100],
                                        text=passage_text, page=page_number, questions=scope))
            return (key, passage_text, page_number, scope)

        pending = remember_passage(preface) or pending
        for index, match in enumerate(matches):
            tail = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            section = body[match.end():tail].strip()
            # A passage after the current item belongs to subsequent question numbers.
            next_passage = PASSAGE.search(section)
            following = None
            if next_passage and next_passage.start() > 0:
                following = section[next_passage.start():]
                section = section[:next_passage.start()].strip()
            number = int(match[1])
            options = {m[1].upper(): m[2].strip() for m in OPTION.finditer(section)}
            prompt = OPTION.split(section, maxsplit=1)[0].strip() if options else section
            if len(prompt) < 5:
                continue
            linked = pending[0] if pending and number in pending[3] else None
            questions.append(ExamQuestion(number=number, prompt=prompt, options=options,
                                          page=page.number, passage_key=linked))
            if following:
                pending = remember_passage(following) or pending
    if not questions:
        raise ValueError("No clear numbered questions found; use structured exam import")
    # Repeated page headers can repeat question numbers; require explicit resolution.
    return ExamBundle(title=document.title.rsplit(".", 1)[0], passages=passages,
                      questions=questions)


def _extract_ce_groups(document: DocumentIR) -> ExamBundle | None:
    """Recognize complete four-assertion C/E groups without guessing item boundaries."""
    chunks = []
    for page in document.pages:
        raw = "\n".join(block.text for block in page.blocks)
        raw = re.sub(r"(?im)^CESPE\s*\|\s*CEBRASPE[^\n]*\n?", "", raw)
        chunks.append((page.number, raw))
    body = "\n".join(chunk for _, chunk in chunks)
    headings = list(GROUP_HEADING.finditer(body))
    if len(headings) < 2:
        return None
    page_starts = []
    offset = 0
    for page, chunk in chunks:
        page_starts.append((offset, page))
        offset += len(chunk) + 1

    def page_at(position: int) -> int:
        return next(page for start, page in reversed(page_starts) if start <= position)

    passages: list[ExamPassage] = []
    passage_keys: dict[str, str] = {}

    def take_passage(raw: str, position: int) -> None:
        marker = TEXT_HEADING.search(raw)
        if not marker:
            return
        text = raw[marker.start():].strip()
        if len(text) < 20:
            return
        name = marker[1].upper()
        key = f"text-{name}"
        if key in passage_keys.values():
            raise ValueError(f"Duplicate shared text {name}; use structured exam import")
        passage_keys[name] = key
        passages.append(ExamPassage(key=key, title=f"Texto {name}", text=text,
                                    page=page_at(position + marker.start()), questions=[]))

    take_passage(body[:headings[0].start()], 0)
    questions: list[ExamQuestion] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        section = body[heading.end():end]
        # A new shared text after item 4 belongs to the following groups.
        passage_marker = TEXT_HEADING.search(section)
        question_section = section[:passage_marker.start()] if passage_marker else section
        if passage_marker:
            take_passage(section[passage_marker.start():], heading.end() + passage_marker.start())
        markers = list(GROUP_ITEM.finditer(question_section))
        if [int(marker[1]) for marker in markers] != [1, 2, 3, 4]:
            return None
        stem = question_section[:markers[0].start()].strip()
        if len(stem) < 5:
            return None
        number = int(heading[1])
        mention = re.search(r"(?i)\btexto\s+([IVXLCDM]+|\d+)\b", stem)
        passage_key = passage_keys.get(mention[1].upper()) if mention else None
        if mention and not passage_key:
            return None
        for item_index, marker in enumerate(markers):
            item_end = markers[item_index + 1].start() if item_index < 3 else len(question_section)
            statement = question_section[marker.end():item_end].strip()
            if len(statement) < 5:
                return None
            questions.append(ExamQuestion(number=number, item=item_index + 1,
                                          prompt=f"{stem}\n\n{statement}",
                                          page=page_at(heading.start()),
                                          passage_key=passage_key))
    for passage in passages:
        passage.questions.extend(sorted({q.number for q in questions
                                         if q.passage_key == passage.key}))
    return ExamBundle(title=document.title.rsplit(".", 1)[0], passages=passages,
                      questions=questions)


def propose_bundle(bundle: ExamBundle, document: DocumentIR, collection_id: str,
                   job_id: str, *, answers: DocumentIR | None = None,
                   subject: str = "General") -> tuple[list[PassageRevision], list[ExerciseRevision]]:
    pages = {page.number: "\n\n".join(block.text for block in page.blocks)
             for page in document.pages}
    key_map = answer_key(answers)
    answer_pages = {page.number: "\n".join(block.text for block in page.blocks)
                    for page in answers.pages} if answers else {}
    passage_revisions: list[PassageRevision] = []
    passage_by_key: dict[str, PassageRevision] = {}
    for passage in bundle.passages:
        if passage.page not in pages:
            raise ValueError(f"Passage {passage.key} has an invalid source page")
        ref = SourceRef(source_id=document.source_id, page=passage.page,
                        quote=passage.text[:300] if passage.text in pages[passage.page]
                        else pages[passage.page][:300])
        stable = uuid5(NAMESPACE_URL, f"vengine:passage:{job_id}:{passage.key}").hex
        item = PassageRevision(id=uuid5(NAMESPACE_URL, stable + ":1").hex,
                               passage_id=stable, collection_id=collection_id,
                               title=passage.title,
                               blocks=[ContentBlock(text=passage.text, source=ref)], sources=[ref])
        passage_revisions.append(item)
        passage_by_key[passage.key] = item
    exercises: list[ExerciseRevision] = []
    for question in bundle.questions:
        if question.page not in pages:
            raise ValueError(f"Question {question.number} has an invalid source page")
        raw_page = pages[question.page]
        statement = question.prompt.split("\n\n")[-1]
        excerpt = statement[:150] if statement in raw_page else (
            question.prompt[:150] if question.prompt in raw_page else raw_page[:150])
        ref = SourceRef(source_id=document.source_id, page=question.page, quote=excerpt)
        notes = ["Check original wording, options, answer, and source before approval."]
        if question.prompt not in raw_page and statement not in raw_page:
            notes.append("Prompt does not exactly match extracted page text; compare with the original.")
        official = key_map.get((question.number, question.item) if question.item else question.number)
        answer = question.answer
        if official and answer and official != answer:
            answer = None
            notes.append("Structured answer conflicts with official key; resolve manually.")
        elif official:
            answer = official
        if answer and question.item is None and answer not in question.options:
            answer = None
            notes.append("Answer letter has no matching option.")
        answer_ref = None
        if official and answer == official and answers and question.item is None:
            match = next(((number, item.group().strip())
                          for number, text in answer_pages.items() for item in KEY.finditer(text)
                          if int(item[1]) == question.number and item[2].upper() == official), None)
            if match:
                answer_ref = SourceRef(source_id=answers.source_id, page=match[0], quote=match[1])
        if official and answer == official and answers and question.item is not None:
            answer_ref = SourceRef(source_id=answers.source_id, page=1,
                                   quote=f"Questão {question.number}")
        if question.options:
            spec = ChoiceSpec(options=[Option(id=letter, blocks=[ContentBlock(text=value)])
                                       for letter, value in question.options.items()],
                              correct=[answer] if answer else [])
            if not answer:
                notes.append("Answer unresolved; this item cannot be approved yet.")
        elif question.item is not None:
            spec = BooleanSpec(correct=True if answer == "C" else False if answer == "E" else None)
            if answer == "X":
                notes.append("Official key annuls this item; leave it out of scored practice.")
            elif not answer:
                notes.append("Answer unresolved; this item cannot be approved yet.")
        else:
            spec = RubricSpec()
        passage = passage_by_key.get(question.passage_key or "")
        exercises.append(ExerciseRevision(
            collection_id=collection_id,
            label=f"{question.number}.{question.item}" if question.item else str(question.number),
            title=f"Question {question.number}.{question.item}" if question.item else f"Question {question.number}",
            subject=subject,
            prompt=[ContentBlock(text=question.prompt, source=ref)],
            contexts=passage.blocks if passage else [],
            passage_id=passage.passage_id if passage else None,
            passage_revision_id=passage.id if passage else None,
            interaction=spec, sources=[ref], answer_source=answer_ref,
            answer_origin="official" if answer_ref else "author" if answer else "unknown",
            status="needs_review", review_notes=notes,
            metadata={"boolean_labels": {"true": "Certo", "false": "Errado"}}
            if question.item is not None else {},
        ))
    return passage_revisions, exercises


def ingest_structured(store, bundle_path: Path, source_path: Path, *,
                      answer_path: Path | None = None, subject: str = "General") -> dict[str, int | str]:
    """Import a reviewed transcription through normal source and revision storage."""
    from . import documents

    raw = Path(bundle_path).read_bytes()
    bundle = ExamBundle.model_validate_json(raw)
    source = store.add_source(source_path, documents.media_type(source_path))
    document = store.document(source["id"])
    if document is None:
        document = documents.parse(Path(source["path"]), source["id"], source["name"])
        store.save_document(document)
    answers = None
    if answer_path:
        key_source = store.add_source(answer_path, documents.media_type(answer_path))
        answers = store.document(key_source["id"])
        if answers is None:
            answers = documents.parse(Path(key_source["path"]), key_source["id"],
                                      key_source["name"])
            store.save_document(answers)
    identity = hashlib.sha256(source["sha256"].encode() + raw).hexdigest()
    collection_id = uuid5(NAMESPACE_URL, f"vengine:collection:{identity}").hex
    store.create_collection(bundle.title, collection_id=collection_id)
    passages, exercises = propose_bundle(bundle, document, collection_id, identity,
                                         answers=answers, subject=subject)
    for passage in passages:
        if store.latest_passage(passage.passage_id) is None:
            store.save_passage(passage)
    added = 0
    revised = 0
    for item in exercises:
        stable = uuid5(NAMESPACE_URL, f"vengine:exam:{identity}:{item.label}").hex
        prior = store.latest(stable)
        if prior is not None:
            if item.answer_source and (prior.answer_source != item.answer_source or
                                       prior.interaction.kind == "choice" and
                                       prior.interaction.correct != item.interaction.correct):
                store.revise(stable, {
                    "interaction": prior.interaction.model_copy(update={
                        "correct": item.interaction.correct}).model_dump(mode="json"),
                    "answer_source": item.answer_source.model_dump(mode="json"),
                    "answer_origin": "official",
                })
                revised += 1
            continue
        store.save_revision(item.model_copy(update={"exercise_id": stable}))
        added += 1
    return {"collection_id": collection_id, "questions": added, "revised": revised,
            "passages": len(passages)}
