from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from story_game.application import Failure, Success
from story_game.application.diagnostics import ModelCallFailed
from story_game.application.generate_story import (
    GenerateStory,
    GenerateStoryRequest,
)
from story_game.application.llm import (
    GenerationConfiguration,
    GenerationOptions,
    LLMError,
    LLMErrorKind,
    ModelSelection,
    StoryGenerationData,
    StoryPromptSelectionResolver,
)
from story_game.application.story_turn_context import (
    SelectStoryTurnContextRequest,
    build_story_turn_context_selection,
)
from story_game.application.story_turn_errors import StoryTurnErrorKind
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.application import turn_context_world as w
from tests.application.diagnostics_double import FakeDiagnosticsLog


PROMPT_ROOT = Path(__file__).parents[2] / "prompts"


class FixedConfigurationResolver:
    def __init__(self, result=None) -> None:
        self.result = result or Success(
            GenerationConfiguration(
                ModelSelection("lmstudio", "storyteller"),
                GenerationOptions(temperature=0.5),
            )
        )
        self.task = None

    def resolve(self, task):
        self.task = task
        return self.result


class RecordingGenerator:
    def __init__(self, result=None) -> None:
        self.result = result or Success(StoryGenerationData("Bertram hebt den Blick."))
        self.call = None

    def generate(self, call):
        self.call = call
        return self.result


def context(player_input: str = "Ich frage den Wirt.", *narrations: str):
    state = w.game_state((w.TAVERN,), *narrations)
    result = build_story_turn_context_selection().apply(
        SelectStoryTurnContextRequest(state, w.MAREN, player_input)
    )
    assert isinstance(result, Success), result
    return result.data


def operation(
    generator=None, configuration_resolver=None, diagnostics=None
) -> GenerateStory:
    return GenerateStory(
        StoryPromptSelectionResolver(FilePromptPackageCatalog(PROMPT_ROOT)),
        configuration_resolver or FixedConfigurationResolver(),
        generator or RecordingGenerator(),
        diagnostics or FakeDiagnosticsLog(),
    )


def request(player_input: str = "Ich frage den Wirt.") -> GenerateStoryRequest:
    return GenerateStoryRequest(
        context(player_input), w.configuration(), player_input
    )


def test_successful_generation_returns_normalized_prose() -> None:
    result = operation().apply(request())

    assert isinstance(result, Success)
    assert result.data.text == "Bertram hebt den Blick."


def test_the_prepared_request_carries_the_projected_sections() -> None:
    generator = RecordingGenerator()

    operation(generator).apply(request("Ich frage den Wirt."))

    prepared = generator.call.request
    assert prepared.user_prompt == "Ich frage den Wirt."
    assert "Bedrohliche Fantasy" in prepared.configuration
    assert "Wirtshaus" in prepared.world_state
    assert "Bertram" in prepared.world_state
    assert prepared.story_state.strip() != ""
    assert len(prepared.system_prompts) == 2


def test_the_resolved_story_model_and_options_reach_the_port() -> None:
    generator = RecordingGenerator()
    resolver = FixedConfigurationResolver()

    operation(generator, resolver).apply(request())

    assert resolver.task.value == "story"
    assert generator.call.model_selection == ModelSelection("lmstudio", "storyteller")
    assert generator.call.generation_options.temperature == 0.5


def test_the_port_receives_the_context_only_as_prepared_text() -> None:
    """The adapter must not select game data; it only renders and transports."""
    generator = RecordingGenerator()

    operation(generator).apply(request())

    prepared = generator.call.request
    assert not hasattr(prepared, "context")
    assert not hasattr(prepared, "entities")
    assert all(isinstance(value, str) for value in (
        prepared.configuration, prepared.world_state, prepared.story_state,
        prepared.user_prompt,
    ))


@pytest.mark.parametrize(
    "kind",
    [
        LLMErrorKind.UNAVAILABLE,
        LLMErrorKind.TIMEOUT,
        LLMErrorKind.RATE_LIMITED,
        LLMErrorKind.CONTEXT_LIMIT,
        LLMErrorKind.INCOMPLETE,
    ],
)
def test_model_failures_stay_visible_without_a_retry(kind: LLMErrorKind) -> None:
    generator = RecordingGenerator(Failure(LLMError(kind, "Fehlgeschlagen.")))

    result = operation(generator).apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.MODEL_FAILURE
    assert result.error.cause is not None
    assert result.error.cause.kind is kind


def test_unusable_output_is_reported_separately_from_transport_failures() -> None:
    generator = RecordingGenerator(
        Failure(LLMError(LLMErrorKind.INVALID_RESPONSE, "Leer."))
    )

    result = operation(generator).apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_MODEL_RESPONSE


def test_a_failed_model_configuration_prevents_the_port_call() -> None:
    generator = RecordingGenerator()
    resolver = FixedConfigurationResolver(
        Failure(LLMError(LLMErrorKind.CONFIGURATION, "Kein Story-Modell."))
    )

    result = operation(generator, resolver).apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.MODEL_FAILURE
    assert generator.call is None


def test_an_unknown_prompt_package_fails_before_the_port_call() -> None:
    generator = RecordingGenerator()
    broken = replace(w.configuration(), prompt_package_id="does.not.exist")

    result = operation(generator).apply(
        GenerateStoryRequest(context(), broken, "Ich warte.")
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_CONFIGURATION
    assert generator.call is None


def test_a_model_failure_is_recorded_as_a_diagnostic_event() -> None:
    diagnostics = FakeDiagnosticsLog()
    generator = RecordingGenerator(
        Failure(LLMError(LLMErrorKind.UNAVAILABLE, "Nicht erreichbar."))
    )

    operation(generator, diagnostics=diagnostics).apply(request())

    assert len(diagnostics.recorded) == 1
    event = diagnostics.recorded[0]
    assert isinstance(event, ModelCallFailed)
    assert event.task == "story"
    assert event.error.kind is LLMErrorKind.UNAVAILABLE


def test_a_successful_call_only_traces_and_never_records() -> None:
    diagnostics = FakeDiagnosticsLog()

    operation(diagnostics=diagnostics).apply(request())

    assert diagnostics.recorded == []
    traced_steps = [step for step, _ in diagnostics.traced]
    assert "generate_story.call" in traced_steps
    assert "generate_story.result" in traced_steps


def test_an_empty_world_selection_still_produces_a_valid_request() -> None:
    generator = RecordingGenerator()
    empty = replace(
        context(),
        scene_locations=(),
        entities=(),
        links=(),
        facts=(),
        knowledge=(),
        rules=(),
        goals=(),
        controlled_entity=None,
    )

    result = operation(generator).apply(
        GenerateStoryRequest(empty, w.configuration(), "Ich warte.")
    )

    assert isinstance(result, Success)
    assert generator.call.request.world_state.strip() != ""
