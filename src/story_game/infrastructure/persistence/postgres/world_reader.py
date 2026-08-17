"""Read the world portion of one immutable PostgreSQL state snapshot."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg

from story_game.domain import StableId, WorldState

from .row_mapping import (
    entity_from_row,
    fact_from_row,
    goal_from_row,
    knowledge_from_row,
    link_from_row,
    rule_from_row,
    stable_id_from_row,
)


class WorldSnapshotReader:
    """Reconstruct only world entities and their current relationships."""

    def read(
        self,
        connection: psycopg.Connection[Any],
        run_id: UUID,
        revision: int,
    ) -> WorldState:
        parameters = (run_id, revision)
        entities = connection.execute(
            """
            SELECT * FROM world_entities
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        links = connection.execute(
            """
            SELECT * FROM world_links
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        facts = connection.execute(
            """
            SELECT * FROM world_facts
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        knowledge = connection.execute(
            """
            SELECT * FROM world_knowledge
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        rules = connection.execute(
            """
            SELECT * FROM world_rules
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        goals = connection.execute(
            """
            SELECT * FROM world_goals
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        scene_locations = connection.execute(
            """
            SELECT location_id FROM world_scene_locations
            WHERE run_id = %s AND revision = %s
            ORDER BY position
            """,
            parameters,
        ).fetchall()
        goal_references = connection.execute(
            """
            SELECT goal_id, entity_id FROM world_goal_related_entities
            WHERE run_id = %s AND revision = %s
            ORDER BY goal_id, position
            """,
            parameters,
        ).fetchall()
        related_by_goal: dict[StableId, list[StableId]] = {}
        for row in goal_references:
            goal_id = stable_id_from_row(row, "goal_id")
            related_by_goal.setdefault(goal_id, []).append(
                stable_id_from_row(row, "entity_id")
            )
        return WorldState(
            entities=tuple(entity_from_row(row) for row in entities),
            links=tuple(link_from_row(row) for row in links),
            facts=tuple(fact_from_row(row) for row in facts),
            knowledge=tuple(knowledge_from_row(row) for row in knowledge),
            rules=tuple(rule_from_row(row) for row in rules),
            goals=tuple(
                goal_from_row(
                    row,
                    tuple(
                        related_by_goal.get(stable_id_from_row(row, "goal_id"), ())
                    ),
                )
                for row in goals
            ),
            scene_location_ids=tuple(
                stable_id_from_row(row, "location_id") for row in scene_locations
            ),
        )
