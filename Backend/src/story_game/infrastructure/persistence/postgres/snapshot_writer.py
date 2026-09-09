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
                run_id, revision, language, genre, tone, prose_style,
                perspective, pacing, length, control_mode, player_agency,
                consequence, challenge, content_profile, narrative_boundaries,
                prompt_package_id, prompt_package_version
            ) VALUES (
                %(run_id)s, %(revision)s, %(language)s,
                %(genre)s, %(tone)s, %(prose_style)s, %(perspective)s,
                %(pacing)s, %(length)s, %(control_mode)s, %(player_agency)s,
                %(consequence)s, %(challenge)s, %(content_profile)s,
                %(narrative_boundaries)s, %(prompt_package_id)s,
                %(prompt_package_version)s
            )
            """,
            {
                "run_id": state.run_id.value,
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
