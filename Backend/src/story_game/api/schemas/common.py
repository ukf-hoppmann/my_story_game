"""Strict API models for complete game documents."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

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
    actor_id: UUID | None = None


class ConditionModel(APIModel):
    name: str = Field(min_length=1)
    description: str = ""


class ActorProfileModel(APIModel):
    role: ActorRole


class WorldEntityModel(APIModel):
    id: UUID
    kind: EntityKind
    label: str = Field(min_length=1)
    description: str = ""
    actor: ActorProfileModel | None = None
    conditions: list[ConditionModel] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class EntityLinkModel(APIModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    kind: RelationKind
    visibility: VisibilityModel
    quantity: int | None = Field(default=None, ge=1)
    description: str = ""


class FactModel(APIModel):
    id: UUID
    statement: str = Field(min_length=1)
    visibility: VisibilityModel
    subject_id: UUID | None = None


class KnowledgeEntryModel(APIModel):
    actor_id: UUID
    fact_id: UUID
    learned_at: int = Field(ge=1)
    forgotten_at: int | None = Field(default=None, ge=1)


class WorldRuleModel(APIModel):
    id: UUID
    statement: str = Field(min_length=1)
    visibility: VisibilityModel


class GoalModel(APIModel):
    id: UUID
    kind: GoalKind
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: GoalStatus
    related_entity_ids: list[UUID] = Field(default_factory=list)


class StoryTurnModel(APIModel):
    id: UUID
    sequence: int = Field(ge=1)
    player_input: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    based_on_revision: int = Field(ge=1)
    resulting_revision: int = Field(ge=2)
    completed_at: datetime


class StorySummarySegmentModel(APIModel):
    """One immutable segment of the summary chain (TASK-032)."""

    from_sequence: int = Field(ge=1)
    through_sequence: int = Field(ge=1)
    text: str = Field(min_length=1)
    based_on_revision: int = Field(ge=1)


class StoryInitializationModel(APIModel):
    """The user premise and normalized opening prose before the first turn."""

    prompt: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    completed_at: datetime


class PromptProfileModel(APIModel):
    genre: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    prose_style: str = Field(min_length=1)
    perspective: str = Field(min_length=1)
    pacing: str = Field(min_length=1)
    length: str = Field(min_length=1)
    control_mode: str = Field(min_length=1)
    player_agency: str = Field(min_length=1)
    consequence: str = Field(min_length=1)
    challenge: str = Field(min_length=1)
    content_profile: str = Field(min_length=1)


class EditablePromptProfileModel(APIModel):
    """The prompt-profile categories a caller may choose.

    Deliberately omits ``control_mode``: it is not a narrative-style choice
    but structurally coupled to run membership (see
    ``confirm_game_run_proposal.py``/``_controlled_entity_ids``) — set once
    via ``ProposeRunRequestModel.control_mode`` at creation and left
    untouched by later configuration updates.
    """

    genre: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    prose_style: str = Field(min_length=1)
    perspective: str = Field(min_length=1)
    pacing: str = Field(min_length=1)
    length: str = Field(min_length=1)
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
    controlled_entity_ids: list[UUID] = Field(default_factory=list)


class ControllableCharacterSeedModel(APIModel):
    name: str = Field(min_length=1)
    description: str = ""


class GameRunModel(APIModel):
    id: UUID
    name: str = Field(min_length=1)
    status: GameRunStatus
    current_revision: int = Field(ge=1)
    members: list[GameRunMemberModel] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
