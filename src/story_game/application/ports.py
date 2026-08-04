"""Persistence ports owned by the application layer."""

from __future__ import annotations

from typing import Protocol

from story_game.domain import ApprovedChangeSet, GameState, StableId, StateRevision


class GameStateReader(Protocol):
    """Load one canonical game-state revision."""

    def load(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState: ...


class GameStateWriter(Protocol):
    """Create or atomically advance one canonical game-state stream."""

    def create_initial(self, state: GameState) -> None: ...

    def commit(
        self,
        run_id: StableId,
        changes: ApprovedChangeSet,
    ) -> GameState: ...
