"""Write revisioned story metadata and append completed turns once."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import (
    StableId,
    StateRevision,
    StorySummarySegment,
    StoryState,
    StoryTurn,
)


class StorySnapshotWriter:
    """Persist only the current sequence and initialization for one revision."""

    def write_metadata(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
        story: StoryState,
    ) -> None:
        initialization = story.initialization
        connection.execute(
            """
            INSERT INTO story_state_metadata (
                run_id, revision, current_turn_sequence,
                initialization_prompt, initialization_narration,
                initialization_completed_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                run_id.value,
                revision.value,
                story.current_turn_sequence,
                None if initialization is None else initialization.prompt,
                None if initialization is None else initialization.narration,
                None if initialization is None else initialization.completed_at,
            ),
        )

    def append_summary_segment(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        segment: StorySummarySegment,
    ) -> None:
        """Insert one new, immutable summary segment. Never called to update one."""
        connection.execute(
            """
            INSERT INTO story_summary_segments (
                run_id, from_sequence, through_sequence, text, based_on_revision
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                run_id.value,
                segment.from_sequence.value,
                segment.through_sequence.value,
                segment.text,
                segment.based_on_revision.value,
            ),
        )

    def append_turn(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        turn: StoryTurn,
    ) -> None:
        connection.execute(
            """
            INSERT INTO story_turns (
                run_id, turn_id, sequence, player_input, narration,
                based_on_revision, resulting_revision, completed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id.value,
                turn.id.value,
                turn.sequence.value,
                turn.player_input,
                turn.narration,
                turn.based_on_revision.value,
                turn.resulting_revision.value,
                turn.completed_at,
            ),
        )
