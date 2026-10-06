"""Split mixed exam prompts into original spans. Never paraphrase the source text."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import ExerciseRevision

Role = Literal["instructions", "scoring", "banner", "heading", "stimulus", "task"]
ROLES = ("instructions", "scoring", "banner", "heading", "stimulus", "task")

INSTRUCTION = re.compile(r"(?i)nesta prova,\s*fa[cç]a o que se pede|in this (?:test|exam),?\s*do what is asked")
SCORING = re.compile(
    r"(?i)em cada uma das quest(?:õ|o)es discursivas|dom[ií]nio do conte[uú]do|pontua[cç][aã]o corresponder[aá]")
BANNER = re.compile(
    r"(?im)(?:--\s*prova escrita de [^-\n]{1,80}\s*--"
    r"|^\s*prova escrita de [^\n]{1,60}?(?=\s*(?:quest(?:ã|a)o|question)\s+\d|\n|$))")
TASK = re.compile(
    r"(?i)\b(?:considerando|redija|discorra|disserte|elabore|"
    r"escreva um texto(?:\s+dissertativo)?|write (?:a|an) (?:text|essay))\b")
RULES = re.compile(
    r"(?i)(?:nesta prova|fa[cç]a o que se pede|rascunho|caderno de textos|caneta esferogr|"
    r"desconsiderad|texto definitivo|folha\(s\)|ser[aã]o apenad|corre[cç][aã]o gramatical|"
    r"dom[ií]nio do conte[uú]do|extens[aã]o m[aá]xima|\[valor\s*:|\[value\s*:|"
    r"valor m[aá]ximo de|m[aá]ximo de\s+\d|prova escrita de|"
    r"quest(?:õ|o)es discursivas|pontua[cç][aã]o corresponder)")
HEADING = re.compile(r"(?i)\b(?:quest(?:ã|a)o|question)\s+\d{1,3}\b")
PAGE_HEADER = re.compile(r"(?im)(?:^\s*concurso p[úu]blico\b|p[áa]gina\s+\d+\s*/\s*\d+)")
EXCERPT = re.compile(r"(?i)leia,?\s+com aten[cç][aã]o,?\s+o(?:s)? excerto")
LINE_LIMIT = re.compile(r"(?im)^\s*(?:extens[aã]o do texto\s*:|\[(?:valor|value)\s*:)")
BULLET = re.compile(r"(?m)^[\s]*[•]\s+\S")


class PromptPart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role
    text: str


class Organization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confidence: Literal["high", "review"]
    parts: list[PromptPart] = Field(default_factory=list)
    reason: str = ""


class Span(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class SpanSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spans: list[Span] = Field(min_length=1)


class QuotePart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role
    text: str = Field(min_length=1)


class QuoteSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parts: list[QuotePart] = Field(min_length=1)


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def prompt_text(item: ExerciseRevision) -> str:
    return "\n\n".join(block.text or "" for block in item.prompt)


def parts_match(original: str, parts: list[dict[str, Any]]) -> bool:
    try:
        texts = [str(part["text"]) for part in parts]
        roles = [str(part["role"]) for part in parts]
    except (KeyError, TypeError):
        return False
    if not texts or any(role not in ROLES for role in roles) or "task" not in roles:
        return False
    return normalize("".join(texts)) == normalize(original)


def segment(text: str) -> Organization:
    """Partition one prompt with the recognition protocols."""
    original = text or ""
    if not original.strip():
        return Organization(confidence="review", reason="empty")
    excerpt = _excerpt_regions(original)
    parts = _stitch(original, excerpt) if excerpt else None
    if parts is not None and _split([part.model_dump() for part in parts]) and not _cover_in_task(parts):
        return Organization(confidence="high", parts=parts, reason="protocol")
    if not _marked(original):
        return Organization(confidence="high", parts=[PromptPart(role="task", text=original)], reason="plain")
    regions = _regions(original)
    parts = _stitch(original, regions) if regions is not None else None
    if parts is None or not any(part.role == "task" and part.text.strip() for part in parts):
        return Organization(confidence="review", reason="unseparated")
    if any(part.role == "task" and INSTRUCTION.search(part.text) for part in parts):
        return Organization(confidence="review", reason="cover in task")
    return Organization(confidence="high", parts=parts, reason="protocol")


def for_practice(item: ExerciseRevision) -> list[dict[str, Any]] | None:
    """Stored spans win. Otherwise return a deterministic split. Never calls a model."""
    original = prompt_text(item)
    stored = item.metadata.get("organization")
    if isinstance(stored, list) and parts_match(original, stored) and _split(stored):
        return stored
    result = segment(original)
    if result.confidence != "high" or not _split([part.model_dump() for part in result.parts]):
        return None
    return [part.model_dump() for part in result.parts]


def ask_agy(text: str) -> Organization:
    """Ask the agy CLI for verbatim parts. Reject any wording it changes."""
    if not shutil.which("agy"):
        return Organization(confidence="review", reason="agy unavailable")
    prompt = (
        "Do not use tools or commands, and do not inspect local files. "
        "Segment this single exam prompt by copying each part verbatim. "
        "Do not rewrite, translate, correct, summarize, or add words. "
        "Roles are only instructions, scoring, banner, heading, stimulus, and task. "
        "instructions holds booklet rules such as rascunho, caderno, and caneta, "
        "or a lead-in such as Leia, com atenção, o excerto. "
        "scoring holds point values and line limits, including Extensão do texto and [valor:]. "
        "banner holds a PROVA ESCRITA heading or a running header such as CONCURSO PÚBLICO, TIPO, and PÁGINA n/n. "
        "heading holds Questão N. "
        "stimulus holds the passage or quotation and its citation. "
        "task holds the command the candidate must answer, including the required topics and bullet lines. "
        "Omit roles that are absent. Keep every word in exactly one part, in order.\n\n"
        "PROMPT:\n" + text)
    command = ["agy", "-p", prompt, "--output-format", "json", "--json-schema",
               json.dumps(QuoteSet.model_json_schema()), "--sandbox", "--disable-slash-commands",
               "--print-timeout", "120s"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=135, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Organization(confidence="review", reason=str(exc)[:200])
    if result.returncode:
        return Organization(confidence="review", reason="agy failed")
    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "structured_output" in data:
            data = data["structured_output"]
        elif isinstance(data, dict) and "response" in data:
            data = data["response"]
            if isinstance(data, str):
                data = json.loads(data)
        parts = _parts_from_agy(text, data)
    except (json.JSONDecodeError, ValueError):
        return Organization(confidence="review", reason="agy returned invalid JSON")
    if parts is None or not _split([part.model_dump() for part in parts]):
        return Organization(confidence="review", reason="agy parts do not match the prompt")
    if INSTRUCTION.search(text) and not any(part.role == "instructions" for part in parts):
        return Organization(confidence="review", reason="agy left the cover rules in the question")
    if any(part.role == "task" and INSTRUCTION.search(part.text) for part in parts):
        return Organization(confidence="review", reason="agy left the cover rules in the task")
    return Organization(confidence="high", parts=parts, reason="agy")


def _parts_from_agy(text: str, data: Any) -> list[PromptPart] | None:
    if isinstance(data, dict) and "spans" in data:
        spans = SpanSet.model_validate(data)
        return _stitch(text, [(span.start, span.end, span.role) for span in spans.spans])
    quotes = QuoteSet.model_validate(data)
    return bind_quotes(text, quotes.parts)


def bind_quotes(original: str, quotes: list[QuotePart]) -> list[PromptPart] | None:
    """Map verbatim copies back onto the original string, in order."""
    cursor = 0
    spans: list[tuple[int, int, str]] = []
    for quote in quotes:
        found = _locate(original, quote.text, cursor)
        if found is None:
            return None
        start, end = found
        spans.append((start, end, quote.role))
        cursor = end
    return _stitch(original, spans)


def organize_store(store, *, apply: bool, resolve: Callable[[str], Organization] | None = None,
                   every_marked: bool = False,
                   on_item: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Classify every latest exercise. Apply only exact, high-confidence partitions."""
    report: dict[str, Any] = {"organized": 0, "unchanged": 0, "uncertain": 0, "applied": 0, "items": []}
    offset = 0
    while True:
        page = store.list_exercises(limit=500, offset=offset)
        for item in page:
            text = prompt_text(item)
            marked = _marked(text) or _open_mixed(text)
            result = segment(text)
            consulted = False
            if resolve is not None and _agy_candidate(item, text, result) and (
                    every_marked or result.confidence != "high"):
                result = resolve(text)
                consulted = True
            split = result.confidence == "high" and _split([part.model_dump() for part in result.parts])
            bucket = "organized" if split else "uncertain" if marked else "unchanged"
            parts = [part.model_dump() for part in result.parts] if split else []
            applied = False
            if apply and split:
                store.set_organization(item.exercise_id, parts)
                applied = True
                report["applied"] += 1
            report[bucket] += 1
            entry = {
                "exercise_id": item.exercise_id,
                "label": item.label,
                "confidence": result.confidence,
                "reason": result.reason,
                "roles": [part.role for part in result.parts] if split else [],
                "parts": parts,
                "applied": applied,
                "consulted": consulted,
            }
            report["items"].append(entry)
            if on_item is not None:
                on_item(entry)
        if len(page) < 500:
            break
        offset += len(page)
    return report


