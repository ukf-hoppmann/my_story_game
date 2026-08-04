"""Conversions between domain values and PostgreSQL row values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from psycopg.types.json import Jsonb

from story_game.domain import (
    ActorProfile,
    ActorRole,
    Chapter,
    ChapterStatus,
    Condition,
    EntityLink,
    EntityKind,
    Evidence,
    Fact,
    Goal,
    GoalStatus,
    KnowledgeEntry,
    RelationKind,
    Scene,
    StableId,
    StateRevision,
    StoryEvent,
    StorySequence,
    StorySummary,
    StoryThread,
    ThreadStatus,
    Visibility,
    VisibilityScope,
    WorldEntity,
    WorldRule,
)
from story_game.infrastructure.persistence.errors import PersistenceConsistencyError


def jsonb(value: Any) -> Jsonb:
    return Jsonb(value)


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
        scope=VisibilityScope(_text(row, "visibility_scope")),
        actor_id=None if actor_id is None else StableId(str(actor_id)),
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
        source=_text(row, "evidence_source"),
        reference=None if reference is None else StableId(str(reference)),
        excerpt=None if excerpt is None else str(excerpt),
    )


def entity_values(
    run_id: StableId,
    revision: int,
    position: int,
    entity: WorldEntity,
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
        id=StableId(_text(row, "entity_id")),
        kind=EntityKind(_text(row, "kind")),
        label=_text(row, "label"),
        description=str(row.get("description") or ""),
        actor=None if actor_role is None else ActorProfile(ActorRole(str(actor_role))),
        conditions=tuple(
            Condition(
                _json_text(item, "name"),
                _json_text(item, "description", default=""),
            )
            for item in _json_list(row.get("conditions"), "conditions")
        ),
        aliases=tuple(
            _value_text(item, "alias")
            for item in _json_list(row.get("aliases"), "aliases")
        ),
    )


def link_values(
    run_id: StableId,
    revision: int,
    position: int,
    link: EntityLink,
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
        id=StableId(_text(row, "link_id")),
        source_id=StableId(_text(row, "source_id")),
        target_id=StableId(_text(row, "target_id")),
        kind=RelationKind(_text(row, "kind")),
        visibility=visibility_from_row(row),
        quantity=None if quantity is None else int(quantity),
        description=str(row.get("description") or ""),
    )


def fact_values(
    run_id: StableId,
    revision: int,
    position: int,
    fact: Fact,
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
        id=StableId(_text(row, "fact_id")),
        statement=_text(row, "statement"),
        subject_id=None if subject_id is None else StableId(str(subject_id)),
        evidence=evidence_from_row(row),
        visibility=visibility_from_row(row),
    )


def knowledge_values(
    run_id: StableId,
    revision: int,
    position: int,
    entry: KnowledgeEntry,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "actor_id": str(entry.actor_id),
        "fact_id": str(entry.fact_id),
        "learned_at": entry.learned_at.value,
        "forgotten_at": (
            None if entry.forgotten_at is None else entry.forgotten_at.value
        ),
    }


def knowledge_from_row(row: Mapping[str, Any]) -> KnowledgeEntry:
    forgotten_at = row.get("forgotten_at")
    return KnowledgeEntry(
        actor_id=StableId(_text(row, "actor_id")),
        fact_id=StableId(_text(row, "fact_id")),
        learned_at=StorySequence(int(row["learned_at"])),
        forgotten_at=(
            None if forgotten_at is None else StorySequence(int(forgotten_at))
        ),
    )


def rule_values(
    run_id: StableId,
    revision: int,
    position: int,
    rule: WorldRule,
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
        id=StableId(_text(row, "rule_id")),
        statement=_text(row, "statement"),
        evidence=evidence_from_row(row),
        visibility=visibility_from_row(row),
    )


def event_values(
    run_id: StableId,
    revision: int,
    position: int,
    event: StoryEvent,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "event_id": str(event.id),
        "sequence": event.sequence.value,
        "kind": event.kind,
        "description": event.description,
        "participant_ids": jsonb([str(item) for item in event.participant_ids]),
        **visibility_values(event.visibility),
    }


def event_from_row(row: Mapping[str, Any]) -> StoryEvent:
    return StoryEvent(
        id=StableId(_text(row, "event_id")),
        sequence=StorySequence(int(row["sequence"])),
        kind=_text(row, "kind"),
        description=_text(row, "description"),
        participant_ids=tuple(
            StableId(_value_text(item, "participant"))
            for item in _json_list(row.get("participant_ids"), "participant_ids")
        ),
        visibility=visibility_from_row(row),
    )


def scene_values(
    run_id: StableId,
    revision: int,
    position: int,
    scene: Scene,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "scene_id": str(scene.id),
        "sequence": scene.sequence.value,
        "location_id": str(scene.location_id),
        "title": scene.title,
        "focus": scene.focus,
        "focus_entity_id": (
            None if scene.focus_entity_id is None else str(scene.focus_entity_id)
        ),
    }


def scene_participant_values(
    run_id: StableId,
    revision: int,
    scene_id: StableId,
    position: int,
    participant: Any,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "scene_id": str(scene_id),
        "position": position,
        "entity_id": str(participant.entity_id),
        "role": participant.role,
        **visibility_values(participant.visibility),
    }


def scene_from_rows(
    scene_row: Mapping[str, Any], participant_rows: list[Mapping[str, Any]]
) -> Scene:
    from story_game.domain import SceneParticipant

    return Scene(
        id=StableId(_text(scene_row, "scene_id")),
        sequence=StorySequence(int(scene_row["sequence"])),
        location_id=StableId(_text(scene_row, "location_id")),
        participants=tuple(
            SceneParticipant(
                entity_id=StableId(_text(row, "entity_id")),
                role=_text(row, "role"),
                visibility=visibility_from_row(row),
            )
            for row in participant_rows
        ),
        title=str(scene_row.get("title") or ""),
        focus=str(scene_row.get("focus") or ""),
        focus_entity_id=(
            None
            if scene_row.get("focus_entity_id") is None
            else StableId(str(scene_row["focus_entity_id"]))
        ),
    )


def chapter_values(
    run_id: StableId,
    revision: int,
    position: int,
    chapter: Chapter,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "chapter_id": str(chapter.id),
        "sequence": chapter.sequence,
        "title": chapter.title,
        "status": chapter.status.value,
        "summary": chapter.summary,
    }


def chapter_from_row(row: Mapping[str, Any]) -> Chapter:
    return Chapter(
        id=StableId(_text(row, "chapter_id")),
        sequence=int(row["sequence"]),
        title=_text(row, "title"),
        status=ChapterStatus(_text(row, "status")),
        summary=str(row.get("summary") or ""),
    )


def thread_values(
    run_id: StableId,
    revision: int,
    position: int,
    thread: StoryThread,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "thread_id": str(thread.id),
        "title": thread.title,
        "status": thread.status.value,
        "progress": thread.progress,
        "related_entity_ids": jsonb([str(item) for item in thread.related_entity_ids]),
    }


def thread_from_row(row: Mapping[str, Any]) -> StoryThread:
    return StoryThread(
        id=StableId(_text(row, "thread_id")),
        title=_text(row, "title"),
        status=ThreadStatus(_text(row, "status")),
        progress=int(row["progress"]),
        related_entity_ids=tuple(
            StableId(_value_text(item, "thread reference"))
            for item in _json_list(
                row.get("related_entity_ids"), "related_entity_ids"
            )
        ),
    )


def goal_values(
    run_id: StableId,
    revision: int,
    position: int,
    goal: Goal,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "goal_id": str(goal.id),
        "title": goal.title,
        "owner_id": None if goal.owner_id is None else str(goal.owner_id),
        "status": goal.status.value,
        "progress": goal.progress,
        "related_entity_ids": jsonb([str(item) for item in goal.related_entity_ids]),
    }


def goal_from_row(row: Mapping[str, Any]) -> Goal:
    owner_id = row.get("owner_id")
    return Goal(
        id=StableId(_text(row, "goal_id")),
        title=_text(row, "title"),
        owner_id=None if owner_id is None else StableId(str(owner_id)),
        status=GoalStatus(_text(row, "status")),
        progress=int(row["progress"]),
        related_entity_ids=tuple(
            StableId(_value_text(item, "goal reference"))
            for item in _json_list(
                row.get("related_entity_ids"), "related_entity_ids"
            )
        ),
    )


def summary_values(
    run_id: StableId,
    revision: int,
    position: int,
    summary: StorySummary,
) -> dict[str, Any]:
    return {
        "run_id": str(run_id),
        "revision": revision,
        "position": position,
        "from_sequence": summary.from_sequence.value,
        "through_sequence": summary.through_sequence.value,
        "text": summary.text,
        "based_on_revision": summary.based_on_revision.value,
    }


def summary_from_row(row: Mapping[str, Any]) -> StorySummary:
    return StorySummary(
        from_sequence=StorySequence(int(row["from_sequence"])),
        through_sequence=StorySequence(int(row["through_sequence"])),
        text=_text(row, "text"),
        based_on_revision=StateRevision(int(row["based_on_revision"])),
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


def _json_text(value: Mapping[str, Any], key: str, *, default: str | None = None) -> str:
    item = value.get(key, default)
    if not isinstance(item, str):
        raise PersistenceConsistencyError(f"Das JSON-Feld {key} muss Text sein")
    return item


def _value_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersistenceConsistencyError(f"{label} muss Text sein")
    return value
