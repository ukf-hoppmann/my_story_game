"""Write the world portion of one immutable PostgreSQL state snapshot."""

from __future__ import annotations

from typing import Any

import psycopg

from story_game.domain import StateRevision, StableId, WorldState

from .row_mapping import (
    entity_values,
    fact_values,
    goal_values,
    knowledge_values,
    link_values,
    rule_values,
)


class WorldSnapshotWriter:
    """Persist world collections into a new revision without updating the head."""

    def write(
        self,
        connection: psycopg.Connection[Any],
        run_id: StableId,
        revision: StateRevision,
        world: WorldState,
    ) -> None:
        for position, entity in enumerate(world.entities):
            connection.execute(
                """
                INSERT INTO world_entities (
                    run_id, revision, position, entity_id, kind, label,
                    description, actor_role, conditions, aliases
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(entity_id)s,
                    %(kind)s, %(label)s, %(description)s, %(actor_role)s,
                    %(conditions)s, %(aliases)s
                )
                """,
                entity_values(run_id, revision.value, position, entity),
            )
        for position, link in enumerate(world.links):
            connection.execute(
                """
                INSERT INTO world_links (
                    run_id, revision, position, link_id, source_id, target_id,
                    kind, visibility_scope, visibility_actor_id, quantity,
                    description
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(link_id)s,
                    %(source_id)s, %(target_id)s, %(kind)s,
                    %(visibility_scope)s, %(visibility_actor_id)s, %(quantity)s,
                    %(description)s
                )
                """,
                link_values(run_id, revision.value, position, link),
            )
        for position, fact in enumerate(world.facts):
            connection.execute(
                """
                INSERT INTO world_facts (
                    run_id, revision, position, fact_id, statement, subject_id,
                    evidence_source, evidence_reference, evidence_excerpt,
                    visibility_scope, visibility_actor_id
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(fact_id)s,
                    %(statement)s, %(subject_id)s, %(evidence_source)s,
                    %(evidence_reference)s, %(evidence_excerpt)s,
                    %(visibility_scope)s, %(visibility_actor_id)s
                )
                """,
                fact_values(run_id, revision.value, position, fact),
            )
        for position, entry in enumerate(world.knowledge):
            connection.execute(
                """
                INSERT INTO world_knowledge (
                    run_id, revision, position, actor_id, fact_id,
                    learned_at, forgotten_at
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(actor_id)s,
                    %(fact_id)s, %(learned_at)s, %(forgotten_at)s
                )
                """,
                knowledge_values(run_id, revision.value, position, entry),
            )
        for position, rule in enumerate(world.rules):
            connection.execute(
                """
                INSERT INTO world_rules (
                    run_id, revision, position, rule_id, statement,
                    evidence_source, evidence_reference, evidence_excerpt,
                    visibility_scope, visibility_actor_id
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(rule_id)s,
                    %(statement)s, %(evidence_source)s, %(evidence_reference)s,
                    %(evidence_excerpt)s, %(visibility_scope)s,
                    %(visibility_actor_id)s
                )
                """,
                rule_values(run_id, revision.value, position, rule),
            )
        for position, goal in enumerate(world.goals):
            connection.execute(
                """
                INSERT INTO world_goals (
                    run_id, revision, position, goal_id, kind, title,
                    description, status, related_entity_ids
                ) VALUES (
                    %(run_id)s, %(revision)s, %(position)s, %(goal_id)s,
                    %(kind)s, %(title)s, %(description)s, %(status)s,
                    %(related_entity_ids)s
                )
                """,
                goal_values(run_id, revision.value, position, goal),
            )
