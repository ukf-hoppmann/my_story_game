from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from story_game.application import Failure, Success
from story_game.application.extract_story_turn_changes import (
    ExtractStoryTurnChanges,
    ExtractStoryTurnChangesRequest,
)
from story_game.application.llm import (
    ExtractionPromptSelectionResolver,
    GenerationConfiguration,
    GenerationOptions,
    LLMError,
    LLMErrorKind,
    ModelSelection,
    TurnChangeCandidate,
)
from story_game.application.story_turn_context import (
    SelectStoryTurnContextRequest,
    build_story_turn_context_selection,
)
from story_game.application.story_turn_errors import StoryTurnErrorKind
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.application import turn_context_world as w


PROMPT_ROOT = Path(__file__).parents[2] / "prompts"

NARRATION = "Maren verlässt das Wirtshaus und tritt in den Schwarzwald."


class FixedConfigurationResolver:
    def __init__(self, result=None) -> None:
        self.result = result or Success(
            GenerationConfiguration(
                ModelSelection("lmstudio", "extractor"),
                GenerationOptions(temperature=0.1),
            )
        )
        self.task = None

    def resolve(self, task):
        self.task = task
        return self.result


class RecordingExtractor:
    def __init__(self, result=None) -> None:
        self.result = result or Success(TurnChangeCandidate())
        self.call = None

    def extract(self, call):
        self.call = call
        return self.result


def context():
    state = w.game_state((w.TAVERN,), "Maren sitzt am Feuer.")
    result = build_story_turn_context_selection().apply(
        SelectStoryTurnContextRequest(state, w.MAREN, "Ich gehe hinaus.")
    )
    assert isinstance(result, Success), result
    return result.data


def operation(extractor=None, configuration_resolver=None) -> ExtractStoryTurnChanges:
    return ExtractStoryTurnChanges(
        ExtractionPromptSelectionResolver(FilePromptPackageCatalog(PROMPT_ROOT)),
        configuration_resolver or FixedConfigurationResolver(),
        extractor or RecordingExtractor(),
    )


def request(configuration=None) -> ExtractStoryTurnChangesRequest:
    return ExtractStoryTurnChangesRequest(
        context(), configuration or w.configuration(), NARRATION
    )


def test_a_successful_extraction_returns_candidate_and_projection() -> None:
    result = operation().apply(request())

    assert isinstance(result, Success)
    assert result.data.candidate == TurnChangeCandidate()
    assert result.data.projection.entity_handles != {}


def test_the_request_compares_narration_against_the_handled_excerpt() -> None:
    extractor = RecordingExtractor()

    operation(extractor).apply(request())

    prepared = extractor.call.request
    assert prepared.narration == NARRATION
    assert "e1" in prepared.world_state
    assert prepared.language == "de"
    assert len(prepared.system_prompts) == 2


def test_the_player_input_never_reaches_the_extraction_model() -> None:
    """The narration is what happened; the attempted input is not."""
    extractor = RecordingExtractor()

    operation(extractor).apply(request())

    assert "Ich gehe hinaus." not in repr(extractor.call.request)


def test_no_story_profile_reaches_the_extraction_model() -> None:
    extractor = RecordingExtractor()

    operation(extractor).apply(request())

    prepared = extractor.call.request
    assert not hasattr(prepared, "perspective")
    assert "Bedrohliche Fantasy" not in repr(prepared)


def test_the_extraction_model_and_its_options_reach_the_port() -> None:
    extractor = RecordingExtractor()
    resolver = FixedConfigurationResolver()

    operation(extractor, resolver).apply(request())

    assert resolver.task.value == "extraction"
    assert extractor.call.model_selection == ModelSelection("lmstudio", "extractor")
    assert extractor.call.generation_options.temperature == 0.1


def test_the_returned_projection_is_the_one_the_model_saw() -> None:
    extractor = RecordingExtractor()

    result = operation(extractor).apply(request())

    assert isinstance(result, Success)
    assert result.data.projection.text == extractor.call.request.world_state


def test_model_failures_stay_visible_without_a_retry() -> None:
    extractor = RecordingExtractor(
        Failure(LLMError(LLMErrorKind.TIMEOUT, "Zeitüberschreitung."))
    )

    result = operation(extractor).apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.MODEL_FAILURE


def test_unusable_output_is_reported_separately() -> None:
    extractor = RecordingExtractor(
        Failure(LLMError(LLMErrorKind.INVALID_RESPONSE, "Kein JSON."))
    )

    result = operation(extractor).apply(request())

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_MODEL_RESPONSE


def test_a_failed_model_configuration_prevents_the_port_call() -> None:
    extractor = RecordingExtractor()
    resolver = FixedConfigurationResolver(
        Failure(LLMError(LLMErrorKind.CONFIGURATION, "Kein Extraction-Modell."))
    )

    result = operation(extractor, resolver).apply(request())

    assert isinstance(result, Failure)
    assert extractor.call is None


def test_an_unknown_prompt_package_fails_before_the_port_call() -> None:
    extractor = RecordingExtractor()
    broken = replace(w.configuration(), prompt_package_id="does.not.exist")

    result = operation(extractor).apply(request(broken))

    assert isinstance(result, Failure)
    assert result.error.kind is StoryTurnErrorKind.INVALID_CONFIGURATION
    assert extractor.call is None
