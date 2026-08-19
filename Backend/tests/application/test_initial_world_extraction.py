from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from story_game.application import Failure, Success
from story_game.application.initialization_errors import StoryInitializationErrorKind
from story_game.application.initialization_models import ControllableCharacterSeed
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


def player_character() -> ControllableCharacterSeed:
    return ControllableCharacterSeed("Maren", "Eine vorsichtige Kartografin.")


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


def test_builds_complete_initial_world_state_as_one_neutral_cast() -> None:
    """No entity is pre-assigned the player role during extraction.

    Even though a ``controllable_characters`` seed is supplied (for prose
    grounding and, later, the confirmation-time role suggestion), the
    extracted "Maren" entity comes back exactly like any other character:
    role assignment is a caller decision made after this step, not part of
    it — see ``propose_game_run.py`` / ``confirm_game_run_proposal.py``.
    """
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("maren", EntityKind.CHARACTER, "Maren"),
                    CandidateEntity("alma", EntityKind.CHARACTER, "Alma"),
                    CandidateEntity("dungeon", EntityKind.LOCATION, "Alter Dungeon"),
                ),
                links=(
                    CandidateLink("maren", "dungeon", RelationKind.LOCATED_IN),
                    CandidateLink("alma", "dungeon", RelationKind.LOCATED_IN),
                ),
                facts=(CandidateFact("Alma begleitet Maren.", "alma"),),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
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
    assert world.entities[0].actor.role is ActorRole.NEUTRAL
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
    assert not hasattr(request, "controllable_characters")
    assert request.perspective == "first_person"
    assert request.control_mode == "player"
    assert len(request.system_prompts) == 1
    assert "player_character" not in request.system_prompts[0]
    assert "unbestätigten Vorschlagsresultat" not in request.system_prompts[0]
    assert "Dieser Prompt darf nicht extrahiert werden." not in repr(request)
    assert not hasattr(request, "initial_prompt")
    assert not hasattr(request, "genre")
    assert not hasattr(request, "world_state")


def test_scene_references_become_ordered_stable_ids() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("dungeon", EntityKind.LOCATION, "Alter Dungeon"),
                    CandidateEntity("hall", EntityKind.LOCATION, "Große Halle"),
                ),
                scene_refs=("hall", "dungeon"),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Success)
    world = result.data
    hall = next(item for item in world.entities if item.label == "Große Halle")
    dungeon = next(item for item in world.entities if item.label == "Alter Dungeon")
    assert world.scene_location_ids == (hall.id, dungeon.id)
    assert world.primary_scene_location() == hall.id


def test_a_world_without_scene_references_has_no_scene() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(CandidateEntity("dungeon", EntityKind.LOCATION, "Dungeon"),)
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Success)
    assert result.data.scene_location_ids == ()


def test_unknown_scene_reference_rejects_the_entire_candidate() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(CandidateEntity("dungeon", EntityKind.LOCATION, "Dungeon"),),
                scene_refs=("missing",),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_CANDIDATE_REFERENCE


@pytest.mark.parametrize(
    "candidate",
    [
        pytest.param(
            WorldInitializationCandidate(
                entities=(CandidateEntity("dungeon", EntityKind.LOCATION, "Dungeon"),),
                scene_refs=("dungeon", "Dungeon"),
            ),
            id="duplicate_scene_reference",
        ),
        pytest.param(
            WorldInitializationCandidate(
                entities=(CandidateEntity("alma", EntityKind.CHARACTER, "Alma"),),
                scene_refs=("alma",),
            ),
            id="scene_reference_is_not_a_location",
        ),
    ],
)
def test_invalid_scene_references_reject_the_entire_candidate(candidate) -> None:
    extractor = RecordingExtractor(Success(candidate))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.DOMAIN_REJECTION


def test_director_mode_can_produce_an_empty_world_without_a_character() -> None:
    extractor = RecordingExtractor(Success(WorldInitializationCandidate()))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration("third_person_omniscient", "director"), story_state()
        )
    )

    assert isinstance(result, Success)
    assert result.data.entities == ()


def test_director_mode_freely_extracts_several_characters_as_neutral() -> None:
    """Director Mode without any seed no longer needs a reserved reference.

    Nothing tells the model "player_character" exists in this run — it just
    is not mentioned at all — so a model that extracts several ordinary
    characters cannot accidentally collide with a reservation that was never
    made. This is the fix for the reported Director-Mode crash.
    """
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("maren", EntityKind.CHARACTER, "Maren"),
                    CandidateEntity("jonas", EntityKind.CHARACTER, "Jonas"),
                    CandidateEntity("dungeon", EntityKind.LOCATION, "Dungeon"),
                ),
                links=(
                    CandidateLink("jonas", "dungeon", RelationKind.LOCATED_IN),
                ),
                facts=(CandidateFact("Maren kennt den Dungeon.", "maren"),),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration("third_person_omniscient", "director"), story_state()
        )
    )

    assert isinstance(result, Success)
    world = result.data
    assert [entity.label for entity in world.entities[:2]] == ["Maren", "Jonas"]
    assert world.entities[0].actor.role is ActorRole.NEUTRAL
    assert world.entities[1].actor.role is ActorRole.NEUTRAL
    request = extractor.call.request
    assert len(request.system_prompts) == 1
    assert "player_character" not in request.system_prompts[0]


