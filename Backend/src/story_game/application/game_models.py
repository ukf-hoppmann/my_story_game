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
    StorySummarySegment,
    StoryState,
    StoryTurn,
    WorldState,
)


@dataclass(frozen=True, slots=True)
class LoadedGame:
    run: GameRun
    state: GameState


@dataclass(frozen=True, slots=True)
class CachedGameRunProposal:
    """A not-yet-persisted initialization result awaiting caller confirmation.

    Held transiently by an ``InitialProposalStore`` between ``ProposeGameRun``
    and ``ConfirmGameRunProposal`` — never written to canonical persistence
    itself. ``issuer``/``subject`` pin the proposal to whoever requested it so
    a confirmation cannot be made against someone else's proposal.
    """

    issuer: str
    subject: str
    configuration: GameConfiguration
    story_state: StoryState
    world_state: WorldState
    suggested_title: str = ""


@dataclass(frozen=True, slots=True)
class GameRunProposal:
    """What a caller reviews before deciding to confirm or discard a run."""

    proposal_id: StableId
    story_state: StoryState
    world_state: WorldState
    suggested_player_entity_ids: tuple[StableId, ...] = ()
    suggested_title: str = ""


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
    new_summary_segment: StorySummarySegment | None
