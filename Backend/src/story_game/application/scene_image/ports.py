"""Narrow ports owned by the scene-image capability."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from story_game.application.contracts import OperationResult
from story_game.domain import StableId

from .errors import ImageGenError
from .models import (
    ImageModelInfo,
    ImageRenderRequest,
    NewSceneImage,
    RenderedImage,
    SceneImageContent,
    SceneImageRecord,
)


class SceneImageStoreError(Exception):
    """Base failure exposed by the scene-image persistence ports."""


class SceneImageWriter(Protocol):
    def create_pending(self, image: NewSceneImage) -> SceneImageRecord: ...

    def find_active(
        self, run_id: StableId, turn_sequence: int, *, created_after: datetime
    ) -> SceneImageRecord | None:
        """The pending image of that turn started after ``created_after``."""
        ...

    def save_prompts(
        self, image_id: StableId, prompt: str, compact_prompt: str | None
    ) -> None: ...

    def complete(
        self, image_id: StableId, content: SceneImageContent, completed_at: datetime
    ) -> None: ...

    def fail(
        self, image_id: StableId, message: str, completed_at: datetime
    ) -> None: ...


class SceneImageReader(Protocol):
    """Reads scoped to a run member; a non-member sees "not found"."""

    def get(
        self, run_id: StableId, image_id: StableId, issuer: str, subject: str
    ) -> SceneImageRecord | None: ...

    def list_for_run(
        self, run_id: StableId, issuer: str, subject: str, limit: int
    ) -> tuple[SceneImageRecord, ...]: ...

    def load_content(
        self, run_id: StableId, image_id: StableId, issuer: str, subject: str
    ) -> SceneImageContent | None: ...


class SceneImageRenderer(Protocol):
    """Render one image, optionally refined, for a prepared request."""

    def render(
        self, request: ImageRenderRequest
    ) -> OperationResult[RenderedImage, ImageGenError]: ...

    def list_models(
        self,
    ) -> OperationResult[tuple[tuple[ImageModelInfo, ...], tuple[ImageModelInfo, ...]], ImageGenError]:
        """Return ``(main models, refine models)`` the provider offers."""
        ...


__all__ = [
    "SceneImageReader",
    "SceneImageRenderer",
    "SceneImageStoreError",
    "SceneImageWriter",
]
