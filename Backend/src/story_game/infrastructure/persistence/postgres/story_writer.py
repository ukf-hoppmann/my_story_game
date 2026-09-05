"""Write revisioned story metadata and append completed turns once."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import StableId, StateRevision, StoryState, StoryTurn


class StorySnapshotWriter:
    """Persist only the rolling summary and sequence for one state revision."""

    def write_metadata(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
        story: StoryState,
    ) -> None:
        summary = story.summary
        initialization = story.initialization
        connection.execute(
            """
            INSERT INTO story_state_metadata (
                run_id, revision, current_turn_sequence,
                summary_through_sequence, summary_text,
                summary_based_on_revision,
                initialization_prompt, initialization_narration,
                initialization_completed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id.value,
                revision.value,
                story.current_turn_sequence,
                None if summary is None else summary.through_sequence.value,
                None if summary is None else summary.text,
                None if summary is None else summary.based_on_revision.value,
                None if initialization is None else initialization.prompt,
                None if initialization is None else initialization.narration,
                None if initialization is None else initialization.completed_at,
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
