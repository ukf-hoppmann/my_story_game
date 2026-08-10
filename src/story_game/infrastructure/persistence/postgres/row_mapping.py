"""Conversions between Domain values and PostgreSQL rows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from psycopg.types.json import Jsonb

from story_game.domain import (
    ActorProfile,
    ActorRole,
    Condition,
    EntityKind,
    EntityLink,
    Evidence,
    Fact,
    GameConfiguration,
    Goal,
    GoalKind,
    GoalStatus,
    KnowledgeEntry,
    PromptProfile,
    RelationKind,
    StableId,
    StorySequence,
    Visibility,
    VisibilityScope,
    WorldEntity,
    WorldRule,
)
from story_game.infrastructure.persistence.errors import PersistenceConsistencyError


def jsonb(value: Any) -> Jsonb:
    return Jsonb(value)


def configuration_values(configuration: GameConfiguration) -> dict[str, Any]:
    return {
        "language": configuration.language,
        "genre": configuration.prompt_profile.genre,
        "tone": configuration.prompt_profile.tone,
        "prose_style": configuration.prompt_profile.prose_style,
        "perspective": configuration.prompt_profile.perspective,
        "pacing": configuration.prompt_profile.pacing,
        "control_mode": configuration.prompt_profile.control_mode,
        "player_agency": configuration.prompt_profile.player_agency,
        "consequence": configuration.prompt_profile.consequence,
        "challenge": configuration.prompt_profile.challenge,
        "content_profile": configuration.prompt_profile.content_profile,
        "narrative_boundaries": jsonb(list(configuration.narrative_boundaries)),
        "prompt_package_id": configuration.prompt_package_id,
        "prompt_package_version": configuration.prompt_package_version,
    }


def configuration_from_row(row: Mapping[str, Any]) -> GameConfiguration:
    return GameConfiguration(
        language=_text(row, "language"),
        prompt_profile=PromptProfile(
            genre=_text(row, "genre"),
            tone=_text(row, "tone"),
            prose_style=_text(row, "prose_style"),
            perspective=_text(row, "perspective"),
            pacing=_text(row, "pacing"),
            control_mode=_text(row, "control_mode"),
            player_agency=_text(row, "player_agency"),
            consequence=_text(row, "consequence"),
            challenge=_text(row, "challenge"),
            content_profile=_text(row, "content_profile"),
        ),
        narrative_boundaries=tuple(
            _value_text(item, "narrative boundary")
            for item in _json_list(row.get("narrative_boundaries"), "narrative_boundaries")
        ),
        prompt_package_id=_text(row, "prompt_package_id"),
        prompt_package_version=_text(row, "prompt_package_version"),
    )


def visibility_values(visibility: Visibility) -> dict[str, str | None]:
    return {
        "visibility_scope": visibility.scope.value,
        "visibility_actor_id": (
            None if visibility.actor_id is None else str(visibility.actor_id)
        ),
    }


def visibility_from_row(row: Mapping[str, Any]) -> Visibility:
    actor_id = row.get("visibility_actor_id")
    return Visibility(
        VisibilityScope(_text(row, "visibility_scope")),
        None if actor_id is None else StableId(str(actor_id)),
    )


def evidence_values(evidence: Evidence) -> dict[str, str | None]:
    return {
        "evidence_source": evidence.source,
        "evidence_reference": (
            None if evidence.reference is None else str(evidence.reference)
        ),
        "evidence_excerpt": evidence.excerpt,
    }


def evidence_from_row(row: Mapping[str, Any]) -> Evidence:
    reference = row.get("evidence_reference")
    excerpt = row.get("evidence_excerpt")
    return Evidence(
        _text(row, "evidence_source"),
        None if reference is None else StableId(str(reference)),
        None if excerpt is None else str(excerpt),
    )


def entity_values(
    run_id: StableId, revision: int, position: int, entity: WorldEntity
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "entity_id": str(entity.id),
        "kind": entity.kind.value,
        "label": entity.label,
        "description": entity.description,
        "actor_role": None if entity.actor is None else entity.actor.role.value,
        "conditions": jsonb(
            [
                {"name": condition.name, "description": condition.description}
                for condition in entity.conditions
            ]
        ),
        "aliases": jsonb(list(entity.aliases)),
    }


def entity_from_row(row: Mapping[str, Any]) -> WorldEntity:
    actor_role = row.get("actor_role")
    return WorldEntity(
        StableId(_text(row, "entity_id")),
        EntityKind(_text(row, "kind")),
        _text(row, "label"),
        str(row.get("description") or ""),
        None if actor_role is None else ActorProfile(ActorRole(str(actor_role))),
        tuple(
            Condition(
                _json_text(item, "name"),
                _json_text(item, "description", default=""),
            )
            for item in _json_list(row.get("conditions"), "conditions")
        ),
        tuple(
            _value_text(item, "alias")
            for item in _json_list(row.get("aliases"), "aliases")
        ),
    )


def link_values(
    run_id: StableId, revision: int, position: int, link: EntityLink
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "link_id": str(link.id),
        "source_id": str(link.source_id),
        "target_id": str(link.target_id),
        "kind": link.kind.value,
        **visibility_values(link.visibility),
        "quantity": link.quantity,
        "description": link.description,
    }


def link_from_row(row: Mapping[str, Any]) -> EntityLink:
    quantity = row.get("quantity")
    return EntityLink(
        StableId(_text(row, "link_id")),
        StableId(_text(row, "source_id")),
        StableId(_text(row, "target_id")),
        RelationKind(_text(row, "kind")),
        visibility_from_row(row),
        None if quantity is None else int(quantity),
        str(row.get("description") or ""),
    )


def fact_values(
    run_id: StableId, revision: int, position: int, fact: Fact
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "fact_id": str(fact.id),
        "statement": fact.statement,
        "subject_id": None if fact.subject_id is None else str(fact.subject_id),
        **evidence_values(fact.evidence),
        **visibility_values(fact.visibility),
    }


def fact_from_row(row: Mapping[str, Any]) -> Fact:
    subject_id = row.get("subject_id")
    return Fact(
        StableId(_text(row, "fact_id")),
        _text(row, "statement"),
        evidence_from_row(row),
        visibility_from_row(row),
        None if subject_id is None else StableId(str(subject_id)),
    )


def knowledge_values(
    run_id: StableId, revision: int, position: int, entry: KnowledgeEntry
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "actor_id": str(entry.actor_id),
        "fact_id": str(entry.fact_id),
        "learned_at": entry.learned_at.value,
        "forgotten_at": None if entry.forgotten_at is None else entry.forgotten_at.value,
    }


def knowledge_from_row(row: Mapping[str, Any]) -> KnowledgeEntry:
    forgotten_at = row.get("forgotten_at")
    return KnowledgeEntry(
        StableId(_text(row, "actor_id")),
        StableId(_text(row, "fact_id")),
        StorySequence(int(row["learned_at"])),
        None if forgotten_at is None else StorySequence(int(forgotten_at)),
    )


def rule_values(
    run_id: StableId, revision: int, position: int, rule: WorldRule
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "rule_id": str(rule.id),
        "statement": rule.statement,
        **evidence_values(rule.evidence),
        **visibility_values(rule.visibility),
    }


def rule_from_row(row: Mapping[str, Any]) -> WorldRule:
    return WorldRule(
        StableId(_text(row, "rule_id")),
        _text(row, "statement"),
        evidence_from_row(row),
        visibility_from_row(row),
    )


def goal_values(
    run_id: StableId, revision: int, position: int, goal: Goal
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "goal_id": str(goal.id),
        "kind": goal.kind.value,
        "title": goal.title,
        "description": goal.description,
        "status": goal.status.value,
        "related_entity_ids": jsonb([str(item) for item in goal.related_entity_ids]),
    }


def goal_from_row(row: Mapping[str, Any]) -> Goal:
    return Goal(
        StableId(_text(row, "goal_id")),
        GoalKind(_text(row, "kind")),
        _text(row, "title"),
        _text(row, "description"),
        GoalStatus(_text(row, "status")),
        tuple(
            StableId(_value_text(item, "goal reference"))
            for item in _json_list(row.get("related_entity_ids"), "related_entity_ids")
        ),
    )


def _text(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PersistenceConsistencyError(f"Die Datenbankspalte {key} ist ungültig")
    return value


def _json_list(value: Any, key: str) -> list[Any]:
    if not isinstance(value, list):
        raise PersistenceConsistencyError(f"Das JSON-Feld {key} muss eine Liste sein")
    return value


def _json_text(
    value: Mapping[str, Any], key: str, *, default: str | None = None
) -> str:
    item = value.get(key, default)
    if not isinstance(item, str):
        raise PersistenceConsistencyError(f"Das JSON-Feld {key} muss Text sein")
    return item


def _value_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceConsistencyError(f"{label} muss Text sein")
    return value
