"""Application writer for transactional PostgreSQL state commits."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.errors import UniqueViolation

from story_game.application.ports import GameStateWriter
from story_game.domain import ApprovedChangeSet, GameState, StableId, StateRevision
from story_game.infrastructure.persistence.errors import (
    PersistenceConflictError,
    PersistenceError,
    PersistenceNotFoundError,
)

from .connection import PostgresConnectionFactory
from .snapshot_reader import PostgresSnapshotReader
from .snapshot_writer import PostgresSnapshotWriter


class PostgresStateWriter(GameStateWriter):
    """Create runs and commit approved changes with row-level head locking."""

    def __init__(
        self,
        connections: PostgresConnectionFactory,
        snapshot_reader: PostgresSnapshotReader | None = None,
        snapshot_writer: PostgresSnapshotWriter | None = None,
    ) -> None:
        self.connections = connections
        self.snapshot_reader = snapshot_reader or PostgresSnapshotReader()
        self.snapshot_writer = snapshot_writer or PostgresSnapshotWriter()

    def create_initial(self, state: GameState) -> None:
        if state.revision != StateRevision(1):
            raise PersistenceConflictError(
                "Ein neuer PostgreSQL-Lauf muss mit Revision 1 beginnen"
            )
        try:
            with self.connections.connect() as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        INSERT INTO story_runs (
                            run_id, player_actor_id, current_revision
                        ) VALUES (%s, %s, %s)
                        """,
                        (
                            str(state.id),
                            None
                            if state.player_actor_id is None
                            else str(state.player_actor_id),
                            state.revision.value,
                        ),
                    )
                    self._insert_commit(
                        connection,
                        state.id,
                        state.revision,
                        proposal_id="initial",
                        previous_revision=None,
                    )
                    self.snapshot_writer.write(connection, state)
        except UniqueViolation as exc:
            raise PersistenceConflictError(
                f"Der Lauf existiert bereits oder die Initialdaten sind doppelt: {state.id}"
            ) from exc
        except psycopg.Error as exc:
            raise PersistenceError(
                f"PostgreSQL-State konnte nicht angelegt werden: {state.id}"
            ) from exc

    def commit(self, run_id: StableId, changes: ApprovedChangeSet) -> GameState:
        try:
            with self.connections.connect() as connection:
                with connection.transaction():
                    head = connection.execute(
                        """
                        SELECT current_revision
                        FROM story_runs
                        WHERE run_id = %s
                        FOR UPDATE
                        """,
                        (str(run_id),),
                    ).fetchone()
                    if head is None:
                        raise PersistenceNotFoundError(f"Der Lauf existiert nicht: {run_id}")
                    current_revision = StateRevision(int(head["current_revision"]))
                    if current_revision != changes.base_revision:
                        raise PersistenceConflictError(
                            "Der PostgreSQL-Laufkopf hat eine andere Revision als der Änderungssatz"
                        )
                    current = self.snapshot_reader.read(
                        connection, run_id, current_revision
                    )
                    updated = current.apply(changes)
                    self._insert_commit(
                        connection,
                        run_id,
                        updated.revision,
                        proposal_id=str(changes.proposal_id),
                        previous_revision=current_revision.value,
                    )
                    self.snapshot_writer.write(connection, updated)
                    connection.execute(
                        """
                        UPDATE story_runs
                        SET current_revision = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE run_id = %s
                        """,
                        (updated.revision.value, str(run_id)),
                    )
                    return updated
        except (PersistenceConflictError, PersistenceNotFoundError):
            raise
        except UniqueViolation as exc:
            raise PersistenceConflictError(
                f"Der Änderungssatz wurde bereits verarbeitet: {changes.proposal_id}"
            ) from exc
        except psycopg.Error as exc:
            raise PersistenceError(
                f"PostgreSQL-State konnte nicht gespeichert werden: {run_id}"
            ) from exc

    @staticmethod
    def _insert_commit(
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
        *,
        proposal_id: str,
        previous_revision: int | None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO story_state_commits (
                run_id, revision, proposal_id, previous_revision
            ) VALUES (%s, %s, %s, %s)
            """,
            (str(run_id), revision.value, proposal_id, previous_revision),
        )
