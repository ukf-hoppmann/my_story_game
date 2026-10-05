"""Values of the versioned system-prompt store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from story_game.domain import StableId


class PromptEntryKind(StrEnum):
    """What a prompt entry is inside its package; mirrors the TOML structure."""

    TASK = "task"
    OPTION = "option"
    DIRECTIVE = "directive"


class PromptVersionSource(StrEnum):
    """Where one stored version of an entry came from."""

    TOML_SEED = "toml_seed"
    UI = "ui"
    TOML_RESET = "toml_reset"


@dataclass(frozen=True, slots=True)
class PromptPackageReference:
    """One ``<package id>/<version>`` pair, the unit that is seeded and loaded."""

    package_id: str
    package_version: str


@dataclass(frozen=True, slots=True)
class PromptEntryRef:
    """Addresses one entry inside a package.

    ``key`` is the TOML id for a task or directive and ``<category>/<option>``
    for an option.
    """

    kind: PromptEntryKind
    key: str


@dataclass(frozen=True, slots=True)
class PromptEntry:
    """The content of one entry: its text plus the structure it carries.

    ``position`` orders entries of the same kind. ``is_default`` is set on
    exactly one option per category; ``task_ids`` names the tasks a directive
    applies to. Both are structure copied from the TOML, never edited.
    """

    kind: PromptEntryKind
    key: str
    text: str
    position: int
    is_default: bool = False
    task_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("Der Schlüssel eines Prompt-Eintrags darf nicht leer sein")
        if not self.text.strip():
            raise ValueError("Der Text eines Prompt-Eintrags darf nicht leer sein")
        if self.position < 0:
            raise ValueError("Die Position eines Prompt-Eintrags darf nicht negativ sein")

    @property
    def ref(self) -> PromptEntryRef:
        return PromptEntryRef(self.kind, self.key)


@dataclass(frozen=True, slots=True)
class NewPromptVersion:
    """A version about to be appended; it becomes the active one for its entry."""

    version_id: StableId
    package_id: str
    package_version: str
    entry: PromptEntry
    source: PromptVersionSource
    created_at: datetime
    created_by: str | None
    """Subject of the editing caller; ``None`` for a seed from the TOML files."""


@dataclass(frozen=True, slots=True)
class PromptVersion:
    """One stored version of an entry. History rows are never changed."""

    version_id: StableId
    package_id: str
    package_version: str
    entry: PromptEntry
    source: PromptVersionSource
    created_at: datetime
    created_by: str | None
    is_active: bool


__all__ = [
    "NewPromptVersion",
    "PromptEntry",
    "PromptEntryKind",
    "PromptEntryRef",
    "PromptPackageReference",
    "PromptVersion",
    "PromptVersionSource",
]
