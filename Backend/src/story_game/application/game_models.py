"""Typed values shared by game operations and their persistence ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from story_game.domain import (
    ApprovedChangeSet,
    GameConfiguration,
    GameRole,
    GameRun,
    GameRunStatus,
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
class RunSummary:
    """Read-optimized projection of one run for a "your runs" listing.

    Deliberately excludes the full ``GameState``/``WorldState`` snapshot so a
    list of many runs never forces loading a whole world per row.
    """

    run_id: StableId
    name: str
    status: GameRunStatus
    current_revision: StateRevision
    game_role: GameRole
    updated_at: datetime


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
