"""Discriminated API commands for application-approved state changes."""

from __future__ import annotations

from typing import Annotated, Literal, Union

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
    StoryThreadModel,
    WorldEntityModel,
)


class CreateEntityChange(APIModel):
    type: Literal["create_entity"]
    entity: WorldEntityModel


class UpdateEntityChange(APIModel):
    type: Literal["update_entity"]
    entity: WorldEntityModel


class AddLinkChange(APIModel):
    type: Literal["add_link"]
    link: EntityLinkModel


class RemoveLinkChange(APIModel):
    type: Literal["remove_link"]
    link_id: str = Field(min_length=1)


class AddFactChange(APIModel):
    type: Literal["add_fact"]
    fact: FactModel


class GrantKnowledgeChange(APIModel):
    type: Literal["grant_knowledge"]
    entry: KnowledgeEntryModel


class RecordEventChange(APIModel):
    type: Literal["record_event"]
    event: StoryEventModel


class AddSceneChange(APIModel):
    type: Literal["add_scene"]
    scene: SceneModel


class SetCurrentSceneChange(APIModel):
    type: Literal["set_current_scene"]
    scene_id: str = Field(min_length=1)


class AddChapterChange(APIModel):
    type: Literal["add_chapter"]
    chapter: ChapterModel


class AddThreadChange(APIModel):
    type: Literal["add_thread"]
    thread: StoryThreadModel


class UpdateThreadChange(APIModel):
    type: Literal["update_thread"]
    thread: StoryThreadModel


class AddGoalChange(APIModel):
    type: Literal["add_goal"]
    goal: GoalModel


class UpdateGoalChange(APIModel):
    type: Literal["update_goal"]
    goal: GoalModel


StateChangeRequest = Annotated[
    Union[
        CreateEntityChange,
        UpdateEntityChange,
        AddLinkChange,
        RemoveLinkChange,
        AddFactChange,
        GrantKnowledgeChange,
        RecordEventChange,
        AddSceneChange,
        SetCurrentSceneChange,
        AddChapterChange,
        AddThreadChange,
        UpdateThreadChange,
        AddGoalChange,
        UpdateGoalChange,
    ],
    Field(discriminator="type"),
]


class ApprovedChangeSetRequest(APIModel):
    """Only this already-approved command set can reach the canonical writer."""

    proposal_id: str = Field(min_length=1)
    base_revision: int = Field(ge=1)
    changes: list[StateChangeRequest] = Field(default_factory=list)
