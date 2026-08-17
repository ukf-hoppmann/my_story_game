"""Typed failures of one regular story turn."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from story_game.application.llm.contracts import LLMError, LLMErrorKind


class StoryTurnErrorKind(StrEnum):
    INVALID_CONFIGURATION = "invalid_configuration"
    MODEL_FAILURE = "model_failure"
    INVALID_MODEL_RESPONSE = "invalid_model_response"


@dataclass(frozen=True, slots=True)
class StoryTurnError:
    """Failure with its provider-independent model cause, if a model was called.

    Separate from ``StoryInitializationError`` on purpose: that type carries
    kinds like a missing player-character seed and stages named after
    initialization, which would describe a running turn wrongly.
    """

    kind: StoryTurnErrorKind
    message: str
    cause: LLMError | None = None

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("Zugfehler benötigen eine Meldung")
        object.__setattr__(self, "message", message)


def story_model_failure(cause: LLMError) -> StoryTurnError:
    """Keep unusable model output distinct from transport and model failures."""
    kind = (
        StoryTurnErrorKind.INVALID_MODEL_RESPONSE
        if cause.kind is LLMErrorKind.INVALID_RESPONSE
        else StoryTurnErrorKind.MODEL_FAILURE
    )
    return StoryTurnError(kind, cause.message, cause)


__all__ = ["StoryTurnError", "StoryTurnErrorKind", "story_model_failure"]
