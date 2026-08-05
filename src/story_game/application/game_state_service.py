"""Application use cases for the canonical story-game state."""

from __future__ import annotations

from story_game.domain import (
    ApprovedChangeSet,
    GameState,
    RevisionConflictError,
    StableId,
    StateRevision,
)

from .ports import GameStateReader, GameStateWriter


class GameStateService:
    """Coordinate state use cases without exposing persistence details to HTTP."""

    def __init__(self, reader: GameStateReader, writer: GameStateWriter) -> None:
        self.reader = reader
        self.writer = writer

    def create_initial(self, state: GameState) -> GameState:
        if state.revision != StateRevision(1):
            raise RevisionConflictError(
                "Ein neuer Storygame-Lauf muss mit Revision 1 beginnen"
            )
        self.writer.create_initial(state)
        return state

    def load(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState:
        return self.reader.load(run_id, revision=revision)

    def commit(self, run_id: StableId, changes: ApprovedChangeSet) -> GameState:
        return self.writer.commit(run_id, changes)
