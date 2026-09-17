from __future__ import annotations

from story_game.application import Failure, Success
from story_game.application.game_models import CachedGameRunProposal
from story_game.application.initialization_models import InitializedStory
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
)
from story_game.application.initialization_models import ControllableCharacterSeed
from story_game.application.propose_game_run import ProposeGameRun, ProposeGameRunRequest
from story_game.application.run_initiator import RunInitiator
from story_game.domain import (
    ActorProfile,
    ActorRole,
    EntityKind,
    GameConfiguration,
    PromptProfile,
    StoryState,
    WorldEntity,
    WorldState,
)
from tests.ids import sid


def configuration(control_mode: str = "director") -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone="balanced",
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode=control_mode,
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        narrative_boundaries=(),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


class RecordingStoryInitializer:
    def __init__(self, result):
        self.result = result
        self.requests = []

    def apply(self, request):
        self.requests.append(request)
        return self.result


class RecordingProposalStore:
    def __init__(self):
        self.saved: dict = {}

    def save(self, proposal_id, proposal):
        self.saved[proposal_id] = proposal

    def load(self, proposal_id):
        return self.saved.get(proposal_id)

    def delete(self, proposal_id):
        self.saved.pop(proposal_id, None)


def initiator() -> RunInitiator:
    return RunInitiator("https://identity.example/story", "user-1")


def request(
    *,
    control_mode: str = "director",
    controllable_characters: tuple[ControllableCharacterSeed, ...] = (),
) -> ProposeGameRunRequest:
    return ProposeGameRunRequest(
        configuration=configuration(control_mode),
        initial_prompt="Maren betritt den Dungeon.",
        initiator=initiator(),
        controllable_characters=controllable_characters,
    )


def test_proposes_without_persisting_a_game_run() -> None:
    alma = WorldEntity(
        id=sid("alma"),
        kind=EntityKind.CHARACTER,
        label="Alma",
        actor=ActorProfile(ActorRole.NEUTRAL),
    )
    initializer = RecordingStoryInitializer(
        Success(
            InitializedStory(
                StoryState(), WorldState(entities=(alma,)), "Der Dungeon"
            )
        )
    )
    store = RecordingProposalStore()
    operation = ProposeGameRun(initializer, store, new_id=lambda: sid("proposal"))

    result = operation.apply(request())

    assert isinstance(result, Success)
    proposal = result.data
    assert proposal.proposal_id == sid("proposal")
    assert proposal.world_state.entities == (alma,)
    assert proposal.suggested_title == "Der Dungeon"
    cached = store.load(sid("proposal"))
    assert cached == CachedGameRunProposal(
        issuer="https://identity.example/story",
        subject="user-1",
        configuration=configuration(),
        story_state=StoryState(),
        world_state=WorldState(entities=(alma,)),
        suggested_title="Der Dungeon",
    )


def test_carries_continuation_options_from_the_initializer_into_the_proposal() -> None:
    initializer = RecordingStoryInitializer(
        Success(
            InitializedStory(
                StoryState(),
                WorldState(),
                "Der Dungeon",
                ("Weitergehen", "Umkehren"),
            )
        )
    )
    store = RecordingProposalStore()
    operation = ProposeGameRun(initializer, store, new_id=lambda: sid("proposal"))

    result = operation.apply(request())

    assert isinstance(result, Success)
    assert result.data.continuation_options == ("Weitergehen", "Umkehren")


def test_suggests_the_player_role_by_name_match_against_seeds() -> None:
    maren = WorldEntity(
        id=sid("maren"), kind=EntityKind.CHARACTER, label="Maren",
        actor=ActorProfile(ActorRole.NEUTRAL),
    )
    jonas = WorldEntity(
        id=sid("jonas"), kind=EntityKind.CHARACTER, label="Jonas",
        actor=ActorProfile(ActorRole.NEUTRAL),
    )
    dungeon = WorldEntity(id=sid("dungeon"), kind=EntityKind.LOCATION, label="Dungeon")
    initializer = RecordingStoryInitializer(
        Success(
            InitializedStory(
                StoryState(), WorldState(entities=(maren, jonas, dungeon))
            )
        )
    )
    store = RecordingProposalStore()
    operation = ProposeGameRun(initializer, store, new_id=lambda: sid("proposal"))

    result = operation.apply(
        request(controllable_characters=(ControllableCharacterSeed("Maren"),))
    )

    assert isinstance(result, Success)
    assert result.data.suggested_player_entity_ids == (sid("maren"),)


def test_no_seeds_means_no_suggestions() -> None:
    initializer = RecordingStoryInitializer(
        Success(InitializedStory(StoryState(), WorldState()))
    )
    store = RecordingProposalStore()
    operation = ProposeGameRun(initializer, store, new_id=lambda: sid("proposal"))

    result = operation.apply(request())

    assert isinstance(result, Success)
    assert result.data.suggested_player_entity_ids == ()


def test_does_not_cache_anything_when_story_initialization_fails() -> None:
    error = StoryInitializationError(
        StoryInitializationErrorKind.MODEL_FAILURE,
        StoryInitializationStage.STORY_GENERATION,
        "Das Story-Modell ist nicht erreichbar.",
    )
    initializer = RecordingStoryInitializer(Failure(error))
    store = RecordingProposalStore()
    operation = ProposeGameRun(initializer, store, new_id=lambda: sid("proposal"))

    result = operation.apply(request())

    assert result == Failure(error)
    assert store.saved == {}
