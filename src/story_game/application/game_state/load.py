"""Load one canonical game-state revision."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.ports import GameStateReader, GameStateStoreError
from story_game.domain import GameState, StableId, StateRevision

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError


@dataclass(frozen=True, slots=True)
class LoadGameStateRequest:
    run_id: StableId
    revision: StateRevision | None = None


class LoadGameState:
    """Load the current or explicitly requested canonical revision."""

    def __init__(self, reader: GameStateReader) -> None:
        self._reader = reader

    def apply(
        self, request: LoadGameStateRequest
    ) -> OperationResult[GameState, GameStateOperationError]:
        try:
            state = self._reader.load(request.run_id, revision=request.revision)
        except GameStateStoreError as error:
            return Failure(map_game_state_error(error))
        return Success(state)
