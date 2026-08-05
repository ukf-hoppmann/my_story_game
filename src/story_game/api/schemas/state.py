"""OpenAPI models for the complete canonical state document."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import (
    APIModel,
    ChapterModel,
    EntityLinkModel,
    FactModel,
    GoalModel,
    KnowledgeEntryModel,
    SceneModel,
    StoryEventModel,
    StorySummaryModel,
    StoryThreadModel,
    WorldEntityModel,
    WorldRuleModel,
)


class GameStateIdentityModel(APIModel):
    id: str = Field(min_length=1)
    player_actor_id: str | None = Field(default=None, min_length=1)


class WorldStateModel(APIModel):
    entities: list[WorldEntityModel] = Field(default_factory=list)
    links: list[EntityLinkModel] = Field(default_factory=list)
    facts: list[FactModel] = Field(default_factory=list)
    knowledge: list[KnowledgeEntryModel] = Field(default_factory=list)
    rules: list[WorldRuleModel] = Field(default_factory=list)


class StoryStateModel(APIModel):
    events: list[StoryEventModel] = Field(default_factory=list)
    scenes: list[SceneModel] = Field(default_factory=list)
    chapters: list[ChapterModel] = Field(default_factory=list)
    threads: list[StoryThreadModel] = Field(default_factory=list)
    goals: list[GoalModel] = Field(default_factory=list)
    summaries: list[StorySummaryModel] = Field(default_factory=list)
    current_scene_id: str | None = Field(default=None, min_length=1)
    current_chapter_id: str | None = Field(default=None, min_length=1)
    current_sequence: int = Field(ge=0)


class StateDocument(APIModel):
    """Versioned transport document for creation and representation of state."""

    schema_version: Literal[1] = 1
    state_revision: int = Field(ge=1)
    game_state: GameStateIdentityModel
    world: WorldStateModel
    story: StoryStateModel
