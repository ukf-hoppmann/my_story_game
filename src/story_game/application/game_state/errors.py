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
class StateRejected:
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
    | StateRejected
    | StoredStateInvalid
    | StateStoreUnavailable
)
