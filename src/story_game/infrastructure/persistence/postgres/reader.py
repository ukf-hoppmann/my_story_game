"""Application reader for PostgreSQL-backed canonical state."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.application.ports import GameStateReader
from story_game.domain import GameState, StableId, StateRevision
from story_game.infrastructure.persistence.errors import PersistenceError

from .connection import PostgresConnectionFactory
from .snapshot_reader import PostgresSnapshotReader


class PostgresStateReader(GameStateReader):
    """Load the head or one immutable historical revision of a story run."""

    def __init__(
        self,
        connections: PostgresConnectionFactory,
        snapshot_reader: PostgresSnapshotReader | None = None,
    ) -> None:
        self.connections = connections
        self.snapshot_reader = snapshot_reader or PostgresSnapshotReader()

    def load(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState:
        try:
            with self.connections.connect() as connection:
                target_revision = revision or self._head_revision(connection, run_id)
                return self.load_connection(connection, run_id, target_revision)
        except (PersistenceError, psycopg.Error):
            raise
        except Exception as exc:
            raise PersistenceError(
                f"PostgreSQL-State konnte nicht geladen werden: {run_id}"
            ) from exc

    def load_connection(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
    ) -> GameState:
        return self.snapshot_reader.read(connection, run_id, revision)

    @staticmethod
    def _head_revision(
        connection: psycopg.Connection[Any], run_id: StableId
    ) -> StateRevision:
        row = connection.execute(
            "SELECT current_revision FROM story_runs WHERE run_id = %s",
            (str(run_id),),
        ).fetchone()
        if row is None:
            from story_game.infrastructure.persistence.errors import PersistenceNotFoundError

            raise PersistenceNotFoundError(f"Der Lauf existiert nicht: {run_id}")
        return StateRevision(int(row["current_revision"]))
