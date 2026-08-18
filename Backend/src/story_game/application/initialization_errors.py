"""Typed failures shared by the transient initialization workflow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from story_game.application.llm.contracts import LLMError, LLMErrorKind


class StoryInitializationStage(StrEnum):
    STORY_GENERATION = "story_generation"
    WORLD_EXTRACTION = "world_extraction"


class StoryInitializationErrorKind(StrEnum):
    INVALID_CONFIGURATION = "invalid_configuration"
    MISSING_PLAYER_CHARACTER = "missing_player_character"
    UNEXPECTED_PLAYER_CHARACTER = "unexpected_player_character"
    MODEL_FAILURE = "model_failure"
    INVALID_MODEL_RESPONSE = "invalid_model_response"
    INVALID_CANDIDATE_REFERENCE = "invalid_candidate_reference"
    DOMAIN_REJECTION = "domain_rejection"


@dataclass(frozen=True, slots=True)
class StoryInitializationError:
    """Failure with its stage and optional provider-independent model cause."""

    kind: StoryInitializationErrorKind
    stage: StoryInitializationStage
    message: str
    cause: LLMError | None = None

    def __post_init__(self) -> None:
        message = self.message.strip()
        if not message:
            raise ValueError("Initialisierungsfehler benötigen eine Meldung")
        object.__setattr__(self, "message", message)


def model_failure(
    stage: StoryInitializationStage,
    cause: LLMError,
) -> StoryInitializationError:
    return StoryInitializationError(
        StoryInitializationErrorKind.MODEL_FAILURE,
        stage,
        cause.message,
        cause,
    )


def extraction_model_failure(cause: LLMError) -> StoryInitializationError:
    """Keep malformed structured output distinct from transport/model failures."""
    kind = (
        StoryInitializationErrorKind.INVALID_MODEL_RESPONSE
        if cause.kind is LLMErrorKind.INVALID_RESPONSE
        else StoryInitializationErrorKind.MODEL_FAILURE
    )
    return StoryInitializationError(
        kind,
        StoryInitializationStage.WORLD_EXTRACTION,
        cause.message,
        cause,
    )