def _locate(original: str, quote: str, cursor: int) -> tuple[int, int] | None:
    tokens = normalize(quote).split()
    if not tokens:
        return None
    pattern = r"\s+".join(re.escape(token) for token in tokens)
    match = re.search(pattern, original[cursor:])
    if match is None:
        return None
    return cursor + match.start(), cursor + match.end()


def _is_cover(paragraph: str) -> bool:
    return bool(INSTRUCTION.search(paragraph) or SCORING.search(paragraph)
                or RULES.search(paragraph) or BANNER.search(paragraph))


def _marked(text: str) -> bool:
    return bool(INSTRUCTION.search(text) or SCORING.search(text) or BANNER.search(text))


def _open_mixed(text: str) -> bool:
    """A discursive prompt with a header, excerpt, topics, or a long Questão passage."""
    if PAGE_HEADER.search(text) or EXCERPT.search(text) or BULLET.search(text) or LINE_LIMIT.search(text):
        return True
    if _marked(text):
        return True
    heading = HEADING.search(text)
    return bool(heading and len(text) - heading.end() > 400)


def _cover_in_task(parts: list[PromptPart]) -> bool:
    return any(part.role == "task" and INSTRUCTION.search(part.text) for part in parts)


def _agy_candidate(item: ExerciseRevision, text: str, result: Organization) -> bool:
    """Open-response prompts the protocol did not already separate."""
    if getattr(item.interaction, "kind", None) != "rubric":
        return False
    if result.confidence == "high" and _split([part.model_dump() for part in result.parts]):
        return False
    if result.reason == "plain" and not _open_mixed(text):
        return False
    return True


