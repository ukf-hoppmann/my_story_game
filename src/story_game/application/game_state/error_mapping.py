"""Translate boundary exceptions into application-owned failure values."""

from __future__ import annotations

from story_game.application.ports import (
    GameStateConflictError,
    GameStateConsistencyError,
    GameStateNotFoundError,
    GameStateStoreError,
)
from story_game.domain import DomainError, RevisionConflictError

from .errors import (
    GameStateOperationError,
    RunConflict,
    RunNotFound,
    StateRejected,
    StateStoreUnavailable,
    StoredStateInvalid,
)


def map_game_state_error(error: Exception) -> GameStateOperationError:
    """Map expected store and domain failures without hiding unknown defects."""
    detail = str(error)
    if isinstance(error, GameStateNotFoundError):
        return RunNotFound(detail)
    if isinstance(error, (GameStateConflictError, RevisionConflictError)):
        return RunConflict(detail)
    if isinstance(error, GameStateConsistencyError):
        return StoredStateInvalid(detail)
    if isinstance(error, GameStateStoreError):
        return StateStoreUnavailable(detail)
    if isinstance(error, DomainError):
        return StateRejected(detail)
    raise error
