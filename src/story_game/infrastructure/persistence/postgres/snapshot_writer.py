"""Compose independent world and story writers for one state revision."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import GameState

from .story_writer import StorySnapshotWriter
from .world_writer import WorldSnapshotWriter


class PostgresSnapshotWriter:
    """Persist all aggregate components after the commit row exists."""

    def __init__(self) -> None:
        self.world_writer = WorldSnapshotWriter()
        self.story_writer = StorySnapshotWriter()

    def write(
        self,
        connection: psycopg.Connection[Any],
        state: GameState,
    ) -> None:
        self.world_writer.write(connection, state.id, state.revision, state.world)
        self.story_writer.write(connection, state.id, state.revision, state.story)
