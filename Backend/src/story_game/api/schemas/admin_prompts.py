"""Transport shapes for the admin endpoints over versioned system prompts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from story_game.application.prompt_management import PromptEntryKind

from .common import APIModel


class PromptVersionModel(APIModel):
    """One stored version of a prompt entry."""

    version_id: UUID
    kind: PromptEntryKind
    key: str = Field(min_length=1)
    text: str = Field(min_length=1)
    is_default: bool
    task_ids: list[str] = Field(default_factory=list)
    source: str = Field(min_length=1)
    created_at: datetime
    created_by: str | None = None
    is_active: bool
    is_modified: bool
    """``True`` while the active version is an edit made in the UI."""
    is_custom: bool = False
    """``True`` for an option added in the UI; it has no shipped original and can be removed."""


class PromptListModel(APIModel):
    package_id: str = Field(min_length=1)
    package_version: str = Field(min_length=1)
    entries: list[PromptVersionModel] = Field(default_factory=list)


class PromptVersionListModel(APIModel):
    versions: list[PromptVersionModel] = Field(default_factory=list)


class UpdatePromptTextRequestModel(APIModel):
    kind: PromptEntryKind
    key: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ResetPromptsRequestModel(APIModel):
    """Name one entry (``kind`` and ``key``), one ``kind``, or nothing for the whole package."""

    kind: PromptEntryKind | None = None
    key: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _key_needs_kind(self) -> ResetPromptsRequestModel:
        if self.key is not None and self.kind is None:
            raise ValueError("key braucht ein kind")
        return self


class CreatePromptOptionRequestModel(APIModel):
    category: str = Field(min_length=1)
    option_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
