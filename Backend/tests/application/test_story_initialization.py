from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from story_game.application import Failure, Success
from story_game.application.initialization_errors import StoryInitializationErrorKind
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.application.llm import (
    GenerationConfiguration,
    GenerationOptions,
    InitialStoryText,
    LLMError,
    LLMErrorKind,
    ModelSelection,
    StoryInitializationPromptResolver,
)
from story_game.application.story_initialization import (
    GenerateInitialStoryState,
    GenerateInitialStoryStateRequest,
)
from story_game.domain import GameConfiguration, PromptProfile
from story_game.infrastructure.llm import FilePromptPackageCatalog


PROMPT_ROOT = Path(__file__).parents[2] / "prompts"


class FixedConfigurationResolver:
    def resolve(self, task):
        assert task.value == "story"
        return Success(
            GenerationConfiguration(
                ModelSelection("lmstudio", "local"),
                GenerationOptions(temperature=0.5),
            )
        )


class RecordingGenerator:
    def __init__(self, result):
        self.result = result
        self.call = None

    def generate(self, call):
        self.call = call
        return self.result


def configuration(
    perspective: str = "third_person_limited",
    control_mode: str = "player",
) -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            "dark_fantasy",
            "balanced",
            "balanced",
            perspective,
            "balanced",
            control_mode,
            "strict",
            "balanced",
            "balanced",
            "teen",
        ),
        narrative_boundaries=("Keine sexualisierte Gewalt",),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def player_character() -> ControllableCharacterSeed:
    return ControllableCharacterSeed("Maren", "Eine vorsichtige Kartografin.")


def operation(generator: RecordingGenerator) -> GenerateInitialStoryState:
    return GenerateInitialStoryState(
        StoryInitializationPromptResolver(FilePromptPackageCatalog(PROMPT_ROOT)),
        FixedConfigurationResolver(),
        generator,
        lambda: datetime(2026, 8, 10, tzinfo=UTC),
    )


def test_generates_an_initialized_story_state_with_the_caller_character() -> None:
    generator = RecordingGenerator(Success(InitialStoryText("Maren hebt die Fackel.")))

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(),
            "Maren und Alma gehen in den Dungeon.",
            (player_character(),),
        )
    )

    assert isinstance(result, Success)
    assert result.data.initialization is not None
    assert result.data.initialization.prompt == "Maren und Alma gehen in den Dungeon."
    assert result.data.turns == ()
    assert generator.call.request.initial_prompt == "Maren und Alma gehen in den Dungeon."
    assert generator.call.request.controllable_characters == (player_character(),)
    assert not hasattr(generator.call.request, "world_state")
    assert not hasattr(generator.call.request, "story_state")


@pytest.mark.parametrize(
    "perspective",
    [
        "first_person",
        "second_person",
        "third_person_limited",
        "third_person_omniscient",
    ],
)
def test_player_mode_supports_every_character_bound_perspective(
    perspective: str,
) -> None:
    generator = RecordingGenerator(Success(InitialStoryText("Maren wartet.")))

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(perspective, "player"),
            "Maren wartet am Tor.",
            (player_character(),),
        )
    )

    assert isinstance(result, Success)
    assert generator.call.request.controllable_characters == (player_character(),)


@pytest.mark.parametrize(
    "perspective",
    [
        "first_person",
        "second_person",
        "third_person_limited",
        "third_person_omniscient",
    ],
)
def test_player_mode_requires_a_character_before_calling_the_model(
    perspective: str,
) -> None:
    generator = RecordingGenerator(Success(InitialStoryText("Nicht erreichbar.")))

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(perspective, "player"),
            "Eine Geschichte beginnt.",
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.MISSING_PLAYER_CHARACTER
    assert generator.call is None


@pytest.mark.parametrize("perspective", ["first_person", "second_person"])
def test_director_mode_rejects_character_bound_perspectives(
    perspective: str,
) -> None:
    generator = RecordingGenerator(Success(InitialStoryText("Nicht erreichbar.")))

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(perspective, "director"),
            "Eine Geschichte beginnt.",
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_CONFIGURATION
    assert generator.call is None


@pytest.mark.parametrize(
    "perspective", ["third_person_limited", "third_person_omniscient"]
)
def test_director_mode_accepts_one_or_more_controllable_characters(
    perspective: str,
) -> None:
    generator = RecordingGenerator(Success(InitialStoryText("Die Szene beginnt.")))
    maren = ControllableCharacterSeed("Maren")
    jonas = ControllableCharacterSeed("Jonas")

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(perspective, "director"),
            "Eine Geschichte beginnt.",
            (maren, jonas),
        )
    )

    assert isinstance(result, Success)
    assert generator.call.request.controllable_characters == (maren, jonas)


@pytest.mark.parametrize(
    "perspective", ["third_person_limited", "third_person_omniscient"]
)
def test_director_mode_rejects_duplicate_controllable_character_names(
    perspective: str,
) -> None:
    generator = RecordingGenerator(Success(InitialStoryText("Nicht erreichbar.")))

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(perspective, "director"),
            "Eine Geschichte beginnt.",
            (ControllableCharacterSeed("Maren"), ControllableCharacterSeed("maren")),
        )
    )

    assert isinstance(result, Failure)
    assert (
        result.error.kind
        is StoryInitializationErrorKind.DUPLICATE_CONTROLLABLE_CHARACTER
    )
    assert generator.call is None


@pytest.mark.parametrize(
    "perspective", ["third_person_limited", "third_person_omniscient"]
)
def test_director_mode_omits_player_agency_and_allows_no_character(
    perspective: str,
) -> None:
    generator = RecordingGenerator(Success(InitialStoryText("Die Szene beginnt.")))

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(perspective, "director"),
            "Eine Geschichte beginnt.",
        )
    )

    assert isinstance(result, Success)
    assert generator.call.request.controllable_characters == ()
    assert "player_agency:" not in generator.call.request.configuration


def test_keeps_a_model_failure_as_the_visible_cause() -> None:
    generator = RecordingGenerator(
        Failure(LLMError(LLMErrorKind.TIMEOUT, "Zeitüberschreitung", retryable=True))
    )

    result = operation(generator).apply(
        GenerateInitialStoryStateRequest(
            configuration(),
            "Maren geht los.",
            (player_character(),),
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.MODEL_FAILURE
    assert result.error.cause is not None
    assert result.error.cause.kind is LLMErrorKind.TIMEOUT
