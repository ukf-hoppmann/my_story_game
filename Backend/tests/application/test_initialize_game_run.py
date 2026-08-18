from __future__ import annotations

from datetime import UTC, datetime

from story_game.application import Failure, Success
from story_game.application.game_state.errors import RunConflict, StateRejected
from story_game.application.game_models import LoadedGame
from story_game.application.initialize_game_run import (
    InitializeGameRun,
    InitializeGameRunRequest,
    RunInitiator,
)
from story_game.application.initialization_models import InitializedStory, PlayerCharacterSeed
from story_game.application.initialization_errors import (
    StoryInitializationError,
    StoryInitializationErrorKind,
    StoryInitializationStage,
)
from story_game.domain import (
    ActorProfile,
    ActorRole,
    EntityKind,
    GameConfiguration,
    GameRole,
    GameRunStatus,
    GameState,
    PromptProfile,
    StableId,
    StateRevision,
    StoryState,
    WorldEntity,
    WorldState,
)
from tests.ids import sid


FIXED_TIME = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)


def configuration(control_mode: str = "player") -> GameConfiguration:
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


class RecordingGameRunCreator:
    def __init__(self):
        self.requests = []
        self.result = None

    def apply(self, request):
        self.requests.append(request)
        if self.result is None:
            self.result = Success(LoadedGame(request.run, request.state))
        return self.result


def initialized_story(*entities: WorldEntity) -> InitializedStory:
    return InitializedStory(StoryState(), WorldState(entities=entities))


def request(
    *,
    control_mode: str = "player",
    player_character: PlayerCharacterSeed | None = PlayerCharacterSeed("Maren"),
) -> InitializeGameRunRequest:
    return InitializeGameRunRequest(
        configuration=configuration(control_mode),
        run_name="Maren und das magische Schwert",
        initial_prompt="Maren betritt den Dungeon.",
        initiator=RunInitiator("https://identity.example/story", "user-1"),
        player_character=player_character,
    )


def test_initializes_and_persists_a_player_game_at_revision_one() -> None:
    player = WorldEntity(
        id=sid("player"),
        kind=EntityKind.CHARACTER,
        label="Maren",
        actor=ActorProfile(ActorRole.PLAYER),
    )
    story_initializer = RecordingStoryInitializer(Success(initialized_story(player)))
    creator = RecordingGameRunCreator()
    operation = InitializeGameRun(
        story_initializer,
        creator,
        new_id=lambda: sid("run"),
        now=lambda: FIXED_TIME,
    )

    result = operation.apply(request())

    assert isinstance(result, Success)
    assert len(creator.requests) == 1
    persisted = creator.requests[0]
    assert persisted.run.id == sid("run")
    assert persisted.run.name == "Maren und das magische Schwert"
    assert persisted.run.status is GameRunStatus.DRAFT
    assert persisted.run.current_revision == StateRevision(1)
    assert persisted.run.created_at == FIXED_TIME
    assert persisted.run.updated_at == FIXED_TIME
    assert persisted.run.members[0].identity == (
        "https://identity.example/story",
        "user-1",
    )
    assert persisted.run.members[0].game_role is GameRole.OWNER
    assert persisted.run.members[0].player_entity_id == player.id
    assert persisted.state == GameState(
        sid("run"),
        StateRevision(1),
        configuration(),
        WorldState(entities=(player,)),
        StoryState(),
    )


def test_initializes_a_director_game_without_a_player_binding() -> None:
    story_initializer = RecordingStoryInitializer(Success(initialized_story()))
    creator = RecordingGameRunCreator()
    operation = InitializeGameRun(
        story_initializer,
        creator,
        new_id=lambda: sid("run"),
        now=lambda: FIXED_TIME,
    )

    result = operation.apply(request(control_mode="director", player_character=None))

    assert isinstance(result, Success)
    member = creator.requests[0].run.members[0]
    assert member.game_role is GameRole.OWNER
    assert member.player_entity_id is None


def test_does_not_persist_when_story_initialization_fails() -> None:
    error = StoryInitializationError(
        StoryInitializationErrorKind.MODEL_FAILURE,
        StoryInitializationStage.STORY_GENERATION,
        "Das Story-Modell ist nicht erreichbar.",
    )
    story_initializer = RecordingStoryInitializer(Failure(error))
    creator = RecordingGameRunCreator()
    operation = InitializeGameRun(story_initializer, creator)

    result = operation.apply(request())

    assert result == Failure(error)
    assert creator.requests == []


def test_rejects_player_mode_without_exactly_one_player_entity() -> None:
    story_initializer = RecordingStoryInitializer(Success(initialized_story()))
    creator = RecordingGameRunCreator()
    operation = InitializeGameRun(story_initializer, creator)

    result = operation.apply(request())

    assert result == Failure(
        StateRejected("Der Player Mode benötigt genau einen Spielercharakter im WorldState")
    )
    assert creator.requests == []


def test_rejects_director_mode_with_a_player_entity() -> None:
    player = WorldEntity(
        id=sid("player"),
        kind=EntityKind.CHARACTER,
        label="Maren",
        actor=ActorProfile(ActorRole.PLAYER),
    )
    story_initializer = RecordingStoryInitializer(Success(initialized_story(player)))
    creator = RecordingGameRunCreator()
    operation = InitializeGameRun(story_initializer, creator)

    result = operation.apply(request(control_mode="director", player_character=None))

    assert result == Failure(
        StateRejected("Der Director Mode darf keinen Spielercharakter im WorldState enthalten")
    )
    assert creator.requests == []


def test_propagates_persistence_conflicts_without_a_partial_result() -> None:
    story_initializer = RecordingStoryInitializer(Success(initialized_story()))
    creator = RecordingGameRunCreator()
    creator.result = Failure(RunConflict("Die Run-ID existiert bereits."))
    operation = InitializeGameRun(story_initializer, creator)

    result = operation.apply(request(control_mode="director", player_character=None))

    assert result == Failure(RunConflict("Die Run-ID existiert bereits."))
    assert len(creator.requests) == 1
