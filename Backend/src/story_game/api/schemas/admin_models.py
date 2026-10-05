"""Transport shapes for the admin endpoints over the per-task model settings."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from story_game.application.llm import GenerationTask

from .common import APIModel


class ModelSettingModel(APIModel):
    """One stored version of a task's model choice."""

    version_id: UUID
    task: GenerationTask
    model_ref: str = Field(min_length=1)
    temperature: float | None = None
    max_output_tokens: int | None = None
    source: str = Field(min_length=1)
    created_at: datetime
    created_by: str | None = None
    is_active: bool
    is_modified: bool
    """``True`` while the active version is an edit made in the UI."""


class ModelCandidateModel(APIModel):
    """A catalog model selectable for ``task``."""

    task: GenerationTask
    model_ref: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)


class ModelSettingsOverviewModel(APIModel):
    settings: list[ModelSettingModel] = Field(default_factory=list)
    candidates: list[ModelCandidateModel] = Field(default_factory=list)


class ModelSettingVersionListModel(APIModel):
    versions: list[ModelSettingModel] = Field(default_factory=list)


class UpdateModelSettingRequestModel(APIModel):
    task: GenerationTask
    model_ref: str = Field(min_length=1)
    temperature: float | None = None
    max_output_tokens: int | None = None


class ResetModelSettingsRequestModel(APIModel):
    """Name one task, or none to reset every task."""

    task: GenerationTask | None = None
