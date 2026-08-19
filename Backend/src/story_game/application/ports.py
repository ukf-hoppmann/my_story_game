"""Narrow persistence ports owned by the application layer."""

from __future__ import annotations

from typing import Protocol

from story_game.domain import GameRun, GameState, StableId, StateRevision

from .game_models import (
    CachedGameRunProposal,
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
    RunSummary,
)


class GameStateStoreError(Exception):
    """Base failure exposed by game persistence ports."""


class GameStateNotFoundError(GameStateStoreError):
    """The requested run or revision does not exist."""


class GameStateConflictError(GameStateStoreError):
    """A write lost its revision or uniqueness race."""


class GameStateConsistencyError(GameStateStoreError):
    """Stored rows cannot be reconstructed as valid Domain values."""


class GameRunCreator(Protocol):
    def create(self, run: GameRun, state: GameState) -> None: ...


class GameRunReader(Protocol):
    def load_run(self, run_id: StableId) -> GameRun: ...


class GameStateReader(Protocol):
    def load_state(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState: ...


class ConfigurationRevisionWriter(Protocol):
    def update_configuration(
        self, request: ConfigurationPersistenceRequest
    ) -> GameState: ...


class CompletedTurnWriter(Protocol):
    def commit_turn(self, request: CompletedTurnPersistenceRequest) -> GameState: ...


class PlayableRunLister(Protocol):
    def list_for_member(self, issuer: str, subject: str) -> tuple[RunSummary, ...]: ...


class InitialProposalStore(Protocol):
    """Short-lived, caller-owned storage for a not-yet-persisted run proposal.

    Deliberately narrower than ``GameRunCreator``: nothing saved here is
    canonical persistence, so the port carries no revision or conflict
    semantics — just save, load, and delete by ``proposal_id``. An expired or
    unknown ``proposal_id`` is not an error at this boundary; ``load`` simply
    returns ``None`` and the caller (``ConfirmGameRunProposal``) turns that
    into a typed ``RunNotFound`` failure.
    """

    def save(self, proposal_id: StableId, proposal: CachedGameRunProposal) -> None: ...

    def load(self, proposal_id: StableId) -> CachedGameRunProposal | None: ...

    def delete(self, proposal_id: StableId) -> None: ...
