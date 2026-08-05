"""Reusable API value models shared by state and change contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from story_game.domain import (
    ActorRole,
    ChapterStatus,
    EntityKind,
    GoalStatus,
    RelationKind,
    ThreadStatus,
    VisibilityScope,
)


class APIModel(BaseModel):
    """Strict boundary model; unknown fields must not silently disappear."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class VisibilityModel(APIModel):
    scope: VisibilityScope
    actor_id: str | None = Field(default=None, min_length=1)


class EvidenceModel(APIModel):
    source: str = Field(min_length=1)
    reference: str | None = Field(default=None, min_length=1)
    excerpt: str | None = None


class ConditionModel(APIModel):
    name: str = Field(min_length=1)
    description: str = ""


class ActorProfileModel(APIModel):
    role: ActorRole


class WorldEntityModel(APIModel):
    id: str = Field(min_length=1)
    kind: EntityKind
    label: str = Field(min_length=1)
    description: str = ""
    actor: ActorProfileModel | None = None
    conditions: list[ConditionModel] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class EntityLinkModel(APIModel):
    id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    kind: RelationKind
    visibility: VisibilityModel
    quantity: int | None = Field(default=None, ge=1)
    description: str = ""


class FactModel(APIModel):
    id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    subject_id: str | None = Field(default=None, min_length=1)
    evidence: EvidenceModel
    visibility: VisibilityModel


class KnowledgeEntryModel(APIModel):
    actor_id: str = Field(min_length=1)
    fact_id: str = Field(min_length=1)
    learned_at: int = Field(ge=1)
    forgotten_at: int | None = Field(default=None, ge=1)


class WorldRuleModel(APIModel):
    id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    evidence: EvidenceModel
    visibility: VisibilityModel


class StoryEventModel(APIModel):
    id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    kind: str = Field(min_length=1)
    description: str = Field(min_length=1)
    participant_ids: list[str] = Field(default_factory=list)
    visibility: VisibilityModel


class SceneParticipantModel(APIModel):
    entity_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    visibility: VisibilityModel


class SceneModel(APIModel):
    id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    location_id: str = Field(min_length=1)
    participants: list[SceneParticipantModel] = Field(default_factory=list)
    title: str = ""
    focus: str = ""
    focus_entity_id: str | None = Field(default=None, min_length=1)


class ChapterModel(APIModel):
    id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    title: str = Field(min_length=1)
    status: ChapterStatus
    summary: str = ""


class StoryThreadModel(APIModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: ThreadStatus
    progress: int = Field(ge=0, le=100)
    related_entity_ids: list[str] = Field(default_factory=list)


class GoalModel(APIModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    owner_id: str | None = Field(default=None, min_length=1)
    status: GoalStatus
    progress: int = Field(ge=0, le=100)
    related_entity_ids: list[str] = Field(default_factory=list)


class StorySummaryModel(APIModel):
    from_sequence: int = Field(ge=1)
    through_sequence: int = Field(ge=1)
    text: str = Field(min_length=1)
    based_on_revision: int = Field(ge=1)
