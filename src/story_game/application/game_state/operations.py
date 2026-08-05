"""Immutable bundle of canonical game-state operations."""

from __future__ import annotations

from dataclasses import dataclass

from .commit import CommitGameStateChanges
from .create_initial import CreateInitialGameState
from .load import LoadGameState


@dataclass(frozen=True, slots=True)
class GameStateOperations:
    create_initial: CreateInitialGameState
    load: LoadGameState
    commit: CommitGameStateChanges
