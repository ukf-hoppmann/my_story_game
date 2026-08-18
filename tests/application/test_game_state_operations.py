from __future__ import annotations

from datetime import UTC, datetime

import story_game.application.game_state as operations
from story_game.application import Failure, Success
from story_game.application.diagnostics import RevisionConflict
from story_game.application.game_models import ConfigurationPersistenceRequest
from story_game.application.llm import PromptCategory, PromptOption, PromptPackage
from story_game.application.ports import (
    GameStateConflictError,
    GameStateNotFoundError,
)
from story_game.domain import (
    ApprovedChangeSet,
    GameConfiguration,
    GameRole,
    GameRun,
    GameRunMember,
    GameRunStatus,
    GameState,
    PromptProfile,
    StableId,
    StateRevision,
    StoryState,
    WorldState,
)
from tests.application.diagnostics_double import FakeDiagnosticsLog
from tests.ids import sid


def configuration(tone: str = "balanced") -> GameConfiguration:
    return GameConfiguration(
        language="de",
        prompt_profile=PromptProfile(
            genre="dark_fantasy",
            tone=tone,
            prose_style="balanced",
            perspective="third_person_limited",
            pacing="balanced",
            control_mode="player",
            player_agency="strict",
            consequence="balanced",
            challenge="balanced",
            content_profile="teen",
        ),
        narrative_boundaries=(),
        prompt_package_id="story.base",
        prompt_package_version="1",
    )


class PromptCatalog:
    def __init__(self) -> None:
        options = {
            "genre": "dark_fantasy",
            "tone": "balanced",
            "prose_style": "balanced",
            "perspective": "third_person_limited",
            "pacing": "balanced",
            "control_mode": "player",
            "player_agency": "strict",
            "consequence": "balanced",
            "challenge": "balanced",
            "content_profile": "teen",
        }
        self.package = PromptPackage(
            id="story.base",
            version="1",
            tasks=(),
            categories=tuple(
                PromptCategory(
                    category_id,
                    option_id,
                    (
                        PromptOption(option_id, f"{category_id} instruction"),
                        *(
                            (PromptOption("dark", "dark tone"),)
                            if category_id == "tone"
                            else ()
                        ),
                    ),
                )
                for category_id, option_id in options.items()
            ),
            directives=(),
        )

    def load(self, package_id: str, version: str) -> PromptPackage:
        assert (package_id, version) == ("story.base", "1")
        return self.package


def validator() -> object:
    assert hasattr(operations, "PromptProfileValidator")
    return operations.PromptProfileValidator(PromptCatalog())


def initial() -> tuple[GameRun, GameState]:
    timestamp = datetime(2026, 8, 6, tzinfo=UTC)
    member = GameRunMember("issuer", "subject", GameRole.OWNER)
    run = GameRun(
        sid("run-1"),
        "Almas und das magische Schwert",
        GameRunStatus.DRAFT,
        StateRevision(1),
        (member,),
        timestamp,
        timestamp,
    )
    state = GameState(
        run.id,
        StateRevision(1),
        configuration(),
        WorldState(),
        StoryState(),
    )
    return run, state


class FakeStore:
    def __init__(self) -> None:
        self.run, self.state = initial()
        self.created: tuple[GameRun, GameState] | None = None
        self.configuration_request: object | None = None
        self.turn_request: object | None = None

    def create(self, run: GameRun, state: GameState) -> None:
        self.created = run, state

    def load_run(self, run_id: StableId) -> GameRun:
        if run_id != self.run.id:
            raise GameStateNotFoundError("missing")
        return self.run

    def load_state(
        self, run_id: StableId, *, revision: StateRevision | None = None
    ) -> GameState:
        if run_id != self.run.id:
            raise GameStateNotFoundError("missing")
        return self.state

    def update_configuration(self, request: object) -> GameState:
        self.configuration_request = request
        return self.state.reconfigure(
            request.configuration, base_revision=request.base_revision  # type: ignore[attr-defined]
        )

    def commit_turn(self, request: object) -> GameState:
        self.turn_request = request
        return self.state.complete_turn(
            request.changes,  # type: ignore[attr-defined]
            request.turn,  # type: ignore[attr-defined]
            request.summary,  # type: ignore[attr-defined]
        )


