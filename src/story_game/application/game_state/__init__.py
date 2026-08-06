"""Composable operations for persisted game runs and state revisions."""

from .commit_completed_turn import CommitCompletedTurn, CommitCompletedTurnRequest
from .create_game_run import CreateGameRun, CreateGameRunRequest
from .errors import (
    GameStateOperationError,
    RunConflict,
    RunNotFound,
    StateRejected,
    StateStoreUnavailable,
    StoredStateInvalid,
)
from .load_game import LoadGame, LoadGameRequest
from story_game.application.game_models import (
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
    LoadedGame,
)
from .operations import GameStateOperations
from .update_configuration import (
    UpdateGameConfiguration,
    UpdateGameConfigurationRequest,
)

__all__ = [
    "CommitCompletedTurn",
    "CommitCompletedTurnRequest",
    "CompletedTurnPersistenceRequest",
    "ConfigurationPersistenceRequest",
    "CreateGameRun",
    "CreateGameRunRequest",
    "GameStateOperationError",
    "GameStateOperations",
    "LoadGame",
    "LoadGameRequest",
    "LoadedGame",
    "RunConflict",
    "RunNotFound",
    "StateRejected",
    "StateStoreUnavailable",
    "StoredStateInvalid",
    "UpdateGameConfiguration",
    "UpdateGameConfigurationRequest",
]
