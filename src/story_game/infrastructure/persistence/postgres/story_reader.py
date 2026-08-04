"""Read the story portion of one immutable PostgreSQL state snapshot."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import psycopg

from story_game.domain import StableId, StoryState

from .row_mapping import (
    chapter_from_row,
    event_from_row,
    goal_from_row,
    scene_from_rows,
    summary_from_row,
    thread_from_row,
)


class StorySnapshotReader:
    """Reconstruct chronology, scenes and dramaturgical state."""

    def read(
        self,
        connection: psycopg.Connection[Any],
        run_id: str,
        revision: int,
    ) -> StoryState:
        parameters = (run_id, revision)
        metadata = connection.execute(
            """
            SELECT current_scene_id, current_chapter_id, current_sequence
            FROM story_state_metadata
            WHERE run_id = %s AND revision = %s
            """,
            parameters,
        ).fetchone()
        if metadata is None:
            raise KeyError("story_state_metadata")

        events = connection.execute(
            """
            SELECT * FROM story_events
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        scenes = connection.execute(
            """
            SELECT * FROM story_scenes
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        participants = connection.execute(
            """
            SELECT * FROM story_scene_participants
            WHERE run_id = %s AND revision = %s
            ORDER BY scene_id, position
            """,
            parameters,
        ).fetchall()
        participants_by_scene: dict[str, list[MappingRow]] = defaultdict(list)
        for participant in participants:
            participants_by_scene[str(participant["scene_id"])].append(participant)

        chapters = connection.execute(
            """
            SELECT * FROM story_chapters
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        threads = connection.execute(
            """
            SELECT * FROM story_threads
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        goals = connection.execute(
            """
            SELECT * FROM story_goals
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        summaries = connection.execute(
            """
            SELECT * FROM story_summaries
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()

        return StoryState(
            events=tuple(event_from_row(row) for row in events),
            scenes=tuple(
                scene_from_rows(
                    row,
                    participants_by_scene.get(str(row["scene_id"]), []),
                )
                for row in scenes
            ),
            chapters=tuple(chapter_from_row(row) for row in chapters),
            threads=tuple(thread_from_row(row) for row in threads),
            goals=tuple(goal_from_row(row) for row in goals),
            summaries=tuple(summary_from_row(row) for row in summaries),
            current_scene_id=(
                None
                if metadata["current_scene_id"] is None
                else StableId(str(metadata["current_scene_id"]))
            ),
            current_chapter_id=(
                None
                if metadata["current_chapter_id"] is None
                else StableId(str(metadata["current_chapter_id"]))
            ),
            current_sequence=int(metadata["current_sequence"]),
        )


MappingRow = dict[str, Any]
