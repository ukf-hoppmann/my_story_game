"""Expected failures of the scene-image capability."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SceneImageErrorKind(StrEnum):
    DISABLED = "disabled"
    NO_STORY = "no_story"
    NOT_FOUND = "not_found"
    INVALID_OPTIONS = "invalid_options"
    ACCESS_DENIED = "access_denied"
    STORE_UNAVAILABLE = "store_unavailable"
    PROMPT_FAILED = "prompt_failed"
    RENDER_FAILED = "render_failed"
    CONFIGURATION = "configuration"


@dataclass(frozen=True, slots=True)
class SceneImageError:
    kind: SceneImageErrorKind
    message: str

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("Fehlermeldungen dürfen nicht leer sein")
        object.__setattr__(self, "message", message)


class ImageGenErrorKind(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    CONFIGURATION = "configuration"


@dataclass(frozen=True, slots=True)
class ImageGenError:
    """Provider-independent image-generation failure; no HTTP objects cross it."""

    kind: ImageGenErrorKind
    message: str

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("Fehlermeldungen dürfen nicht leer sein")
        object.__setattr__(self, "message", message)


__all__ = [
    "ImageGenError",
    "ImageGenErrorKind",
    "SceneImageError",
    "SceneImageErrorKind",
]