def test_duplicate_controllable_character_names_are_rejected_before_the_model_call() -> None:
    extractor = RecordingExtractor(Success(WorldInitializationCandidate()))
    maren = ControllableCharacterSeed("Maren")
    duplicate = ControllableCharacterSeed("MAREN")

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration("third_person_omniscient", "director"),
            story_state(),
            (maren, duplicate),
        )
    )

    assert isinstance(result, Failure)
    assert (
        result.error.kind
        is StoryInitializationErrorKind.DUPLICATE_CONTROLLABLE_CHARACTER
    )
    assert extractor.call is None


def test_player_mode_with_more_than_one_seed_is_rejected_before_the_model_call() -> None:
    extractor = RecordingExtractor(Success(WorldInitializationCandidate()))
    maren = ControllableCharacterSeed("Maren")
    jonas = ControllableCharacterSeed("Jonas")

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(configuration(), story_state(), (maren, jonas))
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.MISSING_PLAYER_CHARACTER
    assert extractor.call is None


def test_requires_an_opening_before_calling_the_model() -> None:
    extractor = RecordingExtractor(Success(WorldInitializationCandidate()))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), StoryState(), (player_character(),)
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_CONFIGURATION
    assert extractor.call is None


def test_a_local_ref_that_happens_to_look_like_the_old_reserved_word_is_ordinary() -> None:
    """``player_character`` carries no special meaning any more.

    It is just a string a model could pick as a local_ref like any other —
    nothing rejects it, and nothing treats it as "the" player.
    """
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("player_character", EntityKind.CHARACTER, "Alma"),
                )
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Success)
    assert result.data.entities[0].label == "Alma"
    assert result.data.entities[0].actor.role is ActorRole.NEUTRAL


def test_a_label_or_alias_matching_a_controllable_character_name_is_no_longer_rejected() -> None:
    """Extraction no longer polices name collisions with caller seeds.

    A model is free to also extract a character named/aliased like a seed;
    whether that becomes "the" player is a caller decision made later, not a
    reason to reject the whole batch here.
    """
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity(
                        "alma", EntityKind.CHARACTER, "Alma", aliases=("maren",)
                    ),
                )
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Success)


@pytest.mark.parametrize(
    "candidate",
    [
        pytest.param(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("maren", EntityKind.CHARACTER, "Maren"),
                    CandidateEntity("maren", EntityKind.CHARACTER, "Andere Maren"),
                )
            ),
            id="duplicate_local_ref",
        ),
        pytest.param(
            WorldInitializationCandidate(
                links=(CandidateLink("missing", "also_missing", RelationKind.KNOWS),)
            ),
            id="unknown_reference",
        ),
    ],
)
def test_rejects_duplicate_or_unknown_candidate_references(candidate) -> None:
    extractor = RecordingExtractor(Success(candidate))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_CANDIDATE_REFERENCE


def test_domain_invariant_rejects_the_entire_candidate() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("maren", EntityKind.CHARACTER, "Maren"),
                    CandidateEntity("sword", EntityKind.ITEM, "Schwert"),
                ),
                links=(
                    CandidateLink("maren", "sword", RelationKind.LOCATED_IN),
                ),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.DOMAIN_REJECTION


def test_exact_duplicate_located_in_links_are_deduplicated() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("maren", EntityKind.CHARACTER, "Maren"),
                    CandidateEntity("room", EntityKind.LOCATION, "Kammer"),
                ),
                links=(
                    CandidateLink("maren", "room", RelationKind.LOCATED_IN),
                    CandidateLink("maren", "room", RelationKind.LOCATED_IN),
                ),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Success)
    located_in_links = [
        link for link in result.data.links if link.kind is RelationKind.LOCATED_IN
    ]
    assert len(located_in_links) == 1


def test_conflicting_located_in_links_still_reject_the_entire_candidate() -> None:
    extractor = RecordingExtractor(
        Success(
            WorldInitializationCandidate(
                entities=(
                    CandidateEntity("maren", EntityKind.CHARACTER, "Maren"),
                    CandidateEntity("room_a", EntityKind.LOCATION, "Kammer A"),
                    CandidateEntity("room_b", EntityKind.LOCATION, "Kammer B"),
                ),
                links=(
                    CandidateLink("maren", "room_a", RelationKind.LOCATED_IN),
                    CandidateLink("maren", "room_b", RelationKind.LOCATED_IN),
                ),
            )
        )
    )

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.DOMAIN_REJECTION


def test_invalid_model_response_remains_visible_without_retry() -> None:
    cause = LLMError(LLMErrorKind.INVALID_RESPONSE, "Kein gültiges JSON")
    extractor = RecordingExtractor(Failure(cause))

    result = operation(extractor).apply(
        ExtractInitialWorldStateRequest(
            configuration(), story_state(), (player_character(),)
        )
    )

    assert isinstance(result, Failure)
    assert result.error.kind is StoryInitializationErrorKind.INVALID_MODEL_RESPONSE
    assert result.error.cause is cause
    assert extractor.call is not None
