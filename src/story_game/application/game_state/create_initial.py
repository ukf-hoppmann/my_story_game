"""Create the first canonical revision of a story-game run."""

from __future__ import annotations

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.ports import GameStateStoreError, GameStateWriter
from story_game.domain import DomainError, GameState

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError, RunConflict


class CreateInitialGameState:
    """Persist the first revision of a canonical game-state stream."""

    def __init__(self, writer: GameStateWriter) -> None:
        self._writer = writer

    def apply(
        self, state: GameState
    ) -> OperationResult[GameState, GameStateOperationError]:
        if state.revision.value != 1:
            return Failure(RunConflict("Der initiale State muss Revision 1 besitzen"))
        try:
            self._writer.create_initial(state)
        except (GameStateStoreError, DomainError) as error:
            return Failure(map_game_state_error(error))
        return Success(state)
