"""Narrow ports owned by model-settings management."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from story_game.application.llm import GenerationTask

from .models import (
    ModelCandidate,
    ModelSettingVersion,
    NewModelSettingVersion,
    TaskModelSetting,
)


class ModelSettingsStoreError(Exception):
    """Base failure exposed by the model-settings persistence ports."""


class ModelSettingsSourceError(Exception):
    """The shipped catalog or original settings cannot be read."""


class ModelCatalog(Protocol):
    """The models the project's catalog offers, per task."""

    def candidates(self) -> tuple[ModelCandidate, ...]: ...


class ModelSettingsOriginals(Protocol):
    """The shipped per-task settings: what is seeded and what a reset restores."""

    def originals(self) -> tuple[TaskModelSetting, ...]: ...


class ModelSettingsReader(Protocol):
    def list_active(self) -> tuple[ModelSettingVersion, ...]: ...

    def list_history(self, task: GenerationTask) -> tuple[ModelSettingVersion, ...]:
        """Every version of one task's setting, newest first."""
        ...


class ModelSettingsWriter(Protocol):
    def append_versions(
        self, versions: Sequence[NewModelSettingVersion]
    ) -> tuple[ModelSettingVersion, ...]:
        """Atomically deactivate each task's current version and insert the new ones."""
        ...


__all__ = [
    "ModelCatalog",
    "ModelSettingsOriginals",
    "ModelSettingsReader",
    "ModelSettingsSourceError",
    "ModelSettingsStoreError",
    "ModelSettingsWriter",
]
