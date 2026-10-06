"""Validated, portable configuration for one V-engine project."""

from __future__ import annotations

import os
import tempfile
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    name: str = Field(min_length=1, max_length=80)
    subject: str = Field(default="General", min_length=1, max_length=80)
    ai_provider: str = Field(default="auto", pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    ai_count: int = Field(default=8, ge=1, le=30)
    proposer: str = Field(default="builtin", pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    practice_mode: Literal["all", "due"] = "all"
    locale: Literal["en", "pt-BR"] = "en"
    show_project: bool = True
    font: Literal[
        "",
        "JetBrainsMono Nerd Font",
        "iA Writer Mono S",
        "Adwaita Mono",
        "Liberation Sans",
    ] = ""
    text_size: Literal["xs", "sm", "md", "lg"] = "md"
    reading_width: Literal["narrow", "standard"] = "standard"
    library_filters: list[str] = Field(default_factory=list)
    blocked_imports: list[str] = Field(default_factory=list)

    @field_validator("library_filters")
    @classmethod
    def short_filters(cls, values: list[str]) -> list[str]:
        if len(values) > 8:
            raise ValueError("too many library filters")
        cleaned = []
        for value in values:
            text = value.strip()
            if not text or len(text) > 40:
                raise ValueError("library filter must be a short name")
            cleaned.append(text)
        return cleaned

    @field_validator("blocked_imports")
    @classmethod
    def short_blocks(cls, values: list[str]) -> list[str]:
        if len(values) > 24:
            raise ValueError("too many blocked import names")
        cleaned = []
        for value in values:
            text = value.strip()
            if not text or len(text) > 40:
                raise ValueError("blocked import name must be short")
            cleaned.append(text)
        return cleaned


def config_path(project_root: Path) -> Path:
    return Path(project_root).resolve() / "vengine.toml"


_LEETCODE_MARKERS = ("titleslug", "questionfrontendid", "leetcode.com")


def refuses_import(config: ProjectConfig | None, label: str, sample: str = "") -> bool:
    """True when a filename, title, or text sample names material this project does not take."""
    if config is None or not config.blocked_imports:
        return False
    folded = f"{label}\n{sample}".casefold()
    if any(pattern.casefold() in folded for pattern in config.blocked_imports):
        return True
    if any("leetcode" in pattern.casefold() for pattern in config.blocked_imports):
        return any(marker in folded for marker in _LEETCODE_MARKERS)
    return False


def load_project(project_root: Path) -> ProjectConfig | None:
    path = config_path(project_root)
    if not path.exists():
        return None
    with path.open("rb") as handle:
        return ProjectConfig.model_validate(tomllib.load(handle))


def save_project(project_root: Path, config: ProjectConfig) -> Path:
    """Replace a manifest atomically; never put credentials in this file."""
    path = config_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"schema_version = {config.schema_version}\n"
        f"name = {_toml_string(config.name)}\n"
        f"subject = {_toml_string(config.subject)}\n"
        f"ai_provider = {_toml_string(config.ai_provider)}\n"
        f"ai_count = {config.ai_count}\n"
        f"proposer = {_toml_string(config.proposer)}\n"
        f"practice_mode = {_toml_string(config.practice_mode)}\n"
        f"locale = {_toml_string(config.locale)}\n"
        f"show_project = {'true' if config.show_project else 'false'}\n"
        f"font = {_toml_string(config.font)}\n"
        f"text_size = {_toml_string(config.text_size)}\n"
        f"reading_width = {_toml_string(config.reading_width)}\n"
        f"library_filters = [{', '.join(_toml_string(item) for item in config.library_filters)}]\n"
        f"blocked_imports = [{', '.join(_toml_string(item) for item in config.blocked_imports)}]\n"
    )
    fd, temporary = tempfile.mkstemp(prefix=".vengine-", suffix=".toml", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def _toml_string(value: str) -> str:
    # JSON string syntax is also valid TOML basic-string syntax.
    import json

    return json.dumps(value, ensure_ascii=False)
