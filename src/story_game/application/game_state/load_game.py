"""Load run metadata and one complete canonical state revision."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.ports import GameRunReader, GameStateReader, GameStateStoreError
from story_game.domain import DomainError, StableId, StateRevision

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError
from story_game.application.game_models import LoadedGame


@dataclass(frozen=True, slots=True)
class LoadGameRequest:
    run_id: StableId
    revision: StateRevision | None = None


class LoadGame:
    def __init__(self, run_reader: GameRunReader, state_reader: GameStateReader) -> None:
        self.run_reader = run_reader
        self.state_reader = state_reader

    def apply(
        self, request: LoadGameRequest
    ) -> OperationResult[LoadedGame, GameStateOperationError]:
        try:
            run = self.run_reader.load_run(request.run_id)
            state = self.state_reader.load_state(
                request.run_id, revision=request.revision
            )
            state.validate_members(run.members)
        except (GameStateStoreError, DomainError) as error:
            return Failure(map_game_state_error(error))
        return Success(LoadedGame(run, state))
