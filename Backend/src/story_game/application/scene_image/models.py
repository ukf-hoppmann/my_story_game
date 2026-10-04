"""Typed values of the scene-image capability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from story_game.application.llm import SummarizedTurn
from story_game.application.run_initiator import RunInitiator
from story_game.domain import GameConfiguration, StableId


class SceneImageStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SceneImageDefaults:
    """Application-facing defaults and limits, resolved by the composition root."""

    turn_window: int = 3
    width: int = 1024
    height: int = 1024
    model: str | None = None
    refine: bool = False
    refine_model: str | None = None
    refine_strength: float = 0.35
    min_refine_strength: float = 0.1
    max_refine_strength: float = 0.8
    compact_prompt_max_words: int = 60

    def __post_init__(self) -> None:
        if self.turn_window < 1:
            raise ValueError("turn_window muss mindestens 1 sein")
        if self.width < 1 or self.height < 1:
            raise ValueError("Bildbreite und -höhe müssen positiv sein")
        if not self.min_refine_strength <= self.refine_strength <= self.max_refine_strength:
            raise ValueError("refine_strength liegt außerhalb des erlaubten Bereichs")
        if self.compact_prompt_max_words < 1:
            raise ValueError("compact_prompt_max_words muss positiv sein")


@dataclass(frozen=True, slots=True)
class SceneImageOptions:
    """Caller choices for one image; ``None`` means "use the default"."""

    model: str | None = None
    refine: bool | None = None
    refine_strength: float | None = None


@dataclass(frozen=True, slots=True)
class ResolvedSceneImageOptions:
    """The concrete choices one image is generated with."""

    model: str | None
    refine: bool
    refine_model: str | None
    refine_strength: float
    width: int
    height: int
    seed: int


@dataclass(frozen=True, slots=True)
class NewSceneImage:
    """What is stored when a generation is requested."""

    image_id: StableId
    run_id: StableId
    turn_sequence: int
    options: ResolvedSceneImageOptions
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SceneImageRecord:
    """Stored metadata of one scene image, without its pixels."""

    image_id: StableId
    run_id: StableId
    turn_sequence: int
    status: SceneImageStatus
    model: str | None
    refine: bool
    refine_model: str | None
    refine_strength: float
    width: int
    height: int
    seed: int
    created_at: datetime
    prompt: str | None = None
    compact_prompt: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SceneImageContent:
    data: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class SceneImageJob:
    """Everything the background generation needs after a request was accepted."""

    record: SceneImageRecord
    turns: tuple[SummarizedTurn, ...]
    configuration: GameConfiguration


@dataclass(frozen=True, slots=True)
class SceneImageRequested:
    """Outcome of a request: the stored record and, if new, the job to run.

    ``job`` is ``None`` when an equivalent generation for the same turn is
    already running; the caller then reports the existing record instead of
    starting a second, paid generation.
    """

    record: SceneImageRecord
    job: SceneImageJob | None


@dataclass(frozen=True, slots=True)
class ImageModelInfo:
    name: str


@dataclass(frozen=True, slots=True)
class SceneImageCapabilities:
    enabled: bool
    defaults: SceneImageDefaults | None = None
    models: tuple[ImageModelInfo, ...] = ()
    refine_models: tuple[ImageModelInfo, ...] = ()
    model_listing_failed: bool = False


@dataclass(frozen=True, slots=True)
class ImageRefinement:
    prompt: str
    model: str | None
    strength: float


@dataclass(frozen=True, slots=True)
class ImageRenderRequest:
    """One render call; ``refinement`` asks for the optional second stage."""

    prompt: str
    seed: int
    width: int
    height: int
    model: str | None
    refinement: ImageRefinement | None = None

    def __post_init__(self) -> None:
        if not self.prompt.strip():
            raise ValueError("Der Bildprompt darf nicht leer sein")


@dataclass(frozen=True, slots=True)
class RenderedImage:
    data: bytes
    content_type: str

    def __post_init__(self) -> None:
        if not self.data:
            raise ValueError("Ein gerendertes Bild darf nicht leer sein")


@dataclass(frozen=True, slots=True)
class RequestSceneImageRequest:
    run_id: StableId
    initiator: RunInitiator
    options: SceneImageOptions = SceneImageOptions()


__all__ = [
    "ImageModelInfo",
    "ImageRefinement",
    "ImageRenderRequest",
    "NewSceneImage",
    "RenderedImage",
    "RequestSceneImageRequest",
    "ResolvedSceneImageOptions",
    "SceneImageCapabilities",
    "SceneImageContent",
    "SceneImageDefaults",
    "SceneImageJob",
    "SceneImageOptions",
    "SceneImageRequested",
    "SceneImageRecord",
    "SceneImageStatus",
]
