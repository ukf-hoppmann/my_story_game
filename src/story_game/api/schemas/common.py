"""Strict API models for complete game documents."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from story_game.domain import (
    ActorRole,
    EntityKind,
    GameRole,
    GameRunStatus,
    GoalKind,
    GoalStatus,
    RelationKind,
    VisibilityScope,
)


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


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
    evidence: EvidenceModel
    visibility: VisibilityModel
    subject_id: str | None = Field(default=None, min_length=1)


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


class GoalModel(APIModel):
    id: str = Field(min_length=1)
    kind: GoalKind
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: GoalStatus
    related_entity_ids: list[str] = Field(default_factory=list)


class StoryTurnModel(APIModel):
    id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    player_input: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    based_on_revision: int = Field(ge=1)
    resulting_revision: int = Field(ge=2)
    completed_at: datetime


class StorySummaryModel(APIModel):
    through_sequence: int = Field(ge=1)
    text: str = Field(min_length=1)
    based_on_revision: int = Field(ge=1)


class PromptProfileModel(APIModel):
    genre: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    prose_style: str = Field(min_length=1)
    perspective: str = Field(min_length=1)
    pacing: str = Field(min_length=1)
    control_mode: str = Field(min_length=1)
    player_agency: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    challenge: str = Field(min_length=1)
    content_profile: str = Field(min_length=1)


class GameConfigurationModel(APIModel):
    language: str = Field(min_length=1)
    prompt_profile: PromptProfileModel
    narrative_boundaries: list[str] = Field(default_factory=list)
    prompt_package_id: str = Field(min_length=1)
    prompt_package_version: str = Field(min_length=1)


class GameRunMemberModel(APIModel):
    issuer: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    game_role: GameRole
    player_entity_id: str | None = Field(default=None, min_length=1)


class GameRunModel(APIModel):
    id: str = Field(min_length=1)
    status: GameRunStatus
    current_revision: int = Field(ge=1)
    members: list[GameRunMemberModel] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
