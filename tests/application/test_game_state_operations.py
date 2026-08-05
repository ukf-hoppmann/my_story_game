from __future__ import annotations

from dataclasses import replace

import pytest

from story_game.application.contracts import Failure, Success
from story_game.application.game_state import (
    CommitGameStateChanges,
    CommitGameStateRequest,
    CreateInitialGameState,
    LoadGameState,
    LoadGameStateRequest,
    RunConflict,
    RunNotFound,
    StateRejected,
    StateStoreUnavailable,
    StoredStateInvalid,
)
from story_game.application.ports import (
    GameStateConflictError,
    GameStateConsistencyError,
    GameStateNotFoundError,
    GameStateStoreError,
)
from story_game.domain import (
    ApprovedChangeSet,
    ChangeRejectedError,
    GameState,
    RevisionConflictError,
    StableId,
    StateRevision,
    StoryState,
    WorldState,
)


def state(revision: int = 1) -> GameState:
    return GameState(
        id=StableId("run-one"),
        revision=StateRevision(revision),
        world=WorldState(),
        story=StoryState(),
    )


class FakeGameStateStore:
    def __init__(self, current: GameState) -> None:
        self.current = current
        self.error: Exception | None = None
        self.created: GameState | None = None
        self.loaded: tuple[StableId, StateRevision | None] | None = None
        self.committed: tuple[StableId, ApprovedChangeSet] | None = None

    def create_initial(self, initial: GameState) -> None:
        self._raise_error()
        self.created = initial

    def load(
        self,
        run_id: StableId,
        *,
        revision: StateRevision | None = None,
    ) -> GameState:
        self._raise_error()
        self.loaded = (run_id, revision)
        return self.current

    def commit(self, run_id: StableId, changes: ApprovedChangeSet) -> GameState:
        self._raise_error()
        self.committed = (run_id, changes)
        return replace(self.current, revision=self.current.revision.next())

    def _raise_error(self) -> None:
        if self.error is not None:
            raise self.error


def test_create_initial_returns_success_and_calls_writer() -> None:
    initial = state()
    store = FakeGameStateStore(initial)

    result = CreateInitialGameState(store).apply(initial)

    assert result == Success(initial)
    assert store.created == initial


def test_create_initial_rejects_non_initial_revision_without_writing() -> None:
    store = FakeGameStateStore(state())

    result = CreateInitialGameState(store).apply(state(revision=2))

    assert isinstance(result, Failure)
    assert isinstance(result.error, RunConflict)
    assert store.created is None


def test_load_returns_the_requested_revision() -> None:
    current = state()
    store = FakeGameStateStore(current)
    request = LoadGameStateRequest(current.id, StateRevision(1))

    result = LoadGameState(store).apply(request)

    assert result == Success(current)
    assert store.loaded == (current.id, StateRevision(1))


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (GameStateNotFoundError("missing"), RunNotFound),
        (GameStateConflictError("conflict"), RunConflict),
        (GameStateConsistencyError("invalid"), StoredStateInvalid),
        (GameStateStoreError("offline"), StateStoreUnavailable),
    ],
)
def test_load_maps_port_failures(raised: Exception, expected: type[object]) -> None:
    current = state()
    store = FakeGameStateStore(current)
    store.error = raised

    result = LoadGameState(store).apply(LoadGameStateRequest(current.id))

    assert isinstance(result, Failure)
    assert isinstance(result.error, expected)


def test_commit_returns_the_advanced_state() -> None:
    current = state()
    store = FakeGameStateStore(current)
    changes = ApprovedChangeSet(StableId("proposal"), StateRevision(1))

    result = CommitGameStateChanges(store).apply(
        CommitGameStateRequest(current.id, changes)
    )

    assert result == Success(replace(current, revision=StateRevision(2)))
    assert store.committed == (current.id, changes)


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (RevisionConflictError("stale"), RunConflict),
        (ChangeRejectedError("rejected"), StateRejected),
    ],
)
def test_commit_maps_domain_failures(raised: Exception, expected: type[object]) -> None:
    current = state()
    store = FakeGameStateStore(current)
    store.error = raised
    request = CommitGameStateRequest(
        current.id,
        ApprovedChangeSet(StableId("proposal"), StateRevision(1)),
    )

    result = CommitGameStateChanges(store).apply(request)

    assert isinstance(result, Failure)
    assert isinstance(result.error, expected)
