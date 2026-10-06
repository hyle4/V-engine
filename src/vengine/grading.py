"""Deterministic grading; open responses remain explicitly ungraded."""

from __future__ import annotations

import math
import unicodedata
from typing import Any

from pydantic import TypeAdapter, ValidationError

from .models import ExerciseRevision, GradeResult, Interaction


def _normalize(value: Any, case_sensitive: bool = False) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip()
    return " ".join(text.split()) if case_sensitive else " ".join(text.casefold().split())


def grade(item: ExerciseRevision, response: Any, sample_only: bool = False) -> GradeResult:
    spec = item.interaction
    kind = spec.kind
    if sample_only:
        if kind == "code":
            from .runner import run_code
            visible_cases = [c for c in spec.cases if c.visible]
            sample_spec = spec.model_copy(update={"cases": visible_cases if visible_cases else spec.cases[:1]})
            return run_code(sample_spec, response)
        return GradeResult(outcome="ungraded", feedback="Sample run only available for code exercises.")
    if kind == "choice":
        if not spec.correct:
            return GradeResult(outcome="ungraded", feedback="No answer key has been reviewed.")
        selected = set(response if isinstance(response, list) else [response])
        valid = {o.id for o in spec.options}
        if not selected <= valid:
            return GradeResult(outcome="error", feedback="Unknown option ID.")
        correct = set(spec.correct)
        if selected == correct:
            return GradeResult(outcome="correct", score=1)
        if spec.multiple and selected:
            score = max(0, (len(selected & correct) - len(selected - correct)) / len(correct))
            if score:
                return GradeResult(outcome="partial", score=score)
        return GradeResult(outcome="incorrect", score=0)
    if kind == "boolean":
        if spec.correct is None:
            return GradeResult(outcome="ungraded", feedback="No answer key has been reviewed.")
        if not isinstance(response, bool):
            return GradeResult(outcome="error", feedback="Expected true or false.")
        passed = response == spec.correct
    elif kind == "text":
        if not spec.accepted:
            return GradeResult(outcome="ungraded", feedback="Review this answer manually.")
        passed = _normalize(response, spec.case_sensitive) in {
            _normalize(x, spec.case_sensitive) for x in spec.accepted}
    elif kind == "numeric":
        if spec.correct is None:
            return GradeResult(outcome="ungraded", feedback="No answer key has been reviewed.")
        try:
            value = float(response)
        except (TypeError, ValueError):
            return GradeResult(outcome="error", feedback="Expected a number.")
        passed = math.isfinite(value) and math.isclose(value, spec.correct,
                              abs_tol=spec.absolute_tolerance, rel_tol=spec.relative_tolerance)
    elif kind == "cloze":
        if not isinstance(response, dict):
            return GradeResult(outcome="error", feedback="Expected gap answers by ID.")
        if not spec.gaps:
            return GradeResult(outcome="ungraded")
        hits = sum(_normalize(response.get(gap.id, "")) in {_normalize(x) for x in gap.accepted}
                   for gap in spec.gaps)
        score = hits / len(spec.gaps)
        return GradeResult(outcome="correct" if score == 1 else "partial" if score else "incorrect",
                           score=score)
    elif kind == "matching":
        if not isinstance(response, dict):
            return GradeResult(outcome="error", feedback="Expected matching pairs by ID.")
        if not spec.pairs:
            return GradeResult(outcome="ungraded")
        hits = sum(response.get(left) == right for left, right in spec.pairs.items())
        score = hits / len(spec.pairs)
        return GradeResult(outcome="correct" if score == 1 else "partial" if score else "incorrect",
                           score=score)
    elif kind == "ordering":
        if not spec.correct_order:
            return GradeResult(outcome="ungraded")
        passed = response == spec.correct_order
    elif kind == "composite":
        if not isinstance(response, list) or len(response) != len(spec.parts) or not spec.parts:
            return GradeResult(outcome="error", feedback="Expected one answer for each part.")
        results = []
        for raw_part, answer in zip(spec.parts, response, strict=True):
            try:
                part = TypeAdapter(Interaction).validate_python(
                    raw_part.get("interaction", raw_part))
            except (ValidationError, AttributeError, TypeError):
                return GradeResult(outcome="error", feedback="Invalid composite part.")
            results.append(grade(item.model_copy(update={"interaction": part}), answer))
        details = {"parts": [result.model_dump(mode="json") for result in results]}
        if any(result.outcome == "error" for result in results):
            return GradeResult(outcome="error", details=details)
        if any(result.outcome == "ungraded" for result in results):
            return GradeResult(outcome="ungraded", details=details,
                               feedback="Assess the open-response parts.")
        score = sum(result.score or 0 for result in results) / len(results)
        return GradeResult(outcome="correct" if score == 1 else
                           "incorrect" if score == 0 else "partial",
                           score=score, details=details)
    elif kind == "rubric":
        return GradeResult(outcome="ungraded", feedback="This response awaits manual review.")
    elif kind in {"code", "sql"}:
        from .runner import run_code
        return run_code(spec, response)
    elif kind == "plugin":
        from .plugins import grade_plugin
        return grade_plugin(spec, response)
    else:
        return GradeResult(outcome="error", feedback="Unsupported interaction.")
    return GradeResult(outcome="correct" if passed else "incorrect", score=float(passed))
