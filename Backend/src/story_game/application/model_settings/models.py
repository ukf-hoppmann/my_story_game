"""Values of the versioned per-task model settings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from story_game.application.llm import GenerationTask
from story_game.domain import StableId


class ModelSettingSource(StrEnum):
    """Where one stored version of a task's setting came from."""

    TOML_SEED = "toml_seed"
    UI = "ui"
    TOML_RESET = "toml_reset"


@dataclass(frozen=True, slots=True)
class ModelCandidate:
    """One catalog model the UI may select for ``task``.

    ``model_ref`` is the catalog's logical id; provider and model id are what
    it resolves to for a call.
    """

    task: GenerationTask
    model_ref: str
    provider_id: str
    model_id: str


@dataclass(frozen=True, slots=True)
class TaskModelSetting:
    """The model reference and generation options in force for one task."""

    task: GenerationTask
    model_ref: str
    temperature: float | None
    max_output_tokens: int | None


@dataclass(frozen=True, slots=True)
class NewModelSettingVersion:
    """A version about to be appended; it becomes the active one for its task."""

    version_id: StableId
    setting: TaskModelSetting
    source: ModelSettingSource
    created_at: datetime
    created_by: str | None
    """Name of the editing caller; ``None`` for a seed from the TOML file."""


@dataclass(frozen=True, slots=True)
class ModelSettingVersion:
    """One stored version of a task's setting. History rows are never changed."""

    version_id: StableId
    setting: TaskModelSetting
    source: ModelSettingSource
    created_at: datetime
    created_by: str | None
    is_active: bool


__all__ = [
    "ModelCandidate",
    "ModelSettingSource",
    "ModelSettingVersion",
    "NewModelSettingVersion",
    "TaskModelSetting",
]
