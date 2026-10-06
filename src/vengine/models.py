"""Versioned contracts shared by imports, the UI, and generated applications."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def new_id() -> str:
    return uuid4().hex


def now() -> datetime:
    return datetime.now(UTC)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(Contract):
    source_id: str
    page: int | None = None
    block_id: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    quote: str | None = None


class ContentBlock(Contract):
    id: str = Field(default_factory=new_id)
    kind: Literal["text", "code", "table", "image", "formula", "audio"] = "text"
    text: str = ""
    language: str | None = None
    asset_id: str | None = None
    source: SourceRef | None = None


class DocumentPage(Contract):
    number: int
    blocks: list[ContentBlock] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DocumentIR(Contract):
    source_id: str
    title: str
    pages: list[DocumentPage] = Field(default_factory=list)
    parser: str
    parser_version: str
    language: str | None = None
    warnings: list[str] = Field(default_factory=list)


class Option(Contract):
    id: str
    blocks: list[ContentBlock]


class ChoiceSpec(Contract):
    kind: Literal["choice"] = "choice"
    options: list[Option]
    correct: list[str] = Field(default_factory=list)
    multiple: bool = False

    @model_validator(mode="after")
    def valid_choices(self) -> ChoiceSpec:
        ids = [o.id for o in self.options]
        if len(ids) != len(set(ids)) or not ids:
            raise ValueError("choice option IDs must be unique and nonempty")
        if not set(self.correct).issubset(ids):
            raise ValueError("correct choices must exist in options")
        if not self.multiple and len(self.correct) > 1:
            raise ValueError("single choice has more than one correct option")
        return self


class BooleanSpec(Contract):
    kind: Literal["boolean"] = "boolean"
    correct: bool | None = None


class TextSpec(Contract):
    kind: Literal["text"] = "text"
    accepted: list[str] = Field(default_factory=list)
    case_sensitive: bool = False


class NumericSpec(Contract):
    kind: Literal["numeric"] = "numeric"
    correct: float | None = None
    absolute_tolerance: float = Field(default=0, ge=0)
    relative_tolerance: float = Field(default=0, ge=0)
    unit: str | None = None


class ClozeGap(Contract):
    id: str
    accepted: list[str]


class ClozeSpec(Contract):
    kind: Literal["cloze"] = "cloze"
    gaps: list[ClozeGap]


class MatchingSpec(Contract):
    kind: Literal["matching"] = "matching"
    pairs: dict[str, str]


class OrderingSpec(Contract):
    kind: Literal["ordering"] = "ordering"
    correct_order: list[str]


class RubricSpec(Contract):
    kind: Literal["rubric"] = "rubric"
    criteria: list[str] = Field(default_factory=list)
    sample_answer: str | None = None


class CodeCase(Contract):
    input: Any
    expected: Any
    visible: bool = False
    name: str | None = None


class CodeSpec(Contract):
    kind: Literal["code"] = "code"
    language: Literal["python", "javascript"] = "python"
    protocol: Literal["function", "stdio"] = "function"
    entrypoint: str = "solve"
    entrypoint_type: Literal["function", "method"] = "function"
    class_name: str = "Solution"
    cases: list[CodeCase] = Field(default_factory=list)
    starter_code: str = ""
    solution_code: str = ""
    difficulty: Literal["easy", "medium", "hard"] | None = None
    constraints: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    structure_type: Literal["standard", "linked_list", "tree"] = "standard"


class SQLSpec(Contract):
    kind: Literal["sql"] = "sql"
    setup_sql: str
    reference_query: str
    order_sensitive: bool = False


class CompositeSpec(Contract):
    kind: Literal["composite"] = "composite"
    parts: list[dict[str, Any]] = Field(default_factory=list)


class PluginSpec(Contract):
    kind: Literal["plugin"] = "plugin"
    plugin: str
    public_payload: dict[str, Any] = Field(default_factory=dict)
    private_payload: dict[str, Any] = Field(default_factory=dict)


Interaction = Annotated[
    ChoiceSpec | BooleanSpec | TextSpec | NumericSpec | ClozeSpec | MatchingSpec
    | OrderingSpec | RubricSpec | CodeSpec | SQLSpec | CompositeSpec | PluginSpec,
    Field(discriminator="kind"),
]


class ExerciseRevision(Contract):
    id: str = Field(default_factory=new_id)
    exercise_id: str = Field(default_factory=new_id)
    revision: int = Field(default=1, ge=1)
    collection_id: str | None = None
    label: str = "1"
    title: str = ""
    subject: str = "General"
    topics: list[str] = Field(default_factory=list)
    language: str | None = None
    prompt: list[ContentBlock]
    contexts: list[ContentBlock] = Field(default_factory=list)
    passage_id: str | None = None
    passage_revision_id: str | None = None
    interaction: Interaction
    sources: list[SourceRef] = Field(default_factory=list)
    answer_source: SourceRef | None = None
    explanation: list[ContentBlock] = Field(default_factory=list)
    answer_origin: Literal["official", "author", "ai_proposed", "legacy", "unknown"] = "unknown"
    status: Literal["draft", "needs_review", "approved", "archived"] = "draft"
    review_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now)
    approved_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def approved_has_time(self) -> ExerciseRevision:
        if self.status == "approved" and self.approved_at is None:
            raise ValueError("approved revision requires approved_at")
        return self

    def public_view(self, reveal: bool = False) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        if not reveal:
            secrets = {"correct", "accepted", "pairs", "correct_order", "sample_answer",
                       "reference_query", "private_payload", "answer", "answer_key", "solutions",
                       "solution_code"}

            def redact(value: Any) -> Any:
                if isinstance(value, list):
                    return [redact(part) for part in value]
                if not isinstance(value, dict):
                    return value
                result = {key: redact(part) for key, part in value.items() if key not in secrets}
                if value.get("kind") == "matching":
                    result["left"] = list(value["pairs"])
                    result["right"] = sorted(set(value["pairs"].values()))
                if value.get("kind") == "ordering":
                    result["items"] = sorted(value["correct_order"])
                if value.get("kind") == "code":
                    result["cases"] = [redact(case) for case in value["cases"] if case["visible"]]
                return result

            data["interaction"] = redact(data["interaction"])
            data.pop("answer_source", None)
            data["explanation"] = []
            data["review_notes"] = []
            data["metadata"] = {}
        return data


class PassageRevision(Contract):
    id: str = Field(default_factory=new_id)
    passage_id: str = Field(default_factory=new_id)
    revision: int = Field(default=1, ge=1)
    collection_id: str
    title: str = ""
    blocks: list[ContentBlock]
    sources: list[SourceRef] = Field(default_factory=list)
    status: Literal["needs_review", "approved", "archived"] = "needs_review"
    created_at: datetime = Field(default_factory=now)
    approved_at: datetime | None = None


class GradeResult(Contract):
    outcome: Literal["correct", "incorrect", "partial", "ungraded", "error", "provisional"]
    score: float | None = Field(default=None, ge=0, le=1)
    feedback: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class Attempt(Contract):
    id: str = Field(default_factory=new_id)
    exercise_id: str
    revision_id: str
    response: Any
    grade: GradeResult
    created_at: datetime = Field(default_factory=now)


class ImportJob(Contract):
    id: str = Field(default_factory=new_id)
    source_id: str
    mode: Literal["study", "originals"] = "study"
    answer_source_id: str | None = None
    title: str | None = None
    stage: Literal["queued", "extracting", "generating", "review_ready", "failed", "cancelled"] = "queued"
    progress: float = Field(default=0, ge=0, le=1)
    error: str | None = None
    collection_id: str | None = None
    generate_ai: bool = False
    provider: str = "gemini"
    proposer: str = "builtin"
    subject: str = Field(default="General", min_length=1, max_length=80)
    usage: dict[str, int] = Field(default_factory=dict)
    count: int = Field(default=8, ge=1, le=30)
    proposals_count: int = 0
    created_at: datetime = Field(default_factory=now)
