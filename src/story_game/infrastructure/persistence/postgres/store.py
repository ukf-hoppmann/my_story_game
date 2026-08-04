"""Composition root for the PostgreSQL persistence adapter."""

from __future__ import annotations

from story_game.application.ports import GameStateReader, GameStateWriter
from story_game.domain import ApprovedChangeSet, GameState, StableId, StateRevision

from .connection import PostgresConnectionFactory
from .reader import PostgresStateReader
from .snapshot_reader import PostgresSnapshotReader
from .snapshot_writer import PostgresSnapshotWriter
from .writer import PostgresStateWriter


class PostgresGameStateStore(GameStateReader, GameStateWriter):
    """Expose the application ports while keeping read/write responsibilities separate."""

    def __init__(self, connections: PostgresConnectionFactory) -> None:
        snapshot_reader = PostgresSnapshotReader()
        snapshot_writer = PostgresSnapshotWriter()
        self.reader = PostgresStateReader(connections, snapshot_reader)
        self.writer = PostgresStateWriter(
            connections,
            snapshot_reader,
            snapshot_writer,
        )

    def load(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState:
        return self.reader.load(run_id, revision=revision)

    def create_initial(self, state: GameState) -> None:
        self.writer.create_initial(state)

    def commit(self, run_id: StableId, changes: ApprovedChangeSet) -> GameState:
        return self.writer.commit(run_id, changes)