def test_create_game_run_validates_and_writes_the_complete_initial_state() -> None:
    assert hasattr(operations, "CreateGameRun")
    run, state = initial()
    store = FakeStore()

    result = operations.CreateGameRun(store, validator()).apply(
        operations.CreateGameRunRequest(run, state)
    )

    assert result == Success(operations.LoadedGame(run, state))
    assert store.created == (run, state)


def test_load_game_returns_run_metadata_and_requested_state() -> None:
    assert hasattr(operations, "LoadGame")
    run, state = initial()
    store = FakeStore()

    result = operations.LoadGame(store, store).apply(
        operations.LoadGameRequest(run.id)
    )

    assert result == Success(operations.LoadedGame(run, state))


def test_load_game_maps_missing_run_to_typed_failure() -> None:
    assert hasattr(operations, "LoadGame")
    store = FakeStore()

    result = operations.LoadGame(store, store).apply(
        operations.LoadGameRequest(sid("missing"))
    )

    assert isinstance(result, Failure)


def test_configuration_revision_uses_a_dedicated_writer() -> None:
    assert hasattr(operations, "UpdateGameConfiguration")
    store = FakeStore()
    request = operations.UpdateGameConfigurationRequest(
        sid("run-1"), StateRevision(1), configuration("dark")
    )

    result = operations.UpdateGameConfiguration(store, validator()).apply(request)

    assert isinstance(result, Success)
    assert store.configuration_request == ConfigurationPersistenceRequest(
        request.run_id,
        request.base_revision,
        request.configuration,
    )


def test_create_game_run_rejects_an_unknown_prompt_option_before_writing() -> None:
    assert hasattr(operations, "InvalidPromptSelection")
    run, state = initial()
    invalid = GameState(
        state.run_id,
        state.revision,
        configuration("unknown"),
        state.world,
        state.story,
    )
    store = FakeStore()

    result = operations.CreateGameRun(store, validator()).apply(
        operations.CreateGameRunRequest(run, invalid)
    )

    assert result == Failure(operations.InvalidPromptSelection("tone", "unknown"))
    assert store.created is None


def test_configuration_update_rejects_an_unknown_prompt_option_before_writing() -> None:
    assert hasattr(operations, "InvalidPromptSelection")
    store = FakeStore()
    request = operations.UpdateGameConfigurationRequest(
        sid("run-1"), StateRevision(1), configuration("unknown")
    )

    result = operations.UpdateGameConfiguration(store, validator()).apply(request)

    assert result == Failure(operations.InvalidPromptSelection("tone", "unknown"))
    assert store.configuration_request is None


def test_completed_turn_is_sent_as_one_atomic_persistence_request() -> None:
    assert hasattr(operations, "CommitCompletedTurn")
    store = FakeStore()
    request = operations.CommitCompletedTurnRequest(
        run_id=sid("run-1"),
        changes=ApprovedChangeSet(sid("proposal-1"), StateRevision(1)),
        turn_id=sid("turn-1"),
        player_input="Ich öffne die Tür.",
        narration="Die Tür schwingt auf.",
        summary_text="Almas hat die Tür geöffnet.",
        completed_at=datetime(2026, 8, 6, tzinfo=UTC),
    )

    result = operations.CommitCompletedTurn(store, store).apply(request)

    assert isinstance(result, Success)
    assert store.turn_request is not None
    assert store.turn_request.turn.sequence.value == 1  # type: ignore[attr-defined]


def test_completed_turn_maps_a_stale_revision_to_conflict() -> None:
    assert hasattr(operations, "CommitCompletedTurn")

    class ConflictingStore(FakeStore):
        def commit_turn(self, request: object) -> GameState:
            raise GameStateConflictError("stale")

    request = operations.CommitCompletedTurnRequest(
        run_id=sid("run-1"),
        changes=ApprovedChangeSet(sid("proposal-1"), StateRevision(1)),
        turn_id=sid("turn-1"),
        player_input="Weiter.",
        narration="Die Geschichte geht weiter.",
        summary_text=None,
        completed_at=datetime(2026, 8, 6, tzinfo=UTC),
    )

    store = ConflictingStore()
    diagnostics = FakeDiagnosticsLog()
    result = operations.CommitCompletedTurn(store, store, diagnostics).apply(request)

    assert isinstance(result, Failure)
    assert len(diagnostics.recorded) == 1
    assert isinstance(diagnostics.recorded[0], RevisionConflict)
