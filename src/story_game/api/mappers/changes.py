"""Translate typed approved-change commands into domain operations."""

from __future__ import annotations

from story_game.domain import (
    AddChapter,
    AddFact,
    AddGoal,
    AddLink,
    AddScene,
    AddThread,
    ActorProfile,
    ActorRole,
    ApprovedChangeSet,
    Chapter,
    Condition,
    CreateEntity,
    EntityLink,
    EntityKind,
    Fact,
    Goal,
    GrantKnowledge,
    KnowledgeEntry,
    RecordEvent,
    RemoveLink,
    Scene,
    SceneParticipant,
    SetCurrentScene,
    StableId,
    StateRevision,
    StoryEvent,
    StorySequence,
    StoryThread,
    UpdateEntity,
    UpdateGoal,
    UpdateThread,
    Visibility,
    WorldEntity,
)

from story_game.api.schemas.changes import (
    AddChapterChange,
    AddFactChange,
    AddGoalChange,
    AddLinkChange,
    AddSceneChange,
    AddThreadChange,
    CreateEntityChange,
    GrantKnowledgeChange,
    RecordEventChange,
    RemoveLinkChange,
    SetCurrentSceneChange,
    StateChangeRequest,
    UpdateEntityChange,
    UpdateGoalChange,
    UpdateThreadChange,
)
from story_game.api.schemas.common import (
    ChapterModel,
    EntityLinkModel,
    EvidenceModel,
    FactModel,
    GoalModel,
    KnowledgeEntryModel,
    SceneModel,
    StoryEventModel,
    StoryThreadModel,
    VisibilityModel,
    WorldEntityModel,
)


def approved_changes_to_domain(
    request: "ApprovedChangeSetRequest",
) -> ApprovedChangeSet:
    from story_game.api.schemas.changes import ApprovedChangeSetRequest

    return ApprovedChangeSet(
        proposal_id=StableId(request.proposal_id),
        base_revision=StateRevision(request.base_revision),
        changes=tuple(_operation(change) for change in request.changes),
    )


def _operation(change: StateChangeRequest):
    if isinstance(change, CreateEntityChange):
        return CreateEntity(_entity(change.entity))
    if isinstance(change, UpdateEntityChange):
        return UpdateEntity(_entity(change.entity))
    if isinstance(change, AddLinkChange):
        return AddLink(_link(change.link))
    if isinstance(change, RemoveLinkChange):
        return RemoveLink(StableId(change.link_id))
    if isinstance(change, AddFactChange):
        return AddFact(_fact(change.fact))
    if isinstance(change, GrantKnowledgeChange):
        return GrantKnowledge(_knowledge(change.entry))
    if isinstance(change, RecordEventChange):
        return RecordEvent(_event(change.event))
    if isinstance(change, AddSceneChange):
        return AddScene(_scene(change.scene))
    if isinstance(change, SetCurrentSceneChange):
        return SetCurrentScene(StableId(change.scene_id))
    if isinstance(change, AddChapterChange):
        return AddChapter(_chapter(change.chapter))
    if isinstance(change, AddThreadChange):
        return AddThread(_thread(change.thread))
    if isinstance(change, UpdateThreadChange):
        return UpdateThread(_thread(change.thread))
    if isinstance(change, AddGoalChange):
        return AddGoal(_goal(change.goal))
    if isinstance(change, UpdateGoalChange):
        return UpdateGoal(_goal(change.goal))
    raise TypeError(f"Nicht unterstützter API-Änderungstyp: {type(change)!r}")


def _entity(model: WorldEntityModel) -> WorldEntity:
    return WorldEntity(
        id=StableId(model.id),
        kind=EntityKind(model.kind),
        label=model.label,
        description=model.description,
        actor=(
            None
            if model.actor is None
            else ActorProfile(ActorRole(model.actor.role))
        ),
        conditions=tuple(
            Condition(condition.name, condition.description)
            for condition in model.conditions
        ),
        aliases=tuple(model.aliases),
    )


def _visibility(model: VisibilityModel) -> Visibility:
    actor_id = None if model.actor_id is None else StableId(model.actor_id)
    return Visibility(scope=model.scope, actor_id=actor_id)


def _evidence(model: EvidenceModel):
    from story_game.domain import Evidence

    return Evidence(
        source=model.source,
        reference=None if model.reference is None else StableId(model.reference),
        excerpt=model.excerpt,
    )


def _link(model: EntityLinkModel) -> EntityLink:
    return EntityLink(
        id=StableId(model.id),
        source_id=StableId(model.source_id),
        target_id=StableId(model.target_id),
        kind=model.kind,
        visibility=_visibility(model.visibility),
        quantity=model.quantity,
        description=model.description,
    )


def _fact(model: FactModel) -> Fact:
    return Fact(
        id=StableId(model.id),
        statement=model.statement,
        subject_id=None if model.subject_id is None else StableId(model.subject_id),
        evidence=_evidence(model.evidence),
        visibility=_visibility(model.visibility),
    )


def _knowledge(model: KnowledgeEntryModel) -> KnowledgeEntry:
    return KnowledgeEntry(
        actor_id=StableId(model.actor_id),
        fact_id=StableId(model.fact_id),
        learned_at=StorySequence(model.learned_at),
        forgotten_at=(
            None
            if model.forgotten_at is None
            else StorySequence(model.forgotten_at)
        ),
    )


def _event(model: StoryEventModel) -> StoryEvent:
    return StoryEvent(
        id=StableId(model.id),
        sequence=StorySequence(model.sequence),
        kind=model.kind,
        description=model.description,
        participant_ids=tuple(StableId(item) for item in model.participant_ids),
        visibility=_visibility(model.visibility),
    )


def _scene(model: SceneModel) -> Scene:
    return Scene(
        id=StableId(model.id),
        sequence=StorySequence(model.sequence),
        location_id=StableId(model.location_id),
        participants=tuple(
            SceneParticipant(
                entity_id=StableId(participant.entity_id),
                role=participant.role,
                visibility=_visibility(participant.visibility),
            )
            for participant in model.participants
        ),
        title=model.title,
        focus=model.focus,
        focus_entity_id=(
            None
            if model.focus_entity_id is None
            else StableId(model.focus_entity_id)
        ),
    )


def _chapter(model: ChapterModel) -> Chapter:
    return Chapter(
        id=StableId(model.id),
        sequence=model.sequence,
        title=model.title,
        status=model.status,
        summary=model.summary,
    )


def _thread(model: StoryThreadModel) -> StoryThread:
    return StoryThread(
        id=StableId(model.id),
        title=model.title,
        status=model.status,
        progress=model.progress,
        related_entity_ids=tuple(StableId(item) for item in model.related_entity_ids),
    )


def _goal(model: GoalModel) -> Goal:
    return Goal(
        id=StableId(model.id),
        title=model.title,
        owner_id=None if model.owner_id is None else StableId(model.owner_id),
        status=model.status,
        progress=model.progress,
        related_entity_ids=tuple(StableId(item) for item in model.related_entity_ids),
    )
