"""Trusted, project-local grading extensions for subject-specific interactions."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .models import GradeResult, PluginSpec

if TYPE_CHECKING:
    from pathlib import Path

    from .ai import ProposalBatch
    from .models import DocumentIR, ExerciseRevision

Grader = Callable[[PluginSpec, Any], GradeResult]
_graders: dict[str, Grader] = {}
_parsers: dict[str, Callable[[Path, str, str], DocumentIR]] = {}
_proposers: dict[str, Callable[[DocumentIR, str], list[ExerciseRevision]]] = {}
_ai_providers: dict[str, Callable[[str], ProposalBatch]] = {}
_loaded = False


def register_grader(name: str, grader: Grader) -> None:
    if not name or name in _graders:
        raise ValueError(f"Duplicate or empty plugin name: {name}")
    _graders[name] = grader


def register_parser(suffix: str, parser: Callable[[Path, str, str], DocumentIR]) -> None:
    suffix = suffix.lower()
    if not suffix.startswith(".") or suffix in _parsers:
        raise ValueError(f"Duplicate or invalid parser suffix: {suffix}")
    _parsers[suffix] = parser


def register_proposer(name: str, proposer: Callable[[DocumentIR, str], list[ExerciseRevision]]) -> None:
    if not name or name == "builtin" or name in _proposers:
        raise ValueError(f"Duplicate or invalid proposer name: {name}")
    _proposers[name] = proposer


def parser_for(suffix: str) -> Callable[[Path, str, str], DocumentIR] | None:
    load_plugins()
    return _parsers.get(suffix.lower())


def supported_extensions() -> set[str]:
    load_plugins()
    return set(_parsers)


def propose(name: str, document: DocumentIR, collection_id: str) -> list[ExerciseRevision]:
    load_plugins()
    if name not in _proposers:
        raise ValueError(f"Unknown proposal adapter: {name}")
    return _proposers[name](document, collection_id)


def proposer_names() -> list[str]:
    load_plugins()
    return ["builtin", *sorted(_proposers)]


def register_ai_provider(name: str, generate: Callable[[str], ProposalBatch]) -> None:
    if not name or name in {"gemini", "agy", "none", "auto"} or name in _ai_providers:
        raise ValueError(f"Duplicate or invalid AI provider: {name}")
    _ai_providers[name] = generate


def ai_provider_for(name: str) -> Callable[[str], ProposalBatch] | None:
    load_plugins()
    return _ai_providers.get(name)


def ai_provider_names() -> list[str]:
    load_plugins()
    return ["gemini", "agy", *sorted(_ai_providers)]


def load_plugins() -> None:
    global _loaded
    if _loaded:
        return
    for name in filter(None, (part.strip() for part in
                              os.environ.get("VENGINE_PLUGIN_MODULES", "").split(","))):
        module = importlib.import_module(name)
        module.register(register_grader)
    _loaded = True


def grade_plugin(spec: PluginSpec, response: Any) -> GradeResult:
    load_plugins()
    grader = _graders.get(spec.plugin)
    if grader is None:
        return GradeResult(outcome="error", feedback=f"Plugin {spec.plugin!r} is not installed.")
    return GradeResult.model_validate(grader(spec, response))
