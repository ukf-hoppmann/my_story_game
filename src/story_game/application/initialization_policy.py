"""Validate caller-controlled initialization choices before model invocation."""

from __future__ import annotations

from story_game.domain import GameConfiguration

from .initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
)
from .initialization_models import PlayerCharacterSeed


def validate_initialization_choices(
    configuration: GameConfiguration,
    player_character: PlayerCharacterSeed | None,
    stage: StoryInitializationStage,
) -> StoryInitializationError | None:
    profile = configuration.prompt_profile
    control_mode = profile.control_mode
    perspective = profile.perspective

    if control_mode not in {"player", "director"}:
        return StoryInitializationError(
            StoryInitializationErrorKind.INVALID_CONFIGURATION,
            stage,
            f"Unbekannter Control Mode: {control_mode}",
        )
    if perspective in {"first_person", "second_person"} and control_mode == "director":
        return StoryInitializationError(
            StoryInitializationErrorKind.INVALID_CONFIGURATION,
            stage,
            "First und Second Person sind im Director Mode nicht erlaubt.",
        )
    if control_mode == "player" and player_character is None:
        return StoryInitializationError(
            StoryInitializationErrorKind.MISSING_PLAYER_CHARACTER,
            stage,
            "Der Player Mode benötigt einen vom User angelegten Charakter.",
        )
    if control_mode == "director" and player_character is not None:
        return StoryInitializationError(
            StoryInitializationErrorKind.UNEXPECTED_PLAYER_CHARACTER,
            stage,
            "Der Director Mode besitzt keinen Spielercharakter.",
        )
    return None
