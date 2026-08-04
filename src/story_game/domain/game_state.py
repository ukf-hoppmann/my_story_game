"""Aggregate root for one canonical storygame run."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .changes import (
    AddChapter,
    AddFact,
    AddGoal,
    AddLink,
    AddScene,
    AddThread,
    ApprovedChangeSet,
    CreateEntity,
    GrantKnowledge,
    RecordEvent,
    RemoveLink,
    SetCurrentScene,
    StateOperation,
    UpdateEntity,
    UpdateGoal,
    UpdateThread,
)
from .errors import ChangeRejectedError, InvalidReferenceError, RevisionConflictError
from .story import StoryState
from .value_objects import StableId, StateRevision, VisibilityScope
from .world import WorldState


@dataclass(frozen=True, slots=True)
class GameState:
    """Canonical state; only approved, revision-checked changes can advance it."""

    id: StableId
    revision: StateRevision
    world: WorldState
    story: StoryState
    player_actor_id: StableId | None = None

    def __post_init__(self) -> None:
        if self.player_actor_id is not None:
            player = self.world.entity(self.player_actor_id)
            if player.actor is None:
                raise InvalidReferenceError("Der Spieler muss auf einen Akteur zeigen")

        entity_ids = {entity.id for entity in self.world.entities}
        actor_ids = {
            entity.id for entity in self.world.entities if entity.actor is not None
        }
        for scene in self.story.scenes:
            if scene.location_id not in entity_ids:
                raise InvalidReferenceError("Eine Szene verweist auf einen unbekannten Ort")
            participant_ids = {participant.entity_id for participant in scene.participants}
            if not participant_ids.issubset(entity_ids):
                raise InvalidReferenceError(
                    "Eine Szene verweist auf unbekannte Teilnehmer"
                )
            if scene.focus_entity_id is not None and scene.focus_entity_id not in participant_ids:
                raise InvalidReferenceError(
                    "Der Szenenfokus muss ein Szenenteilnehmer sein"
                )
            self._validate_visibility(scene.participants, actor_ids)

        for event in self.story.events:
            if not set(event.participant_ids).issubset(entity_ids):
                raise InvalidReferenceError(
                    "Ein Ereignis verweist auf unbekannte Teilnehmer"
                )

        for thread in self.story.threads:
            if not set(thread.related_entity_ids).issubset(entity_ids):
                raise InvalidReferenceError(
                    "Ein Thread verweist auf unbekannte Entitäten"
                )

        for goal in self.story.goals:
            if goal.owner_id is not None and goal.owner_id not in actor_ids:
                raise InvalidReferenceError("Ein Ziel muss einem Akteur gehören")
            if not set(goal.related_entity_ids).issubset(entity_ids):
                raise InvalidReferenceError(
                    "Ein Ziel verweist auf unbekannte Entitäten"
                )

    @staticmethod
    def _validate_visibility(items: tuple[object, ...], actor_ids: set[StableId]) -> None:
        for item in items:
            visibility = getattr(item, "visibility")
            if (
                visibility.scope is VisibilityScope.ACTOR_KNOWN
                and visibility.actor_id not in actor_ids
            ):
                raise InvalidReferenceError(
                    "Akteurspezifische Sichtbarkeit benötigt einen gültigen Akteur"
                )

    def apply(self, changes: ApprovedChangeSet) -> GameState:
        """Apply only application-approved operations as one new state revision."""
        if not isinstance(changes, ApprovedChangeSet):
            raise ChangeRejectedError(
                "Der GameState akzeptiert ausschließlich freigegebene Änderungssätze"
            )
        if changes.base_revision != self.revision:
            raise RevisionConflictError(
                "Der Änderungssatz basiert nicht auf der aktuellen State-Revision"
            )

        current = self
        for operation in changes.changes:
            current = current._apply_operation(operation)
        return replace(current, revision=self.revision.next())

    def _apply_operation(self, operation: StateOperation) -> GameState:
        if isinstance(operation, CreateEntity):
            return replace(self, world=self.world.add_entity(operation.entity))
        if isinstance(operation, UpdateEntity):
            return replace(self, world=self.world.update_entity(operation.entity))
        if isinstance(operation, AddLink):
            return replace(self, world=self.world.add_link(operation.link))
        if isinstance(operation, RemoveLink):
            return replace(self, world=self.world.remove_link(operation.link_id))
        if isinstance(operation, AddFact):
            return replace(self, world=self.world.add_fact(operation.fact))
        if isinstance(operation, GrantKnowledge):
            return replace(self, world=self.world.add_knowledge(operation.entry))
        if isinstance(operation, RecordEvent):
            return replace(self, story=self.story.add_event(operation.event))
        if isinstance(operation, AddScene):
            return replace(self, story=self.story.add_scene(operation.scene))
        if isinstance(operation, SetCurrentScene):
            return replace(self, story=self.story.set_current_scene(operation.scene_id))
        if isinstance(operation, AddChapter):
            return replace(self, story=self.story.add_chapter(operation.chapter))
        if isinstance(operation, AddThread):
            return replace(self, story=self.story.add_thread(operation.thread))
        if isinstance(operation, UpdateThread):
            return replace(self, story=self.story.update_thread(operation.thread))
        if isinstance(operation, AddGoal):
            return replace(self, story=self.story.add_goal(operation.goal))
        if isinstance(operation, UpdateGoal):
            return replace(self, story=self.story.update_goal(operation.goal))
        raise ChangeRejectedError(f"Nicht unterstützte Zustandsoperation: {operation!r}")
