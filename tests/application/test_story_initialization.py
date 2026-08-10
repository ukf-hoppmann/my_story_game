from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from story_game.application import Failure, Success
from story_game.application.llm import (
    GenerationConfiguration,
    GenerationOptions,
    LLMError,
    LLMErrorKind,
    ModelSelection,
)
from story_game.application.story_initialization import (
    GenerateInitialStoryState,
    GenerateInitialStoryStateRequest,
)
from story_game.domain import GameConfiguration, PromptProfile
from story_game.infrastructure.llm import FilePromptPackageCatalog
from story_game.application.llm import StoryInitializationPromptResolver


class FixedConfigurationResolver:
    def resolve(self, task):
        assert task.value == "story"
        return Success(GenerationConfiguration(ModelSelection("lmstudio", "local"), GenerationOptions(temperature=0.5)))


class RecordingGenerator:
    def __init__(self, result):
        self.result = result
        self.call = None

    def generate(self, call):
        self.call = call
        return self.result


def configuration() -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile("dark_fantasy", "balanced", "balanced", "third_person_limited", "balanced", "player", "strict", "balanced", "balanced", "teen"),
        narrative_boundaries=("Keine sexualisierte Gewalt",),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


def test_generates_an_initialized_story_state_without_game_context() -> None:
    from story_game.application.llm import InitialStoryText

    generator = RecordingGenerator(Success(InitialStoryText("Maren hebt die Fackel.")))
    operation = GenerateInitialStoryState(
        StoryInitializationPromptResolver(FilePromptPackageCatalog(Path(__file__).parents[2] / "prompts")),
        FixedConfigurationResolver(),
        generator,
        lambda: datetime(2026, 8, 10, tzinfo=UTC),
    )

    result = operation.apply(GenerateInitialStoryStateRequest(configuration(), "Maren und Almas gehen in den Dungeon."))

    assert isinstance(result, Success)
    assert result.data.initialization is not None
    assert result.data.initialization.prompt == "Maren und Almas gehen in den Dungeon."
    assert result.data.turns == ()
    assert generator.call.request.initial_prompt == "Maren und Almas gehen in den Dungeon."
    assert not hasattr(generator.call.request, "world_state")
    assert not hasattr(generator.call.request, "story_state")


def test_keeps_a_model_failure_without_creating_a_story_state() -> None:
    generator = RecordingGenerator(Failure(LLMError(LLMErrorKind.TIMEOUT, "Zeitüberschreitung", retryable=True)))
    operation = GenerateInitialStoryState(
        StoryInitializationPromptResolver(FilePromptPackageCatalog(Path(__file__).parents[2] / "prompts")),
        FixedConfigurationResolver(),
        generator,
        lambda: datetime(2026, 8, 10, tzinfo=UTC),
    )

    result = operation.apply(GenerateInitialStoryStateRequest(configuration(), "Maren geht los."))

    assert isinstance(result, Failure)
    assert result.error.kind is LLMErrorKind.TIMEOUT
