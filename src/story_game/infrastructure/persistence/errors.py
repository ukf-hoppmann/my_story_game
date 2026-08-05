"""Compatibility names for application-owned persistence port failures."""

from story_game.application.ports import (
    GameStateConflictError,
    GameStateConsistencyError,
    GameStateNotFoundError,
    GameStateStoreError,
)


PersistenceError = GameStateStoreError
PersistenceNotFoundError = GameStateNotFoundError
PersistenceConflictError = GameStateConflictError
PersistenceConsistencyError = GameStateConsistencyError

__all__ = [
    "PersistenceConflictError",
    "PersistenceConsistencyError",
    "PersistenceError",
    "PersistenceNotFoundError",
]
