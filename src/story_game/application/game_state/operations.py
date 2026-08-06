"""Explicit collection of independently testable game operations."""

from __future__ import annotations

from dataclasses import dataclass

from .commit_completed_turn import CommitCompletedTurn
from .create_game_run import CreateGameRun
from .load_game import LoadGame
from .update_configuration import UpdateGameConfiguration


@dataclass(frozen=True, slots=True)
class GameStateOperations:
    create: CreateGameRun
    load: LoadGame
    update_configuration: UpdateGameConfiguration
    commit_turn: CommitCompletedTurn
