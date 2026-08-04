"""Strict JSON mapping for the current domain model."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from story_game.domain import (
    ActorProfile,
    ActorRole,
    Chapter,
    ChapterStatus,
    Condition,
    EntityKind,
    EntityLink,
    Evidence,
    Fact,
    GameState,
    Goal,
    GoalStatus,
    KnowledgeEntry,
    RelationKind,
    Scene,
    SceneParticipant,
    StableId,
    StateRevision,
    StoryEvent,
    StorySequence,
    StoryState,
    StorySummary,
    StoryThread,
    ThreadStatus,
    Visibility,
    VisibilityScope,
    WorldEntity,
    WorldRule,
    WorldState,
)
from story_game.infrastructure.persistence.errors import PersistenceConsistencyError


SCHEMA_VERSION = 1


def state_to_document(state: GameState) -> dict[str, Any]:
    """Convert a validated domain state into a deterministic storage document."""
    return {
        "schema_version": SCHEMA_VERSION,
        "state_revision": state.revision.value,
        "game_state": {
            "id": str(state.id),
            "player_actor_id": _optional_id(state.player_actor_id),
        },
        "world": {
            "entities": [_entity_to_json(item) for item in state.world.entities],
            "links": [_link_to_json(item) for item in state.world.links],
            "facts": [_fact_to_json(item) for item in state.world.facts],
            "knowledge": [_knowledge_to_json(item) for item in state.world.knowledge],
            "rules": [_rule_to_json(item) for item in state.world.rules],
        },
        "story": {
            "events": [_event_to_json(item) for item in state.story.events],
            "scenes": [_scene_to_json(item) for item in state.story.scenes],
            "chapters": [_chapter_to_json(item) for item in state.story.chapters],
            "threads": [_thread_to_json(item) for item in state.story.threads],
            "goals": [_goal_to_json(item) for item in state.story.goals],
            "summaries": [_summary_to_json(item) for item in state.story.summaries],
            "current_scene_id": _optional_id(state.story.current_scene_id),
            "current_chapter_id": _optional_id(state.story.current_chapter_id),
            "current_sequence": state.story.current_sequence,
        },
    }


def state_from_document(document: Mapping[str, Any]) -> GameState:
    """Build and validate a domain state from one versioned JSON document."""
    _require_mapping(document, "Das JSON-Dokument")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise PersistenceConsistencyError(
            f"Unbekannte JSON-Schema-Version: {document.get('schema_version')!r}"
        )

    game_data = _mapping(document, "game_state")
    world_data = _mapping(document, "world")
    story_data = _mapping(document, "story")
    try:
        world = WorldState(
            entities=tuple(
                _entity_from_json(item) for item in _list(world_data, "entities")
            ),
            links=tuple(_link_from_json(item) for item in _list(world_data, "links")),
            facts=tuple(_fact_from_json(item) for item in _list(world_data, "facts")),
            knowledge=tuple(
                _knowledge_from_json(item) for item in _list(world_data, "knowledge")
            ),
            rules=tuple(_rule_from_json(item) for item in _list(world_data, "rules")),
        )
        story = StoryState(
            events=tuple(
                _event_from_json(item) for item in _list(story_data, "events")
            ),
            scenes=tuple(
                _scene_from_json(item) for item in _list(story_data, "scenes")
            ),
            chapters=tuple(
                _chapter_from_json(item) for item in _list(story_data, "chapters")
            ),
            threads=tuple(
                _thread_from_json(item) for item in _list(story_data, "threads")
            ),
            goals=tuple(_goal_from_json(item) for item in _list(story_data, "goals")),
            summaries=tuple(
                _summary_from_json(item) for item in _list(story_data, "summaries")
            ),
            current_scene_id=_optional_stable_id(story_data.get("current_scene_id")),
            current_chapter_id=_optional_stable_id(
                story_data.get("current_chapter_id")
            ),
            current_sequence=_int(story_data, "current_sequence"),
        )
        return GameState(
            id=_stable_id(game_data, "id"),
            revision=StateRevision(_int(document, "state_revision")),
            world=world,
            story=story,
            player_actor_id=_optional_stable_id(game_data.get("player_actor_id")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PersistenceConsistencyError(
            f"JSON-Dokument konnte nicht in den GameState übersetzt werden: {exc}"
        ) from exc


def _entity_to_json(entity: WorldEntity) -> dict[str, Any]:
    return {
        "id": str(entity.id),
        "kind": entity.kind.value,
        "label": entity.label,
        "description": entity.description,
        "actor": None
        if entity.actor is None
        else {"role": entity.actor.role.value},
        "conditions": [
            {"name": condition.name, "description": condition.description}
            for condition in entity.conditions
        ],
        "aliases": list(entity.aliases),
    }


def _entity_from_json(data: Any) -> WorldEntity:
    item = _require_mapping(data, "Entität")
    actor_data = item.get("actor")
    return WorldEntity(
        id=_stable_id(item, "id"),
        kind=EntityKind(_string(item, "kind")),
        label=_string(item, "label"),
        description=_string(item, "description", default=""),
        actor=None
        if actor_data is None
        else ActorProfile(ActorRole(_string(_require_mapping(actor_data, "Akteur"), "role"))),
        conditions=tuple(
            Condition(
                _string(_require_mapping(condition, "Bedingung"), "name"),
                _string(_require_mapping(condition, "Bedingung"), "description", default=""),
            )
            for condition in _list(item, "conditions")
        ),
        aliases=tuple(_string_value(alias, "Alias") for alias in _list(item, "aliases")),
    )


def _link_to_json(link: EntityLink) -> dict[str, Any]:
    return {
        "id": str(link.id),
        "source_id": str(link.source_id),
        "target_id": str(link.target_id),
        "kind": link.kind.value,
        "visibility": _visibility_to_json(link.visibility),
        "quantity": link.quantity,
        "description": link.description,
    }


def _link_from_json(data: Any) -> EntityLink:
    item = _require_mapping(data, "Beziehung")
    return EntityLink(
        id=_stable_id(item, "id"),
        source_id=_stable_id(item, "source_id"),
        target_id=_stable_id(item, "target_id"),
        kind=RelationKind(_string(item, "kind")),
        visibility=_visibility_from_json(item.get("visibility")),
        quantity=_optional_int(item.get("quantity")),
        description=_string(item, "description", default=""),
    )


def _fact_to_json(fact: Fact) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "statement": fact.statement,
        "subject_id": _optional_id(fact.subject_id),
        "evidence": _evidence_to_json(fact.evidence),
        "visibility": _visibility_to_json(fact.visibility),
    }


def _fact_from_json(data: Any) -> Fact:
    item = _require_mapping(data, "Fakt")
    return Fact(
        id=_stable_id(item, "id"),
        statement=_string(item, "statement"),
        subject_id=_optional_stable_id(item.get("subject_id")),
        evidence=_evidence_from_json(item.get("evidence")),
        visibility=_visibility_from_json(item.get("visibility")),
    )


def _knowledge_to_json(entry: KnowledgeEntry) -> dict[str, Any]:
    return {
        "actor_id": str(entry.actor_id),
        "fact_id": str(entry.fact_id),
        "learned_at": entry.learned_at.value,
        "forgotten_at": None
        if entry.forgotten_at is None
        else entry.forgotten_at.value,
    }


def _knowledge_from_json(data: Any) -> KnowledgeEntry:
    item = _require_mapping(data, "Wissenseintrag")
    return KnowledgeEntry(
        actor_id=_stable_id(item, "actor_id"),
        fact_id=_stable_id(item, "fact_id"),
        learned_at=StorySequence(_int(item, "learned_at")),
        forgotten_at=(
            None
            if item.get("forgotten_at") is None
            else StorySequence(_int(item, "forgotten_at"))
        ),
    )


def _rule_to_json(rule: WorldRule) -> dict[str, Any]:
    return {
        "id": str(rule.id),
        "statement": rule.statement,
        "evidence": _evidence_to_json(rule.evidence),
        "visibility": _visibility_to_json(rule.visibility),
    }


def _rule_from_json(data: Any) -> WorldRule:
    item = _require_mapping(data, "Weltregel")
    return WorldRule(
        id=_stable_id(item, "id"),
        statement=_string(item, "statement"),
        evidence=_evidence_from_json(item.get("evidence")),
        visibility=_visibility_from_json(item.get("visibility")),
    )


def _event_to_json(event: StoryEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "sequence": event.sequence.value,
        "kind": event.kind,
        "description": event.description,
        "participant_ids": [str(item) for item in event.participant_ids],
        "visibility": _visibility_to_json(event.visibility),
    }


def _event_from_json(data: Any) -> StoryEvent:
    item = _require_mapping(data, "Ereignis")
    return StoryEvent(
        id=_stable_id(item, "id"),
        sequence=StorySequence(_int(item, "sequence")),
        kind=_string(item, "kind"),
        description=_string(item, "description"),
        participant_ids=tuple(
            _stable_id_value(value, "Ereignisteilnehmer")
            for value in _list(item, "participant_ids")
        ),
        visibility=_visibility_from_json(item.get("visibility")),
    )


def _scene_to_json(scene: Scene) -> dict[str, Any]:
    return {
        "id": str(scene.id),
        "sequence": scene.sequence.value,
        "location_id": str(scene.location_id),
        "participants": [
            {
                "entity_id": str(participant.entity_id),
                "role": participant.role,
                "visibility": _visibility_to_json(participant.visibility),
            }
            for participant in scene.participants
        ],
        "title": scene.title,
        "focus": scene.focus,
        "focus_entity_id": _optional_id(scene.focus_entity_id),
    }


def _scene_from_json(data: Any) -> Scene:
    item = _require_mapping(data, "Szene")
    participants = []
    for participant in _list(item, "participants"):
        participant_data = _require_mapping(participant, "Szenenteilnehmer")
        participants.append(
            SceneParticipant(
                entity_id=_stable_id(participant_data, "entity_id"),
                role=_string(participant_data, "role"),
                visibility=_visibility_from_json(participant_data.get("visibility")),
            )
        )
    return Scene(
        id=_stable_id(item, "id"),
        sequence=StorySequence(_int(item, "sequence")),
        location_id=_stable_id(item, "location_id"),
        participants=tuple(participants),
        title=_string(item, "title", default=""),
        focus=_string(item, "focus", default=""),
        focus_entity_id=_optional_stable_id(item.get("focus_entity_id")),
    )


def _chapter_to_json(chapter: Chapter) -> dict[str, Any]:
    return {
        "id": str(chapter.id),
        "sequence": chapter.sequence,
        "title": chapter.title,
        "status": chapter.status.value,
        "summary": chapter.summary,
    }


def _chapter_from_json(data: Any) -> Chapter:
    item = _require_mapping(data, "Kapitel")
    return Chapter(
        id=_stable_id(item, "id"),
        sequence=_int(item, "sequence"),
        title=_string(item, "title"),
        status=ChapterStatus(_string(item, "status")),
        summary=_string(item, "summary", default=""),
    )


def _thread_to_json(thread: StoryThread) -> dict[str, Any]:
    return {
        "id": str(thread.id),
        "title": thread.title,
        "status": thread.status.value,
        "progress": thread.progress,
        "related_entity_ids": [str(item) for item in thread.related_entity_ids],
    }


def _thread_from_json(data: Any) -> StoryThread:
    item = _require_mapping(data, "Story-Thread")
    return StoryThread(
        id=_stable_id(item, "id"),
        title=_string(item, "title"),
        status=ThreadStatus(_string(item, "status")),
        progress=_int(item, "progress"),
        related_entity_ids=tuple(
            _stable_id_value(value, "Thread-Referenz")
            for value in _list(item, "related_entity_ids")
        ),
    )


def _goal_to_json(goal: Goal) -> dict[str, Any]:
    return {
        "id": str(goal.id),
        "title": goal.title,
        "owner_id": _optional_id(goal.owner_id),
        "status": goal.status.value,
        "progress": goal.progress,
        "related_entity_ids": [str(item) for item in goal.related_entity_ids],
    }


def _goal_from_json(data: Any) -> Goal:
    item = _require_mapping(data, "Ziel")
    return Goal(
        id=_stable_id(item, "id"),
        title=_string(item, "title"),
        owner_id=_optional_stable_id(item.get("owner_id")),
        status=GoalStatus(_string(item, "status")),
        progress=_int(item, "progress"),
        related_entity_ids=tuple(
            _stable_id_value(value, "Zielreferenz")
            for value in _list(item, "related_entity_ids")
        ),
    )


def _summary_to_json(summary: StorySummary) -> dict[str, Any]:
    return {
        "from_sequence": summary.from_sequence.value,
        "through_sequence": summary.through_sequence.value,
        "text": summary.text,
        "based_on_revision": summary.based_on_revision.value,
    }


def _summary_from_json(data: Any) -> StorySummary:
    item = _require_mapping(data, "Zusammenfassung")
    return StorySummary(
        from_sequence=StorySequence(_int(item, "from_sequence")),
        through_sequence=StorySequence(_int(item, "through_sequence")),
        text=_string(item, "text"),
        based_on_revision=StateRevision(_int(item, "based_on_revision")),
    )


def _visibility_to_json(visibility: Visibility) -> dict[str, Any]:
    return {
        "scope": visibility.scope.value,
        "actor_id": _optional_id(visibility.actor_id),
    }


def _visibility_from_json(data: Any) -> Visibility:
    item = _require_mapping(data, "Sichtbarkeit")
    return Visibility(
        scope=VisibilityScope(_string(item, "scope")),
        actor_id=_optional_stable_id(item.get("actor_id")),
    )


def _evidence_to_json(evidence: Evidence) -> dict[str, Any]:
    return {
        "source": evidence.source,
        "reference": _optional_id(evidence.reference),
        "excerpt": evidence.excerpt,
    }


def _evidence_from_json(data: Any) -> Evidence:
    item = _require_mapping(data, "Evidenz")
    return Evidence(
        source=_string(item, "source"),
        reference=_optional_stable_id(item.get("reference")),
        excerpt=_optional_string(item.get("excerpt")),
    )


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PersistenceConsistencyError(f"{label} muss ein Objekt sein")
    return value


def _mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    return _require_mapping(data.get(key), key)


def _list(data: Mapping[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    if not isinstance(value, list):
        raise PersistenceConsistencyError(f"{key} muss eine Liste sein")
    return value


def _string(data: Mapping[str, Any], key: str, *, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise PersistenceConsistencyError(f"{key} muss Text sein")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PersistenceConsistencyError("Ein optionaler Textwert ist ungültig")
    return value


def _string_value(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise PersistenceConsistencyError(f"{label} muss Text sein")
    return value


def _int(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PersistenceConsistencyError(f"{key} muss eine Ganzzahl sein")
    return value


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PersistenceConsistencyError("Ein optionaler Ganzzahlwert ist ungültig")
    return value


def _stable_id(data: Mapping[str, Any], key: str) -> StableId:
    return _stable_id_value(data.get(key), key)


def _stable_id_value(value: Any, label: str) -> StableId:
    if not isinstance(value, str):
        raise PersistenceConsistencyError(f"{label} muss eine ID enthalten")
    return StableId(value)


def _optional_stable_id(value: Any) -> StableId | None:
    if value is None:
        return None
    return _stable_id_value(value, "ID")


def _optional_id(value: StableId | None) -> str | None:
    return None if value is None else str(value)
