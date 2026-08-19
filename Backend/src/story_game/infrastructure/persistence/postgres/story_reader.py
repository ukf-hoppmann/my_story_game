"""Reconstruct StoryState from revision metadata and append-only turns."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg

from story_game.domain import (
    StateRevision,
    StoryInitialization,
    StorySequence,
    StoryState,
    StorySummary,
    StoryTurn,
)

from .row_mapping import stable_id_from_row


class StorySnapshotReader:
    def read(
        self,
        connection: psycopg.Connection[Any],
        run_id: UUID,
        revision: int,
    ) -> StoryState:
        metadata = connection.execute(
            """
            SELECT * FROM story_state_metadata
            WHERE run_id = %s AND revision = %s
            """,
            (run_id, revision),
        ).fetchone()
        if metadata is None:
            raise KeyError("story_state_metadata")
        rows = connection.execute(
            """
            SELECT * FROM story_turns
            WHERE run_id = %s AND resulting_revision <= %s
            ORDER BY sequence
            """,
            (run_id, revision),
        ).fetchall()
        turns = tuple(
            StoryTurn(
                stable_id_from_row(row, "turn_id"),
                StorySequence(int(row["sequence"])),
                str(row["player_input"]),
                str(row["narration"]),
                StateRevision(int(row["based_on_revision"])),
                StateRevision(int(row["resulting_revision"])),
                row["completed_at"],
            )
            for row in rows
        )
        summary = (
            None
            if metadata["summary_text"] is None
            else StorySummary(
                StorySequence(int(metadata["summary_through_sequence"])),
                str(metadata["summary_text"]),
                StateRevision(int(metadata["summary_based_on_revision"])),
            )
        )
        initialization = (
            None
            if metadata["initialization_narration"] is None
            else StoryInitialization(
                str(metadata["initialization_prompt"]),
                str(metadata["initialization_narration"]),
                metadata["initialization_completed_at"],
            )
        )
        return StoryState(
            turns=turns,
            summary=summary,
            current_turn_sequence=int(metadata["current_turn_sequence"]),
            initialization=initialization,
        )
