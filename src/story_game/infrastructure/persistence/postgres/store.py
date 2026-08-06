"""Transactional PostgreSQL adapter for game runs and state revisions."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.errors import UniqueViolation

from story_game.application.game_models import (
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
)
from story_game.domain import (
    DomainError,
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    StableId,
    StateRevision,
)
from story_game.infrastructure.persistence.errors import (
    PersistenceConflictError,
    PersistenceConsistencyError,
    PersistenceError,
    PersistenceNotFoundError,
)

from .connection import PostgresConnectionFactory
from .snapshot_reader import PostgresSnapshotReader
from .snapshot_writer import PostgresSnapshotWriter
from .story_writer import StorySnapshotWriter


class PostgresGameStore:
    """Implement narrow application ports with one atomic transaction per write."""

    def __init__(self, connections: PostgresConnectionFactory) -> None:
        self.connections = connections
        self.snapshot_reader = PostgresSnapshotReader()
        self.snapshot_writer = PostgresSnapshotWriter()
        self.story_writer = StorySnapshotWriter()

    def create(self, run: GameRun, state: GameState) -> None:
        try:
            with self.connections.connect() as connection:
                with connection.transaction():
                    connection.execute(
                        """
                        INSERT INTO game_runs (
                            run_id, status, current_revision, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            str(run.id),
                            run.status.value,
                            run.current_revision.value,
                            run.created_at,
                            run.updated_at,
                        ),
                    )
                    for member in run.members:
                        connection.execute(
                            """
                            INSERT INTO game_run_members (
                                run_id, issuer, subject, game_role, player_entity_id
                            ) VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                str(run.id),
                                member.issuer,
                                member.subject,
                                member.game_role.value,
                                None
                                if member.player_entity_id is None
                                else str(member.player_entity_id),
                            ),
                        )
                    self._insert_revision(
                        connection, run.id, StateRevision(1), previous=None
                    )
                    self.snapshot_writer.write(connection, state)
        except UniqueViolation as error:
            raise PersistenceConflictError(
                f"Der GameRun existiert bereits oder enthält doppelte Daten: {run.id}"
            ) from error
        except psycopg.Error as error:
            raise PersistenceError(
                f"Der GameRun konnte nicht gespeichert werden: {run.id}"
            ) from error

    def load_run(self, run_id: StableId) -> GameRun:
        try:
            with self.connections.connect() as connection:
                row = connection.execute(
                    "SELECT * FROM game_runs WHERE run_id = %s", (str(run_id),)
                ).fetchone()
                if row is None:
                    raise PersistenceNotFoundError(
                        f"Der GameRun existiert nicht: {run_id}"
                    )
                member_rows = connection.execute(
                    """
                    SELECT * FROM game_run_members
                    WHERE run_id = %s
                    ORDER BY issuer, subject
                    """,
                    (str(run_id),),
                ).fetchall()
                return GameRun(
                    id=run_id,
                    status=GameRunStatus(str(row["status"])),
                    current_revision=StateRevision(int(row["current_revision"])),
                    members=tuple(
                        GameRunMember(
                            issuer=str(member["issuer"]),
                            subject=str(member["subject"]),
                            game_role=GameRole(str(member["game_role"])),
                            player_entity_id=(
                                None
                                if member["player_entity_id"] is None
                                else StableId(str(member["player_entity_id"]))
                            ),
                        )
                        for member in member_rows
                    ),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        except PersistenceNotFoundError:
            raise
        except DomainError as error:
            raise PersistenceConsistencyError(
                f"Der gespeicherte GameRun ist ungültig: {run_id}"
            ) from error
        except psycopg.Error as error:
            raise PersistenceError(
                f"Der GameRun konnte nicht geladen werden: {run_id}"
            ) from error

    def load_state(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState:
        try:
            with self.connections.connect() as connection:
                selected_revision = revision or self._current_revision(
                    connection, run_id
                )
                return self.snapshot_reader.read(
                    connection, run_id, selected_revision
                )
        except PersistenceNotFoundError:
            raise
        except (DomainError, KeyError, ValueError, TypeError) as error:
            raise PersistenceConsistencyError(
                f"Der gespeicherte GameState ist ungültig: {run_id}"
            ) from error
        except psycopg.Error as error:
            raise PersistenceError(
                f"Der GameState konnte nicht geladen werden: {run_id}"
            ) from error

    def update_configuration(
        self, request: ConfigurationPersistenceRequest
    ) -> GameState:
        try:
            with self.connections.connect() as connection:
                with connection.transaction():
                    current_revision = self._locked_revision(
                        connection, request.run_id
                    )
                    self._require_current(current_revision, request.base_revision)
                    current = self.snapshot_reader.read(
                        connection, request.run_id, current_revision
                    )
                    updated = current.reconfigure(
                        request.configuration, base_revision=request.base_revision
                    )
                    self._persist_advanced_state(connection, current, updated)
                    return updated
        except (PersistenceConflictError, PersistenceNotFoundError):
            raise
        except psycopg.Error as error:
            raise PersistenceError(
                f"Die Konfiguration konnte nicht gespeichert werden: {request.run_id}"
            ) from error

    def commit_turn(self, request: CompletedTurnPersistenceRequest) -> GameState:
        try:
            with self.connections.connect() as connection:
                with connection.transaction():
                    current_revision = self._locked_revision(
                        connection, request.run_id
                    )
                    self._require_current(
                        current_revision, request.changes.base_revision
                    )
                    current = self.snapshot_reader.read(
                        connection, request.run_id, current_revision
                    )
                    updated = current.complete_turn(
                        request.changes, request.turn, request.summary
                    )
                    self._insert_revision(
                        connection,
                        request.run_id,
                        updated.revision,
                        previous=current_revision,
                    )
                    self.snapshot_writer.write(connection, updated)
                    self.story_writer.append_turn(
                        connection, request.run_id, request.turn
                    )
                    self._update_head(connection, request.run_id, updated.revision)
                    return updated
        except (PersistenceConflictError, PersistenceNotFoundError):
            raise
        except UniqueViolation as error:
            raise PersistenceConflictError(
                f"Der StoryTurn wurde bereits gespeichert: {request.turn.id}"
            ) from error
        except psycopg.Error as error:
            raise PersistenceError(
                f"Der StoryTurn konnte nicht gespeichert werden: {request.run_id}"
            ) from error

    def _persist_advanced_state(
        self,
        connection: psycopg.Connection[Any],
        current: GameState,
        updated: GameState,
    ) -> None:
        self._insert_revision(
            connection,
            current.run_id,
            updated.revision,
            previous=current.revision,
        )
        self.snapshot_writer.write(connection, updated)
        self._update_head(connection, current.run_id, updated.revision)

    @staticmethod
    def _insert_revision(
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
        *,
        previous: StateRevision | None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO game_state_revisions (
                run_id, revision, previous_revision
            ) VALUES (%s, %s, %s)
            """,
            (
                str(run_id),
                revision.value,
                None if previous is None else previous.value,
            ),
        )

    @staticmethod
    def _current_revision(
        connection: psycopg.Connection[Any], run_id: StableId
    ) -> StateRevision:
        row = connection.execute(
            "SELECT current_revision FROM game_runs WHERE run_id = %s",
            (str(run_id),),
        ).fetchone()
        if row is None:
            raise PersistenceNotFoundError(f"Der GameRun existiert nicht: {run_id}")
        return StateRevision(int(row["current_revision"]))

    @classmethod
    def _locked_revision(
        cls, connection: psycopg.Connection[Any], run_id: StableId
    ) -> StateRevision:
        row = connection.execute(
            """
            SELECT current_revision FROM game_runs
            WHERE run_id = %s
            FOR UPDATE
            """,
            (str(run_id),),
        ).fetchone()
        if row is None:
            raise PersistenceNotFoundError(f"Der GameRun existiert nicht: {run_id}")
        return StateRevision(int(row["current_revision"]))

    @staticmethod
    def _require_current(
        current: StateRevision, expected: StateRevision
    ) -> None:
        if current != expected:
            raise PersistenceConflictError(
                "Der GameRun hat eine andere aktuelle Revision"
            )

    @staticmethod
    def _update_head(
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
    ) -> None:
        connection.execute(
            """
            UPDATE game_runs
            SET current_revision = %s, updated_at = CURRENT_TIMESTAMP
            WHERE run_id = %s
            """,
            (revision.value, str(run_id)),
        )
