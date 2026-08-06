"""Read the world portion of one immutable PostgreSQL state snapshot."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import WorldState

from .row_mapping import (
    entity_from_row,
    fact_from_row,
    goal_from_row,
    knowledge_from_row,
    link_from_row,
    rule_from_row,
)


class WorldSnapshotReader:
    """Reconstruct only world entities and their current relationships."""

    def read(
        self,
        connection: psycopg.Connection[Any],
        run_id: str,
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
        return WorldState(
            entities=tuple(entity_from_row(row) for row in entities),
            links=tuple(link_from_row(row) for row in links),
            facts=tuple(fact_from_row(row) for row in facts),
            knowledge=tuple(knowledge_from_row(row) for row in knowledge),
            rules=tuple(rule_from_row(row) for row in rules),
            goals=tuple(goal_from_row(row) for row in goals),
        )
