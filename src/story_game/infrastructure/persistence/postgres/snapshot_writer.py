"""Write all revisioned components of one canonical GameState."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import GameState

from .row_mapping import configuration_values
from .story_writer import StorySnapshotWriter
from .world_writer import WorldSnapshotWriter


class PostgresSnapshotWriter:
    def __init__(self) -> None:
        self.world_writer = WorldSnapshotWriter()
        self.story_writer = StorySnapshotWriter()

    def write(self, connection: psycopg.Connection[Any], state: GameState) -> None:
        connection.execute(
            """
            INSERT INTO game_state_configurations (
                run_id, revision, language, narration_style_id,
                perspective_id, control_mode_id, narrative_boundaries,
                story_model_id, extraction_model_id, summary_model_id,
                prompt_package_id, prompt_package_version
            ) VALUES (
                %(run_id)s, %(revision)s, %(language)s,
                %(narration_style_id)s, %(perspective_id)s,
                %(control_mode_id)s, %(narrative_boundaries)s,
                %(story_model_id)s, %(extraction_model_id)s,
                %(summary_model_id)s, %(prompt_package_id)s,
                %(prompt_package_version)s
            )
            """,
            {
                "run_id": str(state.run_id),
                "revision": state.revision.value,
                **configuration_values(state.configuration),
            },
        )
        self.world_writer.write(
            connection, state.run_id, state.revision, state.world
        )
        self.story_writer.write_metadata(
            connection, state.run_id, state.revision, state.story
        )
