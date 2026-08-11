"""Read one complete committed GameState revision."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import GameState, StableId, StateRevision
from story_game.infrastructure.persistence.errors import PersistenceNotFoundError

from .row_mapping import configuration_from_row
from .story_reader import StorySnapshotReader
from .world_reader import WorldSnapshotReader


class PostgresSnapshotReader:
    def __init__(self) -> None:
        self.world_reader = WorldSnapshotReader()
        self.story_reader = StorySnapshotReader()

    def read(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
    ) -> GameState:
        configuration_row = connection.execute(
            """
            SELECT configuration.*
            FROM game_state_configurations AS configuration
            JOIN game_state_revisions USING (run_id, revision)
            WHERE configuration.run_id = %s AND configuration.revision = %s
            """,
            (run_id.value, revision.value),
        ).fetchone()
        if configuration_row is None:
            raise PersistenceNotFoundError(
                f"Die State-Revision {run_id}/{revision.value} existiert nicht"
            )
        return GameState(
            run_id=run_id,
            revision=revision,
            configuration=configuration_from_row(configuration_row),
            world=self.world_reader.read(connection, run_id.value, revision.value),
            story=self.story_reader.read(connection, run_id.value, revision.value),
        )
