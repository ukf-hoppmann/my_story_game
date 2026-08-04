"""Compose independent world and story readers into the aggregate root."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import GameState, StableId, StateRevision
from story_game.infrastructure.persistence.errors import PersistenceNotFoundError

from .story_reader import StorySnapshotReader
from .world_reader import WorldSnapshotReader


class PostgresSnapshotReader:
    """Read a complete, already committed revision using component readers."""

    def __init__(self) -> None:
        self.world_reader = WorldSnapshotReader()
        self.story_reader = StorySnapshotReader()

    def read(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
    ) -> GameState:
        commit = connection.execute(
            """
            SELECT run_id, revision, player_actor_id
            FROM story_state_commits
            JOIN story_runs USING (run_id)
            WHERE story_state_commits.run_id = %s
              AND story_state_commits.revision = %s
            """,
            (str(run_id), revision.value),
        ).fetchone()
        if commit is None:
            raise PersistenceNotFoundError(
                f"Die State-Revision {run_id}/{revision.value} existiert nicht"
            )
        world = self.world_reader.read(connection, str(run_id), revision.value)
        story = self.story_reader.read(connection, str(run_id), revision.value)
        return GameState(
            id=StableId(str(commit["run_id"])),
            revision=StateRevision(int(commit["revision"])),
            world=world,
            story=story,
            player_actor_id=(
                None
                if commit["player_actor_id"] is None
                else StableId(str(commit["player_actor_id"]))
            ),
        )
