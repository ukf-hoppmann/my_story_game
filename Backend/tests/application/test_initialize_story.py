from __future__ import annotations

from datetime import UTC, datetime

from story_game.application import Failure, Success
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
)
from story_game.application.initialization_models import (
    ControllableCharacterSeed,
    InitializedStory,
)
from story_game.application.initial_world_extraction import WorldExtractionResult
from story_game.application.initialize_story import InitializeStory, InitializeStoryRequest
from story_game.application.story_initialization import GeneratedStoryOpening
from story_game.domain import (
    GameConfiguration,
    PromptProfile,
    StoryInitialization,
    StoryState,
    WorldState,
)


class RecordingOperation:
    def __init__(self, result) -> None:
        self.result = result
        self.requests = []

    def apply(self, request):
        self.requests.append(request)
        return self.result


def configuration() -> GameConfiguration:
    return GameConfiguration(
        "de",
        PromptProfile(
            genre="fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="first_person",
            pacing="balanced",
            control_mode="player",
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        (),
        "story.base",
        "1",
    )


def test_orchestrates_story_then_world_and_returns_both_transient_states() -> None:
    story = StoryState(
        initialization=StoryInitialization(
            "Maren geht in den Dungeon.",
            "Maren betritt den Dungeon.",
            datetime(2026, 8, 10, tzinfo=UTC),
        )
    )
    world = WorldState()
    story_generation = RecordingOperation(
        Success(GeneratedStoryOpening(story, ("Weitergehen", "Umkehren")))
    )
    world_extraction = RecordingOperation(
        Success(WorldExtractionResult(world, "Der Dungeon"))
    )
    seed = ControllableCharacterSeed("Maren")

    result = InitializeStory(story_generation, world_extraction).apply(
        InitializeStoryRequest(
            configuration(), "Maren geht in den Dungeon.", (seed,)
        )
    )

    assert result == Success(
        InitializedStory(story, world, "Der Dungeon", ("Weitergehen", "Umkehren"))
    )
    assert story_generation.requests[0].initial_prompt == "Maren geht in den Dungeon."
    extraction_request = world_extraction.requests[0]
    assert extraction_request.story_state is story
    assert extraction_request.controllable_characters == (seed,)
    assert not hasattr(extraction_request, "initial_prompt")


def test_does_not_extract_when_story_generation_fails() -> None:
    error = StoryInitializationError(
        StoryInitializationErrorKind.MODEL_FAILURE,
        StoryInitializationStage.STORY_GENERATION,
        "Story-Modell nicht erreichbar.",
    )
    story_generation = RecordingOperation(Failure(error))
    world_extraction = RecordingOperation(Success(WorldState()))

    result = InitializeStory(story_generation, world_extraction).apply(
        InitializeStoryRequest(
            configuration(), "Maren geht los.", (ControllableCharacterSeed("Maren"),)
        )
    )

    assert result == Failure(error)
    assert world_extraction.requests == []


def test_returns_extraction_failure_without_a_partial_initialized_result() -> None:
    story = StoryState(
        initialization=StoryInitialization(
            "Maren geht los.",
            "Maren geht los.",
            datetime(2026, 8, 10, tzinfo=UTC),
        )
    )
    error = StoryInitializationError(
        StoryInitializationErrorKind.INVALID_MODEL_RESPONSE,
        StoryInitializationStage.WORLD_EXTRACTION,
        "Extraction lieferte kein JSON.",
    )

    result = InitializeStory(
        RecordingOperation(Success(GeneratedStoryOpening(story))),
        RecordingOperation(Failure(error)),
    ).apply(
        InitializeStoryRequest(
            configuration(), "Maren geht los.", (ControllableCharacterSeed("Maren"),)
        )
    )

    assert result == Failure(error)
