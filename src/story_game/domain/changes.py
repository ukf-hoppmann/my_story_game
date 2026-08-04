"""Model-independent proposals and approved operations on the game state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

from .errors import ValidationError
from .story import Chapter, Goal, Scene, StoryEvent, StoryThread
from .value_objects import Evidence, StableId, StateRevision, Visibility
from .world import EntityLink, Fact, KnowledgeEntry, WorldEntity


class ChangeDomain(StrEnum):
    WORLD = "worldstate"
    STORY = "story_state"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


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
class GrantKnowledge:
    entry: KnowledgeEntry


@dataclass(frozen=True, slots=True)
class RecordEvent:
    event: StoryEvent


@dataclass(frozen=True, slots=True)
class AddScene:
    scene: Scene


@dataclass(frozen=True, slots=True)
class SetCurrentScene:
    scene_id: StableId


@dataclass(frozen=True, slots=True)
class AddChapter:
    chapter: Chapter


@dataclass(frozen=True, slots=True)
class AddThread:
    thread: StoryThread


@dataclass(frozen=True, slots=True)
class UpdateThread:
    thread: StoryThread


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
    | GrantKnowledge
    | RecordEvent
    | AddScene
    | SetCurrentScene
    | AddChapter
    | AddThread
    | UpdateThread
    | AddGoal
    | UpdateGoal
)


def operation_domain(operation: StateOperation) -> ChangeDomain:
    if isinstance(
        operation,
        (CreateEntity, UpdateEntity, AddLink, RemoveLink, AddFact, GrantKnowledge),
    ):
        return ChangeDomain.WORLD
    return ChangeDomain.STORY


@dataclass(frozen=True, slots=True)
class ProposedChange:
    """One typed suggestion awaiting application-level review."""

    id: StableId
    operation: StateOperation
    evidence: Evidence
    visibility: Visibility

    @property
    def target_domain(self) -> ChangeDomain:
        return operation_domain(self.operation)


@dataclass(frozen=True, slots=True)
class ProposedChangeSet:
    """Untrusted, non-canonical changes returned by an application adapter."""

    id: StableId
    base_revision: StateRevision
    changes: tuple[ProposedChange, ...] = ()
    status: ProposalStatus = ProposalStatus.PENDING


@dataclass(frozen=True, slots=True)
class ApprovedChangeSet:
    """Application-approved operations that the canonical state may consume."""

    proposal_id: StableId
    base_revision: StateRevision
    changes: tuple[StateOperation, ...] = ()

    def __post_init__(self) -> None:
        if not self.proposal_id.value:
            raise ValidationError("Ein freigegebener Änderungssatz benötigt eine ID")