def _excerpt_regions(text: str) -> list[tuple[int, int, str]] | None:
    """Split a running header, excerpt, writing command, and line limit."""
    if not (PAGE_HEADER.search(text) or EXCERPT.search(text)):
        return None
    heading = HEADING.search(text)
    if heading is None:
        return None
    task = TASK.search(text, heading.end())
    if task is None:
        return None
    cuts: list[tuple[int, str, int | None]] = []
    if text[:heading.start()].strip():
        cuts.append((0, "banner", heading.start()))
    cuts.append((heading.start(), "heading", heading.end()))
    stimulus_from = heading.end()
    excerpt = EXCERPT.search(text, heading.end())
    if excerpt is not None and excerpt.start() < task.start():
        start = _snap_line(text, excerpt.start())
        line_end = text.find("\n", excerpt.end())
        end = task.start() if line_end < 0 or line_end > task.start() else line_end
        if start < task.start():
            cuts.append((start, "instructions", end))
            stimulus_from = end
    if text[stimulus_from:task.start()].strip():
        cuts.append((stimulus_from, "stimulus", task.start()))
    score = LINE_LIMIT.search(text, task.start())
    cuts.append((task.start(), "task", score.start() if score else len(text)))
    if score is not None:
        cuts.append((score.start(), "scoring", len(text)))
    return _pack_cuts(text, cuts)


def _split(parts: list[dict[str, Any]]) -> bool:
    roles = {str(part.get("role")) for part in parts}
    return len(parts) > 1 and "task" in roles and bool(roles - {"task"})


def _snap_line(text: str, index: int) -> int:
    line = text.rfind("\n", 0, index)
    line_start = 0 if line < 0 else line + 1
    prefix = text[line_start:index]
    if re.fullmatch(r"[\s•\-*]*", prefix):
        return line_start
    return index


def _remainder_start(text: str, origin: int, limit: int) -> int | None:
    """First line after the cover rules. Wrapped rule lines stay in the cover."""
    cursor = origin
    seen_cover = False
    previous_open = False
    while cursor < limit:
        newline = text.find("\n", cursor, limit)
        end = limit if newline < 0 else newline
        stripped = text[cursor:end].strip()
        if stripped:
            continued = seen_cover and previous_open and stripped[:1].islower()
            cover = _is_cover(stripped) or continued
            if seen_cover and not cover:
                return cursor
            if cover:
                seen_cover = True
                previous_open = stripped[-1] not in ".!?:;"
        if newline < 0:
            return None
        cursor = newline + 1
    return None


