"""Validate caller-controlled initialization choices before model invocation."""

from __future__ import annotations

from story_game.domain import GameConfiguration

from .initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
)
from .initialization_models import ControllableCharacterSeed


def validate_initialization_choices(
    configuration: GameConfiguration,
    controllable_characters: tuple[ControllableCharacterSeed, ...],
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
    if control_mode == "player" and len(controllable_characters) != 1:
        return StoryInitializationError(
            StoryInitializationErrorKind.MISSING_PLAYER_CHARACTER,
            stage,
            "Der Player Mode benötigt genau einen vom User angelegten Charakter.",
        )
    names = [seed.name.casefold() for seed in controllable_characters]
    if len(names) != len(set(names)):
        return StoryInitializationError(
            StoryInitializationErrorKind.DUPLICATE_CONTROLLABLE_CHARACTER,
            stage,
            "Steuerbare Figuren müssen sich im Namen unterscheiden.",
        )
    return None
