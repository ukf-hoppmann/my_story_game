"""Small JSON adapter implementing the application persistence ports."""

from __future__ import annotations

from pathlib import Path

from story_game.application.ports import GameStateReader, GameStateWriter
from story_game.domain import ApprovedChangeSet, GameState, StableId, StateRevision
from story_game.infrastructure.persistence.errors import PersistenceConflictError

from .reader import JsonStateReader
from .writer import JsonStateWriter


class JsonGameStateStore(GameStateReader, GameStateWriter):
    """Development store; it persists the latest snapshot but not full history."""

    def __init__(self, path: Path | str) -> None:
        self.reader = JsonStateReader(path)
        self.writer = JsonStateWriter(path)

    def load(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState:
        state = self.reader.load()
        if state.id != run_id:
            raise PersistenceConflictError("Die geladene State-ID passt nicht zum angeforderten Lauf")
        if revision is not None and state.revision != revision:
            raise PersistenceConflictError("Der JSON-Mock besitzt nur seine aktuelle Revision")
        return state

    def create_initial(self, state: GameState) -> None:
        self.writer.save(state)

    def commit(self, run_id: StableId, changes: ApprovedChangeSet) -> GameState:
        current = self.load(run_id)
        updated = current.apply(changes)
        self.writer.save(updated)
        return updated
