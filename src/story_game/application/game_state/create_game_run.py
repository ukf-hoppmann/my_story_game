"""Create one run and its complete initial state."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.ports import GameRunCreator, GameStateStoreError
from story_game.domain import DomainError, GameRun, GameState, StateRevision, ValidationError

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError
from story_game.application.game_models import LoadedGame


@dataclass(frozen=True, slots=True)
class CreateGameRunRequest:
    run: GameRun
    state: GameState


class CreateGameRun:
    def __init__(self, creator: GameRunCreator) -> None:
        self.creator = creator

    def apply(
        self, request: CreateGameRunRequest
    ) -> OperationResult[LoadedGame, GameStateOperationError]:
        try:
            if request.run.id != request.state.run_id:
                raise ValidationError("GameRun und GameState benötigen dieselbe Run-ID")
            if request.run.current_revision != request.state.revision:
                raise ValidationError("GameRun und GameState benötigen dieselbe Revision")
            if request.state.revision != StateRevision(1):
                raise ValidationError("Ein neuer GameRun muss mit Revision 1 beginnen")
            request.state.validate_members(request.run.members)
            self.creator.create(request.run, request.state)
        except (GameStateStoreError, DomainError) as error:
            return Failure(map_game_state_error(error))
        return Success(LoadedGame(request.run, request.state))
