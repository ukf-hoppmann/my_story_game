"""The scene-image operations the HTTP adapter needs, grouped as one value."""

from __future__ import annotations

from dataclasses import dataclass

from .generate_scene_image import GenerateSceneImage
from .read_scene_images import (
    ListSceneImages,
    LoadSceneImage,
    LoadSceneImageContent,
    ReadSceneImageCapabilities,
)
from .request_scene_image import RequestSceneImage


@dataclass(frozen=True, slots=True)
class SceneImageOperations:
    """Present only when the feature is enabled; ``None`` means disabled."""

    request: RequestSceneImage
    generate: GenerateSceneImage
    list: ListSceneImages
    load: LoadSceneImage
    content: LoadSceneImageContent
    capabilities: ReadSceneImageCapabilities


__all__ = ["SceneImageOperations"]
