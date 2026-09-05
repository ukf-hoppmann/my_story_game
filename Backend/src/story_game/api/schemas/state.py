"""Versioned transport document for the complete test state."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from .common import (
    APIModel,
    EntityLinkModel,
    FactModel,
    GameConfigurationModel,
    GameRunModel,
    GoalModel,
    KnowledgeEntryModel,
    StoryInitializationModel,
    StorySummaryModel,
    StoryTurnModel,
    WorldEntityModel,
    WorldRuleModel,
)


class WorldStateModel(APIModel):
    entities: list[WorldEntityModel] = Field(default_factory=list)
    links: list[EntityLinkModel] = Field(default_factory=list)
    facts: list[FactModel] = Field(default_factory=list)
    knowledge: list[KnowledgeEntryModel] = Field(default_factory=list)
    rules: list[WorldRuleModel] = Field(default_factory=list)
    goals: list[GoalModel] = Field(default_factory=list)
    scene_location_ids: list[UUID] = Field(default_factory=list)


class StoryStateModel(APIModel):
    turns: list[StoryTurnModel] = Field(default_factory=list)
    summary: StorySummaryModel | None = None
    current_turn_sequence: int = Field(ge=0)
    initialization: StoryInitializationModel | None = None


class GameStateModel(APIModel):
    run_id: UUID
    revision: int = Field(ge=1)
    configuration: GameConfigurationModel
    world: WorldStateModel
    story: StoryStateModel


class GameDocument(APIModel):
    """Versioned transport document for a complete run and game-state snapshot."""

    schema_version: Literal[1] = 1
    game_run: GameRunModel
    game_state: GameStateModel
