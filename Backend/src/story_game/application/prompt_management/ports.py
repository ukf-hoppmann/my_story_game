"""Narrow ports owned by prompt management."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from story_game.application.llm import PromptPackageCatalog

from .models import NewPromptVersion, PromptEntryKind, PromptPackageReference, PromptVersion


class PromptStoreError(Exception):
    """Base failure exposed by the prompt-version persistence ports."""


class PromptPackageSource(PromptPackageCatalog, Protocol):
    """The shipped originals (the TOML files): what is seeded and what a reset restores."""

    def references(self) -> tuple[PromptPackageReference, ...]: ...


class PromptVersionReader(Protocol):
    def list_active(
        self, package_id: str, package_version: str
    ) -> tuple[PromptVersion, ...]:
        """Every active entry of the package, tasks then options then directives."""
        ...

    def list_history(
        self,
        package_id: str,
        package_version: str,
        kind: PromptEntryKind,
        key: str,
    ) -> tuple[PromptVersion, ...]:
        """Every version of one entry, newest first."""
        ...


class PromptVersionWriter(Protocol):
    def append_versions(
        self, versions: Sequence[NewPromptVersion]
    ) -> tuple[PromptVersion, ...]:
        """Atomically deactivate the current version of each entry and insert the new ones."""
        ...


__all__ = [
    "PromptPackageSource",
    "PromptStoreError",
    "PromptVersionReader",
    "PromptVersionWriter",
]
