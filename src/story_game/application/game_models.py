"""Typed values shared by game operations and their persistence ports."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.domain import (
    ApprovedChangeSet,
    GameConfiguration,
    GameRun,
    GameState,
    StableId,
    StateRevision,
    StorySummary,
    StoryTurn,
)


@dataclass(frozen=True, slots=True)
class LoadedGame:
    run: GameRun
    state: GameState


@dataclass(frozen=True, slots=True)
class ConfigurationPersistenceRequest:
    run_id: StableId
    base_revision: StateRevision
    configuration: GameConfiguration


@dataclass(frozen=True, slots=True)
class CompletedTurnPersistenceRequest:
    run_id: StableId
    changes: ApprovedChangeSet
    turn: StoryTurn
    summary: StorySummary | None
