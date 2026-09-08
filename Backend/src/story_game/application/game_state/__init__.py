"""Composable operations for persisted game runs and state revisions."""

from .commit_completed_turn import CommitCompletedTurn, CommitCompletedTurnRequest
from .create_game_run import CreateGameRun, CreateGameRunRequest
from .errors import (
    GameStateOperationError,
    InvalidPromptPackageReference,
    InvalidPromptSelection,
    PromptPackageConfigurationInvalid,
    RunAccessDenied,
    RunConflict,
    RunNotFound,
    StateRejected,
    StateStoreUnavailable,
    StoredStateInvalid,
)
from .list_playable_runs import ListPlayableRuns, ListPlayableRunsRequest
from .load_game import LoadGame, LoadGameRequest
from story_game.application.game_models import (
    CompletedTurnPersistenceRequest,
    ConfigurationPersistenceRequest,
    LoadedGame,
    RunSummary,
)
from .operations import GameStateOperations
from .update_configuration import (
    UpdateGameConfiguration,
    UpdateGameConfigurationRequest,
)
from .prompt_profile_validation import PromptProfileValidator

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
    "InvalidPromptPackageReference",
    "InvalidPromptSelection",
    "ListPlayableRuns",
    "ListPlayableRunsRequest",
    "PromptPackageConfigurationInvalid",
    "PromptProfileValidator",
    "RunAccessDenied",
    "RunConflict",
    "RunNotFound",
    "RunSummary",
    "StateRejected",
    "StateStoreUnavailable",
    "StoredStateInvalid",
    "UpdateGameConfiguration",
    "UpdateGameConfigurationRequest",
]
