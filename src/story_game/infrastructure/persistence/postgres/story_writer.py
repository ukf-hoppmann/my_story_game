"""Write the story portion of one immutable PostgreSQL state snapshot."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import StateRevision, StableId, StoryState

from .row_mapping import (
    chapter_values,
    event_values,
    goal_values,
    scene_participant_values,
    scene_values,
    summary_values,
    thread_values,
)


class StorySnapshotWriter:
    """Persist chronology and dramaturgical collections for one revision."""

    def write(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
        story: StoryState,
    ) -> None:
        connection.execute(
            """
            INSERT INTO story_state_metadata (
                run_id, revision, current_scene_id, current_chapter_id,
                current_sequence
            ) VALUES (
                %(run_id)s, %(revision)s, %(current_scene_id)s,
                %(current_chapter_id)s, %(current_sequence)s
            )
            """,
            {
                "run_id": str(run_id),
                "revision": revision.value,
                "current_scene_id": (
                    None
                    if story.current_scene_id is None
                    else str(story.current_scene_id)
                ),
                "current_chapter_id": (
                    None
                    if story.current_chapter_id is None
                    else str(story.current_chapter_id)
                ),
                "current_sequence": story.current_sequence,
            },
        )
        for position, event in enumerate(story.events):
            connection.execute(
                """
                INSERT INTO story_events (
                    run_id, revision, position, event_id, sequence, kind,
                    description, participant_ids, visibility_scope,
                    visibility_actor_id
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(event_id)s,
                    %(sequence)s, %(kind)s, %(description)s,
                    %(participant_ids)s, %(visibility_scope)s,
                    %(visibility_actor_id)s
                )
                """,
                event_values(run_id, revision.value, position, event),
            )
        for position, scene in enumerate(story.scenes):
            connection.execute(
                """
                INSERT INTO story_scenes (
                    run_id, revision, position, scene_id, sequence,
                    location_id, title, focus, focus_entity_id
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(scene_id)s,
                    %(sequence)s, %(location_id)s, %(title)s, %(focus)s,
                    %(focus_entity_id)s
                )
                """,
                scene_values(run_id, revision.value, position, scene),
            )
            for participant_position, participant in enumerate(scene.participants):
                connection.execute(
                    """
                    INSERT INTO story_scene_participants (
                        run_id, revision, scene_id, position, entity_id,
                        role, visibility_scope, visibility_actor_id
                    ) VALUES (
                        %(run_id)s, %(revision)s, %(scene_id)s, %(position)s,
                        %(entity_id)s, %(role)s, %(visibility_scope)s,
                        %(visibility_actor_id)s
                    )
                    """,
                    scene_participant_values(
                        run_id,
                        revision.value,
                        scene.id,
                        participant_position,
                        participant,
                    ),
                )
        for position, chapter in enumerate(story.chapters):
            connection.execute(
                """
                INSERT INTO story_chapters (
                    run_id, revision, position, chapter_id, sequence,
                    title, status, summary
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(chapter_id)s,
                    %(sequence)s, %(title)s, %(status)s, %(summary)s
                )
                """,
                chapter_values(run_id, revision.value, position, chapter),
            )
        for position, thread in enumerate(story.threads):
            connection.execute(
                """
                INSERT INTO story_threads (
                    run_id, revision, position, thread_id, title, status,
                    progress, related_entity_ids
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(thread_id)s,
                    %(title)s, %(status)s, %(progress)s,
                    %(related_entity_ids)s
                )
                """,
                thread_values(run_id, revision.value, position, thread),
            )
        for position, goal in enumerate(story.goals):
            connection.execute(
                """
                INSERT INTO story_goals (
                    run_id, revision, position, goal_id, title, owner_id,
                    status, progress, related_entity_ids
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(goal_id)s,
                    %(title)s, %(owner_id)s, %(status)s, %(progress)s,
                    %(related_entity_ids)s
                )
                """,
                goal_values(run_id, revision.value, position, goal),
            )
        for position, summary in enumerate(story.summaries):
            connection.execute(
                """
                INSERT INTO story_summaries (
                    run_id, revision, position, from_sequence,
                    through_sequence, text, based_on_revision
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s,
                    %(from_sequence)s, %(through_sequence)s, %(text)s,
                    %(based_on_revision)s
                )
                """,
                summary_values(run_id, revision.value, position, summary),
            )
