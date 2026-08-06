"""Reconstruct StoryState from revision metadata and append-only turns."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import (
    StableId,
    StateRevision,
    StorySequence,
    StoryState,
    StorySummary,
    StoryTurn,
)


class StorySnapshotReader:
    def read(
        self,
        connection: psycopg.Connection[Any],
        run_id: str,
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
                StableId(str(row["turn_id"])),
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
        return StoryState(
            turns=turns,
            summary=summary,
            current_turn_sequence=int(metadata["current_turn_sequence"]),
        )
