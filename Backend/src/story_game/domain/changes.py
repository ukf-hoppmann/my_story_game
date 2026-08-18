"""Application-approved operations accepted by the canonical world state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .value_objects import StableId, StateRevision
from .world import EntityLink, Fact, Goal, KnowledgeEntry, WorldEntity


@dataclass(frozen=True, slots=True)
class CreateEntity:
    entity: WorldEntity


@dataclass(frozen=True, slots=True)
class UpdateEntity:
    entity: WorldEntity


@dataclass(frozen=True, slots=True)
class AddLink:
    link: EntityLink


@dataclass(frozen=True, slots=True)
class RemoveLink:
    link_id: StableId


@dataclass(frozen=True, slots=True)
class AddFact:
    fact: Fact


@dataclass(frozen=True, slots=True)
class RemoveFact:
    """Retire a statement the story has made untrue.

    Without this facts could only ever accumulate, so a door unlocked during
    play would keep contradicting every later prompt.
    """

    fact_id: StableId


@dataclass(frozen=True, slots=True)
class SetSceneLocations:
    """Move where the narration looks, most relevant location first.

    Distinct from a location link: that records where an entity is, this where
    the story is being told. An empty tuple clears the scene.
    """

    location_ids: tuple[StableId, ...] = ()


@dataclass(frozen=True, slots=True)
class GrantKnowledge:
    entry: KnowledgeEntry


@dataclass(frozen=True, slots=True)
class AddGoal:
    goal: Goal


@dataclass(frozen=True, slots=True)
class UpdateGoal:
    goal: Goal


StateOperation: TypeAlias = (
    CreateEntity
    | UpdateEntity
    | AddLink
    | RemoveLink
    | AddFact
    | RemoveFact
    | GrantKnowledge
    | AddGoal
    | UpdateGoal
    | SetSceneLocations
)


@dataclass(frozen=True, slots=True)
class ApprovedChangeSet:
    """Revision-bound world operations approved outside the Domain layer."""

    proposal_id: StableId
    base_revision: StateRevision
    changes: tuple[StateOperation, ...] = ()
