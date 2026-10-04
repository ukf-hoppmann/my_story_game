"""Transport shapes for the scene-image endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from story_game.application.scene_image import SceneImageStatus

from .common import APIModel


class CreateSceneImageRequestModel(APIModel):
    """Optional per-image choices; omitted fields use the server defaults."""

    model: str | None = Field(default=None, min_length=1)
    refine: bool | None = None
    refine_strength: float | None = None


class SceneImageModel(APIModel):
    image_id: UUID
    run_id: UUID
    turn_sequence: int
    status: SceneImageStatus
    model: str | None
    refine: bool
    refine_model: str | None
    refine_strength: float
    width: int
    height: int
    seed: int
    prompt: str | None
    compact_prompt: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class SceneImageListModel(APIModel):
    images: list[SceneImageModel]


class ImageModelModel(APIModel):
    name: str


class SceneImageCapabilitiesModel(APIModel):
    """What the UI needs to decide whether and how to offer the button."""

    enabled: bool
    models: list[ImageModelModel] = Field(default_factory=list)
    refine_models: list[ImageModelModel] = Field(default_factory=list)
    model_listing_failed: bool = False
    default_model: str | None = None
    default_refine: bool = False
    default_refine_model: str | None = None
    default_refine_strength: float | None = None
    min_refine_strength: float | None = None
    max_refine_strength: float | None = None
    turn_window: int | None = None


__all__ = [
    "CreateSceneImageRequestModel",
    "ImageModelModel",
    "SceneImageCapabilitiesModel",
    "SceneImageListModel",
    "SceneImageModel",
]
