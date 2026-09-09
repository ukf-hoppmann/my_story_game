"""Typed failures returned by canonical game-state operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class RunNotFound:
    detail: str


@dataclass(frozen=True, slots=True)
class RunConflict:
    detail: str


@dataclass(frozen=True, slots=True)
class RunAccessDenied:
    """The caller is authenticated but not a member of the requested run."""

    detail: str


@dataclass(frozen=True, slots=True)
class StateRejected:
    detail: str


@dataclass(frozen=True, slots=True)
class InvalidPromptSelection:
    category: str
    option_id: str

    @property
    def detail(self) -> str:
        return (
            f"Die Option {self.option_id!r} ist für die Kategorie {self.category!r} "
            "nicht verfügbar"
        )

    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class InvalidPromptPackageReference:
    detail: str


@dataclass(frozen=True, slots=True)
class PromptPackageConfigurationInvalid:
    detail: str


@dataclass(frozen=True, slots=True)
class StoredStateInvalid:
    detail: str


@dataclass(frozen=True, slots=True)
class StateStoreUnavailable:
    detail: str


GameStateOperationError: TypeAlias = (
    RunNotFound
    | RunConflict
    | RunAccessDenied
    | StateRejected
    | InvalidPromptSelection
    | InvalidPromptPackageReference
    | PromptPackageConfigurationInvalid
    | StoredStateInvalid
    | StateStoreUnavailable
)
