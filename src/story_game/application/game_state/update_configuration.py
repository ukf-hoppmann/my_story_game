"""Persist one state-only configuration revision."""

from __future__ import annotations

from dataclasses import dataclass

from story_game.application.contracts import Failure, OperationResult, Success
from story_game.application.ports import ConfigurationRevisionWriter, GameStateStoreError
from story_game.domain import DomainError, GameConfiguration, GameState, StableId, StateRevision

from .error_mapping import map_game_state_error
from .errors import GameStateOperationError
from story_game.application.game_models import ConfigurationPersistenceRequest


@dataclass(frozen=True, slots=True)
class UpdateGameConfigurationRequest:
    run_id: StableId
    base_revision: StateRevision
    configuration: GameConfiguration


class UpdateGameConfiguration:
    def __init__(self, writer: ConfigurationRevisionWriter) -> None:
        self.writer = writer

    def apply(
        self, request: UpdateGameConfigurationRequest
    ) -> OperationResult[GameState, GameStateOperationError]:
        persistence_request = ConfigurationPersistenceRequest(
            request.run_id, request.base_revision, request.configuration
        )
        try:
            state = self.writer.update_configuration(persistence_request)
        except (GameStateStoreError, DomainError) as error:
            return Failure(map_game_state_error(error))
        return Success(state)
