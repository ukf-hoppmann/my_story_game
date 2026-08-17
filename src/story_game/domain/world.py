"""Canonical world-state entities for the narrative core."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .errors import InvalidReferenceError, ValidationError
from .value_objects import (
    ActorRole,
    EntityKind,
    GoalKind,
    GoalStatus,
    RelationKind,
    StableId,
    StorySequence,
    Visibility,
)


def _require_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValidationError(f"{field_name} darf nicht leer sein")
    return value


def _unique_ids(items: tuple[object, ...], field_name: str) -> None:
    ids = [getattr(item, "id", None) for item in items]
    if len(ids) != len(set(ids)):
        raise ValidationError(f"{field_name} müssen eindeutige IDs besitzen")


@dataclass(frozen=True, slots=True)
class ActorProfile:
    """Role information for a world entity that can act or know facts."""

    role: ActorRole


@dataclass(frozen=True, slots=True)
class Condition:
    """A current narrative condition without RPG-specific mechanics."""

    name: str
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _require_text(self.name, "Der Zustandsname"))
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class WorldEntity:
    """Stable identity and current narrative profile of a world object."""

    id: StableId
    kind: EntityKind
    label: str
    description: str = ""
    actor: ActorProfile | None = None
    conditions: tuple[Condition, ...] = ()
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", _require_text(self.label, "Die Bezeichnung"))
        object.__setattr__(self, "description", self.description.strip())
        aliases = tuple(alias.strip() for alias in self.aliases if alias.strip())
        if len(aliases) != len(set(aliases)):
            raise ValidationError("Aliase einer Entität müssen eindeutig sein")
        object.__setattr__(self, "aliases", aliases)
        if self.actor is not None and self.kind not in {
            EntityKind.CHARACTER,
            EntityKind.CREATURE,
            EntityKind.FACTION,
        }:
            raise ValidationError(
                "Nur Charaktere, Kreaturen und Fraktionen können Akteure sein"
            )

    @property
    def is_actor(self) -> bool:
        return self.actor is not None


@dataclass(frozen=True, slots=True)
class EntityLink:
    """A typed, current relationship between two world entities."""

    id: StableId
    source_id: StableId
    target_id: StableId
    kind: RelationKind
    visibility: Visibility = field(default_factory=Visibility.public)
    quantity: int | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if self.source_id == self.target_id:
            raise ValidationError("Eine Entitätsbeziehung darf nicht auf sich selbst zeigen")
        if self.quantity is not None:
            if self.quantity < 1:
                raise ValidationError("Eine Beziehungsmenge muss positiv sein")
            if self.kind not in {RelationKind.POSSESSES, RelationKind.CONTAINS}:
                raise ValidationError(
                    "Mengen sind nur für Besitz- und Behälterbeziehungen erlaubt"
                )
        object.__setattr__(self, "description", self.description.strip())


@dataclass(frozen=True, slots=True)
class Fact:
    """A confirmed canonical statement about the story world."""

    id: StableId
    statement: str
    visibility: Visibility = field(default_factory=Visibility.public)
    subject_id: StableId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "statement", _require_text(self.statement, "Eine Tatsache")
        )


@dataclass(frozen=True, slots=True)
class KnowledgeEntry:
    """The fact-knowledge relation for one actor."""

    actor_id: StableId
    fact_id: StableId
    learned_at: StorySequence
    forgotten_at: StorySequence | None = None

    def __post_init__(self) -> None:
        if self.forgotten_at is not None and self.forgotten_at < self.learned_at:
            raise ValidationError(
                "Ein Vergessenszeitpunkt darf nicht vor dem Lernzeitpunkt liegen"
            )


@dataclass(frozen=True, slots=True)
class WorldRule:
    """A confirmed rule or boundary of the fictional world."""

    id: StableId
    statement: str
    visibility: Visibility = field(default_factory=Visibility.public)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "statement", _require_text(self.statement, "Eine Weltregel")
        )


@dataclass(frozen=True, slots=True)
class Goal:
    """A main or side objective in the structured canonical game state."""

    id: StableId
    kind: GoalKind
    title: str
    description: str
    status: GoalStatus = GoalStatus.OPEN
    related_entity_ids: tuple[StableId, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _require_text(self.title, "Der Zieltitel"))
        object.__setattr__(
            self, "description", _require_text(self.description, "Die Zielbeschreibung")
        )
        if len(self.related_entity_ids) != len(set(self.related_entity_ids)):
            raise ValidationError("Zielreferenzen müssen eindeutig sein")


@dataclass(frozen=True, slots=True)
class WorldState:
    """Canonical world data with referential and relationship invariants."""

    entities: tuple[WorldEntity, ...] = ()
    links: tuple[EntityLink, ...] = ()
    facts: tuple[Fact, ...] = ()
    knowledge: tuple[KnowledgeEntry, ...] = ()
    rules: tuple[WorldRule, ...] = ()
    goals: tuple[Goal, ...] = ()
    scene_location_ids: tuple[StableId, ...] = ()
    """Where the narration currently looks, most relevant location first.

    This is a separate statement from the ``LOCATED_IN`` links: those say where
    an entity *is*, the scene says where the story is being told. Director
    control may narrate a scene the controlled character is not part of, so the
    scene must not be derived from any entity's location.
    """

    def __post_init__(self) -> None:
        _unique_ids(self.entities, "Entitäten")
        _unique_ids(self.links, "Beziehungen")
        _unique_ids(self.facts, "Fakten")
        _unique_ids(self.rules, "Weltregeln")
        _unique_ids(self.goals, "Ziele")

        entities = {entity.id: entity for entity in self.entities}
        facts = {fact.id: fact for fact in self.facts}
        knowledge_keys: set[tuple[StableId, StableId]] = set()
        location_sources: set[StableId] = set()
        possession_targets: set[StableId] = set()

        for link in self.links:
            source = entities.get(link.source_id)
            target = entities.get(link.target_id)
            if source is None or target is None:
                raise InvalidReferenceError(
                    "Eine Beziehung muss auf vorhandene Entitäten verweisen"
                )
            if link.kind is RelationKind.LOCATED_IN:
                if target.kind is not EntityKind.LOCATION:
                    raise ValidationError(
                        "Eine Aufenthaltsbeziehung muss auf einen Ort zeigen"
                    )
                if link.source_id in location_sources:
                    raise ValidationError(
                        "Eine Entität darf nur einen aktuellen Aufenthaltsort besitzen"
                    )
                location_sources.add(link.source_id)
            elif link.kind is RelationKind.POSSESSES:
                if not source.is_actor:
                    raise ValidationError("Nur Akteure können Gegenstände besitzen")
                if target.kind is not EntityKind.ITEM:
                    raise ValidationError("Besitzbeziehungen müssen auf Gegenstände zeigen")
                if target.id in possession_targets:
                    raise ValidationError(
                        "Ein Gegenstand darf nur einen aktuellen Besitzer besitzen"
                    )
                possession_targets.add(target.id)
            elif link.kind is RelationKind.CONTAINS and target.kind is EntityKind.LOCATION:
                raise ValidationError("Ein Ort kann nicht in einem Gegenstand enthalten sein")
            elif link.kind is RelationKind.MEMBER_OF:
                if target.kind is not EntityKind.FACTION:
                    raise ValidationError(
                        "Zugehörigkeitsbeziehungen müssen auf Fraktionen zeigen"
                    )
            elif link.kind is RelationKind.KNOWS:
                if not source.is_actor or not target.is_actor:
                    raise ValidationError("Bekanntschaften benötigen zwei Akteure")

        for fact in self.facts:
            if fact.subject_id is not None and fact.subject_id not in entities:
                raise InvalidReferenceError(
                    "Eine Tatsache muss auf eine vorhandene Entität verweisen"
                )

        for entry in self.knowledge:
            if entry.actor_id not in entities or not entities[entry.actor_id].is_actor:
                raise InvalidReferenceError(
                    "Wissen muss einem vorhandenen Akteur zugeordnet sein"
                )
            if entry.fact_id not in facts:
                raise InvalidReferenceError(
                    "Wissen muss auf eine vorhandene Tatsache verweisen"
                )
            key = (entry.actor_id, entry.fact_id)
            if key in knowledge_keys:
                raise ValidationError(
                    "Ein Akteur darf denselben Fakt nur einmal als Wissen besitzen"
                )
            knowledge_keys.add(key)

        for goal in self.goals:
            if not set(goal.related_entity_ids).issubset(entities):
                raise InvalidReferenceError(
                    "Ein Ziel muss auf vorhandene Entitäten verweisen"
                )

        if len(self.scene_location_ids) != len(set(self.scene_location_ids)):
            raise ValidationError("Schauplätze einer Szene müssen eindeutig sein")
        for location_id in self.scene_location_ids:
            location = entities.get(location_id)
            if location is None:
                raise InvalidReferenceError(
                    "Ein Schauplatz muss auf eine vorhandene Entität verweisen"
                )
            if location.kind is not EntityKind.LOCATION:
                raise ValidationError("Ein Schauplatz muss ein Ort sein")

    def primary_scene_location(self) -> StableId | None:
        """Return the location the narration currently focuses on, if any."""
        return self.scene_location_ids[0] if self.scene_location_ids else None

    def entity(self, entity_id: StableId) -> WorldEntity:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        raise InvalidReferenceError(f"Unbekannte Entität: {entity_id}")

    def goal(self, goal_id: StableId) -> Goal:
        for goal in self.goals:
            if goal.id == goal_id:
                return goal
        raise InvalidReferenceError(f"Unbekanntes Ziel: {goal_id}")

    def add_goal(self, goal: Goal) -> WorldState:
        if any(existing.id == goal.id for existing in self.goals):
            raise ValidationError(f"Die Ziel-ID existiert bereits: {goal.id}")
        return replace(self, goals=(*self.goals, goal))

    def update_goal(self, goal: Goal) -> WorldState:
        if not any(existing.id == goal.id for existing in self.goals):
            raise InvalidReferenceError(f"Unbekanntes Ziel: {goal.id}")
        return replace(
            self,
            goals=tuple(
                goal if existing.id == goal.id else existing for existing in self.goals
            ),
        )

    def fact(self, fact_id: StableId) -> Fact:
        for fact in self.facts:
            if fact.id == fact_id:
                return fact
        raise InvalidReferenceError(f"Unbekannte Tatsache: {fact_id}")

    def add_entity(self, entity: WorldEntity) -> WorldState:
        if any(existing.id == entity.id for existing in self.entities):
            raise ValidationError(f"Die Entitäts-ID existiert bereits: {entity.id}")
        return replace(self, entities=(*self.entities, entity))

    def update_entity(self, entity: WorldEntity) -> WorldState:
        current = self.entity(entity.id)
        if current.kind is not entity.kind:
            raise ValidationError("Der Typ einer stabilen Entität darf nicht wechseln")
        entities = tuple(
            entity if existing.id == entity.id else existing for existing in self.entities
        )
        return replace(self, entities=entities)

    def add_link(self, link: EntityLink) -> WorldState:
        if any(existing.id == link.id for existing in self.links):
            raise ValidationError(f"Die Beziehungs-ID existiert bereits: {link.id}")
        return replace(self, links=(*self.links, link))

    def remove_link(self, link_id: StableId) -> WorldState:
        if not any(link.id == link_id for link in self.links):
            raise InvalidReferenceError(f"Unbekannte Beziehung: {link_id}")
        return replace(
            self, links=tuple(link for link in self.links if link.id != link_id)
        )

    def add_fact(self, fact: Fact) -> WorldState:
        if any(existing.id == fact.id for existing in self.facts):
            raise ValidationError(f"Die Fakten-ID existiert bereits: {fact.id}")
        return replace(self, facts=(*self.facts, fact))

    def add_knowledge(self, entry: KnowledgeEntry) -> WorldState:
        return replace(self, knowledge=(*self.knowledge, entry))

    def inventory(self, owner_id: StableId) -> tuple[WorldEntity, ...]:
        owner = self.entity(owner_id)
        if not owner.is_actor:
            raise ValidationError("Nur Akteure können ein Inventar besitzen")
        item_ids = {
            link.target_id
            for link in self.links
            if link.kind is RelationKind.POSSESSES and link.source_id == owner_id
        }
        return tuple(entity for entity in self.entities if entity.id in item_ids)

    def location_of(self, entity_id: StableId) -> StableId | None:
        self.entity(entity_id)
        for link in self.links:
            if link.kind is RelationKind.LOCATED_IN and link.source_id == entity_id:
                return link.target_id
        return None
