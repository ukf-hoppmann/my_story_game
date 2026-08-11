from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from story_game.application import Failure, Success
from story_game.application.initialization_errors import StoryInitializationErrorKind
from story_game.application.initialization_models import PlayerCharacterSeed
from story_game.application.initial_world_extraction import (
    ExtractInitialWorldState,
    ExtractInitialWorldStateRequest,
)
from story_game.application.llm import (
    CandidateEntity,
    CandidateFact,
    CandidateLink,
    GenerationConfiguration,
    GenerationOptions,
    InitialExtractionPromptSelectionResolver,
    LLMError,
    LLMErrorKind,
    ModelSelection,
    WorldInitializationCandidate,
)
from story_game.domain import (
    ActorRole,
    EntityKind,
    GameConfiguration,
    PromptProfile,
    RelationKind,
    StoryInitialization,
    StoryState,
)
from story_game.infrastructure.llm import FilePromptPackageCatalog
from tests.ids import sid


PROMPT_ROOT = Path(__file__).parents[2] / "prompts"


class FixedConfigurationResolver:
    def resolve(self, task):
        assert task.value == "extraction"
        return Success(
            GenerationConfiguration(
                ModelSelection("lmstudio", "extractor"),
                GenerationOptions(temperature=0.1),
            )
        )


class RecordingExtractor:
    def __init__(self, result) -> None:
        self.result = result
        self.call = None

    def extract(self, call):
        self.call = call
        return self.result


def configuration(
    perspective: str = "first_person",
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


def story_state() -> StoryState:
    return StoryState(
        initialization=StoryInitialization(
            "Dieser Prompt darf nicht extrahiert werden.",
            "Maren und Alma betreten den alten Dungeon.",
            datetime(2026, 8, 10, tzinfo=UTC),
        )
    )


def player_character() -> PlayerCharacterSeed:
    return PlayerCharacterSeed("Maren", "Eine vorsichtige Kartografin.")


def operation(extractor: RecordingExtractor) -> ExtractInitialWorldState:
    values = iter((f"id-{number}" for number in range(1, 20)))
    return ExtractInitialWorldState(
        InitialExtractionPromptSelectionResolver(
            FilePromptPackageCatalog(PROMPT_ROOT)
        ),
        FixedConfigurationResolver(),
        extractor,
        lambda: sid(next(values)),
    )


def test_builds_complete_initial_world_state_and_keeps_request_minimal() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("alma", EntityKind.CHARACTER, "Alma"),
                    CandidateEntity("dungeon", EntityKind.LOCATION, "Alter Dungeon"),
                ),
                links=(
                    CandidateLink(
                        "player_character", "dungeon", RelationKind.LOCATED_IN
                    ),
                    CandidateLink("alma", "dungeon", RelationKind.LOCATED_IN),
                ),
                facts=(CandidateFact("Alma begleitet Maren.", "alma"),),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), player_character()
        )
    )

    assert isinstance(result, Success)
    world = result.data
    assert [entity.label for entity in world.entities] == [
        "Maren",
        "Alma",
        "Alter Dungeon",
    ]
    assert world.entities[0].actor is not None
    assert world.entities[0].actor.role is ActorRole.PLAYER
    assert world.entities[1].actor is not None
    assert world.entities[1].actor.role is ActorRole.NEUTRAL
    assert world.entities[2].actor is None
    assert world.knowledge == ()
    assert world.rules == ()
    assert world.goals == ()
    assert all(link.visibility.scope.value == "public" for link in world.links)
    assert world.facts[0].visibility.scope.value == "public"
    request = extractor.call.request
    assert request.opening_narration == story_state().initialization.narration
    assert request.player_character == player_character()
    assert request.perspective == "first_person"
    assert request.control_mode == "player"
    assert len(request.system_prompts) == 2
    assert "Der bekannte Spieler heißt 'Maren'" in request.system_prompts[1]
    assert "unbestätigten Vorschlagsresultat" not in request.system_prompts[0]
    assert "Dieser Prompt darf nicht extrahiert werden." not in repr(request)
    assert not hasattr(request, "initial_prompt")
    assert not hasattr(request, "genre")
    assert not hasattr(request, "world_state")


def test_director_mode_can_produce_an_empty_world_without_a_character() -> None:
    extractor = RecordingExtractor(Success(WorldInitializationCandidate()))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration("third_person_omniscient", "director"), story_state()
        )
    )

    assert isinstance(result, Success)
    assert result.data.entities == ()
    assert extractor.call.request.player_character is None


def test_requires_an_opening_before_calling_the_model() -> None:
    extractor = RecordingExtractor(Success(WorldInitializationCandidate()))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), StoryState(), player_character()
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_CONFIGURATION
    assert extractor.call is None


@pytest.mark.parametrize(
    "candidate",
    [
        WorldInitializationCandidate(
            entities=(CandidateEntity("player_character", EntityKind.CHARACTER, "Alma"),)
        ),
        WorldInitializationCandidate(
            entities=(CandidateEntity("maren_copy", EntityKind.CHARACTER, "MAREN"),)
        ),
        WorldInitializationCandidate(
            entities=(CandidateEntity("alma", EntityKind.CHARACTER, "Alma", aliases=("maren",)),)
        ),
        WorldInitializationCandidate(
            links=(CandidateLink("missing", "player_character", RelationKind.KNOWS),)
        ),
    ],
)
def test_rejects_reserved_duplicate_or_unknown_candidate_references(candidate) -> None:
    extractor = RecordingExtractor(Success(candidate))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), player_character()
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_CANDIDATE_REFERENCE


def test_domain_invariant_rejects_the_entire_candidate() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(CandidateEntity("sword", EntityKind.ITEM, "Schwert"),),
                links=(
                    CandidateLink(
                        "player_character", "sword", RelationKind.LOCATED_IN
                    ),
                ),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), player_character()
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.DOMAIN_REJECTION


def test_invalid_model_response_remains_visible_without_retry() -> None:
    cause = LLMError(LLMErrorKind.INVALID_RESPONSE, "Kein gültiges JSON")
    extractor = RecordingExtractor(Failure(cause))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), player_character()
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_MODEL_RESPONSE
    assert result.error.cause is cause
    assert extractor.call is not None