def _regions(text: str) -> list[tuple[int, int, str]] | None:
    instruction = INSTRUCTION.search(text)
    scoring = SCORING.search(text)
    banner = BANNER.search(text)
    instruction_start = _snap_line(text, instruction.start()) if instruction else None
    scoring_start = _snap_line(text, scoring.start()) if scoring else None
    banner_end = banner.end() if banner else None
    heading_from = banner_end if banner_end is not None else 0
    if not heading_from and scoring:
        heading_from = scoring.end()
    if not heading_from and instruction:
        heading_from = instruction.end()
    heading = HEADING.search(text, heading_from)
    heading_span = (heading.start(), heading.end()) if heading else None
    task = TASK.search(text, heading_span[1]) if heading_span else None
    if banner and heading_span and banner.end() > heading_span[0]:
        banner_end = heading_span[0]

    cuts: list[tuple[int, str, int | None]] = []
    if instruction_start is not None:
        cuts.append((instruction_start, "instructions", None))
    if scoring_start is not None:
        cuts.append((scoring_start, "scoring", None))
    if banner:
        cuts.append((banner.start(), "banner", banner_end))
    if heading_span:
        cuts.append((heading_span[0], "heading", heading_span[1]))
    if heading_span and task and text[heading_span[1]:task.start()].strip():
        cuts.append((heading_span[1], "stimulus", task.start()))
    if task:
        cuts.append((task.start(), "task", len(text)))
    elif heading_span and text[heading_span[1]:].strip():
        cuts.append((heading_span[1], "task", len(text)))
    elif heading_span is None:
        origin = instruction_start if instruction_start is not None else banner_end
        tail = _remainder_start(text, origin, len(text)) if origin is not None else None
        if tail is not None:
            command = TASK.search(text, tail)
            if command and text[tail:command.start()].strip():
                cuts.append((tail, "stimulus", command.start()))
                cuts.append((command.start(), "task", len(text)))
            else:
                cuts.append((tail, "task", len(text)))

    return _pack_cuts(text, cuts)


def _pack_cuts(text: str, cuts: list[tuple[int, str, int | None]]) -> list[tuple[int, int, str]] | None:
    ordered = sorted(cuts, key=lambda item: item[0])
    resolved: list[tuple[int, int, str]] = []
    for index, (start, role, end) in enumerate(ordered):
        nxt = ordered[index + 1][0] if index + 1 < len(ordered) else len(text)
        if start < 0 or start > len(text) or (resolved and start < resolved[-1][1] and text[resolved[-1][1]:start].strip()):
            return None
        stop = nxt if end is None else end
        if resolved and start < resolved[-1][1]:
            return None
        if stop < start:
            return None
        if stop > nxt and role != "task":
            stop = nxt
        resolved.append((start, min(stop, len(text)), role))
    return resolved


def _stitch(text: str, regions: list[tuple[int, int, str]]) -> list[PromptPart] | None:
    pieces: list[tuple[int, int, str]] = []
    cursor = 0
    for start, end, role in sorted(regions, key=lambda item: item[0]):
        if role not in ROLES or end < start or start < cursor or end > len(text):
            return None
        if start > cursor:
            if text[cursor:start].strip():
                return None
            if pieces:
                prev_start, _, prev_role = pieces[-1]
                pieces[-1] = (prev_start, start, prev_role)
            else:
                start = cursor
        pieces.append((start, end, role))
        cursor = end
    if not pieces:
        return None
    if cursor < len(text):
        if text[cursor:].strip():
            return None
        prev_start, _, prev_role = pieces[-1]
        pieces[-1] = (prev_start, len(text), prev_role)
    parts: list[PromptPart] = []
    for start, end, role in pieces:
        if start == end:
            continue
        if parts and parts[-1].role == role:
            parts[-1] = PromptPart(role=role, text=parts[-1].text + text[start:end])
        else:
            parts.append(PromptPart(role=role, text=text[start:end]))
    joined = "".join(part.text for part in parts)
    if joined != text or not any(part.role == "task" and part.text.strip() for part in parts):
        return None
    return parts
